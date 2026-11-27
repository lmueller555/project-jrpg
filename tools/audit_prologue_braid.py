"""Measure Iselin's visible braid regions in actual painted RGB pixels.

The braid can lie over opaque clothing, so an alpha silhouette cannot establish
its continuity. Identity-reviewed, source-hash-bound free-end boxes select cool
light pixels; the statistic is their regional centroid, not an exact hair tip or
persistent material particle. Diffuse-end observations retain their uncertainty.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from tools.audit_prologue_motion import Drawing, ROOT, load_drawings, load_fixture
    from tools.prologue_motion_review import frame_identity, metric_context, find_reviewed_exception
except ModuleNotFoundError:
    from audit_prologue_motion import Drawing, ROOT, load_drawings, load_fixture
    from prologue_motion_review import frame_identity, metric_context, find_reviewed_exception


CONTRACT = ROOT / 'tests/fixtures/prologue_motion/braid_contract.json'


def exported_image(drawing: Drawing) -> Image.Image:
    """Reproduce uniform whole-figure sampling and rounded export translation."""
    source = drawing.image.copy()
    source.putalpha(source.getchannel('A').point(lambda a: 0 if a <= 16 else a))
    size = tuple(max(1, round(value * drawing.scale)) for value in source.size)
    sampled = source.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
    result = Image.new('RGBA', (1024, 1024))
    result.alpha_composite(sampled, tuple(round(value) for value in drawing.origin))
    return result


def selected_pixels(image: Image.Image, box: list[int], rule: dict) -> np.ndarray:
    """A reviewed distal region, not automatic braid/cuff classification."""
    rgba = np.asarray(image.crop(tuple(box))).astype(np.int16)
    red, green, blue, alpha = (rgba[:, :, index] for index in range(4))
    maximum = np.maximum(np.maximum(red, green), blue)
    minimum = np.minimum(np.minimum(red, green), blue)
    return ((alpha > rule['alpha_min']) & (red > rule['red_min'])
            & (green > rule['green_min']) & (blue > rule['blue_min'])
            & (blue + rule['warm_tolerance'] >= red)
            & (green + rule['warm_tolerance'] >= red)
            & (maximum - minimum < rule['maximum_chroma']))


def reviewed_view(drawing: Drawing, observation: dict, rendered: Image.Image | None = None) -> Image.Image:
    """Registered PNG fixtures deliberately use an exact identity transform.

    Premultiply/unpremultiply would round their already-exported edge colors.
    Raw complete sources still take the actual crop/scale/rounded-origin path.
    """
    identity_snapshot = (drawing.digest == observation.get('exported_snapshot_sha256')
                         and drawing.scale == 1 and drawing.origin == (0, 0)
                         and drawing.cell == (0, 0, *drawing.image.size)
                         and list(drawing.image.size) == observation['exported_size'])
    return drawing.image.copy() if identity_snapshot else (rendered or exported_image(drawing))


def observation_for(drawing: Drawing, contract: dict, *, rendered: Image.Image | None = None) -> dict | None:
    """Bind ROI approval to the actual exported pixels and neck registration."""
    for row in contract['observations']:
        if (row['frame'] != drawing.index
                or drawing.digest not in (row.get('source_sha256'), row.get('exported_snapshot_sha256'))):
            continue
        neck = [drawing.neck[index] * drawing.scale + round(drawing.origin[index]) for index in (0, 1)]
        if not np.allclose(neck, row['neck_exported'], rtol=0, atol=1e-6):
            continue
        image = reviewed_view(drawing, row, rendered)
        if (list(image.size) == row['exported_size']
                and sha256(image.tobytes()).hexdigest() == row['exported_pixels_sha256']):
            return row
    return None


def measure(drawing: Drawing, observation: dict, contract: dict,
            *, rendered: Image.Image | None = None) -> dict:
    image = reviewed_view(drawing, observation, rendered)
    box = observation['box_exported']
    selected = selected_pixels(image, box, contract['color_mask'])
    yy, xx = np.nonzero(selected)
    if len(xx) < contract['minimum_selected_pixels']:
        raise ValueError('Too few actual cool-light pixels in the reviewed visible braid region')
    point = [float(np.mean(xx) + box[0]), float(np.mean(yy) + box[1])]
    neck = [drawing.neck[index] * drawing.scale + round(drawing.origin[index]) for index in (0, 1)]
    return {'frame': drawing.index, 'source': drawing.source, 'sha256': drawing.digest,
            'box_exported': box, 'selected_pixels': len(xx),
            'centroid_exported': point,
            'centroid_neck_relative': [point[index] - neck[index] for index in (0, 1)],
            'visible_end_observation_uncertainty_px': observation['uncertainty_px'],
            'meaning': 'Centroid of actual selected distal-region pixels; not an exact tip or persistent particle.'}


def audit(drawings: list[Drawing], contract: dict | None = None, *, complete: bool = True) -> dict:
    contract = contract or json.loads(CONTRACT.read_text())
    report = {'actor': 'iselin', 'measurements': [], 'violations': [], 'diagnostics': [], 'unmeasured': [],
              'coverage': {'visible': 0, 'occluded_or_ambiguous': 0}}
    indices = [drawing.index for drawing in drawings]
    if complete and indices != list(range(48)):
        report['violations'].append({'check': 'complete_braid_cycle_coverage', 'indices': indices})
    if complete and contract['mask_review_state'] != 'reviewed':
        report['violations'].append({'check': 'braid_mask_identity_review_pending'})
    frames = {drawing.index: drawing for drawing in drawings}
    points = {}
    identities, observations = {}, {}
    for drawing in drawings:
        rendered = exported_image(drawing)
        observation = observation_for(drawing, contract, rendered=rendered)
        if observation is None:
            report['violations'].append({'check': 'reviewed_braid_observation_coverage',
                                          'frame': drawing.index, 'source': drawing.source,
                                          'sha256': drawing.digest})
            continue
        if observation['visibility'] != 'visible':
            report['coverage']['occluded_or_ambiguous'] += 1
            report['unmeasured'].append({'frame': drawing.index, 'visibility': observation['visibility'],
                                         'reason': observation.get('reason', 'No visible distal region measured.')})
            continue
        if not observation.get('pixel_identity_reviewed', False):
            report['violations'].append({'check': 'braid_pixel_identity_review_pending',
                                          'frame': drawing.index, 'sha256': drawing.digest})
        try:
            item = measure(drawing, observation, contract, rendered=rendered)
        except ValueError as error:
            report['violations'].append({'check': 'braid_visible_pixel_coverage',
                                          'frame': drawing.index, 'reason': str(error)})
            continue
        report['coverage']['visible'] += 1
        report['measurements'].append(item)
        points[drawing.index] = item['centroid_neck_relative']
        identities[drawing.index] = frame_identity(drawing, reviewed_view(drawing, observation, rendered))
        observations[drawing.index] = observation
    for first in range(48):
        second = (first + 1) % 48
        if first in points and second in points:
            distance = float(np.linalg.norm(np.asarray(points[second]) - points[first]))
            if distance > contract['maximum_region_centroid_step']:
                context = metric_context('braid_region_centroid', 'visible_distal_braid',
                    [identities[first], identities[second]],
                    {'color_mask': contract['color_mask'], 'minimum_selected_pixels': contract['minimum_selected_pixels'],
                     'boxes': [observations[first]['box_exported'], observations[second]['box_exported']],
                     'normalization': 'neck_relative', 'statistic_version': 1})
                review = find_reviewed_exception(contract.get('reviewed_metric_exceptions', []),
                    context=context, value=distance, default_limit=contract['maximum_region_centroid_step'])
                item = {'check': 'braid_region_step', 'frames': [first, second],
                        'pixels': round(distance, 3), 'limit': contract['maximum_region_centroid_step']}
                if review:
                    report['diagnostics'].append({**item, 'check': 'reviewed_braid_region_step',
                        'review_id': review['id'], 'maximum_reviewed_value': review['maximum_reviewed_value'],
                        'reason': review['reason']})
                else:
                    report['violations'].append({**item, 'review_context': context})
    for first, second in contract['required_visible_joins']:
        if first in frames and second in frames and (first not in points or second not in points):
            report['violations'].append({'check': 'required_braid_join_coverage', 'frames': [first, second]})
    if complete:
        values = list(points.values())
        excursion = (max(float(np.linalg.norm(np.asarray(point) - values[0])) for point in values)
                     if values else 0)
        report['maximum_centroid_excursion'] = round(excursion, 3)
        if excursion < contract['minimum_cycle_centroid_excursion']:
            report['violations'].append({'check': 'frozen_braid_region', 'pixels': round(excursion, 3),
                                          'minimum': contract['minimum_cycle_centroid_excursion']})
    return report


def overlay(drawings: list[Drawing], path: Path, contract: dict | None = None) -> None:
    """Tint the actual contributing pixels so material identity can be reviewed."""
    contract = contract or json.loads(CONTRACT.read_text())
    sheet = Image.new('RGB', (256 * min(8, len(drawings)), 320 * ((len(drawings) + 7) // 8)), '#777780')
    for tile_index, drawing in enumerate(drawings):
        image = exported_image(drawing)
        canvas = Image.new('RGB', image.size, '#777780')
        canvas.paste(image, (0, 0), image)
        observation = observation_for(drawing, contract, rendered=image)
        if observation:
            image = reviewed_view(drawing, observation, image)
            canvas = Image.new('RGB', image.size, '#777780')
            canvas.paste(image, (0, 0), image)
        if observation and observation['visibility'] == 'visible':
            box = observation['box_exported']
            selected = selected_pixels(image, box, contract['color_mask'])
            pixels = np.array(canvas)
            region = pixels[box[1]:box[3], box[0]:box[2]]
            region[selected] = np.rint(region[selected] * .35 + np.asarray([0, 255, 235]) * .65).astype(np.uint8)
            canvas = Image.fromarray(pixels)
            pen = ImageDraw.Draw(canvas)
            pen.rectangle(box, outline='yellow', width=1)
            if np.any(selected):
                yy, xx = np.nonzero(selected)
                x, y = float(np.mean(xx) + box[0]), float(np.mean(yy) + box[1])
                pen.ellipse((x - 4, y - 4, x + 4, y + 4), outline='red', width=2)
        crop = canvas.crop((500, 110, 820, 480))
        crop.thumbnail((256, 296))
        x, y = (tile_index % 8) * 256, (tile_index // 8) * 320
        sheet.paste(crop, (x, y + 20))
        ImageDraw.Draw(sheet).text((x + 5, y + 3), f'{drawing.index:02d} {drawing.digest[:10]}', fill='yellow')
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def rejected_groups() -> dict[str, list[Drawing]]:
    root = CONTRACT.parent
    raw = {drawing.index: drawing for drawing in load_fixture('iselin', root / 'braid_before')}
    original = load_fixture('iselin', root / 'braid_reach_before')
    late = load_fixture('iselin', root / 'braid_late_before')
    return {'rejected_10_11': [raw[10], raw[11]], 'original_rejected_14_15': original,
            'rejected_32_33': [raw[32], raw[33]], 'rejected_39_40': [raw[39], raw[40]],
            'late_rejected_38_39': late,
            'ordinary_31_32': [raw[31], raw[32]], 'ordinary_33_34': [raw[33], raw[34]]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--overlay', type=Path)
    args = parser.parse_args()
    groups = rejected_groups() if args.before else {'production': load_drawings('iselin')}
    reports = {}
    for name, drawings in groups.items():
        report = audit(drawings, complete=not args.before)
        reports[name] = report
        print(name + ': ' + json.dumps(report['violations']))
        if args.overlay:
            overlay(drawings, args.overlay / (name + '.png'))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, indent=2) + '\n')
    return int(any(report['violations'] for report in reports.values()))


if __name__ == '__main__':
    raise SystemExit(main())
