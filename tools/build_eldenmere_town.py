"""Compose the approved village plan from native approved environment assets."""
from array import array
from collections import deque
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from random import Random
from PIL import Image, ImageChops, ImageDraw, ImageFont

from build_eldenmere_stream import read_json, write_json, enlarged, composite_tile, surface_variant
from build_eldenmere_terrain import BITS, OFFSETS, normalize_mask
from build_eldenmere_blockout import geometry, cells
from build_eldenmere_gate import channel_assets, channel_response, spillway_response
from build_eldenmere_watermill import race_assets
from build_eldenmere_bridge import clip_to_water

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/maps/eldenmere/terrain_foundation'
OUTPUT=ROOT/'assets/maps/eldenmere/terrain_foundation'
TERRAIN=ROOT/'assets/terrain/eldenmere'
TILE=24
FONT_DIR=Path('/usr/share/fonts/truetype/dejavu')


@lru_cache(None)
def opened(path):
    with Image.open(path) as im:
        return im.convert('RGBA')


def font(size,bold=False):
    return ImageFont.truetype(str(FONT_DIR/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)


def box(rect):
    x,y,w,h=rect;return x,y,x+w,y+h


def pixel_rect(rect):
    return [n*24 for n in rect]


def adapted_plan(recipe):
    plan=deepcopy(read_json(ROOT/recipe['approved_layout']))
    plan['stream_centres']=[[0,10,35],[11,17,34],[18,29,35],[30,43,34],[44,55,35]]
    next(r for r in plan['water_branches'] if r['id']=='mill_race')['points']=recipe['mill_race_points']
    next(r for r in plan['crossings'] if r['id']=='mill_landing')['rect']=[39,14,2,1]
    next(r for r in plan['stairs'] if r['id']=='eastern_steps').update(rect=[48,35,2,2],orientation='north-south')
    next(r for r in plan['roads'] if r['id']=='venn_access')['points']=[[39,38],[49,38],[49,34],[59,34],[59,26]]
    next(r for r in plan['roads'] if r['id']=='venn_door')['points']=[[52,30],[52,34]]
    next(r for r in plan['buildings'] if r['id']=='venn')['door']=[52,30]
    return plan


def ground(plan,geo):
    gm=read_json(TERRAIN/'grass_dirt/tileset.json')
    grass=[opened(TERRAIN/'grass_dirt'/p) for p in gm['grass']['images']]
    dirt={r['mask']:opened(TERRAIN/'grass_dirt'/r['image']) for r in gm['tiles']}
    fills=[opened(TERRAIN/'grass_dirt'/p) for p in gm['dirt_interiors']['images']]
    width,height=plan['size_tiles'];size=(width*24,height*24)
    base=Image.new('RGBA',size)
    grass_ids=[];rng=Random(706)
    for y in range(height):
        row=[]
        for x in range(width):
            variant=rng.choices(range(4),weights=(5,3,2,1))[0]
            row.append(variant);base.paste(grass[variant],(x*24,y*24))
        grass_ids.append(row)
    dirt_cells=set(geo['roads'])
    for space in plan['spaces']:
        if space['kind'] in ('yard','plots','garden'):
            dirt_cells.update(cells(space['rect']))
    dirt_cells-=geo['water']|geo['buildings']
    layer=Image.new('RGBA',size);masks=[]
    for x,y in sorted(dirt_cells):
        raw=sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in dirt_cells)
        mask=normalize_mask(raw)
        sprite=fills[(x+2*y)%3] if mask==255 else dirt[mask]
        layer.alpha_composite(sprite,(x*24,y*24));masks.append({'cell':[x,y],'mask':mask})
    base.save(OUTPUT/'layers/grass.png');layer.save(OUTPUT/'layers/paths.png')
    result=base.copy();result.alpha_composite(layer)
    return result,base,{'grass_variants':grass_ids,'dirt_cells':masks}


