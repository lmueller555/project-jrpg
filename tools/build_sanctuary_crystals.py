"""Author reusable native crystal, ancient-stone and remembrance modules.

Shard/facet geometry is authored at native resolution. Stone retains the
established limestone pixels; no painted scene or arbitrary image scaling is
an input. Animation changes only internal facets, leaving solid roots fixed.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/sanctuary_fantasy/crystals.json'
OUTPUT = ROOT/'assets/terrain/sanctuary_fantasy/crystals'


def png(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def stone_texture(size, texture, polygon, holes=()):
    image=Image.new('RGBA',size)
    for y in range(0,size[1],texture.height):
        for x in range(0,size[0],texture.width):image.alpha_composite(texture,(x,y))
    mask=Image.new('L',size);draw=ImageDraw.Draw(mask)
    draw.polygon(polygon,fill=255)
    for hole in holes:draw.polygon(hole,fill=0)
    image.putalpha(mask);image.paste((0,0,0,0),mask=ImageChops.invert(mask))
    return image


def socket(size, texture, wide=False):
    w,h=size
    points=[(2,h-5),(5,h-11),(w//3,h-14),(w//2,h-11),
            (w*3//4,h-13),(w-4,h-8),(w-2,h-4),(w-8,h-1),(8,h-1)]
    image=stone_texture(size,texture,points)
    d=ImageDraw.Draw(image)
    d.line(points+[points[0]],fill='#3d5148')
    d.line([(6,h-10),(w//3,h-13),(w//2,h-10),(w*3//4,h-12)],fill='#9ba68b')
    d.line([(w//3,h-11),(w//3-2,h-4),(w//3+3,h-2)],fill='#4d6555')
    d.line([(w*3//4,h-10),(w*3//4-2,h-5),(w-6,h-4)],fill='#4d6555')
    if wide:
        d.line([(9,h-5),(16,h-7),(24,h-4)],fill='#7b8f73')
        d.line([(w-23,h-6),(w-17,h-8),(w-11,h-5)],fill='#87997a')
    return image


def shard(image, geometry, palette, phase, ordinal):
    bx,by,tx,ty,width=geometry
    height=by-ty
    shoulder=ty+max(3,round(height*.13))
    left=(tx-max(2,width//2),shoulder)
    right=(tx+max(2,width//2),shoulder+1)
    lb=(bx-width//2,by-2);rb=(bx+width//2,by-2)
    ridge=(round(tx*.64+bx*.36),round(ty+height*.42))
    points=[(tx,ty),right,rb,(bx,by),lb,left]
    d=ImageDraw.Draw(image)
    d.polygon(points,fill=palette['shadow'],outline=palette['deep'])
    d.polygon([(tx,ty),left,lb,(bx,by-2),ridge],fill=palette['mid'])
    d.polygon([(tx,ty),ridge,(bx,by-2),rb,right],fill=palette['light'])
    d.polygon([(tx,ty),left,ridge,right],fill=palette['bright'])
    d.line([(tx,ty+1),ridge,(bx,by-3)],fill=palette['bright'])
    d.line([left,lb],fill=palette['shadow'])
    # Sparse, deliberately arranged mineral bands interrupt long clean facets.
    for ratio in (.38,.62,.77):
        yy=round(ty+height*ratio)
        xx=round(tx+(bx-tx)*ratio)
        half=max(1,round(width*(.35+.1*ratio)))
        d.line([(xx-half,yy),(xx,yy+2),(xx+half-1,yy+1)],fill=palette['mid'])
        if ratio==.62:d.line([(xx+1,yy+3),(xx+half-1,yy+2)],fill=palette['shadow'])
    # Each frame brightens a different internal edge; neither canvas alpha nor
    # root pixels depend on phase. No moving star is placed outside a shard.
    ratio=(.23,.34,.47,.57,.43,.29)[phase]
    yy=round(ty+height*ratio);xx=round(tx+(bx-tx)*ratio)
    shimmer=Image.new('RGBA',image.size);sd=ImageDraw.Draw(shimmer)
    if ordinal%2==0:
        sd.line([(xx,yy-2),(xx,yy+2)],fill=palette['glint'])
        sd.line([(xx-1,yy),(xx+2,yy)],fill=palette['glint'])
    else:sd.line([(xx,yy),(xx+max(1,width//4),yy-1)],fill=palette['bright'])
    physical=Image.new('L',image.size);ImageDraw.Draw(physical).polygon(points,fill=255)
    shimmer.putalpha(ImageChops.multiply(shimmer.getchannel('A'),physical))
    # Small mineral inclusions are fixed, useful close to the player scale.
    ratio=.71;xx=round(tx+(bx-tx)*ratio);yy=round(ty+height*ratio)
    d.point((xx-1,yy),fill=palette['deep'])
    d.point((xx,yy+1),fill=palette['shadow'])
    image.alpha_composite(shimmer)


def crystal(spec,palette,phase,texture):
    image=Image.new('RGBA',tuple(spec['size']))
    for ordinal,geometry in enumerate(spec['shards']):
        shard(image,geometry,palette,phase,ordinal)
    # A small socket visually anchors the cluster, not an opaque rectangle.
    ax,ay=spec['anchor'];base=socket((min(36,image.width-2),16),texture)
    image.alpha_composite(base,(ax-base.width//2,ay-11))
    d=ImageDraw.Draw(image)
    d.line([(ax-7,ay),(ax-3,ay-2),(ax+2,ay),(ax+8,ay-2)],fill=palette['deep'])
    d.line([(ax-2,ay-1),(ax+1,ay-3),(ax+3,ay-1)],fill=palette['mid'])
    return image


def vein(palette,phase):
    image=Image.new('RGBA',(48,32));d=ImageDraw.Draw(image)
    paths=[[(2,26),(13,21),(20,14),(30,11),(36,3)],
           [(13,21),(15,9),(12,4)],[(20,14),(29,22),(42,24)],
           [(30,11),(42,8),(46,3)]]
    for points in paths:
        d.line(points,fill=palette['deep'],width=3)
        d.line(points,fill=palette['mid'],width=1)
    for index,points in enumerate(paths):
        x,y=points[1]
        d.line([(x,y),(x+2,y-1)],fill=palette['bright'] if (phase+index)%3 else palette['glint'])
    return image


def ruins(texture):
    result={}
    outlines={
        'slab':((48,32),[(2,20),(8,7),(29,3),(44,11),(46,23),(35,29),(9,28)]),
        'stele':((32,52),[(6,48),(5,20),(9,5),(17,2),(25,9),(27,48)]),
        'corner':((48,40),[(2,35),(4,13),(15,3),(41,4),(45,15),(22,17),(19,36)]),
        'root_stone':((40,32),[(2,28),(3,14),(12,4),(29,6),(37,16),(34,28)]),
        'paving':((48,24),[(2,12),(13,3),(32,4),(45,13),(33,21),(11,20)]),
    }
    for name,(size,points) in outlines.items():
        image=stone_texture(size,texture,points);d=ImageDraw.Draw(image)
        d.line(points+[points[0]],fill='#4a5a4c')
        d.line([(points[1][0],points[1][1]+1),points[2],points[3]],fill='#c8c5a6')
        w,h=size
        # Broken flowing arcs are ornament, not readable invented scripture.
        d.arc((w//2-9,h//2-7,w//2+9,h//2+7),195,330,fill='#697d6a',width=2)
        d.arc((w//2-7,h//2-5,w//2+7,h//2+5),195,315,fill='#b4bca0',width=1)
        d.line([(w//2,h//2+5),(w//2-1,h-7)],fill='#768a72')
        d.line([(w//2,h//2+3),(w//2+7,h//2)],fill='#768a72')
        # Small grass/root traces emerge along the buried edge.
        d.line([(6,h-4),(11,h-6),(16,h-3),(22,h-5)],fill='#367454')
        d.line([(15,h-4),(18,h-9),(20,h-6)],fill='#55956c')
        result[name]=image
    for name,broken in (('arc',False),('broken_arc',True)):
        image=Image.new('RGBA',(72,40));mask=Image.new('L',image.size);md=ImageDraw.Draw(mask)
        md.arc((2,1,69,47),195,345,fill=255,width=9)
        if broken:
            md.polygon([(33,4),(41,5),(42,17),(33,18)],fill=0)
            md.polygon([(2,13),(10,12),(12,23),(1,24)],fill=0)
        for y in range(0,40,texture.height):
            for x in range(0,72,texture.width):image.alpha_composite(texture,(x,y))
        image.putalpha(mask);image.paste((0,0,0,0),mask=ImageChops.invert(mask))
        d=ImageDraw.Draw(image)
        # Carve only within stone alpha, so empty gaps remain transparent.
        carving=Image.new('RGBA',image.size);cd=ImageDraw.Draw(carving)
        cd.arc((4,4,67,44),200,340,fill='#c4c7aa',width=1)
        cd.arc((9,8,62,39),200,340,fill='#627b66',width=1)
        carving.putalpha(ImageChops.multiply(carving.getchannel('A'),mask))
        image.alpha_composite(carving)
        result[name]=image
    return result


def memorial(texture):
    modules={}
    marker=stone_texture((24,36),texture,[(4,32),(4,13),(8,4),(15,3),(20,11),(20,32)])
    d=ImageDraw.Draw(marker)
    d.line([(5,12),(9,5),(15,4),(19,11)],fill='#c5c7a9')
    d.arc((7,10,17,21),190,350,fill='#5d7b69',width=2)
    d.line([(12,18),(12,27),(8,24)],fill='#5d7b69')
    d.line([(12,24),(16,21)],fill='#5d7b69')
    d.line([(3,32),(10,30),(17,32),(22,30)],fill='#3f7c59')
    modules['marker']=marker
    lamp=Image.new('RGBA',(24,40));d=ImageDraw.Draw(lamp)
    d.polygon([(5,37),(6,32),(9,30),(9,19),(6,16),(6,9),(12,4),(18,9),(18,16),(15,19),(15,30),(18,32),(19,37)],fill='#43564e',outline='#293d37')
    d.polygon([(8,10),(12,6),(16,10),(15,16),(9,16)],fill='#edcf8b')
    d.polygon([(11,10),(13,9),(14,14),(11,16)],fill='#fff0be')
    d.line([(12,7),(12,16)],fill='#a99a6b')
    d.line([(6,33),(18,33)],fill='#b5ad8b',width=2)
    d.line([(7,37),(18,37)],fill='#c7bd93')
    modules['lamp']=lamp
    offering=Image.new('RGBA',(40,24));d=ImageDraw.Draw(offering)
    d.ellipse((3,11,36,22),fill='#5c5141',outline='#a09368',width=2)
    d.line([(5,16),(34,16)],fill='#7b684b')
    for x,y in ((10,11),(19,9),(28,12)):
        d.line([(x,y+5),(x+1,y-1)],fill='#468259',width=2)
        for px,py in ((x-2,y),(x+2,y),(x,y-2),(x,y+2)):
            d.rectangle((px,py,px+1,py+1),fill='#d8d4e4' if x!=19 else '#dbba77')
        d.point((x,y),fill='#f4ecbd')
    modules['offering']=offering
    return modules


def products():
    recipe=json.loads(SOURCE.read_text());stone=recipe['limestone'];source=ROOT/stone['source']
    if sha256(source.read_bytes()).hexdigest()!=stone['sha256']:
        raise ValueError('Sanctuary limestone source changed')
    for record in recipe['review_sources']:
        if sha256((ROOT/record['path']).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Sanctuary review reference changed: '+record['path'])
    texture=Image.open(source).convert('RGBA').crop(tuple(stone['crop']))
    # The ridge reference includes yellow-green moss. Preserve its native
    # pixel structure while moving mineral bases into a quiet limestone ramp.
    ramp=[tuple(bytes.fromhex(color[1:])) for color in stone['ramp']]
    texture.putdata([(*ramp[min(len(ramp)-1,int((r*.2126+g*.7152+b*.0722)/256*len(ramp)))],255)
                     for r,g,b,_ in texture.get_flattened_data()])
    output={};modules={};previews={}
    def export(identifier,images,anchor,footprints=(),kind='decoration'):
        paths=[]
        for index,image in enumerate(images):
            path=OUTPUT/identifier.replace('.','/')/f'frame_{index:02}.png'
            output[path]=png(image);paths.append(path.relative_to(ROOT).as_posix())
        modules[identifier]={'frames':paths,'size':list(images[0].size),'anchor':list(anchor),
            'footprints':[list(rect) for rect in footprints],
            'frame_duration_ms':recipe['frame_duration_ms'] if len(images)>1 else 1000,
            'kind':kind,'fixed_root_rows':5 if kind=='crystal' else 0}
        previews[identifier]=images[0]
    for shape,spec in recipe['shapes'].items():
        for name,palette in recipe['palettes'].items():
            images=[crystal(spec,palette,phase,texture) for phase in range(6)]
            export(f'crystal.{shape}.{name}',images,spec['anchor'],spec['footprints'],'crystal')
    for name,palette in recipe['palettes'].items():
        export('vein.'+name,[vein(palette,phase) for phase in range(6)],(24,28),kind='surface_vein')
    export('socket.small',[socket((40,20),texture)],(20,17),((5,13,30,6),),'socket')
    export('socket.wide',[socket((72,24),texture,True)],(36,21),((8,17,56,6),),'socket')
    for name,image in ruins(texture).items():
        footprints=[] if name in ('arc','broken_arc','paving') else [[4,image.height-9,image.width-8,7]]
        export('ruins.'+name,[image],(image.width//2,image.height-4),footprints,'buried_masonry')
    for name,image in memorial(texture).items():
        export('memorial.'+name,[image],(image.width//2,image.height-3),
               () if name=='offering' else ((4,image.height-8,image.width-8,6),),'memorial')
    manifest={'version':1,'id':recipe['id'],'tile_size':24,'modules':modules,
        'palettes':recipe['palettes'],'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
        'source_recipe_sha256':sha256(SOURCE.read_bytes()).hexdigest(),
        'source_assets':[{'path':stone['source'],'sha256':stone['sha256']},*recipe['review_sources']],
        'notes':recipe['notes']}
    output[OUTPUT/'assets.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    fontpath=ROOT/'assets/ui/fonts/DejaVuSans.ttf'
    font=ImageFont.truetype(str(fontpath),16);small=ImageFont.truetype(str(fontpath),13)
    board=Image.new('RGB',(1240,990),'#173f31');d=ImageDraw.Draw(board)
    d.text((20,14),'Sanctuary crystals / authored native modules / Caelan 34px',font=font,fill='#e3e9d9')
    # Historical scale references retain the original approved figure.
    hero=Image.open(ROOT/'assets/source/characters/caelan/overworld_refresh/legacy/idle_front.png').convert('RGBA')
    shapes=list(recipe['shapes']);colors=list(recipe['palettes'])
    for row,name in enumerate(colors):
        yy=65+row*190
        d.text((20,yy-22),name.title(),font=font,fill=recipe['palettes'][name]['bright'])
        for col,shape in enumerate(shapes):
            image=previews[f'crystal.{shape}.{name}'];baseline=yy+145
            # All assets use the same scale with roots on one ground line.
            enlarged=image.resize((image.width,image.height),Image.Resampling.NEAREST)
            x=48+col*190
            board.paste(enlarged,(x,baseline-recipe['shapes'][shape]['anchor'][1]),enlarged)
            board.paste(hero,(x-28,baseline-34),hero)
            d.line((x-34,baseline+3,x+130,baseline+3),fill='#3d6b53')
            d.text((x-15,baseline+12),shape.replace('_',' '),font=small,fill='#c3d4ce')
    yy=835
    for index,(name,image) in enumerate((item for item in previews.items() if not item[0].startswith('crystal.'))):
        x=20+(index%10)*120;y=yy+(index//10)*85
        board.paste(image,(x,y),image)
        d.text((x,y+54),name.replace('memorial.','').replace('ruins.',''),font=small,fill='#c3d4ce')
    output[OUTPUT/'materials_review.png']=png(board)
    return output


def build(check=False):
    output=products()
    for path,body in output.items():
        if check:
            if not path.exists() or path.read_bytes()!=body:raise ValueError('Stale Sanctuary crystal asset: '+str(path.relative_to(ROOT)))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    print(('Verified' if check else 'Built')+' native Sanctuary crystal, stone and remembrance modules')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
