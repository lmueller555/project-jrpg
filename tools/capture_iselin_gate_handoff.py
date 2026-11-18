"""Capture the live aerial-to-ground arrival handoff without artwork overrides.

Continuous previews station aerial_descent once at 4.3s, then use production
updates. Separate endpoint stills are explicitly labelled boundary diagnostics.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0, str(ROOT))

from tools.capture_iselin_walk_stop import Review, digest, font, live_bank_evidence, write_gif

START = 4.3


def station(review, shot, seconds, reduced):
    """Initial fixture setup only; callers never station a running capture."""
    scene = review.scene
    scene.clear_actor_actions()
    scene.phase_index = next(i for i, p in enumerate(scene.data['phases']) if p['id'] == shot)
    scene.phase_time = seconds
    scene.elapsed = sum(p['min_seconds'] for p in scene.data['phases'][:scene.phase_index])+seconds
    scene.dialogue_index = scene.page_index = 0
    scene.active = True;scene.paused = False;scene.focused = True
    review.child._music_focused = True
    review.child.audio.reduced_motion = reduced
    review.elapsed = 0.


def advance_to(review, target):
    """Split updates at the actual phase end, avoiding a discarded overshoot."""
    while target-review.elapsed > 1e-10:
        delta = min(.02, target-review.elapsed)
        remaining = review.scene.phase['min_seconds']-review.scene.phase_time
        if review.scene.shot == 'aerial_descent' and 0 < remaining <= delta+1e-10:
            delta = remaining
        review.advance(delta)


def state(review):
    scene = review.scene;snapshot = scene.aerial_snapshot()
    result = {'capture_elapsed': round(review.elapsed, 9), 'shot': scene.shot,
              'shot_seconds': round(scene.phase_time, 9), 'reduced_motion': scene.reduced_motion,
              'action': scene.actor_action_state('iselin')}
    if snapshot:
        result['aerial'] = {key: snapshot[key] for key in
            ('seconds', 'spatial_seconds', 'ground_handoff', 'ground_viewport',
             'canopy', 'camera', 'projected_actors')}
    else:
        actor = next(a for a in scene.phase['actors'] if a['id'] == 'iselin')
        frame = scene._frame(actor)
        result.update(root=list(scene.actor_position(actor)), camera=list(scene.camera_position),
                      rendered_frame_rgba_sha256=sha256(review.pygame.image.tobytes(frame, 'RGBA')).hexdigest())
    return result


def label(review, image, observation):
    from PIL import Image, ImageDraw
    result = Image.new('RGB', (480, 360), '#e8edf2')
    result.paste(image.resize((480, 320), Image.Resampling.NEAREST), (0, 40))
    draw = ImageDraw.Draw(result)
    draw.text((8, 3), 'LIVE AERIAL → GATE / '+('REDUCED MOTION' if observation['reduced_motion'] else 'NORMAL'),
              font=font(ROOT, 14), fill='#263c35')
    draw.text((8, 21), f'{observation["shot"]} {observation["shot_seconds"]:.2f}s / updates only',
              font=font(ROOT, 13), fill='#263c35')
    return result


def continuous(output, reduced):
    name = 'reduced' if reduced else 'normal'
    frames = [];observations = [];stills = []
    with tempfile.TemporaryDirectory(prefix='iselin-handoff-live-') as directory:
        review = Review(ROOT, directory)
        try:
            station(review, 'aerial_descent', START, reduced)
            approval = live_bank_evidence(review)
            for index in range(99):
                advance_to(review, round(index*.05, 9))
                observation = state(review);image = review.image()
                frames.append(label(review, image, observation));observations.append(observation)
                if index in (0, 4, 16, 94, 98):
                    filename = f'handoff_{name}_{index:03}.png';image.save(output/filename)
                    stills.append({'file': filename, **observation})
            if review.scene.shot != 'gate_approach' or abs(review.scene.phase_time-.2) > 1e-8:
                raise ValueError('Continuous capture did not reach the first .2s of gate approach')
            playback = write_gif(output/f'handoff_{name}.gif', frames, 50)
        finally:review.close()
    return {'initial_station': {'shot': 'aerial_descent', 'shot_seconds': START},
            'maximum_update_seconds': .02, 'sample_exposure_ms': 50,
            'classification': 'Continuous production Game.update/Game.draw after one initial shot station; no frame, root or artwork overrides.',
            'playback': playback, 'live_bank_approval': approval,
            'timeline_samples': observations, 'meaningful_samples': stills}


def boundary(output, reduced):
    """Two independent initially stationed production-plate diagnostics."""
    from PIL import Image
    name = 'reduced' if reduced else 'normal';values = [];images = []
    for shot, seconds, suffix in (('aerial_descent', 9., 'endpoint'), ('gate_approach', 0., 'ground')):
        with tempfile.TemporaryDirectory(prefix='iselin-handoff-boundary-') as directory:
            review = Review(ROOT, directory)
            try:
                station(review, shot, seconds, reduced)
                canvas = review.pygame.Surface((480, 320), review.pygame.SRCALPHA)
                ui = review.pygame.Surface((480, 320), review.pygame.SRCALPHA)
                review.scene.draw(canvas, ui)
                pixels = review.pygame.image.tobytes(canvas, 'RGB')
                image = Image.frombytes('RGB', canvas.get_size(), pixels)
                filename = f'handoff_{name}_{suffix}.png';image.save(output/filename)
                values.append({'file': filename, 'initial_station': {'shot': shot, 'shot_seconds': seconds},
                               'production_plate_rgb_sha256': sha256(pixels).hexdigest(),
                               'fade_alpha': review.scene.fade_alpha})
                images.append(image)
            finally:review.close()
    if images[0].tobytes() != images[1].tobytes():
        raise ValueError('Exact aerial endpoint and ground start are not pixel-identical')
    return {'classification': 'Two independently stationed exact-boundary diagnostics; not sequential played updates.',
            'reduced_motion': reduced, 'exact_plate_rgb_equality': True,
            'different_rgb_pixels': 0, 'stills': values}, images


def capture(output):
    from PIL import Image, ImageDraw
    output.mkdir(parents=True, exist_ok=True)
    continuous_reports = {name: continuous(output, reduced) for name, reduced in (('normal', False), ('reduced', True))}
    boundary_reports = {};board = Image.new('RGB', (960, 714), '#e8edf2');draw = ImageDraw.Draw(board)
    for row, (name, reduced) in enumerate((('normal', False), ('reduced', True))):
        report, images = boundary(output, reduced);boundary_reports[name] = report
        for column, (image, kind) in enumerate(zip(images, ('Exact aerial endpoint', 'Ground approach start'))):
            x = column*480;y = row*357
            draw.text((x+8, y+4), f'{name}: {kind} / boundary diagnostic', font=font(ROOT, 15), fill='#263c35')
            board.paste(image, (x, y+30))
    board.save(output/'handoff_boundary_board.png')
    dependencies = ('regent_arrival.py', 'regent_aerial.py', 'tools/capture_iselin_walk_stop.py',
                    'tools/export_iselin_gate_detail.py', 'tools/build_regent_iselin.py',
                    'assets/story/regent_arrival/scene.json',
                    'assets/story/regent_arrival/actors/iselin/animation.json',
                    'assets/source/characters/iselin/cinematic_gate_left/approval.json')
    report = {'capture_helper_sha256': digest(Path(__file__)),
              'continuous': continuous_reports, 'exact_boundary_diagnostics': boundary_reports,
              'input_sha256': {name: digest(ROOT/name) for name in dependencies},
              'output_sha256': {path.name: digest(path) for path in sorted(output.glob('handoff_*'))
                                if path.suffix in ('.gif', '.png')
                                and path.name.startswith(('handoff_normal', 'handoff_reduced', 'handoff_boundary'))}}
    (output/'handoff_capture.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Live aerial-to-gate capture complete:', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(tempfile.gettempdir())/'iselin-gate-handoff')
    args = parser.parse_args()
    os.environ['SDL_VIDEODRIVER'] = 'dummy';os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    capture(args.out)


if __name__ == '__main__':main()
