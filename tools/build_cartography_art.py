"""Export original cartographic sheets to native materials and illustrations.

Sources remain unmodified image generations. This exporter only crops, scales
uniformly with nearest-neighbour sampling, reduces palettes, cleans alpha and
pads transparent canvases. Runtime geography belongs to the separate survey
and atlas-tile builder.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/cartography/elden_vale'
OUTPUT = ROOT / 'assets/cartography/elden_vale/art'


def clean_alpha(image, threshold):
    image = image.convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda value: 255 if value >= threshold else 0))
    return image


def remove_specks(image):
    """Discard isolated one/two-pixel alpha fragments left by sheet gutters."""
    alpha = image.getchannel('A')
    pixels = alpha.load();visited = set()
    for y in range(image.height):
        for x in range(image.width):
            if not pixels[x,y] or (x,y) in visited:continue
            pending = [(x,y)];component = [];visited.add((x,y))
            while pending:
                px,py = pending.pop();component.append((px,py))
                for nx in range(max(0,px-1),min(image.width,px+2)):
                    for ny in range(max(0,py-1),min(image.height,py+2)):
                        if pixels[nx,ny] and (nx,ny) not in visited:
                            visited.add((nx,ny));pending.append((nx,ny))
            if len(component) <= 2:
                for px,py in component:pixels[px,py] = 0
    image.putalpha(alpha)
    return image


def export(spec, recipe, transparent):
    image = Image.open(SOURCE/spec['source']).convert('RGBA').crop(spec['crop'])
    image = clean_alpha(image, recipe['alpha_threshold'])
    size = tuple(spec['size'])
    if transparent:
        box = image.getbbox()
        if box is None:raise ValueError(f'Empty illustration: {spec}')
        image = image.crop(box)
        ratio = min(size[0]/image.width, size[1]/image.height)
        image = image.resize((max(1, round(image.width*ratio)), max(1, round(image.height*ratio))),
                             Image.Resampling.NEAREST)
        canvas = Image.new('RGBA', size)
        canvas.alpha_composite(image, ((size[0]-image.width)//2, size[1]-image.height))
        image = canvas
        colors = recipe['mass_colors'] if spec.get('role') == 'mass' else recipe['icon_colors']
    else:
        if image.width != image.height:raise ValueError('Material source crop must be square')
        image = image.resize(size, Image.Resampling.NEAREST)
        colors = recipe['material_colors']
    alpha = image.getchannel('A')
    image = image.convert('RGB').quantize(colors=colors, dither=Image.Dither.NONE).convert('RGBA')
    image.putalpha(alpha)
    image = clean_alpha(image, recipe['alpha_threshold'])
    return remove_specks(image) if transparent else image


def png(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def build(check=False):
    recipe = json.loads((SOURCE/'recipe.json').read_text())
    for record in recipe['source_records']:
        path = ROOT/record['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Unaltered generation differs: {record["file"]}')
    manifest = {'version': 1, 'tiles': {}, 'props': {}}
    products = {}
    images = []
    for kind in ('tiles', 'props'):
        for key,spec in recipe[kind].items():
            path = OUTPUT/kind/f'{key}.png'
            image = export(spec, recipe, kind == 'props')
            products[path] = png(image)
            entry = {'image': path.relative_to(ROOT).as_posix(), 'native_size': list(image.size)}
            if kind == 'props':
                entry.update(foot_anchor=spec['foot_anchor'], role=spec['role'])
            manifest[kind][key] = entry
            images.append((key, image))
    products[OUTPUT/'art.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    columns,cell = 4,280
    review = Image.new('RGB', (columns*cell, ((len(images)+columns-1)//columns)*cell), '#d6d4bc')
    draw = ImageDraw.Draw(review);font = ImageFont.load_default()
    for index,(key,image) in enumerate(images):
        x,y = index%columns*cell,index//columns*cell
        review.paste(image, (x+(cell-image.width)//2,y+8), image)
        draw.text((x+10,y+264),f'{key} {image.width}x{image.height}',font=font,fill='#243d33')
    products[SOURCE/'native_review.png'] = png(review)
    stale = []
    for path,content in products.items():
        if check:
            if not path.exists() or path.read_bytes() != content:stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(content)
    if stale:raise SystemExit('Cartographic art is stale: '+', '.join(stale))
    print(f'{"Verified" if check else "Exported"} {len(images)} cartographic materials/illustrations and art.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
