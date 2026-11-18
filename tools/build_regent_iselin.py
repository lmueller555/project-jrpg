"""Export Iselin scene drawings at their retained camera sizes.

Approved ordinary idles/walks remain pixel-exact inputs. Complete scene sources
register on a native grid before uniform nearest-neighbor camera presentation;
no predecessor artwork or detached-limb animation constructs these exports.
The approved detailed gate performance is authored directly on the 80x96 grid.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_mira_combat import _main_component
from tools.export_iselin_gate_detail import products as gate_detail_products

SOURCE = ROOT / 'assets/source/characters/iselin/native_scene_work'
GROUND = ROOT / 'assets/story/regent_arrival/actors/iselin'
AERIAL = ROOT / 'assets/story/regent_aerial/actors/iselin'
NATIVE = ROOT / 'assets/characters/iselin'
GROUND_SCALE = 80 / 34
GROUND_CANVAS, GROUND_ANCHOR = (80, 96), (40, 92)
NATIVE_GROUND_ANCHOR = (12, 34)
AERIAL_SCALE = 1.5
AERIAL_CANVAS, AERIAL_ANCHOR = (48, 64), (24, 56)
NATIVE_AERIAL_ANCHOR = (8, 22)
AERIAL_BOUNDS = (14, 28, 34, 56)


def png(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def json_bytes(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def _stable_png(path, image):
    if path.exists():
        previous = Image.open(path).convert('RGBA')
        if previous.size == image.size and previous.tobytes() == image.tobytes():
            return path.read_bytes()
    return png(image)


def _check_fits(image, origin, canvas, label):
    bounds = image.getbbox()
    if bounds is None:
        raise ValueError('Empty authored drawing: ' + label)
    if (bounds[0] + origin[0] < 0 or bounds[1] + origin[1] < 0
            or bounds[2] + origin[0] > canvas[0]
            or bounds[3] + origin[1] > canvas[1]):
        raise ValueError(('Clipped complete drawing', label, list(bounds), origin, canvas))


def native_drawing(record, label):
    """Register a whole source crop from explicit body anchors and density.

    Rects are [x,y,width,height]; source anchors are local to that crop. Scale
    comes from the authored body grid, never the current foot/pose bounds.
    """
    source_label = record.get('approved_image', record.get('source'))
    path = ROOT / source_label if 'approved_image' in record else SOURCE / source_label
    image = Image.open(path).convert('RGBA')
    rect = record.get('rect', [0, 0, image.width, image.height])
    x, y, width, height = rect
    image = image.crop((x, y, x + width, y + height))
    image.putalpha(image.getchannel('A').point(lambda value: 255 if value >= 220 else 0))
    if not record.get('native', False):
        image = _main_component(image)
    canvas = tuple(record.get('canvas', [24, 36]))
    scale = float(record.get('scale', 1))
    if scale <= 0:
        raise ValueError('Source density must be positive: ' + label)
    source_anchor = record.get('source_anchor', [0, 0])
    destination_anchor = record.get('destination_anchor', [0, 0])
    size = (round(image.width * scale), round(image.height * scale))
    sampled = image.resize(size, Image.Resampling.NEAREST)
    origin = tuple(round(destination_anchor[i] - source_anchor[i] * scale) for i in range(2))
    _check_fits(sampled, origin, canvas, label)
    result = Image.new('RGBA', canvas)
    result.alpha_composite(sampled, origin)
    preservation = record.get('preserve')
    if preservation:
        accepted_path = ROOT / preservation['image']
        accepted = Image.open(accepted_path).convert('RGBA')
        px, py, pw, ph = preservation['rect']
        destination = tuple(preservation.get('destination', [px, py]))
        if (min(destination) < 0 or destination[0] + pw > canvas[0]
                or destination[1] + ph > canvas[1]):
            raise ValueError('Protected region would clip: ' + label)
        result.paste(accepted.crop((px, py, px + pw, py + ph)), destination)
    return result, {'source': source_label, 'source_sha256': sha256(path.read_bytes()).hexdigest(),
                    'source_rect_xywh': rect, 'source_anchor': source_anchor,
                    'destination_anchor': destination_anchor, 'uniform_scale': scale,
                    'sample_size': list(size), 'origin': list(origin), 'canvas': list(canvas),
                    'opaque_bounds': list(result.getbbox()),
                    'native_rgba_sha256': sha256(result.tobytes()).hexdigest(), 'preserve': preservation}


def presentation(image, scale, canvas, source_anchor, destination_anchor, label):
    size = (round(image.width * scale), round(image.height * scale))
    sampled = image.resize(size, Image.Resampling.NEAREST)
    origin = tuple(round(destination_anchor[i] - source_anchor[i] * scale) for i in range(2))
    _check_fits(sampled, origin, canvas, label)
    result = Image.new('RGBA', canvas)
    result.alpha_composite(sampled, origin)
    return result


def ground_presentation(image, label):
    if image.size != (24, 36):
        raise ValueError(('Expected native ground drawing', label, image.size))
    return presentation(image, GROUND_SCALE, GROUND_CANVAS,
                        NATIVE_GROUND_ANCHOR, GROUND_ANCHOR, label)


def products():
    specification_path = SOURCE / 'scene_art.json'
    specification = json.loads(specification_path.read_text())
    outputs, records, dependencies, authored = {}, {}, {}, {}
    for name in ('listen_left', 'gesture_left', 'turn_left_back', 'seated_left', 'overhead', 'oblique'):
        image, record = native_drawing(specification['poses'][name], name)
        expected = (16, 24) if name in ('overhead', 'oblique') else (24, 36)
        if image.size != expected:
            raise ValueError(('Wrong native canvas', name, image.size, expected))
        authored[name], records[name] = image, record
    poses = {name: ground_presentation(authored[name], name)
             for name in ('listen_left', 'gesture_left', 'turn_left_back')}
    for direction in ('left', 'right', 'back'):
        path = NATIVE / 'native_idles' / f'idle_{direction}.png'
        image = Image.open(path).convert('RGBA')
        dependencies[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
        poses['stand_' + direction] = ground_presentation(image, 'stand_' + direction)
    loops = {}
    for direction in ('left', 'back'):
        loop = []
        for index in range(16):
            path = NATIVE / ('native_walk_' + direction) / f'frame_{index + 1:02}.png'
            dependencies[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
            name = f'walk_{direction}_{index:02}.png'
            image = Image.open(path).convert('RGBA')
            outputs[GROUND / name] = _stable_png(GROUND / name, ground_presentation(image, name))
            loop.append({'file': name, 'duration_ms': 35})
        loops['walk_' + direction] = loop
    if len(specification['diagonal']) != 16:
        raise ValueError('The diagonal scene walk needs sixteen complete drawings')
    diagonal, records['diagonal'] = [], []
    for index, entry in enumerate(specification['diagonal']):
        name = f'walk_left_back_{index:02}.png'
        image, record = native_drawing(entry, name)
        if entry.get('preserve_native_pose'):
            pose_name = entry['preserve_native_pose']
            x, y, width, height = entry.get('preserve_rect', [0, 0, 24, 12])
            accepted = authored[pose_name].crop((x, y, x + width, y + height))
            image.paste(accepted, (x, y))
            record['protected_native_pose'] = {'name': pose_name, 'rect_xywh': [x, y, width, height],
                                                'rgba_sha256': sha256(accepted.tobytes()).hexdigest()}
            record['native_rgba_sha256'] = sha256(image.tobytes()).hexdigest()
        outputs[GROUND / name] = _stable_png(GROUND / name, ground_presentation(image, name))
        diagonal.append({'file': name, 'duration_ms': 35})
        records['diagonal'].append(record)
    loops['walk_left_back'] = diagonal
    for name, image in poses.items():
        outputs[GROUND / (name + '.png')] = _stable_png(GROUND / (name + '.png'), image)
    gate_outputs, gate = gate_detail_products()
    outputs.update(gate_outputs)
    outputs[GROUND / 'animation.json'] = json_bytes({
        'version': 1, 'canvas': list(GROUND_CANVAS), 'anchor': list(GROUND_ANCHOR),
        'poses': {**{name: name + '.png' for name in poses}, **gate['poses']},
        'loops': {**loops, **gate['loops']}, 'actions': gate['actions'],
        'gaits': {'walk_left': {'stride_pixels': 32}, **gate['gaits']},
        'detailed_performances': {'gate_stop': {
            'canvas': list(GROUND_CANVAS), 'anchor': list(GROUND_ANCHOR),
            'source': 'assets/source/characters/iselin/cinematic_gate_left/approval.json',
            'loop': 'gate_walk_left', 'rest_pose': 'gate_stand_left',
            'scope': 'Gate approach, stop, greeting and initial admission wait; not a generic travel loop.'}},
        'native_canvas': [24, 36], 'native_ground_anchor': list(NATIVE_GROUND_ANCHOR),
        'camera_scale': GROUND_SCALE,
        'source': 'Native-derived generic travel and scene poses, plus the approved directly authored 80x96 gate approach, stop and idle. Native metadata applies to the generic poses; detailed_performances records the gate exception.'})
    seated = ROOT / 'assets/story/regent/poses/iselin_seated.png'
    outputs[seated] = _stable_png(seated, authored['seated_left'])
    for name in ('overhead', 'oblique'):
        image = presentation(authored[name], AERIAL_SCALE, AERIAL_CANVAS,
                             NATIVE_AERIAL_ANCHOR, AERIAL_ANCHOR, name)
        bounds = image.getbbox()
        if (bounds[0] < AERIAL_BOUNDS[0] or bounds[1] < AERIAL_BOUNDS[1]
                or bounds[2] > AERIAL_BOUNDS[2] or bounds[3] > AERIAL_BOUNDS[3]):
            raise ValueError(('Aerial silhouette leaves retained crop', name, bounds, AERIAL_BOUNDS))
        outputs[AERIAL / (name + '.png')] = _stable_png(AERIAL / (name + '.png'), image)
    outputs[AERIAL / 'animation.json'] = json_bytes({
        'version': 1, 'canvas': list(AERIAL_CANVAS), 'anchor': list(AERIAL_ANCHOR),
        'poses': {'overhead': 'overhead.png', 'oblique': 'oblique.png'}, 'loops': {},
        'overhead_facing': 'north', 'oblique_facing': 'northwest',
        'native_canvas': [16, 24], 'native_ground_anchor': list(NATIVE_AERIAL_ANCHOR),
        'camera_scale': AERIAL_SCALE,
        'source': 'Native complete Iselin overhead/oblique drawings; uniform nearest-neighbor aerial presentation.'})
    outputs[SOURCE / 'registration.json'] = json_bytes({
        'generation_tool': 'image_gen.imagegen',
        'specification_sha256': sha256(specification_path.read_bytes()).hexdigest(),
        'native_ground_canvas': [24, 36], 'native_ground_anchor': list(NATIVE_GROUND_ANCHOR),
        'ground_camera_canvas': list(GROUND_CANVAS), 'ground_camera_anchor': list(GROUND_ANCHOR),
        'ground_camera_scale': GROUND_SCALE, 'aerial_camera_scale': AERIAL_SCALE,
        'aerial_crop': list(AERIAL_BOUNDS), 'records': records,
        'approved_asset_dependencies': dependencies,
        'construction': 'Complete native generic poses and diagonal cycle with uniform camera presentation; the separately registered approved 80x96 gate performance is exported directly. No predecessor art or limb assembly.',
        'exports': {str(path.relative_to(ROOT)): sha256(data).hexdigest()
                    for path, data in outputs.items()}})
    return outputs


def build(check=False):
    output = products()
    changed = [str(path.relative_to(ROOT)) for path, data in output.items()
               if not path.exists() or path.read_bytes() != data]
    if check and changed:
        raise SystemExit('Stale Iselin scene exports: ' + ', '.join(changed))
    if not check:
        for path, data in output.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
