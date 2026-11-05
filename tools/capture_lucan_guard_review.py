"""Review Lucan's guarded hold through the existing rescue camera orbit.

Restore the prior Lucan directional manifest in an isolated baseline stage;
loading only the prior Python would otherwise inherit the corrected metadata.
No ordinary saves, production artwork or cinematic timing are changed.
"""
from __future__ import annotations

import argparse
import copy
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
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

import numpy as np
import pygame

from main import Game
from tools import capture_mira_prefire_review as helpers
from tools.capture_rhea_winter_cinematic import validate_frame

OUTPUT = ROOT/'docs/reviews/lucan_guard_review'
START, END, FPS = 7., 11.4, 60
SNAPSHOTS = (7.2, 8.5, 9., 9.5, 9.7, 10., 10.4, 10.8, 11.)
MANIFEST = 'assets/story/ice_reaper_continuity/actors/lucan/animation.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(output=OUTPUT, *, baseline_ref='HEAD', protected_hashes=None):
    output.mkdir(parents=True, exist_ok=True)
    Stage, commit, baseline_source_hash = helpers.committed_action_stage(baseline_ref)
    old_manifest_bytes = subprocess.check_output(['git', 'show', f'{commit}:{MANIFEST}'], cwd=ROOT)
    old_manifest = json.loads(old_manifest_bytes)
    protected = json.loads(Path(protected_hashes).read_text()) if protected_hashes else {}
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected asset changed before capture')
    source_names = ('ice_reaper_action.py', 'ice_reaper_opening.py', 'opening_cinematic.py',
                    'ice_reaper_audio.py', 'tools/capture_lucan_guard_review.py',
                    'tools/capture_mira_prefire_review.py')
    sources = {name: digest(ROOT/name) for name in source_names}
    manifest_hash = digest(ROOT/MANIFEST)
    reference_path = ROOT/'docs/reviews/rhea_winter_cinematic/verification.json'
    reference = json.loads(reference_path.read_text())
    timeline, snapshots, sprite_snapshots = [], [], []
    sample_frames = {round((time-START)*FPS): time for time in SNAPSHOTS}
    frames = round((END-START)*FPS)

    with tempfile.TemporaryDirectory(prefix='lucan-guard-review-') as folder:
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
            for key, entry in old_manifest['animations'].items():
                baseline.actors['lucan']['manifest']['animations'][key] = copy.deepcopy(entry)
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
                    position = stage.actor_positions(story_time)['lucan']
                    action, local, duration = stage._action('lucan', story_time)
                    key = stage.sequence_key('lucan', action, local, duration, camera, position, story_time)
                    image, _ = stage._sequence('lucan', action, local, duration, camera, position, time=story_time)
                    timeline.append(dict(frame=frame, time=time, shot=scene.shot,
                        dialogue=scene.dialogue['text'] if scene.dialogue else None,
                        lucan_action=action, lucan_view=key,
                        lucan_azimuth=stage.view_angles('lucan', camera, position, story_time)[0],
                        camera_position=list(camera.position), camera_target=list(camera.target), focal=camera.focal))
                    if frame in sample_frames:
                        label = f'{sample_frames[frame]:05.2f}'
                        name = f'{label}_scene.png'
                        pygame.image.save(child.ui_surface, str(output/name))
                        snapshots.append(name)
                        name = f'{label}_sprite.png'
                        pygame.image.save(image, str(output/name))
                        sprite_snapshots.append(name)
                encoder.stdin.close()
                if encoder.wait():
                    raise RuntimeError('Review encoding failed')
            music_gain = pygame.mixer.music.get_volume()
            effects_gain = child.audio.effects_volume
            # Reuse the exact audio reconstruction helper with this excerpt's
            # explicit boundaries. This is an isolated offline process.
            prior_start, prior_end = helpers.START, helpers.END
            try:
                helpers.START, helpers.END = START, END
                cues = helpers.audio_segment(video, output/'preview.mp4', music_gain, effects_gain)
            finally:
                helpers.START, helpers.END = prior_start, prior_end

            current_canvas = pygame.Surface((480, 320))
            old_canvas = pygame.Surface((480, 320))
            preserved = {}
            for frame in range(300, round(9.7*FPS)):
                time = frame/FPS
                stage.draw(current_canvas, time, False)
                baseline.draw(old_canvas, time, False)
                current = pygame.image.tobytes(current_canvas, 'RGB')
                if current != pygame.image.tobytes(old_canvas, 'RGB'):
                    raise AssertionError(f'Dash/interception changed before held pose: {time:.6f}s')
                preserved[frame] = hashlib.sha256(current).hexdigest()
            for record in reference['timeline']:
                scene.elapsed = record['scene_time']
                validate_frame(scene, record)
            if (folder/'journey.json').exists() or (folder/'settings.json').read_bytes() != settings:
                raise AssertionError('Review changed save/settings files')
        finally:
            if parent.gallery_session is not None:
                parent.gallery_session.close(resume_music=False)
            parent.music.stop()
            pygame.quit()

    if sources != {name: digest(ROOT/name) for name in sources}:
        raise AssertionError('Runtime changed during capture')
    if manifest_hash != digest(ROOT/MANIFEST):
        raise AssertionError('Lucan directional metadata changed during capture')
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected asset changed during capture')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                       '-show_format', '-of', 'json', str(output/'preview.mp4')]))
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    if int(stream['nb_frames']) != frames or abs(float(stream['duration'])-(END-START)) > .001:
        raise AssertionError('Review excerpt has the wrong duration/frame count')
    audio = np.frombuffer(subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output/'preview.mp4'),
                            '-vn', '-ar', '48000', '-ac', '2', '-f', 'f32le', '-']), dtype='<f4')
    if not np.isfinite(audio).all() or np.any(np.abs(audio) >= 1):
        raise AssertionError('Review audio is invalid or clipped')
    helpers.contact(output, snapshots, 'scene_contact.png')
    helpers.contact(output, sprite_snapshots, 'sprite_contact.png', sprites=True)
    report = dict(version=1, segment=[START, END], fps=FPS, frames=frames,
        baseline_ref=commit, baseline_action_source_sha256=baseline_source_hash,
        baseline_lucan_manifest_sha256=hashlib.sha256(old_manifest_bytes).hexdigest(),
        current_lucan_manifest_sha256=manifest_hash,
        runtime_sources=sources, protected_asset_hashes=protected,
        save_and_settings_unchanged=True,
        full_scene_camera_and_blocking=dict(frames=1920, unchanged=True,
            reference=str(reference_path.relative_to(ROOT)), reference_sha256=digest(reference_path)),
        early_rescue_preservation=dict(segment=[5., 9.7], frames=len(preserved),
            all_native_frames_pixel_identical=True, old_lucan_metadata_restored=True,
            frame_hashes={str(frame): value for frame, value in preserved.items()}),
        music=dict(file=str(helpers.MUSIC.relative_to(ROOT)), sha256=digest(helpers.MUSIC),
                   rendered_gain=music_gain, segment=[START, END]),
        effects_settings_gain=effects_gain, effects=cues,
        audio_capture_method='Reconstructed runtime score/SFX; SDL dummy has no loopback',
        audio_peak=float(np.max(np.abs(audio))), audio_clipped_samples=0,
        snapshots=snapshots, sprite_snapshots=sprite_snapshots, timeline=timeline,
        preview_sha256=digest(output/'preview.mp4'))
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(segment=report['segment'], frames=frames, fps=FPS,
                         early_native_frames_preserved=len(preserved), camera_frames_checked=1920,
                         video_bytes=(output/'preview.mp4').stat().st_size)))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--baseline-ref', default='HEAD', help='Commit before the held-guard metadata correction')
    parser.add_argument('--protected-hashes', type=Path)
    args = parser.parse_args()
    capture(args.output.resolve(), baseline_ref=args.baseline_ref, protected_hashes=args.protected_hashes)
