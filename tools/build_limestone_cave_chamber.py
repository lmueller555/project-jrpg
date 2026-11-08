"""Compile one isolated cave material review room from reusable pixel modules.

The authoritative recipe owns room geometry and all placements. Production
Sanctuary maps remain read-only; this chamber uses the ordinary world renderer
and pulsing cave lighting at native character scale.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/limestone_cave_review/recipe.json'
OUTPUT = ROOT/'assets/maps/limestone_cave_review'
TILE = 24
COLORS = {'cyan':[94,201,215], 'amethyst':[163,117,218],
          'opal':[197,221,216], 'amber':[223,172,92]}


def encoded(image):
    stream = BytesIO(); image.save(stream, format='PNG'); return stream.getvalue()


def products():
    spec = json.loads(SOURCE.read_text())
    used = {SOURCE}
    output = {}

    def read(path):
        path = ROOT/path; used.add(path)
        return json.loads(path.read_text())

    def opened(path):
        path = ROOT/path; used.add(path)
        with Image.open(path) as image:return image.convert('RGBA')

    def emit(name, image):
        path = (OUTPUT/name).relative_to(ROOT).as_posix()
        output[path] = encoded(image)
        return path

    pack = read(spec['asset_manifest'])
    crystals = read(spec['crystal_manifest'])
    width, height = (n*TILE for n in spec['size_tiles'])
    rng = random.Random(spec['seed'])
    materials = {name:[opened(path) for path in record['tiles']]
                 for name,record in pack['materials'].items()}
    if any(image.size != (TILE,TILE) for images in materials.values() for image in images):
        raise ValueError('Limestone review uses native 24 pixel floor modules')

    def material(name):
        images = materials[name]; result = Image.new('RGBA',(width,height))
        for y in range(0,height,TILE):
            for x in range(0,width,TILE):
                index = (x//TILE*137+y//TILE*271+spec['seed'])%len(images)
                result.alpha_composite(images[index],(x,y))
        return result

    floor = Image.new('L',(width,height));fd=ImageDraw.Draw(floor)
    fd.polygon([tuple(point) for point in spec['floor_outline']],fill=255)
    ground = material(spec['materials']['base'])
    # Soft coverage chooses hard native pixels; the material itself is never
    # blurred or scaled, preserving its stone chips and clustered highlights.
    bayer = ((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
    for patch in spec['materials']['patches']:
        mask = Image.new('L',(width,height));ImageDraw.Draw(mask).polygon(
            [tuple(point) for point in patch['polygon']],fill=255)
        cover = mask.filter(ImageFilter.BoxBlur(spec['materials']['blend_radius']))
        mask.putdata([255 if cover.getpixel((x,y))>(bayer[(y//2)%4][(x//2)%4]+.5)*16 else 0
                      for y in range(height) for x in range(width)])
        ground.paste(material(patch['material']),(0,0),mask)

    # The dark surrounding mass is the same native material at reduced value.
    rock_mass = material('dry').convert('RGB').point(lambda value:round(value*.38)).convert('RGBA')
    rock_mass.paste(ground,(0,0),floor);ground=rock_mass
    modules = pack['modules'];entities=[];solids=[]

    def module(name):
        record=modules[name];return record,opened(record['frames'][0])

    for item in spec['geology_patches']:
        record,image=module(item['module']);ground.alpha_composite(image,tuple(item['position']))

    # Sample long geological faces without resizing. Each native 72-pixel
    # profile follows the curved floor edge and stays outside traversable floor.
    faces=[module(f'wall.front.{index}')[1] for index in range(6)]
    fp=floor.load();gp=ground.load()
    for x in range(width):
        edges=[y for y in range(1,height) if fp[x,y] and not fp[x,y-1]]
        for bottom in edges:
            face=faces[(x//96)%len(faces)];fx=x%face.width
            for y in range(max(0,bottom-64),bottom):
                if fp[x,y]:continue
                pixel=face.getpixel((fx,y-bottom+64))
                if pixel[3]:gp[x,y]=pixel

    # Wall foot shadows stay narrow. Open ground remains visibly walkable.
    inner=ImageChops.subtract(floor,floor.filter(ImageFilter.MinFilter(5)))
    ground.paste((61,65,57,255),(0,0,width,height),inner)
    pool=spec['pool'];water=Image.new('L',(width,height));wd=ImageDraw.Draw(water)
    wd.polygon([tuple(p) for p in pool['outline']],fill=255)
    outer=ImageChops.subtract(water.filter(ImageFilter.MaxFilter(13)),water)
    wet_rim=ImageChops.subtract(water.filter(ImageFilter.MaxFilter(5)),water)
    ground.paste(material('damp'),(0,0),outer)
    ground.paste((147,153,127,255),(0,0,width,height),wet_rim)
    ground.paste((62,100,105,255),(0,0,width,height),water)
    gd=ImageDraw.Draw(ground)
    gd.polygon([tuple(p) for p in pool['deep']],fill=(39,69,78,255))
    for index in range(46):
        x=rng.randrange(505,706);y=rng.randrange(289,412)
        if water.getpixel((x,y)):
            gd.line((x,y,x+rng.randrange(2,8),y),fill=rng.choice(('#446f77','#4b7a7e','#638f8a')))
    collision=ImageChops.lighter(ImageChops.invert(floor),water)

    def entity(identifier,record,image,feet,**extra):
        used.update(ROOT/path for path in record['frames'])
        anchor=record.get('anchor',[image.width//2,image.height-3])
        position=[round(feet[0]-anchor[0]),round(feet[1]-anchor[1])]
        result={'id':identifier,'position':position,'sort_y':round(feet[1]),
                'sort_priority':0,'frames':record['frames'],'frame_duration_ms':700,
                'phase_offset':0,'reduced_motion_frame':0,**extra}
        entities.append(result)
        return result,position

    for item in spec['wall_details']:
        record,image=module(item['module']);rec,_=entity(item['id'],record,image,item['position'],source_module=item['module'])
        rec['sort_y']=item['position'][1]-12
    for item in spec['formations']:
        record,image=module(item['module']);rec,position=entity(item['id'],record,image,item['position'],source_module=item['module'])
        if item.get('foreground'):rec['sort_y']=height+10
        else:
            footprints=record.get('footprints',[])
            for i,rect in enumerate(footprints):
                x,y,w,h=rect;x+=position[0];y+=position[1]
                ImageDraw.Draw(collision).rectangle((x,y,x+w-1,y+h-1),fill=255)
                solids.append({'id':item['id']+':'+str(i),'position':[x+w//2,y+h//2]})
            rec['footprints']=[[r[0]+position[0],r[1]+position[1],*r[2:]] for r in footprints]

    record,image=module(spec['tunnel']['module'])
    rec,_=entity('natural_tunnel',record,image,spec['tunnel']['position'],source_module=spec['tunnel']['module'])
    rec['sort_y']=spec['tunnel']['position'][1]-10
    paving=opened(spec['keeper_paving']['image'])
    for pos in spec['keeper_paving']['positions']:ground.alpha_composite(paving,tuple(pos))
    lights=[]
    for index,item in enumerate(spec['crystals']):
        record=crystals['modules'][item['module']];image=opened(record['frames'][0])
        rec,pos=entity(item['id'],record,image,item['position'],light_index=index,source_module=item['module'])
        color=item['module'].split('.')[-1]
        lights.append({'position':item['light_position'],'color':COLORS[color],
                       'radius':item['radius'],'phase':item['phase'],'entity_id':item['id']})
        x,y=item['position'];ImageDraw.Draw(collision).rectangle((x-8,y-3,x+8,y+3),fill=255)
        rec['footprints']=[[x-8,y-3,17,7]]
        if index in (1,3,5):
            vein=crystals['modules']['vein.'+color];vi=opened(vein['frames'][0])
            entity('inset_vein_'+str(index),vein,vi,[x+38,y-5],light_index=index,source_module='vein.'+color)
    # A faint steady entrance wash relates the warm stone to the exterior.
    lights.append({'position':[240,532],'color':[201,195,157],'radius':150,'steady':True})

    # Water reflects the mineral palette in broken horizontal ribbons. These
    # animate independently of the pulse while retaining a fixed shoreline.
    cx,cy=pool['center'];rx,ry=pool['radii'];water_frames=[]
    water_box=(cx-rx-3,cy-ry-3,cx+rx+4,cy+ry+4)
    local=water.crop(water_box)
    for phase in range(6):
        reflection=Image.new('RGBA',local.size);rd=ImageDraw.Draw(reflection)
        for line in range(18):
            yy=7+(line*9+phase*2)%(local.height-14)
            xx=local.width//2+round(math.sin(line*1.7+phase*.13)*local.width*.31)
            rd.line((xx-6,yy,xx+4+(line%3)*3,yy),fill=(137,192,180,45+(line%4)*14))
        for line in range(11):
            yy=16+line*7;xx=55+round(math.sin(line*1.4+phase*.5)*5)
            rd.line((xx-5+line//3,yy,xx+7+line//3,yy),fill=(170,147,209,85-line*4))
        reflection.putalpha(ImageChops.multiply(reflection.getchannel('A'),local))
        water_frames.append(emit(f'water/frame_{phase:02}.png',reflection))
    entities.append({'id':'pool_reflection','position':list(water_box[:2]),
                     'sort_y':-1,'sort_priority':0,'frames':water_frames,
                     'frame_duration_ms':700,'phase_offset':0,'reduced_motion_frame':2})
    emit('ground.png',ground.convert('RGB'))
    emit('collision.png',collision.convert('RGB'))
    overview=ground.copy()
    for rec in sorted(entities,key=lambda rec:(rec['sort_y'],rec['sort_priority'])):
        path=rec['frames'][0]
        image=(Image.open(BytesIO(output[path])).convert('RGBA') if path in output else opened(path))
        overview.alpha_composite(image,tuple(rec['position']))
    emit('overview.png',overview.convert('RGB'))
    checks={'solid_points':[{'id':'outer_rock','position':[30,30]},
                            {'id':'deep_pool','position':pool['center']},*solids],
            'light_station':spec['review_points']['dry_limestone'],
            'depth_cases':spec['review_checks']['depth_cases']}
    data={'id':spec['id'],'name':spec['name'],'kind':'cave_review','tile_size':TILE,
          'size_pixels':[width,height],'size_tiles':spec['size_tiles'],
          'player_probe_size':[24,12],'player_draw_anchor':[12,30],'spawn':spec['spawn'],
          'ground_frames':[(OUTPUT/'ground.png').relative_to(ROOT).as_posix()],
          'ground_frame_duration_ms':700,'collision':(OUTPUT/'collision.png').relative_to(ROOT).as_posix(),
          'overview':(OUTPUT/'overview.png').relative_to(ROOT).as_posix(),
          'entities':entities,'foreground':[],'doors':[],'npcs':[],
          'landmarks':spec['landmarks'],
          'cave':{'ambient':[112,119,127],'lights':lights,'pulse_period_ms':6000,
                  'review_points':spec['review_points'],'routes':spec['routes'],
                  'review_checks':checks,'treasures':[],'links':[]},
          'build':{'tool':'tools/build_limestone_cave_chamber.py',
                   'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
                   'source_sha256':{str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest()
                                    for path in sorted(used)}}}
    output[(OUTPUT/'map.json').relative_to(ROOT).as_posix()]=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');args=parser.parse_args()
    changed=[];result=products()
    for name,raw in result.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            changed.append(name)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if args.check and changed:raise SystemExit('Stale review chamber: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(result)} limestone chamber exports')


if __name__=='__main__':main()
