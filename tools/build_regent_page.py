"""Register the Page's canonical moss-coat design at native overworld scale.

The retained turnaround is exported as separately registered head, coat and
boots, so its large JRPG head and normal 24x36 ground scale are deliberate.
Eight articulated gait drawings retain the source materials, while native
ledger/hand drawings supply readable contact and one shared foot registration.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/story/regent_page'
OUT = ROOT/'assets/story/regent/actors/regent_clerk'
SIZE = (24, 36)
ANCHOR = (12, 30)
DIRECTIONS = ('front', 'left', 'right', 'back')
# Bounds in the retained source; each material is registered independently.
REGIONS = {
    'front': ((92,157,317,355), (50,350,363,782), (87,779,319,944)),
    'left': ((432,157,673,356), (440,350,676,783), (463,778,609,943)),
    'right': ((779,157,1017,356), (797,350,1018,785), (824,777,992,944)),
    'back': ((1126,157,1359,357), (1084,351,1402,784), (1127,778,1360,944)),
}
PALETTE = {
    'outline':'#241e20', 'coat_dark':'#292e23', 'coat':'#424936',
    'coat_light':'#666b46', 'gold':'#ae8544', 'gold_light':'#d2b475',
    'shirt':'#e4d6b1', 'shirt_dark':'#a99c7a', 'skin':'#dfad7d',
    'skin_light':'#f5c998', 'leather':'#674731', 'leather_dark':'#3c2c25',
    'paper':'#e8dbb3', 'paper_shadow':'#b5a580', 'ink':'#776a53',
}


def png(image):
    stream=BytesIO();image.save(stream,format='PNG',optimize=True)
    return stream.getvalue()


def _source():
    recipe=json.loads((SOURCE/'recipe.json').read_text())
    if sha256((SOURCE/recipe['source']).read_bytes()).hexdigest()!=recipe['source_sha256']:
        raise ValueError('Page source artwork differs from its registered recipe')
    image=Image.open(SOURCE/'turnaround_generated.png').convert('RGBA')
    pixels=image.load()
    for y in range(image.height):
        for x in range(image.width):
            r,g,b,a=pixels[x,y]
            if r>g*1.6 and b>g*1.6 and max(r,b)>60:pixels[x,y]=(0,0,0,0)
    return image


def parts(image, direction):
    head,coat,boots=REGIONS[direction]
    # One restrained shared source palette prevents per-frame color flicker.
    def section(rect, size):
        crop=image.crop(rect).resize(size,Image.Resampling.NEAREST)
        alpha=crop.getchannel('A').point(lambda v:255 if v>=128 else 0)
        rgb=crop.convert('RGB').quantize(colors=40,method=Image.Quantize.MEDIANCUT).convert('RGBA')
        rgb.putalpha(alpha)
        return rgb
    side=direction in ('left','right')
    return (section(head,(14,13)), section(coat,(14 if side else 18,17)),
            section(boots,(10 if side else 14,8)))


def standing(art, direction):
    head,coat,boots=art
    image=Image.new('RGBA',SIZE)
    image.alpha_composite(boots,((24-boots.width)//2,27))
    image.alpha_composite(coat,((24-coat.width)//2,12))
    image.alpha_composite(head,(5,0))
    return image


def walking(art, direction, phase):
    head,coat,boots=art
    image=Image.new('RGBA',SIZE)
    side=direction in ('left','right')
    near=(0,1,2,1,0,-1,-2,-1)[phase]
    lift=(0,0,0,-1,-2,-1,0,0)[phase]
    far=(0,-1,-2,-1,0,1,2,1)[phase]
    bob=(0,0,1,0,0,0,1,0)[phase]
    if side:
        # Profile boots are drawn as two separately articulated planted soles.
        floor=34
        d=ImageDraw.Draw(image)
        sign=-1 if direction=='left' else 1
        for step,raised,shade in ((far,lift,PALETTE['leather_dark']),
                                  (near,(0,-1,-2,-1,0,0,0,0)[phase],PALETTE['leather'])):
            ankle=12+step
            d.line((ankle,27,ankle,floor-1+raised),fill=shade,width=3)
            toe=ankle+3*sign
            d.line((ankle,floor+raised,toe,floor+raised),fill=PALETTE['outline'],width=2)
            d.point((toe,floor-1+raised),fill=PALETTE['leather'])
    else:
        left=boots.crop((0,0,boots.width//2,boots.height))
        right=boots.crop((boots.width//2,0,boots.width,boots.height))
        x=(24-boots.width)//2
        # Contact foot stays at y34 while its partner lifts through passing.
        left_y=(0,0,-1,-2,-1,0,0,0)[phase]
        right_y=(-1,0,0,0,0,0,-1,-2)[phase]
        image.alpha_composite(left,(x+(near//2),27+left_y))
        image.alpha_composite(right,(x+boots.width//2+(far//2),27+right_y))
    # Separate front/back coat tails swing one pixel across opposing legs.
    body_x=(24-coat.width)//2
    upper=coat.crop((0,0,coat.width,12))
    tails=coat.crop((0,12,coat.width,17))
    sway=(0,0,1,1,0,0,-1,-1)[phase]
    image.alpha_composite(tails,(body_x+sway,24+bob))
    image.alpha_composite(upper,(body_x,12+bob))
    image.alpha_composite(head,(5,bob))
    return image


def ledger_pose(idle, phase, *, lowering=False):
    """Six contact drawings: free folio, opening, settled spread and glance."""
    if lowering:phase=5-phase
    image=idle.copy();d=ImageDraw.Draw(image)
    # The native left-facing body supplies head/coat; sleeve and hands reach
    # toward the book instead of borrowing a differently proportioned figure.
    open_width=(3,4,6,8,9,9)[phase]
    y=(24,23,22,21,20,20)[phase]
    x=2 if phase>=2 else 5
    d.line((9,17,7,y+2,5,y+2),fill=PALETTE['outline'],width=3)
    d.line((9,17,7,y+1),fill=PALETTE['coat_light'],width=2)
    d.line((14,18,11,y+4,x+open_width-1,y+3),fill=PALETTE['coat_dark'],width=3)
    d.point((7,y+2),fill=PALETTE['skin'])
    d.polygon(((x,y),(x+open_width//2,y+1),(x+open_width,y),
               (x+open_width,y+6),(x+open_width//2,y+7),(x,y+5)),
              fill=PALETTE['leather_dark'],outline=PALETTE['outline'])
    if phase>=2:
        d.polygon(((x+1,y+1),(x+open_width//2,y+2),(x+open_width-1,y+1),
                   (x+open_width-1,y+5),(x+open_width//2,y+6),(x+1,y+4)),fill=PALETTE['paper'])
        d.line((x+open_width//2,y+2,x+open_width//2,y+6),fill=PALETTE['paper_shadow'])
        if phase>=4:
            d.line((x+1,y+3,x+2,y+3),fill=PALETTE['ink'])
            d.line((x+6,y+3,x+7,y+3),fill=PALETTE['ink'])
    else:d.line((x+1,y+1,x+1,y+4),fill=PALETTE['gold'])
    d.point((x+1,y+5),fill=PALETTE['skin_light'])
    d.point((x+open_width-1,y+5),fill=PALETTE['skin'])
    return image


def seated(idle):
    image=idle.copy();image.paste((0,0,0,0),(0,26,24,36))
    d=ImageDraw.Draw(image)
    # Bent coat tails keep the formal moss silhouette above the meal chair.
    d.polygon(((5,23),(18,23),(20,28),(17,30),(12,28),(7,30),(4,28)),
              fill=PALETTE['coat_dark'],outline=PALETTE['outline'])
    d.line((6,25,11,27,17,26),fill=PALETTE['coat_light'])
    for x in (7,17):
        d.line((x,29,x,32),fill=PALETTE['leather'],width=3)
        d.line((x-1,33,x+2,33),fill=PALETTE['outline'],width=2)
    return image


def products():
    image=_source();out={};idles={};walks={};poses={}
    sheet=Image.new('RGBA',(9*24,6*36))
    native={direction:parts(image,direction) for direction in DIRECTIONS}
    for row,direction in enumerate(DIRECTIONS):
        idle=standing(native[direction],direction)
        rect=[0,row*36,24,36];sheet.alpha_composite(idle,rect[:2]);idles[direction]=rect
        frames=[]
        for phase in range(8):
            frame=walking(native[direction],direction,phase)
            rect=[(phase+1)*24,row*36,24,36]
            sheet.alpha_composite(frame,rect[:2]);frames.append({'rect':rect,'duration_ms':80})
        walks[direction]=frames
    left=standing(native['left'],'left')
    for row,name in ((4,'read'),(5,'read_lower')):
        frames=[]
        for phase in range(6):
            frame=ledger_pose(left,phase,lowering=name=='read_lower')
            rect=[phase*24,row*36,24,36];sheet.alpha_composite(frame,rect[:2])
            frames.append({'rect':rect,'duration_ms':(140,110,100,140,180,200)[phase]})
        poses[name]={'frames':frames,'loop':False,'facing':'left'}
    out[OUT/'poses.png']=png(sheet)
    out[ROOT/'assets/story/regent/poses/clerk_seated.png']=png(seated(standing(native['front'],'front')))
    manifest={'version':2,'canvas':list(SIZE),'draw_anchor':list(ANCHOR),'foot_anchor':[12,34],
              'sheet':'assets/story/regent/actors/regent_clerk/poses.png','idles':idles,'walks':walks,
              'poses':poses,'portrait':'regent_page',
              'source_recipe':'assets/source/story/regent_page/recipe.json',
              'design':'Canonical brown-haired Page; moss-green coat, ivory collar, brass trim, leather folio.'}
    out[OUT/'animation.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    return out


def build(check=False):
    output=products();changed=[]
    for path,data in output.items():
        if not path.exists() or path.read_bytes()!=data:changed.append(path)
        if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if check and changed:raise SystemExit('Stale Page exports: '+', '.join(str(p.relative_to(ROOT)) for p in changed))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
