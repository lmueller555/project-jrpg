"""Register two genuine native field fills without changing their donor pixels.

These are flat young-vegetable and tilled-earth surfaces, not raised beds or
harvestable objects. The town composer owns contact masks, repetition, physical
geometry and activation. Provenance is checked back to the retained material
master; an independent replay also verifies that the pinned PNG is a fresh
native export, rather than merely accepting a claimed donor hash.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RECIPE = 'assets/source/maps/eldenmere/growing_fields/recipe.json'
PACK = 'assets/terrain/eldenmere/growing_fields'
FIELDS = (('vegetables_east_west', 'vegetables'), ('furrows_east_west', 'furrows'))


def document(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def _path(value):
    path = Path(value)
    target = (ROOT/path).resolve()
    if path.is_absolute() or not target.is_relative_to(ROOT.resolve()) or not target.is_file():
        raise ValueError('Growing field source must exist inside the repository: '+str(value))
    return target


def _pinned(record):
    raw = _path(record['file']).read_bytes()
    if sha256(raw).hexdigest() != record['sha256']:
        raise ValueError('Changed growing field provenance: '+record['file'])
    return raw


def _select(value, selector):
    try:
        for key in selector:
            value = value[key]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError('Changed growing field source selector: '+str(selector)) from error
    return value


def _replay_native(master, crop, source_recipe):
    """Replay only the pinned field branch of the regional native exporter.

    Neither crop receives the prop outline/emerald transform. Their east-west
    variant is a zero-degree rotation of this original 48px texture export.
    This calculation validates provenance only; published PNG bytes are copied.
    """
    threshold = source_recipe['alpha_threshold']
    image = master.crop(crop).convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda value: 255 if value >= threshold else 0))
    image = image.resize((48, 48), Image.Resampling.NEAREST)
    alpha = image.getchannel('A')
    image = image.convert('RGB').quantize(colors=source_recipe['tile_palette_colors'],
                                        dither=Image.Dither.NONE).convert('RGBA')
    image.putalpha(alpha.point(lambda value: 255 if value >= threshold else 0))
    image = image.rotate(0)
    stream = BytesIO(); image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def _bed_contact(record):
    """Rasterize the authored whole-bed perimeter without touching donor tiles."""
    if record.get('id') != 'worked_bed' or record.get('logical_size') != [48, 24]:
        raise ValueError('Growing field contact must cover the reviewed 48x24 logical bed')
    if record.get('rect_space') != 'artwork xywh' or not record.get('edge_notches_artwork'):
        raise ValueError('Growing field contact needs explicit artwork-space edge notches')
    mask = Image.new('L', (96, 48), 255)
    draw = ImageDraw.Draw(mask)
    for rect in record['edge_notches_artwork']:
        if (not isinstance(rect, list) or len(rect) != 4
                or any(type(value) is not int for value in rect)):
            raise ValueError('Growing field contact notches need integer xywh rectangles')
        x, y, width, height = rect
        if not (0 <= x < x+width <= 96 and 0 <= y < y+height <= 48):
            raise ValueError('Growing field contact notch leaves its native canvas')
        if not (x+width <= 2 or x >= 94 or y+height <= 2 or y >= 46):
            raise ValueError('Growing field contact notch reaches beyond the two-pixel perimeter')
        draw.rectangle((x, y, x+width-1, y+height-1), fill=0)
    if mask.getextrema() != (0, 255) or mask.crop((2, 2, 94, 46)).getextrema() != (255, 255):
        raise ValueError('Growing field contact must preserve its fully opaque interior')
    stream = BytesIO(); mask.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def products():
    """Return deterministic output bytes after verifying all relevant sources."""
    recipe_raw = _path(RECIPE).read_bytes()
    recipe = json.loads(recipe_raw)
    if (recipe.get('version') != 1 or recipe.get('artwork_pixels_per_world_pixel') != 2
            or [item.get('id') for item in recipe.get('props', [])] != [name for name, _ in FIELDS]):
        raise ValueError('Growing fields require the two reviewed native field records')
    provenance = recipe['provenance']
    donor_manifest = json.loads(_pinned(provenance['donor_manifest']))
    donor_recipe = json.loads(_pinned(provenance['donor_source_recipe']))
    retained_recipe = json.loads(_pinned(provenance['retained_source_recipe']))
    if recipe['palette']['colors_per_tile'] != retained_recipe['tile_palette_colors']:
        raise ValueError('Growing field palette no longer agrees with its retained source recipe')
    generators = provenance['generators']
    if [item['file'] for item in generators] != [
            'tools/build_elden_vale_hd_foundation.py', 'tools/build_overworld_polish_art.py']:
        raise ValueError('Growing field native generator provenance changed')
    for item in [*generators, provenance['retained_source_recipe']]:
        _pinned(item)
        if donor_recipe['sources'].get(item['file']) != item['sha256']:
            raise ValueError('Growing field donor recipe no longer verifies '+item['file'])
    if donor_manifest.get('artwork_pixels_per_world_pixel') != 2 or donor_recipe.get('density') != 2:
        raise ValueError('Growing field donors must retain native 2x density')

    result, exports, props = {}, [], []
    for record, (name, field) in zip(recipe['props'], FIELDS):
        if record.get('logical_size') != [24, 24] or record.get('row_orientation') != 'east_west':
            raise ValueError('Growing field source must retain its native dimensions/orientation: '+name)
        donor, source = record['donor'], record['source']
        raw = _pinned(donor)
        selected = _select(donor_manifest, donor['source_selector'])
        if (donor['source_selector'][:2] != ['material_variants', field]
                or selected.get('image') != donor['file']
                or selected.get('logical_size') != [24, 24]
                or selected.get('row_orientation') != 'east_west'):
            raise ValueError('Growing field donor identity/orientation changed: '+name)
        original = _select(retained_recipe, source['source_selector'])
        tile = donor_manifest['tiles'][field]
        if (source['source_selector'] != ['tiles', field]
                or original.get('source') != 'quiet_texture_sheet.png'
                or original.get('crop') != source['crop'] or original.get('size') != [24, 24]
                or source['file'] != str(Path(provenance['retained_source_recipe']['file']).parent/original['source'])
                or tile.get('source_recipe') != provenance['retained_source_recipe']['file']
                or tile.get('logical_size') != [24, 24]):
            raise ValueError('Growing field retained crop identity changed: '+name)
        master_raw = _pinned(source)
        if donor_recipe['sources'].get(source['file']) != source['sha256']:
            raise ValueError('Growing field donor recipe no longer verifies its retained master')
        originals = [item for item in retained_recipe['source_records'] if item['file'] == source['file']]
        if (len(originals) != 1 or originals[0]['sha256'] != source['sha256']
                or originals[0].get('generator_original') != source['generator_original']):
            raise ValueError('Growing field original generation provenance changed: '+name)
        with Image.open(BytesIO(master_raw)) as opened:
            master = opened.convert('RGBA')
        crop = source['crop']
        if (len(crop) != 4 or any(type(value) is not int for value in crop)
                or not 0 <= crop[0] < crop[2] <= master.width
                or not 0 <= crop[1] < crop[3] <= master.height
                or sha256(master.crop(crop).tobytes()).hexdigest() != source['crop_pixels_sha256']):
            raise ValueError('Growing field retained crop pixels changed: '+name)
        if _replay_native(master, crop, retained_recipe) != raw:
            raise ValueError('Growing field donor is stale against its native generator: '+name)
        with Image.open(BytesIO(raw)) as opened:
            if opened.mode != 'RGBA' or opened.size != (48, 48):
                raise ValueError('Growing field donor lost its 48x48 native canvas: '+name)
            image = opened.copy()
        if set(image.getchannel('A').tobytes()) != {255}:
            raise ValueError('Growing field fill must retain opaque hard alpha: '+name)
        palette = sorted(set(zip(*[iter(image.tobytes())]*4)))
        if [list(color) for color in palette] != record['palette_rgba']:
            raise ValueError('Growing field donor palette changed: '+name)
        fine = sum(len({image.getpixel((x+dx, y+dy)) for dx in (0, 1) for dy in (0, 1)}) > 1
                   for y in range(0, 48, 2) for x in range(0, 48, 2))
        if fine != record['native_detail_blocks'] or fine == 0:
            raise ValueError('Growing field donor lost its authored native detail: '+name)
        relative = 'materials/'+name+'/idle.png'
        target = PACK+'/'+relative
        result[target] = raw
        exports.append(dict(file=target, artwork_size=[48, 48], sha256=sha256(raw).hexdigest()))
        props.append(dict(id=name, family='cultivated_surface', mount='ground',
                          logical_size=[24, 24], artwork_size=[48, 48],
                          artwork_pixels_per_world_pixel=2, idle=relative,
                          frames=[dict(file=relative, duration_ms=600)],
                          animation='static', frame_duration_ms=600,
                          depth_baseline_logical=24, draw_anchor_logical=[12, 24],
                          anchor_artwork=[24, 48], anchor_space='artwork',
                          occupied_rect_logical=[0, 0, 24, 24],
                          collision='not_registered; flat decorative ground without physical supports',
                          interaction_cues=False, row_orientation='east_west',
                          semantic_use=record['semantic_use'], source=deepcopy(donor),
                          retained_source=deepcopy(source), native_detail_blocks=fine,
                          palette_rgba=deepcopy(record['palette_rgba']),
                          output_sha256=sha256(raw).hexdigest()))
    contact_raw = _bed_contact(recipe['bed_contact'])
    contact_file = 'contacts/worked_bed.png'
    contact_path = PACK+'/'+contact_file
    contact_hash = sha256(contact_raw).hexdigest()
    result[contact_path] = contact_raw
    exports.append(dict(file=contact_path, artwork_size=[96, 48], sha256=contact_hash,
                        role='whole_bed_contact'))
    contact = dict(id='worked_bed', file=contact_file, logical_size=[48, 24],
                   artwork_size=[96, 48], artwork_pixels_per_world_pixel=2,
                   sha256=contact_hash, mask_channel='L',
                   source_ref=dict(file=RECIPE, path=['bed_contact']))
    manifest = dict(version=1, id=recipe['id'], artwork_state='byte_identical_native_donor_export',
                    integration_status='available_for_explicit_flat_ground_placement',
                    visual_approval='town_scale_and_contact_review_required',
                    artwork_pixels_per_world_pixel=2, recipe=RECIPE,
                    recipe_sha256=sha256(recipe_raw).hexdigest(),
                    exporter='tools/export_eldenmere_growing_fields.py',
                    exporter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                    provenance=deepcopy(provenance), palette=deepcopy(recipe['palette']),
                    props=props, bed_contact=contact, exports=exports)
    result[PACK+'/manifest.json'] = document(manifest)
    return result


def build(check=False):
    result = products()
    stale = []
    for path, raw in result.items():
        target = ROOT/path
        if not target.is_file() or target.read_bytes() != raw:
            stale.append(path)
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
    if check and stale:
        raise SystemExit('Stale growing field exports: '+', '.join(stale))
    print(f'{len(result)} growing field exports '+('verified' if check else 'built'))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
