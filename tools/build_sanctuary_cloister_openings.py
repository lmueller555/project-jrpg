"""Export localized imagegen cloister floors and replacement architecture depth.

The immutable sanctuary ground and all existing depth exports stay unchanged.
Only cropped generated floor pixels enter the new ground patch; retained source
pixels keep the original columns, arches, roof and occupied eastern workbay.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/elden_vale_cloister_openings'
RECIPE = SOURCE / 'art_recipe.json'
OUTPUT = ROOT / 'assets/terrain/elden_vale_cloister_openings'


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def rectangle_mask(size, box):
    mask = Image.new('L', size)
    mask.paste(255, tuple(box))
    return mask


def exports():
    recipe = json.loads(RECIPE.read_text(encoding='utf-8'))
    for record in recipe['sources']:
        if hashlib.sha256((ROOT / record['path']).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Retained cloister source changed: {record["path"]}')
    images = []
    for field in ('original_source', 'generated_source'):
        with Image.open(ROOT / recipe[field]) as source:
            if list(source.size) != recipe['source_size']:
                raise ValueError(f'Cloister {field} size differs from recipe')
            images.append(source.convert('RGB').resize(tuple(recipe['native_size']), Image.Resampling.NEAREST))
    original, generated = images
    native = original.copy()
    for box in recipe['edited_interior_rectangles']:
        native.paste(generated.crop(tuple(box)), tuple(box[:2]))
    bounds = recipe['native_patch_bounds']
    products = {'ground_patch.png': encoded(native.crop(tuple(bounds)))}
    entities = []

    def entity(identifier, name, position, sort_y, anchor=None):
        record = {
            'id': identifier, 'source_id': identifier,
            'frames': [(OUTPUT / name).relative_to(ROOT).as_posix()],
            'position': list(position), 'sort_y': sort_y,
            'frame_duration_ms': 1000, 'phase_offset': 0,
        }
        if anchor is not None:
            record['ground_anchor'] = list(anchor)
        return record

    ground = entity('sanctuary_cloister_openings_ground', 'ground_patch.png', bounds[:2], -1000)
    ground['layer'] = 'ground_patch'

    def depth(identifier, pixels, mask, sort_y, anchor):
        crop = mask.getbbox()
        if crop is None:
            raise ValueError(f'Empty cloister mask: {identifier}')
        surface = pixels.convert('RGBA')
        surface.putalpha(mask)
        surface = surface.crop(crop)
        # Fully transparent texels carry no rectangular source-color matte.
        surface.paste((0, 0, 0, 0), mask=surface.getchannel('A').point(lambda value: 255 - value))
        name = 'depth/' + identifier + '.png'
        products[name] = encoded(surface)
        entities.append(entity(identifier, name, crop[:2], sort_y, anchor))

    architecture = Image.new('L', original.size)
    painter = ImageDraw.Draw(architecture)
    painter.polygon(recipe['cloister_outer_polygon'], fill=255)
    for polygon in recipe['opening_polygons']:
        painter.polygon(polygon, fill=0)
    architecture.paste(0, (0, recipe['front_architecture_cutoff_y'], original.width, original.height))
    for index, box in enumerate(recipe['column_rectangles']):
        column = ImageChops.multiply(architecture, rectangle_mask(original.size, box))
        architecture.paste(0, tuple(box))
        depth(f'cloister_open_column_{index:02}', original, column,
              recipe['front_architecture_sort_y'], ((box[0] + box[2]) // 2, box[3]))
    depth('cloister_open_roof_arches', original, architecture,
          recipe['front_architecture_sort_y'], (750, recipe['front_architecture_sort_y']))

    rear = Image.new('L', original.size)
    painter = ImageDraw.Draw(rear)
    for polygon in recipe['opening_polygons']:
        painter.polygon(polygon, fill=255)
    rear.paste(0, (0, recipe['rear_wall_bottom_y'], original.width, original.height))
    depth('cloister_open_rear_wall', native, rear,
          recipe['rear_wall_sort_y'], (742, recipe['rear_wall_sort_y']))

    stock = Image.new('L', original.size)
    painter = ImageDraw.Draw(stock)
    for polygon in recipe['east_stock_polygons']:
        painter.polygon(polygon, fill=255)
    depth('cloister_preserved_east_stock', original, stock,
          recipe['east_stock_sort_y'], (842, recipe['east_stock_sort_y']))

    manifest = {
        'version': 1,
        'native_size': recipe['native_size'],
        'patch_bounds': bounds,
        'ground_patch_entities': [ground],
        'depth_entities': entities,
        'entities': [ground, *entities],
        'replace_entity_ids': recipe['replace_entity_ids'],
        'rear_wall_sort_y': recipe['rear_wall_sort_y'],
        'recommended_rear_wall_rect': recipe['recommended_rear_wall_rect'],
        'source_recipe': RECIPE.relative_to(ROOT).as_posix(),
        'source_recipe_sha256': hashlib.sha256(RECIPE.read_bytes()).hexdigest(),
    }
    products['art.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    return products


def build(check=False):
    products = exports()
    for name, content in products.items():
        path = OUTPUT / name
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f'Stale cloister opening export: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(f'{"Verified" if check else "Exported"} three open cloister bays and {len(products) - 2} depth silhouettes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
