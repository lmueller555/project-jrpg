"""Reproduce the approved detailed gate approach without changing travel art.

All complete drawings and their original source lineage live in the source
pack. Whole-frame sampling and the documented stable head window reproduce the
approved R2 pixels directly at cinematic density, with no native-size stage.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/characters/iselin/cinematic_gate_left'
OUT = ROOT / 'assets/characters/iselin/cinematic/ground'
CANVAS = (80, 96)
ANCHOR = (40, 92)


def json_bytes(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def rgba(path):
    with Image.open(path) as original:
        return original.convert('RGBA')


def source_path(name):
    path = (SOURCE / name).resolve()
    if not path.is_relative_to(SOURCE.resolve()):
        raise ValueError('Detailed gate source leaves its pack: ' + name)
    return path


def drawing(record, label, preservation=None):
    """Register one complete pose; never fit pose bounds or separate limbs."""
    if 'image' in record:
        path = source_path(record['image'])
        image = rgba(path)
        if image.size != CANVAS:
            raise ValueError('Reused detailed drawing has the wrong canvas: ' + label)
        registration = {'complete_image': record['image'],
                        'source_sha256': sha256(path.read_bytes()).hexdigest()}
    else:
        path = source_path(record['source'])
        original = rgba(path)
        x, y, width, height = record['rect']
        if (min(x, y) < 0 or min(width, height) <= 0
                or x + width > original.width or y + height > original.height):
            raise ValueError('Detailed source crop leaves its master: ' + label)
        crop = original.crop((x, y, x + width, y + height))
        crop.putalpha(crop.getchannel('A').point(lambda value: 255 if value >= 220 else 0))
        scale = record['scale']
        if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
            raise ValueError('Detailed source density must be finite and positive')
        size = (round(width * scale), round(height * scale))
        sampled = crop.resize(size, Image.Resampling.NEAREST)
        source_anchor = record['source_anchor']
        origin = tuple(round(ANCHOR[i] - source_anchor[i] * scale) for i in range(2))
        bounds = sampled.getbbox()
        if (bounds is None or bounds[0] + origin[0] < 0 or bounds[1] + origin[1] < 0
                or bounds[2] + origin[0] > CANVAS[0] or bounds[3] + origin[1] > CANVAS[1]):
            raise ValueError(('Detailed whole drawing would clip', label, bounds, origin))
        image = Image.new('RGBA', CANVAS)
        image.alpha_composite(sampled, origin)
        registration = {'source': record['source'],
                        'source_sha256': sha256(path.read_bytes()).hexdigest(),
                        'source_rect_xywh': record['rect'], 'uniform_scale': scale,
                        'source_anchor': source_anchor, 'sample_size': list(size),
                        'origin': list(origin)}
    registration['before_preservation_rgba_sha256'] = sha256(image.tobytes()).hexdigest()
    if preservation is not None and record.get('preserve_head', True):
        path = source_path(preservation['image'])
        protected = rgba(path)
        if protected.size != CANVAS:
            raise ValueError('Protected detailed head has the wrong camera canvas')
        px, py, pw, ph = preservation['rect']
        if min(px, py) < 0 or min(pw, ph) <= 0 or px + pw > 80 or py + ph > 96:
            raise ValueError('Protected detailed head leaves the camera canvas')
        window = (px, py, px + pw, py + ph)
        image.paste(protected.crop(window), (px, py))
        registration['protected_high_resolution_region'] = {
            'image': preservation['image'], 'source_sha256': sha256(path.read_bytes()).hexdigest(),
            'rect_xywh': preservation['rect'],
            'rgba_sha256': sha256(protected.crop(window).tobytes()).hexdigest()}
    if image.getbbox() is None or not set(image.tobytes()[3::4]) <= {0, 255}:
        raise ValueError('Detailed gate drawing must have visible hard-alpha artwork: ' + label)
    registration.update({'camera_canvas': list(CANVAS), 'camera_anchor': list(ANCHOR),
                         'opaque_bounds': list(image.getbbox()),
                         'rgba_sha256': sha256(image.tobytes()).hexdigest()})
    return image, registration


def verify_sources(approval):
    for name, expected in approval['source_sha256'].items():
        if sha256(source_path(name).read_bytes()).hexdigest() != expected:
            raise ValueError('Approved detailed source changed: ' + name)
    # The complete reused camera PNGs remain traceable to unchanged generated
    # masters. Validate that lineage independently of the protected-head pass.
    lineage = json.loads((SOURCE / 'lineage.json').read_text())
    for name, record in lineage['records'].items():
        image, _ = drawing(record, name)
        reference = rgba(source_path(name))
        if image.tobytes() != reference.tobytes():
            raise ValueError('Reused complete drawing differs from its source lineage: ' + name)


def products():
    """Return production PNG/provenance outputs and a manifest merge piece.

    The caller owns the combined actor manifest. Generic travel loops and
    unrelated poses are deliberately absent from this gate-only merge piece.
    """
    recipe_path = SOURCE / 'recipe.json'
    approval_path = SOURCE / 'approval.json'
    approval = json.loads(approval_path.read_text())
    if (approval.get('version') != 1 or approval['camera_canvas'] != list(CANVAS)
            or approval['camera_anchor'] != list(ANCHOR) or len(approval['files']) != 25):
        raise ValueError('Detailed gate approval must preserve all 25 cinematic drawings')
    verify_sources(approval)
    recipe = json.loads(recipe_path.read_text())
    if (recipe.get('version') != 2 or len(recipe.get('walk_left', [])) != 16
            or len(recipe.get('stop_left', [])) != 8):
        raise ValueError('Detailed gate needs sixteen approaches and eight stopping drawings')
    records = [('gate_stand_left.png', recipe['stand_left'])]
    records += [(f'gate_walk_left/frame_{index + 1:02}.png', record)
                for index, record in enumerate(recipe['walk_left'])]
    records += [(f'stop_left/frame_{index + 1:02}.png', record)
                for index, record in enumerate(recipe['stop_left'])]
    outputs, registrations, grids = {}, {}, {}
    for name, record in records:
        if 'source' in record:
            grid = (record['scale'], tuple(record['source_anchor']), tuple(record['rect'][2:]))
            if record['source'] in grids and grids[record['source']] != grid:
                raise ValueError('Detailed body density or anchor varies within a master')
            grids[record['source']] = grid
        image, registration = drawing(record, name, recipe['head_preservation'])
        stream = io.BytesIO()
        image.save(stream, format='PNG', optimize=True)
        data = stream.getvalue()
        path = OUT / name
        key = path.relative_to(ROOT).as_posix()
        expected = approval['files'][key]
        # Preserve the approved encoding across Pillow/zlib versions when the
        # freshly reproduced pixels and the committed PNG are both exact.
        if (path.is_file()
                and sha256(path.read_bytes()).hexdigest() == expected['approved_file_sha256']
                and rgba(path).tobytes() == image.tobytes()):
            data = path.read_bytes()
        if (sha256(data).hexdigest() != expected['approved_file_sha256']
                or sha256(image.tobytes()).hexdigest() != expected['approved_rgba_sha256']):
            raise ValueError('Detailed gate drawing differs from approved R2: ' + key)
        outputs[path] = data
        registrations[name] = registration
    if {path.relative_to(ROOT).as_posix() for path in outputs} != set(approval['files']):
        raise ValueError('Detailed gate approval and production drawings differ')
    if outputs[OUT / 'gate_stand_left.png'] != outputs[OUT / 'stop_left/frame_08.png']:
        raise ValueError('Detailed final whole stopping pose must equal its standing idle')
    timing = approval['stop_timing_ms']
    if (approval['walk_frame_ms'] != [35] * 16
            or timing != {'handoff': 40, 'frames': [60] * 8,
                          'hold': 60, 'recovery': 120, 'total': 700}):
        raise ValueError('Approved detailed gate timing changed')
    piece = {
        'poses': {'gate_stand_left': 'gate_stand_left.png'},
        'loops': {'gate_walk_left': [
            {'file': f'gate_walk_left/frame_{index + 1:02}.png', 'duration_ms': duration}
            for index, duration in enumerate(approval['walk_frame_ms'])],
            # The first eight approved poses close a compact incoming cycle.
            # Keep the later stop anticipation out of the aerial lead-in.
            'gate_incoming_left': [
                {'file': f'gate_walk_left/frame_{index + 1:02}.png', 'duration_ms': duration}
                for index, duration in enumerate(approval['walk_frame_ms'][:8])]},
        'actions': {'stop_left': {
            'entry': [{'file': 'gate_walk_left/frame_16.png', 'duration_ms': timing['handoff']}]
                + [{'file': f'stop_left/frame_{index + 1:02}.png', 'duration_ms': duration}
                   for index, duration in enumerate(timing['frames'])],
            'hold': {'file': 'stop_left/frame_08.png', 'duration_ms': timing['hold']},
            'recovery': [{'pose': 'gate_stand_left', 'duration_ms': timing['recovery']}],
            'rest_pose': 'gate_stand_left'}},
        'gaits': {'gate_walk_left': {'stride_pixels': 32},
                  'gate_incoming_left': {'stride_pixels': 16}},
    }
    outputs[SOURCE / 'registration.json'] = json_bytes({
        'generation_tool': 'image_gen.imagegen',
        'approval_sha256': sha256(approval_path.read_bytes()).hexdigest(),
        'recipe_sha256': sha256(recipe_path.read_bytes()).hexdigest(),
        'camera_canvas': list(CANVAS), 'camera_anchor': list(ANCHOR),
        'construction': 'Approved complete detailed gate drawings, fixed whole-master sampling and a documented stable high-resolution head window. No native-size intermediate, separate-limb assembly or per-foot fitting.',
        'scope': 'Gate approach, stop and settled idle; generic travel loops are separate.',
        'records': registrations, 'manifest_piece': piece,
        'exports': {path.relative_to(ROOT).as_posix(): sha256(data).hexdigest()
                    for path, data in outputs.items()}})
    return outputs, piece


def build(check=False):
    outputs, _ = products()
    changed = [path.relative_to(ROOT).as_posix() for path, data in outputs.items()
               if not path.exists() or path.read_bytes() != data]
    if check and changed:
        raise SystemExit('Stale approved detailed gate exports: ' + ', '.join(changed))
    if not check:
        for path, data in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    result = build(parser.parse_args().check)
    print(f'Verified approved detailed gate: {len(result)} production/provenance products')