def masonry(plan,geo,size):
    layer=Image.new('RGBA',size);collision=Image.new('L',size)
    levels=geo['levels'];width,height=plan['size_tiles'];placements=[]
    def place(name,x,y,kind):
        sprite=opened(TERRAIN/'terraces/tiles'/f'{name}.png')
        pos=(x*24,y*24);layer.alpha_composite(sprite,pos)
        collision.paste(255,pos,sprite.getchannel('A'))
        placements.append({'tile':name,'position':list(pos),'kind':kind})
    for y in range(height):
        for x in range(width):
            level=levels[y][x]
            if y>0 and levels[y-1][x]>level:
                for tier in range(levels[y-1][x]-level):
                    if y+tier<height:
                        place(f'wall_front_{(x+tier)%3:02}',x,y+tier,'front')
            if y>0 and levels[y-1][x]<level:
                place('wall_back',x,y,'back')
            if x>0 and levels[y][x-1]<level:
                place('wall_side_left',x,y,'side')
            if x+1<width and levels[y][x+1]<level:
                place('wall_side_right',x,y,'side')
    stairs=[]
    stair=opened(TERRAIN/'terraces/stairs_south.png')
    for record in plan['stairs']:
        px,py,w,h=pixel_rect(record['rect'])
        # The full 48px prefab replaces masonry; its 34px central tread is walkable.
        layer.paste((0,0,0,0),(px,py,px+w,py+h))
        layer.alpha_composite(stair,(px,py))
        collision.paste(0,(px,py,px+w,py+h))
        collision.paste(255,(px,py,px+7,py+h));collision.paste(255,(px+41,py,px+w,py+h))
        stairs.append({**record,'image':'assets/terrain/eldenmere/terraces/stairs_south.png',
                       'position':[px,py],'walkable_rect':[px+7,py,34,48]})
    layer.save(OUTPUT/'layers/masonry.png')
    return layer,collision,placements,stairs


def channels(plan,geo):
    palette=read_json(TERRAIN/'gate/palette.json')['materials']
    records,tiles,masks=channel_assets()
    mr,mt,mm=race_assets(palette)
    records.update(mr);tiles.update(mt);masks.update(mm)
    placements=[]
    vectors={(0,-1):'N',(1,0):'E',(0,1):'S',(-1,0):'W'}
    bits={'N':1,'E':2,'S':4,'W':8}
    brook={(x+dx,y) for x,y,_ in geo['stream'] for dx in (-1,0,1)}
    for name,nodes in geo['branches'].items():
        receiver=next(i for i,node in enumerate(nodes) if i>0 and tuple(node[:2]) in brook)
        for i,node in enumerate(nodes[:receiver+1]):
            x,y,h=node
            previous=nodes[i-1] if i else [x,y-1,h]
            following=nodes[i+1] if i<receiver else None
            incoming=vectors[(previous[0]-x,previous[1]-y)]
            if following:
                outgoing=vectors[(following[0]-x,following[1]-y)]
                key=f'channel_{bits[incoming]+bits[outgoing]:02}_from_{incoming.lower()}'
            else:
                key='return_w'
            mode='receiver' if i==receiver else 'trickle' if name=='irrigation' and i>=next(j for j,n in enumerate(nodes) if n[:2]==[60,27]) else 'full'
            placements.append({'branch':name,'cell':[x,y],'route':key,'height':h,'mode':mode})
    # Every full drop is an approved 24x48 south-facing spillway, including two-tier headwater weirs.
    falls=[]
    for x in (34,35,36,43):
        for y in (6,8):
            falls.append({'position':[x*24,y*24],'mode':'full','branch':'brook' if x!=43 else 'mill_race'})
    falls.extend([{'position':[60*24,6*24],'mode':'full','branch':'irrigation'},
                  {'position':[60*24,36*24],'mode':'trickle','branch':'irrigation'}])
    return records,tiles,masks,palette,placements,falls


def stream_tiles(geo):
    meta=read_json(TERRAIN/'stream/tileset.json')
    masks={r['mask']:opened(TERRAIN/'stream'/meta['water_masks']).crop(box(r['rect'])) for r in meta['tiles']}
    banks={r['mask']:opened(TERRAIN/'stream'/meta['banks']).crop(box(r['rect'])) for r in meta['tiles']}
    wet=set()
    for x,y,_ in geo['stream']:
        wet.update((xx,y) for xx in range(x-1,x+2))
    placements=[]
    for x,y in sorted(wet):
        raw=sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in wet or (y+dy<0 and abs(x+dx-35)<=1) or (y+dy>=56 and abs(x+dx-35)<=1))
        placements.append({'cell':[x,y],'mask':normalize_mask(raw),'variant':surface_variant(x,y)})
    tiles={}
    for phase in range(6):
        for r in placements:
            key=(r['variant'],phase,r['mask'])
            if key not in tiles:
                surface=opened(TERRAIN/'stream/surface'/f"variant_{r['variant']:02}_frame_{phase+1:02}.png")
                tiles[key]=composite_tile(surface,banks[r['mask']],masks[r['mask']])
    return placements,tiles


