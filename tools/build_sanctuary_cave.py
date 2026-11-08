"""Build the native Sanctuary cave kit and three authored exploration scenes.

All scenery is assembled from modular 24 px materials, native crystal sprites
and separately depth-sorted props. The recipe owns topology and placements;
collision, lighting sockets and overviews come from the same geometry.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import random
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parents[1]
PACK='assets/terrain/sanctuary_cave'
MAPS='assets/maps/sanctuary_cave'
SOURCE='assets/source/terrain/sanctuary_cave/recipe.json'
COLORS={'cyan':(94,201,215),'amethyst':(163,117,218),'opal':(197,221,216),'amber':(223,172,92)}
OUT={}


def emit(path,value):
    if isinstance(value,Image.Image):
        stream=BytesIO();value.save(stream,format='PNG');value=stream.getvalue()
    elif isinstance(value,(dict,list)):value=(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
    elif isinstance(value,str):value=value.encode()
    OUT[path]=value


def clamp(n):return max(0,min(255,n))


def tile(seed,kind='stone'):
    rng=random.Random(seed);im=Image.new('RGB',(24,24));d=ImageDraw.Draw(im)
    base={'stone':(83,86,97),'damp':(61,84,89),'scree':(88,82,91),'wall':(53,57,72)}[kind]
    for y in range(24):
        for x in range(24):
            n=rng.choice((-5,-3,-1,0,0,0,2,4));im.putpixel((x,y),tuple(clamp(c+n) for c in base))
    for _ in range(6 if kind!='scree' else 13):
        x=rng.randrange(1,22);y=rng.randrange(1,22);w=rng.randrange(2,8);h=rng.randrange(1,4)
        tone=rng.choice((-11,-7,5,8));c=tuple(clamp(v+tone) for v in base)
        d.line((x,y,min(23,x+w),y),fill=c,width=h)
        if kind=='scree':d.line((x,y,x+max(1,w//2),y-1),fill=tuple(clamp(v+13) for v in base))
    if seed%3==0:
        x=rng.randrange(4,12);y=rng.randrange(4,17)
        d.line([(x,y),(x+4,y+2),(x+7,y+1),(x+10,y+4)],fill=tuple(clamp(v-17) for v in base))
        d.line((x+5,y+2,x+4,y+5),fill=tuple(clamp(v-10) for v in base))
    return im


def rock(seed,w=48,h=42):
    rng=random.Random(seed);im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    p=[(2,h-10),(5,h//2),(w//4,8),(w//2,3),(w*3//4,9),(w-5,h//2),(w-2,h-9),(w*3//4,h-3),(w//3,h-2)]
    d.ellipse((1,h-12,w-1,h-1),fill='#282d3b')
    d.polygon(p,fill='#4d5364',outline='#303747')
    d.polygon([p[0],p[1],p[2],p[3],(w//2,h//2),(w//4,h-12)],fill='#6f7582')
    d.polygon([p[3],p[4],p[5],(w//2,h-10),(w//2,h//2)],fill='#5e6677')
    d.line([p[1],p[2],p[3],p[4]],fill='#8a8e99',width=1)
    d.line([(w//2,5),(w//2-3,h//2),(w//2+4,h-10)],fill='#3b4354')
    for _ in range(w*2):
        x=rng.randrange(5,w-5);y=rng.randrange(10,h-8)
        if im.getpixel((x,y))[3]:d.line((x,y,x+rng.randrange(1,3),y),fill=rng.choice(('#747c88','#525a6b','#858a95')))
    return im



def cliff(seed=0):
    """A reusable vertical crag with native layered mineral facets."""
    rng=random.Random(810+seed);im=Image.new('RGBA',(96,72),'#424b60');d=ImageDraw.Draw(im)
    for band in range(4):
        yy=band*17
        for x in range(-12,110,25):
            x+=rng.randrange(-4,5);top=yy+rng.randrange(-3,3);ww=rng.randrange(20,33);hh=rng.randrange(16,24)
            poly=[(x,top+3),(x+6,top),(x+ww-4,top+2),(x+ww,top+8),(x+ww-3,top+hh),(x+5,top+hh+1),(x-2,top+hh-4)]
            col=rng.choice(('#59677a','#687183','#586276','#727b8a','#4f5b70'))
            d.polygon(poly,fill=col,outline='#333f54')
            d.polygon([(x+6,top+1),(x+ww-4,top+3),(x+ww//2,top+8),(x+3,top+hh-3)],fill='#798492')
            d.line([(x+1,top+4),(x+6,top+1),(x+ww-5,top+3)],fill='#a2a5aa')
            d.line([(x+ww-2,top+9),(x+ww-5,top+hh-2),(x+7,top+hh)],fill='#283348',width=2)
    for _ in range(360):
        x=rng.randrange(96);y=rng.randrange(72);c=im.getpixel((x,y));delta=rng.choice((-12,-7,6,10))
        d.line((x,y,min(95,x+rng.randrange(1,3)),y),fill=tuple(clamp(v+delta) for v in c[:3]))
    for x in (15,53,82):
        yy=rng.randrange(8,16)
        d.line([(x,yy),(x-3,yy+13),(x+2,yy+20),(x-4,yy+34),(x-1,yy+45)],fill='#283348',width=1)
        d.line([(x+1,yy),(x-1,yy+12)],fill='#89949a')
    d.line((0,69,95,69),fill='#263245',width=3)
    return im


def spire(seed=0):
    im=Image.new('RGBA',(42,74));d=ImageDraw.Draw(im);rng=random.Random(seed)
    for x,height,width in ((12,48,13),(24,66,18),(34,32,10)):
        top=71-height;p=[(x,top),(x+width//3,top+9),(x+width//2,70),(x-width//2,70),(x-width//3,top+13)]
        d.polygon(p,fill='#576478',outline='#303e52');d.polygon([(x,top+2),(x,69),(x-width//2+2,69),(x-width//3+1,top+14)],fill='#808a98')
        d.line([(x,top+2),(x-width//3+1,top+14),(x-width//2+2,67)],fill='#a0a7ac')
        for yy in range(top+18,68,8):
            d.line((x-2,yy,x+2,yy+2),fill='#47546a')
    return im



def tunnel_mouth(facing):
    """Readable rock-framed passage, authored at native actor scale.

    Jambs sit outside the 52 px central passage. The worn threshold is surface
    detail, with no additional collision or change to authored transfer points.
    """
    south=facing=='south';height=64 if south else 88
    im=Image.new('RGBA',(96,height));d=ImageDraw.Draw(im)
    def points(values):
        return [(x,round((88-y)*height/88) if south else y) for x,y in values]
    surround=[(3,83),(5,48),(12,25),(27,10),(46,2),(66,9),(84,28),(92,51),(94,83)]
    d.polygon(points(surround),fill='#505d70',outline='#263347')
    # Uneven strata retain the same faceted material language as cave walls.
    for polygon,color in (([(5,49),(13,25),(27,11),(37,8),(25,31),(20,58),(16,82),(4,83)],'#7c8793'),
                          ([(28,11),(46,3),(65,10),(75,21),(58,17),(39,18),(25,32)],'#8c959d'),
                          ([(66,10),(84,28),(92,51),(93,82),(80,82),(76,49),(68,30),(58,17)],'#657387')):
        d.polygon(points(polygon),fill=color)
    recess=[(20,83),(21,53),(28,33),(40,23),(53,22),(67,33),(75,53),(77,83)]
    d.polygon(points(recess),fill='#101e2b',outline='#293d4e')
    inner=[(28,83),(29,55),(35,39),(46,31),(56,36),(65,54),(67,83)]
    d.polygon(points(inner),fill='#0b1420')
    for line in (((7,48),(15,27),(29,12),(45,5),(64,11),(82,29)),
                 ((6,65),(19,61)),((12,34),(25,39)),((21,18),(31,28)),
                 ((52,5),(49,20)),((71,18),(65,33)),((86,39),(74,44)),((91,62),(78,64))):
        d.line(points(line),fill='#a0a9ad',width=1)
    for line in (((11,48),(17,42),(17,31)),((32,12),(37,17),(34,23)),((82,31),(79,38),(85,48)),((85,65),(82,76))):
        d.line(points(line),fill='#334358',width=1)
    # A pale abraded edge leads the eye into the recess before E appears.
    d.line(points([(20,84),(34,82),(49,84),(64,82),(77,84)]),fill='#909c9c',width=2)
    return im

def container(kind,state):
    im=Image.new('RGBA',(40,36));d=ImageDraw.Draw(im)
    if kind=='pack':
        d.ellipse((7,26,33,33),fill='#252d38');d.polygon([(10,12),(15,7),(27,9),(32,15),(31,29),(9,29)],fill='#677b76',outline='#293d42')
        d.rectangle((13,10,29,18),fill='#8d9a89');d.line((20,11,20,28),fill='#c4b98b',width=2)
        d.rectangle((17,18,23,22),fill='#494b45');d.point((20,19),fill='#ddc385')
        if state=='open':d.polygon([(9,13),(14,5),(29,7),(31,11)],fill='#384c4e');d.line((13,14,28,15),fill='#b3b798')
    else:
        d.ellipse((3,27,37,34),fill='#252b37');d.rectangle((5,17,34,29),fill='#625040',outline='#2b3039')
        for y in (20,25):d.line((7,y,32,y),fill='#806b50')
        if state=='closed':
            d.polygon([(5,17),(8,9),(31,9),(34,17)],fill='#9b7d53',outline='#32373f')
            d.line((9,11,30,11),fill='#c1a36d');d.line((7,17,32,17),fill='#4b4139')
        else:
            d.rectangle((7,3,32,14),fill='#92764f',outline='#30363f');d.rectangle((10,5,29,11),fill='#4c4641');d.rectangle((7,16,32,20),fill='#242b36')
        for x in (10,28):d.rectangle((x,10 if state=='closed' else 17,x+2,29),fill='#939287')
        d.rectangle((18,17,22,22),fill='#b9b898');d.point((20,19),fill='#e3d7ac')
    return im


def marker():
    im=Image.new('RGBA',(28,40));d=ImageDraw.Draw(im)
    d.ellipse((3,32,25,39),fill='#2c3440');d.polygon([(6,34),(7,8),(12,4),(21,6),(22,34)],fill='#989e99',outline='#454e57')
    d.line((9,10,9,31),fill='#bbc0ac');d.line((12,14,18,14),fill='#586b70');d.arc((11,17,19,27),40,310,fill='#607c7e',width=1)
    d.rectangle((4,32,24,36),fill='#697a76');return im


def jagged_ellipse(d,center,radii,rng,fill):
    cx,cy=center;rx,ry=radii;points=[]
    for i in range(48):
        a=i*math.tau/48;noise=rng.uniform(.93,1.04)
        points.append((round((cx+math.cos(a)*rx*noise)/3)*3,round((cy+math.sin(a)*ry*noise)/3)*3))
    d.polygon(points,fill=fill)


def scene(spec,modules):
    key=spec['key'];w,h=spec['size'];rng=random.Random(130+len(key));base=f'{MAPS}/{key}';art=f'{PACK}/scenes/{key}'
    floor=Image.new('L',(w,h));fd=ImageDraw.Draw(floor)
    for _,_,center,radii in spec['rooms']:jagged_ellipse(fd,center,radii,rng,255)
    for path in spec['paths']:
        fd.line([tuple(p) for p in path],fill=255,width=108)
        for x,y in path:fd.ellipse((x-54,y-54,x+54,y+54),fill=255)
    # Material patches follow broad organic fields rather than visible tiles.
    ground=Image.new('RGB',(w,h));floor_tex=Image.new('RGB',(w,h));wall_tex=Image.new('RGB',(w,h))
    for y in range(0,h,24):
        for x in range(0,w,24):
            zone=math.sin(x/137)+math.cos(y/109)+math.sin((x+y)/211)
            kind='stone'
            floor_tex.paste(tile(rng.randrange(10)+{'stone':0,'damp':100,'scree':200}[kind],kind),(x,y));wall_tex.paste(tile(300+rng.randrange(10),'wall'),(x,y))
    tex=floor_tex.load()
    for yy in range(h):
        for xx in range(w):
            wave=math.sin(xx/137)+math.cos(yy/109)+math.sin((xx+yy)/211)
            wet=max(0.,min(1.,(-wave-.25)/2.1));warm=max(0.,min(1.,(wave-1.0)/1.5))
            r,g,b=tex[xx,yy];tex[xx,yy]=(clamp(round(r-18*wet+5*warm)),clamp(round(g-4*wet-3*warm)),clamp(round(b-7*wet-2*warm)))
    ground.paste(wall_tex);ground.paste(floor_tex,(0,0),floor)
    # Tall faceted faces extend above each northern floor contour. The same
    # exported wall modules are sampled here without rescaling their pixels.
    cliff_modules=[cliff(i) for i in range(3)];fp=floor.load();gp=ground.load()
    for x in range(w):
        for y in range(1,h):
            if fp[x,y] and not fp[x,y-1]:
                height=59+round(5*math.sin(x*.085))+((x//15)%3)*2
                mat=cliff_modules[(x//96)%3];mp=mat.load()
                for yy in range(max(0,y-height),y):
                    if not fp[x,yy]:
                        local=round((yy-y+height)*71/height)
                        gp[x,yy]=mp[x%96,local][:3]
                # Rugged top lip catches a narrow mineral rim.
                if y-height>0 and not fp[x,y-height]:gp[x,y-height]=(112,125,139)
    edge=ImageChops.subtract(floor,floor.filter(ImageFilter.MinFilter(5)))
    ground.paste('#303c4e',(0,0,w,h),edge)
    gd=ImageDraw.Draw(ground)
    # Long, irregular seams bind small texture marks into broad geology.
    for _ in range(95):
        x=rng.randrange(w);y=rng.randrange(h);length=rng.randrange(18,75)
        pts=[(x,y),(x+length//3,y+rng.randrange(-5,5)),(x+length*2//3,y+rng.randrange(-7,7)),(x+length,y+rng.randrange(-9,9))]
        if all(0<=xx<w and 0<=yy<h and fp[xx,yy] for xx,yy in pts):
            gd.line(pts,fill=rng.choice(('#384657','#69747f','#465963')),width=1)
            if _%3==0:gd.line([(xx,yy+1) for xx,yy in pts],fill='#879294',width=1)
    for _ in range(450):
        x=rng.randrange(w);y=rng.randrange(h)
        if fp[x,y]:
            gd.line((x,y,x+2,y),fill=rng.choice(('#6e8b91','#728095','#779595','#929999')))
    # Pools are physical, irregular depressions. Their shoreline stays readable.
    water=Image.new('L',(w,h));pd=ImageDraw.Draw(water)
    for center,radii in spec['pools']:jagged_ellipse(pd,center,radii,rng,255)
    shore=ImageChops.subtract(water.filter(ImageFilter.MaxFilter(9)),water)
    ground.paste('#788a91',(0,0,w,h),shore);ground.paste('#304b5b',(0,0,w,h),water)
    gd=ImageDraw.Draw(ground)
    for _ in range(650):
        x=rng.randrange(w);y=rng.randrange(h)
        if water.getpixel((x,y)):
            gd.line((x,y,x+rng.randrange(2,10),y),fill=rng.choice(('#436878','#537c88','#6d9b9f')))
    collision=ImageChops.invert(floor);collision=ImageChops.lighter(collision,water)
    entities=[];lights=[];treasures=[]
    def prop(identifier,image,pos,footprint=None,**extras):
        rec={'id':identifier,'position':list(pos),'sort_y':pos[1]+image.height-3,'sort_priority':0,'frames':[],'frame_duration_ms':700,'phase_offset':0,**extras}
        if 'image_path' in rec:path=rec.pop('image_path')
        else:path=f'{art}/props/{identifier}.png';emit(path,image)
        rec['frames']=[path];entities.append(rec)
        if footprint:
            rec['footprint']=list(footprint);ImageDraw.Draw(collision).rectangle((footprint[0],footprint[1],footprint[0]+footprint[2]-1,footprint[1]+footprint[3]-1),fill=255)
        return rec
    # Native boulders break up silhouettes away from authored route centers.
    rocks=[(120,715,40,34),(435,525,42,36),(1030,490,55,46)] if key=='entrance' else ([(350,660,80,95),(365,680,46,64),(590,280,54,44),(890,740,42,34)] if key=='hollow' else [(160,710,44,37),(540,460,42,38),(1010,300,44,48)])
    for index,(x,y,rw,rh) in enumerate(rocks):
        im=rock(10+index,rw,rh);prop(f'boulder_{index}',im,(x-rw//2,y-rh+5),(x-rw//3,y-7,rw*2//3,12))
    formations={'entrance':[(145,595),(520,335),(1060,650)],'hollow':[(130,605),(565,320),(1040,735)],'depths':[(110,625),(545,355),(1010,180)]}[key]
    for index,(x,y) in enumerate(formations):
        im=spire(index);prop(f'stalagmites_{index}',im,(x-21,y-70),(x-12,y-5,24,9),image_path=f'{PACK}/formations/stalagmites_{index}.png')
    for index,(x,y) in enumerate(formations[:2]):
        im=spire(index).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        rec=prop(f'stalactites_{index}',im,(x+35,y-100),image_path=f'{PACK}/formations/stalactites_{index}.png')
        rec['sort_y']=y+200
    if key=='hollow':
        # Old paving is only a surface treatment; it adds no invisible barrier.
        for yy in range(697,733,13):
            for xx in range(795,905,24):
                gd.rounded_rectangle((xx,yy,xx+20,yy+9),radius=2,fill='#7a8485',outline='#a3a89a')
                gd.line((xx+3,yy+5,xx+17,yy+5),fill='#687776')
    for index,(x,y,shape,color) in enumerate(spec['crystals']):
        module=modules['crystal.'+shape+'.'+color];ax,ay=module['anchor'];im=Image.open(ROOT/module['frames'][0]).convert('RGBA')
        rec=prop(f'crystal_{index}',im,(x-ax,y-ay),light_index=len(lights),reduced_motion_frame=2)
        rec.update(frames=module['frames'],phase_offset=index%6,source_module='crystal.'+shape+'.'+color)
        # Use a root immediately in front of the cluster so light enters the room.
        ly=y+13
        while ly<h-15 and floor.getpixel((x,ly))<128 and ly<y+60:ly+=3
        if not floor.getpixel((x,ly)):
            candidates=[(xx,yy) for yy in range(max(0,y-50),min(h,y+85),4) for xx in range(max(0,x-70),min(w,x+75),4) if floor.getpixel((xx,yy))]
            if candidates:xlight,ly=min(candidates,key=lambda p:(p[0]-x)**2+(p[1]-y-15)**2)
            else:xlight=x
        else:xlight=x
        lights.append({'position':[xlight,ly],'color':list(COLORS[color]),'radius':145 if shape.startswith('large') else 116,'phase':round(index*.37,3),'entity_id':rec['id']})
        fp=[x-9,y-3,18,6];rec['footprint']=fp;ImageDraw.Draw(collision).rectangle((fp[0],fp[1],fp[0]+17,fp[1]+5),fill=255)
    # Inset seams spread mineral growth along the faces between large fans.
    for index,(x,y,shape,color) in enumerate(spec['crystals']):
        if index%2:continue
        module=modules['vein.'+color];im=Image.open(ROOT/module['frames'][0]).convert('RGBA')
        rec=prop(f'wall_vein_{index}',im,(x+18,y-37),light_index=index,reduced_motion_frame=2)
        rec.update(frames=module['frames'],phase_offset=index%6,source_module='vein.'+color)
    # Reflections animate over an unchanged physical shoreline.
    for index,(center,radii) in enumerate(spec['pools']):
        cx,cy=center;rx,ry=radii;frames=[]
        for phase in range(6):
            reflection=Image.new('RGBA',(rx*2+1,ry*2+1));rd=ImageDraw.Draw(reflection)
            for line in range(12):
                xx=rx+round(math.sin(line*2.1)*rx*.55);yy=5+(line*13+phase*2)%(ry*2-10)
                alpha=55+((line+phase)%4)*18
                rd.line((xx-3,yy,xx+6+(line%3)*2,yy),fill=(151,208,209,alpha))
            local=water.crop((cx-rx,cy-ry,cx+rx+1,cy+ry+1));reflection.putalpha(ImageChops.multiply(reflection.getchannel('A'),local))
            path=f'{art}/water/reflection_{index}_{phase}.png';emit(path,reflection);frames.append(path)
        rec=prop(f'pool_reflection_{index}',Image.new('RGBA',(rx*2+1,ry*2+1)),(cx-rx,cy-ry),image_path=frames[0],reduced_motion_frame=2)
        rec.update(frames=frames,frame_duration_ms=950,sort_y=cy+ry)
    for identifier,kind,pos,approach,label in spec['treasures']:
        im=container(kind,'closed');rec=prop(identifier,im,(pos[0]-20,pos[1]-31),(pos[0]-14,pos[1]-5,28,10))
        rec.update(state='closed',state_images={state:f'{PACK}/containers/{kind}_{state}.png' for state in ('closed','open')},frames=[f'{PACK}/containers/{kind}_closed.png'])
        treasures.append({'id':identifier,'entity_id':identifier,'position':pos,'approach':approach,'kind':kind,'reward_id':identifier,'label':label})
    if key=='hollow':
        for index,(x,y) in enumerate(((770,650),(795,645),(850,750))):
            prop(f'keeper_marker_{index}',marker(),(x-14,y-34),(x-7,y-3,14,6))
    for identifier,pos,dest,landing,facing,label in spec['links']:
        orientation='south' if dest=='elden_vale_sanctuary' or (key=='hollow' and identifier=='entrance') or key=='depths' else 'north'
        im=tunnel_mouth(orientation);x,y=pos
        origin=(x-48,y-4) if orientation=='south' else (x-48,y-80)
        rec=prop('tunnel_'+identifier,im,origin,image_path=f'{PACK}/tunnels/mouth_{orientation}.png',link_id=identifier,kind='tunnel_mouth')
        rec['sort_y']=y-8
        # Native worn approach fans into the surrounding floor without a curb.
        for stripe in range(6):
            xx=x-22+stripe*8;yy=y-12 if orientation=='south' else y+12
            gd.line((xx,yy,xx+4,yy+(stripe%3-1)*2),fill='#899496')
    links=[{'id':identifier,'position':pos,'radius':24,'destination':dest,'landing':landing,'facing':facing,'label':label} for identifier,pos,dest,landing,facing,label in spec['links']]
    landmarks=[{'id':i,'name':n,'position':p,'description':d} for i,n,p,d in spec['landmarks']]
    inspections=[{'id':i,'position':p,'approach':a,'radius':44,'label':label,'text':text} for i,p,a,label,text in spec['inspections']]
    # Warm entrance daylight does not establish a second artificial light source.
    if key=='entrance':lights.append({'position':[240,760],'color':[226,221,184],'radius':160,'phase':0,'steady':True})
    emit(f'{art}/ground.png',ground);emit(f'{base}/collision.png',collision.convert('RGB'))
    overview=ground.convert('RGBA')
    for rec in sorted(entities,key=lambda r:r['sort_y']):
        path=rec['frames'][0];data=OUT.get(path)
        im=Image.open(BytesIO(data)) if data else Image.open(ROOT/path)
        overview.alpha_composite(im.convert('RGBA'),tuple(rec['position']))
    emit(f'{art}/overview.png',overview.convert('RGB'))
    data={'id':'sanctuary_cave_'+key,'name':'Sanctuary Cave — '+({'entrance':'Vein Gallery','hollow':'Splitstone Hollow','depths':'Echo Chamber'}[key]),'kind':'cave','tile_size':24,'size_pixels':[w,h],'size_tiles':[w//24,h//24],
          'player_probe_size':[24,12],'player_draw_anchor':[12,30],'spawn':spec['spawn'],'ground_frames':[f'{art}/ground.png'],'ground_frame_duration_ms':700,'collision':f'{base}/collision.png','overview':f'{art}/overview.png','entities':entities,'foreground':[],'doors':[],'npcs':[],'landmarks':landmarks,
          'cave':{'lights':lights,'pulse_period_ms':6000,'treasures':treasures,'links':links,'inspections':inspections,'routes':spec['routes'],'review_points':({'cave_entrance':[240,690],'vein_gallery':[390,440],'reflecting_grotto':[840,730]} if key=='entrance' else {'splitstone_hollow':[310,760],'keeper_recess':[875,720],'deep_gallery':[720,325]} if key=='hollow' else {'quiet_shelf':[400,440],'echo_chamber':[795,300]}),'encounter_spaces':([{'id':'future_miniboss','center':[795,260],'radius':100}] if key=='depths' else [{'id':key+'_future_encounter','center':spec['rooms'][0][2],'radius':65}])}}
    emit(f'{base}/map.json',data)
    return overview,data


def build():
    OUT.clear();spec=json.loads((ROOT/SOURCE).read_text())
    modules=json.loads((ROOT/'assets/terrain/sanctuary_fantasy/crystals/assets.json').read_text())['modules'];manifest={'version':1,'id':'terrain.sanctuary.cave.24','tile_size':24,'source_recipe':SOURCE,'modules':{}}
    board=Image.new('RGB',(768,560),'#222b39');d=ImageDraw.Draw(board);d.text((16,12),'SANCTUARY CAVE  /  native 24 px material library',fill='#e5e0cb')
    for row,kind in enumerate(('stone','damp','scree','wall')):
        d.text((16,45+row*45),kind.upper(),fill='#c2cbd0')
        for i in range(10):
            im=tile(i+row*100,kind);path=f'{PACK}/tiles/{kind}_{i:02}.png';emit(path,im);manifest['modules'][kind+f'.{i:02}']={'frames':[path],'size':[24,24]};board.paste(im,(130+i*30,40+row*45))
    for i in range(5):
        im=rock(i,40+i*9,40+i*7);path=f'{PACK}/formations/boulder_{i:02}.png';emit(path,im);manifest['modules']['boulder.'+str(i)]={'frames':[path],'size':list(im.size)};board.paste(im,(20+i*90,235),im)
    for j,kind in enumerate(('chest','pack')):
        for i,state in enumerate(('closed','open')):
            im=container(kind,state);path=f'{PACK}/containers/{kind}_{state}.png';emit(path,im);manifest['modules'][kind+'.'+state]={'frames':[path],'size':list(im.size)};board.paste(im,(30+i*65+j*180,350),im)
    for i in range(3):
        im=cliff(i);path=f'{PACK}/walls/face_{i:02}.png';emit(path,im);manifest['modules'][f'wall.face.{i}']={'frames':[path],'size':list(im.size),'anchor':[48,71]}
        for kind in ('return_left','return_right','overhang'):
            part=im.copy();mask=Image.new('L',im.size);md=ImageDraw.Draw(mask)
            poly=([(0,0),(95,0),(95,17),(30,25),(0,71)] if kind=='overhang' else [(0,0),(72,9),(95,71),(0,71)] if kind=='return_left' else [(24,9),(95,0),(95,71),(0,71)])
            md.polygon(poly,fill=255);part.putalpha(mask);p=f'{PACK}/walls/{kind}_{i:02}.png';emit(p,part);manifest['modules'][f'wall.{kind}.{i}']={'frames':[p],'size':list(part.size)}
        im=spire(i);path=f'{PACK}/formations/stalagmites_{i}.png';emit(path,im);manifest['modules'][f'stalagmites.{i}']={'frames':[path],'size':list(im.size)}
        pendant=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM);p=f'{PACK}/formations/stalactites_{i}.png';emit(p,pendant);manifest['modules'][f'stalactites.{i}']={'frames':[p],'size':list(pendant.size)}
    for orientation in ('north','south'):
        im=tunnel_mouth(orientation);path=f'{PACK}/tunnels/mouth_{orientation}.png';emit(path,im)
        manifest['modules']['tunnel.mouth.'+orientation]={'frames':[path],'size':list(im.size),'anchor':[48,80] if orientation=='north' else [48,4]}
        board.paste(im,(510+(0 if orientation=='north' else 105),230),im)
    im=marker();emit(f'{PACK}/keeper_marker.png',im);manifest['modules']['keeper_marker']={'frames':[f'{PACK}/keeper_marker.png'],'size':list(im.size)};board.paste(im,(400,350),im)
    for i,color in enumerate(COLORS):
        module=modules['crystal.medium_fan.'+color];im=Image.open(ROOT/module['frames'][0]).convert('RGBA');board.paste(im,(20+i*110,440),im);d.text((20+i*110,525),color,fill='#c2cbd0')
    ca=Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA');board.paste(ca,(630,350),ca);d.text((590,390),'Caelan / scale',fill='#c2cbd0')
    for i in range(3):
        wall=cliff(i);board.paste(wall,(470+i*98,70),wall)
    d.text((475,155),'Layered cliff faces / native pixels',fill='#c2cbd0')
    emit(f'{PACK}/materials_review.png',board)
    overviews=[]
    for sc in spec['scenes']:overviews.append(scene(sc,modules))
    atlas=Image.new('RGB',(1152,350),'#222b39');ad=ImageDraw.Draw(atlas)
    for i,(im,data) in enumerate(overviews):
        im.thumbnail((370,300));atlas.paste(im,(i*384+7,40));ad.text((i*384+10,12),data['name'],fill='#e5e0cb')
    emit(f'{PACK}/layout_overview.png',atlas)
    manifest['inputs']={'recipe':{'path':SOURCE,'sha256':sha256((ROOT/SOURCE).read_bytes()).hexdigest()},'crystals':{'path':'assets/terrain/sanctuary_fantasy/crystals/assets.json','sha256':sha256((ROOT/'assets/terrain/sanctuary_fantasy/crystals/assets.json').read_bytes()).hexdigest()}}
    reused={path for module in modules.values() for path in module.get('frames',[]) if isinstance(path,str)}
    manifest['inputs']['crystal_frames']={path:sha256((ROOT/path).read_bytes()).hexdigest() for path in sorted(reused)}
    manifest['artifacts']={path:sha256(value).hexdigest() for path,value in OUT.items()};emit(f'{PACK}/assets.json',manifest)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();build();changed=[]
    for path,data in OUT.items():
        destination=ROOT/path
        if not destination.exists() or destination.read_bytes()!=data:
            changed.append(path)
            if not args.check:destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
    if args.check and changed:raise SystemExit('Stale cave exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(OUT)} Sanctuary cave artifacts')

if __name__=='__main__':main()
