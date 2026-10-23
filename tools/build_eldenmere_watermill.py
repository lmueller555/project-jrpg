"""Build a static rural mill, eight-paddle rotating wheel and directed millrace."""

from collections import deque
from copy import deepcopy
from math import atan2, cos, hypot, pi, radians, sin
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw

from build_eldenmere_stream import read_json, write_json, rgba, enlarged, save_loop
from build_eldenmere_irrigation import core_frame, special_layers
from build_eldenmere_gate import channel_response

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/watermill'
OUTPUT=ROOT/'assets/terrain/eldenmere/watermill'
BRIDGE=OUTPUT.parent/'bridge'
CHANNELS=OUTPUT.parent/'irrigation'
STREAM=OUTPUT.parent/'stream'
GROUND=OUTPUT.parent/'grass_dirt'
PORTS={'N':1,'E':2,'S':4,'W':8}


def quantized(sample,colors):
    image=Image.new('RGBA',sample.size); ramp=[rgba(c) for c in colors]
    for y in range(sample.height):
        for x in range(sample.width):
            pixel=sample.getpixel((x,y))[:3]
            image.putpixel((x,y),min(ramp,key=lambda c:sum((a-b)**2 for a,b in zip(pixel,c))))
    return image


def extract_building(recipe,palette):
    reference=Image.open(SOURCE/recipe['source']).convert('RGB')
    sample=reference.crop(recipe['building_crop']).resize(tuple(recipe['building_size']),Image.Resampling.NEAREST)
    colors=[c for ramp in palette.values() for c in ramp.values()]
    building=quantized(sample,colors)
    # Flood only border-connected neutral backdrop; enclosed plaster and windows survive.
    corners=[sample.getpixel(p) for p in ((0,0),(119,0),(0,143),(119,143))]
    ramp=[rgba(c)[:3] for c in colors]
    def background(x,y):
        pixel=sample.getpixel((x,y))
        dist=lambda c:sum((a-b)**2 for a,b in zip(pixel,c))
        return min(map(dist,corners))+recipe['background_color_margin']<min(map(dist,ramp))
    pending=deque([(x,y) for y in range(144) for x in range(120) if x in (0,119) or y in (0,143)])
    visited=set()
    while pending:
        x,y=pending.popleft()
        if (x,y) in visited or not (0<=x<120 and 0<=y<144): continue
        visited.add((x,y))
        if not background(x,y): continue
        building.putpixel((x,y),(0,0,0,0))
        pending.extend(((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
    directory=SOURCE/'parts'; directory.mkdir(exist_ok=True)
    building.save(directory/'building_native.png')
    material=quantized(reference.crop(recipe['wheel_material_crop']).resize((4,12),Image.Resampling.NEAREST),palette['wood'].values())
    paddle=quantized(reference.crop(recipe['paddle_crop']).resize((8,3),Image.Resampling.NEAREST),palette['wood'].values())
    material.save(directory/'wheel_material.png'); paddle.save(directory/'paddle.png')
    return building,material,paddle


def structure_layer(building,recipe,palette):
    image=Image.new('RGBA',tuple(recipe['prefab_size'])); d=ImageDraw.Draw(image)
    x,y,w,h=recipe['porch_rect']
    d.rectangle((x,y,x+w-1,y+h-1),fill=palette['wood']['base'])
    for xx in range(x,x+w,6):
        d.line((xx,y,xx,y+h-1),fill=palette['wood']['shadow'])
        d.line((xx+1,y+2,xx+1,y+h-3),fill=palette['wood']['light'])
    for yy in (y,y+h-1): d.line((x,yy,x+w-1,yy),fill=palette['stone']['cap'])
    image.alpha_composite(building,tuple(recipe['building_offset']))
    return image


def wheel_frame(phase,recipe,palette,material,paddle):
    image=Image.new('RGBA',(48,48)); cx,cy=recipe['wheel_center']
    angle=radians(phase*recipe['wheel_step_degrees']); pitch=2*pi/8
    for y in range(48):
        for x in range(48):
            dx,dy=x-cx,y-cy; radius=hypot(dx,dy)
            theta=atan2(dy,dx)
            ray=angle+round((theta-angle)/pitch)*pitch
            along=dx*cos(ray)+dy*sin(ray); cross=-dx*sin(ray)+dy*cos(ray)
            if 17.5<=radius<=21:
                key='shadow' if radius<18.5 or radius>20.5 else 'base' if dx+dy>0 else 'light'
                image.putpixel((x,y),rgba(palette['wood'][key]))
            if 4<=along<=19 and abs(cross)<1.6:
                image.putpixel((x,y),material.getpixel((min(3,int(cross+1.6)),int(along)%12)))
    d=ImageDraw.Draw(image); centers=[]
    for spoke in range(8):
        theta=angle+spoke*pitch; ux,uy=cos(theta),sin(theta); vx,vy=-uy,ux
        center=(cx+22.5*ux,cy+22.5*uy); centers.append([round(c,4) for c in center])
        polygon=[(center[0]+a*ux+b*vx,center[1]+a*uy+b*vy) for a,b in ((-1.5,-4),(1.5,-4),(1.5,4),(-1.5,4))]
        d.polygon(polygon,fill=palette['wood']['base'],outline=palette['wood']['shadow'])
        p1=(center[0]-ux-3*vx,center[1]-uy-3*vy)
        p2=(center[0]-ux+3*vx,center[1]-uy+3*vy)
        d.line((p1,p2),fill=paddle.getpixel((4,1)))
        bx,by=round(cx+18*ux),round(cy+18*uy)
        d.rectangle((bx,by,bx+1,by+1),fill=palette['iron']['base'])
    d.ellipse((18,18,29,29),fill=palette['iron']['shadow'])
    d.ellipse((20,20,27,27),fill=palette['wood']['base'])
    d.ellipse((22,22,25,25),fill=palette['iron']['base'])
    d.point((23,23),fill=palette['iron']['light'])
    return image,centers


def race_placements(recipe):
    cells=[{'cell':recipe['intake_cell'],'route':'inlet_e','input':'stream','outputs':['E']}]
    def add(x,y,incoming,outgoing):
        cells.append({'cell':[x,y],'route':f'channel_{PORTS[incoming]+PORTS[outgoing]:02}_from_{incoming.lower()}',
                      'input':incoming,'outputs':[outgoing]})
    for x in range(18,28): add(x,4,'W','E')
    add(28,4,'W','S')
    for y in range(5,11): add(28,y,'N','S')
    add(28,11,'N','W')
    for x in range(27,17,-1): add(x,11,'E','W')
    cells.append({'cell':recipe['return_cell'],'route':'return_w','input':'E','outputs':['stream']})
    wheel_index=next(i for i,p in enumerate(cells) if p['cell']==[26,11])
    for index,p in enumerate(cells):
        if index<=wheel_index:
            surface=recipe['intake_water_elevation_pixels']+(recipe['race_water_elevation_pixels']-recipe['intake_water_elevation_pixels'])*index/wheel_index
        else:
            surface=recipe['race_water_elevation_pixels']+(recipe['return_water_elevation_pixels']-recipe['race_water_elevation_pixels'])*(index-wheel_index)/(len(cells)-1-wheel_index)
        p['water_elevation_pixels']=round(surface,4)
    return cells


def elevations(recipe):
    return {'bank':recipe['bank_elevation_pixels'],'floor_and_landing':recipe['floor_elevation_pixels'],
            'intake_water':recipe['intake_water_elevation_pixels'],'race_water':recipe['race_water_elevation_pixels'],
            'return_water':recipe['return_water_elevation_pixels'],'wheel_axle':recipe['wheel_axle_elevation_pixels'],
            'wheel_radius':recipe['wheel_radius_pixels']}


def race_assets(palette):
    meta=read_json(CHANNELS/'tileset.json'); records={r['id']:r for r in meta['routes']}
    frames=[Image.open(CHANNELS/f['image']).convert('RGBA') for f in meta['frames']]
    tiles={}; masks={}
    for name,record in records.items():
        x,y,w,h=record['rect']; tiles[name]=[a.crop((x,y,x+w,y+h)) for a in frames]
        masks[name]=Image.open(CHANNELS/record['water_mask']).convert('RGBA')
    bank,mask=special_layers('inlet','E',palette)
    recipe=read_json(ROOT/'assets/source/terrain/eldenmere/irrigation/recipe.json')
    tiles['return_w']=[core_frame({'input':'E','outputs':['W']},bank,mask,p,recipe,palette) for p in range(6)]
    masks['return_w']=mask
    records['return_w']={'id':'return_w','kind':'channel','input':'E','outputs':['W']}
    return records,tiles,masks


def obstruction_frame(tile,mask,record,palette):
    image=channel_response(tile,mask,record,'dry',0,palette)
    for y in range(24):
        for x in range(12):
            if mask.getpixel((x,y))[3]: image.putpixel((x,y),tile.getpixel((x,y)))
    d=ImageDraw.Draw(image)
    d.line((10,7,14,17),fill=palette['wood']['shadow'],width=2)
    for x,y in ((12,8),(11,11),(13,14)):
        d.rectangle((x,y,x+2,y+2),fill=palette['stone']['shadow'])
        d.line((x,y,x+1,y),fill=palette['stone']['light'])
    return image


def effects_layer(phase,recipe,palette):
    image=Image.new('RGBA',tuple(recipe['prefab_size'])); d=ImageDraw.Draw(image)
    wx,wy=recipe['wheel_offset']; water=palette['water']
    # Clockwise motion lifts wet paddles on the left. Drops fall toward the race below.
    for offset in (0,3):
        tick=(phase+offset)%6; x=wx+7+offset
        y=wy+33+tick*2
        if y<140: d.line((x,y,x,y+1),fill=water['reflection'])
    for x,y in ((wx+13-phase%2,141),(wx+16+phase%2,143)):
        d.point((x,y),fill=water['glint'])
    radius=2+phase//2
    d.arc((wx-6-radius,145,wx-6+radius,147),90,270,fill=water['flow' if phase in (0,5) else 'reflection'])
    return image


def export_race(recipe,palette,records,tiles,masks):
    placements=race_placements(recipe)
    names=list(dict.fromkeys(p['route'] for p in placements)); metadata=[]
    for index,name in enumerate(names):
        metadata.append({'id':name,'rect':[index%4*24,index//4*24,24,24]})
    blocked=placements.index(next(p for p in placements if p['cell']==recipe['obstruction_cell']))
    for index,p in enumerate(placements): p['stopped_mode']='full' if index<blocked else 'blocked' if index==blocked else 'dry'
    height=((len(names)+3)//4)*24
    for phase in range(6):
        atlas=Image.new('RGBA',(96,height))
        for record in metadata: atlas.paste(tiles[record['id']][phase],tuple(record['rect'][:2]))
        atlas.save(OUTPUT/f'race/frame_{phase+1:02}.png')
    dry=Image.new('RGBA',(96,height))
    for record in metadata:
        name=record['id']
        dry.paste(channel_response(tiles[name][0],masks[name],records[name],'dry',0,palette),tuple(record['rect'][:2]))
    dry.save(OUTPUT/'race/dry.png')
    record=next(p for p in placements if p['stopped_mode']=='blocked'); name=record['route']
    blockage=obstruction_frame(tiles[name][0],masks[name],records[name],palette)
    blockage.save(OUTPUT/'race/blocked.png')
    return placements,metadata,blockage


def background_frames(recipe,palette):
    old=read_json(BRIDGE/'review_scene.json'); stream=read_json(STREAM/'review_scene.json')
    gm=read_json(GROUND/'tileset.json'); grass=[Image.open(GROUND/p).convert('RGBA') for p in gm['grass']['images']]
    dirt={t['mask']:Image.open(GROUND/t['image']).convert('RGBA') for t in gm['tiles']}
    fills=[Image.open(GROUND/p).convert('RGBA') for p in gm['dirt_interiors']['images']]
    width,height=recipe['scene_size']; grass_ids=deepcopy(old['grass_variants']); rng=Random(712)
    for row in grass_ids: row.extend(rng.choices(range(4),weights=(5,3,2,1),k=width-len(row)))
    cells={tuple(p) for p in recipe['yard_dirt_cells']}; joins=cells|{tuple(p) for p in recipe['dirt_join_cells']}
    offsets=[(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]
    frames=[]
    for phase in range(6):
        image=Image.new('RGBA',(width*24,height*24))
        for y,row in enumerate(grass_ids):
            for x,variant in enumerate(row): image.paste(grass[variant],(x*24,y*24))
        old_frame=Image.open(BRIDGE/f'scene_frames/frame_{phase+1:02}.png').convert('RGBA')
        image.paste(old_frame,(0,0))
        for x,y in recipe['restored_cells']:
            tile=grass[grass_ids[y][x]].copy(); mask=stream['dirt_masks'][y][x]; fill=stream['dirt_fill_variants'][y][x]
            if mask is not None: tile.alpha_composite(fills[fill] if fill is not None else dirt[mask])
            assert stream['water_masks'][y][x] is None
            image.paste(tile,(x*24,y*24))
        for x,y in cells:
            raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in joins)
            mask=gm['tiles'][gm['lookup_256'][raw]]['mask']; image.alpha_composite(dirt[mask],(x*24,y*24))
        frames.append(image)
    return frames,grass_ids


def build_scene(recipe,palette,mill_frames,stopped,records,tiles,masks,placements,blockage):
    backgrounds,grass_ids=background_frames(recipe,palette)
    worker=Image.open(ROOT/'assets/characters/npcs/male_03/idle_front.png').convert('RGBA')
    scene_frames={}; native_states={}
    for state in ('running','stopped'):
        previews=[]; closeups=[]; native_states[state]=[]; scene_frames[state]=[]
        for phase,background in enumerate(backgrounds):
            image=background.copy()
            for p in placements:
                name=p['route']; tile=tiles[name][phase]
                mode='full' if state=='running' else p['stopped_mode']
                if mode=='dry': tile=channel_response(tiles[name][0],masks[name],records[name],'dry',0,palette)
                if mode=='blocked': tile=blockage
                x,y=p['cell']; image.alpha_composite(tile,(x*24,y*24))
            mill=mill_frames[phase] if state=='running' else stopped
            image.alpha_composite(mill,tuple(recipe['scene_position']))
            image.alpha_composite(worker,tuple(recipe['worker_position']))
            native=image.convert('RGB'); path=f'scene_{state}/frame_{phase+1:02}.png'; native.save(OUTPUT/path)
            native_states[state].append(native); scene_frames[state].append({'image':path,'water_phase':phase,'duration_ms':200})
            previews.append(enlarged(native,recipe['scene_scale']))
            closeups.append(enlarged(native.crop(recipe['closeup_rect']),recipe['closeup_scale']))
        prefix='review_scene' if state=='running' else 'stopped_scene'
        previews[0].save(OUTPUT/f'{prefix}.png'); save_loop(OUTPUT/f'{prefix}.gif',previews,recipe)
        prefix='mill_closeup' if state=='running' else 'stopped_closeup'
        closeups[0].save(OUTPUT/f'{prefix}.png'); save_loop(OUTPUT/f'{prefix}.gif',closeups,recipe)
    boards=[]
    for phase in range(6):
        board=Image.new('RGB',(1392,832),'#e8edf2'); d=ImageDraw.Draw(board); d.fontmode='1'
        d.text((16,12),f"Eldenmere watermill / {recipe['status']}",fill='#243529',font_size=24)
        for col,state in enumerate(('running','stopped')):
            crop=native_states[state][phase].crop((504,96,720,336))
            board.paste(enlarged(crop,3),(col*696+24,80))
            d.text((col*696+24,52),'RUNNING / supplied race' if state=='running' else 'STOPPED / blocked supply',fill='#243529',font_size=20)
        boards.append(board)
    boards[0].save(OUTPUT/'states_review.png'); save_loop(OUTPUT/'states_review.gif',boards,recipe)
    write_json(OUTPUT/'review_scene.json',{'status':recipe['status'],'purpose':'Mill art/state review; illustrative layout, not canonical geography or gameplay',
        'base_scene':'../bridge/review_scene.json','grid_size':recipe['scene_size'],'grass_variants':grass_ids,
        'mill_position':recipe['scene_position'],'race':placements,'race_flow_at_wheel':'W','wheel_direction':'clockwise',
        'obstruction_cell':recipe['obstruction_cell'],'restored_cells':recipe['restored_cells'],
        'yard_dirt_cells':recipe['yard_dirt_cells'],'dirt_join_cells':recipe['dirt_join_cells'],
        'worker':{'image_from_repo_root':'assets/characters/npcs/male_03/idle_front.png','position':recipe['worker_position'],
                  'foot':recipe['worker_foot'],'replaces_original':True,'role':'generic NPC for scale, not a new named-character design'},
        'elevations':elevations(recipe),
        'states':scene_frames,'loop':True,'cycle_duration_ms':1200,
        'review':{'scene_scale':recipe['scene_scale'],'closeup_rect':recipe['closeup_rect'],'closeup_scale':recipe['closeup_scale']}})


def build():
    recipe=read_json(SOURCE/'recipe.json'); palette=deepcopy(read_json(BRIDGE/'palette.json')['materials']); palette.update(recipe['palette'])
    OUTPUT.mkdir(exist_ok=True)
    for directory in ('wheel','effects','running','race','scene_running','scene_stopped'): (OUTPUT/directory).mkdir(exist_ok=True)
    building,material,paddle=extract_building(recipe,palette)
    structure=structure_layer(building,recipe,palette); structure.save(OUTPUT/'building.png')
    wheel_frames=[]; running=[]; wheel_meta=[]; sheet=Image.new('RGBA',(144,1008))
    for phase in range(6):
        wheel,centers=wheel_frame(phase,recipe,palette,material,paddle); wheel_frames.append(wheel)
        wheel.save(OUTPUT/f'wheel/frame_{phase+1:02}.png')
        effects=effects_layer(phase,recipe,palette); effects.save(OUTPUT/f'effects/frame_{phase+1:02}.png')
        frame=structure.copy(); frame.alpha_composite(wheel,tuple(recipe['wheel_offset'])); frame.alpha_composite(effects)
        frame.save(OUTPUT/f'running/frame_{phase+1:02}.png'); running.append(frame); sheet.paste(frame,(0,phase*168))
        wheel_meta.append({'image':f'wheel/frame_{phase+1:02}.png','angle_degrees':phase*7.5,'paddle_centers':centers,'duration_ms':200})
    stopped=structure.copy(); stopped.alpha_composite(wheel_frames[0],tuple(recipe['wheel_offset'])); stopped.save(OUTPUT/'stopped.png')
    sheet.save(OUTPUT/'mill_sheet.png')
    records,tiles,masks=race_assets(palette)
    placements,race_meta,blockage=export_race(recipe,palette,records,tiles,masks)
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':palette})
    write_json(OUTPUT/'mill.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],'prefab_size':recipe['prefab_size'],
        'building':'building.png','stopped':'stopped.png','sheet':'mill_sheet.png','building_ground_rect':recipe['building_ground_rect'],
        'wheel':{'size':[48,48],'position':recipe['wheel_offset'],'spokes':8,'paddles':8,'direction':'clockwise',
                 'step_degrees':7.5,'symmetric_repeat_degrees':45,'implied_full_turn_ms':9600,'frames':wheel_meta},
        'running':{'loop':True,'cycle_duration_ms':1200,'frames':[{'image':f'running/frame_{p+1:02}.png',
            'effects':f'effects/frame_{p+1:02}.png','sheet_rect':[0,p*168,144,168],'duration_ms':200} for p in range(6)]},
        'landing_rect':recipe['porch_rect'],'elevations':elevations(recipe),
        'race':{'tiles':race_meta,'frames':[f'race/frame_{p+1:02}.png' for p in range(6)],'dry':'race/dry.png','blocked':'race/blocked.png',
                'water_width_pixels':8,'intake_cell':recipe['intake_cell'],'return_cell':recipe['return_cell'],'obstruction_optional':True},
        'recipe':'../../../source/terrain/eldenmere/watermill/recipe.json',
        'review':{'scene':'review_scene.gif','closeup':'mill_closeup.gif','states':'states_review.gif','stopped_scene':'stopped_scene.gif'}})
    build_scene(recipe,palette,running,stopped,records,tiles,masks,placements,blockage)
    print('Built watermill: static slate-roof building, six clockwise wheel phases, directed race and stopped supply state')


if __name__=='__main__':
    build()
