"""Assemble the reserve hall from native Eldenmere pixel asset modules.

Runtime terrain is a cache of authored floor/wall tiles. Furniture remains
independently depth-sorted, with real ground-contact rectangles. No painting,
image tracing or source-photo cutout participates in this build.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/elden_vale_sanctuary_hall/recipe.json'
ART = ROOT/'assets/terrain/elden_vale_sanctuary_hall'
MAP = ROOT/'assets/maps/elden_vale_sanctuary_hall'


def png(image):
    stream = BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def box(rect):
    x, y, width, height = rect
    return x, y, x+width, y+height


def products():
    data = json.loads(SOURCE.read_text())
    assets = {}
    for name, source in data['assets'].items():
        path = ROOT/source['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Source pixel asset changed: '+source['path'])
        with Image.open(path) as image:
            assets[name] = image.convert('RGBA')

    def stone(image):
        """Use the terrace masonry pixels with an indoor limestone palette."""
        palette = {tuple(bytes.fromhex(key[1:])): tuple(bytes.fromhex(value[1:]))
                   for key, value in data['stone_palette'].items()}
        result = image.copy()
        pixels = []
        for r, g, b, alpha in image.get_flattened_data():
            color = palette.get((r, g, b))
            # Exterior moss is omitted in maintained interior masonry.
            if color is None and g > r:
                color = (185, 177, 152)
            pixels.append((*color, alpha) if color else (r, g, b, alpha))
        result.putdata(pixels)
        return result

    masonry = stone(assets['stone_front'])
    cap = stone(assets['stone_back'])
    ground = Image.new('RGBA', tuple(data['native_size']), '#24302d')
    fx, fy, fw, fh = data['floor_rect']
    for row in range(fh//24):
        for col in range(fw//24):
            ground.alpha_composite(assets['floor_'+('abc'[(col+2*row)%3])],
                                   (fx+col*24, fy+row*24))
    # All wall courses use the same native24px pack blocks; none is stretched.
    for rect in data['walls'].values():
        x, y, width, height = rect
        for yy in range(y, y+height, 24):
            for xx in range(x, x+width, 24):
                ground.alpha_composite(masonry.crop((0, 0, min(24, x+width-xx),
                                                    min(24, y+height-yy))), (xx, yy))
    for x in range(0, 576, 24):
        ground.alpha_composite(cap.crop((0, 0, 24, 8)), (x, 42))
    for x in (0, 552):
        for y in range(48, 336, 24):
            ground.alpha_composite(cap.crop((0, 0, 8, 24)), (x+(16 if x == 0 else 0), y))
    # Four native windows and a care noticeboard make the back wall readable.
    for point in data['windows']:
        ground.alpha_composite(assets['window'], tuple(point))
    ground.alpha_composite(assets['noticeboard'], tuple(data['noticeboard']))
    ex, ey, ew, eh = data['exit_clearance']
    for y in range(ey, ey+eh, 24):
        for x in range(ex, ex+ew, 24):
            ground.alpha_composite(assets['floor_a'].crop((0, 0, min(24, ex+ew-x),
                                                        min(24, ey+eh-y))), (x, y))
    for x in range(ex, ex+ew, 24):
        ground.alpha_composite(assets['threshold'], (x, 348))
    blocked = Image.new('L', ground.size, 255)
    blocked.paste(0, box(data['floor_rect']))
    blocked.paste(0, box(data['exit_clearance']))
    output = {ART/'ground.png': png(ground.convert('RGB'))}
    entities = []
    footprints = []
    for record in data['objects']:
        if record.get('kind') == 'remembrance_table':
            image = Image.new('RGBA', (144, 64))
            for x in (0, 48, 96):image.alpha_composite(assets['table'], (x, 16))
            image.alpha_composite(assets['basket'], (10, 8))
            image.alpha_composite(assets['notes'], (51, 10))
            image.alpha_composite(assets['herb'], (116, 2))
            refs = ['table', 'basket', 'notes', 'herb']
        elif record.get('kind') == 'records_desk':
            image = Image.new('RGBA', (96, 54))
            for x in (0, 48):image.alpha_composite(assets['table'], (x, 6))
            image.alpha_composite(assets['notes'], (12, 0))
            image.alpha_composite(assets['herb'], (73, 0))
            refs = ['table', 'notes', 'herb']
        elif record.get('kind') == 'bookcases':
            image = Image.new('RGBA', (72, 60))
            image.alpha_composite(assets['bookcase'], (0, 0))
            image.alpha_composite(assets['bookcase'], (36, 0))
            refs = ['bookcase']
        else:
            image = assets[record['asset']]
            refs = [record['asset']]
        path = ART/'props'/(record['id']+'.png')
        output[path] = png(image)
        x, y = record['position']
        entity = {'id': record['id'], 'position': record['position'],
                  'sort_y': record['sort_y'], 'sort_priority': 0,
                  'frames': [path.relative_to(ROOT).as_posix()],
                  'frame_duration_ms': 300, 'phase_offset': 0,
                  'source_assets': [data['assets'][name]['path'] for name in refs]}
        if 'floor_rect' in record:
            dx, dy, width, height = record['floor_rect']
            footprint = [x+dx, y+dy, width, height]
            blocked.paste(255, box(footprint))
            entity['footprint'] = footprint
            footprints.append({'id': record['id'], 'rect': footprint})
        entities.append(entity)
    overview = ground.copy()
    for entity in sorted(entities, key=lambda item: item['sort_y']):
        image = Image.open(BytesIO(output[ROOT/entity['frames'][0]])).convert('RGBA')
        overview.alpha_composite(image, tuple(entity['position']))
    output[ART/'overview.png'] = png(overview.convert('RGB'))
    output[MAP/'collision.png'] = png(blocked)
    map_data = {
        'id': data['id'], 'name': data['name'], 'kind': 'interior',
        'size_pixels': data['native_size'], 'size_tiles': [24, 16], 'tile_size': 24,
        'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
        'spawn': data['spawn'], 'ground_frames': [(ART/'ground.png').relative_to(ROOT).as_posix()],
        'ground_frame_duration_ms': 300, 'overview': (ART/'overview.png').relative_to(ROOT).as_posix(),
        'collision': (MAP/'collision.png').relative_to(ROOT).as_posix(),
        'entities': entities, 'foreground': [], 'npcs': [], 'quests': [], 'landmarks': [],
        'exterior_map_position': data['exterior_map_position'],
        'destinations': data['destinations'], 'inspection_points': data['inspection_points'],
        'doors': [{
            'id': 'reserve_exit', 'anchor': data['exit_anchor'], 'entry_y': data['exit_anchor'][1],
            'entry_side': 'south', 'entry_half_width': 22, 'open_radius': 30, 'close_radius': 38,
            'frame_duration_ms': 100, 'frames': [], 'position': [0, 0], 'host': None,
            'requires_open': False, 'destination': 'assets/maps/elden_vale_sanctuary/map.json',
            'spawn': data['exterior_return'], 'arrival_facing': 'front', 'arrival_door': 'sanctuary_hall'}],
        'authoring': data['authoring'], 'source_recipe': SOURCE.relative_to(ROOT).as_posix(),
        'source_recipe_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'source_assets': list(data['assets'].values()), 'object_footprints': footprints,
        'walkable_floor': data['floor_rect'], 'exit_clearance': data['exit_clearance']}
    output[MAP/'map.json'] = (json.dumps(map_data, indent=2)+'\n').encode()
    manifest = {'version': 1, 'authoring': data['authoring'],
                'source_recipe': SOURCE.relative_to(ROOT).as_posix(),
                'source_assets': list(data['assets'].values()),
                'entities': entities, 'native_size': data['native_size']}
    output[ART/'art.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    return output


def build(check=False):
    output = products()
    expected = set(output)
    obsolete = [path for directory in (ART/'depth', ART/'props')
                for path in directory.glob('*.png') if path not in expected]
    if check and obsolete:raise ValueError('Obsolete reserve hall art exports remain')
    for path, content in output.items():
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError('Stale reserve hall export: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if not check:
        for path in obsolete:path.unlink()
    print(f'{"Verified" if check else "Exported"} {len(output)} modular reserve hall products')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
