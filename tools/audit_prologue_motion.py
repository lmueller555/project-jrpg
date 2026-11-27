"""Measure selected motion promises directly from complete painted RGBA drawings.

This is a regression instrument, not an anatomy solver.  Boot measurements are
distal silhouette quantiles inside reviewed, identity-separated windows; they
are not claimed ankle/joint locations.  Material checks measure regional alpha
contours.  Measured neck/belt registration and whole-image density are inputs;
authoring targets, generation prompts and phase labels are not motion evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from tools.prologue_motion_review import (frame_identity, metric_context,
                                              find_reviewed_exception)
except ModuleNotFoundError:
    from prologue_motion_review import (frame_identity, metric_context,
                                        find_reviewed_exception)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/cinematics/fire_veinhold/face_reveal'
CONTRACT = ROOT / 'tests/fixtures/prologue_motion/contract.json'
OBSERVATIONS = CONTRACT.parent / 'registration_observations.json'


@dataclass
class Drawing:
    index: int
    source: str
    digest: str
    image: Image.Image
    neck: tuple[float, float]
    belt: tuple[float, float]
    scale: float
    cell: tuple[int, int, int, int]
    origin: tuple[float, float]


def load_drawings(actor: str, source: Path = SOURCE) -> list[Drawing]:
    """Follow the authored profile sequence, never PNG filename order."""
    folder = source / actor
    profile = json.loads((folder / 'source_art_48.json').read_text())
    drawings = [_drawing(index, record, folder) for index, record in enumerate(profile['frames'])]
    for drawing, record in zip(drawings, profile['frames']):
        if profile.get('source_sha256', {}).get(record['source']) != drawing.digest:
            raise ValueError('Artwork no longer matches its measured registration: ' + drawing.source)
    return drawings


def _drawing(index: int, record: dict, folder: Path) -> Drawing:
    path = folder / record['source']
    points = record['landmarks']
    image = Image.open(path).convert('RGBA').crop(tuple(record['cell']))
    return Drawing(index, record.get('original_source', record['source']),
                   sha256(path.read_bytes()).hexdigest(), image,
                   tuple(points['neck']), tuple(points['belt']), record['scale'],
                   tuple(record['cell']), tuple(record['origin']))


def load_fixture(actor: str, folder: Path) -> list[Drawing]:
    manifest = json.loads((folder / 'manifest.json').read_text())
    drawings = []
    for record in manifest[actor]['frames']:
        drawing = _drawing(record['index'], record, folder)
        if drawing.digest != record['sha256']:
            raise ValueError('Changed negative fixture: ' + drawing.source)
        drawings.append(drawing)
    return drawings


def validate_registration_observations(actor: str, drawings: list[Drawing],
                                      path: Path = OBSERVATIONS) -> None:
    """Require a reviewable change when actual measured registration changes.

    Source path/crop/hash, whole-image origin and measured neck/belt/density are
    bound together. This prevents editing registration coordinates or the crop
    from silently moving the metric windows. The observation file is a review
    artifact, not a generated guide.
    """
    observations = json.loads(path.read_text())['actors'][actor]
    if len(drawings) != len(observations):
        raise ValueError('Registration observation coverage changed: ' + actor)
    for drawing in drawings:
        expected = observations[str(drawing.index)]
        actual = {'sha256': drawing.digest, 'source': drawing.source, 'cell': list(drawing.cell),
                  'origin': list(drawing.origin), 'neck': list(drawing.neck),
                  'belt': list(drawing.belt), 'scale': drawing.scale}
        if actual != {key: expected[key] for key in actual}:
            raise ValueError(f'Review actual artwork registration before adoption: {actor}:{drawing.index}')


def distal_contour(drawing: Drawing, region: dict) -> dict:
    """Actual alpha-boundary bottom, at fixed recorded whole-image density."""
    rgba = np.asarray(drawing.image)
    yy, xx = np.nonzero(rgba[:, :, 3] > 128)
    x = (xx - drawing.neck[0]) * drawing.scale
    y = (yy - drawing.neck[1]) * drawing.scale
    belt_y = (drawing.belt[1] - drawing.neck[1]) * drawing.scale
    left, right = region['x']
    vertical = None
    reviewed = None
    for observation in region.get('reviewed_window_overrides', []):
        if observation['sha256'] == drawing.digest:
            left, right = observation['x']
            vertical = observation.get('y')
            reviewed = observation
    selected = (x > left) & (x < right)
    if vertical is None:
        selected &= y > belt_y + region['below_belt']
    else:
        selected &= (y > vertical[0]) & (y < vertical[1])
    if np.count_nonzero(selected) < region.get('minimum_pixels', 100):
        raise ValueError(f'Unmeasurable distal region {drawing.index}:{region}')
    bottom_y = float(np.quantile(y[selected], .995))
    bottom = selected & (y >= bottom_y)
    result = {'x': float(np.median(x[bottom])), 'y': bottom_y,
              'opaque_pixels': int(np.count_nonzero(selected)), 'window_x': [left, right],
              'window_y': vertical or [belt_y + region['below_belt'], 1000]}
    if reviewed and 'observed_distal_exported' in reviewed:
        # This observed point is a reviewed lowest-visible sole observation,
        # never a desired gait target or an inferred hidden ankle/heel.
        actual_y = bottom_y + drawing.neck[1] * drawing.scale + round(drawing.origin[1])
        result['observed_y_error'] = actual_y - reviewed['observed_distal_exported'][1]
        result['observed_y_tolerance'] = reviewed['uncertainty_pixels'] + 1
    return result


def registered_image(drawing: Drawing) -> Image.Image:
    """Whole-figure uniform sampling, translated to neck (512, 200).

    Translation removes body registration/bob for material-relative measurements;
    no silhouette fitting, regional alignment or per-limb transform is applied.
    """
    image = drawing.image.copy()
    image.putalpha(image.getchannel('A').point(lambda a: 0 if a <= 16 else a))
    size = tuple(max(1, round(value * drawing.scale)) for value in image.size)
    image = image.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
    canvas = Image.new('RGBA', (1024, 1200))
    origin = (round(512 - drawing.neck[0] * drawing.scale),
              round(200 - drawing.neck[1] * drawing.scale))
    canvas.alpha_composite(image, origin)
    return canvas


def registered_alpha(drawing: Drawing) -> np.ndarray:
    return np.asarray(registered_image(drawing))[:, :, 3] > 128


def regional_contour(alpha: np.ndarray, region: dict) -> np.ndarray:
    x0, x1, y0, y1 = region['window']
    x0, x1, y0, y1 = x0 + 512, x1 + 512, y0 + 200, y1 + 200
    mask = alpha[y0:y1, x0:x1]
    interior = mask.copy()
    interior[1:-1, 1:-1] &= (mask[:-2, 1:-1] & mask[2:, 1:-1]
                               & mask[1:-1, :-2] & mask[1:-1, 2:])
    boundary = mask & ~interior
    # Cropping creates a rectangle edge, not a painted material contour.
    margin = region.get('crop_margin', 3)
    boundary[:margin] = boundary[-margin:] = False
    boundary[:, :margin] = boundary[:, -margin:] = False
    yy, xx = np.nonzero(boundary)
    if len(xx) < 20:
        raise ValueError('Unmeasurable material contour')
    return np.column_stack((xx + x0, yy + y0)).astype(np.float32)


def contour_distance(first: np.ndarray, second: np.ndarray) -> float:
    """Symmetric 90th-percentile nearest-contour distance in artwork pixels."""
    if np.array_equal(first, second):
        return 0.0
    def nearest(a, b):
        result = []
        for start in range(0, len(a), 128):
            difference = a[start:start + 128, None, :] - b[None, :, :]
            result.extend(np.sqrt(np.min(np.sum(difference * difference, axis=2), axis=1)))
        return np.asarray(result)
    return float(np.quantile(np.concatenate((nearest(first, second), nearest(second, first))), .9))


def contour_features(contour: np.ndarray) -> np.ndarray:
    """Distribution landmarks, not correspondences to persistent cloth points."""
    return np.quantile(contour, [.1, .5, .9], axis=0).reshape(-1)


def audit(actor: str, drawings: list[Drawing], contract: dict | None = None,
          complete: bool = True) -> dict:
    contract = contract or json.loads(CONTRACT.read_text())
    rules = contract['actors'][actor]
    frames = {drawing.index: drawing for drawing in drawings}
    report = {'actor': actor, 'measurements': {}, 'violations': [], 'diagnostics': [],
              'sources': [{'index': d.index, 'source': d.source, 'sha256': d.digest} for d in drawings]}
    if complete and (set(frames) != set(range(48)) or len(drawings) != 48):
        report['violations'].append({'check': 'complete_frame_coverage',
                                      'missing': sorted(set(range(48)) - set(frames)),
                                      'unexpected': sorted(set(frames) - set(range(48)))})
    # Unlike the body-relative contour checks, these retain the actual export
    # translation and use the exporter's whole-origin rounding convention.
    for landmark, maximum in rules['max_exported_registration_delta'].items():
        points = {i: [getattr(d, landmark)[j] * d.scale + round(d.origin[j]) for j in (0, 1)]
                  for i, d in frames.items()}
        report['measurements']['exported_' + landmark] = points
        for first in range(48):
            second = (first + 1) % 48
            if first in points and second in points:
                distance = float(np.linalg.norm(np.asarray(points[second]) - points[first]))
                if distance > maximum:
                    report['violations'].append({'check': 'exported_registration_step',
                        'landmark': landmark, 'frames': [first, second],
                        'pixels': round(distance, 3), 'limit': maximum})
    torso = {i: (d.belt[1] - d.neck[1]) * d.scale for i, d in frames.items()}
    report['measurements']['projected_torso_span'] = torso
    for index, span in torso.items():
        reference = rules['reference_projected_torso_span']
        if span <= 0 or abs(span - reference) > rules['maximum_torso_relative_error'] * reference:
            report['violations'].append({'check': 'projected_torso_model', 'frame': index,
                                          'pixels': round(span, 3), 'reference_pixels': reference,
                                          'relative_limit': rules['maximum_torso_relative_error']})
    values = {}
    for label, region in rules.get('distal_regions', {}).items():
        values[label] = {i: distal_contour(d, region) for i, d in frames.items()}
        report['measurements'][label] = values[label]
        for index, point in values[label].items():
            if abs(point.get('observed_y_error', 0)) > point.get('observed_y_tolerance', 0):
                report['violations'].append({'check': 'reviewed_sole_pixel_support', 'region': label,
                    'frame': index, 'pixels': round(point['observed_y_error'], 3),
                    'limit': point['observed_y_tolerance'],
                    'note': 'Reviewed lowest-visible sole y lacks support in its actual painted identity ROI.'})
            if min(abs(point['x'] - edge) for edge in point['window_x']) < 5:
                report['diagnostics'].append({'check': 'distal_border_intrusion', 'region': label,
                                              'frame': index, 'x': round(point['x'], 3),
                                              'note': 'Review foot identity; contour approaches measurement-window boundary.'})
        for first, second in rules.get('required_transitions', []):
            if first in frames and second in frames:
                delta = values[label][second]['y'] - values[label][first]['y']
                if abs(delta) > rules['max_distal_delta']:
                    report['violations'].append({'check': 'distal_step', 'region': label,
                                                  'frames': [first, second], 'pixels': round(delta, 3),
                                                  'limit': rules['max_distal_delta']})
            elif complete:
                report['violations'].append({'check': 'required_coverage', 'region': label,
                                              'frames': [first, second]})
        if complete:
            span = max(v['y'] for v in values[label].values()) - min(v['y'] for v in values[label].values())
            if span < rules['minimum_cycle_distal_range']:
                report['violations'].append({'check': 'cycle_progress', 'region': label,
                                              'pixels': round(span, 3), 'minimum': rules['minimum_cycle_distal_range']})
    for window in rules.get('progress_windows', []):
        start, early, end = window['frames']
        label = window['region']
        if not all(i in frames for i in range(start, end + 1)):
            if complete:
                report['violations'].append({'check': 'required_progress_coverage', 'region': label,
                                              'frames': [start, early, end]})
            continue
        y = values[label]
        direction = window['direction']
        progress = direction * (y[early]['y'] - y[start]['y'])
        if progress < window['minimum_early_progress']:
            report['violations'].append({'check': 'held_exchange', 'region': label,
                                          'frames': [start, early], 'pixels': round(progress, 3),
                                          'minimum': window['minimum_early_progress']})
        net = direction * (y[end]['y'] - y[start]['y'])
        maximum = max(direction * (y[i + 3]['y'] - y[i]['y']) for i in range(start, end - 2))
        if net <= 0 or maximum > window['maximum_three_tick_fraction'] * net:
            report['diagnostics'].append({'check': 'concentrated_exchange', 'region': label,
                                          'frames': [start, end], 'three_tick_pixels': round(maximum, 3),
                                          'net_pixels': round(net, 3),
                                          'review_trigger': window['maximum_three_tick_fraction'],
                                          'note': 'Review timing in the actual sequence; projected toe rotation and contour variation prevent this ratio from defining natural anatomy.'})
    if rules.get('material_regions'):
        alphas = {i: registered_alpha(d) for i, d in frames.items()}
        for label, region in rules['material_regions'].items():
            contours = {i: regional_contour(a, region) for i, a in alphas.items()}
            features = {i: contour_features(c) for i, c in contours.items()}
            measurements = []
            pairs = [(i, (i + 1) % 48) for i in frames if (i + 1) % 48 in frames]
            for first, second in pairs:
                distance = contour_distance(contours[first], contours[second])
                item = {'region': label, 'frames': [first, second], 'pixels': round(distance, 3),
                        'limit': region['max_q90_distance']}
                measurements.append(item)
                if distance > region['max_q90_distance']:
                    context = metric_context('material_contour', label,
                        [frame_identity(frames[index], registered_image(frames[index]))
                         for index in (first, second)], region)
                    reviewed = find_reviewed_exception(rules.get('reviewed_metric_exceptions', []),
                        context=context, value=distance, default_limit=region['max_q90_distance'])
                    if reviewed is None:
                        report['violations'].append({'check': 'material_contour', **item})
                    else:
                        report['diagnostics'].append({'check': 'reviewed_material_contour', **item,
                            'review_id': reviewed['id'], 'reason': reviewed['reason'],
                            'evidence': reviewed['evidence'],
                            'maximum_reviewed_value': reviewed['maximum_reviewed_value']})
            report['measurements'][label] = measurements
            if complete:
                origin = features[min(features)]
                excursion = max(float(np.sqrt(np.mean((feature - origin) ** 2)))
                                for feature in features.values())
                minimum = region['minimum_feature_excursion']
                if excursion < minimum:
                    report['violations'].append({'check': 'frozen_material', 'region': label,
                                                  'rms_pixels': round(excursion, 3), 'minimum': minimum})
            if all(i in features for i in (46, 47, 0, 1)):
                incoming = features[47] - features[46]
                seam = features[0] - features[47]
                outgoing = features[1] - features[0]
                report['diagnostics'].append({'check': 'material_seam_feature_velocity', 'region': label,
                    'incoming_rms': round(float(np.sqrt(np.mean(incoming ** 2))), 3),
                    'seam_rms': round(float(np.sqrt(np.mean(seam ** 2))), 3),
                    'outgoing_rms': round(float(np.sqrt(np.mean(outgoing ** 2))), 3),
                    'incoming_dot_seam': round(float(incoming @ seam), 3),
                    'seam_dot_outgoing': round(float(seam @ outgoing), 3),
                    'note': 'Diagnostic only: contour quantiles do not identify persistent material points; natural reversals are possible.'})
        if complete and not (47 in frames and 0 in frames):
            report['violations'].append({'check': 'required_material_seam_coverage', 'frames': [47, 0]})
    return report


def overlay(actor: str, drawings: list[Drawing], target: Path, contract: dict | None = None):
    """A numbered visual artifact makes the actual measurement windows reviewable."""
    contract = contract or json.loads(CONTRACT.read_text())
    rules = contract['actors'][actor]
    tiles = []
    for drawing in drawings:
        tile = Image.new('RGB', (1024, 1200), '#6f7380')
        image = registered_image(drawing)
        tile.paste(image, (0, 0), image)
        pen = ImageDraw.Draw(tile)
        pen.ellipse((508, 196, 516, 204), fill='red')
        belt_y = 200 + (drawing.belt[1] - drawing.neck[1]) * drawing.scale
        for label, region in rules.get('distal_regions', {}).items():
            point = distal_contour(drawing, region)
            x0, x1 = point['window_x']
            y0, y1 = point['window_y']
            pen.rectangle((512 + x0, 200 + y0, 512 + x1, 200 + y1), outline='orange', width=2)
            p = point
            pen.ellipse((508 + p['x'], 196 + p['y'], 516 + p['x'], 204 + p['y']), fill='red')
        for region in rules.get('material_regions', {}).values():
            x0, x1, y0, y1 = region['window']
            pen.rectangle((512 + x0, 200 + y0, 512 + x1, 200 + y1), outline='cyan', width=2)
        pen.text((30, 1100), f'{drawing.index:02d}  {drawing.digest[:12]}', fill='yellow')
        tile.thumbnail((256, 300))
        tiles.append(tile)
    sheet = Image.new('RGB', (256 * min(8, len(tiles)), 300 * ((len(tiles) + 7) // 8)))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % 8) * 256, (i // 8) * 300))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor', choices=('lucan', 'iselin', 'crown_soldier'))
    parser.add_argument('--before', action='store_true', help='Measure immutable rejected-art fixtures')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--overlay', type=Path)
    args = parser.parse_args()
    reports = []
    for actor in ([args.actor] if args.actor else ('lucan', 'iselin', 'crown_soldier')):
        drawings = (load_fixture(actor, CONTRACT.parent / 'before') if args.before else load_drawings(actor))
        report = audit(actor, drawings, complete=not args.before)
        if not args.before:
            try:
                validate_registration_observations(actor, drawings)
            except ValueError as error:
                report['violations'].append({'check': 'registration_observation_review', 'message': str(error)})
        reports.append(report)
        if args.overlay:
            overlay(actor, drawings, args.overlay / f'{actor}_measurement_windows.png')
        print(actor + ': ' + json.dumps(report['violations']))
        timing_review = [item for item in report['diagnostics'] if item['check'] == 'concentrated_exchange']
        if timing_review:
            print(actor + ' timing review (diagnostic): ' + json.dumps(timing_review))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, indent=2) + '\n')
    return int(any(report['violations'] for report in reports))


if __name__ == '__main__':
    raise SystemExit(main())
