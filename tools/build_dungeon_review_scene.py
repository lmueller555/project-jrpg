"""Compile an isolated connected review route using the expanded dungeon pack.

Every material and placed object comes from the retained asset manifests. The
source recipe owns geometry, physical footprints, review stations and routes;
production maps and controllers are never written by this tool.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/maps/dungeon_pack_review/recipe.json'
OUTPUT=ROOT/'assets/maps/dungeon_pack_review'


def encoded(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def products():
    spec=json.loads(SOURCE.read_text());used={SOURCE};out={}
    def read(name):
        path=ROOT/name;used.add(path);return json.loads(path.read_text())
    def opened(name):
        path=ROOT/name;used.add(path)
        with Image.open(path) as image:return image.convert('RGBA')
    def emit(name,image):
        path=(OUTPUT/name).relative_to(ROOT).as_posix();out[path]=encoded(image);return path
    packs={name:read(path) for name,path in spec['manifests'].items()}
    w,h=(value*24 for value in spec['size_tiles'])
    materials={name:[opened(path) for path in record['tiles']]
               for name,record in packs['base']['materials'].items()}
    def material(name):
        result=Image.new('RGBA',(w,h));tiles=materials[name]
        for y in range(0,h,24):
            for x in range(0,w,24):
                result.alpha_composite(tiles[(x//24*137+y//24*271+spec['seed'])%len(tiles)],(x,y))
        return result
    floor=Image.new('L',(w,h));fd=ImageDraw.Draw(floor)
    for polygon in spec['rooms']:fd.polygon([tuple(point) for point in polygon],fill=255)
    for route in spec.get('corridors',[]):
        fd.line([tuple(p) for p in route['points']],fill=255,width=route['width'])
        radius=route['width']//2
        for x,y in route['points']:fd.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
    ground=material('dry');bayer=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
    for patch in spec['material_patches']:
        mask=Image.new('L',(w,h));ImageDraw.Draw(mask).polygon([tuple(p) for p in patch['polygon']],fill=255)
        cover=mask.filter(ImageFilter.BoxBlur(10))
        mask.putdata([255 if cover.getpixel((x,y))>(bayer[(y//2)%4][(x//2)%4]+.5)*16 else 0
                      for y in range(h) for x in range(w)])
        ground.paste(material(patch['material']),(0,0),mask)
    surrounding=material('dry').convert('RGB').point(lambda v:round(v*.35)).convert('RGBA')
    surrounding.paste(ground,(0,0),floor);ground=surrounding
    # Ordinary front profiles follow every northern wall contour, at native
    # pixel density. The directional modules below make the side/rear samples.
    faces=[opened(packs['base']['modules'][f'wall.front.{i}']['frames'][0]) for i in range(6)]
    fp=floor.load();gp=ground.load()
    for x in range(w):
        for bottom in [y for y in range(1,h) if fp[x,y] and not fp[x,y-1]]:
            face=faces[x//96%6]
            for yy in range(max(0,bottom-64),bottom):
                if fp[x,yy]:continue
                pixel=face.getpixel((x%96,yy-bottom+64))
                if pixel[3]:gp[x,yy]=pixel
    lip=ImageChops.subtract(floor,floor.filter(ImageFilter.MinFilter(5)))
    ground.paste((61,65,57,255),(0,0,w,h),lip)
    collision=ImageChops.invert(floor);water_mask=Image.new('L',(w,h))
    entities=[];solids=[];placed=[];water_records=[]
    def module(pack,name):
        record=packs[pack]['modules'][name]
        images=[opened(path) for path in record['frames']]
        return record,images
    def add_entity(identifier,record,images,position,sort_y,**extra):
        rec={'id':identifier,'position':list(position),'frames':record['frames'],
             'sort_y':sort_y,'sort_priority':0,'frame_duration_ms':record.get('frame_duration_ms',700),
             'phase_offset':0,'reduced_motion_frame':record.get('reduced_motion_frame',0),**extra}
        entities.append(rec);return rec
    def physical(identifier,record,position,enabled=True):
        rects=[]
        if enabled:
            for local in record.get('footprints',[]):
                x,y,ww,hh=local;x+=position[0];y+=position[1]
                ImageDraw.Draw(collision).rectangle((x,y,x+ww-1,y+hh-1),fill=255)
                rects.append([x,y,ww,hh]);solids.append({'id':identifier+':'+str(len(rects)), 'position':[x+ww//2,y+hh//2]})
        return rects
    def water_collision(record,position):
        for x,y,ww,hh in record.get('water_regions',[]):
            ImageDraw.Draw(water_mask).rectangle((x+position[0],y+position[1],x+position[0]+ww-1,y+position[1]+hh-1),fill=255)
    # Connected pool tiles use actual bank masks, including diagonal joins.
    cells={tuple(point) for point in spec['pool_cells']}
    for index,(x,y) in enumerate(sorted(cells,key=lambda p:(p[1],p[0]))):
        n,e,s,west=(x,y-1) not in cells,(x+1,y) not in cells,(x,y+1) not in cells,(x-1,y) not in cells
        if n and e:key='bank.outer_ne.0'
        elif e and s:key='bank.outer_se.0'
        elif s and west:key='bank.outer_sw.0'
        elif west and n:key='bank.outer_nw.0'
        elif n:key='bank.north.0'
        elif e:key='bank.east.0'
        elif s:key='bank.south.0'
        elif west:key='bank.west.0'
        elif (x+1,y-1) not in cells:key='bank.inner_ne.0'
        elif (x+1,y+1) not in cells:key='bank.inner_se.0'
        elif (x-1,y+1) not in cells:key='bank.inner_sw.0'
        elif (x-1,y-1) not in cells:key='bank.inner_nw.0'
        else:key='water.deep.'+str((x*17+y*31+x*y*7)%3)
        record,images=module('water',key);position=[x*24,y*24]
        ground.alpha_composite(images[0],tuple(position))
        add_entity('pool_tile_'+str(index),record,images,position,-100,
                   source_module=key,source_pack='water',water=True,
                   phase_offset=(x*7+y*11)%6)
        water_collision(record,position)
        water_records.append({'entity_id':'pool_tile_'+str(index),'module':key,'position':position})
    for item in spec['placements']:
        record,images=module(item['pack'],item['module']);anchor=record['anchor'];feet=item['position']
        position=[feet[0]-anchor[0],feet[1]-anchor[1]]
        ground_piece=item.get('ground') or item['module'].startswith(('ramp.','steps.','shelf.'))
        if ground_piece:
            ground.alpha_composite(images[0],tuple(position))
        else:
            rec=add_entity(item['id'],record,images,position,feet[1],
                           source_module=item['module'],source_pack=item['pack'])
            rec['footprints']=physical(item['id'],record,position,item.get('collision',True))
        if ground_piece:
            physical(item['id'],record,position,item.get('collision',True))
            if item['module'].startswith('shelf.'):
                # Shelf top is walkable ground. Its actual lower lip retains
                # foreground occlusion independently of the top material.
                face=Image.new('RGBA',images[0].size)
                cutoff=images[0].height-24
                face.alpha_composite(images[0].crop((0,cutoff,face.width,face.height)),(0,cutoff))
                path=emit('props/'+item['id']+'_lip.png',face)
                add_entity(item['id']+'_lip',{'frames':[path]},[face],position,feet[1])
        if item.get('water_collision'):water_collision(record,position)
        placed.append({'id':item['id'],'pack':item['pack'],'module':item['module'],
                       'position':position,'feet':feet,'ground':bool(ground_piece)})
    collision=ImageChops.lighter(collision,water_mask)
    lights=[];gem_records=[]
    def first_floor(x):return next((y for y in range(h) if floor.getpixel((x,y))),h)
    for i,item in enumerate(spec['microcrystals']):
        record,images=module('micro',item['module']);ax,ay=record['anchor'];cx,cy=item['position']
        ex,ey,ew,eh=record['emission_bounds']
        if record.get('pattern')=='vertical':
            occupied=[]
            for yy in range(max(0,cy-ay+ey),min(h,cy-ay+ey+eh)):
                occupied.append(max((xx for xx in range(w) if floor.getpixel((xx,yy))),default=0))
            cx=max(cx,max(occupied)+4+ax-ex)
            cx=min(cx,w-(ex+ew-ax)-1)
        else:
            borders=[first_floor(xx) for xx in range(max(0,cx-ax+ex),min(w,cx-ax+ex+ew))]
            cy=min(cy,min(borders)-(ey+eh-ay)-3)
        position=[round(cx-ax),round(cy-ay)]
        # Every individual facet is in real rock; no unseen ground obstruction
        # can stand in for a wall-embedded crystal.
        for gx,gy,gw,gh in record['core_components']:
            for xx in range(position[0]+gx,position[0]+gx+gw):
                for yy in range(position[1]+gy,position[1]+gy+gh):
                    if not(0<=xx<w and 0<=yy<h) or floor.getpixel((xx,yy)):
                        raise ValueError('Microcrystal projects onto the walking floor: '+item['id'])
        source_pos=item['light_position']
        if collision.getpixel(tuple(source_pos)):
            candidates=[(source_pos[0]+dx,source_pos[1]+dy) for r in range(1,65) for dx,dy in ((r,0),(-r,0),(0,r),(0,-r))]
            source_pos=list(next((p for p in candidates if 0<=p[0]<w and 0<=p[1]<h and not collision.getpixel(p)),source_pos))
        if collision.getpixel(tuple(source_pos)):raise ValueError('Blocked light root: '+item['id'])
        add_entity(item['id'],record,images,position,cy,source_module=item['module'],source_pack='micro',light_index=len(lights),wall_gem_color=item['color'])
        lights.append({'position':source_pos,'color':record['color'],'radius':170,
                       'phase':i*.12,'gain':.48 if item['color']!='white' else .32,'entity_id':item['id']})
        gem_records.append({'id':item['id'],'entity_id':item['id'],'color':item['color'],
                            'position':[cx,cy],'light_position':source_pos,
                            'crystal_count':record['crystal_count'],'crystal_sizes':record['crystal_sizes'],
                            'emission_bounds':[position[0]+ex,position[1]+ey,ew,eh]})
    lights.append({'position':[232,645],'color':[190,185,145],'radius':180,'steady':True,'gain':.5})
    emit('ground.png',ground.convert('RGB'));emit('collision.png',collision.convert('RGB'));emit('water_mask.png',water_mask.convert('RGB'))
    overview=ground.copy()
    for rec in sorted(entities,key=lambda r:(r['sort_y'],r.get('sort_priority',0))):
        raw=out.get(rec['frames'][0]);image=Image.open(BytesIO(raw)).convert('RGBA') if raw else opened(rec['frames'][0])
        overview.alpha_composite(image,tuple(rec['position']))
    emit('overview.png',overview.convert('RGB'))
    checks=dict(spec['review_checks']);checks['solid_points']=checks['solid_points']+solids
    checks['depth_cases']=[{'id':'wall_column','feet':[267,370],'hidden_pixel':[264,358],
                            'visible_feet':[267,430],'visible_pixel':[264,418]}]
    data={'id':spec['id'],'name':spec['name'],'kind':'dungeon_pack_review','tile_size':24,
          'size_tiles':spec['size_tiles'],'size_pixels':[w,h],'player_probe_size':[24,12],
          'player_draw_anchor':[12,30],'spawn':spec['spawn'],'ground_frames':[(OUTPUT/'ground.png').relative_to(ROOT).as_posix()],
          'ground_frame_duration_ms':700,'collision':(OUTPUT/'collision.png').relative_to(ROOT).as_posix(),
          'overview':(OUTPUT/'overview.png').relative_to(ROOT).as_posix(),'entities':entities,'foreground':[],
          'doors':[],'npcs':[],'landmarks':spec['landmarks'],
          'cave':{'ambient':[112,119,127],'lights':lights,'pulse_period_ms':6000,'wall_gems':gem_records,
                  'microcrystal_count':sum(item['crystal_count'] for item in gem_records),
                  'review_points':spec['review_points'],'routes':spec['routes'],'review_checks':checks,
                  'placed_modules':placed,'water_tiles':water_records,'treasures':[],'links':[]},
          'build':{'tool':'tools/build_dungeon_review_scene.py','source_recipe':SOURCE.relative_to(ROOT).as_posix(),
                   'source_sha256':{str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest() for path in sorted(used)}}}
    # Catch authored endpoints before handing the scene to the movement review.
    for name,point in spec['review_points'].items():
        x,y=(round(value) for value in point)
        if collision.crop((x-12,y-6,x+12,y+6)).getbbox():
            raise ValueError('Blocked full-foot review station '+name+': '+str(point))
    out[(OUTPUT/'map.json').relative_to(ROOT).as_posix()]=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    return out


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    result=products();changed=[]
    for name,raw in result.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            changed.append(name)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if args.check and changed:raise SystemExit('Stale dungeon review exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(result)} dungeon review exports')
    return 0


if __name__=='__main__':raise SystemExit(main())
