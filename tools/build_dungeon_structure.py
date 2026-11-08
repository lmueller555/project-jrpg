"""Native directional limestone walls, shelves and passages for review.

Geometry is drawn for each perspective at the existing 24 px grid. Surface
texture is sampled at native resolution by the approved limestone author.
Only the supplemental output directory is written.
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PIL import Image, ImageChops, ImageDraw, ImageFont
from tools.build_limestone_cave_assets import Author

SOURCE=ROOT/'assets/source/terrain/limestone_cave/structure.json'
PACK='assets/terrain/limestone_cave/structure'


class StructureAuthor:
    def __init__(self):
        self.spec=json.loads(SOURCE.read_text());self.base=Author()
        self.ramp=self.base.ramps['limestone'];self.modules={};self.outputs={}

    def emit(self,path,value):
        if isinstance(value,Image.Image):
            stream=BytesIO();value.save(stream,format='PNG');raw=stream.getvalue()
        elif isinstance(value,str):raw=value.encode()
        else:raw=(json.dumps(value,indent=2)+'\n').encode()
        self.outputs[path]=raw

    def crag(self,size,outline,seed,*,bias=0.,shade=.0):
        image=self.base.clipped(size,outline,seed,bias=bias)
        mask=image.getchannel('A');w,h=size;rng=random.Random(self.spec['seed']+seed)
        layer=Image.new('RGBA',size);d=ImageDraw.Draw(layer)
        # Broken overlapping geological planes and channels retain broad quiet
        # areas. Cracks do not outline repeated bricks or stone courses.
        for i in range(max(3,w*h//1150)):
            x=rng.randrange(2,max(3,w-4));y=rng.randrange(3,max(4,h-5))
            length=rng.randrange(12,31)
            path=[(x,y),(x-3,y+length//3),(x+1,y+length*2//3),(x-4,min(h-2,y+length))]
            d.line(path,fill=(*self.ramp[0],190),width=1)
            d.line([(px-1,py) for px,py in path[:3]],fill=(*self.ramp[5],130))
            if i%2:d.line([(x-3,y+length//3),(x-11,y+length//3+4)],fill=(*self.ramp[1],160))
        for y in range(13,h-5,19):
            start=rng.randrange(-7,max(1,w//3));end=min(w-1,start+rng.randrange(25,max(26,w)))
            path=[(x,y+round(math.sin(x/13+seed)*2)) for x in range(start,end,4)]
            d.line(path,fill=(*self.ramp[2],140))
            d.line([(x,y-1) for x,y in path[:-2]],fill=(*self.ramp[5],120))
        layer.putalpha(ImageChops.multiply(layer.getchannel('A'),mask));image.alpha_composite(layer)
        pixels=image.load()
        for y in range(h):
            for x in range(w):
                r,g,b,a=pixels[x,y]
                if a:
                    factor=1-shade*(x/max(1,w-1))
                    pixels[x,y]=round(r*factor),round(g*factor),round(b*factor),a
        return image

    def register(self,name,image,*,anchor=None,footprints=(),walkable_regions=(),**metadata):
        path=f'{PACK}/modules/{name.replace(".","/")}.png';self.emit(path,image)
        self.modules[name]={'frames':[path],'size':list(image.size),
            'anchor':list(anchor or (image.width//2,image.height-5)),
            'footprints':[list(r) for r in footprints],
            'walkable_regions':[list(r) for r in walkable_regions],**metadata}

    def face(self,direction,height):
        if direction in ('north','south'):
            w,h=96,height+24
            edge=[(0,12),(12,7),(26,10),(39,5),(54,9),(68,5),(83,10),(95,9)]
            points=edge+[(95,h-7),(83,h-3),(66,h-6),(49,h-2),(31,h-5),(13,h-2),(0,h-7)]
            image=self.crag((w,h),points,110+height+(direction=='south')*3,bias=.1 if direction=='north' else -.7,shade=.14)
            d=ImageDraw.Draw(image)
            d.line(edge,fill=self.ramp[6]);d.line([(x,y+3) for x,y in edge],fill=self.ramp[4])
            d.line([(0,h-6),(16,h-2),(32,h-5),(49,h-2),(67,h-6),(84,h-3),(95,h-7)],fill=self.ramp[0],width=2)
            if direction=='south':
                # A rear/cutaway treatment has a broad darker top shelf, not
                # an upside-down front wall.
                cap=[(0,12),(14,6),(40,7),(68,5),(95,9),(95,23),(72,19),(49,24),(22,20),(0,23)]
                texture=self.base.clipped((w,h),cap,151+height,bias=-.65)
                image.alpha_composite(texture)
                ImageDraw.Draw(image).line(cap[:5],fill=self.ramp[4])
            return image,([4,h-16,88,12] if direction=='north' else [4,12,88,12]),([48,h-10] if direction=='north' else [48,18])
        w,h=height//2+24,96
        if direction=='east':
            points=[(8,0),(w-12,3),(w-4,16),(w-8,34),(w-3,52),(w-8,73),(w-4,95),(12,95),(6,78),(10,59),(5,40),(9,20)]
            edge=[(8,0),(9,20),(5,40),(10,59),(6,78),(12,95)]
            fp=[8,6,12,84];anchor=[14,90]
        else:
            points=[(8,3),(w-9,0),(w-10,22),(w-5,41),(w-9,61),(w-5,78),(w-12,95),(4,95),(8,73),(3,52),(8,33),(4,16)]
            edge=[(w-9,0),(w-10,22),(w-5,41),(w-9,61),(w-5,78),(w-12,95)]
            fp=[w-20,6,12,84];anchor=[w-14,90]
        image=self.crag((w,h),points,190+height+(direction=='west')*4,bias=-.3,shade=.22 if direction=='east' else .08)
        d=ImageDraw.Draw(image);d.line(edge,fill=self.ramp[6],width=2)
        for i,y in enumerate((17,39,63,82)):
            x=9 if direction=='east' else w-13
            d.line([(x,y),(x+(w//2 if direction=='east' else -w//2),y+5),(w-5 if direction=='east' else 5,y+1)],fill=self.ramp[2])
        return image,fp,anchor

    def edge(self,direction,base=False):
        vertical=direction in ('east','west');size=(24,96) if vertical else (96,24)
        if vertical:
            points=[(4,0),(17,4),(20,23),(16,44),(20,65),(18,95),(3,95),(5,73),(2,52),(6,30)]
        else:points=[(0,5),(16,2),(33,6),(49,3),(68,6),(83,2),(95,5),(95,20),(74,18),(52,22),(28,18),(0,21)]
        image=self.crag(size,points,250+len(direction)+base*20,bias=-.35 if base else .35)
        d=ImageDraw.Draw(image)
        line=([(4,y) for y in range(0,96,8)] if vertical else [(x,5+round(math.sin(x/13)*2)) for x in range(0,96,4)])
        d.line(line,fill=self.ramp[1 if base else 6],width=2 if base else 1)
        return image

    def corner(self,kind,corner):
        image=Image.new('RGBA',(72,72));mask=Image.new('L',image.size);md=ImageDraw.Draw(mask)
        # Native L-shaped mass with an irregular inner or outer elbow. Each
        # corner is drawn in its actual room quadrant.
        east='e' in corner;south='s' in corner
        xside=49 if east else 3;yside=49 if south else 3
        md.polygon([(xside,3),(xside+18,7),(xside+20,60),(xside+15,68),(xside,64)],fill=255)
        md.polygon([(3,yside),(28,yside+3),(52,yside),(68,yside+4),(66,yside+20),(9,yside+18),(3,yside+13)],fill=255)
        if kind=='outer':
            cx=49 if east else 22;cy=49 if south else 22
            md.ellipse((cx-14,cy-14,cx+14,cy+14),fill=255)
        image=self.base.texture((72,72),313+sum(map(ord,corner)),bias=-.2);image.putalpha(mask)
        border=ImageChops.subtract(mask,mask.filter(__import__('PIL.ImageFilter',fromlist=['MinFilter']).MinFilter(3)))
        image.paste((*self.ramp[1],255),(0,0,72,72),border)
        return image

    def shelf(self,index):
        w,h=self.spec['shelf_sizes'][index];cx=w//2
        outline=[(3,18),(13,10),(33,6),(cx-8,10),(cx+13,5),(w-20,10),(w-4,18),(w-2,h-14),(w-14,h-7),(cx+24,h-9),(cx-24,h-9),(15,h-5),(3,h-13)]
        image=self.crag((w,h),outline,380+index,bias=.4,shade=.12);d=ImageDraw.Draw(image)
        # Low front faces split at a generous walking port for an attached ramp.
        for x0,x1 in ((5,cx-24),(cx+24,w-5)):
            face=[(x0,h-24),(x0+9,h-26),(x1-7,h-24),(x1,h-25),
                  (x1,h-9),(x1-8,h-6),(x0+5,h-4),(x0,h-12)]
            layer=self.crag((w,h),face,392+index+x0,bias=-.7,shade=.1)
            image.alpha_composite(layer);d=ImageDraw.Draw(image)
            d.line(face[:4],fill=self.ramp[5])
            d.line([(x0+4,h-9),(x0+13,h-7),(x1-4,h-11)],fill=self.ramp[1])
        floor_texture=self.base.texture((w,h),402+index,'dry')
        for x in range(cx-22,cx+23):
            for y in range(h-25,h):
                image.putpixel((x,y),floor_texture.getpixel((x,y)))
        fp=[[6,h-23,cx-31,16],[cx+25,h-23,w-cx-31,16],
            [5,20,6,h-45],[w-11,20,6,h-45],[18,11,w-36,7]]
        walk=[[12,21,w-24,h-48],[cx-24,20,48,h-20]]
        return image,fp,walk

    def incline(self,direction,steps):
        horizontal=direction in ('east','west');w,h=(96,72) if horizontal else (72,96)
        im=self.base.texture((w,h),410+len(direction),'dry');d=ImageDraw.Draw(im)
        if horizontal:
            cheek_polys=[[(0,4),(14,2),(31,5),(51,3),(70,5),(95,2),(95,11),(0,11)],
                         [(0,61),(95,61),(95,68),(76,70),(55,67),(33,70),(15,67),(0,69)]]
            fp=[[8,4,80,6],[8,63,80,5]];walk=[[0,12,w,48]]
        else:
            cheek_polys=[[(3,0),(11,0),(11,95),(2,95),(4,77),(2,57),(4,39),(2,18)],
                         [(61,0),(69,0),(71,19),(68,39),(70,57),(68,77),(70,95),(61,95)]]
            fp=[[4,8,6,80],[63,8,5,80]];walk=[[12,0,48,h]]
        for ordinal,poly in enumerate(cheek_polys):
            layer=self.crag((w,h),poly,430+ordinal+len(direction),bias=-.15,shade=.06)
            im.alpha_composite(layer)
        # Gentle broad value changes describe an eroded slope, not parallel
        # planks or a set of dark metal rails.
        px=im.load()
        for y in range(h):
            for x in range(w):
                on_floor=(12<=y<60) if horizontal else (12<=x<60)
                if on_floor:
                    distance=(x/w if horizontal else y/h)
                    if direction in ('south','west'):distance=1-distance
                    factor=.92+.08*distance
                    r,g,b,a=px[x,y];px[x,y]=round(r*factor),round(g*factor),round(b*factor),a
        d=ImageDraw.Draw(im)
        distance=w if horizontal else h
        if steps:
            for ordinal,t in enumerate(range(12,distance-6,17)):
                if horizontal:
                    edge=[(t+round(math.sin(y/9+ordinal)*1.5),y) for y in range(12,61,4)]
                    d.line(edge,fill=self.ramp[5]);d.line([(x+2,y) for x,y in edge],fill=self.ramp[2],width=2)
                else:
                    edge=[(x,t+round(math.sin(x/9+ordinal)*1.5)) for x in range(12,61,4)]
                    d.line(edge,fill=self.ramp[5]);d.line([(x,y+2) for x,y in edge],fill=self.ramp[2],width=2)
        else:
            # Broad erosion channels are drawn along the actual direction of
            # travel. Their value ramp implies a gentle 24 px rise.
            for line in range(3):
                if horizontal:
                    points=[(x,19+line*12+round(math.sin(x/14+line)*2)) for x in range(12+line*9,45+line*10,5)]
                else:points=[(19+line*12+round(math.sin(y/14+line)*2),y) for y in range(12+line*9,45+line*10,5)]
                d.line(points,fill=self.ramp[3]);d.line([(x+1,y) for x,y in points],fill=self.ramp[4])
        # Eroded chip marks connect the cheeks to existing natural limestone.
        for i in range(16):
            x=(i*23+7)%w;y=(i*37+9)%h
            if (horizontal and (y<11 or y>61)) or (not horizontal and (x<11 or x>61)):
                d.line((x,y,min(w-1,x+3),y),fill=self.ramp[5])
        silhouette=Image.new('L',(w,h));md=ImageDraw.Draw(silhouette)
        if horizontal:
            points=[(0,3),(18,2),(37,4),(55,2),(74,4),(95,2),
                    (95,70),(77,68),(57,70),(39,68),(18,70),(0,68)]
        else:
            points=[(3,0),(69,0),(70,18),(68,37),(71,55),(68,74),(70,95),
                    (2,95),(4,77),(2,57),(4,39),(2,18)]
        md.polygon(points,fill=255);im.putalpha(silhouette)
        return im,fp,walk

    def tunnel(self,direction,opening,alcove=False):
        if direction in ('north','south'):
            w,h=opening+48,96 if direction=='north' else 72;cx=w//2
            if direction=='north':
                outline=[(3,h-5),(6,50),(15,25),(31,11),(cx-5,5),(cx+17,10),(w-17,28),(w-6,50),(w-3,h-5)]
                recess=[(cx-opening//2,h-1),(cx-opening//2,54),(cx-opening//2+8,35),(cx-4,24),(cx+12,30),(cx+opening//2-4,47),(cx+opening//2,h-1)]
                footprint=[[6,h-29,12,22],[w-18,h-29,12,22]]
                walk=[[cx-opening//2,48,opening,h-48]];anchor=[cx,h-6]
            else:
                outline=[(4,3),(w-5,5),(w-3,37),(w-14,h-9),(cx+18,h-3),(cx-13,h-5),(14,h-12),(3,36)]
                recess=[(cx-opening//2,0),(cx+opening//2,0),(cx+opening//2,31),(cx+opening//2-7,46),(cx+6,53),(cx-12,49),(cx-opening//2,33)]
                footprint=[[6,10,12,38],[w-18,10,12,38]]
                walk=[[cx-opening//2,0,opening,48]];anchor=[cx,12]
        else:
            w,h=112,opening+40;cy=h//2
            if direction=='east':
                # Upright side-wall opening: a foreshortened top shelf and
                # deep vertical far jamb, not an arch rotated onto its side.
                outline=[(2,15),(31,9),(63,3),(91,8),(108,19),(110,h-16),
                         (94,h-6),(60,h-3),(29,h-8),(2,h-15)]
                recess=[(0,cy-opening//2),(53,cy-opening//2-7),
                        (89,cy-opening//2-2),(89,cy+opening//2+2),
                        (52,cy+opening//2+7),(0,cy+opening//2)]
                anchor=[16,cy];footprint=[[18,10,60,6],[18,h-16,60,8],[97,19,9,h-38]]
                walk=[[0,cy-opening//2,88,opening]]
            else:
                outline=[(3,19),(20,8),(49,3),(81,9),(110,15),(110,h-15),
                         (81,h-8),(52,h-3),(18,h-6),(2,h-16)]
                recess=[(111,cy-opening//2),(59,cy-opening//2-7),
                        (23,cy-opening//2-2),(23,cy+opening//2+2),
                        (59,cy+opening//2+7),(111,cy+opening//2)]
                anchor=[w-16,cy];footprint=[[34,10,60,6],[34,h-16,60,8],[6,19,9,h-38]]
                walk=[[24,cy-opening//2,88,opening]]
        im=self.crag((w,h),outline,500+len(direction)+opening,bias=-.1,shade=.16);d=ImageDraw.Draw(im)
        d.polygon(recess,fill='#152321');d.line(recess[1:-1],fill=self.ramp[0],width=2)
        if direction in ('north','south'):
            cx=w//2
            d.line([(cx-opening//2+3,h-5 if direction=='north' else 5),(cx+opening//2-3,h-5 if direction=='north' else 5)],fill=self.ramp[5])
        else:
            if direction=='east':
                top=[(3,17),(31,11),(63,5),(91,10),(107,21)]
                threshold=[(0,cy+opening//2),(51,cy+opening//2+7),(90,cy+opening//2+2)]
                far=[(92,cy-opening//2-1),(92,cy+opening//2+1)]
            else:
                top=[(4,21),(21,10),(49,5),(81,11),(109,17)]
                threshold=[(111,cy+opening//2),(59,cy+opening//2+7),(22,cy+opening//2+2)]
                far=[(20,cy-opening//2-1),(20,cy+opening//2+1)]
            d.line(top,fill=self.ramp[5]);d.line(threshold,fill=self.ramp[5],width=2)
            d.line(far,fill=self.ramp[0],width=3)
            # A narrower deep plane lends the vertical jamb thickness.
            d.line([(x+2,y) for x,y in far],fill=self.ramp[2])
        if alcove:
            # A shallow recess keeps an observable stone back and floor; it is
            # an inspection/treasure niche, not a misleading through-passage.
            if direction in ('north','south'):
                back=recess
                layer=self.crag((w,h),back,650+len(direction),bias=-1.5,shade=.18)
                im.alpha_composite(layer)
                floor=[(w//2-22,h-29),(w//2+21,h-31),(w//2+24,h-2),(w//2-24,h-2)]
                layer=self.base.clipped((w,h),floor,670+len(direction),'dry',bias=-.4)
                im.alpha_composite(layer);d=ImageDraw.Draw(im)
                d.line(floor[:2],fill=self.ramp[1])
            else:
                back=recess
                layer=self.crag((w,h),back,690+len(direction),bias=-1.5,shade=.2)
                im.alpha_composite(layer);d=ImageDraw.Draw(im)
                floor=[(0,cy+9),(61,cy+14),(89,cy+opening//2+2),(50,cy+opening//2+7),(0,cy+opening//2)] if direction=='east' else [(111,cy+9),(51,cy+14),(23,cy+opening//2+2),(59,cy+opening//2+7),(111,cy+opening//2)]
                im.alpha_composite(self.base.clipped((w,h),floor,710+len(direction),'dry',bias=-.6))
        return im,footprint,walk,anchor

    def build(self):
        directions=self.spec['directions']
        for direction in directions:
            for height in self.spec['heights']:
                im,fp,anchor=self.face(direction,height)
                self.register(f'wall.face.{direction}.h{height}',im,anchor=anchor,footprints=[fp],direction=direction,height_px=height)
            for kind in ('cap','base'):
                im=self.edge(direction,kind=='base')
                self.register(f'wall.{kind}.{direction}',im,direction=direction,height_px=0)
            im,fp,anchor=self.face(direction,self.spec['ledge_height'])
            self.register(f'ledge.edge.{direction}',im,anchor=anchor,footprints=[fp],direction=direction,elevation=24)
            for kind in ('ramp','steps'):
                im,fp,walk=self.incline(direction,kind=='steps')
                self.register(f'{kind}.{direction}',im,anchor=([im.width//2,im.height-6] if direction in ('north','south') else [im.width-6,im.height//2]),footprints=fp,walkable_regions=walk,direction=direction,elevation=24,clear_width=48)
            for size,opening in self.spec['tunnel_widths'].items():
                im,fp,walk,anchor=self.tunnel(direction,opening)
                self.register(f'tunnel.{direction}.{size}',im,anchor=anchor,footprints=fp,walkable_regions=walk,direction=direction,clear_width=opening)
            im,fp,walk,anchor=self.tunnel(direction,48,alcove=True)
            self.register(f'alcove.{direction}',im,anchor=anchor,footprints=fp,walkable_regions=walk,direction=direction,clear_width=48,passage=False)
        for kind in ('inner','outer'):
            for corner in ('ne','se','sw','nw'):
                image=self.corner(kind,corner)
                side_x=52 if 'e' in corner else 6;edge_y=52 if 's' in corner else 7
                self.register(f'wall.corner.{kind}.{corner}',image,direction=corner,height_px=24,
                              footprints=[[side_x,12,12,48],[12,edge_y,45,10]])
        for index in range(len(self.spec['shelf_sizes'])):
            im,fp,walk=self.shelf(index)
            self.register(f'shelf.low.{index}',im,anchor=[im.width//2,im.height-6],footprints=fp,walkable_regions=walk,elevation=24,clear_width=48)
        # A readable compact family board complements the complete catalog.
        categories=[('Walls and heights','wall.face.'),('Wall caps and bases','wall.cap.'),('Ledges and shelves','ledge.edge.'),('Walkable ramps and worn steps','ramp.'),('Directional passage mouths','tunnel.'),('Shallow alcoves','alcove.')]
        board=Image.new('RGB',(1440,2000),'#24312c');d=ImageDraw.Draw(board)
        title=ImageFont.load_default(size=20);label=ImageFont.load_default(size=14)
        d.text((20,12),'LIMESTONE STRUCTURE / native 24 px grid / artwork enlarged exactly 2x',fill='#e8dfc7',font=title)
        for row,(name,prefix) in enumerate(categories):
            y=50+row*300;d.text((20,y),name,fill='#e8dfc7',font=title)
            examples=[(key,record) for key,record in self.modules.items() if key.startswith(prefix)][:5]
            for col,(key,record) in enumerate(examples):
                image=Image.open(BytesIO(self.outputs[record['frames'][0]])).convert('RGBA')
                image=image.resize((image.width*2,image.height*2),Image.Resampling.NEAREST)
                x=24+col*278;board.alpha_composite(image,(x,y+29)) if board.mode=='RGBA' else board.paste(image,(x,y+29),image)
                d.text((x,y+282),key.replace(prefix,''),fill='#cbd5c8',font=label)
        ca_path=ROOT/'assets/characters/caelan/idle_front.png';ca=Image.open(ca_path).convert('RGBA')
        ca=ca.resize((ca.width*2,ca.height*2),Image.Resampling.NEAREST);board.paste(ca,(1315,1878),ca)
        d.text((1130,1962),'Caelan / same enlargement',fill='#e8dfc7',font=label)
        self.emit(f'{PACK}/structure_review.png',board)
        self.emit(f'{PACK}/README.md','# Limestone dungeon structure\n\nStatus: pending visual review.\n\nNative directional walls, caps, bases, ledges, shelves, ramps, worn steps,\npassage mouths and shallow alcoves extend the existing limestone pack.\nRamps and steps use ordinary walking; elevation is a visual composition value.\n`walkable_regions` identify clear passage surfaces, while `footprints` describe\nsolid rock only. All coordinates are local to the unscaled native module.\n\nRebuild with `python tools/build_dungeon_structure.py`; append `--check`\nfor deterministic verification. Source: `assets/source/terrain/limestone_cave/structure.json`.\n')
        paths={SOURCE,ROOT/self.spec['base_manifest'],ROOT/self.spec['base_recipe'],ROOT/'tools/build_limestone_cave_assets.py',Path(__file__).resolve(),ca_path}
        paths.update(ROOT/name for name in self.base.recipe['source_assets'])
        inputs={str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
        manifest={'version':1,'id':self.spec['id'],'approval_status':self.spec['approval_status'],'tile_size':24,'source_recipe':str(SOURCE.relative_to(ROOT)),'modules':self.modules,'inputs':inputs,'artifacts':{path:sha256(raw).hexdigest() for path,raw in self.outputs.items()}}
        self.emit(f'{PACK}/assets.json',manifest)
        return self.outputs


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    outputs=StructureAuthor().build();changed=[]
    for name,raw in outputs.items():
        destination=ROOT/name
        if not destination.exists() or destination.read_bytes()!=raw:
            changed.append(name)
            if not args.check:destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
    if args.check and changed:raise SystemExit('Stale structure assets: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(outputs)} structural exports')
    return 0


if __name__=='__main__':raise SystemExit(main())
