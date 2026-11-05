"""Review Mira's preparation without changing the approved firing sequence.

Capture 9.5–14.2 seconds through the production Gallery. Reconstruct the same
score/SFX segment and compare every later native scene frame with the previous
committed action renderer loaded in an isolated module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

from PIL import Image, ImageDraw
import numpy as np
import pygame

from main import Game
from ice_reaper_audio import CUES
from tools.capture_ice_reaper_opening import MUSIC

OUTPUT = ROOT/'docs/reviews/mira_prefire_review'
START, END, FPS = 9.5, 14.2, 60
SNAPSHOTS = (9.5, 11., 12.25, 12.5, 12.9, 13.1, 13.3, 13.5, 13.8)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def committed_action_stage(ref):
    commit = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(['git', 'show', f'{commit}:ice_reaper_action.py'], cwd=ROOT)
    name = '_mira_prefire_committed_action'
    module = ModuleType(name)
    module.__file__ = str(ROOT/'ice_reaper_action.py')
    sys.modules[name] = module
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module.IceReaperActionStage, commit, hashlib.sha256(source).hexdigest()


def audio_segment(video, movie, music_gain, effects_gain):
    command = ['ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(MUSIC)]
    filters = [f'[1:a]atrim=start={START}:end={END},asetpts=PTS-STARTPTS,volume={music_gain}[music]']
    labels = ['[music]']
    cues = []
    for cue in CUES:
        if cue['time'] >= END:
            continue
        file = ROOT/cue['file']
        duration = float(subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(file)], text=True))
        if cue['time']+duration <= START:
            continue
        index = len(cues)+2
        command += ['-i', str(file)]
        trim = max(0., START-cue['time'])
        delay = round(max(0., cue['time']-START)*1000)
        gain = cue['gain']*effects_gain
        label = f'effect{index}'
        filters.append(f'[{index}:a]atrim=start={trim},asetpts=PTS-STARTPTS,'
                       f'volume={gain},adelay={delay}:all=1[{label}]')
        labels.append(f'[{label}]')
        cues.append(dict(cue, sha256=digest(file), source_trim=trim,
                         local_delay_ms=delay, rendered_gain=gain))
    filters.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:normalize=0,'
                   f'atrim=duration={END-START}[mix]')
    command += ['-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[mix]',
                '-t', str(END-START), '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', str(movie)]
    subprocess.run(command, check=True)
    return cues


def contact(output, names, destination, *, sprites=False):
    width, height = (384, 418) if sprites else (480, 344)
    sheet = Image.new('RGB', (width*3, math.ceil(len(names)/3)*height), '#14232c')
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(names):
        x, y = index%3*width, index//3*height
        draw.text((x+9, y+5), name, fill='#eee7d6')
        image = Image.open(output/name).convert('RGBA')
        image = image.resize((384, 384) if sprites else (480, 320), Image.Resampling.NEAREST)
        sheet.paste(image, (x, y+24), image)
    sheet.save(output/destination, optimize=True)


def capture(output=OUTPUT, *, baseline_ref='HEAD', protected_hashes=None):
    output.mkdir(parents=True, exist_ok=True)
    Stage, commit, baseline_source_hash = committed_action_stage(baseline_ref)
    protected = json.loads(Path(protected_hashes).read_text()) if protected_hashes else {}
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected asset changed before capture')
    sources = {name: digest(ROOT/name) for name in
               ('ice_reaper_action.py', 'ice_reaper_opening.py', 'opening_cinematic.py',
                'ice_reaper_audio.py', 'tools/capture_mira_prefire_review.py')}
    assets = {str(path.relative_to(ROOT)): digest(path)
              for folder in ('assets/story/mira_prefire_aim',
                             'assets/source/cinematics/mira_prefire_aim')
              for path in sorted((ROOT/folder).rglob('*')) if path.is_file()}
    timeline, snapshots, sprite_snapshots = [], [], []
    sample_frames = {round((time-START)*FPS): time for time in SNAPSHOTS}
    frames = round((END-START)*FPS)
    with tempfile.TemporaryDirectory(prefix='mira-prefire-review-') as folder:
        folder = Path(folder)
        parent = Game(window_size=(960, 800), fullscreen=False, start_on_title=True,
                      save_path=folder/'journey.json', settings_path=folder/'settings.json')
        try:
            parent.audio.set_music(1.)
            parent.audio.set_effects(1.)
            parent.audio._save()
            settings = (folder/'settings.json').read_bytes()
            assert parent.open_gallery() and parent.launch_gallery_scene('ice_reaper_opening')
            child = parent.gallery_session.game
            scene = child.opening_cinematic
            scene.elapsed = START
            stage = scene.action_stage
            baseline = Stage(stage.asset_root, strict=True)
            frozen = (child._progress_signature(), child.elapsed_ms, tuple(child.player.position))
            video = folder/'video.mp4'
            command = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                       '-s', '960x640', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
                       '-preset', 'medium', '-crf', '20', '-threads', '2', '-pix_fmt', 'yuv420p', str(video)]
            with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
                for frame in range(frames):
                    time = START+frame/FPS
                    scene.elapsed = time
                    parent.draw()
                    encoder.stdin.write(pygame.image.tobytes(child.ui_surface, 'RGB'))
                    if frozen != (child._progress_signature(), child.elapsed_ms, tuple(child.player.position)):
                        raise AssertionError('Review changed the ordinary world')
                    story_time = stage.story_time(time)
                    camera = stage.camera(story_time)
                    position = stage.actor_positions(story_time)['mira']
                    action, local, duration = stage._action('mira', story_time)
                    key = stage.sequence_key('mira', action, local, duration, camera, position, story_time)
                    image, _ = stage._sequence('mira', action, local, duration, camera, position, time=story_time)
                    timeline.append(dict(frame=frame, time=time,
                        shot=scene.shot, dialogue=scene.dialogue['text'] if scene.dialogue else None,
                        mira_action=action, mira_view=key,
                        mira_azimuth=stage.view_angles('mira', camera, position, story_time)[0],
                        camera_position=list(camera.position), camera_target=list(camera.target), focal=camera.focal))
                    if frame in sample_frames:
                        label=f'{sample_frames[frame]:05.2f}'
                        filename=f'{label}_scene.png'
                        pygame.image.save(child.ui_surface, str(output/filename))
                        snapshots.append(filename)
                        filename=f'{label}_sprite.png'
                        pygame.image.save(image, str(output/filename))
                        sprite_snapshots.append(filename)
                encoder.stdin.close()
                if encoder.wait():
                    raise RuntimeError('Review video encoding failed')
            music_gain = pygame.mixer.music.get_volume()
            effects_gain = child.audio.effects_volume
            cues = audio_segment(video, output/'preview.mp4', music_gain, effects_gain)
            if (folder/'journey.json').exists() or (folder/'settings.json').read_bytes() != settings:
                raise AssertionError('Review changed save/settings files')

            # All visible native scene pixels from the first firing frame until
            # the end must match the previous renderer, including the scope,
            # projectiles, awakening, wardrobe and duel continuation.
            current_canvas = pygame.Surface((480, 320))
            old_canvas = pygame.Surface((480, 320))
            preserved = {}
            for frame in range(round(END*FPS), 32*FPS):
                time = frame/FPS
                stage.draw(current_canvas, time, False)
                baseline.draw(old_canvas, time, False)
                current = pygame.image.tobytes(current_canvas, 'RGB')
                if current != pygame.image.tobytes(old_canvas, 'RGB'):
                    raise AssertionError(f'Approved firing/later scene changed at {time:.6f}s')
                preserved[frame] = hashlib.sha256(current).hexdigest()
            for time in (14.2, 14.5, 14.95, 15.1, 17.3, 21., 24., 27., 31.9):
                stage.draw(current_canvas, time, True)
                baseline.draw(old_canvas, time, True)
                if pygame.image.tobytes(current_canvas, 'RGB') != pygame.image.tobytes(old_canvas, 'RGB'):
                    raise AssertionError(f'Reduced-motion firing/later scene changed at {time}s')
        finally:
            if parent.gallery_session is not None:
                parent.gallery_session.close(resume_music=False)
            parent.music.stop()
            pygame.quit()

    if sources != {name: digest(ROOT/name) for name in sources}:
        raise AssertionError('Runtime changed during capture')
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected asset changed during capture')
    if assets != {name: digest(ROOT/name) for name in assets}:
        raise AssertionError('Mira preparation art changed during capture')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                       '-show_format', '-of', 'json', str(output/'preview.mp4')]))
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    if int(stream['nb_frames']) != frames or abs(float(stream['duration'])-(END-START)) > .001:
        raise AssertionError('Review excerpt has the wrong frame count or duration')
    audio = np.frombuffer(subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output/'preview.mp4'),
                            '-vn', '-ar', '48000', '-ac', '2', '-f', 'f32le', '-']), dtype='<f4')
    if not np.isfinite(audio).all() or np.any(np.abs(audio) >= 1):
        raise AssertionError('Review audio is invalid or clipped')
    if 'Incoming! I got this one!' not in {item['dialogue'] for item in timeline}:
        raise AssertionError('Mira dialogue is missing')
    contact(output, snapshots, 'scene_contact.png')
    contact(output, sprite_snapshots, 'sprite_contact.png', sprites=True)
    report = dict(version=1, segment=[START, END], fps=FPS, frames=frames,
        baseline_ref=commit, baseline_action_source_sha256=baseline_source_hash,
        runtime_sources=sources, preparation_asset_hashes=assets, protected_asset_hashes=protected,
        save_and_settings_unchanged=True, cameras='Unmodified production Gallery camera',
        music=dict(file=str(MUSIC.relative_to(ROOT)), sha256=digest(MUSIC),
                   rendered_gain=music_gain, segment=[START, END]),
        effects_settings_gain=effects_gain,
        effects=cues, audio_capture_method='Reconstructed from the runtime score/SFX and cue gains; no SDL loopback',
        audio_peak=float(np.max(np.abs(audio))), audio_clipped_samples=0,
        postfire_preservation=dict(start=END, end=32., frames=len(preserved),
            all_native_frames_pixel_identical=True, reduced_motion_samples=9,
            frame_hashes={str(frame): value for frame, value in preserved.items()}),
        snapshots=snapshots, sprite_snapshots=sprite_snapshots, timeline=timeline,
        preview_sha256=digest(output/'preview.mp4'))
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(segment=report['segment'], frames=frames, fps=FPS,
                         postfire_preserved_frames=len(preserved),
                         video_bytes=(output/'preview.mp4').stat().st_size)))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--baseline-ref', default='HEAD', help='Commit before the prefire correction')
    parser.add_argument('--protected-hashes', type=Path)
    args = parser.parse_args()
    capture(args.output.resolve(), baseline_ref=args.baseline_ref, protected_hashes=args.protected_hashes)
