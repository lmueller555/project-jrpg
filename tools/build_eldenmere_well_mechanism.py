"""Export additive staged well-mechanism parts; never write the live town.

Mechanical primitives are authored at native density from the source geometry.
The crank, winding marks and rope are rigid objects, not a character limb rig.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'assets/source/terrain/eldenmere/well_hd/mechanism/art_recipe.json'
PACK = 'assets/terrain/eldenmere/well_hd/mechanism'


def document(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def read(path):
    return json.loads((ROOT/path).read_text())


def digest(raw):
    return sha256(raw).hexdigest()


def clean_path(path):
    value = Path(path)
    if value.is_absolute() or '..' in value.parts:
        raise ValueError('Mechanism exports must remain within their pack')
    return value.as_posix()


def products():
    raw = (ROOT/SOURCE).read_bytes(); recipe = json.loads(raw)
    base = read(recipe['base_pack'])
    contract_raw = (ROOT/recipe['contract']).read_bytes()
    contract = json.loads(contract_raw)
    if recipe['version'] != 1 or recipe['integration_status'] != 'staged':
        raise ValueError('Only the staged mechanism pack is owned here')
    density = recipe['artwork_pixels_per_world_pixel']
    size = tuple(recipe['artwork_size'])
    if density != 2 or list(size) != [2*v for v in recipe['logical_size']]:
        raise ValueError('Native mechanism registration changed')
    if list(size) != base['assembly']['artwork_size']:
        raise ValueError('Mechanism and retained structure canvases disagree')
    palette = recipe['palette']
    output, exports = {}, []

    def png(relative, image, role):
        relative = clean_path(relative)
        buffer = BytesIO(); image.save(buffer, format='PNG')
        encoded = buffer.getvalue()
        path = PACK+'/'+relative
        if path in output:
            raise ValueError('Duplicate mechanism export')
        output[path] = encoded
        exports.append({'file': relative, 'artwork_size': list(image.size),
                        'mode': image.mode, 'role': role, 'sha256': digest(encoded)})
        return relative

    def image():
        return Image.new('RGBA', size)

    def line(draw, points, color, width=1):
        draw.line([(round(x*density), round(y*density)) for x, y in points], fill=palette[color], width=width)

    crank = recipe['crank']; pivot = crank['pivot_logical']; radii = crank['radii_logical']
    base_pivot = base['geometry']['anchors_logical']['crank_pivot']
    if (pivot != base_pivot or pivot != contract['geometry']['crank_pivot_local']
            or radii != contract['geometry']['crank_radii_local']):
        raise ValueError('Crank axle must retain the shared geometry pivot')
    frames = []
    for sample in range(crank['samples']):
        angle = sample*math.tau/crank['samples']
        handle = [pivot[0]+radii[0]*math.cos(angle), pivot[1]+radii[1]*math.sin(angle)]
        part = image(); draw = ImageDraw.Draw(part)
        line(draw, [pivot, handle], 'contour', crank['arm_width_artwork']+2)
        line(draw, [pivot, handle], 'iron', crank['arm_width_artwork'])
        px, py = (round(v*density) for v in pivot)
        draw.ellipse((px-3, py-3, px+3, py+3), fill=palette['iron_dark'], outline=palette['contour'])
        draw.line((px-1, py-1, px+1, py-1), fill=palette['iron_light'])
        hx, hy = (round(v*density) for v in handle)
        draw.rounded_rectangle((hx-1, hy-2, hx+5, hy+2), radius=1, fill=palette['wood'], outline=palette['contour'])
        draw.line((hx+1, hy-1, hx+3, hy-1), fill=palette['wood_light'])
        path = png(f'crank/frame_{sample:02}.png', part, 'rigid_centered_crank')
        frames.append({'sample': sample, 'phase': sample/crank['samples'], 'handle_logical': handle, 'file': path})

    spindle_record = next(item for item in base['layers'] if item['id'] == 'windlass')
    spindle_alpha = Image.open(ROOT/Path(recipe['base_pack']).parent/spindle_record['file']).convert('RGBA').getchannel('A')
    spindle_frames = []
    for sample in range(crank['samples']):
        part = image(); draw = ImageDraw.Draw(part)
        phase = sample*math.tau/crank['samples']
        center = recipe['spindle']['center_logical']
        cy = center[1]+1.4*math.sin(phase)
        line(draw, [(center[0]-1.7, cy-.5), (center[0]-.5, cy+.4), (center[0]+1, cy-.1)],
             'wood_light' if math.cos(phase) >= 0 else 'wood_dark')
        part.putalpha(ImageChops.multiply(part.getchannel('A'), spindle_alpha))
        spindle_frames.append(png(f'spindle/frame_{sample:02}.png', part, 'phase_locked_winding_marks'))

    hook = recipe['hook']; hook_image = Image.new('RGBA', tuple(hook['artwork_size']))
    rope_offset = [(hook['rope_anchor_artwork'][i]-hook['attachment_anchor_artwork'][i])/density for i in (0, 1)]
    if rope_offset != contract['geometry']['hook_rope_offset_logical']:
        raise ValueError('The hook drawing and controller rope endpoint disagree')
    draw = ImageDraw.Draw(hook_image); points = [tuple(p) for p in hook['points_artwork']]
    draw.line(points, fill=palette['contour'], width=3)
    draw.line(points, fill=palette['iron_light'], width=1)
    hook_path = png('hook.png', hook_image, 'hook_attachment')

    rope_swatch = Image.new('RGBA', (6, 32)); draw = ImageDraw.Draw(rope_swatch)
    draw.line((3, 0, 3, 31), fill=palette['rope_dark'], width=recipe['rope']['outline_width_artwork'])
    draw.line((3, 0, 3, 31), fill=palette['rope_light'], width=recipe['rope']['strand_width_artwork'])
    png('rope_reference.png', rope_swatch, 'native_rope_material_reference')

    water_mask = Image.open(ROOT/recipe['water']['mask']).convert('L')
    water_frames, contact_frames = [], []
    for phase in range(recipe['water']['ambient_frames']):
        part = image(); draw = ImageDraw.Draw(part)
        # Small, intentionally authored glint clusters across the retained surface.
        clusters = ((31+phase*.5, 67), (39-phase*.5, 71), (35+(phase % 3), 64.5))
        for n, (x, y) in enumerate(clusters):
            line(draw, [(x-1.5, y), (x+1, y)], 'reflection' if n else 'glint')
            if n == 1: line(draw, [(x-1, y+.5), (x, y+.5)], 'water')
        part.putalpha(ImageChops.multiply(part.getchannel('A'), water_mask))
        water_frames.append(png(f'water/ambient_{phase:02}.png', part, 'masked_ambient_water'))
    for phase in range(recipe['water']['contact_frames']):
        part = image(); draw = ImageDraw.Draw(part)
        rx, ry = 2+phase*.7, .7+phase*.25
        cx, cy = 36, 69
        box = tuple(round(v*density) for v in (cx-rx, cy-ry, cx+rx, cy+ry))
        draw.arc(box, 8, 164, fill=palette['reflection'], width=1)
        draw.arc(box, 194, 340, fill=palette['water'], width=1)
        if phase < 3:
            line(draw, [(cx-2, cy-1.5-phase*.4), (cx-1.5, cy-.5-phase*.4)], 'glint')
            line(draw, [(cx+2, cy-1-phase*.3), (cx+2.5, cy-phase*.3)], 'reflection')
        part.putalpha(ImageChops.multiply(part.getchannel('A'), water_mask))
        contact_frames.append(png(f'water/contact_{phase:02}.png', part, 'masked_water_contact'))

    # A density-aware visual footprint for tests and downstream composition.
    crank_mask = Image.new('L', size)
    for record in frames:
        frame = Image.open(BytesIO(output[PACK+'/'+record['file']])).convert('RGBA')
        crank_mask = ImageChops.lighter(crank_mask, frame.getchannel('A'))
    mask_path = png('masks/crank_coverage.png', crank_mask, 'crank_coverage_mask')
    spindle_mask = Image.new('L', size)
    for path in spindle_frames:
        frame = Image.open(BytesIO(output[PACK+'/'+path])).convert('RGBA')
        spindle_mask = ImageChops.lighter(spindle_mask, frame.getchannel('A'))
    spindle_mask_path = png('masks/spindle_coverage.png', spindle_mask, 'spindle_coverage_mask')
    sources = {
        SOURCE: digest(raw), recipe['contract']: digest(contract_raw),
        recipe['base_pack']: digest((ROOT/recipe['base_pack']).read_bytes()),
        recipe['water']['mask']: digest((ROOT/recipe['water']['mask']).read_bytes()),
    }
    manifest = {
        'version': 1, 'id': recipe['id'], 'integration_status': 'staged',
        'runtime_activation': False, 'visual_approval': 'pending_user_review',
        'artwork_pixels_per_world_pixel': density, 'logical_size': recipe['logical_size'],
        'artwork_size': recipe['artwork_size'], 'source': SOURCE,
        'source_sha256': digest(raw), 'contract': recipe['contract'],
        'contract_sha256': digest(contract_raw),
        'contract_schema_version': contract.get('schema_version', contract.get('version', 1)),
        'base_pack': recipe['base_pack'], 'sources': sources,
        'exporter': 'tools/build_eldenmere_well_mechanism.py',
        'exporter_sha256': digest(Path(__file__).read_bytes()),
        'crank': {'pivot_logical': pivot, 'radii_logical': radii, 'frames': frames, 'coverage_mask': mask_path},
        'spindle': {'frames': spindle_frames, 'coverage_mask': spindle_mask_path},
        'hook': {**hook, 'file': hook_path}, 'rope': recipe['rope'], 'palette': palette,
        'water': {'ambient_frames': water_frames, 'contact_frames': contact_frames,
                  'frame_duration_ms': recipe['water']['ambient_frame_duration_ms'],
                  'mask': recipe['water']['mask']}, 'cache': recipe['cache'],
        'exports': exports,
        'limits': 'Additive staged components. The live well, actor and town are unchanged; PR4 owns gameplay activation.',
    }
    output[PACK+'/manifest.json'] = document(manifest)
    return output


def build(check=False):
    output = products()
    stale = [path for path, raw in output.items() if not (ROOT/path).is_file() or (ROOT/path).read_bytes() != raw]
    if check and stale:
        raise SystemExit('Stale well mechanism exports: '+', '.join(stale))
    if not check:
        for path, raw in output.items():
            target = ROOT/path
            if not target.is_file() or target.read_bytes() != raw:
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    print(f'{len(output)} staged well mechanism exports '+('verified' if check else 'built'))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
