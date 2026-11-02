"""Record the real MQ02-report arrival, including its gate-to-bridge transition.

Earlier quest work is the same documented fixture used by the gameplay tests.
The unread report, all cinematic phases and the final receipt use production
input/update/draw. No cinematic time, actor station or phase is assigned. SDL
dummy has no audio loopback, so these sprite/staging previews are silent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image, ImageDraw

from main import Game
from quests import MILL_QUEST, REGENT_QUEST
from test_regent_arrival import seed_mill_report, acknowledge_report
from tools.capture_region_npcs import save_gif

FPS = 30
DEFAULT_OUTPUT = ROOT/'docs/reviews/regent_arrival_polish'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(game, value):
    events = [pygame.event.Event(pygame.KEYDOWN, key=value, repeat=False),
              pygame.event.Event(pygame.KEYUP, key=value)]
    assert game.handle_events(events)


def world_signature(game):
    return (game.world.data['id'], tuple(game.player.position), game.elapsed_ms,
            tuple((world.data['id'], actor.data['id'], tuple(actor.position))
                  for world in game.scenes.values() for actor in world.npcs))


def make_game(directory, *, title=False):
    game = Game(window_size=(960,640), fullscreen=False, start_on_title=title,
                save_path=directory/'journey.json', settings_path=directory/'settings.json')
    game.audio.set_music(0)
    game.audio.set_effects(0)
    pygame.event.clear()
    return game


def source_inputs():
    paths = [ROOT/name for name in (
        'regent_arrival.py', 'regent_aerial.py', 'main.py', 'speech_bubble.py', 'cutscene_gallery.py',
        'gallery_session.py', 'tools/build_regent_arrival_actors.py',
        'tools/build_regent_arrival_scenery.py', 'tools/capture_regent_arrival_polish.py',
        'tests/test_regent_arrival.py', 'tools/capture_region_npcs.py')]
    for folder in ('assets/story/regent_arrival', 'assets/source/cinematics/regent_arrival',
                   'assets/story/regent_aerial', 'assets/source/cinematics/regent_aerial'):
        paths.extend(path for path in (ROOT/folder).rglob('*') if path.is_file())
    return {str(path.relative_to(ROOT)):digest(path) for path in sorted(set(paths))}


def pose_sheet(output):
    root = ROOT/'assets/story/regent_arrival/actors/aldric'
    manifest = json.loads((root/'animation.json').read_text())
    files = [frame['file'] for frame in manifest['loops']['walk_left']]
    sheet = Image.new('RGB', (len(files)*180, 230), '#26352e')
    draw = ImageDraw.Draw(sheet)
    for index, filename in enumerate(files):
        sprite = Image.open(root/filename).convert('RGBA')
        sprite = sprite.resize((160,192),Image.Resampling.NEAREST)
        sheet.paste(sprite,(index*180+10,12),sprite)
        draw.text((index*180+10,210),filename,fill='#f1e7c8')
    sheet.save(output/'aldric_walk_frames.png')


def staging_sheet(output, filenames):
    names = [name for name in filenames if name.startswith(('gate_admission_',
             'gate_departure_black_', 'crossroads_establishing_'))]
    columns = 3
    sheet = Image.new('RGB',(columns*480,((len(names)+columns-1)//columns)*344),'#26352e')
    draw = ImageDraw.Draw(sheet)
    for index,name in enumerate(names):
        x,y = index%columns*480,index//columns*344
        with Image.open(output/name) as image:
            sheet.paste(image.resize((480,320),Image.Resampling.NEAREST),(x,y))
        draw.text((x+8,y+324),name,fill='#f1e7c8')
    sheet.save(output/'gate_transition_contact_sheet.png')


def turn_sheet(output, frames):
    columns = 3
    sheet = Image.new('RGB',(columns*480,((len(frames)+columns-1)//columns)*344),'#26352e')
    draw = ImageDraw.Draw(sheet)
    for index,(seconds,image) in enumerate(frames):
        x,y = index%columns*480,index//columns*344
        sheet.paste(image,(x,y))
        draw.text((x+8,y+324),f'gate_admission {seconds:.3f}s',fill='#f1e7c8')
    sheet.save(output/'gate_turn_sequence.png')


def smoke_checks(directory, saved_pending, saved_completed):
    path = directory/'journey.json'
    path.write_bytes(saved_pending)
    game = make_game(directory,title=True)
    assert game.begin_journey(True) and game.regent_arrival.active
    scene = game.regent_arrival
    assert scene.shot == 'mill_close'
    before = (scene.elapsed,scene.phase_time,world_signature(game))
    key(game,pygame.K_ESCAPE)
    game.update(.5,(1,1),True)
    assert scene.paused and (scene.elapsed,scene.phase_time,world_signature(game)) == before
    key(game,pygame.K_ESCAPE)
    game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
    game.update(.5,(1,1),True)
    assert (scene.elapsed,scene.phase_time,world_signature(game)) == before
    game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
    game.update(.1,(0,0),False)
    assert scene.elapsed > before[0]
    game.draw()
    point = tuple(value*2 for value in scene.skip_rect.center)
    game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                        pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point)])
    assert not scene.active and scene.state == 'seen' and scene.finished_reason == 'skipped'
    assert game.quests.status(MILL_QUEST) == 'completed'
    assert game.quests.status(REGENT_QUEST) == 'available'
    game.music.stop();game.opening_audio.reset();game.regional_audio.reset()
    path.write_bytes(saved_completed)
    title = make_game(directory,title=True)
    original = path.read_bytes()
    assert title.open_gallery() and title.launch_gallery_scene('regent_arrival')
    session = title.gallery_session
    assert session is not None and session.game.regent_arrival.active
    observed = []
    for _ in range(8000):
        session = title.gallery_session
        if session is None:break
        child = session.game
        scene = child.regent_arrival
        if scene.active:
            if not observed or observed[-1] != scene.shot:observed.append(scene.shot)
            if scene.dialogue is not None:key(title,pygame.K_SPACE)
        title.update(.1,(0,0),False)
    assert title.gallery_session is None and title.on_gallery
    assert 'gate_departure_black' in observed and 'crossroads_establishing' in observed
    assert path.read_bytes() == original
    title.music.stop();title.opening_audio.reset();title.regional_audio.reset()
    return {'pending_reload_starts_from_beginning':True, 'pause_freezes_scene_and_world':True,
            'focus_freezes_scene_and_world':True, 'skip_preserves_quest_handoff':True,
            'gallery_plays_new_phases':True, 'gallery_preserves_save_bytes':True}


def capture(output):
    output.mkdir(parents=True,exist_ok=True)
    readme = output/'README.md'
    verification = ''
    if readme.exists() and '\n## Verification\n' in readme.read_text():
        verification = '\n## Verification\n'+readme.read_text().split('\n## Verification\n',1)[1]
    started = datetime.now(timezone.utc).isoformat()
    inputs = source_inputs()
    with tempfile.TemporaryDirectory(prefix='arrival-polish-capture-') as temporary:
        directory = Path(temporary)
        game = make_game(directory)
        seed_mill_report(game)
        acknowledge_report(game)
        pending = (directory/'journey.json').read_bytes()
        game.update(1/FPS,(0,0),False)
        scene = game.regent_arrival
        assert scene.active
        frozen = world_signature(game)
        video = subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo',
            '-pixel_format','rgb24','-video_size','960x640','-framerate',str(FPS),
            '-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','22',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(output/'arrival_polish.mp4')],
            stdin=subprocess.PIPE)
        gate_video = None
        gate_gif = []
        gate_frames = 0
        turn_frames = []
        phases = []
        samples = []
        pages = []
        saved_images = []
        last_page = None
        due = 0
        frames = 0
        freezes = 0
        shot_counts = {}
        try:
            for tick in range(18000):
                if not scene.active:break
                game.draw()
                shot = scene.shot
                if not phases or phases[-1]['shot'] != shot:
                    phases.append({'shot':shot,'scene':scene.phase['scene'],
                                   'video_second':round(frames/FPS,3)})
                if tick%15 == 0:
                    actors = []
                    for actor in scene.phase['actors']:
                        pose = scene.actor_pose(actor) if hasattr(scene,'actor_pose') else actor['pose']
                        actors.append({'id':actor['id'],'pose':pose,
                            'foot':list(scene.actor_position(actor)),
                            'scale':scene._actor_scale(actor)})
                    samples.append({'shot':shot,'phase_second':round(scene.phase_time,3),
                        'video_second':round(frames/FPS,3),'fade_alpha':scene.fade_alpha,
                        'camera':list(scene.camera_position),'actors':actors})
                shot_counts[shot] = shot_counts.get(shot,0)+1
                wanted = {'gate_approach':(2.,),
                    'gate_admission':tuple(round(scene.phase['min_seconds']*fraction,2)
                                            for fraction in (.05,.25,.5,.75,.94)),
                    'gate_departure_black':(.1,), 'crossroads_establishing':(.1,1.5,2.5),
                    'locals':(1.,), 'town_approach':(2.,)}
                for target in wanted.get(shot,()):
                    name = shot+'_'+str(target).replace('.','_')+'.png'
                    if scene.phase_time>=target and name not in saved_images:
                        pygame.image.save(game.window,str(output/name));saved_images.append(name)
                identity = (scene.phase_index,scene.dialogue_index,scene.page_index)
                if scene.dialogue is not None and identity != last_page:
                    last_page = identity
                    words = len(' '.join(scene.caption_lines).split())
                    due = frames/FPS+max(1.7,words*.20)
                    pages.append({'shot':shot,'speaker':scene.dialogue['speaker'],
                                  'page':scene.page_index,'video_second':round(frames/FPS,3)})
                pixels = pygame.image.tobytes(game.window,'RGB')
                if (shot == 'gate_admission' and 2.8 <= scene.phase_time <= 5.6
                        and shot_counts[shot]%6 == 1):
                    turn_frames.append((scene.phase_time,Image.frombytes('RGB',(960,640),pixels)
                                        .resize((480,320),Image.Resampling.NEAREST)))
                video.stdin.write(pixels)
                in_gate_transition = (shot in ('gate_admission','gate_departure_black','crossroads_establishing')
                                      or shot == 'locals' and scene.phase_time < 1.5)
                if in_gate_transition:
                    if gate_video is None:
                        gate_video = subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo',
                            '-pixel_format','rgb24','-video_size','960x640','-framerate',str(FPS),
                            '-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','20',
                            '-pix_fmt','yuv420p','-movflags','+faststart',str(output/'gate_to_bridge.mp4')],
                            stdin=subprocess.PIPE)
                    gate_video.stdin.write(pixels)
                    if gate_frames%3 == 0:
                        gate_gif.append(Image.frombytes('RGB',(960,640),pixels).resize((480,320),Image.Resampling.NEAREST))
                    gate_frames += 1
                if scene.dialogue is not None and frames/FPS>=due:key(game,pygame.K_SPACE)
                before = world_signature(game)
                game.update(1/FPS,(0,0),False)
                if scene.active:
                    assert world_signature(game) == before == frozen
                    freezes += 1
                frames += 1
            else:raise AssertionError('Scene failed to finish through ordinary input')
        finally:
            video.stdin.close();assert video.wait()==0
            if gate_video is not None:gate_video.stdin.close();assert gate_video.wait()==0
        assert scene.state == 'seen' and scene.finished_reason == 'finished'
        assert game.quests.status(MILL_QUEST) == 'completed'
        assert game.quests.status(REGENT_QUEST) == 'available'
        assert game.regent_quest.stage == 'idle'
        assert (directory/'journey.json').exists()
        completed = (directory/'journey.json').read_bytes()
        gif = save_gif(output/'gate_to_bridge.gif',gate_gif)
        pose_sheet(output)
        staging_sheet(output,saved_images)
        turn_sheet(output,turn_frames)
        game.music.stop();game.opening_audio.reset();game.regional_audio.reset()
        smoke = smoke_checks(directory,pending,completed)
        assert inputs == source_inputs(), 'Render inputs changed during capture; recapture after freeze'
        report = {'actual_renderer':True,'started_at_utc':started,
            'finished_at_utc':datetime.now(timezone.utc).isoformat(),
            'fixture':{'earlier_quest_work':'test_regent_arrival.seed_mill_report; unread MQ02 report',
                       'report_acknowledged_by':'production dialogue input',
                       'cinematic_clocks_or_phases_assigned':False,'actors_relocated_after_fixture':False},
            'audio':'Silent SDL-dummy visual preview; no reconstructed or synthetic soundtrack.',
            'frames':frames,'fps':FPS,'gate_to_bridge_frames':gate_frames,
            'world_freeze_checks':freezes,
            'ordinary_completion':True,'MQ03_available_not_accepted':True,
            'phases':phases,'dialogue_pages':pages,'sampled_actor_trace':samples,
            'gif_validation':gif,'smoke_checks':smoke,'render_input_sha256':inputs,
            'captures':{path.name:digest(path) for path in sorted(output.iterdir())
                        if path.is_file() and path.suffix in ('.png','.gif','.mp4')}}
        (output/'capture_report.json').write_text(json.dumps(report,indent=2)+'\n')
        (output/'README.md').write_text('''# Aldric arrival: movement and transition polish

[Gate passage and bridge transition](gate_to_bridge.mp4) · [Animated preview](gate_to_bridge.gif) · [Full arrival](arrival_polish.mp4)

These are silent, uninterrupted production Game recordings. The fixture completes earlier quest work only; the unread MQ02 report, arrival, dialogue and final MQ03 handoff use normal input/update/draw. No cinematic clock, phase or actor station is assigned during playback.

![Corrected Aldric walk frames](aldric_walk_frames.png)

![Gate passage, fade and bridge establishing frames](gate_transition_contact_sheet.png)

[Gate turn at five frames per second](gate_turn_sequence.png)

The gate-to-bridge recording includes the whole gate passage, departure fade, black hold, bridge establishing shot and start of the local conversation. The full video also includes Serene and the final town arrival. Sound is intentionally absent because SDL dummy has no hardware audio loopback.

The [capture report](capture_report.json) includes compact phase/actor samples, current render fingerprints, artifact hashes, GIF pixel/timing validation and pause, focus, reload, skip, world-freeze and isolated Gallery smoke checks.

To review in-game without repeating MQ02: **Title → Gallery → Aldric’s Relief Caravan**.

Reproduce with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_regent_arrival_polish.py`.
'''+verification)
        print(json.dumps({'frames':frames,'phases':[p['shot'] for p in phases],
                          'world_freeze_checks':freezes,'gif_validation':gif,
                          'smoke_checks':smoke,'render_inputs':len(inputs)},indent=2))
    pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    capture(args.output.resolve())


if __name__ == '__main__':main()
