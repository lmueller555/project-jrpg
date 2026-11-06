"""Export the approved reserve clean plate and registered depth silhouettes.

Image generation removes the preview's people; this deterministic exporter only
scales the retained source and registers polygon-masked copies of its pixels.
Geometry, actors, interaction and travel belong to the separate scene builder.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/elden_vale_sanctuary'
RECIPE = SOURCE/'art_recipe.json'
OUTPUT = ROOT/'assets/terrain/elden_vale_sanctuary'


def encoded(image):
    data = BytesIO()
    image.save(data, format='PNG')
    return data.getvalue()


def exports():
    recipe = json.loads(RECIPE.read_text(encoding='utf-8'))
    source_path = ROOT/recipe['clean_plate']
    for record in recipe['sources']:
        if hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Retained sanctuary source changed: {record["path"]}')
    with Image.open(source_path) as original:
        if list(original.size) != recipe['source_size']:
            raise ValueError('Sanctuary clean plate size differs from recipe')
        native = original.convert('RGB').resize(tuple(recipe['native_size']), Image.Resampling.NEAREST)
    ground = encoded(native)
    products = {'ground.png': ground, 'overview.png': ground}
    entities = []
    source_width, source_height = recipe['source_size']
    scale_x = native.width/source_width
    scale_y = native.height/source_height
    for record in recipe['depth_silhouettes']:
        mask = Image.new('L', native.size)
        points = [(round(x*scale_x), round(y*scale_y)) for x, y in record['polygon']]
        painter = ImageDraw.Draw(mask)
        painter.polygon(points, fill=255)
        for opening in record.get('openings', []):
            painter.polygon([(round(x*scale_x), round(y*scale_y)) for x, y in opening], fill=0)
        bounds = mask.getbbox()
        if bounds is None:
            raise ValueError(f'Empty sanctuary depth silhouette: {record["id"]}')
        surface = native.convert('RGBA')
        surface.putalpha(mask)
        surface = surface.crop(bounds)
        # Transparent pixels never carry a rectangular ground-colored matte.
        surface.paste((0, 0, 0, 0), mask=surface.getchannel('A').point(lambda value: 255-value))
        name = 'depth/'+record['id']+'.png'
        products[name] = encoded(surface)
        entities.append({'id': record['id'],
                         'frames': [(OUTPUT/name).relative_to(ROOT).as_posix()],
                         'position': list(bounds[:2]),
                         'sort_y': round(record['baseline']*scale_y),
                         'frame_duration_ms': 1000,
                         'phase_offset': 0})
    manifest = {'version': 1,
                'size_pixels': list(native.size),
                'ground': (OUTPUT/'ground.png').relative_to(ROOT).as_posix(),
                'overview': (OUTPUT/'overview.png').relative_to(ROOT).as_posix(),
                'entities': entities,
                'source_recipe': RECIPE.relative_to(ROOT).as_posix(),
                'source_recipe_sha256': hashlib.sha256(RECIPE.read_bytes()).hexdigest(),
                'clean_plate_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest()}
    products['art.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    return products


def build(check=False):
    products = exports()
    for name, content in products.items():
        path = OUTPUT/name
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f'Stale sanctuary art export: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(f'{"Verified" if check else "Exported"} sanctuary clean plate and '
          f'{len(products)-3} registered depth silhouettes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
