"""Assemble the regional Sanctuary icon from its native landmark modules.

The compact icon shares the reserve's hall, crystal and tree pixels. Uniform
nearest-neighbour reduction preserves native facets; no scenery painting,
collision mask, scene transfer or regional geography is authored here.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

if __package__:
    from .reserve_stone_kit import make_kit
else:
    from reserve_stone_kit import make_kit


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT/'assets/source/terrain/overworld/elden_vale/sanctuary/recipe.json'
OUT = ROOT/'assets/terrain/overworld/elden_vale/sanctuary'


def exports():
    recipe = json.loads(RECIPE.read_text())
    kit, kit_metadata = make_kit()
    used = {ROOT/'tools/reserve_stone_kit.py', RECIPE}
    used.update(ROOT/path for path in kit_metadata['source_sha256'])
    libraries = {}
    for name, filename in recipe['libraries'].items():
        path = ROOT/filename
        used.add(path)
        libraries[name] = json.loads(path.read_text())
    grounding={}
    for name,filename in recipe['grounding']['materials'].items():
        path=ROOT/filename;used.add(path)
        grounding[name]=Image.open(path).convert('RGBA')

    def module(library, identifier):
        if library == 'kit':return kit[identifier].copy()
        record = libraries[library]['modules'][identifier]
        frame = record['frames'][0]
        filename = frame['image'] if isinstance(frame, dict) else frame
        path = ROOT/filename
        used.add(path)
        return Image.open(path).convert('RGBA')

    def component(record):
        names = record.get('modules', [record.get('module')])
        images = [module(record['library'], identifier) for identifier in names]
        image = images[0].copy()
        for layer in images[1:]:image.alpha_composite(layer)
        bounds = image.getchannel('A').getbbox()
        if bounds is None:raise ValueError('Empty Sanctuary icon component')
        image = image.crop(bounds)
        ratio = min(a/b for a,b in zip(record['fit'],image.size))
        size = tuple(max(1,round(dimension*ratio)) for dimension in image.size)
        return image.resize(size,Image.Resampling.NEAREST)

    files = {};props = {}
    for key, record in recipe['exports'].items():
        canvas = Image.new('RGBA',tuple(record['canvas']))
        def textured_patch(points,material):
            mask=Image.new('L',canvas.size)
            ImageDraw.Draw(mask).polygon([tuple(point) for point in points],fill=255)
            texture=Image.new('RGBA',canvas.size)
            tile=grounding[material]
            for y in range(0,canvas.height,tile.height):
                for x in range(0,canvas.width,tile.width):texture.alpha_composite(tile,(x,y))
            canvas.paste(texture,(0,0),mask)
        # Small, disconnected native regional-grass footings leave the world
        # visible between them. No colored island or vertical ground skirt is
        # introduced beneath the compact architecture and landmark tree.
        for patch in recipe['grounding']['patches']:
            textured_patch(patch,'grass')
        for part in recipe['components']:
            image = component(part)
            canvas.alpha_composite(image,tuple(part['position']))
        # A short maintained approach meets the unchanged [32,74] registration.
        textured_patch(recipe['grounding']['approach'],'dirt')
        alpha=canvas.getchannel('A').point(lambda value:255 if value>=128 else 0)
        canvas.putalpha(alpha)
        canvas.putdata([pixel if pixel[3] else (0,0,0,0)
                        for pixel in canvas.get_flattened_data()])
        data=BytesIO();canvas.save(data,format='PNG');files[key+'.png']=data.getvalue()
        props[key]={'image':(OUT/(key+'.png')).relative_to(ROOT).as_posix(),
                    'foot_anchor':record['foot_anchor']}
    manifest={'version':2,'authoring':'native_pixel_asset_assembly','tiles':{},'props':props,
              'source_recipe':RECIPE.relative_to(ROOT).as_posix(),
              'source_recipe_sha256':hashlib.sha256(RECIPE.read_bytes()).hexdigest(),
              'source_assets':[{'path':path.relative_to(ROOT).as_posix(),
                                'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                               for path in sorted(used)],
              'components':recipe['components'],'grounding':recipe['grounding']}
    files['art.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    return files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args();files=exports()
    if args.check:
        stale=[name for name,data in files.items()
               if not (OUT/name).is_file() or (OUT/name).read_bytes()!=data]
        if stale:raise SystemExit('Stale Sanctuary miniature: '+', '.join(stale))
        print('Verified native Sanctuary landmark miniature.')
        return
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(OUT/name).write_bytes(data)
    print('Exported native Sanctuary landmark miniature.')


if __name__=='__main__':main()
