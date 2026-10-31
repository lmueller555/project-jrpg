"""Export the wide bridge without changing its generated stone proportions.

The two abutments are isolated by the generation's transparent central gap.
One uniform resize establishes the road depth; transparent canvas padding
between the cropped abutments restores the authored 288px river span.
Only crop, uniform nearest scaling, palette/alpha cleanup and padding touch
runtime pixels. Rulers/text appear only in the separate source review image.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/overworld/elden_vale/composition'
OUTPUT = ROOT/'assets/terrain/overworld/elden_vale/composition'


def png(image):
    buffer = BytesIO();image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def export(spec, recipe):
    with Image.open(SOURCE/spec['source']) as original:
        image = original.convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda a:255 if a>=recipe['alpha_threshold'] else 0))
    if 'uniform_resize' in spec:
        size = spec['uniform_resize']
        if abs(size[0]/image.width-size[1]/image.height)>1e-9:
            raise ValueError('Native export must preserve source proportions')
        image = image.resize(size, Image.Resampling.NEAREST)
    if 'crop' in spec:image = image.crop(spec['crop'])
    if spec.get('components'):
        native = Image.new('RGBA',spec['size'])
        for component in spec['components']:
            native.alpha_composite(image.crop(component['crop']),component['position'])
        image = native
    elif image.size != tuple(spec['size']):
        scale=min(spec['size'][0]/image.width,spec['size'][1]/image.height)
        image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.NEAREST)
        native=Image.new('RGBA',spec['size'])
        native.alpha_composite(image,((native.width-image.width)//2,native.height-image.height));image=native
    alpha=image.getchannel('A')
    image=image.convert('RGB').quantize(colors=recipe['palette_colors'],dither=Image.Dither.NONE).convert('RGBA')
    image.putalpha(alpha)
    return image


def review(image, spec):
    canvas=Image.new('RGB',(1200,680),'#293d35')
    canvas.paste(image.resize((1152,576),Image.Resampling.NEAREST),(24,56),image.resize((1152,576),Image.Resampling.NEAREST))
    draw=ImageDraw.Draw(canvas);font=ImageFont.load_default()
    draw.text((24,12),'BROKEN WESTERN BRIDGE - native 288 x 144; clear roadway 3 x 24px',font=font,fill='#f6e8c8')
    top=56+spec['deck_top_px']*4;bottom=56+spec['deck_bottom_px']*4
    x=24+spec['deck_sample_x_px'][0]*4
    draw.line((x,top,x,bottom),fill='#f3d07b',width=3)
    for i in range(4):
        y=top+i*24*4;draw.line((x-14,y,x+14,y),fill='#f3d07b',width=3)
    draw.text((24,650),'Review-only ruler: 72 native pixels between parapets; source stone geometry uniformly scaled, abutments padded apart.',font=font,fill='#f6e8c8')
    return canvas


def build(check=False):
    recipe=json.loads((SOURCE/'recipe.json').read_text())
    for source in recipe['source_records']:
        if hashlib.sha256((ROOT/source['file']).read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Unaltered generated source changed: '+source['file'])
    products={};manifest={'version':1,'tiles':{},'props':{}}
    for key,spec in recipe['props'].items():
        image=export(spec,recipe)
        if image.size!=tuple(spec['size']):raise ValueError('Wrong native size: '+key)
        if set(image.getchannel('A').tobytes())- {0,255}:raise ValueError('Nonbinary alpha: '+key)
        path=OUTPUT/'props'/f'{key}.png';products[path]=png(image)
        entry={'image':path.relative_to(ROOT).as_posix(),'foot_anchor':spec['foot_anchor']}
        if key=='broken_bridge_wide':
            top,bottom=spec['deck_top_px'],spec['deck_bottom_px']
            if bottom-top!=72 or spec['deck_clear_width_px']!=72:raise ValueError('Roadway must be exactly three tiles')
            if spec['foot_anchor']!=[144,(top+bottom)//2+24]:raise ValueError('Roadway anchor disagrees with the global centerline')
            gap=spec['central_gap_x_px']
            if image.getchannel('A').crop((gap[0],0,gap[1],image.height)).getbbox():raise ValueError('Broken span must remain transparent')
            for name in ('deck_top_px','deck_bottom_px','deck_clear_width_px','deck_sample_x_px','central_gap_x_px'):entry[name]=spec[name]
            products[SOURCE/'native_width_review.png']=png(review(image,spec))
        manifest['props'][key]=entry
    products[OUTPUT/'art.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    for path,data in products.items():
        if check:
            if not path.exists() or path.read_bytes()!=data:raise ValueError('Generated output is stale: '+path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print(f"{'Verified' if check else 'Exported'} {len(recipe['props'])} composition props and bridge width metadata")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
