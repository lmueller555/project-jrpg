"""Build loose geology and entrance treatments for the limestone cave pack.

The palette and fine texture come from the existing limestone, grass and grove
recipes. New native silhouettes supply erosion, fragments, roots and mineral
deposits without changing any approved map or asset. Only raised slabs block.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_limestone_cave_assets import Author

SOURCE = ROOT/'assets/source/terrain/limestone_cave/geology.json'
PACK = 'assets/terrain/limestone_cave/geology'
DIRECTIONS = ('north', 'east', 'south', 'west', 'outer_ne', 'outer_se',
              'outer_sw', 'outer_nw', 'inner_ne', 'inner_se', 'inner_sw', 'inner_nw')


def rgb(value):return tuple(bytes.fromhex(value.removeprefix('#')))


def png(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


class GeologyAuthor:
    def __init__(self):
        self.spec=json.loads(SOURCE.read_text());self.base=Author()
        self.stone=self.base.ramps['limestone']
        self.grove=json.loads((ROOT/self.spec['grove_recipe']).read_text())['palette']
        self.grass=json.loads((ROOT/self.spec['grass_recipe']).read_text())['palette']
        self.earth=[rgb(v) for v in self.spec['earth_palette']]
        self.leaves=[rgb(v) for v in self.spec['leaf_palette']]
        self.outputs={};self.modules={}

    def emit(self,path,value):
        self.outputs[path]=(png(value) if isinstance(value,Image.Image) else
                            (json.dumps(value,indent=2)+'\n').encode())

    def texture_shape(self,canvas,polygon,seed,bias=0):
        image=self.base.texture(canvas,seed,bias=bias)
        mask=Image.new('L',canvas);ImageDraw.Draw(mask).polygon(polygon,fill=255)
        image.putalpha(mask)
        return image

    def pebble(self,target,x,y,w,h,seed):
        rng=random.Random(seed)
        points=[(x-w//2,y),(x-w//2+1,y-h//2),(x-1,y-h),
                (x+w//3,y-h+1),(x+w//2,y-h//3),(x+w//2-1,y+1),(x,y+2)]
        image=self.texture_shape(target.size,points,seed,bias=rng.choice((-.3,.1,.4)))
        d=ImageDraw.Draw(image)
        d.line(points[:4],fill=self.stone[5])
        d.line(points[4:]+[points[0]],fill=self.stone[1])
        if w>8:d.line([(x-1,y-h+1),(x-2,y-h//2),(x+1,y)],fill=self.stone[2])
        target.alpha_composite(image)

    def debris(self,kind,index):
        size=tuple(self.spec['families'][kind]);w,h=size
        im=Image.new('RGBA',size);rng=random.Random(self.spec['seed']+index*31+len(kind)*103)
        counts={'debris.pebbles':7,'debris.rubble':18,'debris.talus':37}
        # Stone chips remain separate and small enough to read as a walkable
        # scatter. The fan narrows toward a wall fracture and spreads below it.
        candidates=[]
        for ordinal in range(counts[kind]):
            if kind=='debris.talus':
                y=rng.randrange(7,h-3);spread=8+(y/h)*(w*.42)
                x=round(w*.5+rng.uniform(-spread,spread))
            else:x=rng.randrange(4,w-3);y=rng.randrange(7,h-3)
            x=max(4,min(w-5,x));pw=rng.randrange(3,9 if kind=='debris.pebbles' else 12)
            ph=rng.randrange(2,5 if kind=='debris.pebbles' else 7)
            candidates.append((y,x,pw,ph,ordinal))
        for y,x,pw,ph,ordinal in sorted(candidates):self.pebble(im,x,y,pw,ph,ordinal+index*47)
        # Fine loose grit between the chips, in quiet source-material colors.
        d=ImageDraw.Draw(im)
        for _ in range(16 if kind!='debris.talus' else 42):
            x=rng.randrange(2,w-2);y=rng.randrange(2,h-2)
            if kind!='debris.talus' or abs(x-w/2)<8+y/w*40:
                d.line((x,y,x+1,y),fill=self.stone[rng.choice((2,3,5))])
        return im

    def slab(self,index):
        size=tuple(self.spec['families']['slab.fallen']);w,h=size
        rng=random.Random(428+index);im=Image.new('RGBA',size)
        # A shallow raised fragment: its top is naturally fractured and the
        # front edge has several thin strata. The collision hugs that base.
        points=[tuple(point) for point in self.spec['slab_outlines'][index]]
        for layer in (7,5,3):
            poly=[(x,y+layer) for x,y in points]
            part=self.texture_shape(size,poly,index+522,bias=-.7)
            ImageDraw.Draw(part).line(poly[4:]+[poly[0]],fill=self.stone[0],width=1)
            im.alpha_composite(part)
        top=self.texture_shape(size,points,index+816,bias=.35);d=ImageDraw.Draw(top)
        d.line(points[:5],fill=self.stone[6]);d.line(points[5:]+[points[0]],fill=self.stone[2])
        trace=[(29,9),(27,16),(32,23),(29,31),(36,36)]
        d.line(trace,fill=self.stone[1]);d.line([(x+1,y) for x,y in trace[:3]],fill=self.stone[5])
        d.line([(31,23),(42,20),(51,24)],fill=self.stone[2])
        for _ in range(15):
            x=rng.randrange(14,57);y=rng.randrange(15,29)
            if top.getpixel((x,y))[3]:d.line((x,y,x+2,y),fill=rng.choice((self.stone[3],self.stone[5])))
        im.alpha_composite(top)
        return im

    def cracks(self,index,channel=False):
        family='erosion.channel' if channel else 'crack.branching'
        size=tuple(self.spec['families'][family]);im=Image.new('RGBA',size);d=ImageDraw.Draw(im)
        rng=random.Random(index+920+(80 if channel else 0));w,h=size
        branches=[[tuple(point) for point in branch]
                  for branch in self.spec['crack_graphs'][index]]
        for ordinal,points in enumerate(branches):
            if channel:
                d.line([(x,y+1) for x,y in points],fill='#9b9d87',width=5 if ordinal==0 else 3)
                d.line(points,fill='#5d746b',width=3 if ordinal==0 else 2)
                d.line([(x,y-1) for x,y in points],fill='#405b57',width=1)
                for x,y in points[1:-1]:d.line((x+2,y+2,x+4,y+2),fill='#b6b59b')
            else:
                d.line([(x-1,y-1) for x,y in points],fill=self.stone[5])
                d.line(points,fill=self.stone[0],width=2 if ordinal==0 else 1)
                d.line([(x+1,y+1) for x,y in points[1:]],fill=self.stone[2])
        return im

    def crust(self,index,damp=False):
        size=tuple(self.spec['families']['stain.damp' if damp else 'mineral.crust'])
        w,h=size;im=Image.new('RGBA',size);d=ImageDraw.Draw(im);rng=random.Random(1169+index)
        palette=self.base.ramps['damp'] if damp else [self.stone[3],self.stone[5],self.stone[6],rgb('#d4cdb6')]
        for _ in range(90 if damp else 60):
            a=rng.random()*math.tau;r=rng.random()**.6
            x=round(w/2+math.cos(a)*w*.43*r);y=round(h/2+math.sin(a)*h*.37*r)
            size=rng.randrange(2,7 if damp else 5)
            p=[(x,y),(x+size,y+1),(x+size-1,y+3),(x+1,y+3)]
            d.polygon(p,fill=rng.choice(palette))
        if not damp:
            for yy in range(8,h-5,7):
                d.line([(4,yy),(14,yy-2),(21,yy+1),(32,yy),(43,yy-2)],fill=self.stone[6])
        return im

    def roots(self,index):
        w,h=self.spec['families']['entrance.root'];im=Image.new('RGBA',(w,h));rng=random.Random(index+441)
        root_colors=[rgb(self.grove[key]) for key in ('wood_deep','wood_shadow','wood_mid','wood_light')]
        branches=[[tuple(point) for point in branch]
                  for branch in self.spec['root_graphs'][index]]
        d=ImageDraw.Draw(im)
        for ordinal,path in enumerate(branches):
            width=5 if ordinal==0 else 3
            d.line([(x+1,y+1) for x,y in path],fill=root_colors[0],width=width+1)
            d.line(path,fill=root_colors[1],width=width)
            d.line([(x-1,y) for x,y in path],fill=root_colors[2],width=max(1,width-2))
            d.line(path[:2],fill=root_colors[3])
        for _ in range(13):
            ordinal=rng.randrange(len(branches));path=branches[ordinal];x,y=path[rng.randrange(1,len(path))]
            d.line([(x,y),(x+rng.choice((-3,3)),y+4),(x+rng.choice((-5,5)),y+6)],fill=root_colors[1])
        return im

    def moss(self,index):
        w,h=self.spec['families']['entrance.moss'];im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
        rng=random.Random(741+index);colors=[rgb(self.grass.get(key, fallback)) for key,fallback in
            (('shadow','#175c3e'),('base','#246b48'),('light','#378268'),('tip','#67a27a'))]
        # Irregular small velvet cushions. Dark pockets and tiny growth points
        # use the approved emerald ramp; the limestone still shows between them.
        for _ in range(42):
            angle=rng.random()*math.tau;r=rng.random()**.5
            x=round(w/2+math.cos(angle)*w*.42*r);y=round(h/2+math.sin(angle)*h*.37*r)
            dx=rng.randrange(2,5);dy=rng.randrange(1,4)
            d.polygon([(x-dx,y),(x-1,y-dy),(x+dx,y),(x+dx-1,y+dy),(x-2,y+dy)],fill=colors[rng.randrange(3)])
            if rng.randrange(3)==0:d.line((x-1,y-dy,x+1,y-dy),fill=colors[-1])
        return im

    def leaf_litter(self,index):
        w,h=self.spec['families']['entrance.leaves'];im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);rng=random.Random(739+index)
        for _ in range(13+index):
            x=rng.randrange(4,w-5);y=rng.randrange(4,h-5);dx=rng.randrange(2,5);dy=rng.randrange(1,4)
            points=[(x-dx,y),(x,y-dy),(x+dx,y+1),(x+1,y+dy)]
            d.polygon(points,fill=rng.choice(self.leaves));d.line([(x-dx+1,y),(x+dx,y+1)],fill=self.leaves[0])
            if dx>3:d.point((x-1,y-1),fill=self.leaves[3])
        return im

    def earth_tile(self,index):
        im=self.base.material_tile('silt',index).copy();d=ImageDraw.Draw(im);rng=random.Random(223+index)
        # Retain native sediment texture, with drier warm earth exposed in
        # irregular platelets and a few small pale limestone inclusions.
        for _ in range(37):
            x=rng.randrange(24);y=rng.randrange(24);w=rng.randrange(2,5)
            d.line((x,y,min(23,x+w),y),fill=rng.choice(self.earth))
        for _ in range(4):
            x=rng.randrange(2,22);y=rng.randrange(2,22);d.line((x,y,x+2,y),fill=self.stone[5])
        return im

    def transition(self,direction,index):
        im=self.earth_tile(index);mask=Image.new('L',(24,24));d=ImageDraw.Draw(mask)
        if direction in ('north','east','south','west'):
            points=[(0,6),(4,5),(8,7),(12,4),(17,6),(21,3),(23,5),(23,23),(0,23)]
            d.polygon(points,fill=255)
            rotation={'north':0,'east':90,'south':180,'west':270}[direction]
            mask=mask.transpose({90:Image.Transpose.ROTATE_90,180:Image.Transpose.ROTATE_180,270:Image.Transpose.ROTATE_270}[rotation]) if rotation else mask
        else:
            d.polygon([(0,0),(14,0),(18,4),(20,9),(23,15),(23,23),(0,23)],fill=255)
            if direction.startswith('inner'):mask=ImageChops.invert(mask)
            rotation={'ne':0,'se':270,'sw':180,'nw':90}[direction[-2:]]
            if rotation:mask=mask.transpose({90:Image.Transpose.ROTATE_90,180:Image.Transpose.ROTATE_180,270:Image.Transpose.ROTATE_270}[rotation])
        # A thin pale chip edge belongs to the source limestone transition.
        eroded=mask.filter(__import__('PIL.ImageFilter',fromlist=['MinFilter']).MinFilter(3))
        edge=ImageChops.subtract(mask,eroded);ed=ImageDraw.Draw(im)
        for y in range(24):
            for x in range(24):
                if edge.getpixel((x,y)) and (x*17+y*11+index)%4==0:ed.point((x,y),fill=self.stone[4])
        im.putalpha(mask)
        return im

    def module(self,key,im,*,ground=True,footprints=(),anchor=None,**metadata):
        path=f'{PACK}/modules/{key.replace(".","/")}.png';self.emit(path,im)
        self.modules[key]={'frames':[path],'size':list(im.size),
            'anchor':list(anchor or ((0,0) if ground else (im.width//2,im.height-5))),
            'footprints':[list(rect) for rect in footprints], 'ground_decal':ground,
            'frame_duration_ms':700,'reduced_motion_frame':0,**metadata}

    def build(self):
        methods={'debris.pebbles':lambda i:self.debris('debris.pebbles',i),
                 'debris.rubble':lambda i:self.debris('debris.rubble',i),
                 'debris.talus':lambda i:self.debris('debris.talus',i),
                 'slab.fallen':self.slab,'crack.branching':self.cracks,
                 'erosion.channel':lambda i:self.cracks(i,channel=True),
                 'mineral.crust':self.crust,'stain.damp':lambda i:self.crust(i,damp=True),
                 'entrance.root':self.roots,'entrance.moss':self.moss,'entrance.leaves':self.leaf_litter}
        for family in self.spec['families']:
            for index in range(self.spec['variants']):
                is_slab=family=='slab.fallen'
                self.module(f'{family}.{index}',methods[family](index),ground=not is_slab,
                    footprints=((12,34,46,10),) if is_slab else (),
                    placement='entrance' if family.startswith('entrance') else 'cave',
                    terrain_role='solid_fragment' if is_slab else 'surface_detail')
        materials={}
        for index in range(4):
            path=f'{PACK}/tiles/earth_{index:02}.png';self.emit(path,self.earth_tile(index))
            materials.setdefault('earth',{'tiles':[]})['tiles'].append(path)
        for direction in DIRECTIONS:
            for index in range(self.spec['transition_variants']):
                self.module(f'transition.earth.{direction}.{index}',self.transition(direction,index),direction=direction)

        # The board shows actual native sprites enlarged exactly two times;
        # neutral backgrounds make sparse decal pixels legible without changing
        # the exported hard-alpha modules or painting a demonstration scene.
        cols=4;cell_w=280;cell_h=145
        rows=len(self.spec['families'])+3
        board=Image.new('RGB',(cols*cell_w+40,rows*cell_h+100),'#26322f')
        d=ImageDraw.Draw(board);font=ImageFont.load_default(size=17);small=ImageFont.load_default(size=13)
        d.text((20,15),'LIMESTONE GEOLOGY / entrance treatments / all sprites at 2x',font=font,fill='#ece3cd')
        for row,family in enumerate(self.spec['families']):
            for col in range(4):
                key=f'{family}.{col}';record=self.modules[key]
                image=Image.open(BytesIO(self.outputs[record['frames'][0]])).convert('RGBA')
                x=20+col*cell_w;y=55+row*cell_h
                # Use the actual dry limestone below sparse floor overlays.
                if record['ground_decal']:
                    backdrop=self.base.texture(image.size,41,'dry');backdrop.alpha_composite(image)
                else:backdrop=image
                scaled=backdrop.resize((backdrop.width*2,backdrop.height*2),Image.Resampling.NEAREST)
                board.paste(scaled,(x,y+24),scaled)
                d.text((x,y),key,font=small,fill='#d5d5bf')
        offset=55+len(self.spec['families'])*cell_h
        for row,group in enumerate((DIRECTIONS[:4],DIRECTIONS[4:8],DIRECTIONS[8:])):
            for col,direction in enumerate(group):
                key=f'transition.earth.{direction}.0';record=self.modules[key]
                image=Image.open(BytesIO(self.outputs[record['frames'][0]])).convert('RGBA')
                back=self.base.material_tile('dry',0);back.alpha_composite(image)
                # Four adjacent cells show edge readability at native tile size.
                patch=Image.new('RGBA',(48,48))
                for y in (0,24):
                    for x in (0,24):patch.alpha_composite(back,(x,y))
                patch=patch.resize((96,96),Image.Resampling.NEAREST)
                x=20+col*cell_w;y=offset+row*cell_h
                d.text((x,y),key,font=small,fill='#d5d5bf');board.paste(patch,(x,y+24),patch)
        ca_path=ROOT/'assets/source/characters/caelan/overworld_refresh/legacy/idle_front.png'
        with Image.open(ca_path) as source:ca=source.convert('RGBA')
        ca=ca.resize((ca.width*2,ca.height*2),Image.Resampling.NEAREST)
        board.paste(ca,(board.width-90,board.height-85),ca)
        d.text((20,board.height-30),'Small scatter and entrance details are walkable decals; only raised slabs have a solid base.',font=small,fill='#c5cebc')
        self.emit(f'{PACK}/geology_review.png',board)
        self.outputs[f'{PACK}/README.md']=(
            '# Limestone loose geology and entrance treatments\n\n'
            'Status: pending visual review; isolated from live maps.\n\n'
            'Four native variants each: small pebbles, rubble, wall-foot talus,\n'
            'raised fallen slabs, branching cracks, erosion channels, calcite\n'
            'crust, damp staining, exposed roots, emerald moss and leaf litter.\n'
            'Four 24-pixel earth fills and two variants of every cardinal,\n'
            'inside-corner and outside-corner earth-to-stone transition complete\n'
            'the entrance material coverage.\n\n'
            'Every module declares its native size, anchor and footprints.\n'
            'Most are ground decals and never add collision. Raised slabs own\n'
            'a shallow physical footing matching their visible lower edge.\n'
            'Roots, moss and leaves are intended for the cave threshold and\n'
            'daylight margins rather than dense growth throughout the dungeon.\n\n'
            'Rebuild with `python tools/build_dungeon_geology.py`; use `--check`\n'
            'to validate deterministic exports without modifying files.\n'
        ).encode()
        inputs=[SOURCE,ROOT/self.spec['source_recipe'],ROOT/self.spec['grove_recipe'],
                ROOT/self.spec['grass_recipe'],ROOT/'tools/build_limestone_cave_assets.py',
                Path(__file__).resolve(),ca_path]
        inputs.extend(ROOT/path for path in self.base.recipe['source_assets'])
        manifest={'version':1,'id':self.spec['id'],'approval_status':self.spec['approval_status'],
                  'tile_size':24,'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
                  'materials':materials,'modules':self.modules,
                  'inputs':{str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest()
                            for path in sorted(set(inputs))},
                  'artifacts':{path:sha256(raw).hexdigest() for path,raw in self.outputs.items()}}
        self.emit(f'{PACK}/assets.json',manifest)
        return self.outputs


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    products=GeologyAuthor().build();changed=[]
    for name,data in products.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=data:
            changed.append(name)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if args.check and changed:raise SystemExit('Stale geology exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(products)} geology exports')
    return 0


if __name__=='__main__':raise SystemExit(main())
