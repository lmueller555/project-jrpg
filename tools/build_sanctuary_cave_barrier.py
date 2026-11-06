"""Export the retained imagegen cave safety barrier as an isolated native prop.

This only crops and scales a transparent generated source. It never modifies
the sanctuary's existing ground, depth silhouettes, map, or runtime geometry.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/elden_vale_cave_barrier'
RECIPE = SOURCE / 'art_recipe.json'
OUTPUT = ROOT / 'assets/terrain/elden_vale_cave_barrier'


def exports():
    recipe = json.loads(RECIPE.read_text(encoding='utf-8'))
    for record in recipe['sources']:
        path = ROOT / record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Retained cave barrier source changed: {record["path"]}')
    with Image.open(ROOT / recipe['export_source']) as source:
        if source.mode != 'RGBA' or list(source.size) != recipe['source_size']:
            raise ValueError('Cave barrier source size or transparency differs from recipe')
        crop = source.crop(tuple(recipe['source_crop']))
        left, top, right, bottom = recipe['native_content_box']
        crop = crop.resize((right - left, bottom - top), Image.Resampling.NEAREST)
    native = Image.new('RGBA', tuple(recipe['native_size']))
    native.paste(crop, (left, top))
    if native.getchannel('A').getextrema() != (0, 255):
        raise ValueError('Cave barrier must retain transparent background and opaque prop pixels')
    stream = BytesIO()
    native.save(stream, format='PNG')
    entity = {
        'id': 'sanctuary_cave_safety_barrier',
        'frames': [recipe['image']],
        'position': recipe['position'],
        'ground_anchor': recipe['ground_anchor'],
        'sort_y': recipe['sort_y'],
        'frame_duration_ms': 1000,
        'phase_offset': 0,
    }
    manifest = {
        'version': 1,
        'image': recipe['image'],
        'native_size': recipe['native_size'],
        'position': recipe['position'],
        'ground_anchor': recipe['ground_anchor'],
        'local_ground_anchor': recipe['local_ground_anchor'],
        'sort_y': recipe['sort_y'],
        'solid_rect': recipe['solid_rect'],
        'interaction_approach': recipe['interaction_approach'],
        'entity': entity,
        'source_recipe': RECIPE.relative_to(ROOT).as_posix(),
        'source_recipe_sha256': hashlib.sha256(RECIPE.read_bytes()).hexdigest(),
    }
    return {
        'barrier.png': stream.getvalue(),
        'art.json': (json.dumps(manifest, indent=2) + '\n').encode(),
    }


def build(check=False):
    products = exports()
    for name, content in products.items():
        path = OUTPUT / name
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f'Stale cave barrier export: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(f'{"Verified" if check else "Exported"} isolated sanctuary cave safety barrier')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
