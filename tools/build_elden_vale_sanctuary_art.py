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


def foliage_gaps(mask, native):
    """Exclude path/limestone visible between the immutable source's leaves.

    Semantic crown outlines supply the object boundary. This palette gate only
    clears pale neutral stone and warm bare soil inside those outlines; trunks
    and branches have separate, tightly traced solid polygons.
    """
    bounds = mask.getbbox()
    if bounds is None:return
    alpha = mask.load();pixels = native.load()
    for y in range(bounds[1], bounds[3]):
        for x in range(bounds[0], bounds[2]):
            if not alpha[x,y]:continue
            red, green, blue = pixels[x,y]
            # Dark, low-saturation pixels include the oak's real branchwork.
            # Only pale neutral gaps are stone; filtering every muted pixel
            # punched holes through brown trunks and branches in all crowns.
            stone = min(red,green,blue) > 85 and blue > green*.73
            soil = red > 125 and red > green*1.15 and blue > green*.45
            if stone or soil:alpha[x,y] = 0


def profile_y(points, x):
    if x <= points[0][0]:return points[0][1]
    for start,end in zip(points,points[1:]):
        if x <= end[0]:
            fraction = (x-start[0])/(end[0]-start[0])
            return start[1]+fraction*(end[1]-start[1])
    return points[-1][1]


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
        parts = record.get('parts', [{'polygon':record.get('polygon',[])}])
        for part in parts:
            layer = Image.new('L', native.size)
            points = [(round(x*scale_x),round(y*scale_y)) for x,y in part['polygon']]
            ImageDraw.Draw(layer).polygon(points,fill=255)
            if part.get('material') == 'foliage':foliage_gaps(layer,native)
            mask.paste(255,mask=layer)
        painter = ImageDraw.Draw(mask)
        for opening in record.get('openings', []):
            painter.polygon([(round(x*scale_x), round(y*scale_y)) for x, y in opening], fill=0)
        bounds = mask.getbbox()
        if bounds is None:raise ValueError(f'Empty sanctuary depth silhouette: {record["id"]}')
        slices = [(record['id'],mask,record['baseline'])]
        if record.get('baseline_profile'):
            slices = []
            step = max(1,round(record.get('strip_width',24)*scale_x))
            for index,left in enumerate(range(bounds[0],bounds[2],step)):
                right = min(bounds[2],left+step)
                strip = Image.new('L',native.size)
                strip.paste(mask.crop((left,bounds[1],right,bounds[3])),(left,bounds[1]))
                if strip.getbbox():
                    x = (left+right)/(2*scale_x)
                    slices.append((record['id']+f'_{index:02}',strip,
                                   profile_y(record['baseline_profile'],x)))
        for identifier,alpha,baseline in slices:
            bounds = alpha.getbbox()
            surface = native.convert('RGBA');surface.putalpha(alpha)
            surface = surface.crop(bounds)
            # Transparent pixels never carry a rectangular ground-colored matte.
            surface.paste((0,0,0,0),mask=surface.getchannel('A').point(lambda value:255-value))
            name = 'depth/'+identifier+'.png'
            products[name] = encoded(surface)
            entity = {'id':identifier,'source_id':record['id'],
                      'frames':[(OUTPUT/name).relative_to(ROOT).as_posix()],
                      'position':list(bounds[:2]),'sort_y':round(baseline*scale_y),
                      'frame_duration_ms':1000,'phase_offset':0}
            if 'ground_anchor' in record:
                entity['ground_anchor'] = [round(value*scale) for value,scale in
                                           zip(record['ground_anchor'],(scale_x,scale_y))]
            entities.append(entity)
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
    expected = {OUTPUT/name for name in products}
    obsolete = [path for path in (OUTPUT/'depth').glob('*.png') if path not in expected]
    if check and obsolete:raise ValueError('Obsolete sanctuary depth exports remain')
    for name, content in products.items():
        path = OUTPUT/name
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f'Stale sanctuary art export: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if not check:
        for path in obsolete:path.unlink()
    print(f'{"Verified" if check else "Exported"} sanctuary clean plate and '
          f'{len(products)-3} registered depth silhouettes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
