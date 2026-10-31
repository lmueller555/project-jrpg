#!/usr/bin/env python3
"""Export original countryside generations to the Elden Vale native art API.

The four source sheets are retained unaltered. Export operations are limited to
documented crops, alpha cleanup, uniform nearest-neighbour scale, palette
reduction and transparent padding. This tool does not paint illustrations.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/overworld/elden_vale/polish'
OUTPUT = ROOT / 'assets/terrain/overworld/elden_vale/polish'


def clean_alpha(image, threshold):
    image = image.convert('RGBA')
    # Generated transparent gutters can contain vivid RGB at alpha 1. Threshold
    # alpha before cropping/palette selection so these invisible fringes never
    # become outlines or contaminate the native palette. Opaque apples remain.
    image.putalpha(image.getchannel('A').point(lambda value: 255 if value >= threshold else 0))
    return image


def native_image(spec, recipe, *, prop):
    with Image.open(SOURCE / spec['source']) as sheet:
        image = clean_alpha(sheet.crop(spec['crop']), recipe['alpha_threshold'])
    size = tuple(spec['size'])
    if prop:
        box = image.getbbox()
        if box is None:
            raise ValueError(f'Empty generated crop: {spec}')
        image = image.crop(box)
        factor = min(size[0] / image.width, size[1] / image.height)
        image = image.resize((max(1, round(image.width * factor)),
                              max(1, round(image.height * factor))), Image.Resampling.NEAREST)
        result = Image.new('RGBA', size)
        result.alpha_composite(image, ((size[0] - image.width) // 2, size[1] - image.height))
        image = result
    else:
        image = image.resize(size, Image.Resampling.NEAREST)
    alpha = image.getchannel('A')
    image = image.convert('RGB').quantize(
        colors=recipe['prop_palette_colors' if prop else 'tile_palette_colors'],
        dither=Image.Dither.NONE).convert('RGBA')
    image.putalpha(alpha)
    return clean_alpha(image, recipe['alpha_threshold'])


def png_bytes(image):
    output = BytesIO()
    image.save(output, format='PNG', optimize=True)
    return output.getvalue()


def contact_sheet(images):
    """Asset review diagram: labels and enlarged native sprites only."""
    width, cell_width, cell_height = 1024, 256, 172
    rows = (len(images) + 3) // 4
    diagram = Image.new('RGB', (width, rows * cell_height), '#34433a')
    draw = ImageDraw.Draw(diagram)
    font = ImageFont.load_default()
    for index, (key, image) in enumerate(images.items()):
        x, y = index % 4 * cell_width, index // 4 * cell_height
        factor = min(3, 230 // image.width, 140 // image.height)
        enlarged = image.resize((image.width * factor, image.height * factor), Image.Resampling.NEAREST)
        diagram.paste(enlarged, (x + (cell_width - enlarged.width) // 2,
                                 y + 146 - enlarged.height), enlarged)
        draw.text((x + 8, y + 152), f'{key}  {image.width}x{image.height}', font=font, fill='#ece6cf')
    return diagram


def build(check=False):
    recipe = json.loads((SOURCE / 'recipe.json').read_text())
    for record in recipe['source_records']:
        if hashlib.sha256((ROOT / record['file']).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Unaltered source hash differs: {record["file"]}')
    manifest = {'version': 1, 'tiles': {}, 'props': {}}
    products, images = {}, {}
    for kind in ('tiles', 'props'):
        for key, spec in recipe[kind].items():
            image = native_image(spec, recipe, prop=kind == 'props')
            alpha = set(image.getchannel('A').tobytes())
            if not alpha <= {0, 255} or not image.getbbox():
                raise ValueError(f'Invalid native alpha: {key}')
            if kind == 'tiles' and alpha != {255}:
                raise ValueError(f'Texture is not opaque: {key}')
            path = OUTPUT / kind / (key + '.png')
            products[path] = png_bytes(image)
            manifest[kind][key] = {'image': path.relative_to(ROOT).as_posix()}
            if kind == 'props':
                manifest[kind][key]['foot_anchor'] = spec['foot_anchor']
            images[key] = image
    products[OUTPUT / 'art.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    products[SOURCE / 'native_review.png'] = png_bytes(contact_sheet(images))
    stale = []
    for path, content in products.items():
        if check:
            if not path.exists() or path.read_bytes() != content:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if stale:
        raise SystemExit('Stale native art: ' + ', '.join(stale))
    print(f'{"Verified" if check else "Exported"} {len(images)} native PNGs, art manifest and review sheet')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify byte-for-byte reproducible outputs')
    build(parser.parse_args().check)
