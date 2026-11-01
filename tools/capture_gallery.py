"""Capture the actual Gallery, production replay frames and save-safe return.

Run with the game's Python environment and ffmpeg installed:
  python tools/capture_gallery.py --mode all

SDL dummy has no audio loopback. The MP4 is deliberately silent; it demonstrates
rendering and input, not perceptual audio review. All scene animation clocks run
at 30 Hz. Only dialogue acknowledgement is automated, through normal input.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont
import pygame
from main import Game
from cutscene_gallery import GALLERY_ENTRIES, GALLERY_BY_ID

FPS = 30
OUT = ROOT/'docs/reviews/gallery'
THUMBS = ROOT/'assets/ui/gallery'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def runtime_digest():
    digest = hashlib.sha256()
    for path in sorted(ROOT.glob('*.py')):
        digest.update(path.name.encode()+b'\0'+path.read_bytes()+b'\0')
    return digest.hexdigest()


def key(game, value):
    game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=value, repeat=False),
                        pygame.event.Event(pygame.KEYUP, key=value)])


def point(game, native, size=(480, 320)):
    if size == (480, 320) and game.gallery_session is not None:
        session = game.gallery_session
        scale, _, origin = session.game._ensure_ui_surface()
        offset = session.viewport_rect.topleft
        return (round(offset[0]+origin[0]+native[0]*scale),
                round(offset[1]+origin[1]+native[1]*scale))
    width, height = game.window.get_size()
    scale = max(1, min(width//size[0], height//size[1])) if size == (480, 320) else min(width/size[0],height/size[1])
    return (round((width-size[0]*scale)/2+native[0]*scale),
            round((height-size[1]*scale)/2+native[1]*scale))


def click(game, native, size=(480, 320)):
    position = point(game, native, size)
    game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position),
                        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=position)])


def acknowledge(game):
    session = game.gallery_session
    if session is None:return
    child = session.game
    if child.social.choosing:
        child.draw()
        click(game, child.social.choice_rects[0].center)
    elif child.social.active or (child.regent_arrival.active and child.regent_arrival.dialogue is not None):
        key(game, pygame.K_SPACE)


def phase(game):
    return {'opening': game.opening.stage,
            'opening_action': (game.opening._action or {}).get('name'),
            'opening_action_seconds': round(game.opening._action_time, 4),
            'cinematic_seconds': round(game.opening_cinematic.elapsed, 4),
            'arrival_shot': game.regent_arrival.shot,
            'arrival_seconds': round(game.regent_arrival.phase_time, 4),
            'elira_action': game.elira_visit.action,
            'elira_seconds': round(game.elira_visit.action_time, 4),
            'venn_phase': game.venn_visit.phase,
            'venn_seconds': round(game.venn_visit.phase_time, 4),
            'mill_action': game.mill_quest.action,
            'mill_seconds': round(game.mill_quest.action_time, 4),
            'mill_camera': game.mill_quest.encounter_cutscene_phase,
            'lantern_action': game.lantern_quest.action,
            'lantern_seconds': round(game.lantern_quest.action_time, 4),
            'lantern_stage': game.lantern_quest.stage,
            'regent_stage': game.regent_quest.stage,
            'regent_cart_released': game.regent_quest.cart_released,
            'halden_action': game.halden_visit.action,
            'halden_seconds': round(game.halden_visit.action_time,4),
            'tomas_job': game.halden_visit.tomas_job,
            'bridge_stage': getattr(getattr(game.world,'bridge_crew',None),'stage',None),
            'bridge_seconds': round(getattr(getattr(game.world,'bridge_crew',None),'timer',0),4),
            'grain_stage': getattr(getattr(game.world,'grain_farm',None),'stage',None),
            'grain_seconds': round(getattr(getattr(game.world,'grain_farm',None),'timer',0),4),
            'garden_phase': getattr(getattr(game.world,'garden_orchard',None),'state',{}).get('gardener',{}).get('phase'),
            'garden_step': getattr(getattr(game.world,'garden_orchard',None),'state',{}).get('gardener',{}).get('step'),
            'garden_seconds': round(getattr(getattr(game.world,'garden_orchard',None),'state',{}).get('gardener',{}).get('elapsed',0),4),
            'wildlife_vignette': dict(getattr(getattr(game.world,'wildlife',None),'vignette',{})),
            'checkpoint_stage': getattr(getattr(game.world,'checkpoint_charm',None),'stage',None),
            'checkpoint_state': getattr(getattr(game.world,'checkpoint_charm',None),'to_dict',lambda:None)(),
            'dialogue': game.social.script_identifier}


def thumbnail_ready(identifier, g, seconds):
    if identifier == 'checkpoint_borrowed_seat':
        return g.world.checkpoint_charm.stage == 'banter'
    if identifier == 'sheep_basket_visit':
        from purposeful_wildlife import PAT_STEP
        visit = g.world.wildlife.vignette
        return (visit['phase'] == 'visit' and visit['step'] == PAT_STEP
                and visit['contact'] and visit['basket'] == 'pen')
    if identifier == 'garden_quiet_care':
        controller = g.world.garden_orchard
        state = controller.state['gardener']
        action = controller.action('gardener') or {}
        return (state['phase'] == 'scene' and action.get('kind') == 'put'
                and action.get('item') == 'plant' and state['elapsed'] >= .9)
    if identifier == 'halden_medicine':return g.halden_visit.action == 'medicine' and g.halden_visit.action_time >= .4
    if identifier == 'tomas_sack':return g.halden_visit.tomas_job == 'carry' and g.halden_visit.tomas.position.y < 230
    if identifier == 'bridge_tea':return g.world.bridge_crew.stage == 'reach' and g.world.bridge_crew.timer > .7
    if identifier == 'grain_extra_sack':return g.world.grain_farm.stage == 'help_place' and g.world.grain_farm.timer > .4
    if identifier == 'later_journey':return seconds >= 27
    if identifier == 'morning_wake':return (g.opening._action or {}).get('name') == 'wake_up' and g.opening._action_time >= .5
    if identifier == 'morning_breakfast':return (g.opening._action or {}).get('name') == 'eat' and g.opening._action_time >= .6
    if identifier.startswith('elira_'):return g.elira_visit.action_time >= (1.45 if identifier.endswith('retrieval') else .7)
    if identifier.startswith('venn_'):
        return g.venn_visit.phase == ('attempt' if identifier == 'venn_failed_spell' else 'work_pin') and g.venn_visit.phase_time >= .35
    if identifier == 'halden_arrival':return g.opening_conclusion.settled and g.social.active
    if identifier == 'millrace_threat':return g.mill_quest.encounter_cutscene_phase == 'conversation' and g.mill_quest._encounter_elapsed >= .2
    if identifier.startswith('mill_'):return g.mill_quest.action is not None and g.mill_quest.action_time >= .75
    if identifier == 'regent_arrival':return g.regent_arrival.shot == 'gate_approach' and g.regent_arrival.phase_time >= 3.3
    if identifier == 'regent_cart_release':return g.regent_quest.cart_released and g.regent_quest._release_time >= .6
    wanted = {'lantern_frame':'assemble', 'lantern_collect':'rest_pickup',
              'lantern_homecoming':'rest_place', 'lantern_paper_practice':'rest_draft',
              'lantern_finishing':'finish_pickup', 'lantern_putaway':'finish_place'}
    return g.lantern_quest.action == wanted.get(identifier) and g.lantern_quest.action_time >= .65


def crop_rect(identifier, game):
    if identifier in ('later_journey', 'regent_arrival'):
        return pygame.Rect(0, 25, 480, 270)
    camera = game.camera.position()
    protagonist = getattr(game.player, 'story_position', None) or game.player.position
    center = pygame.Vector2(protagonist)-camera+(0,-20)
    width = 240
    if identifier == 'checkpoint_borrowed_seat':
        center = pygame.Vector2(365,-2182)-camera
        width = 240
    elif identifier == 'sheep_basket_visit':
        center = pygame.Vector2(-357,1404)-camera
        width = 128
    elif identifier == 'garden_quiet_care':
        center = pygame.Vector2(-538,1156)-camera
        width = 240
    elif identifier == 'tomas_sack':
        center = game.halden_visit.tomas.position-camera+(0,-20)
    elif identifier in ('bridge_tea','grain_extra_sack'):
        width = 320
    elif identifier.startswith('venn_'):
        width = 192
    elif identifier == 'millrace_threat':
        center = pygame.Vector2(240, 105)
        width = 320
    elif identifier.startswith('lantern_'):
        center = (pygame.Vector2(protagonist)+game.lantern_quest.liam.position)/2-camera+(0,-14)
    elif identifier.startswith('mill_'):
        center = (pygame.Vector2(protagonist)+game.mill_quest.mira.position)/2-camera+(0,-18)
    elif identifier == 'halden_arrival':
        center = (pygame.Vector2(protagonist)+game.opening_conclusion.halden.position)/2-camera+(0,-20)
    elif identifier == 'regent_cart_release':
        center = game.regent_quest.venn.position-camera+(0,-18)
        width = 288
    elif identifier == 'morning_breakfast':
        center = (pygame.Vector2(game.opening.data['caelan_seated_position'])+pygame.Vector2(game.opening.data['tomas_seated_position']))/2-camera+(0,-15)
        width = 240
    rect = pygame.Rect(0, 0, width, round(width*9/16));rect.center = tuple(round(x) for x in center)
    return rect.clamp(pygame.Rect(0, 0, 480, 320))


def capture_thumbnails(identifiers=None):
    OUT.mkdir(parents=True, exist_ok=True);THUMBS.mkdir(parents=True, exist_ok=True)
    records = []
    entries = [entry for entry in GALLERY_ENTRIES if identifiers is None or entry.id in identifiers]
    source = {'source_commit':git('rev-parse','HEAD'), 'runtime_python_sha256':runtime_digest()}
    parent = Game(fullscreen=False)
    parent.open_gallery()
    for entry in entries:
        random.seed(9182)
        assert parent.launch_gallery_scene(entry.id), (entry.id, parent.gallery.error)
        session = parent.gallery_session
        selected = None
        fallback = None
        for frame in range(FPS*120):
            if frame % 6 == 0:acknowledge(parent)
            parent.update(1/FPS, (0, 0), False)
            if session.closed:break
            g = session.game
            if frame % 3 == 0:
                g.draw()
                fallback = (g.canvas.copy(), phase(g), crop_rect(entry.id,g), frame)
                if thumbnail_ready(entry.id, g, (frame+1)/FPS):
                    selected = fallback;break
        if selected is None:
            raise AssertionError(('Representative thumbnail cue was never reached', entry.id,
                                  fallback[1] if fallback else None))
        surface, state, rect, frame = selected
        image = Image.frombytes('RGB', surface.get_size(), pygame.image.tobytes(surface, 'RGB'))
        image = image.crop((rect.left,rect.top,rect.right,rect.bottom)).resize((320,180),Image.Resampling.NEAREST)
        path = THUMBS/f'{entry.id}.png';image.save(path,optimize=True)
        records.append({'id':entry.id,'name':entry.name,'source':'production Game.canvas',
                        'file':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'frame':frame,'seconds':round((frame+1)/FPS,4),'crop':list(rect),'state':state})
        if identifiers is not None:
            records[-1].update(source)
            # A focused addition also leaves its full replay composition for
            # review, including the actual Gallery toolbar and normal zoom.
            parent.draw()
            still = OUT/f'regional_{entry.id}.png'
            pygame.image.save(parent.window,str(still))
            records[-1]['review_frame'] = str(still.relative_to(ROOT))
        session.close()
        g = session = None
        gc.collect()
        print('thumbnail',entry.id,frame,flush=True)
    parent.music.stop();pygame.quit()
    metadata = {**source,'fps':FPS,
        'method':'Real isolated Gallery fixtures, normal 30 Hz updates and dialogue input; world canvas cropped before UI.',
        'entries':records}
    if identifiers is not None and (THUMBS/'capture.json').exists():
        # Retain the original catalogue-wide provenance and every untouched
        # thumbnail. A focused recapture supplies its own per-entry source.
        metadata = json.loads((THUMBS/'capture.json').read_text())
        by_id = {record['id']:record for record in metadata['entries']}
        by_id.update({record['id']:record for record in records})
        records = [by_id[entry.id] for entry in GALLERY_ENTRIES if entry.id in by_id]
        metadata['entries'] = records
    (THUMBS/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    montage = Image.new('RGB',(960,240*((len(records)+2)//3)),'#10271f')
    draw = ImageDraw.Draw(montage)
    font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'),17)
    for index,record in enumerate(records):
        x=(index%3)*320;y=(index//3)*240
        montage.paste(Image.open(ROOT/record['file']),(x,y))
        draw.text((x+8,y+188),record['name'],font=font,fill='#f8f0d9')
        draw.text((x+8,y+211),record['id'],font=font,fill='#b7c3af')
    montage.save(OUT/'thumbnail_contact_sheet.jpg',quality=88)
    return records


class Review:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory/'journey.json'
        seed = Game(fullscreen=False,start_on_title=False,save_path=self.path)
        seed.begin_journey(False,show_cinematic=False)
        assert seed.save_progress()
        seed.music.stop();seed.opening_audio.reset()
        self.saved_bytes = self.path.read_bytes()
        self.g = Game(window_size=(1280,720),fullscreen=False,save_path=self.path)
        pygame.event.clear()
        assert self.g.has_saved_journey
        self.frame_index = 0;self.events = [];self.screenshots = []
        self.encoder = subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y',
            '-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','-',
            '-an','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(OUT/'gallery_review.mp4')],stdin=subprocess.PIPE)

    def mark(self, name, **details):
        self.events.append({'event':name,'frame':self.frame_index,'seconds':round(self.frame_index/FPS,3),**details})

    def frame(self):
        self.g.update(1/FPS,(0,0),False);self.g.draw()
        self.encoder.stdin.write(pygame.image.tobytes(self.g.window,'RGB'))
        self.frame_index += 1

    def hold(self,seconds):
        for _ in range(round(seconds*FPS)):self.frame()

    def screenshot(self,name):
        self.g.draw();pygame.image.save(self.g.window,str(OUT/name));self.screenshots.append(name)

    def select(self,identifier, mouse=False):
        gallery=self.g.gallery
        target=next(index for index,e in enumerate(gallery.entries) if e.id==identifier)
        # All selection navigation in the recorded run uses real keyboard input.
        while gallery.selected != target:
            key(self.g,pygame.K_DOWN if gallery.selected<target else pygame.K_UP)
            self.hold(.10)
        self.hold(.8)
        if mouse:
            click(self.g,gallery.rows[target].center,(640,360))
        else:key(self.g,pygame.K_RETURN)
        assert self.g.gallery_session is not None
        self.mark('scene_launched',id=identifier,input='mouse' if mouse else 'keyboard',selected=target,scroll=gallery.scroll)

    def return_check(self,identifier):
        assert self.g.gallery_session is None
        assert self.g.gallery.selected_entry.id == identifier
        assert self.path.read_bytes()==self.saved_bytes
        self.mark('returned_to_gallery',id=identifier,selected=self.g.gallery.selected,scroll=self.g.gallery.scroll,
                  saved_bytes_unchanged=True)
        self.hold(1)

    def run(self):
        g=self.g
        self.mark('title');self.hold(1.4);self.screenshot('title_gallery.png')
        key(g,pygame.K_DOWN);key(g,pygame.K_DOWN);key(g,pygame.K_RETURN)
        assert g.on_gallery
        self.mark('gallery_open_keyboard');self.hold(1.8);self.screenshot('gallery_top.png')
        g.handle_events([pygame.event.Event(pygame.MOUSEWHEEL,x=0,y=-4)])
        self.mark('wheel_scroll');self.hold(1);self.screenshot('gallery_middle.png')
        key(g,pygame.K_END);self.hold(1);self.screenshot('gallery_bottom.png')
        key(g,pygame.K_HOME);self.hold(.6)
        self.select('later_journey')
        self.hold(27);self.screenshot('replay_prologue.png')
        child=g.gallery_session.game
        click(g,child.opening_cinematic.skip_rect.center)
        self.hold(.8);self.return_check('later_journey')
        child = None;gc.collect()
        self.select('regent_arrival',mouse=True)
        for frame in range(FPS*18):
            if frame%30==0:acknowledge(g)
            self.frame()
        self.screenshot('replay_arrival.png')
        key(g,pygame.K_ESCAPE);self.return_check('regent_arrival')
        self.select('mill_repair')
        session=g.gallery_session
        screenshot=False
        for frame in range(FPS*70):
            if g.gallery_session is None:break
            if frame%24==0:acknowledge(g)
            self.frame()
            if not screenshot and session.game.mill_quest.action_time>=1:
                self.screenshot('replay_mill_repair.png');screenshot=True
        assert g.gallery_session is None,'Mill repair must complete naturally'
        self.return_check('mill_repair')
        session = None;gc.collect()
        self.select('lantern_finishing',mouse=True)
        session=g.gallery_session
        screenshot=False
        for frame in range(FPS*100):
            if g.gallery_session is None:break
            if frame%12==0:acknowledge(g)
            self.frame()
            if not screenshot and session.game.lantern_quest.action=='finish_pickup' and session.game.lantern_quest.action_time>.7:
                self.screenshot('replay_lantern_finished.png');screenshot=True
        assert g.gallery_session is None,'Lantern finishing must complete naturally'
        self.return_check('lantern_finishing')
        self.screenshot('gallery_return_selection.png')
        key(g,pygame.K_ESCAPE);assert g.on_title and not g.on_gallery
        self.hold(.8)
        key(g,pygame.K_UP);key(g,pygame.K_RETURN)
        self.hold(1)
        assert not g.on_title and g.world.data['id']=='sanctuary_bedroom'
        self.mark('continue_original_journey',scene=g.world.data['id'],opening=g.opening.stage)
        self.screenshot('continue_original_save.png');self.hold(2)
        self.encoder.stdin.close();assert self.encoder.wait()==0
        return {'source_commit':git('rev-parse','HEAD'),'runtime_python_sha256':runtime_digest(),'fps':FPS,'frames':self.frame_index,
                'duration_seconds':round(self.frame_index/FPS,3),
                'audio':'Silent video: SDL dummy provides no audio loopback; no perceptual listening claim.',
                'dialogue_input':'Automated 0.4–1.0s acknowledgement cadence; all authored action/camera clocks still run at normal 30 Hz.',
                'save_sha256_before_previews':hashlib.sha256(self.saved_bytes).hexdigest(),
                'save_bytes_unchanged_through_all_previews':True,'events':self.events,'screenshots':self.screenshots}


def responsive_stills():
    records=[]
    game=Game(window_size=(960,640),fullscreen=False)
    game.open_gallery()
    for size,scale in (((960,640),1.0),((480,320),1.5),((800,800),1.5),((1920,810),1.0)):
        game.window=pygame.display.set_mode(size,pygame.RESIZABLE)
        game.audio.text_scale=scale
        key(game,pygame.K_HOME);game.draw()
        name=f'gallery_{size[0]}x{size[1]}_text{scale:g}.png'
        pygame.image.save(game.window,str(OUT/name))
        records.append({'file':name,'size':size,'text_scale':scale,'no_save':not game.has_saved_journey})
    game.music.stop();pygame.quit()
    return records


def preview_stills():
    """Inspect real caption layouts and a regional action below the toolbar."""
    records=[]
    game=Game(fullscreen=False)
    game.open_gallery()
    specs=(
        ('arrival_dialogue_960x640.png','regent_arrival',(960,640),1.0),
        ('arrival_dialogue_480x320_text1.5.png','regent_arrival',(480,320),1.5),
        ('millrace_dialogue_960x640.png','millrace_threat',(960,640),1.0),
        ('millrace_dialogue_480x320_text1.5.png','millrace_threat',(480,320),1.5),
        ('regional_bridge_tea.png','bridge_tea',(960,640),1.0),
        ('regional_garden_quiet_care.png','garden_quiet_care',(960,640),1.0),
    )
    for filename,identifier,size,text_scale in specs:
        game.window=pygame.display.set_mode(size,pygame.RESIZABLE)
        game.audio.text_scale=text_scale
        assert game.launch_gallery_scene(identifier)
        session=game.gallery_session
        reached=False
        for frame in range(FPS*60):
            game.update(1/FPS,(0,0),False)
            if session.closed:break
            child=session.game
            game.draw()
            if identifier=='regent_arrival':
                reached=child.regent_arrival.shot=='gate_greeting' and child.regent_arrival.dialogue is not None
            elif identifier=='millrace_threat':
                reached=child.mill_quest.encounter_cutscene_phase=='conversation' and child.social.active
            else:reached=thumbnail_ready(identifier,child,(frame+1)/FPS)
            if reached:
                pygame.image.save(game.window,str(OUT/filename))
                records.append({'file':filename,'scene':identifier,'size':size,'text_scale':text_scale,
                                'frame':frame,'state':phase(child)})
                break
            if frame%12==0:acknowledge(game)
        assert reached,('Preview screenshot cue not reached',identifier)
        session.close();session=child=None;gc.collect()
    game.music.stop();pygame.quit()
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('all','thumbnails','review'),default='all')
    parser.add_argument('--scene',action='append',choices=tuple(GALLERY_BY_ID),
                        help='Capture only this thumbnail; repeat to select several. Requires --mode thumbnails.')
    args=parser.parse_args()
    if args.scene and args.mode != 'thumbnails':parser.error('--scene requires --mode thumbnails')
    OUT.mkdir(parents=True,exist_ok=True)
    if args.mode in ('all','thumbnails'):capture_thumbnails(args.scene)
    if args.mode in ('all','review'):
        with tempfile.TemporaryDirectory(prefix='gallery-capture-') as directory:
            review=Review(directory)
            try:metadata=review.run()
            finally:
                if review.encoder.poll() is None:
                    review.encoder.stdin.close();review.encoder.wait()
                if review.g.gallery_session is not None:review.g.gallery_session.close()
                review.g.music.stop();review.g.opening_audio.reset();pygame.quit()
        metadata['responsive_stills']=responsive_stills()
        metadata['preview_stills']=preview_stills()
        (OUT/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
        print(json.dumps({'video':str(OUT/'gallery_review.mp4'),'duration_seconds':metadata['duration_seconds']}),flush=True)


if __name__=='__main__':main()
