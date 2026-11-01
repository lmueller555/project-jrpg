"""Record the bird-led arrival through production Game input/update/draw.

Only the earlier mill work is a fixture. The unread report, cinematic clocks,
camera, bird and convoy proceed through their normal controllers. SDL dummy
provides no audio loopback, so the review video is explicitly silent.
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

from quests import MILL_QUEST, REGENT_QUEST
from test_regent_arrival import acknowledge_report, seed_mill_report
from tools.capture_regent_arrival_polish import key, make_game
from tools.capture_region_npcs import save_gif

FPS = 30
AERIAL_PHASES = ('aerial_region', 'aerial_bank', 'aerial_gate', 'aerial_descent')
DEFAULT_OUTPUT = ROOT/'docs/reviews/regent_aerial'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_inputs():
    names = ('regent_arrival.py', 'regent_aerial.py', 'main.py', 'speech_bubble.py',
             'cutscene_gallery.py', 'gallery_session.py', 'purposeful_wildlife.py',
             'overworld_world.py', 'assets/maps/overworld/elden_vale/region.json',
             'tools/build_regent_aerial_landscape.py', 'tools/build_regent_aerial_actors.py',
             'tools/capture_regent_aerial.py', 'tools/capture_regent_arrival_polish.py',
             'tools/capture_region_npcs.py', 'tests/test_regent_arrival.py')
    paths = [ROOT/name for name in names if (ROOT/name).is_file()]
    for folder in ('assets/story/regent_arrival', 'assets/story/regent_aerial',
                   'assets/source/cinematics/regent_aerial'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
    return {str(path.relative_to(ROOT)):digest(path) for path in sorted(set(paths))}


def world_signature(game):
    cached = game._overworld_world
    return {'world':game.world.data['id'], 'player':list(game.player.position),
            'elapsed_ms':game.elapsed_ms,
            'residents':[(world.data['id'], actor.data['id'], list(actor.position))
                         for world in game.scenes.values() for actor in world.npcs],
            'cached_residents':[(actor.data['id'],list(actor.position),getattr(actor,'clock',None))
                                for actor in cached.npcs] if cached is not None else None,
            'cached_wildlife':cached.wildlife.to_dict() if cached is not None else None}


def json_value(value):
    if isinstance(value, pygame.Vector2):return list(value)
    if isinstance(value, dict):return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):return [json_value(v) for v in value]
    if hasattr(value, 'tolist'):return value.tolist()
    return value


def aerial_sample(scene):
    """Read diagnostics without advancing or assigning any visual clock."""
    snapshot = getattr(scene, 'aerial_snapshot', None)
    if callable(snapshot):return json_value(snapshot())
    if snapshot is not None:return json_value(snapshot)
    return None


def image_frame(game):
    return Image.frombytes('RGB',game.window.get_size(),
        pygame.image.tobytes(game.window,'RGB')).resize((480,320),Image.Resampling.NEAREST)


def contact_sheet(path, frames, columns=3):
    sheet = Image.new('RGB',(columns*480,((len(frames)+columns-1)//columns)*342),'#25362e')
    draw = ImageDraw.Draw(sheet)
    for index,(label,image) in enumerate(frames):
        x,y = index%columns*480,index//columns*342
        sheet.paste(image,(x,y));draw.text((x+7,y+323),label,fill='#eee5ce')
    if path.suffix == '.jpg':sheet.save(path,quality=85,subsampling=2,optimize=True)
    else:sheet.save(path,optimize=True)


def encoder(path):
    return subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo',
        '-pixel_format','rgb24','-video_size','480x320','-framerate',str(FPS),
        '-i','-','-an','-c:v','libx264','-preset','medium','-crf','26',
        '-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)


def close_encoder(process):
    if process is not None:
        process.stdin.close()
        assert process.wait() == 0


def advance_until(game, predicate, limit=12000):
    for _ in range(limit):
        if predicate():return
        scene = game.regent_arrival
        if scene.active and scene.dialogue is not None:key(game,pygame.K_SPACE)
        game.update(1/FPS,(0,0),False)
    raise AssertionError(('Timed out',game.regent_arrival.shot))


def smoke_checks(directory, pending, completed, output):
    path = directory/'journey.json'
    path.write_bytes(pending)
    game = make_game(directory,title=True)
    assert game.begin_journey(True) and game.regent_arrival.active
    scene = game.regent_arrival
    assert scene.shot == 'mill_close'
    advance_until(game,lambda:scene.shot == 'aerial_region' and scene.phase_time > 1)
    before = (scene.elapsed,scene.phase_time,aerial_sample(scene),world_signature(game))
    key(game,pygame.K_ESCAPE)
    game.update(.75,(1,1),True)
    assert scene.paused and before == (scene.elapsed,scene.phase_time,aerial_sample(scene),world_signature(game))
    key(game,pygame.K_ESCAPE)
    game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
    game.update(.75,(1,1),True)
    assert before == (scene.elapsed,scene.phase_time,aerial_sample(scene),world_signature(game))
    game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
    game.draw()
    point = tuple(value*2 for value in scene.skip_rect.center)
    game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                        pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point)])
    assert not scene.active and scene.state == 'seen' and scene.finished_reason == 'skipped'
    assert game.quests.status(MILL_QUEST) == 'completed'
    assert game.quests.status(REGENT_QUEST) == 'available'
    game.music.stop();game.opening_audio.reset();game.regional_audio.reset()

    path.write_bytes(completed)
    title = make_game(directory,title=True)
    original = path.read_bytes()
    assert title.open_gallery() and title.launch_gallery_scene('regent_arrival')
    observed = []
    for _ in range(12000):
        session = title.gallery_session
        if session is None:break
        scene = session.game.regent_arrival
        if scene.active:
            if not observed or observed[-1] != scene.shot:observed.append(scene.shot)
            if scene.dialogue is not None:key(title,pygame.K_SPACE)
        title.update(.1,(0,0),False)
    assert title.gallery_session is None and title.on_gallery
    assert all(shot in observed for shot in AERIAL_PHASES)
    assert path.read_bytes() == original
    title.music.stop();title.opening_audio.reset();title.regional_audio.reset()
    path.write_bytes(pending)
    reduced = make_game(directory,title=True)
    reduced.audio.reduced_motion = True
    assert reduced.begin_journey(True)
    scene = reduced.regent_arrival
    advance_until(reduced,lambda:scene.shot == 'aerial_region' and scene.phase_time > 1)
    snapshot = aerial_sample(scene)
    assert snapshot is not None
    camera = snapshot['camera']
    for _ in range(FPS):
        reduced.update(1/FPS,(0,0),False)
        assert aerial_sample(scene)['camera'] == camera,'Reduced Motion camera moved'
    reduced.draw();image_frame(reduced).save(output/'reduced_motion.png',optimize=True)
    scene.finish('skipped')
    reduced.music.stop();reduced.opening_audio.reset();reduced.regional_audio.reset()
    return {'pending_reload_restarts_before_aerial':True,'pause_freezes_camera_bird_and_world':True,
            'focus_freezes_camera_bird_and_world':True,'skip_preserves_quest_handoff':True,
            'gallery_plays_aerial_and_finishes':True,'gallery_preserves_save_bytes':True,
            'reduced_motion_camera_holds':True}


def capture(output, *, prototype=False):
    output.mkdir(parents=True,exist_ok=True)
    readme = output/'README.md'
    verification = ''
    if readme.exists() and '\n## Verification\n' in readme.read_text():
        verification = '\n## Verification\n'+readme.read_text().split('\n## Verification\n',1)[1]
    started = datetime.now(timezone.utc).isoformat()
    inputs = source_inputs()
    with tempfile.TemporaryDirectory(prefix='regent-aerial-capture-') as temporary:
        directory = Path(temporary)
        game = make_game(directory)
        game.overworld_world  # Materialize cached animals before the real report.
        seed_mill_report(game);acknowledge_report(game)
        pending = (directory/'journey.json').read_bytes()
        game.update(1/FPS,(0,0),False)
        scene = game.regent_arrival
        assert scene.active and all(shot in [p['id'] for p in scene.data['phases']] for shot in AERIAL_PHASES)
        frozen = world_signature(game)
        video = encoder(output/'aerial_intro.mp4')
        video_frames = 0
        gif_frames = []
        keyframes = []
        handoff = []
        view_change = []
        phases = []
        samples = []
        canopy_handoffs = []
        pages = []
        saved = []
        sampled_images = set()
        frames = freezes = 0
        last_page = None
        due = 0
        previous_ground_handoff = False
        try:
            for _ in range(18000):
                if not scene.active:break
                game.draw()
                shot = scene.shot
                if not phases or phases[-1]['shot'] != shot:
                    phases.append({'shot':shot,'scene':scene.phase['scene'],'video_second':round(frames/FPS,3)})
                snapshot = aerial_sample(scene) if shot in AERIAL_PHASES else None
                if frames%6 == 0 and shot in AERIAL_PHASES:
                    samples.append({'shot':shot,'phase_second':round(scene.phase_time,4),
                        'video_second':round(frames/FPS,4),'aerial':snapshot})
                if snapshot is not None:
                    ground_handoff = bool(snapshot.get('ground_handoff',False))
                    if ground_handoff and not previous_ground_handoff:
                        canopy = snapshot['canopy']
                        assert canopy['full_occlusion'] and canopy['coverage'] >= .9999,'Background switch was visible'
                        canopy_handoffs.append({'video_second':round(frames/FPS,4),
                            'aerial_seconds':snapshot['seconds'],'canopy':canopy})
                        name = 'canopy_handoff.png'
                        image_frame(game).save(output/name,optimize=True);saved.append(name)
                        keyframes.append(('Opaque foreground canopy handoff',image_frame(game)))
                    previous_ground_handoff = ground_handoff
                targets = ((.08,.5,.92) if shot in AERIAL_PHASES else (.2,) if shot == 'gate_approach' else ())
                for fraction in targets:
                    target = scene.phase['min_seconds']*fraction if shot in AERIAL_PHASES else fraction
                    name = shot+'_'+str(fraction).replace('.','_')+'.png'
                    if scene.phase_time >= target and name not in sampled_images:
                        native = image_frame(game)
                        if fraction == .5 or shot == 'gate_approach':
                            native.save(output/name,optimize=True);saved.append(name)
                        sampled_images.add(name)
                        keyframes.append((f'{shot} {scene.phase_time:.2f}s',native))
                if (shot == 'aerial_descent' and (.8 <= scene.phase_time <= 2.4 or
                                                scene.phase_time >= scene.phase['min_seconds']-.6)
                        or shot == 'gate_approach' and scene.phase_time < .5):
                    interval = 2 if shot == 'aerial_descent' and scene.phase_time < 2.4 else 6
                    if frames%interval == 0:handoff.append((f'{shot} {scene.phase_time:.3f}s',image_frame(game)))
                if shot == 'aerial_descent' and 2.5 <= scene.phase_time <= 5.5 and frames%6 == 0:
                    view_change.append((f'ground push-in {scene.phase_time+22:.3f}s',image_frame(game)))
                identity = (scene.phase_index,scene.dialogue_index,scene.page_index)
                if scene.dialogue is not None and identity != last_page:
                    last_page = identity
                    words = len(' '.join(scene.caption_lines).split())
                    due = frames/FPS+max(1.7,words*.20)
                    pages.append({'shot':shot,'speaker':scene.dialogue['speaker'],'page':scene.page_index})
                recording = shot in ('mill_close',*AERIAL_PHASES,'gate_approach') or shot == 'gate_greeting' and scene.phase_time < 2.2
                if recording:
                    native = image_frame(game)
                    video.stdin.write(native.tobytes())
                    if video_frames%6 == 0:gif_frames.append(native.resize((192,128),Image.Resampling.NEAREST))
                    video_frames += 1
                if scene.dialogue is not None and frames/FPS >= due:key(game,pygame.K_SPACE)
                before = world_signature(game)
                game.update(1/FPS,(0,0),False)
                if scene.active:
                    assert world_signature(game) == before == frozen,'World advanced behind arrival'
                    freezes += 1
                frames += 1
            else:raise AssertionError('Arrival did not finish through ordinary input')
        finally:close_encoder(video)
        assert scene.state == 'seen' and scene.finished_reason == 'finished'
        assert game.quests.status(MILL_QUEST) == 'completed' and game.quests.status(REGENT_QUEST) == 'available'
        assert game.regent_quest.stage == 'idle'
        assert all(shot in [p['shot'] for p in phases] for shot in AERIAL_PHASES)
        assert samples and all(sample['aerial'] is not None for sample in samples),'Missing aerial diagnostics'
        region_samples = [sample['aerial'] for sample in samples if sample['shot'] == 'aerial_region']
        assert region_samples[-1]['bird']['world_xy'][0] < region_samples[0]['bird']['world_xy'][0], 'Bird did not travel west'
        gate_samples = [sample['aerial'] for sample in samples if sample['shot'] == 'aerial_gate']
        assert gate_samples[-1]['bird']['world_xy'][1] > gate_samples[0]['bird']['world_xy'][1], 'Bird did not travel south'
        gate_cast_visible = [sample for sample in gate_samples if
            all(key in sample['projected_actors'] and
                0 <= sample['projected_actors'][key]['screen_xy'][0] < 480 and
                0 <= sample['projected_actors'][key]['screen_xy'][1] < 320
                for key in ('aldric','caravan','guard_west','guard_east'))]
        assert gate_cast_visible,'Gate overflight never showed the complete convoy and guard group'
        if not prototype:assert len(canopy_handoffs) == 1,'Missing the occluded background handoff'
        completed = (directory/'journey.json').read_bytes()
        gif = save_gif(output/'aerial_intro.gif',gif_frames,fps=5)
        contact_sheet(output/'aerial_contact_sheet.jpg',keyframes)
        contact_sheet(output/'descent_handoff.jpg',handoff)
        contact_sheet(output/'ground_push_in.jpg',view_change)
        game.music.stop();game.opening_audio.reset();game.regional_audio.reset()
        smoke = smoke_checks(directory,pending,completed,output) if not prototype else {}
        if not prototype:assert inputs == source_inputs(),'Render inputs changed; recapture after freeze'
        media = set(saved+['aerial_intro.mp4','aerial_intro.gif',
                           'aerial_contact_sheet.jpg','descent_handoff.jpg','ground_push_in.jpg'])
        if not prototype:media.add('reduced_motion.png')
        report = {'actual_renderer':True,'capture_stage':'prototype' if prototype else 'final',
            'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
            'fixture':{'earlier_quest_work':'test_regent_arrival.seed_mill_report; unread MQ02 report',
                       'cached_region_materialized_before_report':True,'report_acknowledged_by':'production dialogue input',
                       'cinematic_clocks_or_phases_assigned':False,'actors_relocated_after_fixture':False},
            'audio':'Silent SDL-dummy recording; no reconstructed soundtrack.',
            'frames':frames,'video_frames':video_frames,'video_size':[480,320],
            'fps':FPS,'world_freeze_checks':freezes,
            'ordinary_completion':True,'MQ03_available_not_accepted':True,
            'phases':phases,'dialogue_pages':pages,'sampled_aerial_trace':samples,
            'canopy_handoffs':canopy_handoffs,
            'gate_cast_visible_samples':len(gate_cast_visible),
            'gif_validation':gif,'smoke_checks':smoke,'render_input_sha256':inputs,
            'captures':{name:digest(output/name) for name in sorted(media)}}
        (output/'capture_report.json').write_text(json.dumps(report,indent=2)+'\n')
        readme.write_text('''# Bird-led introduction to Elden Vale

[Continuous aerial introduction](aerial_intro.mp4) · [Animated preview](aerial_intro.gif)

These silent production Game recordings begin with the acknowledged MQ02 report and follow the new aerial view continuously into the caravan scene. Earlier mill work is the documented fixture; cinematic phases, camera, bird and convoy are never assigned during playback.

![Aerial flight and descent](aerial_contact_sheet.jpg)

[Native descent and ground-scene handoff](descent_handoff.jpg)

[Ground camera settles on the caravan](ground_push_in.jpg)

The rest of the arrival completes through normal dialogue input. The [capture report](capture_report.json) records phase and aerial-camera samples, current source fingerprints, artifact hashes, GIF pixel/timing verification, world/wildlife freezing, and reload, pause, focus, skip and isolated Gallery save-preservation checks. The preview is silent because SDL dummy has no audio loopback.

The video and individual stills preserve the game's native 480×320 view; the GIF is a smaller navigation preview. Contact sheets use JPEG to keep the review lightweight.

Replay in-game from **Title → Gallery → Aldric’s Relief Caravan**.

Reproduce with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_regent_aerial.py`.
'''+verification)
        print(json.dumps({'capture_stage':report['capture_stage'],'frames':frames,'video_frames':video_frames,
                          'world_freeze_checks':freezes,'render_inputs':len(inputs),'gif_validation':gif},indent=2))
    pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--prototype',action='store_true')
    args = parser.parse_args()
    capture(args.output.resolve(),prototype=args.prototype)


if __name__ == '__main__':main()
