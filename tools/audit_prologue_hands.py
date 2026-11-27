"""Review visible hand pumps in the actual frontal paintings.

Warm skin/glove components are measured in torso-relative windows. This is a
scoped detector for these reviewed costumes, not a general pose estimator. The
opaque shield hides Lucan's and the soldier's other wrists; their equipment and
counterbalance still need visual review. Source neck/belt points and scale are
reviewed registration measurements, never intended hand-motion targets.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.audit_prologue_motion import Drawing, load_drawings, load_fixture


ACTORS = ('lucan', 'iselin', 'crown_soldier')
MINIMUM_RANGE = 40.0  # Recorded artwork pixels at the existing whole-body density.
DIAGNOSTIC_STEP = 40.0  # Component centroids are not persistent wrist joints.
# Independently reviewed on all 48 baseline drawings: the two real fist jumps
# measure 72/79 pixels, while the other observations stay below 55. This is a
# conservative detector for these costumes and density, not a universal speed.
MAXIMUM_GROSS_STEP = 60.0
REVIEWED_WINDOWS = ROOT/'tests/fixtures/prologue_hands/reviewed_windows.json'


def reviewed_window(actor: str, drawing: Drawing, side: str):
    """Select reviewed glove material, binding approval to the actual view.

    Costume-colored equipment can otherwise win the broad component search.
    These source-space boxes isolate glove pixels; they do not supply a hand
    position or change the movement bounds. Crop, pixels and registration must
    still match the independently inspected observation.
    """
    records = json.loads(REVIEWED_WINDOWS.read_text())['actors'].get(actor, [])
    for record in records:
        if record['source'] != drawing.source or record['side'] != side:
            continue
        actual = {'source_sha256': drawing.digest, 'cell': list(drawing.cell),
                  'neck': list(drawing.neck), 'belt': list(drawing.belt),
                  'scale': drawing.scale, 'origin': list(drawing.origin),
                  'cropped_rgba_sha256': sha256(drawing.image.tobytes()).hexdigest()}
        if any(record[key] != value for key, value in actual.items()):
            raise ValueError(f'Review actual glove window before adoption: {actor}:{drawing.index}')
        box = record['source_hand_box']
        if not (0 <= box[0] < box[2] <= drawing.image.width
                and 0 <= box[1] < box[3] <= drawing.image.height):
            raise ValueError('Invalid reviewed glove window')
        return tuple(box)
    return None


def _components(mask):
    """Four-connected painted warm regions; return size, centroid and bounds."""
    pending_mask = mask.copy()
    result = []
    for y, x in zip(*np.nonzero(mask)):
        if not pending_mask[y, x]:
            continue
        stack = [(int(y), int(x))]
        pending_mask[y, x] = False
        points = []
        while stack:
            yy, xx = stack.pop()
            points.append((xx, yy))
            for ny, nx in ((yy-1, xx), (yy+1, xx), (yy, xx-1), (yy, xx+1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and pending_mask[ny, nx]:
                    pending_mask[ny, nx] = False
                    stack.append((ny, nx))
        if len(points) < 24:
            continue
        points = np.asarray(points)
        low, high = points.min(axis=0), points.max(axis=0)
        aspect = (high[0]-low[0]+1)/(high[1]-low[1]+1)
        if .4 <= aspect <= 2.1:
            result.append({'area': len(points), 'point': points.mean(axis=0),
                           'bounds': [*low, *(high+1)]})
    return sorted(result, key=lambda item: item['area'], reverse=True)


def measure(drawing: Drawing, side: str, *, gloved: bool, window=None):
    """Locate a visible painted hand/glove, independently of guide coordinates."""
    neck_x, neck_y = drawing.neck
    belt_y = drawing.belt[1]
    scale = drawing.scale
    sign = -1 if side == 'anatomical_right' else 1
    x0, x1 = sorted((neck_x+sign*32/scale, neck_x+sign*240/scale))
    y0, y1 = neck_y+20/scale, belt_y+135/scale
    box = (max(0, int(x0)), max(0, int(y0)), min(drawing.image.width, int(x1)+1),
           min(drawing.image.height, int(y1)+1))
    if window is not None:
        box = window
    rgba = np.asarray(drawing.image.crop(box)).astype(np.int16)
    r, g, b, a = (rgba[:, :, i] for i in range(4))
    warm = ((a > 180) & (r > 65) & (g > 40) & (b > 25)
            & (r-g > 12) & (r-b > 22) & (g-b > 2) & (r < 2.5*g))
    if gloved:
        # Brown leather has much less yellow saturation than the adjoining
        # brass cuffs, sword hilt and coat trim. These bounds are reviewed on
        # the approved costume, not adjusted to manufacture a motion result.
        warm &= (r < 155) & (g < 118) & (b < 110) & (r-b < 65) & (g-b < 32)
    matches = _components(warm)
    if not matches:
        raise ValueError(f'No reviewed visible hand component: {drawing.index}:{side}')
    match = matches[0]
    point = match['point']+np.asarray(box[:2])
    return {'point_source': point.tolist(),
            'point_neck_relative': ((point-np.asarray(drawing.neck))*scale).tolist(),
            'bounds_source': [int(value+box[i % 2]) for i, value in enumerate(match['bounds'])],
            'area': match['area'], 'candidate_count': len(matches)}


def audit(actor: str, drawings: list[Drawing], *, complete: bool = True):
    sides = ['anatomical_right']
    if actor == 'iselin':
        sides.append('anatomical_left')
    report = {'actor': actor, 'measurements': [], 'violations': [], 'diagnostics': [],
              'occluded': ([] if actor == 'iselin' else ['anatomical_left_wrist_behind_shield'])}
    indices = [drawing.index for drawing in drawings]
    if complete and indices != list(range(48)):
        report['violations'].append({'check': 'complete_hand_cycle_coverage', 'indices': indices,
                                       'expected': '48 chronological drawings, indices 0 through 47'})
    if not drawings:
        report['violations'].append({'check': 'empty_hand_cycle'})
        return report
    for drawing in drawings:
        item = {'frame': drawing.index, 'source': drawing.source, 'sha256': drawing.digest, 'hands': {}}
        for side in sides:
            try:
                window = reviewed_window(actor, drawing, side)
                item['hands'][side] = measure(drawing, side, gloved=actor != 'iselin', window=window)
            except ValueError as error:
                report['violations'].append({'check': 'visible_hand_coverage', 'side': side,
                                               'frame': drawing.index, 'reason': str(error)})
        report['measurements'].append(item)
    for side in sides:
        points = [(row['frame'], row['hands'][side]['point_neck_relative'])
                  for row in report['measurements'] if side in row['hands']]
        if len(points) != len(drawings):
            continue
        ys = [point[1] for _, point in points]
        span = max(ys)-min(ys)
        if complete and span < MINIMUM_RANGE:
            report['violations'].append({'check': 'hand_pump_range', 'side': side,
                                           'pixels': round(span, 3), 'minimum': MINIMUM_RANGE})
        for (first, a), (second, b) in zip(points, points[1:]+points[:1]):
            if second != (first+1) % 48:
                continue
            distance = float(np.linalg.norm(np.asarray(b)-a))
            if distance > MAXIMUM_GROSS_STEP:
                report['violations'].append({'check': 'hand_gross_step', 'side': side,
                                               'frames': [first, second], 'pixels': round(distance, 3),
                                               'maximum': MAXIMUM_GROSS_STEP})
            if distance > DIAGNOSTIC_STEP:
                report['diagnostics'].append({'check': 'hand_step_review', 'side': side,
                                               'frames': [first, second], 'pixels': round(distance, 3),
                                               'review_above': DIAGNOSTIC_STEP})
    return report


def overlay(actor: str, drawings: list[Drawing], path: Path):
    report = audit(actor, drawings)
    sheet = Image.new('RGB', (320*8, 260*((len(drawings)+7)//8)), '#172436')
    for n, (drawing, row) in enumerate(zip(drawings, report['measurements'])):
        image = drawing.image.copy()
        pen = ImageDraw.Draw(image)
        for side, hand in row['hands'].items():
            x, y = hand['point_source']
            color = 'yellow' if side == 'anatomical_right' else 'red'
            pen.ellipse((x-10, y-10, x+10, y+10), outline=color, width=4)
        # One whole-image crop and uniform resampling for diagnostic presentation.
        nx, ny = drawing.neck
        box = (int(nx-255/drawing.scale), int(ny-20/drawing.scale),
               int(nx+255/drawing.scale), int(drawing.belt[1]+150/drawing.scale))
        image = image.crop(box)
        image.thumbnail((320, 235))
        x, y = (n % 8)*320, (n//8)*260
        sheet.paste(image, (x+(320-image.width)//2, y), image)
        ImageDraw.Draw(sheet).text((x+5, y+240), f'{drawing.index:02d} {drawing.digest[:10]}', fill='white')
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', action='store_true', help='Reject the retained real fist-jump pairs')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--overlays', type=Path)
    args = parser.parse_args()
    reports = []
    for actor in (('lucan', 'iselin') if args.before else ACTORS):
        drawings = (load_fixture(actor, ROOT/'tests/fixtures/prologue_hands/before')
                    if args.before else load_drawings(actor))
        report = audit(actor, drawings, complete=not args.before)
        reports.append(report)
        print(actor, json.dumps(report['violations']))
        if args.overlays:
            overlay(actor, drawings, args.overlays/f'{actor}_hands.jpg')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, indent=2)+'\n')
    return int(any(report['violations'] for report in reports))


if __name__ == '__main__':
    raise SystemExit(main())
