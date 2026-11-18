"""Inspect existing Iselin cinematics and optional clips in an isolated Gallery.

No production art or scene file is written. The built-in probe switches between
existing still drawings to test playback mechanics; it is not new performance art.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
REVIEW=ROOT/'docs/reviews/iselin_cinematic_foundation'
OUT=Path(tempfile.gettempdir())/'iselin-cinematic-preview'
GROUND=ROOT/'assets/story/regent_arrival/actors/iselin/animation.json'
SCENE=ROOT/'assets/story/regent_arrival/scene.json'
PROBE='synthetic_mechanic_probe'
CUE='review:iselin'


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def font(size):
    from PIL import ImageFont
    return ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'),size)


def preservation():
    baseline=json.loads((REVIEW/'preservation_baseline.json').read_text())
    changed=[name for name,value in baseline['sha256'].items()
             if not (ROOT/name).is_file() or digest(ROOT/name)!=value]
    if changed:raise ValueError('Historical PR1 preservation check failed: '+', '.join(changed))
    return {'baseline_commit':baseline['base_commit'],
            'png_count':baseline['iselin_png_count'],'json_count':baseline['production_json_count'],
            'all_unchanged':True}


def reference_board(output):
    from PIL import Image,ImageDraw
    board=Image.new('RGB',(1280,690),'#e8edf2');draw=ImageDraw.Draw(board)
    draw.text((16,10),'EXISTING ISELIN REFERENCES / NO NEW ARTWORK',font=font(23),fill='#263c35')
    draw.text((16,43),'Each group labels its own canvas and inspection enlargement; these are different camera slots.',
              font=font(16),fill='#263c35')
    refs=[]
    def paste(path,x,y,scale,label):
        image=Image.open(ROOT/path).convert('RGBA')
        large=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
        board.paste(large,(x,y),large)
        draw.text((x,y+large.height+7),label,font=font(14),fill='#263c35')
        refs.append({'path':path,'sha256':digest(ROOT/path),'canvas':list(image.size),'enlargement':scale})
    for index,direction in enumerate(('front','left','right','back')):
        paste(f'assets/characters/iselin/native_idles/idle_{direction}.png',16+index*150,104,4,
              f'{direction}:24x36 /4x')
    paste('assets/story/regent/poses/iselin_seated.png',646,104,4,'seated:24x36 /4x')
    for index,name in enumerate(('overhead','oblique')):
        paste(f'assets/story/regent_aerial/actors/iselin/{name}.png',834+index*210,84,3,
              f'{name}:48x64 /3x')
    data=json.loads(GROUND.read_text())
    for index,(name,filename) in enumerate(data['poses'].items()):
        paste('assets/story/regent_arrival/actors/iselin/'+filename,16+index*208,370,2,
              name+' /80x96 /2x')
    draw.text((16,651),'Native idles/seat:world scale. Ground/aerial:existing cinematic camera presentation. No limb edits or interpolation.',
              font=font(15),fill='#263c35')
    board.save(output/'reference_board.png')
    return refs


def probe_record():
    return {'classification':'Synthetic mechanic probe using existing still poses; not authored performance animation.',
            'actions':{PROBE:{'entry':[{'pose':'stand_left','duration_ms':100}],
                 'hold':{'pose':'gesture_left','duration_ms':None},
                 'recovery':[{'pose':'listen_left','duration_ms':120}],
                 'rest_pose':'stand_left'}}}


class Review:
    def __init__(self,args,directory):
        import pygame
        from main import Game
        from cinematic_actor_actions import load_actions
        self.args=args;self.output=args.out;self.pygame=pygame
        self.parent=Game(window_size=(960,640),fullscreen=False,start_on_title=True,
                         save_path=Path(directory)/'journey.json',settings_path=Path(directory)/'settings.json')
        self.parent.audio.set_music(0);self.parent.audio.set_effects(0)
        if not self.parent.open_gallery() or not self.parent.launch_gallery_scene('regent_arrival'):
            raise ValueError('The isolated arrival Gallery could not start')
        self.session=self.parent.gallery_session;self.child=self.session.game;self.scene=self.child.regent_arrival
        self.parent.draw()  # Let the production renderer initialize its lazy art cache.
        self.original=deepcopy(self.scene.data);self.art=self.scene.actor_art['iselin']
        self.action=PROBE if args.probe else args.action
        self.release_at=args.release_at if args.release_at is not None else (.3 if args.probe else None)
        self.source_file=None;self.input_hashes={}
        if args.probe:
            self.source_file=self.output/'synthetic_probe.json'
            self.source_file.write_text(json.dumps(probe_record(),indent=2)+'\n')
        elif args.action_file:self.source_file=args.action_file.resolve()
        if self.source_file is not None:
            record=json.loads(self.source_file.read_text())
            canvas=list(next(iter(self.art['poses'].values())).get_size())
            if 'canvas' in record and record['canvas']!=canvas:
                raise ValueError('Clip file canvas must match the selected80x96 ground actor')
            record={**record,'canvas':canvas}
            clips=load_actions(record,self.art['poses'],self.source_file,
                               lambda path:pygame.image.load(str(path)).convert_alpha())
            self.art['actions']=clips
            self.input_hashes[str(self.source_file)]=digest(self.source_file)
            # Include file-frame inputs alongside the clip definition.
            for action in record.get('actions',{}).values():
                for frame in (*action['entry'],action['hold'],*action['recovery']):
                    if 'file' in frame:
                        path=(self.source_file.parent/frame['file']).resolve()
                        self.input_hashes[str(path)]=digest(path)
        self.restart()

    def restart(self,*,release_at='default'):
        self.scene.clear_actor_actions()
        self.scene.data=deepcopy(self.original)
        self.scene.phase_index=next(i for i,p in enumerate(self.scene.data['phases']) if p['id']==self.args.shot)
        self.scene.phase_time=self.args.shot_time;self.scene.elapsed=0
        self.scene.dialogue_index=self.scene.page_index=0
        self.scene.paused=False;self.scene.focused=True;self.scene.active=True
        self.child._music_focused=True
        actors=[actor for actor in self.scene.phase['actors'] if actor['id']=='iselin']
        if (self.args.pose or self.args.loop or self.action) and not actors:
            raise ValueError('The selected shot has no ground Iselin actor; use its authored aerial presentation or a ground shot')
        selected=self.args.pose or self.args.loop
        if selected:
            bank=self.art['poses'] if self.args.pose else self.art['loops']
            if selected not in bank:raise ValueError('Unknown selected pose/loop: '+selected)
            # This is an explicit review selection in the isolated scene data,
            # not a patched runtime function or a production scene edit.
            for actor in actors:
                for field in ('pose','before_pose','after_pose','turn_pose'):actor[field]=selected
                actor['route_poses']=[[0,selected]]
        self.elapsed=0.;self.paused=False;self.released=False
        self.current_release=self.release_at if release_at=='default' else release_at
        self.started=None
        if self.action:
            self.started=self.scene.play_actor_action('iselin',self.action,CUE)
            if not self.started:raise ValueError('The selected actor action could not start in this shot')

    def state(self):
        return {'time':round(self.elapsed,8),'shot':self.scene.shot,
                'shot_seconds':round(self.scene.phase_time,8),
                'action':self.scene.actor_action_state('iselin')}

    def release(self):
        result=self.scene.release_actor_action('iselin',CUE)
        self.released=True
        return result

    def advance(self,seconds):
        if (self.paused or self.scene.paused or not self.scene.focused
                or not self.child._music_focused):return
        goal=self.elapsed+seconds
        while self.elapsed+1e-10<goal:
            if self.action and not self.released and self.current_release is not None and self.current_release<=self.elapsed+1e-10:
                self.release()
            step=min(1/self.args.fps,goal-self.elapsed)
            if self.action and not self.released and self.current_release is not None:
                step=min(step,max(0.,self.current_release-self.elapsed))
            if step<=1e-10:continue
            self.child.update(step,(0,0),False);self.elapsed+=step
        if self.action and not self.released and self.current_release is not None and self.current_release<=self.elapsed+1e-10:
            self.release()

    def seek(self,seconds):
        self.restart();self.advance(max(0.,seconds))

    def draw(self):
        from PIL import Image,ImageDraw
        self.parent.draw()
        raw=Image.frombytes('RGB',self.parent.window.get_size(),
                            self.pygame.image.tobytes(self.parent.window,'RGB'))
        labelled=Image.new('RGB',(raw.width,raw.height+64),'#e8edf2');labelled.paste(raw,(0,64))
        draw=ImageDraw.Draw(labelled)
        mode='SYNTHETIC MECHANIC PROBE / EXISTING STILLS' if self.args.probe else (
             'REVIEW '+('POSE:'+self.args.pose if self.args.pose else 'LOOP:'+self.args.loop if self.args.loop else
                        'ACTION:'+self.action if self.action else 'AUTHORED SHOT'))
        draw.text((12,8),mode,font=font(18),fill='#263c35')
        state=self.scene.actor_action_state('iselin')
        draw.text((12,34),f'{self.scene.shot} / t={self.elapsed:.3f}s / {state["stage"]} / selected shot; isolated Gallery',
                  font=font(15),fill='#263c35')
        return labelled

    def close(self):
        self.session.close();self.parent.opening_audio.reset();self.parent.regional_audio.reset()
        self.parent.music.stop();self.pygame.quit()


def write_gif(path,frames,durations):
    from PIL import Image
    palette=frames[0].quantize(colors=256)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=durations,
                    loop=0,disposal=1,optimize=False)
    total=0
    with Image.open(path) as image:
        count=image.n_frames
        if count!=len(indexed):raise ValueError('GIF sampled frame count changed')
        for index in range(count):
            image.seek(index);total+=image.info['duration']
            if image.info['duration']!=durations[index]:
                raise ValueError('GIF sampled exposure changed')
            if image.convert('RGB').tobytes()!=indexed[index].convert('RGB').tobytes():
                raise ValueError('GIF decoded frame differs from its quantized source')
    if total!=sum(durations):raise ValueError('GIF playback duration was not preserved')
    return {'frames':count,'total_ms':total,'decoded_frames_match_quantized_sources':True,
            'sample_exposures_preserved':True,'disposal':1}


def exposures(count,fps,speed):
    edges=[round(index*100/fps/speed)*10 for index in range(count+1)]
    values=[b-a for a,b in zip(edges,edges[1:])]
    if min(values)<10:raise ValueError('GIF speed/fps requires less than its10ms minimum exposure')
    return values


def headless(review,args):
    from PIL import Image,ImageDraw
    observations=[];frames=[]
    count=max(1,round(args.seconds*args.fps))
    for index in range(count):
        review.seek(index/args.fps)
        frames.append(review.draw());observations.append(review.state())
    gifs={'preview.gif':write_gif(args.out/'preview.gif',frames,exposures(count,args.fps,args.speed)),
          'preview_slow.gif':write_gif(args.out/'preview_slow.gif',frames,exposures(count,args.fps,args.speed/4))}
    stills=[]
    for index,seconds in enumerate(args.samples):
        review.seek(seconds);image=review.draw();name=f'sample_{index:02}.png';image.save(args.out/name)
        stills.append({'file':name,**review.state()})
    board=Image.new('RGB',(960,3*int(math.ceil(len(stills)/3))*110),'#e8edf2')
    # Six actual selected-shot frames at320px width retain the full composition.
    for index,record in enumerate(stills):
        image=Image.open(args.out/record['file']).convert('RGB')
        image=image.resize((320,235),Image.Resampling.NEAREST)
        y=(index//3)*330;board.paste(image,((index%3)*320,y))
        ImageDraw.Draw(board).text(((index%3)*320+8,y+245),
             f't={record["time"]:.3f}s / {record["action"]["stage"]}',font=font(16),fill='#263c35')
    board.save(args.out/'samples.png')
    checks={}
    if args.probe:
        review.restart();initial=review.scene.actor_action_state('iselin')
        checks['duplicate_cue_ignored']=not review.scene.play_actor_action('iselin',PROBE,CUE)
        checks['duplicate_does_not_reset']=review.scene.actor_action_state('iselin')==initial
        checks['busy_distinct_cue_ignored']=not review.scene.play_actor_action('iselin',PROBE,CUE+':busy')
        review.advance(.15);before=review.scene.actor_action_state('iselin')
        review.scene.paused=True;review.child.update(.5,(0,0),False)
        checks['pause_clock_frozen']=review.scene.actor_action_state('iselin')==before
        review.draw();review.draw();checks['draw_queries_are_pure']=review.scene.actor_action_state('iselin')==before
        review.scene.paused=False
        review.scene.handle_event(review.pygame.event.Event(review.pygame.WINDOWFOCUSLOST))
        before=review.state();review.advance(.5)
        checks['focus_freezes_review_and_runtime']=review.state()==before
        review.scene.handle_event(review.pygame.event.Event(review.pygame.WINDOWFOCUSGAINED))
        review.restart(release_at=.05);review.advance(.05)
        early=review.scene.actor_action_state('iselin')
        checks['early_release_finishes_entry']=early['stage']=='entry' and early['release_requested']
        review.advance(.25);checks['early_release_recovers_to_rest']=review.scene.actor_action_state('iselin')['stage']=='rest'
        review.draw().save(args.out/'early_release.png')
        review.restart();checks['restart_accepts_same_cue']=review.started is True
        if not all(checks.values()):raise ValueError('Synthetic mechanic check failed: '+str(checks))
    return {'gif_playback':gifs,'timeline_samples':observations,'meaningful_samples':stills,'mechanic_checks':checks}


def interactive(review,args):
    pygame=review.pygame;clock=pygame.time.Clock();running=True;speed=args.speed;snap=0
    print('Space:pause | R:restart | S:normal/quarter | Left/Right:20ms step | E:release | F:PNG | Esc:exit')
    while running:
        dt=min(clock.tick(60)/1000,.1)
        for event in pygame.event.get():
            if event.type==pygame.QUIT:running=False
            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:running=False
                elif event.key==pygame.K_SPACE:
                    review.paused=not review.paused;review.scene.paused=review.paused
                elif event.key==pygame.K_r:review.restart()
                elif event.key==pygame.K_s:speed=.25 if speed==1 else 1
                elif event.key in (pygame.K_LEFT,pygame.K_RIGHT):
                    target=max(0,review.elapsed+(.02 if event.key==pygame.K_RIGHT else -.02))
                    review.seek(target);review.paused=True;review.scene.paused=True
                elif event.key==pygame.K_e:review.release()
                elif event.key==pygame.K_f:
                    review.draw().save(args.out/f'interactive_{snap:03}.png');snap+=1
            elif event.type in (pygame.WINDOWFOCUSLOST,pygame.WINDOWFOCUSGAINED):
                review.scene.handle_event(event)
        if running:
            review.advance(dt*speed);review.draw()


def main():
    parser=argparse.ArgumentParser(description=__doc__,epilog='External clips: {"actions":{"name":{"entry":[{"pose":"stand_left","duration_ms":100}],"hold":{"pose":"gesture_left","duration_ms":null},"recovery":[{"pose":"listen_left","duration_ms":120}],"rest_pose":"stand_left"}}}. File frames use file:"local.png" instead of pose and must be80x96 PNGs beside that JSON.')
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--board-only',action='store_true')
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--shot',default='relief')
    parser.add_argument('--shot-time',type=float,default=0)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--pose');group.add_argument('--loop');group.add_argument('--action')
    group.add_argument('--probe',action='store_true',help='Synthetic existing-still mechanic test; not new performance art')
    parser.add_argument('--action-file',type=Path)
    parser.add_argument('--release-at',type=float)
    parser.add_argument('--seconds',type=float,default=1)
    parser.add_argument('--speed',type=float,choices=(1,.25),default=1)
    parser.add_argument('--fps',type=int,default=50)
    parser.add_argument('--samples',default='0,.05,.1,.3,.42,.7')
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--check-preservation',action='store_true',help='Check the historical PR1 baseline; leave off for future intentional asset edits')
    args=parser.parse_args()
    data=json.loads(SCENE.read_text());art=json.loads(GROUND.read_text())
    if args.list:
        print(json.dumps({'shots':[p['id'] for p in data['phases']],'poses':list(art['poses']),
                          'loops':list(art['loops']),'actions':list(art.get('actions',{}))},indent=2));return
    if args.shot not in {p['id'] for p in data['phases']}:parser.error('Unknown arrival shot')
    if args.action_file and not args.action:parser.error('--action-file requires --action NAME')
    if not 1<=args.fps<=100:parser.error('--fps must be between1 and100')
    if not math.isfinite(args.seconds) or args.seconds<=0:parser.error('--seconds must be positive and finite')
    if not math.isfinite(args.shot_time) or args.shot_time<0:parser.error('--shot-time must be nonnegative and finite')
    if args.release_at is not None and (not math.isfinite(args.release_at) or args.release_at<0):parser.error('--release-at must be nonnegative and finite')
    try:args.samples=[float(value) for value in args.samples.split(',')]
    except ValueError:parser.error('--samples needs comma-separated seconds')
    if not args.samples or any(not math.isfinite(value) or value<0 for value in args.samples):parser.error('--samples must be nonnegative and finite')
    args.out.mkdir(parents=True,exist_ok=True)
    proof=preservation() if args.check_preservation else None
    references=reference_board(args.out)
    if args.board_only:return
    if args.headless:
        os.environ['SDL_VIDEODRIVER']='dummy';os.environ.setdefault('SDL_AUDIODRIVER','dummy')
    result={}
    with tempfile.TemporaryDirectory(prefix='iselin-cinematic-preview-') as directory:
        review=Review(args,directory)
        try:
            if args.headless:result=headless(review,args)
            else:interactive(review,args)
            inputs=review.input_hashes
        finally:review.close()
    if args.check_preservation:proof=preservation()
    result.update({'classification':'Synthetic mechanic probe using existing stills; no authored performance or completed played quest claimed.' if args.probe else 'Selected production shot with explicitly requested isolated review selection.',
                   'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   'shot':args.shot,'shot_start_seconds':args.shot_time,'pose':args.pose,'loop':args.loop,'action':PROBE if args.probe else args.action,
                   'release_at':args.release_at if args.release_at is not None else .3 if args.probe else None,
                   'simulation_seconds':args.seconds,'primary_speed':args.speed,
                   'references':references,'external_inputs':inputs,'preservation':proof,
                   'persistence':'Actual isolated Gallery child; temporary parent save/settings; no production asset writes.',
                   'output_sha256':{p.name:digest(p) for p in sorted(args.out.iterdir()) if p.suffix in ('.png','.gif')}})
    (args.out/'capture.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Iselin cinematic preview complete:',args.out)


if __name__=='__main__':main()
