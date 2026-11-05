"""Capture the complete Ice Reaper cinematic with Rhea's winter outfit.

The new wardrobe deliberately changes the pixels. Validate all 1,920 frames'
camera paths and blocking against the previous production capture instead of
claiming that the previous character artwork remains pixel-identical.
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

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

import numpy as np
import pygame

import capture_ice_reaper_opening as production
from capture_ice_reaper_scene_awakening import decode_frames, filmstrip

REFERENCE = ROOT/'docs/reviews/ice_reaper_duel/verification.json'
OUTPUT = ROOT/'docs/reviews/rhea_winter_cinematic'
KEYFRAMES = {
    0: 'opening', 1: 'wide', 4.2: 'frozen_rhea', 8.5: 'rescue',
    10.8: 'mira_dialogue', 13.8: 'launcher', 15.8: 'closed_eyes',
    16.65: 'awakening', 17.35: 'breakout', 17.8: 'energy_release',
    19.8: 'shoulder_sweep', 21.5: 'rhea_dialogue', 23.6: 'caelan_dialogue',
    24.2: 'staff_sweep', 24.6: 'wind', 25.1: 'landing', 26.1: 'casting',
    26.8: 'orbit_start', 27.4: 'orbit_quarter', 28.: 'orbit_half',
    28.6: 'orbit_three_quarters', 29.15: 'orbit_end', 30.1: 'windup',
    31.1: 'charge', 31.9: 'fade',
}
POSTERS = {4.2: 'before_awakening.png', 17.35: 'breakout.png',
           21.5: 'rhea_dialogue.png', 24.2: 'staff_sweep.png',
           27.4: 'orbit.png'}
STRIPS = {
    'wardrobe_filmstrip': (1., 4.2, 8.5, 15.8, 16.65, 17.35),
    'energy_filmstrip': (17.35, 17.8, 19.8, 21.5, 24.2, 26.1, 27.4, 28., 28.6),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assert_close(actual, expected, path='value', tolerance=1e-8):
    """Compare nested numeric camera/blocking values without raster baselines."""
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise AssertionError(f'{path}: keys changed')
        for key in expected:
            assert_close(actual[key], expected[key], f'{path}.{key}', tolerance)
    elif isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            raise AssertionError(f'{path}: vector length changed')
        for index, value in enumerate(expected):
            assert_close(actual[index], value, f'{path}[{index}]', tolerance)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not math.isclose(actual, expected, rel_tol=0, abs_tol=tolerance):
            raise AssertionError(f'{path}: changed from {expected!r} to {actual!r}')
    elif actual != expected:
        raise AssertionError(f'{path}: changed from {expected!r} to {actual!r}')


def validate_frame(scene, expected):
    """Wardrobe/energy pixels may change; authored cameras and staging may not."""
    actual = dict(shot=scene.shot, camera=list(scene.camera_position),
                  zoom=scene.camera_zoom, brush=scene.brush_progress)
    for key in actual:
        assert_close(actual[key], expected[key], key)
    if 'action' in expected:
        action = scene.action_stage.telemetry(scene.elapsed)
        for key in ('shot', 'positions', 'camera_position', 'camera_target', 'focal'):
            if key in expected['action']:
                assert_close(action[key], expected['action'][key], f'action.{key}')
        if action.get('world_rhea_count', 1) != 1:
            raise AssertionError('The cinematic must contain one world-space Rhea')
        trace = getattr(scene.action_stage, 'last_draw_trace', [])
        if sum(entry.get('actor') == 'rhea' for entry in trace) > 1:
            raise AssertionError('Rhea was drawn more than once in the world')


def encoded_audio_metrics(movie):
    raw = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(movie), '-vn', '-ar', '48000',
        '-ac', '2', '-f', 'f32le', '-'])
    samples = np.frombuffer(raw, dtype='<f4').reshape(-1, 2)
    if not np.isfinite(samples).all():
        raise AssertionError('Encoded review audio contains non-finite samples')
    peak = float(np.max(np.abs(samples)))
    clipped = int(np.count_nonzero(np.abs(samples) >= 1.))
    if clipped:
        raise AssertionError(f'Encoded review audio clips at {clipped} samples')
    return dict(rate=48000, channels=2, decoded_frames=len(samples),
                sample_peak=peak, sample_peak_dbfs=20*math.log10(max(peak, 1e-12)),
                clipped_samples=clipped)


def capture(output=OUTPUT, *, protected_hashes=None):
    from ice_reaper_opening import IceReaperOpening

    output.mkdir(parents=True, exist_ok=True)
    reference = json.loads(REFERENCE.read_text())
    if reference['frames'] != 1920 or reference['duration_seconds'] != 32:
        raise AssertionError('The previous complete cinematic baseline is missing')
    baseline = {record['frame']: record for record in reference['timeline']}
    source_names = ('opening_cinematic.py', 'ice_reaper_opening.py',
                    'ice_reaper_action.py', 'rhea_scene_awakening.py',
                    'ice_reaper_duel.py', 'ice_reaper_audio.py',
                    'tools/capture_rhea_winter_cinematic.py')
    if (ROOT/'rhea_winter.py').exists():
        source_names += ('rhea_winter.py',)
    hashes = {name: digest(ROOT/name) for name in source_names}
    assets = {str(path.relative_to(ROOT)): digest(path)
              for folder in ('assets/story/rhea_winter',
                             'assets/source/cinematics/rhea_winter')
              for path in sorted((ROOT/folder).rglob('*')) if path.is_file()}
    if not assets:
        raise AssertionError('Winter art assets are not ready to capture')
    protected = json.loads(Path(protected_hashes).read_text()) if protected_hashes else {}
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected character, music or sound asset changed')

    checked = set()
    original_draw = IceReaperOpening._draw_scene
    original_keys = production.KEYFRAME_TIMES
    original_thumbnails = production.capture_thumbnails
    original_popen = subprocess.Popen

    def checked_scene(scene, canvas, camera):
        original_draw(scene, canvas, camera)
        index = round(scene.elapsed*60)
        if index in baseline:
            validate_frame(scene, baseline[index])
            checked.add(index)

    def bounded_encoder(command, *args, **kwargs):
        if (isinstance(command, (list, tuple)) and command
                and Path(command[0]).name == 'ffmpeg' and 'rawvideo' in command):
            command = list(command)
            for option, value in (('-preset', 'medium'), ('-crf', '21'),
                                  ('-maxrate', '2M'), ('-bufsize', '4M')):
                if option in command:
                    command[command.index(option)+1] = value
        return original_popen(command, *args, **kwargs)

    try:
        IceReaperOpening._draw_scene = checked_scene
        production.KEYFRAME_TIMES = KEYFRAMES
        production.capture_thumbnails = lambda _ids: None
        subprocess.Popen = bounded_encoder
        production.capture(output, fps=60)
    finally:
        IceReaperOpening._draw_scene = original_draw
        production.KEYFRAME_TIMES = original_keys
        production.capture_thumbnails = original_thumbnails
        subprocess.Popen = original_popen

    if checked != set(range(1920)):
        raise AssertionError(f'Incomplete camera/blocking validation: {len(checked)}')
    if hashes != {name: digest(ROOT/name) for name in hashes}:
        raise AssertionError('Runtime changed during capture')
    if assets != {name: digest(ROOT/name) for name in assets}:
        raise AssertionError('Winter art changed during capture')
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected character, music or sound asset changed during capture')

    path = output/'verification.json'
    report = json.loads(path.read_text())
    if report['frames'] != 1920 or report['duration_seconds'] != 32:
        raise AssertionError('Review movie must contain the full 32-second cinematic')
    lines = {frame['dialogue'] for frame in report['timeline'] if frame['dialogue']}
    expected_lines = {'Rhea! No!', "Cael, go! I'll cover!", 'Incoming! I got this one!',
                      'Thanks guys, now leave her to me...', 'Rhea...are you su-'}
    if lines != expected_lines:
        raise AssertionError(f'Dialogue changed or disappeared: {lines!r}')
    pressure = next(cue for cue in report['effects']['cues'] if cue['id'] == 'prison_burst')
    if pressure['time'] != 17.1 or 'ice_reaper_breakout/' not in pressure['file']:
        raise AssertionError('The approved pressure-release sound must remain in the movie')
    report.update(runtime_sources=hashes, winter_asset_hashes=assets,
                  protected_asset_hashes=protected,
                  camera_and_blocking_preservation=dict(frames=1920, all_frames_checked=True,
                      reference=str(REFERENCE.relative_to(ROOT)), reference_sha256=digest(REFERENCE),
                      pixel_art_changes='Rhea winter wardrobe and flowing energy intentionally updated'),
                  encoded_audio=encoded_audio_metrics(output/'preview.mp4'))
    report['encoder_policy'] = dict(preset='medium', crf=21, maxrate='2M',
                                    bufsize='4M', audio='AAC 192k')
    path.write_text(json.dumps(report, indent=2)+'\n')
    times = sorted({*POSTERS, *(time for values in STRIPS.values() for time in values)})
    decoded = decode_frames(output/'preview.mp4', times, 60)
    for time, name in POSTERS.items():
        decoded[round(time*60)].save(output/name, optimize=True)
    for name, values in STRIPS.items():
        filmstrip(decoded, values, 60, output/f'{name}.png', name.replace('_', ' ').title())
    print(json.dumps(dict(duration=32, fps=60, frames=1920,
                         camera_and_blocking_frames_checked=len(checked),
                         video_bytes=(output/'preview.mp4').stat().st_size,
                         encoded_audio=report['encoded_audio'])))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--protected-hashes', type=Path,
                        help='Optional pre-edit JSON map of character/audio/portrait SHA-256 hashes')
    args = parser.parse_args()
    capture(args.output.resolve(), protected_hashes=args.protected_hashes)
