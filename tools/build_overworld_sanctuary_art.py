"""Export the approved sanctuary miniature into the native overworld prop kit.

The generated source remains unchanged. Both exports use one uniform nearest
scale and hard alpha; no scene image, collider or entry trigger is produced.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT/'assets/source/terrain/overworld/elden_vale/sanctuary/recipe.json'
OUT = ROOT/'assets/terrain/overworld/elden_vale/sanctuary'


def exports():
    recipe = json.loads(RECIPE.read_text())
    path = ROOT/recipe['source']
    if hashlib.sha256(path.read_bytes()).hexdigest() != recipe['source_sha256']:
        raise ValueError('Sanctuary source artwork changed')
    source = Image.open(path).convert('RGBA')
    source.putalpha(source.getchannel('A').point(
        lambda value: 255 if value >= recipe['alpha_threshold'] else 0))
    files = {};props = {}
    for key, record in recipe['exports'].items():
        crop = source.crop(record['crop'])
        ratio = min(a/b for a, b in zip(record['fit'], crop.size))
        size = tuple(max(1, round(dimension*ratio)) for dimension in crop.size)
        image = crop.resize(size, Image.Resampling.NEAREST)
        canvas = Image.new('RGBA', tuple(record['canvas']))
        bottom = int(record['paste'].rsplit('_', 1)[1])
        canvas.alpha_composite(image, ((canvas.width-image.width)//2, bottom-image.height))
        # Transparent pixels carry no matte color into scaling or icon exports.
        pixels = canvas.load()
        for y in range(canvas.height):
            for x in range(canvas.width):
                if not pixels[x, y][3]:pixels[x, y] = (0, 0, 0, 0)
        data = BytesIO();canvas.save(data, format='PNG')
        files[key+'.png'] = data.getvalue()
        props[key] = {'image': (OUT/(key+'.png')).relative_to(ROOT).as_posix(),
                      'foot_anchor': record['foot_anchor']}
    manifest = {'version': 1, 'tiles': {}, 'props': props,
                'source_recipe': RECIPE.relative_to(ROOT).as_posix(),
                'source_recipe_sha256': hashlib.sha256(RECIPE.read_bytes()).hexdigest()}
    files['art.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = exports()
    if args.check:
        stale = [name for name, data in files.items()
                 if not (OUT/name).exists() or (OUT/name).read_bytes() != data]
        if stale:raise SystemExit('Stale sanctuary exports: '+', '.join(stale))
        print('Sanctuary native exports match their retained source.')
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():(OUT/name).write_bytes(data)
    print('Exported sanctuary miniature, steps and prop manifest.')


if __name__ == '__main__':main()
