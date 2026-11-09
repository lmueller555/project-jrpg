"""Compose native cave battle stages from the approved limestone pack.

The recipe references real continuous-cave rooms and retained terrain modules.
Lighting and water are compiled into a short background cycle; no characters,
interface, shadows or encounter decisions are baked into these images.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat/cave_battlefields/recipe.json'
SIZE = (480, 320)
FRAME_COUNT = 24
FRAME_MS = 250
FIELD_IDS = frozenset(('cave_outer', 'cave_grotto', 'cave_hollow', 'cave_depths',
                       'cave_echo_chamber', 'cave_embervein', 'cave_stillfrost'))


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def products():
    spec = json.loads(SOURCE.read_text())
    if (spec.get('version') != 1 or spec.get('canvas') != list(SIZE)
            or spec.get('tile_size') != 24 or spec.get('frame_count') != FRAME_COUNT
            or spec.get('frame_duration_ms') != FRAME_MS
            or spec.get('reduced_motion_frame') != 8):
        raise ValueError('Invalid cave battlefield recipe dimensions or timing')
    fields = spec.get('fields')
    if (not isinstance(fields, list) or len(fields) != len(FIELD_IDS)
            or any(not isinstance(field, dict) or not isinstance(field.get('id'), str)
                   for field in fields)
            or {field['id'] for field in fields} != FIELD_IDS):
        raise ValueError('Invalid cave battlefield recipe roster')
    used = {SOURCE, Path(__file__).resolve()}
    result = {}
    source_map = ROOT/spec['source_map']
    used.add(source_map)
    cave = json.loads(source_map.read_text())
    rooms = {room['id']: room for room in cave['cave']['rooms']}
    packs = {}
    for key, name in spec['manifests'].items():
        path = ROOT/name
        used.add(path)
        packs[key] = json.loads(path.read_text())
    image_cache = {}
    def opened(name):
        used.add(ROOT/name)
        if name not in image_cache:
            with Image.open(ROOT/name) as image:
                image_cache[name] = image.convert('RGBA')
        return image_cache[name]
    def module(pack, name, index=0):
        entry = packs[pack]['modules'][name]
        return entry, opened(entry['frames'][index % len(entry['frames'])])
    materials = {name: [opened(path) for path in entry['tiles']]
                 for name, entry in packs['base']['materials'].items()}
    materials['earth'] = [opened(path) for path in packs['geology']['materials']['earth']['tiles']]
    width, height = SIZE
    yy, xx = np.indices((height, width))
    bayer = np.array(((0, 8, 2, 10), (12, 4, 14, 6),
                      (3, 11, 1, 9), (15, 7, 13, 5)))
    threshold = (bayer[(yy//2) % 4, (xx//2) % 4]+.5)*16
    def material(name, seed):
        image = Image.new('RGBA', SIZE)
        tiles = materials[name]
        for y in range(0, height, 12):
            for x in range(0, width, 24):
                number = ((x//24*137) ^ (y//12*271) ^ seed) % len(tiles)
                # The same native rock is compressed vertically for the low
                # battle camera. Sampling is nearest-neighbour throughout.
                tile = tiles[number].resize((24, 12), Image.Resampling.NEAREST)
                image.alpha_composite(tile, (x, y))
        return image
    def placement(canvas, item, phase=0):
        record, image = module(item['pack'], item['module'], phase)
        scale = item.get('scale', 1)
        anchor = record.get('anchor', [0, 0])
        if scale != 1:
            image = image.resize((round(image.width*scale), round(image.height*scale)), Image.Resampling.NEAREST)
        point = item['position']
        position = [round(point[0]-anchor[0]*scale), round(point[1]-anchor[1]*scale)]
        canvas.alpha_composite(image, tuple(position))
        return {'pack': item['pack'], 'module': item['module'], 'position': position,
                'scale': scale, 'source_frames': record['frames']}
    for field in spec['fields']:
        if any(identifier not in rooms for identifier in field['source_rooms']):
            raise ValueError('Unknown continuous-cave source room: '+field['id'])
        ground = material(field['floor_material'], field['seed'])
        for patch in field.get('patches', []):
            mask = Image.new('L', SIZE)
            ImageDraw.Draw(mask).polygon([tuple(p) for p in patch['polygon']], fill=255)
            cover = np.array(mask.filter(ImageFilter.BoxBlur(9)))
            mask = Image.fromarray(np.where(cover > threshold, 255, 0).astype(np.uint8))
            ground.paste(material(patch['material'], field['seed']+29), (0, 0), mask)
        wall_mask = Image.new('L', SIZE)
        edge = [tuple(point) for point in field['wall_edge']]
        ImageDraw.Draw(wall_mask).polygon([(0, 0), (width, 0), *reversed(edge)], fill=255)
        wall_fill = material('dry', field['seed']+71)
        # A quiet overhead roof fades into the textured vertical rear face.
        roof_values = np.array(wall_fill.convert('RGB'), dtype=np.float32)
        roof_gain = np.clip((yy-12)/65, 0, 1)*.40+.37
        roof_values *= roof_gain[:, :, None]
        wall_fill = Image.fromarray(np.rint(roof_values).astype(np.uint8)).convert('RGBA')
        ground.paste(wall_fill, (0, 0), wall_mask)
        # Fit the approved front-face module along a restrained irregular rear
        # contour, rather than using a map screenshot or giant stretched tile.
        wall_records = []
        for index in range(6):
            x = index*94-2
            bottom = field['wall_baselines'][index]
            record, face = module('base', 'wall.front.'+str((index+field['seed']) % 6))
            position = [x, bottom-64]
            ground.alpha_composite(face, tuple(position))
            wall_records.append({'pack': 'base', 'module': 'wall.front.'+str((index+field['seed']) % 6),
                                 'position': position})
        placed = []
        for item in field.get('placements', []):
            if not item.get('animated'):
                placed.append(placement(ground, item))
        # All opaque scenery ends above the arena, apart from harmless ground
        # decals. The four enemy slots and three player slots remain clear.
        lighting_mask = np.ones((height, width), dtype=np.float32)
        lighting_mask[yy < 36] = 0
        for rect in field.get('dark_recesses', []):
            x, y, w, h = rect
            lighting_mask[y:y+h, x:x+w] = 0
        static = ground.copy()
        water_cells = {tuple(point) for point in field.get('water_cells', [])}
        water_records = []
        if water_cells:
            for cell_x, cell_y in sorted(water_cells):
                n, e, s, west = ((cell_x, cell_y-1) not in water_cells,
                                 (cell_x+1, cell_y) not in water_cells,
                                 (cell_x, cell_y+1) not in water_cells,
                                 (cell_x-1, cell_y) not in water_cells)
                if n and e: key = 'bank.outer_ne.0'
                elif e and s: key = 'bank.outer_se.0'
                elif s and west: key = 'bank.outer_sw.0'
                elif west and n: key = 'bank.outer_nw.0'
                elif n: key = 'bank.north.0'
                elif e: key = 'bank.east.0'
                elif s: key = 'bank.south.0'
                elif west: key = 'bank.west.0'
                else: key = 'water.deep.'+str((cell_x*17+cell_y*31) % 3)
                water_records.append({'pack': 'water', 'module': key,
                                      'position': [cell_x*24, cell_y*24]})
        lights, crystals = [], []
        for item in field['crystals']:
            record, _ = module('micro', item['module'])
            anchor = record['anchor']
            position = [item['position'][0]-anchor[0], item['position'][1]-anchor[1]]
            for bx, by, w, h in record['core_components']:
                x, y = position[0]+bx, position[1]+by
                if not (0 <= x and 0 <= y and x+w <= width and y+h <= height):
                    raise ValueError('Clipped battlefield microcrystal: '+field['id'])
                if not np.all(np.array(wall_mask)[y:y+h, x:x+w]):
                    raise ValueError('Battlefield microcrystal leaves rear wall: '+field['id'])
            origin = item.get('light_position', [item['position'][0], min(150, item['position'][1]+38)])
            radius = item.get('radius', 150)
            falloff = np.clip(1-np.sqrt((xx-origin[0])**2+(yy-origin[1])**2)/radius, 0, 1)**1.7
            falloff *= lighting_mask
            lights.append((falloff, np.array(record['color'], dtype=np.float32), item.get('phase', 0)))
            crystals.append({'module': item['module'], 'position': position,
                             'color': record['gem_color'], 'crystal_count': record['crystal_count'],
                             'crystal_sizes': record['crystal_sizes'], 'core_components': record['core_components'],
                             'light_position': origin, 'radius': radius})
        frames = []
        for frame in range(FRAME_COUNT):
            canvas = static.copy()
            for item in water_records:
                _, image = module('water', item['module'], frame)
                canvas.alpha_composite(image, tuple(item['position']))
            for item in field.get('placements', []):
                if item.get('animated'):
                    placement(canvas, item, frame)
            values = np.array(canvas.convert('RGB'), dtype=np.float32)
            # Ambient brightness remains readable at the trough. A soft rear-
            # to-front grade gives a low camera angle while retaining detail.
            gain = field.get('ambient', .64)+np.clip((yy-128)/192, 0, 1)*.12
            values *= gain[:, :, None]
            if field.get('daylight'):
                daylight = np.clip(1-np.sqrt((xx+25)**2+(yy-115)**2)/310, 0, 1)**1.6
                values += daylight[:, :, None]*np.array((23, 24, 14), dtype=np.float32)
            pulses = []
            for falloff, color, phase in lights:
                pulse = .5-.5*math.cos(frame/FRAME_COUNT*math.tau+phase)
                values += falloff[:, :, None]*color*(.022+.075*pulse)*field.get('light_gain',1.)
                pulses.append(pulse)
            canvas = Image.fromarray(np.rint(np.clip(values, 0, 255)).astype(np.uint8)).convert('RGBA')
            for item, pulse in zip(field['crystals'], pulses):
                placement(canvas, {'pack': 'micro', **item}, round(pulse*5))
            directory = ROOT/'assets/combat'/field['id']
            name = f'background_{frame:02}.png'
            result[(directory/name).relative_to(ROOT).as_posix()] = encoded(canvas.convert('RGB'))
            frames.append((directory/name).relative_to(ROOT).as_posix())
        directory = ROOT/'assets/combat'/field['id']
        result[(directory/'background.png').relative_to(ROOT).as_posix()] = result[frames[8]]
        provenance = {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
                      for path in sorted(used)}
        data = {'version': 1, 'id': field['id'], 'name': field['name'], 'size': list(SIZE),
                'background_frames': frames, 'frame_duration_ms': FRAME_MS,
                'reduced_motion_frame': 8, 'foreground': [],
                'source_scene': 'sanctuary_cave', 'source_rooms': field['source_rooms'],
                'source_room_names': [rooms[name]['name'] for name in field['source_rooms']],
                'source_position': field['source_position'], 'camera': 'low view toward the rear cave wall',
                'clear_actor_stage': [24, 145, 432, 77],
                'animation': {'period_ms': FRAME_COUNT*FRAME_MS,
                              'crystal_colors': sorted({item['color'] for item in crystals}),
                              'microcrystal_count': sum(item['crystal_count'] for item in crystals),
                              'water_tiles': len(water_records), 'pulse': True},
                'crystals': crystals, 'placed_modules': wall_records+placed,
                'build': {'tool': 'tools/build_cave_battlefields.py',
                          'source_recipe': SOURCE.relative_to(ROOT).as_posix(),
                          'source_sha256': provenance}}
        result[(directory/'battlefield.json').relative_to(ROOT).as_posix()] = (
            json.dumps(data, indent=2)+'\n').encode()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    changed = []
    result = products()
    for name, raw in result.items():
        path = ROOT/name
        if not path.exists() or path.read_bytes() != raw:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
    if args.check and changed:
        raise SystemExit('Stale cave battlefield exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(result)} cave battlefield exports')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