def building_assets(recipe,plan):
    instances=[]
    for b in plan['buildings']:
        x,y,w,h=pixel_rect(b['rect'])
        if b['id'] in recipe['cottage_packs']:
            path=TERRAIN/recipe['cottage_packs'][b['id']]
            meta=read_json(path/'cottage.json');gx,gy,gw,gh=meta['ground_rect']
            if [gw,gh]!=[w,h]:raise ValueError(f"Footprint mismatch: {b['id']}")
            origin=[x-gx,y-gy];dx,dy=meta['door']['position'];dw,dh=meta['door']['size']
            frames=[]
            offset=len(instances)*3
            for tick in range(recipe['frame_count']):
                sprite=opened(path/'structure.png').copy()
                sprite.alpha_composite(opened(path/'doors/frame_01.png'))
                index=(tick+offset)%18+1
                sprite.alpha_composite(opened(path/'lantern'/f'frame_{index:02}.png'))
                sprite.alpha_composite(opened(path/'smoke'/f'frame_{index:02}.png'))
                frames.append(sprite)
            instances.append({**b,'pack':str(path.relative_to(ROOT)),'position':origin,
                              'ground_rect_pixels':[x,y,w,h],'prefab_size':meta['prefab_size'],
                              'door_centre':[origin[0]+dx+dw/2,origin[1]+dy+dh],
                              'sort_y':y+h,'frames':frames,'smoke_offset':offset%18,'placeholder':False})
        elif b['id']=='mill':
            path=TERRAIN/'watermill';meta=read_json(path/'mill.json');gx,gy,gw,gh=meta['building_ground_rect']
            origin=[x-gx,y-gy]
            instances.append({**b,'pack':str(path.relative_to(ROOT)),'position':origin,
                              'ground_rect_pixels':[x,y,w,h],'prefab_size':meta['prefab_size'],
                              'sort_y':y+h,'frames':[opened(path/f'running/frame_{p+1:02}.png') for p in range(6)],'placeholder':False})
        else:
            sprite=Image.new('RGBA',(w,h));d=ImageDraw.Draw(sprite);d.fontmode='1'
            d.rectangle((0,0,w-1,h-1),fill='#a8ad9b',outline='#667267',width=2)
            for xx in range(0,w,12):d.line((xx,2,min(w-1,xx+22),min(h-2,24)),fill='#919b88',width=1)
            title='SANCTUARY' if b['id']=='sanctuary' else "MIRA'S WORKSHOP"
            d.text((w/2,h/2-10),title,font=font(12 if w>=160 else 10,True),fill='#36473f',anchor='mm')
            d.text((w/2,h/2+11),'DESIGN PENDING',font=font(9),fill='#45584b',anchor='mm')
            instances.append({**b,'position':[x,y],'ground_rect_pixels':[x,y,w,h],
                              'prefab_size':[w,h],'sort_y':y+h,'frames':[sprite],'placeholder':True})
    return instances


def bridge_assets(plan):
    result=[];source=TERRAIN/'bridge';meta=read_json(source/'tileset.json')
    indices={name:i for i,name in enumerate(meta['assembly'])}
    for r in plan['crossings']:
        if r['kind']!='stream_bridge':continue
        x,y,w,h=r['rect'];names=['west']+['middle_a' if i%2==0 else 'middle_b' for i in range(w-2)]+['east']
        base=Image.new('RGBA',(w*24,72));front=base.copy();lamps=[];shadows=[];wakes=[]
        for i,name in enumerate(names):
            base.alpha_composite(opened(source/'modules'/name/'base.png'),(i*24,0))
            front.alpha_composite(opened(source/'modules'/name/'foreground.png'),(i*24,0))
        for phase in range(6):
            ll=Image.new('RGBA',base.size);ss=ll.copy();ww=ll.copy()
            for i,name in enumerate(names):
                left=indices[name]*24;crop=(left,0,left+24,72)
                ll.alpha_composite(opened(source/f'lanterns/frame_{phase+1:02}.png').crop(crop),(i*24,0))
                ss.alpha_composite(opened(source/'water_shadow.png').crop(crop),(i*24,0))
                ww.alpha_composite(opened(source/f'wakes/frame_{phase+1:02}.png').crop(crop),(i*24,0))
            lamps.append(ll);shadows.append(ss);wakes.append(ww)
        result.append({**r,'position':[x*24,y*24-12],'assembly':names,
                       'base':base,'foreground':front,'lamps':lamps,'shadows':shadows,'wakes':wakes})
    return result


