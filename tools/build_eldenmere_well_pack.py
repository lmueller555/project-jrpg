"""Export the staged well/pail drawings without touching any live town owner.

Source polygons name real structural boundaries in one uniformly registered
master. They partition its pixels; no layer is independently fitted or stretched.
The later mechanism, actor and integration PRs own motion and activation.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RECIPE = 'assets/source/terrain/eldenmere/well_hd/recipe.json'
PACK = 'assets/terrain/eldenmere/well_hd'


def document(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def digest(raw):
    return sha256(raw).hexdigest()


def relative_file(value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Pack paths must remain relative to their owner')
    return path.as_posix()


def normalized_master(record, threshold):
    path = ROOT / Path(RECIPE).parent / relative_file(record['file'])
    raw = path.read_bytes()
    if digest(raw) != record['sha256']:
        raise ValueError('Changed source master: '+record['file'])
    with Image.open(BytesIO(raw)) as source:
        image = source.convert('RGBA')
    if list(image.size) != record['source_artwork_size']:
        raise ValueError('Source master dimensions changed')
    crop = record['crop_artwork']; width, height = record['resize_artwork']
    scale = width/(crop[2]-crop[0])
    if abs(height-(crop[3]-crop[1])*scale) > 1:
        raise ValueError('Normalization must use a uniform whole-master scale')
    if record['resampling'] != 'nearest':
        raise ValueError('Native pixel artwork requires nearest sampling')
    image.putalpha(image.getchannel('A').point(lambda a: 255 if a >= threshold else 0))
    image = image.crop(tuple(crop)).resize((width, height), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', tuple(record['canvas_artwork']))
    x, y = record['offset_artwork']
    if min(x, y) < 0 or x+width > canvas.width or y+height > canvas.height:
        raise ValueError('Normalized master leaves its canvas')
    canvas.alpha_composite(image, (x, y))
    return canvas


def masks_for(records, image):
    result = {}
    alpha = image.getchannel('A')
    for record in records:
        name = record['id']
        if name in result or record['space'] != 'artwork':
            raise ValueError('Duplicate mask or undeclared coordinate space')
        mask = Image.new('L', image.size)
        draw = ImageDraw.Draw(mask)
        shape = record['shape']
        if shape == 'polygon':
            draw.polygon([tuple(point) for point in record['points']], fill=255)
        elif shape == 'multipolygon':
            for points in record['polygons']:
                draw.polygon([tuple(point) for point in points], fill=255)
        elif shape == 'ellipse':
            draw.ellipse(tuple(record['box']), fill=255)
        elif shape == 'rectangles':
            for x0, y0, x1, y1 in record['boxes']:
                draw.rectangle((x0, y0, x1-1, y1-1), fill=255)
        elif shape == 'source_alpha_remainder':
            mask = alpha.copy()
        else:
            raise ValueError('Unsupported authored mask shape: '+shape)
        if record.get('clip_to_source_alpha'):
            mask = ImageChops.multiply(mask, alpha)
        for other in record.get('intersection', []):
            mask = ImageChops.multiply(mask, result[other])
        for other in record.get('subtract', []):
            mask = ImageChops.subtract(mask, result[other])
        if mask.getbbox() is None:
            raise ValueError('Empty authored mask: '+name)
        result[name] = mask
    return result


def masked(image, mask):
    result = image.copy()
    result.putalpha(ImageChops.multiply(image.getchannel('A'), mask))
    # Deterministic transparent RGB avoids phantom color in technical consumers.
    transparent = Image.new('RGBA', image.size)
    transparent.paste(result, (0, 0), result.getchannel('A'))
    return transparent


def products():
    raw_recipe = (ROOT/RECIPE).read_bytes()
    recipe = json.loads(raw_recipe)
    if (recipe['schema_version'] != 1 or recipe['status'] != 'staged'
            or recipe['artwork_pixels_per_world_pixel'] != 2
            or any(recipe['activation'].values())):
        raise ValueError('This exporter owns only the staged PR1 native asset bank')
    well, pail = recipe['well'], recipe['pail']
    for owner in (well, pail):
        if owner['artwork_size'] != [2*v for v in owner['logical_size']]:
            raise ValueError('Art and logical sizes disagree')
    masters = {record['id']: normalized_master(record, recipe['alpha']['threshold'])
               for record in recipe['source_normalization']}
    if set(masters) != {'well', 'pail'}:
        raise ValueError('Exactly the declared new well and pail masters are required')
    if list(masters['well'].size) != well['artwork_size'] or list(masters['pail'].size) != pail['artwork_size']:
        raise ValueError('Master canvas disagrees with its owning asset')
    masks = masks_for(well['masks'], masters['well'])
    pail_masks = masks_for(pail['masks'], masters['pail'])
    if ImageChops.subtract(masks['water'], masks['aperture']).getbbox():
        raise ValueError('Water leaves the shaft aperture')
    if ImageChops.multiply(masks['water'], masks['near_wall']).getbbox():
        raise ValueError('Near masonry covers the declared water surface')
    if ImageChops.subtract(pail_masks['interior'], pail_masks['mouth']).getbbox():
        raise ValueError('Pail water leaves its interior')
    pivot = well['anchors_logical']['crank_pivot']
    if pivot != well['mechanism_reference']['crank_orbit']['center_logical']:
        raise ValueError('Projected crank orbit must be centered on its axle')
    output, exports = {}, []

    def png(relative, image, role):
        path = PACK+'/'+relative_file(relative)
        if path in output:
            raise ValueError('Duplicate pack export: '+path)
        buffer = BytesIO(); image.save(buffer, format='PNG')
        raw = buffer.getvalue(); output[path] = raw
        exports.append({'file': relative, 'sha256': digest(raw),
                        'artwork_size': list(image.size), 'mode': image.mode, 'role': role})
        return relative

    layers = {}; remaining = masters['well'].getchannel('A')
    partition = well['layer_partition']
    for name in partition['priority']:
        mask_name = partition['mask_by_layer'][name]
        mask = remaining.copy() if mask_name == 'remaining_source_alpha' else ImageChops.multiply(remaining, masks[mask_name])
        layers[name] = masked(masters['well'], mask)
        remaining = ImageChops.subtract(remaining, mask)
    if remaining.getbbox():
        raise ValueError('Unowned structural pixels remain')
    structural = Image.new('RGBA', masters['well'].size)
    for name in partition['priority']:
        structural.alpha_composite(layers[name])
    canonical_master = masked(masters['well'], masters['well'].getchannel('A'))
    if structural.tobytes() != canonical_master.tobytes():
        raise ValueError('Structural layers do not reconstruct their master')
    shadow_record = next(item for item in well['layers'] if item['id'] == 'contact_shadow')
    shadow = Image.new('RGBA', masters['well'].size, shadow_record['color'])
    shadow.putalpha(masks['contact_shadow']); layers['contact_shadow'] = shadow
    assembly = Image.new('RGBA', masters['well'].size)
    layer_records = deepcopy(well['layers'])
    for record in layer_records:
        image = layers[record['id']]
        png(record['file'], image, record['role'])
        rendered = image.copy()
        rendered.putalpha(rendered.getchannel('A').point(lambda a, opacity=record['opacity']: round(a*opacity)))
        assembly.alpha_composite(rendered)
        record.update(logical_size=well['logical_size'], artwork_size=well['artwork_size'], artwork_pixels_per_world_pixel=2)
    for record in well['masks']:
        png(record['file'], masks[record['id']], 'well_'+record['id']+'_mask')
    # Distinct filenames keep pail-local and well-local mask spaces unambiguous.
    pail_mask_paths = {}
    for record in pail['masks']:
        pail_mask_paths[record['id']] = png('masks/pail_'+record['id']+'.png', pail_masks[record['id']], 'pail_'+record['id']+'_mask')
    colors = recipe['palette']['water_colors']
    interior = pail_masks['interior']; bounds = interior.getbbox()
    variants = deepcopy(pail['variants'])
    for record in variants:
        units = record['units']
        if type(units) is not int or not 0 <= units <= pail['capacity_units']:
            raise ValueError('Invalid static pail fill level')
        image = masters['pail'].copy()
        if units:
            fill = Image.new('RGBA', image.size)
            painter = ImageDraw.Draw(fill)
            y0 = bounds[3]-round((bounds[3]-bounds[1])*units/pail['capacity_units'])
            painter.rectangle((bounds[0], y0, bounds[2]-1, bounds[3]-1), fill=colors['deep'])
            if y0 <= bounds[3]-2:
                painter.rectangle((bounds[0]+1, y0, bounds[2]-2, bounds[3]-2), fill=colors['base'])
            painter.line((bounds[0]+2, y0, bounds[2]-3, y0), fill=colors['reflection'], width=1)
            fill.putalpha(ImageChops.multiply(fill.getchannel('A'), interior))
            image.alpha_composite(fill)
        png(record['file'], image, 'static_pail_fill')
    if {record['units'] for record in variants} != set(range(pail['capacity_units']+1)):
        raise ValueError('Static pail levels must cover empty through full')
    png('assembled.png', assembly, 'static_layered_review_composite')
    png('structure.png', structural, 'uniformly_registered_structural_master')
    manifest = {
        'version': 1, 'id': recipe['id'], 'integration_status': 'staged',
        'visual_approval': 'pending_user_review', 'runtime_activation': False,
        'artwork_pixels_per_world_pixel': 2,
        'source_recipe': RECIPE, 'source_recipe_sha256': digest(raw_recipe),
        'exporter': 'tools/build_eldenmere_well_pack.py',
        'exporter_sha256': digest(Path(__file__).read_bytes()),
        'sources': deepcopy(recipe['source_normalization']),
        'authoring': deepcopy(recipe['authoring']),
        'geometry': deepcopy(well),
        'assembly': {'file': 'assembled.png', 'logical_size': well['logical_size'],
                     'artwork_size': well['artwork_size'], 'world_position': well['world_position_logical'],
                     'draw_anchor_logical': well['draw_anchor_logical'],
                     'ground_anchor_logical': well['ground_anchor_logical'],
                     'ground_anchor_world': well['ground_anchor_world_logical'],
                     'alpha_policy': 'Hard structural layers; declared whole-layer shadow opacity in this derived composite.'},
        'layers': layer_records, 'masks': deepcopy(well['masks']),
        'pail': {'logical_size': pail['logical_size'], 'artwork_size': pail['artwork_size'],
                 'grip_logical': pail['grip_anchor_logical'], 'support_logical': pail['support_anchor_logical'],
                 'capacity_units': pail['capacity_units'], 'variants': variants, 'masks': pail_mask_paths},
        'exports': exports,
        'limits': 'PR1 static asset bank. No animated mechanism, new actor poses, live bindings, interaction or collision registration. Geometry targets require later motion/pose review.',
    }
    output[PACK+'/manifest.json'] = document(manifest)
    return output


def build(check=False):
    output = products()
    stale = [path for path, raw in output.items()
             if not (ROOT/path).is_file() or (ROOT/path).read_bytes() != raw]
    if check and stale:
        raise SystemExit('Stale staged well exports: '+', '.join(stale))
    if not check:
        for path, raw in output.items():
            target = ROOT/path
            if not target.is_file() or target.read_bytes() != raw:
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    print(f'{len(output)} staged well/pail exports '+('verified' if check else 'built'))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
