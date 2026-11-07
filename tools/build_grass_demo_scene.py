"""Compile an isolated, walkable grass review field from native pixel assets.

The three proposed ground materials form larger irregular patches. Tall grass
is exported as interactive placement data rather than baked into runtime ground.
Existing Eldenmere and Sanctuary maps and source packs remain read only.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/grass_demo/recipe.json'
OUTPUT = ROOT/'assets/maps/grass_demo'
TILE = 24
BITS = {'N': 1, 'NE': 2, 'E': 4, 'SE': 8,
        'S': 16, 'SW': 32, 'W': 64, 'NW': 128}
OFFSETS = {'N': (0, -1), 'NE': (1, -1), 'E': (1, 0), 'SE': (1, 1),
           'S': (0, 1), 'SW': (-1, 1), 'W': (-1, 0), 'NW': (-1, -1)}


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def rect_box(rect):
    x, y, width, height = rect
    return x, y, x+width, y+height


def products():
    recipe = json.loads(SOURCE.read_text())
    manifest_path = ROOT/recipe['asset_manifest']
    manifest = json.loads(manifest_path.read_text())
    used = {SOURCE, manifest_path}

    def opened(relative):
        path = ROOT/relative
        used.add(path)
        with Image.open(path) as image:
            return image.convert('RGBA')

    def read(relative):
        path = ROOT/relative
        used.add(path)
        return json.loads(path.read_text())

    width, height = (value*TILE for value in recipe['size_tiles'])
    materials = {name: [opened(path) for path in record['tiles']]
                 for name, record in manifest['materials'].items()}
    if any(image.size != (TILE, TILE)
           for variants in materials.values() for image in variants):
        raise ValueError('Grass demonstration materials must be native 24-pixel tiles')

    def material_layer(name):
        variants = materials[name]
        image = Image.new('RGBA', (width, height))
        # Fine, quiet materials dominate. Fuller growth belongs to larger
        # authored patches rather than one centered tuft in every tile.
        patches = recipe['materials']['accent_patches'][name]
        for row in range(recipe['size_tiles'][1]):
            for col in range(recipe['size_tiles'][0]):
                x, y = col*TILE+TILE/2, row*TILE+TILE/2
                density = max((max(0, 1-((x-patch['center'][0])/patch['radius'][0])**2
                                  -((y-patch['center'][1])/patch['radius'][1])**2)
                               for patch in patches), default=0)
                sample = ((col*173+row*379+col*row*37+recipe['seed']) % 997)/997
                index = 0 if sample < .64 else 1
                if density > .12 and sample < density*.8:
                    index = 3 if (col*13+row*7+recipe['seed']) % 5 == 0 else 2
                image.alpha_composite(variants[index], (col*TILE, row*TILE))
        return image

    ground = material_layer(recipe['materials']['base'])
    # Blending uses hard, two-pixel clusters from the source colors, not an
    # antialiased seam. Coverage changes over an eight-pixel neighborhood.
    bayer = ((0, 8, 2, 10), (12, 4, 14, 6),
             (3, 11, 1, 9), (15, 7, 13, 5))
    for patch in recipe['materials']['patches']:
        mask = Image.new('L', (width, height))
        ImageDraw.Draw(mask).polygon([tuple(point) for point in patch['polygon']], fill=255)
        soft = mask.filter(ImageFilter.BoxBlur(recipe['materials']['blend_radius']))
        pixels = []
        for y in range(height):
            for x in range(width):
                value = soft.getpixel((x, y))
                threshold = (bayer[(y//2) % 4][(x//2) % 4]+.5)*16
                pixels.append(255 if value >= threshold else 0)
        mask.putdata(pixels)
        ground.paste(material_layer(patch['material']), (0, 0), mask)

    original = read('assets/terrain/eldenmere/grass_dirt/tileset.json')
    old_grass = [opened('assets/terrain/eldenmere/grass_dirt/'+path)
                 for path in original['grass']['images']]
    current = recipe['materials']['comparison_current']['rect']
    for y in range(current[1], current[1]+current[3], TILE):
        for x in range(current[0], current[0]+current[2], TILE):
            ground.alpha_composite(old_grass[(x//TILE+y//TILE) % len(old_grass)], (x, y))
    proposed = recipe['materials']['comparison_proposed']['rect']
    for y in range(proposed[1], proposed[1]+proposed[3], TILE):
        for x in range(proposed[0], proposed[0]+proposed[2], TILE):
            ground.alpha_composite(materials['lawn'][(x//TILE+y//TILE) % len(materials['lawn'])], (x, y))

    # The existing dirt treatment is a fixed palette/context comparison. Paths
    # follow a gentle circuit and leave the continuous grass crossing lanes open.
    path_mask = Image.new('1', tuple(recipe['size_tiles']))
    ImageDraw.Draw(path_mask).line([tuple(point) for point in recipe['path']['points']], fill=1,
                                  width=recipe['path']['width_tiles'])
    path_cells = {(x, y) for y in range(path_mask.height) for x in range(path_mask.width)
                  if path_mask.getpixel((x, y))}
    dirt = {record['mask']: opened('assets/terrain/eldenmere/grass_dirt/'+record['image'])
            for record in original['tiles']}
    for x, y in sorted(path_cells):
        raw = sum(BITS[name] for name, (dx, dy) in OFFSETS.items()
                  if (x+dx, y+dy) in path_cells)
        for diagonal, first, second in (('NE', 'N', 'E'), ('SE', 'E', 'S'),
                                         ('SW', 'S', 'W'), ('NW', 'W', 'N')):
            if not (raw & BITS[first] and raw & BITS[second]):
                raw &= ~BITS[diagonal]
        ground.alpha_composite(dirt[raw], (x*TILE, y*TILE))

    # A visible low masonry boundary distinguishes the finite review field.
    wall = opened('assets/terrain/eldenmere/terraces/tiles/wall_front_00.png')
    for x in range(0, width, TILE):
        ground.alpha_composite(wall, (x, 0))
        ground.alpha_composite(wall, (x, height-TILE))
    for y in range(TILE, height-TILE, TILE):
        ground.alpha_composite(wall, (0, y))
        ground.alpha_composite(wall, (width-TILE, y))

    footprints = [{'id': 'north_boundary', 'rect': [0, 0, width, TILE]},
                  {'id': 'south_boundary', 'rect': [0, height-TILE, width, TILE]},
                  {'id': 'west_boundary', 'rect': [0, TILE, TILE, height-2*TILE]},
                  {'id': 'east_boundary', 'rect': [width-TILE, TILE, TILE, height-2*TILE]}]
    entities = []
    for prop in recipe['props']:
        if prop['kind'] == 'tree':
            paths = [f'assets/terrain/eldenmere/foliage/tree/frames/frame_{index:02}.png'
                     for index in range(1, 10)]
            duration = 600
        else:
            paths = ['assets/terrain/eldenmere/sanctuary_charm/props/bench.png']
            duration = 1000
        for path in paths:opened(path)
        entities.append({'id': prop['id'], 'position': prop['position'],
                         'sort_y': prop['sort_y'], 'frames': paths,
                         'frame_duration_ms': duration, 'phase_offset': len(entities)*2})
        footprints.append({'id': prop['id'], 'rect': prop['footprint']})
    blocked = Image.new('L', (width, height), 0)
    for record in footprints:
        ImageDraw.Draw(blocked).rectangle(tuple(value-1 if index >= 2 else value
                                                for index, value in enumerate(rect_box(record['rect']))),
                                          fill=255)

    overview = ground.copy()
    ordered = []
    for entity in entities:
        ordered.append((entity['sort_y'], opened(entity['frames'][0]), entity['position']))
    tall = manifest['tall_grass']
    variants = tall['variants']
    anchor = tall.get('anchor', [12, 28])
    for record in recipe['grass']['instances']:
        first = variants[record['variant']]['idle'][0]
        position = [record['position'][0]-anchor[0], record['position'][1]-anchor[1]]
        ordered.append((record['position'][1]-2, opened(first['rear']), position))
        ordered.append((record['position'][1]+2, opened(first['front']), position))
    for _, image, position in sorted(ordered, key=lambda item: item[0]):
        overview.alpha_composite(image, tuple(position))

    # All source records reflect actual files read by composition. Tall-grass
    # runtime frames are listed by their manifest and remain separate from ground.
    sources = [{'path': path.relative_to(ROOT).as_posix(),
                'sha256': sha256(path.read_bytes()).hexdigest()}
               for path in sorted(used)]
    map_data = {'version': 1, 'id': recipe['id'], 'name': recipe['name'],
                'kind': 'demo', 'tile_size': TILE, 'size_tiles': recipe['size_tiles'],
                'size_pixels': [width, height], 'player_probe_size': [24, 12],
                'player_draw_anchor': [12, 30], 'spawn': recipe['spawn'],
                'ground_frames': [(OUTPUT/'ground.png').relative_to(ROOT).as_posix()],
                'ground_frame_duration_ms': 1000,
                'collision': (OUTPUT/'collision.png').relative_to(ROOT).as_posix(),
                'overview': (OUTPUT/'overview.png').relative_to(ROOT).as_posix(),
                'entities': entities, 'foreground': [], 'npcs': [], 'doors': [],
                'landmarks': [{'id': name, 'name': name.replace('_', ' ').title(),
                               'position': position}
                              for name, position in recipe['checkpoints'].items()],
                'regions': recipe['regions'], 'checkpoints': recipe['checkpoints'],
                'demo_route': recipe['demo_route'], 'review_route': recipe['review_route'],
                'grass': recipe['grass'], 'collision_footprints': footprints,
                'build': {'tool': 'tools/build_grass_demo_scene.py',
                          'source_recipe': SOURCE.relative_to(ROOT).as_posix(),
                          'source_recipe_sha256': sha256(SOURCE.read_bytes()).hexdigest(),
                          'source_assets': sources}}
    return {'ground.png': encoded(ground.convert('RGB')),
            'collision.png': encoded(blocked.convert('RGB')),
            'overview.png': encoded(overview.convert('RGB')),
            'map.json': (json.dumps(map_data, indent=2)+'\n').encode()}


def build(check=False):
    exports = products()
    for name, content in exports.items():
        path = OUTPUT/name
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError('Stale grass demonstration scene: '+name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(('Verified' if check else 'Exported')+' isolated grass demonstration scene')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
