"""Build reusable native water, wet limestone banks and cave seepage modules.

Six short frames move only water highlights. Fixed monochrome masks accompany
water regions; every bank is identical through animation. The existing cave,
base limestone pack and game code are read-only inputs.
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

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_limestone_cave_assets import Author

SOURCE = ROOT/'assets/source/terrain/limestone_cave/water.json'
PACK = 'assets/terrain/limestone_cave/water'


def color(value):return tuple(bytes.fromhex(value.removeprefix('#')))


def png(image):
    output=BytesIO();image.save(output,format='PNG');return output.getvalue()


def rectangles(mask):
    """Merge equal scanline runs into exact, non-overlapping region rectangles."""
    active={};done=[]
    for y in range(mask.height+1):
        runs=[];start=None
        if y<mask.height:
            for x in range(mask.width+1):
                filled=x<mask.width and mask.getpixel((x,y))>0
                if filled and start is None:start=x
                elif not filled and start is not None:runs.append((start,x-start));start=None
        for key in list(active):
            if key not in runs:done.append(active.pop(key))
        for x,width in runs:
            if (x,width) in active:active[x,width][3]+=1
            else:active[x,width]=[x,y,width,1]
    return done


def rotated(image, direction):
    return image.transpose({'north':Image.Transpose.ROTATE_180,
                            'east':Image.Transpose.ROTATE_270,
                            'west':Image.Transpose.ROTATE_90}[direction]) if direction!='south' else image.copy()


class WaterAuthor:
    def __init__(self):
        self.spec=json.loads(SOURCE.read_text());self.base=Author()
        self.pal={key:([color(v) for v in value] if isinstance(value,list) else color(value))
                  for key,value in self.spec['palette'].items()}
        self.outputs={};self.modules={};self.frames={}

    def emit(self,path,value):
        self.outputs[path]=png(value) if isinstance(value,Image.Image) else (json.dumps(value,indent=2)+'\n').encode()

    def water(self,size,depth,index,phase):
        """Quiet native clustered water; glints change on a periodic six-frame clock."""
        ramp=self.pal[depth];image=Image.new('RGBA',size,(*ramp[0],255));draw=ImageDraw.Draw(image)
        rng=random.Random(self.spec['seed']+index*137+len(depth))
        # Fixed horizontal variations retain broad calm areas between ripples.
        for row in range(-3,size[1],5):
            offset=rng.randrange(0,7)
            for x in range(-8,size[0],13):
                xx=x+offset;yy=row+(x//13)%3
                draw.line((xx,yy,xx+rng.randrange(3,9),yy),fill=ramp[1])
        for ordinal in range(max(3,size[0]*size[1]//100)):
            x=(rng.randrange(size[0])+phase*(1 if depth=='shallow' else -1))%size[0]
            y=(rng.randrange(size[1])+round(math.sin((phase+ordinal)*math.tau/6)))%size[1]
            width=2+ordinal%4
            tone=ramp[2] if (ordinal+phase)%4 else ramp[3]
            for point in range(width):draw.point(((x+point)%size[0],y),fill=tone)
        return image

    def bank_mask(self,kind,index):
        mask=Image.new('L',(24,24));draw=ImageDraw.Draw(mask)
        if kind in ('north','east','south','west'):
            points=[(0,7),(5,6+index),(11,8),(17,6),(23,7),(23,23),(0,23)]
            draw.polygon(points,fill=255)
            return rotated(mask,{'north':'south','south':'north','east':'east','west':'west'}[kind])
        inner=kind.startswith('inner');quadrant=kind.rsplit('_',1)[1]
        points=([(0,0),(9,0),(10,5+index),(15,9),(19,11),(23,11),(23,23),(0,23)]
                if inner else [(0,7),(5,8),(10,10+index),(14,15),(17,23),(0,23)])
        draw.polygon(points,fill=255)
        return mask.rotate({'ne':0,'se':270,'sw':180,'nw':90}[quadrant])

    def stone_bank(self,mask,index,transparent=False):
        """A damp limestone rim and pale mineral lip, fixed in every frame."""
        size=mask.size;image=self.base.texture(size,index+472,'damp',bias=.2)
        if transparent:
            dilation=mask.filter(ImageFilter.MaxFilter(11))
            image.putalpha(dilation)
        # Only the dry side receives the short pale mineral edge.
        lip=ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(3)),mask)
        broad=ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(7)),mask)
        image.paste((*self.pal['wet_rock'],255),(0,0,*size),broad)
        image.paste((*self.pal['mineral_crust'],255),(0,0,*size),lip)
        if transparent:
            image.putalpha(ImageChops.lighter(mask.filter(ImageFilter.MaxFilter(11)),image.getchannel('A')))
        return image

    def bank(self,kind,index,phase):
        mask=self.bank_mask(kind,index);image=self.stone_bank(mask,index)
        image.paste(self.water(mask.size,'shallow',index,phase),(0,0),mask)
        return image,mask

    def stream_mask(self,kind,index):
        size=(48,48);mask=Image.new('L',size);draw=ImageDraw.Draw(mask)
        n=(24,0);e=(47,24);s=(24,47);w=(0,24);middle=(24,24)
        connections={'vertical':['north','south'],'horizontal':['east','west'],
          'bend_ne':['north','east'],'bend_se':['south','east'],
          'bend_sw':['south','west'],'bend_nw':['north','west'],
          't_n':['north','east','west'],'t_e':['north','east','south'],
          't_s':['east','south','west'],'t_w':['north','south','west'],
          'cross':['north','east','south','west'],'inlet':['south'],'outlet':['north']}[kind]
        endpoints={'north':n,'east':e,'south':s,'west':w}
        bend=index*2-1
        for direction in connections:
            endpoint=endpoints[direction]
            halfway=((endpoint[0]+middle[0])//2,(endpoint[1]+middle[1])//2)
            if direction in ('north','south'):halfway=(halfway[0]+bend,halfway[1])
            else:halfway=(halfway[0],halfway[1]+bend)
            draw.line([endpoint,halfway,middle],fill=255,width=14)
            for x,y in (halfway,middle):draw.ellipse((x-6,y-6,x+6,y+6),fill=255)
        if kind=='inlet':draw.ellipse((19,8,29,23),fill=255);draw.line((24,16,24,27),fill=255,width=6)
        if kind=='outlet':draw.ellipse((15,20,33,38),fill=255)
        # Pillow's clipped diagonal line caps taper asymmetrically at the far
        # image edge. Author short, explicit connection throats instead: every
        # open port has the same 14 native pixels and joins the existing channel
        # nine pixels inside the tile. Interior bends/basins remain unchanged.
        for box in ((0,0,47,8),(0,39,47,47),(0,0,8,47),(39,0,47,47)):
            draw.rectangle(box,fill=0)
        throats={'north':(17,0,30,8),'south':(17,39,30,47),
                 'east':(39,17,47,30),'west':(0,17,8,30)}
        for direction in connections:draw.rectangle(throats[direction],fill=255)
        self.validate_stream_ports(mask,connections)
        return mask,connections

    @staticmethod
    def validate_stream_ports(mask,connections):
        """Declared stream edges must tile without gaps or sideways water leaks."""
        edges={'north':lambda p:(p,0),'south':lambda p:(p,47),
               'east':lambda p:(47,p),'west':lambda p:(0,p)}
        for direction,point in edges.items():
            actual={p for p in range(48) if mask.getpixel(point(p))}
            expected=set(range(17,31)) if direction in connections else set()
            if actual!=expected:
                raise ValueError('Water port disagrees with its connection: '+direction)

    def stream(self,kind,index,phase):
        mask,connections=self.stream_mask(kind,index);image=self.stone_bank(mask,index+100,True)
        image.paste(self.water(mask.size,'shallow',index+5,phase),(0,0),mask)
        return image,mask,connections

    def overlay(self,kind,index,phase):
        sizes={'seepage':(32,64),'wet_crack':(48,32),'trickle':(24,72),'drip':(16,64),'ripple':(32,20),'crust_edge':(32,24),'crust_corner':(32,24)}
        size=sizes[kind];image=Image.new('RGBA',size);draw=ImageDraw.Draw(image)
        if kind in ('seepage','wet_crack'):
            vertical=kind=='seepage'
            lines=[[(12+index*3,3),(10+index*3,16),(15+index,29),(12+index*2,46),(16,59)],
                   [(13,25),(22,29),(25,41),(22,50)]] if vertical else [[(2,12+index),(11,9+index*2),(21,14+index),(31,11+index),(45,16+index)],[(19+index,13),(23+index,21),(32,25+index)]]
            for ordinal,points in enumerate(lines):
                draw.line(points,fill=(*self.pal['wet_shadow'],175),width=5)
                draw.line(points,fill=(*self.pal['wet_rock'],210),width=3)
                draw.line([(x-1,y) for x,y in points],fill=(*self.pal['mineral_crust'],145))
                segment=(phase+ordinal)%len(points);x,y=points[segment]
                draw.line((x,y,x,y+2) if vertical else (x,y,x+3,y),fill=(*self.pal['ripple'],190))
            if vertical:
                yy=7+(phase*8+index*5)%48;xx=12+index*2
                draw.line((xx,yy,xx,yy+3),fill=(*self.pal['ripple'],195))
        elif kind=='trickle':
            # Stationary calcite/wet throat surrounds a moving water ribbon.
            draw.line([(8,0),(10,12),(8,28),(11,43),(10,61)],fill=(*self.pal['wet_shadow'],170),width=8)
            draw.line([(6,0),(8,12),(6,28),(9,43),(8,61)],fill=(*self.pal['mineral_crust'],200),width=2)
            for yy in range(0,64):
                xx=9+round(math.sin(yy/11+index)*1.4)
                draw.point((xx,yy),fill=(*self.pal['wet_rock'],210))
                if (yy-phase*3)%13<4:draw.point((xx+1,yy),fill=(*self.pal['ripple'],230))
            # A compact splash fits the same fixed ground basin.
            draw.arc((3,61,20,70),0,180,fill=(*self.pal['ripple'],150),width=1)
            xx=4+(phase*3)%14;draw.point((xx,65-phase%3),fill=(*self.pal['ripple'],180))
        elif kind=='drip':
            yy=7+(phase*9+index*4)%48;xx=7+index
            draw.line((xx,yy,xx,yy+2),fill=(*self.pal['ripple'],220))
            draw.point((xx+1,yy),fill=(*self.pal['ripple'],155))
            if phase>2:
                rx=2+(phase-2)*2
                draw.ellipse((8-rx,58-rx//3,8+rx,58+rx//3),outline=(*self.pal['ripple'],max(45,180-phase*23)))
        elif kind=='ripple':
            radius=3+phase*2+index
            draw.ellipse((16-radius,10-radius//3,16+radius,10+radius//3+index),outline=(*self.pal['ripple'],205-phase*24))
            if phase>2:draw.ellipse((12,9,20,12),outline=(*self.pal['ripple'],60))
        else:
            points=([(1,8),(7,5+index),(14,7-index),(21,4+index),(30,7)] if kind=='crust_edge' else [(3,0),(5+index,9),(13,17-index),(25,21),(31,20-index)])
            draw.line(points,fill=(*self.pal['wet_shadow'],200),width=5)
            draw.line(points,fill=(*self.pal['wet_rock'],230),width=3)
            draw.line([(x,y-1) for x,y in points],fill=(*self.pal['mineral_crust'],255),width=2)
            for x,y in points[1:-1]:draw.point((x+2,y-2),fill=(*self.base.ramps['limestone'][6],255))
        return image

    def add(self,name,images,mask=None,connections=(),kind='water',anchor=None):
        paths=[];w,h=images[0].size
        for phase,image in enumerate(images):
            path=f'{PACK}/modules/{name.replace(".","/")}/frame_{phase:02}.png'
            self.emit(path,image);paths.append(path)
        record={'frames':paths,'size':[w,h],'anchor':list(anchor or (w//2,h-2)),
                'footprints':[],'collision_kind':kind,'water_regions':rectangles(mask) if mask is not None else [],
                'frame_duration_ms':self.spec['frame_duration_ms'],'reduced_motion_frame':min(2,len(paths)-1),
                'banks_fixed':True}
        if mask is not None:
            path=f'{PACK}/masks/{name.replace(".","/")}.png';self.emit(path,mask.convert('RGB'));record['water_mask']=path
        if connections:record['connections']=list(connections)
        if name.startswith('stream.'):
            record['ports']={direction:{'first_pixel':17,'last_pixel':30,'width':14}
                             for direction in connections}
        self.modules[name]=record;self.frames[name]=images

    def build(self):
        count=self.spec['pulse_frames']
        for depth in ('shallow','deep'):
            for index in range(self.spec['water_variants']):
                images=[self.water((24,24),depth,index,phase) for phase in range(count)]
                self.add(f'water.{depth}.{index}',images,Image.new('L',(24,24),255))
        directions=('north','east','south','west','outer_ne','outer_se','outer_sw','outer_nw','inner_ne','inner_se','inner_sw','inner_nw')
        for kind in directions:
            for index in range(self.spec['bank_variants']):
                values=[self.bank(kind,index,phase) for phase in range(count)]
                self.add(f'bank.{kind}.{index}',[v[0] for v in values],values[0][1])
        kinds=('vertical','horizontal','bend_ne','bend_se','bend_sw','bend_nw','t_n','t_e','t_s','t_w','cross','inlet','outlet')
        for kind in kinds:
            for index in range(self.spec['stream_variants']):
                values=[self.stream(kind,index,phase) for phase in range(count)]
                self.add(f'stream.{kind}.{index}',[v[0] for v in values],values[0][1],values[0][2])
        for kind,number in (('seepage',3),('wet_crack',3),('trickle',2),('drip',2),('ripple',2),('crust_edge',2),('crust_corner',2)):
            for index in range(number):
                key={'seepage':'seepage.wall','trickle':'trickle.wall','drip':'drip.falling','ripple':'ripple.small','crust_edge':'crust.edge','crust_corner':'crust.corner'}.get(kind,kind)
                images=[self.overlay(kind,index,phase) for phase in range(1 if kind.startswith('crust') else count)]
                self.add(f'{key}.{index}',images,kind='none')
        self.board()
        self.outputs[f'{PACK}/README.md']=(
            '# Cave water and seepage modules\n\nApproval status: pending visual review.\n\n'
            'Native 24-pixel water tiles, fixed limestone banks, 48-pixel stream prefabs,\n'
            'wet cracks, seepage, trickles, falling drops, ripples and mineral crusts.\n'
            'Water highlights animate in six 140 ms frames; bank pixels and fixed\n'
            'water masks never change. Reduced motion holds frame 2.\n\n'
            '`water_regions` is an exact set of nonoverlapping [x,y,w,h] rectangles;\n'
            '`water_mask` is the matching white-water/black-ground bitmap.\n'
            'Water uses the existing blocked-water rule; shallow is a material\n'
            'appearance, not a new movement mechanic. Decorative effects add no\n'
            'floor collision. Anchors are bottom center; stream connections name\n'
            'the open ports. Native terrain remains independent of crystal light.\n\n'
            'Build with `python tools/build_dungeon_water.py`; use `--check` for\n'
            'deterministic read-only verification. Source: assets/source/terrain/\n'
            'limestone_cave/water.json. The live cave and runtime are untouched.\n').encode()
        inputs=[SOURCE,Path(__file__).resolve(),ROOT/'tools/build_limestone_cave_assets.py',
                ROOT/'assets/source/terrain/limestone_cave/recipe.json',
                ROOT/'assets/terrain/overworld/elden_vale/polish/props/ridge.png',
                ROOT/'assets/characters/caelan/idle_front.png']
        manifest={'version':1,'id':self.spec['id'],'approval_status':self.spec['approval_status'],
                  'tile_size':24,'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
                  'modules':self.modules,'inputs':{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in inputs},
                  'artifacts':{path:sha256(raw).hexdigest() for path,raw in self.outputs.items()}}
        self.emit(f'{PACK}/assets.json',manifest)
        return self.outputs

    def board(self):
        names=list(self.modules);cols=8;cellw,cellh=150,190
        rows=math.ceil(len(names)/cols);images=[]
        font=ImageFont.load_default(size=12);title=ImageFont.load_default(size=18)
        for phase in range(6):
            board=Image.new('RGB',(cols*cellw+24,rows*cellh+134),'#22312f');draw=ImageDraw.Draw(board)
            draw.text((16,10),'CAVE WATER / native pixel modules at exact 2x scale',fill='#e6dfc9',font=title)
            draw.text((16,36),'Fixed limestone banks and water masks / six 140 ms frames / shallow and deep / seepage and drops',fill='#c4d2c6',font=font)
            for index,name in enumerate(names):
                x=12+index%cols*cellw;y=110+index//cols*cellh
                frame=self.frames[name][phase%len(self.frames[name])]
                frame=frame.resize((frame.width*2,frame.height*2),Image.Resampling.NEAREST)
                board.paste(frame,(x+(cellw-frame.width)//2,y),frame)
                label=name.replace('stream.','stream.\n').replace('bank.','bank.\n')
                draw.multiline_text((x+3,y+150),label,fill='#e6dfc9',font=font,spacing=2)
            ca=Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
            ca=ca.resize((ca.width*2,ca.height*2),Image.Resampling.NEAREST)
            board.paste(ca,(cols*cellw-74,10),ca)
            draw.text((cols*cellw-150,55),'Caelan / same 2x',fill='#c4d2c6',font=font)
            images.append(board)
        self.emit(f'{PACK}/water_review.png',images[2])
        stream=BytesIO();images[0].save(stream,format='GIF',save_all=True,append_images=images[1:],duration=140,loop=0)
        self.outputs[f'{PACK}/water_review.gif']=stream.getvalue()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    output=WaterAuthor().build();changed=[]
    for relative,raw in output.items():
        path=ROOT/relative
        if not path.exists() or path.read_bytes()!=raw:
            changed.append(relative)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if args.check and changed:raise SystemExit('Stale water exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(output)} reusable cave water exports')
    return 0


if __name__=='__main__':raise SystemExit(main())