def render_environment(tick,base,grass,masonry_layer,water_placements,water_tiles,channel_data,buildings,bridges):
    records,tiles,masks,palette,placements,falls=channel_data
    phase=tick%6;image=base.copy();image.alpha_composite(masonry_layer)
    for r in water_placements:
        x,y=r['cell'];image.alpha_composite(water_tiles[r['variant'],phase,r['mask']],(x*24,y*24))
    for r in placements:
        x,y=r['cell'];name=r['route'];sprite=tiles[name][phase]
        if r['mode']=='trickle':sprite=channel_response(sprite,masks[name],records[name],'trickle',phase,palette)
        image.alpha_composite(sprite,(x*24,y*24))
    for r in falls:
        x,y=r['position'];image.paste(grass.crop((x,y,x+24,y+48)),(x,y))
        sprite=opened(TERRAIN/'terraces/spillway'/f'frame_{phase+1:02}.png')
        if r['mode']=='trickle':sprite=spillway_response(sprite,'trickle',phase,palette)
        image.alpha_composite(sprite,(x,y))
    image.alpha_composite(opened(TERRAIN/'gate/animations/idle_jammed'/f'frame_{phase+1:02}.png'),(60*24,27*24-12))
    # Building ground baselines determine ordering; actors are added separately below.
    for instance in sorted(buildings,key=lambda r:r['sort_y']):
        frames=instance['frames'];image.alpha_composite(frames[tick%len(frames)],tuple(instance['position']))
    for bridge in bridges:
        pos=tuple(bridge['position'])
        for layer in ('shadows','wakes'):
            overlay=clip_to_water(bridge[layer][phase],image,pos,palette)
            image.alpha_composite(overlay,pos)
        image.alpha_composite(bridge['base'],pos);image.alpha_composite(bridge['lamps'][phase],pos)
    return image


def with_actor(environment,bridges,foot,facing='front'):
    image=environment.copy();hero=opened(ROOT/f'assets/characters/caelan/idle_{facing}.png')
    image.alpha_composite(hero,(foot[0]-12,foot[1]-30))
    for bridge in bridges:image.alpha_composite(bridge['foreground'],tuple(bridge['position']))
    return image.convert('RGB')


def navigation(plan,geo,wall_collision,buildings,bridges,recipe):
    size=wall_collision.size;blocked=wall_collision.copy();allowed=Image.new('L',size)
    for x,y in geo['water']:blocked.paste(255,(x*24,y*24,x*24+24,y*24+24))
    for b in buildings:blocked.paste(255,box(b['ground_rect_pixels']))
    for crossing in plan['crossings']:
        r=pixel_rect(crossing['rect']);blocked.paste(0,box(r))
    for x,y in geo['roads']:allowed.paste(255,(x*24,y*24,x*24+24,y*24+24))
    for space in plan['spaces']:
        if space['kind'] in ('commons','yard'):allowed.paste(255,box(pixel_rect(space['rect'])))
    w,h=size;stride=w+1;integral=array('I',[0])*((w+1)*(h+1));pixels=blocked.tobytes()
    for y in range(h):
        total=0;row=(y+1)*stride;previous=y*stride
        for x in range(w):
            total+=bool(pixels[y*w+x]);integral[row+x+1]=integral[previous+x+1]+total
    free=set()
    for y in range(6,h-5,2):
        for x in range(12,w-11,2):
            if not allowed.getpixel((x,y)):continue
            left,right=x-12,x+12;top,bottom=y-6,y+6
            count=integral[bottom*stride+right]-integral[top*stride+right]-integral[bottom*stride+left]+integral[top*stride+left]
            if not count:free.add((x,y))
    start=(384,312);reached=set();queue=deque([start])
    while queue:
        p=queue.popleft()
        if p in reached or p not in free:continue
        reached.add(p);x,y=p;queue.extend(((x-2,y),(x+2,y),(x,y-2),(x,y+2)))
    destinations={r['id']:[r['door'][0]*24+12,r['door'][1]*24+12] for r in plan['buildings']}
    destinations.update({r['id']:[r.get('approach',r['position'])[0]*24+12,r.get('approach',r['position'])[1]*24+12] for r in plan['landmarks']})
    destinations['woodland_exit']=[720,6]
    destinations['main_hero']=recipe['main_hero_foot']
    for b in buildings:
        if 'door_centre' in b:
            x,y,w,h=b['ground_rect_pixels']
            destinations[b['id']+'_actual_threshold']=[round(b['door_centre'][0]/2)*2,y+h+12]
    destinations.update({r['id']:r['foot'] for r in recipe['scale_checks']})
    for name,p in destinations.items():
        if tuple(p) not in reached:raise ValueError(f'Actor probe cannot reach {name}: {p}')
    blocked.save(OUTPUT/'navigation/blocking.png')
    mask=Image.new('L',size)
    for p in reached:mask.putpixel(p,255)
    mask.save(OUTPUT/'navigation/reachable_centres.png')
    allowed.save(OUTPUT/'navigation/allowed_routes.png')
    return {'probe_size':[24,12],'anchor':[12,30],'grid_step':2,'start':list(start),
            'destinations':destinations,'reachable_centres':len(reached),'engine_collision_implemented':False}


