"""Capture Caelan's dialogue-to-crosswind correction through the real Gallery.

Compare all duel blocking, camera paths, action clocks and other actors' headings
with the committed pre-correction renderer. Caelan's heading/art may change.
Use temporary save/settings files, and reconstruct audio from production cues.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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

import pygame
from main import Game
from ice_reaper_duel import IceReaperDuel
from tools import capture_mira_prefire_review as helpers
from tools.capture_rhea_winter_cinematic import assert_close, encoded_audio_metrics

OUTPUT = ROOT/'docs/reviews/caelan_duel_correction'
START, END, FPS = 21., 25.65, 60
SNAPSHOTS = (21.1, 22.5, 23.6, 24.12, 24.22, 24.35, 24.6, 24.85, 25.05)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def committed_duel(ref):
    commit = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(['git', 'show', f'{commit}:ice_reaper_duel.py'], cwd=ROOT)
    name = '_caelan_review_committed_duel'
    module = ModuleType(name)
    module.__file__ = str(ROOT/'ice_reaper_duel.py')
    sys.modules[name] = module
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module.IceReaperDuel, commit, hashlib.sha256(source).hexdigest()


def verify_preservation(baseline):
    checked = 0
    for frame in range(round(21*FPS), round(32*FPS)):
        time = frame/FPS
        assert_close(IceReaperDuel.actor_positions(time), baseline.actor_positions(time), 'positions')
        assert_close(IceReaperDuel.state(time), baseline.state(time), 'action_clock')
        for reduced in (False, True):
            actual, expected = IceReaperDuel.camera(time, reduced), baseline.camera(time, reduced)
            for name in ('position', 'target', 'focal'):
                assert_close(getattr(actual, name), getattr(expected, name), 'camera.'+name)
        actual, expected = IceReaperDuel.headings(time), baseline.headings(time)
        for actor in expected:
            if actor != 'caelan':
                assert_close(list(actual[actor]), list(expected[actor]), f'headings.{actor}')
        for actor in ('caelan', 'lucan', 'mira', 'rhea', 'ice_reaper'):
            assert_close(IceReaperDuel._action(actor, time), baseline._action(actor, time), f'action.{actor}')
        checked += 1
    return dict(frames=checked, positions_unchanged=True, cameras_unchanged=True,
                reduced_motion_cameras_unchanged=True, action_clocks_unchanged=True,
                other_actor_headings_unchanged=True)


def render(parent, output, start, end, filename, *, snapshots=()):
    child = parent.gallery_session.game
    scene = child.opening_cinematic
    duel = scene.action_stage.duel
    frozen = (child._progress_signature(), child.elapsed_ms, tuple(child.player.position))
    frames = round((end-start)*FPS)
    snapshot_frames = {round((time-start)*FPS): time for time in snapshots}
    timeline, scene_names, sprite_names = [], [], []
    with tempfile.TemporaryDirectory(prefix='caelan-review-video-') as folder:
        video = Path(folder)/'video.mp4'
        command = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                   '-s', '960x640', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
                   '-preset', 'medium', '-crf', '21', '-maxrate', '2M', '-bufsize', '4M',
                   '-threads', '2', '-pix_fmt', 'yuv420p', str(video)]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            for frame in range(frames):
                time = start+frame/FPS
                scene.elapsed = time
                parent.draw()
                if child.ui_surface.get_size() != (960, 640):
                    raise AssertionError('Review must retain the exact 2x pixel scale')
                encoder.stdin.write(pygame.image.tobytes(child.ui_surface, 'RGB'))
                if frozen != (child._progress_signature(), child.elapsed_ms, tuple(child.player.position)):
                    raise AssertionError('Capture changed the ordinary world')
                record = dict(frame=frame, time=time, shot=scene.shot,
                              dialogue=scene.dialogue['text'] if scene.dialogue else None)
                if time >= 21:
                    camera = duel.camera(time)
                    position = duel.actor_positions(time)['caelan']
                    image, _, key = duel._image('caelan', camera, position, time)
                    record.update(caelan_view=key, caelan_azimuth=duel._azimuth('caelan', camera, position, time),
                                  caelan_heading=list(duel.headings(time)['caelan']),
                                  caelan_position=list(position), camera_position=list(camera.position),
                                  camera_target=list(camera.target), focal=camera.focal)
                timeline.append(record)
                if frame in snapshot_frames:
                    label = f'{snapshot_frames[frame]:05.2f}'
                    name = label+'_scene.png'
                    pygame.image.save(child.ui_surface, str(output/name))
                    scene_names.append(name)
                    name = label+'_sprite.png'
                    pygame.image.save(image, str(output/name))
                    sprite_names.append(name)
            encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError('Review encoding failed')
        old_start, old_end = helpers.START, helpers.END
        try:
            helpers.START, helpers.END = start, end
            cues = helpers.audio_segment(video, output/filename,
                pygame.mixer.music.get_volume(), child.audio.effects_volume)
        finally:
            helpers.START, helpers.END = old_start, old_end
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                       '-show_format', '-of', 'json', str(output/filename)]))
    stream = next(item for item in probe['streams'] if item['codec_type'] == 'video')
    if int(stream['nb_frames']) != frames or abs(float(stream['duration'])-(end-start)) > .001:
        raise AssertionError('Encoded preview duration or frame count is incorrect')
    return dict(segment=[start, end], fps=FPS, frames=frames, timeline=timeline,
                preview=filename, preview_sha256=digest(output/filename),
                audio=encoded_audio_metrics(output/filename), effects=cues,
                snapshots=scene_names, sprite_snapshots=sprite_names)


def capture(output=OUTPUT, *, baseline_ref='HEAD', full=False):
    output.mkdir(parents=True, exist_ok=True)
    baseline, commit, source_hash = committed_duel(baseline_ref)
    preservation = verify_preservation(baseline)
    source_paths = ('ice_reaper_duel.py', 'ice_reaper_action.py', 'ice_reaper_opening.py',
                    'ice_reaper_audio.py', 'tools/capture_caelan_duel_review.py')
    source_hashes = {name: digest(ROOT/name) for name in source_paths}
    with tempfile.TemporaryDirectory(prefix='caelan-duel-review-') as folder:
        folder = Path(folder)
        parent = Game(window_size=(960, 800), fullscreen=False, start_on_title=True,
                      save_path=folder/'journey.json', settings_path=folder/'settings.json')
        try:
            parent.audio.set_music(1.)
            parent.audio.set_effects(1.)
            parent.audio._save()
            settings = (folder/'settings.json').read_bytes()
            if not parent.open_gallery() or not parent.launch_gallery_scene('ice_reaper_opening'):
                raise RuntimeError('Ice Reaper Gallery preview failed to open')
            excerpt = render(parent, output, START, END, 'preview.mp4', snapshots=SNAPSHOTS)
            full_movie = render(parent, output, 0., 32., 'full_preview.mp4') if full else None
            if (folder/'journey.json').exists() or (folder/'settings.json').read_bytes() != settings:
                raise AssertionError('Capture changed save/settings files')
        finally:
            if parent.gallery_session is not None:
                parent.gallery_session.close(resume_music=False)
            parent.music.stop()
            pygame.quit()
    if source_hashes != {name: digest(ROOT/name) for name in source_paths}:
        raise AssertionError('Runtime changed during capture')
    helpers.contact(output, excerpt['snapshots'], 'scene_contact.png')
    helpers.contact(output, excerpt['sprite_snapshots'], 'sprite_contact.png', sprites=True)
    report = dict(version=1, baseline_ref=commit, baseline_duel_sha256=source_hash,
                  runtime_sources=source_hashes, preservation=preservation,
                  save_and_settings_unchanged=True,
                  audio_capture_method='Reconstructed from production music/SFX cues and gains; no SDL loopback',
                  excerpt=excerpt, full_movie=full_movie)
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(excerpt=excerpt['segment'], frames=excerpt['frames'],
                         preservation=preservation, full_preview=bool(full_movie))))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--baseline-ref', default='HEAD')
    parser.add_argument('--full', action='store_true', help='Also capture the complete 32-second scene')
    args = parser.parse_args()
    capture(args.output.resolve(), baseline_ref=args.baseline_ref, full=args.full)
