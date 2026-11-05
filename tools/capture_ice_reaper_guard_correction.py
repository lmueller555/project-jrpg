"""Capture the Lucan guard and approved Reaper-art correction, preserving the shot.

This wraps the same production Gallery capture. Comparison images decode the
resulting MP4; scope checks inspect the runtime stage against the saved PR108
baseline. No diagnostic guides are part of the game's cinematic renderer.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

from PIL import Image, ImageDraw
import capture_ice_reaper_continuity as continuity

OUTPUT = ROOT/'docs/reviews/ice_reaper_guard_correction'
PREVIOUS = ROOT/'docs/reviews/ice_reaper_continuity'
TEMP_BASELINE = Path('/tmp/ice-guard-correction-baseline/state.json')
STRIPS = {
    'rescue_filmstrip': (7.3, 7.5, 8., 8.5, 8.99, 9.2),
    'orbit_filmstrip': (9.5, 9.8, 10.1, 10.4, 10.7, 11.),
    'panorama_filmstrip': (17.2, 18.3, 19., 19.8),
}


def pixels_hash(image):
    import pygame
    return hashlib.sha256(pygame.image.tobytes(image, 'RGBA')).hexdigest()


def verify_scope(output, baseline_path=None):
    import pygame
    from ice_reaper_action import IceReaperActionStage as Stage
    baseline_path = Path(baseline_path) if baseline_path else output/'scope_baseline.json'
    if not baseline_path.is_file():
        if not TEMP_BASELINE.is_file():
            raise FileNotFoundError('The pre-edit PR108 scope baseline is required')
        shutil.copyfile(TEMP_BASELINE, baseline_path)
    baseline = json.loads(baseline_path.read_text())
    pygame.init()
    pygame.display.set_mode((480, 320))
    try:
        stage = Stage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        camera_results = []
        for old in baseline['camera']:
            time = old[0]
            camera = stage.camera(time)
            current = [time, list(camera.position), list(camera.target), camera.focal, list(camera.center)]
            if current != old:
                raise AssertionError(f'Approved camera trajectory changed at {time}')
            camera_results.append(current)
        environments = {}
        for value, expected in baseline['environment'].items():
            time = float(value)
            canvas = pygame.Surface((480, 320))
            stage._background(canvas, stage.camera(time), time)
            actual = hashlib.sha256(pygame.image.tobytes(canvas, 'RGB')).hexdigest()
            if actual != expected:
                raise AssertionError(f'Approved environment changed at {time}')
            environments[value] = actual
        lucan = {}
        for value, expected in baseline['lucan_end'].items():
            time = float(value)
            position = stage.actor_positions(time)['lucan']
            camera = stage.camera(time)
            action, local, duration = stage._action('lucan', time)
            image, _ = stage._sequence('lucan', action, local, duration, camera, position, time=time)
            current = dict(heading=list(stage.actor_heading('lucan', time)),
                           position=list(position), frame=pixels_hash(image))
            if current != expected:
                raise AssertionError(f'Already-correct Lucan ending changed at {time}: {current}')
            lucan[value] = current
        tree = ast.parse((ROOT/'ice_reaper_action.py').read_text())
        methods = {}
        for name, expected in baseline['method_hashes'].items():
            node = next(node for node in ast.walk(tree)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
            actual = hashlib.sha256(ast.dump(node).encode()).hexdigest()
            if actual != expected:
                raise AssertionError(f'Protected camera/environment/projection method changed: {name}')
            methods[name] = actual
        approved = set()
        folder = ROOT/'assets/story/ice_reaper_rescue/actors/ice_reaper'
        for file in ('recharge_06.png', *(f'ready_rear_{i:02}.png' for i in range(1, 4)),
                     *(f'ready_side_{i:02}.png' for i in range(1, 4))):
            approved.add(pixels_hash(pygame.image.load(str(folder/file)).convert_alpha()))
        restored = {}
        for time in (16.3, 17.2, 17.8, 18.3, 19., 19.8):
            camera = stage.camera(time)
            position = stage.actor_positions(time)['ice_reaper']
            action, local, duration = stage._action('ice_reaper', time)
            image, _ = stage._sequence('ice_reaper', action, local, duration, camera, position, time=time)
            digest = pixels_hash(image)
            if digest not in approved:
                raise AssertionError(f'Final Reaper frame is not retained approved art at {time}')
            restored[str(time)] = digest
    finally:
        pygame.quit()
    record = dict(
        version=1, comparison='Pre-correction PR108 runtime baseline',
        camera_samples_unchanged=len(camera_results),
        camera_track_sha256=hashlib.sha256(json.dumps(camera_results).encode()).hexdigest(),
        protected_method_hashes=methods, environment_hashes_unchanged=environments,
        lucan_ending_unchanged=lucan, restored_approved_reaper_art=restored,
        note='Camera, environment and projection checks use the direct runtime; movie comparisons include lossy encoding.',
    )
    (output/'correction_scope_verification.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def compare(previous, current, output, time, left, right):
    sheet = Image.new('RGB', (960, 358), '#142331')
    draw = ImageDraw.Draw(sheet)
    for column, (label, image) in enumerate(((left, previous), (right, current))):
        x = column*480
        draw.text((x+10, 8), label, font=continuity.font(16), fill='#f5e7c2')
        draw.text((x+10, 25), f'{time:.2f}s', font=continuity.font(12), fill='#e4edf2')
        sheet.paste(image.resize((480, 320), Image.Resampling.NEAREST), (x, 38))
    sheet.save(output, optimize=True)


def approved_art_card(output):
    folder = ROOT/'assets/story/ice_reaper_rescue/actors/ice_reaper'
    files = [folder/f'ready_rear_{i:02}.png' for i in range(1, 4)]
    sheet = Image.new('RGB', (768, 300), '#142331')
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), 'Retained approved Ice Reaper artwork — source sprites only',
              font=continuity.font(18), fill='#f5e7c2')
    for index, file in enumerate(files):
        image = Image.open(file).convert('RGBA')
        sheet.paste(image, (index*256+32, 46), image)
        draw.text((index*256+24, 260), file.name, font=continuity.font(15), fill='#e4edf2')
    sheet.save(output/'approved_reaper_art.png', optimize=True)


def capture(output=OUTPUT, *, fps=60, reuse=False, baseline_path=None):
    output.mkdir(parents=True, exist_ok=True)
    scope = verify_scope(output, baseline_path)
    old_previous, old_strips = continuity.PREVIOUS, continuity.STRIPS
    try:
        continuity.PREVIOUS, continuity.STRIPS = PREVIOUS, STRIPS
        continuity.review(output, fps=fps, reuse=reuse)
    finally:
        continuity.PREVIOUS, continuity.STRIPS = old_previous, old_strips
    times = (8.6, 8.99, 19.3)
    current = continuity.video_frames(output/'preview.mp4', times, fps)
    previous = continuity.video_frames(PREVIOUS/'preview.mp4', times, fps)
    for time, file in ((8.6, 'guard_comparison.png'), (8.99, 'impact_comparison.png')):
        compare(previous[round(time*fps)], current[round(time*fps)], output/file,
                time, 'PR108: previous guard', 'Updated: faces the Ice Reaper')
    compare(previous[round(19.3*fps)], current[round(19.3*fps)],
            output/'final_shot_comparison.png', 19.3,
            'PR108: newer Reaper artwork', 'Updated: approved art, same shot')
    approved_art_card(output)
    print(json.dumps(dict(scope_checks='passed', camera_samples=scope['camera_samples_unchanged'],
                         backgrounds=len(scope['environment_hashes_unchanged']),
                         preserved_lucan_poses=len(scope['lucan_ending_unchanged']))))
    return scope


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--fps', type=int, choices=(30, 60), default=60)
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    capture(args.output.resolve(), fps=args.fps, reuse=args.reuse, baseline_path=args.baseline)