def review_frame(native,recipe):
    scale=recipe['review_scale'];scene=enlarged(native,scale)
    board=Image.new('RGB',(scene.width,scene.height+120),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
    d.text((24,14),f"ELDENMERE / terrain foundation / {recipe['status']}",font=font(27,True),fill='#243529')
    d.text((24,50),'64 x 56 tiles / existing native assets / Caelan at the commons',font=font(20),fill='#53696e')
    board.paste(scene,(0,84))
    d.text((24,scene.height+91),'Sanctuary and workshop are measured placeholders. Water, mill, lanterns and smoke animate; doors stay closed.',font=font(19),fill='#53696e')
    return board


def save_exact_gif(path,images,duration):
    colors=set()
    for im in images:
        colors.update(c for _,c in im.getcolors(maxcolors=65536) or [])
    if len(colors)>256:
        raise ValueError(f'GIF requires {len(colors)} colors; use an exact local palette per frame.')
    ordered=sorted(colors);lookup={c:i for i,c in enumerate(ordered)}
    flat=[v for c in ordered for v in c];palette=flat+[0]*(768-len(flat))
    def encode(rgb):
        # Pillow's nearest-palette cache can merge very close approved colors.
        # An explicit RGB lookup keeps every native pixel exact.
        raw=rgb.tobytes()
        data=bytes(lookup[c] for c in zip(raw[0::3],raw[1::3],raw[2::3]))
        result=Image.frombytes('P',rgb.size,data);result.putpalette(palette)
        return result
    indexed=[]
    for im in images:
        w,h=im.size;bottom=h-36
        native=im.crop((0,84,w,bottom)).resize((w//2,(bottom-84)//2),Image.Resampling.NEAREST)
        result=Image.new('P',im.size);result.putpalette(palette)
        result.paste(encode(im.crop((0,0,w,84))),(0,0))
        result.paste(enlarged(encode(native),2),(0,84))
        result.paste(encode(im.crop((0,bottom,w,h))),(0,bottom))
        indexed.append(result)
    indexed[0].save(path,save_all=True,append_images=indexed[1:],loop=0,duration=duration,disposal=1,optimize=False)


def scale_board(environment,bridges,recipe):
    # Each panel is a different placement of the same unmodified Caelan sprite.
    board=Image.new('RGB',(4160,1780),'#e8edf2');d=ImageDraw.Draw(board)
    d.text((24,18),'ELDENMERE / character scale and access / same Caelan in eight separate snapshots',font=font(29,True),fill='#243529')
    for i,record in enumerate(recipe['scale_checks']):
        image=with_actor(environment,bridges,record['foot'],record['facing'])
        crop=image.crop(box(pixel_rect(record['crop_tiles'])))
        col,row=i%4,i//4;x,y=24+col*1032,84+row*840
        d.text((x,y),record['label'],font=font(21,True),fill='#243529')
        board.paste(enlarged(crop,3),(x,y+34))
    board.save(OUTPUT/'scale_checks.png')


def labeled(native,plan,buildings,recipe):
    board=review_frame(native,recipe);d=ImageDraw.Draw(board)
    for b in buildings:
        if b['placeholder']:continue
        x,y,w,h=b['ground_rect_pixels'];point=(int((x+w/2)*2),int((y-84)*2+84))
        text={'halden':'HALDEN','elira':'ELIRA','venn':'VENN','mill':'WATERMILL'}.get(b['id'],'COTTAGE')
        f=font(21,True);rect=d.textbbox(point,text,font=f,anchor='mm')
        d.rounded_rectangle((rect[0]-8,rect[1]-4,rect[2]+8,rect[3]+4),radius=3,fill='#e8edf2')
        d.text(point,text,font=f,fill='#243529',anchor='mm')
    for text,point in [('COMMONS',(21,35)),('GATE / JAMMED',(58,25)),('EASTERN STEPS',(48,39)),('UPPER CROSSING',(35,22)),('MAIN BRIDGE',(34,45)),('WOODLAND ROUTE',(29,2))]:
        px,py=(point[0]*48+24,point[1]*48+108)
        f=font(20,True);rect=d.textbbox((px,py),text,font=f,anchor='mm')
        d.rectangle((rect[0]-7,rect[1]-4,rect[2]+7,rect[3]+4),fill='#e8edf2')
        d.text((px,py),text,font=f,fill='#243529',anchor='mm')
    board.save(OUTPUT/'labeled_layout.png')


def build():
    recipe=read_json(SOURCE/'recipe.json');plan=adapted_plan(recipe);geo=geometry(plan)
    for name in ('layers','frames','navigation'):(OUTPUT/name).mkdir(parents=True,exist_ok=True)
    base,grass,ground_meta=ground(plan,geo)
    masonry_layer,wall_collision,placements,stairs=masonry(plan,geo,base.size)
    water_placements,water_tiles=stream_tiles(geo)
    channel_data=channels(plan,geo);buildings=building_assets(recipe,plan);bridges=bridge_assets(plan)
    access=navigation(plan,geo,wall_collision,buildings,bridges,recipe)
    previews=[];frames=[];first_environment=None
    for tick in range(recipe['frame_count']):
        environment=render_environment(tick,base,grass,masonry_layer,water_placements,water_tiles,channel_data,buildings,bridges)
        if tick==0:first_environment=environment
        native=with_actor(environment,bridges,recipe['main_hero_foot'])
        path=f'frames/frame_{tick+1:02}.png';native.save(OUTPUT/path)
        previews.append(review_frame(native,recipe))
        frames.append({'image':path,'duration_ms':recipe['duration_ms'],'water_phase':tick%6,'smoke_phase':tick%18})
        if tick==0:
            native.save(OUTPUT/'town_native.png');labeled(native,plan,buildings,recipe)
    previews[0].save(OUTPUT/'town_review.png')
    save_exact_gif(OUTPUT/'town_review.gif',previews,recipe['duration_ms'])
    scale_board(first_environment,bridges,recipe)
    clean_buildings=[{k:v for k,v in r.items() if k!='frames'} for r in buildings]
    clean_bridges=[{k:v for k,v in r.items() if k not in ('base','foreground','lamps','shadows','wakes')} for r in bridges]
    write_json(OUTPUT/'scene.json',{'id':recipe['id'],'status':recipe['status'],'size_tiles':plan['size_tiles'],
        'tile_size':[24,24],'native_size':list(base.size),'approved_layout':recipe['approved_layout'],
        'adaptations':recipe['adaptations'],'ground':ground_meta,'masonry':placements,'stairs':stairs,
        'stream':water_placements,'water_flows':{'brook':geo['stream'],**geo['branches']},
        'channels':channel_data[4],'spillways':channel_data[5],'buildings':clean_buildings,'bridges':clean_bridges,
        'gate':{'state':recipe['gate_state'],'position':[1440,636],'ground_rect':[1440,648,24,24]},
        'frames':frames,'cycle_duration_ms':3600,'loop':True,'navigation':access,
        'hero':{'foot':recipe['main_hero_foot'],'anchor':[12,30],'image':'assets/characters/caelan/idle_front.png'},
        'scale_checks':recipe['scale_checks'],'review_scale':2,'review_image_rect':[0,84,3072,2688],
        'engine_map_implemented':False,'exterior_transitions_implemented':False,'quest_interaction_implemented':False,
        'purpose':'First terrain and building-placement pass; sanctuary/workshop placeholders; no final foliage or festival dressing.'})
    write_json(OUTPUT/'adapted_plan.json',plan)
    print('Built Eldenmere terrain foundation: 18 native frames, 2x loop, labeled layout and eight 3x Caelan scale snapshots.')


if __name__=='__main__':build()
