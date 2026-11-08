"""Build six colors of native wall-inset gemstones for the cave review.

Each module is a chipped recess in the same limestone as the cave wall. The
gem's facets sit behind the rock lips, rather than growing from a floor socket.
All six pulse frames keep fixed geometry, texture and hard-alpha silhouettes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import random

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/limestone_cave/wall_gems.json'
PACK = 'assets/terrain/limestone_cave/wall_gems'


def png(image):
    output = BytesIO();image.save(output,format='PNG');return output.getvalue()


def expanded(points, center, scale):
    cx,cy=center
    return [(round(cx+(x-cx)*scale),round(cy+(y-cy)*scale)) for x,y in points]


def tone(color, gain):
    return tuple(min(255,max(0,round(channel*gain))) for channel in color)


def quiet_stone(pixel):
    """Keep rock outside the production mineral self-emission heuristic."""
    channels=list(pixel[:3]);low=min(channels)
    if low>=180:channels=[value-(low-176) for value in channels]
    low=min(channels)
    channels=[min(value,low+24) for value in channels]
    return (*channels,pixel[3])


def products():
    spec = json.loads(SOURCE.read_text())
    wall_path = ROOT/spec['wall_texture']
    limestone_path = ROOT/spec['limestone_recipe']
    limestone = json.loads(limestone_path.read_text())['palette']
    ramp = [tuple(bytes.fromhex(value[1:])) for value in limestone['limestone']]
    with Image.open(wall_path) as image:wall=image.convert('RGBA')
    output={};modules={}

    def emit(path,value):
        output[path]=(png(value) if isinstance(value,Image.Image)
                      else (json.dumps(value,indent=2)+'\n').encode())

    def stone(variant,index):
        w,h=variant['size'];im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
        mask=Image.new('L',(w,h));ImageDraw.Draw(mask).polygon(variant['rock'],fill=255)
        for y in range(h):
            for x in range(w):
                pixel=wall.getpixel(((x+index*17+19)%wall.width,(y+12)%wall.height))
                if not pixel[3]:pixel=(*ramp[3],255)
                im.putpixel((x,y),quiet_stone(pixel))
        im.putalpha(mask)
        # Short natural fractures radiate into existing wall strata. They do
        # not form a metal bezel or a regular rim around the mineral core.
        d=ImageDraw.Draw(im)
        cx,cy=variant['anchor']
        fractures=[[(cx-7,cy-6),(cx-12,cy-9),(cx-14,cy-13)],
                   [(cx+7,cy+4),(cx+12,cy+7),(cx+14,cy+6)],
                   [(cx-5,cy+7),(cx-9,cy+12),(cx-13,cy+13)]]
        for points in fractures:
            d.line(points,fill=ramp[0],width=1)
            d.line([(x-1,y-1) for x,y in points[:2]],fill=ramp[5],width=1)
        rng=random.Random(742+index)
        for _ in range(24):
            x=rng.randrange(4,w-4);y=rng.randrange(5,h-4)
            if mask.getpixel((x,y)):
                color=rng.choice((ramp[2],ramp[4],ramp[5]))
                d.line((x,y,min(w-1,x+rng.randrange(1,3)),y),fill=color)
        im.putalpha(mask)
        return im,mask

    def module(variant,index,palette,level):
        im,mask=stone(variant,index);d=ImageDraw.Draw(im)
        core=variant['gem'];cx,cy=variant['anchor'];ridge=variant['ridge']
        cavity=expanded(core,(cx,cy),1.22)
        d.polygon(cavity,fill='#2b3631')
        # Slightly offset inner shadow makes the gem read as set into rock.
        d.line(cavity[:5],fill='#202c2b',width=2)
        gain=.68+.32*level/(spec['pulse_frames']-1)
        deep=tone(palette['deep'],.82+.18*level/(spec['pulse_frames']-1))
        mid=tone(palette['mid'],gain)
        bright=tone(palette['bright'],gain)
        glint=tone(palette['glint'],.76+.24*level/(spec['pulse_frames']-1))
        d.polygon(core,fill=deep)
        d.polygon([core[0],core[1],core[2],ridge,core[-1]],fill=bright)
        d.polygon([core[-1],ridge,core[5],core[6]],fill=mid)
        d.polygon([ridge,core[2],core[3],core[4],core[5]],fill=mid)
        d.polygon([ridge,core[4],core[5],core[6]],fill=deep)
        # Internal edges catch the pulse; fine fissures remain visible within
        # the gemstone, whose irregular outline stays wholly inside the wall.
        d.line([core[0],ridge,core[5]],fill=bright,width=1)
        d.line([core[1],ridge,core[3]],fill=glint,width=1)
        d.line([core[6],(ridge[0]-3,ridge[1]+3)],fill=mid,width=1)
        d.line([(ridge[0]+1,ridge[1]-3),(ridge[0]+2,ridge[1]-1)],fill=glint,width=1)
        # Fixed opaque rock lips cover the margins, embedding the mineral.
        for lip in variant['lips']:
            d.polygon(lip,fill=ramp[3])
            d.line(lip[:3],fill=ramp[5],width=1)
            d.line(lip[-2:],fill=ramp[1],width=1)
        im.putalpha(mask)
        return im

    for name,palette in spec['colors'].items():
        for index,variant in enumerate(spec['variants']):
            frames=[]
            for level in range(spec['pulse_frames']):
                image=module(variant,index,palette,level)
                path=f'{PACK}/{name}/variant_{index}/frame_{level:02}.png'
                emit(path,image);frames.append(path)
            xs=[x for x,y in variant['gem']];ys=[y for x,y in variant['gem']]
            modules[f'wall_gem.{name}.{index}']={
                'frames':frames,'size':variant['size'],'anchor':variant['anchor'],
                'color':palette['light'],'gem_color':name,'label':palette['label'],
                'emission_bounds':[min(xs),min(ys),max(xs)-min(xs)+1,max(ys)-min(ys)+1],
                'footprints':[],'mount':'embedded_wall','pulse_frames':spec['pulse_frames']}

    # This is an explicitly labelled material board. Every sprite and Caelan
    # share an exact 3x nearest-neighbour enlargement, with no painted mockup.
    board=Image.new('RGB',(1200,675),'#26322f');bd=ImageDraw.Draw(board)
    title=ImageFont.load_default(size=20);small=ImageFont.load_default(size=16)
    bd.text((20,14),'WALL-EMBEDDED GEMS / limestone recesses / native art enlarged 3x',fill='#e9e1ce',font=title)
    names=list(spec['colors'])
    for col,name in enumerate(names):
        x=20+col*194
        bd.text((x,52),spec['colors'][name]['label'],fill='#ece5d3',font=title)
        for row,variant in enumerate(spec['variants']):
            image=module(variant,row,spec['colors'][name],5)
            # Show the inset against its actual parent rock instead of making
            # an isolated icon that could be mistaken for loose jewelry.
            panel=Image.new('RGBA',(60,48));px=(60-image.width)//2;py=(48-image.height)//2
            for yy in range(panel.height):
                for xx in range(panel.width):
                    pixel=wall.getpixel(((xx-px+row*17+19)%wall.width,
                                         (yy-py+12)%wall.height))
                    if not pixel[3]:pixel=(*ramp[3],255)
                    panel.putpixel((xx,yy),quiet_stone(pixel))
            panel.alpha_composite(image,(px,py))
            scaled=panel.resize((panel.width*3,panel.height*3),Image.Resampling.NEAREST)
            board.paste(scaled,(x,88+row*154),scaled)
    ca_path=ROOT/'assets/characters/caelan/idle_front.png'
    with Image.open(ca_path) as image:ca=image.convert('RGBA')
    ca=ca.resize((ca.width*3,ca.height*3),Image.Resampling.NEAREST)
    board.paste(ca,(1055,552),ca)
    bd.text((20,573),'Facets brighten inside fixed limestone lips.',fill='#d0d8cd',font=small)
    bd.text((20,598),'Colored environmental light comes from the cave renderer.',fill='#d0d8cd',font=small)
    bd.text((20,627),'Six visual colors; elemental relationships remain unassigned.',fill='#bbc7bc',font=small)
    bd.text((940,654),'Caelan / same scale',fill='#e9e1ce',font=small)
    emit(f'{PACK}/colors_review.png',board)
    output[f'{PACK}/README.md']=(
        '# Embedded cave wall gems\n\n'
        'Status: pending visual review; not merged into the live game.\n\n'
        'Red, Blue, Green, White, Orange and Purple gemstones sit flush inside\n'
        'chipped limestone cavities. Fixed stone lips partially cover each\n'
        'mineral core. These modules have no floor footprint or standing shards.\n\n'
        'Each color has three native silhouettes and six frames of increasing\n'
        'facet brightness. Anchors point to the gem center, not the floor.\n'
        '`emission_bounds` records the core rectangle; the rock surround is\n'
        'kept below the production renderer\'s mineral emission thresholds.\n\n'
        'The existing six-second cave pulse selects the frame and illuminates\n'
        'nearby walls, floor and characters through an exposed light root.\n'
        'The colors do not establish elemental relationships.\n\n'
        'Rebuild with `python tools/build_wall_gems.py`; append `--check` for a\n'
        'read-only deterministic validation. The editable source recipe is\n'
        '`assets/source/terrain/limestone_cave/wall_gems.json`.\n'
    ).encode()
    inputs={str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest()
            for path in (SOURCE,wall_path,limestone_path,ca_path)}
    manifest={'version':1,'id':spec['id'],'approval_status':spec['approval_status'],
              'tile_size':24,'pulse_frames':spec['pulse_frames'],'colors':spec['colors'],
              'source_recipe':str(SOURCE.relative_to(ROOT)),'modules':modules,'inputs':inputs,
              'artifacts':{path:sha256(raw).hexdigest() for path,raw in output.items()}}
    emit(f'{PACK}/assets.json',manifest)
    return output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    output=products();changed=[]
    for relative,raw in output.items():
        path=ROOT/relative
        if not path.exists() or path.read_bytes()!=raw:
            changed.append(relative)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if args.check and changed:raise SystemExit('Stale wall gem exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(output)} wall gem exports')
    return 0


if __name__=='__main__':raise SystemExit(main())
