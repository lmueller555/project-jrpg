"""Export Aldric's approved brown-haired, navy-coated identity at native scale.

The portrait and cinematic body drawings are the canonical source. Head, coat
and boots have their own native registrations rather than an inherited gray
villager palette. The shared articulated gait keeps ordinary JRPG proportions.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw

if __package__:
    from .build_regent_page import png, standing, walking
else:
    from build_regent_page import png, standing, walking

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/story/regent_aldric'
OUT=ROOT/'assets/story/regent/actors/aldric'
DIRECTIONS=('front','left','right','back')
DRAW_ANCHOR=(12,30)
ART='assets/story/regent_arrival/actors/aldric/'


def _part(path, bounds, size):
    source=Image.open(ROOT/path).convert('RGBA')
    if path.endswith('aldric_neutral.png'):
        # The portrait's flat green backdrop is matte, not part of his head.
        # Brown hair and warm skin retain their exact approved source pixels.
        px=source.load()
        for y in range(source.height):
            for x in range(source.width):
                r,g,b,a=px[x,y]
                if g>r and g>b:px[x,y]=(0,0,0,0)
    image=source.crop(bounds).resize(size,Image.Resampling.NEAREST)
    image.putalpha(image.getchannel('A').point(lambda v:255 if v>=128 else 0))
    return image


def native_parts(direction):
    name='stand_right' if direction=='front' else 'stand_'+direction
    file=ART+name+'.png'
    if direction=='front':
        head=_part('assets/portraits/eldenmere/aldric_neutral.png',(14,0,58,44),(14,13))
        coat=_part(file,(27,28,55,73),(18,17))
        boots=_part(file,(28,73,54,92),(14,8))
    elif direction=='left':
        head=_part(file,(31,12,49,30),(14,13))
        coat=_part(file,(28,28,55,73),(14,17))
        boots=_part(file,(27,73,54,92),(10,8))
    elif direction=='right':
        head=_part(file,(33,12,52,30),(14,13))
        coat=_part(file,(27,28,55,73),(14,17))
        boots=_part(file,(28,73,54,92),(10,8))
    else:
        head=_part(file,(27,12,50,30),(14,13))
        coat=_part(file,(22,28,55,73),(18,17))
        boots=_part(file,(32,73,46,92),(14,8))
    return head,coat,boots


def seated(idle):
    image=idle.copy();image.paste((0,0,0,0),(0,26,24,36))
    draw=ImageDraw.Draw(image)
    draw.polygon(((5,23),(18,23),(20,28),(17,30),(12,28),(7,30),(4,28)),
                 fill='#263647',outline='#191e29')
    draw.line((6,25,11,27,17,26),fill='#52677d')
    draw.line((6,27,8,28),fill='#b99b62')
    draw.line((16,27,18,28),fill='#b99b62')
    for x in (7,17):
        draw.line((x,29,x,32),fill='#674731',width=3)
        draw.line((x-1,33,x+2,33),fill='#241e20',width=2)
    return image


def products():
    recipe=json.loads((SOURCE/'recipe.json').read_text())
    for path,digest in recipe['source_hashes'].items():
        if sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('Aldric canonical reference changed: '+path)
    sheet=Image.new('RGBA',(9*24,4*36));idles={};walks={}
    for row,direction in enumerate(DIRECTIONS):
        parts=native_parts(direction)
        image=standing(parts,direction)
        rect=[0,row*36,24,36];idles[direction]=rect
        sheet.alpha_composite(image,rect[:2]);walks[direction]=[]
        for phase in range(8):
            rect=[(phase+1)*24,row*36,24,36]
            sheet.alpha_composite(walking(parts,direction,phase),rect[:2])
            walks[direction].append({'rect':rect,'duration_ms':80})
    animation={'version':2,'canvas':[24,36],'draw_anchor':list(DRAW_ANCHOR),
               'foot_anchor':[12,34],'sheet':'assets/story/regent/actors/aldric/poses.png',
               'idles':idles,'walks':walks,'portrait':'aldric',
               'source_recipe':'assets/source/story/regent_aldric/recipe.json',
               'design':'Canonical brown-haired Aldric: navy travelling coat, brass edging, ivory collar and leather boots.'}
    return {OUT/'poses.png':png(sheet),OUT/'animation.json':(json.dumps(animation,indent=2)+'\n').encode(),
            ROOT/'assets/story/regent/poses/aldric_seated.png':png(seated(standing(native_parts('left'),'left')))}


def build(check=False):
    output=products();changed=[]
    for path,data in output.items():
        if not path.exists() or path.read_bytes()!=data:changed.append(path)
        if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if check and changed:raise SystemExit('Stale Aldric exports: '+', '.join(str(p.relative_to(ROOT)) for p in changed))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
