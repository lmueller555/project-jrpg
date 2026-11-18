"""Author a reusable native limestone material library for visual review.

Regional rock pixels supply the fine texture. Geological silhouettes, erosion,
strata, wet edges and calcite deposits are independently authored at native
resolution. The existing game maps and cave assets are never written here.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import random

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/limestone_cave/recipe.json'
PACK = 'assets/terrain/limestone_cave'


def rgba(value):
    return tuple(bytes.fromhex(value.removeprefix('#')))


def png(image):
    stream = BytesIO(); image.save(stream, format='PNG'); return stream.getvalue()


class Author:
    def __init__(self):
        self.recipe = json.loads(SOURCE.read_text())
        self.palette = self.recipe['palette']
        self.ramps = {name: [rgba(c) for c in colors]
                      for name, colors in self.palette.items() if isinstance(colors, list)}
        self.source = Image.open(ROOT/self.recipe['source_assets'][0]).convert('RGBA')
        self.outputs = {}
        self.modules = {}

    def emit(self, path, value):
        self.outputs[path] = (png(value) if isinstance(value, Image.Image) else
                              (json.dumps(value, indent=2)+'\n').encode())

    def texture(self, size, seed, material='limestone', bias=0):
        """Sample source pixels at 1:1 scale; keep their clustered variation."""
        w, h = size; ramp = self.ramps[material]
        im = Image.new('RGBA', size); rng = random.Random(seed)
        ox, oy = rng.randrange(self.source.width), rng.randrange(self.source.height)
        for y in range(h):
            for x in range(w):
                pixel = self.source.getpixel(((x+ox)%self.source.width,
                                              (y+oy)%self.source.height))
                if not pixel[3]:
                    # Empty sky around the source outcrop is never a flat
                    # fill in the material. Sample its native interior crop.
                    pixel=self.source.getpixel((24+(x+ox)%24,20+(y+oy)%24))
                # The ridge contains moss and transparent margins. They supply
                # texture rhythm only; the cave stone has its own neutral ramp.
                light = pixel[0]*.30+pixel[1]*.50+pixel[2]*.20
                detail = (light-115)/52
                broad = math.sin((x+seed*3)/17)*.35+math.sin((y-seed)/13)*.3
                index = round((len(ramp)-1)*.53 + detail*.65 + broad + bias)
                im.putpixel((x,y), (*ramp[max(0,min(len(ramp)-1,index))],255))
        return im

    def clipped(self, size, points, seed, material='limestone', bias=0):
        im = self.texture(size, seed, material, bias)
        mask = Image.new('L', size); ImageDraw.Draw(mask).polygon(points, fill=255)
        im.putalpha(mask)
        return im

    def material_tile(self, name, index):
        rng = random.Random(1000+index+list(self.recipe['materials']).index(name)*103)
        im = self.texture((24,24), index+71, name)
        d = ImageDraw.Draw(im); ramp = self.ramps[name]
        # Quiet, irregular platelets give broad stone texture instead of salt
        # noise. Most tiles remain subdued so characters read in motion.
        for _ in range(4 if name!='gravel' else 17):
            x,y = rng.randrange(-2,23),rng.randrange(1,23)
            w,h = ((rng.randrange(2,5),rng.randrange(1,4)) if name=='gravel'
                   else (rng.randrange(4,11),rng.randrange(2,6)))
            points = [(x,y+1),(x+w//3,y),(x+w,y+1),(x+w-1,y+h),(x+1,y+h+1)]
            color = ramp[rng.randrange(1,4)]
            d.polygon(points, fill=color)
            if name=='gravel':
                d.line([points[0],points[1],points[2]], fill=ramp[-1])
                d.line([points[3],points[4]], fill=ramp[0])
        if name in ('dry','damp') and index%3==0:
            x,y=rng.randrange(1,8),rng.randrange(6,14)
            points=[(x,y),(x+5,y+2),(x+9,y+1),(x+13,y+4),(x+18,y+3)]
            d.line(points,fill=ramp[1])
            if index%2:d.line([(x+8,y+2),(x+10,y+6),(x+9,y+9)],fill=ramp[1])
        if name=='damp':
            for _ in range(3):
                x,y=rng.randrange(2,20),rng.randrange(2,21)
                d.line((x,y,x+rng.randrange(2,5),y),fill=ramp[3])
        return im

    def wall(self, index, size=(96,72)):
        w,h=size; rng=random.Random(605+index)
        outline=[(0,13),(12,10),(25,6),(40,9),(53,4),(70,7),(84,10),(w-1,13),
                 (w-1,h-6),(84,h-3),(65,h-5),(49,h-2),(29,h-4),(12,h-2),(0,h-6)]
        im=self.clipped(size,outline,index+120,bias=-.4);d=ImageDraw.Draw(im)
        # Broad, overlapping outcrop facets follow the native regional ridge.
        # Their varied heights and angled boundaries avoid regular masonry rows.
        offset=rng.randrange(-4,5)
        masses=[([(0,14),(15,9),(31,11),(43,31+offset),(29,56),(10,63),(0,54)],.5),
                ([(25,9),(49,6),(63,16),(63,45),(48,65),(28,60),(36,34)],-.35),
                ([(55,12),(71,7),(90,12),(96,30),(82,55),(62,63),(65,35)],.7)]
        for ordinal,(points,bias) in enumerate(masses):
            layer=self.clipped(size,points,index+ordinal+439,bias=bias)
            ld=ImageDraw.Draw(layer)
            # Softly broken mineral lips belong to each massive face, rather
            # than outlining every stone like individual building blocks.
            edge=points[:3]
            ld.line(edge,fill=self.ramps['limestone'][6])
            im.alpha_composite(layer)
        d=ImageDraw.Draw(im)
        for yy,start,end in ((30+index%5,3,45),(49-index%4,33,91)):
            points=[(x,yy+round(math.sin((x+index*11)/17)*3)) for x in range(start,end,5)]
            d.line(points,fill=self.ramps['limestone'][2])
            d.line([(x,y-1) for x,y in points[:-2]],fill=self.ramps['limestone'][5])
        # Eroded pockets interrupt the bedding and give the faces real mass.
        for ordinal in range(5):
            x=rng.randrange(9,w-17);y=rng.randrange(22,h-12)
            d.arc((x-6,y-3,x+10,y+7),185,350,fill=self.ramps['limestone'][1],width=2)
            d.line([(x-3,y+5),(x+1,y+7),(x+7,y+6)],fill=self.ramps['limestone'][5])
        for x in (18+rng.randrange(-7,8),60+rng.randrange(-9,10)):
            y=rng.randrange(9,19)
            points=[(x,y),(x-3,y+10),(x+2,y+18),(x-4,y+32),(x-2,min(h-8,y+43))]
            d.line(points,fill=self.palette['deep_joint'],width=2)
            d.line([(px+2,py) for px,py in points[:3]],fill=self.ramps['limestone'][5])
        # Mineral streaks have irregular tapering edges and restrained color.
        if index%2==0:
            x=37+index*3
            for yy in range(18,h-10):
                xx=x+round(math.sin(yy/9)*2)
                d.line((xx,yy,xx+(3 if yy<38 else 1),yy),fill=self.ramps['limestone'][5])
        mask=Image.new('L',size);ImageDraw.Draw(mask).polygon(outline,fill=255)
        im.putalpha(mask)
        return im

    def formation(self, kind, index):
        rng=random.Random(960+index*13+len(kind));w,h=(72,80)
        if kind=='boulder':w,h=64,48
        if kind=='flowstone':w,h=80,80
        im=Image.new('RGBA',(w,h));shadow=ImageDraw.Draw(im)
        shadow.ellipse((4,h-13,w-4,h-2),fill='#3d4941')
        shapes=[]
        if kind=='boulder':
            shapes=[[(3,h-13),(7,h-29),(18,8),(31,3),(46,9),(57,23),(61,h-12),(50,h-4),(26,h-2),(9,h-6)]]
        elif kind=='broken_column':
            shapes=[[(7,h-9),(10,49),(14,31),(16,23),(23,17),(29,21),(36,14),
                     (43,21),(48,18),(53,24),(57,37),(61,57),(64,h-9),
                     (57,h-4),(43,h-2),(26,h-3),(15,h-5)]]
        elif kind=='flowstone':
            shapes=[[(4,71),(7,46),(12,26),(20,30),(28,16),(37,5),(45,4),
                     (51,12),(57,26),(64,25),(71,39),(77,63),(74,72),
                     (67,77),(61,72),(53,78),(45,74),(37,78),(29,72),
                     (21,77),(15,72),(9,75)]]
        else:
            # The stalks are worn, broad and asymmetrical, with rounded tips.
            for cx,top,width in ((24,18+index*3,29),(46,3+index*4,28),(60,35-index*3,20)):
                shapes.append([(cx-width//2,h-6),(cx-width//2+3,h-27),
                    (cx-8,top+17),(cx-5,top+5),(cx,top),(cx+4,top+3),
                    (cx+7,top+15),(cx+9,h-29),(cx+width//2,h-7)])
        for ordinal,points in enumerate(shapes):
            layer=self.clipped((w,h),points,130+index+ordinal,bias=.3)
            d=ImageDraw.Draw(layer)
            xs=[x for x,y in points];x0,x1=min(xs),max(xs);mid=(x0+x1)//2
            # Rounded mineral mass keeps source texture in the shaded flank.
            # A smooth volume ramp replaces the old flat dark side panel.
            pixels=layer.load()
            for yy in range(h):
                for xx in range(w):
                    r,g,b,a=pixels[xx,yy]
                    if a:
                        shade=.99-.27*max(0,(xx-mid)/(max(1,x1-mid)))
                        pixels[xx,yy]=(round(r*shade),round(g*shade),round(b*shade),a)
            d=ImageDraw.Draw(layer)
            for xx in range(x0+5,x1-2,7 if kind=='flowstone' else 10):
                if kind=='boulder':continue
                trace=[]
                for yy in range(8,h-7,4):
                    spread=.32+.68*(yy/h)
                    px=mid+(xx-mid)*spread+math.sin(yy/14+xx)*2
                    trace.append((round(px),yy))
                stroke=Image.new('RGBA',(w,h));sd=ImageDraw.Draw(stroke)
                sd.line(trace,fill=(*self.ramps['limestone'][5 if xx%3 else 6],130),width=1)
                if xx%2:
                    # Branches join wider drips and stop before the footing.
                    sx,sy=trace[len(trace)//2]
                    sd.line([(sx-4,sy-11),(sx-2,sy-5),(sx,sy)],fill=(*self.ramps['limestone'][5],100))
                stroke.putalpha(ImageChops.multiply(stroke.getchannel('A'),layer.getchannel('A')))
                layer.alpha_composite(stroke)
            # Fracture and dissolved lip details; no horizontal brick courses.
            for yy in ((h//2+index*3,) if kind=='broken_column' else () if kind=='flowstone' else (h-19,)):
                stroke=Image.new('RGBA',(w,h));sd=ImageDraw.Draw(stroke)
                sd.line([(x0+2,yy),(mid-6,yy+3),(mid+3,yy+1)],fill=(*self.ramps['limestone'][2],160))
                stroke.putalpha(ImageChops.multiply(stroke.getchannel('A'),layer.getchannel('A')))
                layer.alpha_composite(stroke)
            im.alpha_composite(layer)
        if kind=='pendants':
            im=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return im

    def patch(self, name, index):
        size=(48+24*index,48+24*index);w,h=size;rng=random.Random(410+index)
        im=self.texture(size,240+index,name);mask=Image.new('L',size);d=ImageDraw.Draw(mask)
        points=[]
        for i in range(32):
            a=i*math.tau/32;r=rng.uniform(.74,.97)
            points.append((round(w/2+math.cos(a)*w*.48*r),round(h/2+math.sin(a)*h*.44*r)))
        d.polygon(points,fill=255)
        # Sparse hard clusters soften patch edges without blurred pixels.
        inner=mask.filter(__import__('PIL.ImageFilter',fromlist=['MinFilter']).MinFilter(5))
        for y in range(h):
            for x in range(w):
                if mask.getpixel((x,y)) and not inner.getpixel((x,y)):
                    if (x*17+y*23+index)%5<2:mask.putpixel((x,y),0)
        im.putalpha(mask)
        return im

    def shoreline(self, kind, index):
        size=(48,24) if kind=='edge' else (48,48)
        im=Image.new('RGBA',size);d=ImageDraw.Draw(im);w,h=size
        if kind=='edge':
            top=[(x,5+round(math.sin(x/8+index)*2)) for x in range(0,w,4)]
            points=top+[(w-1,h-1),(0,h-1)]
        elif kind=='corner':points=[(0,0),(20,0),(25,5),(28,17),(39,22),(47,23),(47,47),(0,47)]
        else:points=[(0,24),(12,22),(20,14),(24,0),(47,0),(47,47),(0,47)]
        im=self.clipped(size,points,index+453,bias=-.25);d=ImageDraw.Draw(im)
        line=points[:-2] if kind=='edge' else points[:6]
        d.line(line,fill=self.palette['calcite'],width=2)
        d.line([(x,y+3) for x,y in line],fill=self.palette['wet_edge'],width=3)
        return im

    def tunnel(self):
        w,h=96,88
        points=[(2,84),(5,48),(14,24),(29,10),(43,4),(57,6),(75,17),(88,35),(94,62),(93,84)]
        im=self.clipped((w,h),points,643);d=ImageDraw.Draw(im)
        recess=[(21,85),(23,53),(29,35),(39,25),(53,23),(65,33),(74,51),(76,85)]
        d.polygon(recess,fill='#263c38')
        d.polygon([(29,85),(30,55),(36,40),(46,32),(56,38),(64,55),(66,85)],fill='#172b2b')
        for offset in (0,9):
            d.line([(7,44+offset),(16,26+offset),(31,12+offset),(45,8+offset),(60,12+offset),(77,25+offset),(87,44+offset)],fill=self.ramps['limestone'][5],width=2)
        d.line([(8,64),(20,63)],fill=self.ramps['limestone'][1],width=2)
        d.line([(78,65),(92,68)],fill=self.ramps['limestone'][1],width=2)
        d.line([(23,84),(36,82),(50,84),(64,82),(76,84)],fill=self.palette['calcite'])
        return im

    def module(self, name, im, anchor=None, footprints=()):
        path=f'{PACK}/modules/{name.replace(".","/")}.png';self.emit(path,im)
        self.modules[name]={'frames':[path],'size':list(im.size),
                            'anchor':list(anchor or (im.width//2,im.height-4)),
                            'footprints':[list(r) for r in footprints]}
        return path

    def build(self):
        materials={}
        for name,count in self.recipe['materials'].items():
            paths=[]
            for i in range(count):
                path=f'{PACK}/tiles/{name}_{i:02}.png';self.emit(path,self.material_tile(name,i));paths.append(path)
            materials[name]={'tiles':paths}
        for i in range(self.recipe['wall_variants']):
            self.module(f'wall.front.{i}',self.wall(i),anchor=(48,64))
        for i in range(3):
            for name in ('return_left','return_right','concave','convex'):
                im=self.wall(i+7).crop((0,0,72,72));mask=im.getchannel('A');d=ImageDraw.Draw(mask)
                if name=='return_left':d.polygon([(0,0),(35,0),(0,56)],fill=0)
                elif name=='return_right':d.polygon([(38,0),(71,0),(71,56)],fill=0)
                elif name=='concave':d.polygon([(30,0),(72,0),(72,34),(50,18)],fill=0)
                else:d.polygon([(0,40),(0,72),(34,72),(13,58)],fill=0)
                im.putalpha(mask);self.module(f'wall.{name}.{i}',im,anchor=(36,64))
            im=self.wall(i+19).crop((0,0,96,48));d=ImageDraw.Draw(im)
            d.line([(0,39),(15,45),(29,41),(43,46),(59,39),(77,45),(95,40)],fill=self.palette['deep_joint'],width=3)
            self.module(f'wall.overhang.{i}',im,anchor=(48,43))
            for kind in ('stalagmites','broken_column','flowstone','pendants','boulder'):
                im=self.formation(kind,i)
                self.module(f'formation.{kind}.{i}',im,footprints=((im.width//4,im.height-13,im.width//2,10),) if kind!='pendants' else ())
            for name in self.recipe['materials']:
                self.module(f'patch.{name}.{i}',self.patch(name,i))
            for name in ('edge','corner','inner'):
                self.module(f'shoreline.{name}.{i}',self.shoreline(name,i))
            im=self.formation('boulder',i).crop((0,21,64,48));self.module(f'socket.{i}',im,anchor=(32,21),footprints=((10,15,44,10),))
        self.module('tunnel.north',self.tunnel(),anchor=(48,84))
        # Small transition tiles can be combined along arbitrary material edges.
        for name in ('damp','gravel','silt'):
            for edge in ('north','east','south','west','outer_ne','outer_se','outer_sw','outer_nw','inner_ne','inner_se','inner_sw','inner_nw'):
                im=self.material_tile(name,1);mask=Image.new('L',(24,24));d=ImageDraw.Draw(mask)
                if edge in ('north','south','east','west'):
                    poly=[(0,5),(6,3),(12,5),(18,2),(23,4),(23,23),(0,23)]
                    d.polygon(poly,fill=255)
                    if edge=='south':mask=mask.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                    elif edge=='east':mask=mask.transpose(Image.Transpose.ROTATE_90)
                    elif edge=='west':mask=mask.transpose(Image.Transpose.ROTATE_270)
                else:
                    d.polygon([(0,0),(13,0),(16,5),(21,9),(23,14),(23,23),(0,23)],fill=255)
                    rotation={'ne':0,'se':270,'sw':180,'nw':90}[edge[-2:]]
                    mask=mask.rotate(rotation)
                    if edge.startswith('inner'):mask=ImageChops.invert(mask)
                im.putalpha(mask);self.module(f'transition.{name}.{edge}',im,anchor=(0,0))
        board=Image.new('RGB',(1200,960),'#26322f');d=ImageDraw.Draw(board)
        font=ImageFont.load_default(size=17);small=ImageFont.load_default(size=13)
        d.text((20,14),'SANCTUARY LIMESTONE / native 24 px material review',font=font,fill='#e3dcc7')
        for row,(name,record) in enumerate(materials.items()):
            y=59+row*45;d.text((20,y+4),name.upper(),font=small,fill='#d3d5bc')
            for i,path in enumerate(record['tiles']):board.paste(Image.open(BytesIO(self.outputs[path])),(130+i*32,y))
        d.text((20,256),'Natural wall strata / erosion / calcite',font=font,fill='#e3dcc7')
        for i in range(6):
            im=self.wall(i);board.paste(im,(20+i*110,291),im)
        d.text((20,398),'Worn formations / sockets / shoreline',font=font,fill='#e3dcc7')
        for col,kind in enumerate(('stalagmites','broken_column','flowstone','pendants','boulder')):
            im=self.formation(kind,0);board.paste(im,(20+col*155,439),im)
            d.text((20+col*155,529),kind.replace('_',' '),font=small,fill='#d3d5bc')
        for i in range(3):
            im=self.shoreline('corner',i);board.paste(im,(835+i*84,447),im)
        d.text((20,583),'Larger material patches / native geometry',font=font,fill='#e3dcc7')
        for col,name in enumerate(materials):
            im=self.patch(name,2);board.paste(im,(20+col*160,624),im)
        d.text((20,758),'Source relationship / approved regional stone / original character scale',font=font,fill='#e3dcc7')
        for i,path in enumerate(self.recipe['source_assets'][:3]):
            im=Image.open(ROOT/path).convert('RGBA');board.paste(im,(20+i*150,808),im)
        ca=Image.open(ROOT/'assets/source/characters/caelan/overworld_refresh/legacy/idle_front.png').convert('RGBA')
        board.paste(ca,(655,808),ca);d.text((600,860),'Caelan: native scale',font=small,fill='#d3d5bc')
        d.text((20,902),'Unlit material board. Crystal emission and colored environment light remain runtime effects.',font=small,fill='#b9c8be')
        self.emit(f'{PACK}/materials_review.png',board)
        detail=Image.new('RGB',(1200,770),'#26322f');dd=ImageDraw.Draw(detail)
        dd.text((22,16),'Regional rock relationship / all scenery enlarged exactly 3x',font=font,fill='#e3dcc7')
        comparisons=[('Sanctuary exterior source',Image.open(ROOT/self.recipe['source_assets'][0]).convert('RGBA')),
                     ('Current slate cave',Image.open(ROOT/'assets/terrain/sanctuary_cave/walls/face_00.png').convert('RGBA')),
                     ('Proposed limestone',self.wall(0))]
        for i,(label,im) in enumerate(comparisons):
            x=22+i*390;dd.text((x,58),label,font=font,fill='#e3dcc7')
            large=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST)
            detail.paste(large,(x,94),large)
            char=ca.resize((ca.width*3,ca.height*3),Image.Resampling.NEAREST)
            detail.paste(char,(x+300,94+large.height-char.height),char)
        dd.text((22,345),'Natural limestone detail / full material-size context',font=font,fill='#e3dcc7')
        for i,kind in enumerate(('stalagmites','broken_column','flowstone','boulder')):
            im=self.formation(kind,0);large=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST)
            detail.paste(large,(22+i*292,390),large)
            dd.text((22+i*292,650),kind.replace('_',' '),font=small,fill='#cdd1bc')
        dd.text((22,704),'Neutral stone receives crystal color in the production lighting pass. No colored light is painted into these modules.',font=small,fill='#b9c8be')
        self.emit(f'{PACK}/regional_comparison.png',detail)
        inputs={path:sha256((ROOT/path).read_bytes()).hexdigest() for path in self.recipe['source_assets']}
        for path in ('assets/source/characters/caelan/overworld_refresh/legacy/idle_front.png','assets/terrain/sanctuary_cave/walls/face_00.png'):
            inputs[path]=sha256((ROOT/path).read_bytes()).hexdigest()
        inputs[SOURCE.relative_to(ROOT).as_posix()]=sha256(SOURCE.read_bytes()).hexdigest()
        manifest={'version':1,'id':self.recipe['id'],'status':'review','approval_status':'pending_review','tile_size':24,
                  'source_recipe':SOURCE.relative_to(ROOT).as_posix(),'materials':materials,
                  'modules':self.modules,'palette':self.palette,'inputs':inputs,
                  'artifacts':{path:sha256(data).hexdigest() for path,data in self.outputs.items()}}
        self.emit(f'{PACK}/assets.json',manifest)
        return self.outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    products=Author().build();changed=[]
    for path,data in products.items():
        destination=ROOT/path
        if not destination.exists() or destination.read_bytes()!=data:
            changed.append(path)
            if not args.check:
                destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
    if args.check and changed:raise SystemExit('Stale limestone assets: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(products)} native limestone exports')


if __name__=='__main__':main()
