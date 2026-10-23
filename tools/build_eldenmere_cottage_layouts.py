"""Assemble three cottage interiors from approved native assets; check floor access."""
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import opened, save_loop
from build_eldenmere_cottage_hearth import mix

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage_layouts'
OUTPUT=ROOT/'assets/terrain/eldenmere/cottage_layouts'
TERRAIN=OUTPUT.parent
INTERIOR=TERRAIN/'cottage_interior'
HEARTH=TERRAIN/'cottage_hearth'
PACK_META={'cottage_furniture':'furniture.json','cottage_storage':'storage.json','cottage_kitchen':'kitchen.json'}


def box(rect):
    x,y,w,h=rect;return (x,y,x+w,y+h)


def source_object(record):
    meta=read_json(TERRAIN/record['pack']/PACK_META[record['pack']])
    sprite=next(r for r in meta['sprites'] if r['id']==record['sprite'])
    x,y=record['position']
    floor=sprite.get('floor_rect')
    return {**record,'image_from_repo_root':str((TERRAIN/record['pack']/sprite['image']).relative_to(ROOT)),
            'frame_size':sprite['frame_size'],'floor_rect':None if floor is None else [x+floor[0],y+floor[1],*floor[2:]],
            'sort_y':0 if floor is None else y+floor[1]+floor[3]}


def alignment(layout):
    exterior=read_json(TERRAIN/layout['exterior']/'cottage.json')
    gx,gy,gw,gh=exterior['ground_rect'];dx,dy=exterior['door']['position'];dw,dh=exterior['door']['size']
    width=layout['floor_tiles'][0]*24
    ideal_entry=24+(dx+dw/2-gx)/gw*width
    centre=round(ideal_entry/2)*2
    original=read_json(TERRAIN/'cottage/cottage.json')
    chimney=next(r for r in original['components'] if r['id']=='chimney')
    offset=exterior.get('animation_offset_from_source',[0,0])[0]
    cx=chimney['position'][0]+chimney['rect'][2]-chimney['rect'][0]
    cx-= (chimney['rect'][2]-chimney['rect'][0])/2
    ideal_chimney=24+(cx+offset-gx)/gw*width
    return exterior,[centre-12,216,24,8],[round(ideal_chimney)-24,24],{
        'exterior_ground_rect':exterior['ground_rect'],'ideal_entry_center_x':ideal_entry,
        'entry_center_x':centre,'ideal_chimney_center_x':ideal_chimney,
        'chimney_center_x':round(ideal_chimney),'exterior_front_window_count':exterior.get('window_count',2)}


def shell(layout,entry):
    w,h=[n*24 for n in layout['floor_tiles']];size=(w+48,h+96)
    floor=Image.new('RGBA',size);walls=Image.new('RGBA',size);fixtures=Image.new('RGBA',size)
    for row in range(h//24):
        for col in range(w//24):
            floor.alpha_composite(opened(INTERIOR/'tiles'/f"floor_{'abc'[(col+row*2)%3]}.png"),(24+col*24,72+row*24))
    for col in range(w//24):
        walls.alpha_composite(opened(INTERIOR/'tiles'/f"north_{'a' if col%2==0 else 'b'}.png"),(24+col*24,24))
        walls.alpha_composite(opened(INTERIOR/'tiles/south_cap.png'),(24+col*24,216))
    for y in range(72,216,24):
        walls.alpha_composite(opened(INTERIOR/'tiles/west_side.png'),(0,y))
        walls.alpha_composite(opened(INTERIOR/'tiles/east_side.png'),(w+24,y))
    for name,pos in [('northwest_corner',(0,24)),('northeast_corner',(w+24,24)),('southwest_corner',(0,216)),('southeast_corner',(w+24,216))]:
        walls.alpha_composite(opened(INTERIOR/'tiles'/f'{name}.png'),pos)
    # The exterior door can land on a half-tile; clear both affected cap pieces.
    walls.paste((0,0,0,0),box(entry));walls.alpha_composite(opened(INTERIOR/'tiles/entry_threshold.png'),tuple(entry[:2]))
    for x in layout['supports']:fixtures.alpha_composite(opened(INTERIOR/'parts/vertical_beam.png'),(x,24))
    window=opened(INTERIOR/'parts/window.png')
    for position in layout['window_positions']:fixtures.alpha_composite(window,tuple(position))
    partition=Image.new('RGBA',size)
    if layout['partition']:
        x,y,pw,ph=layout['partition'];strip=opened(INTERIOR/'tiles/west_side.png').crop((12,0,24,24))
        for yy in range(y,y+ph,24):partition.alpha_composite(strip,(x,yy))
    structure=Image.new('RGBA',size,'#24302d')
    for layer in (floor,walls,fixtures,partition):structure.alpha_composite(layer)
    return floor,walls,fixtures,partition,structure


def navigation(size,floor_rect,objects,partition,entry,probe):
    blocked=Image.new('L',size);draw=ImageDraw.Draw(blocked)
    rectangles=[r['floor_rect'] for r in objects if r.get('floor_rect')]
    if partition:rectangles.append(partition)
    for x,y,w,h in rectangles:draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
    x0,y0,w,h=floor_rect;pw,ph=probe;centres=Image.new('L',size)
    for y in range(y0+ph//2,y0+h-ph//2+1,2):
        for x in range(x0+pw//2,x0+w-pw//2+1,2):
            if not blocked.crop((x-pw//2,y-ph//2,x+pw//2,y+ph//2)).getbbox():centres.putpixel((x,y),255)
    start=(entry[0]+12,210);reached=set();queue=deque([start])
    while queue:
        x,y=queue.popleft()
        if (x,y) in reached or not (0<=x<size[0] and 0<=y<size[1]) or not centres.getpixel((x,y)):continue
        reached.add((x,y));queue.extend(((x-2,y),(x+2,y),(x,y-2),(x,y+2)))
    for r in objects:
        if tuple(r['access']) not in reached:raise ValueError(f"Unreachable {r['id']} at {r['access']}")
    return blocked,centres,reached


def room_frames(recipe,layout):
    out=OUTPUT/layout['id'];(out/'scene_frames').mkdir(parents=True,exist_ok=True)
    exterior,entry,hearth_position,registration=alignment(layout)
    floor,walls,fixtures,partition,structure=shell(layout,entry)
    objects=[source_object(r) for r in layout['objects']]
    hx,hy=hearth_position
    hearth={'id':'hearth','floor_rect':[hx+2,hy+48,44,20],'position':hearth_position,
            'frame_size':[48,72],'access':[hx+24,104],'sort_y':hy+68}
    objects.append(hearth)
    floor_rect=[24,72,layout['floor_tiles'][0]*24,144]
    blocked,centres,reached=navigation(structure.size,floor_rect,objects,layout['partition'],entry,recipe['actor_probe_size'])
    hero=opened(ROOT/'assets/characters/caelan/idle_front.png');hero_position=layout['hero_position']
    anchor=recipe['hero_foot_anchor'];hero_centre=(hero_position[0]+anchor[0],hero_position[1]+anchor[1])
    if hero_centre not in reached:raise ValueError(f'Unreachable hero: {layout["id"]}')
    base_recipe=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_interior/recipe.json')
    hearth_recipe=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_hearth/recipe.json')
    # Derive the fixed pane projection directly from the approved glass pixels.
    glass={rgba(c) for c in base_recipe['palette']['glass'].values()}
    window=opened(INTERIOR/'parts/window.png');glass_mask=Image.new('L',window.size)
    glass_mask.putdata([255 if p in glass else 0 for p in window.get_flattened_data()])
    projection=glass_mask.resize((30,24),Image.Resampling.NEAREST);daymask=Image.new('L',structure.size)
    for wx,wy in layout['window_positions']:
        for y in range(24):
            for x in range(30):
                px,py=wx+6+x+y//3,78+y
                if projection.getpixel((x,y)) and floor.getpixel((px,py))[3]:daymask.putpixel((px,py),255)
    glowmask=Image.new('L',structure.size)
    for y in range(89,110):
        for x in range(hx+2,hx+48):
            distance=((x+.5-(hx+25))/23)**2+((y+.5-99.5)/10.5)**2
            if floor.getpixel((x,y))[3] and distance<=1:glowmask.putpixel((x,y),255 if distance<=.45 else 128)
    for name,im in [('floor',floor),('walls',walls),('fixtures',fixtures),('partition',partition),('structure',structure),('blocking',blocked),('navigable_centres',centres),('daylight_mask',daymask),('floor_glow_mask',glowmask)]:im.save(out/f'{name}.png')
    wood=list(base_recipe['palette']['wood'].values());wood_rgba=[rgba(c) for c in wood]
    daylight=read_json(INTERIOR/'palette.json')['daylight']
    sprites={r['id']:opened(ROOT/r['image_from_repo_root']) for r in objects if r['id']!='hearth'}
    frames=[];timeline=[]
    for tick in range(36):
        phase=tick%4;day_phase=tick//2%9;strength=base_recipe['light_strengths'][day_phase]
        image=structure.copy()
        for y in range(image.height):
            for x in range(image.width):
                if daymask.getpixel((x,y)):
                    index=wood_rgba.index(floor.getpixel((x,y)))
                    image.putpixel((x,y),rgba(list(daylight[strength].values())[index]))
                intensity=glowmask.getpixel((x,y))
                if intensity:image.putpixel((x,y),mix(image.getpixel((x,y)),rgba(hearth_recipe['glow_color']),hearth_recipe['glow_strengths'][phase]*(1 if intensity==255 else .5)))
        draws=[]
        for r in objects:
            sprite=opened(HEARTH/'frames'/f'frame_{phase+1:02}.png') if r['id']=='hearth' else sprites[r['id']]
            draws.append((r['sort_y'],sprite,r['position']))
        draws.append((hero_centre[1]+6,hero,hero_position))
        for _,sprite,pos in sorted(draws,key=lambda r:r[0]):image.alpha_composite(sprite,tuple(pos))
        native=image.convert('RGB');native.save(out/'scene_frames'/f'frame_{tick+1:02}.png');frames.append(native)
        timeline.append({'image':f'scene_frames/frame_{tick+1:02}.png','duration_ms':300,'fire_phase':phase,'daylight_phase':day_phase})
    frames[0].resize((structure.width*4,structure.height*4),Image.Resampling.NEAREST).save(out/'room_review.png')
    save_loop(out/'room_review.gif',[enlarged(f,4) for f in frames],{'duration_ms':300})
    write_json(out/'room.json',{'id':layout['id'],'status':recipe['status'],'floor_tiles':layout['floor_tiles'],
        'room_size':list(structure.size),'floor_rect':floor_rect,'entry_rect':entry,'exterior':layout['exterior'],
        'registration':registration,'rear_windows':layout['window_positions'],'partition_rect':layout['partition'],
        'objects':objects,'hero_position':hero_position,'hero_foot_anchor':anchor,'actor_probe_size':recipe['actor_probe_size'],
        'navigation_start':[entry[0]+12,210],'reachable_probe_positions':len(reached),
        'frames':timeline,'cycle_duration_ms':10800,'loop':True,'review_scale':4,
        'engine_collision_implemented':False,'exterior_transition_implemented':False,
        'purpose':'Furnished size/layout review; no named household assigned','draw_order':'Structure and local lighting, then furnishings and character by floor-foot baseline'})
    return frames,opened(TERRAIN/layout['exterior']/'closed.png')


def build():
    recipe=read_json(SOURCE/'recipe.json');OUTPUT.mkdir(parents=True,exist_ok=True)
    rendered=[room_frames(recipe,layout) for layout in recipe['layouts']]
    scale=recipe['review_scale'];width=sum(frames[0].width*scale for frames,_ in rendered)+24*4
    boards=[]
    for tick in range(36):
        board=Image.new('RGB',(width,1320),'#e8edf2');draw=ImageDraw.Draw(board);draw.fontmode='1'
        draw.text((24,14),f"Eldenmere cottage interiors / {recipe['status']} / same 3x pixel scale",fill='#243529',font_size=26)
        x=24
        for layout,(frames,exterior) in zip(recipe['layouts'],rendered,strict=True):
            column=frames[0].width*scale
            draw.text((x,66),f"{layout['label']} / outside {layout['floor_tiles'][0]//2} x 3",fill='#243529',font_size=23)
            board.paste(enlarged(exterior,scale),(x+(column-exterior.width*scale)//2,96),enlarged(exterior,scale))
            draw.text((x,554),f"Interior floor {layout['floor_tiles'][0]} x 6 / 24px tiles",fill='#243529',font_size=23)
            board.paste(enlarged(frames[tick],scale),(x,594));x+=column+24
        boards.append(board)
    boards[0].save(OUTPUT/'layouts_review.png');save_loop(OUTPUT/'layouts_review.gif',boards,{'duration_ms':300})
    write_json(OUTPUT/'layouts.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'character_frame_size':[24,36],'layouts':[{'id':r['id'],'floor_tiles':r['floor_tiles'],'room':f"{r['id']}/room.json"} for r in recipe['layouts']],
        'review_scale':scale,'review_size':list(boards[0].size),'cycle_duration_ms':10800,'frame_duration_ms':300,
        'source_recipe':'../../../source/terrain/eldenmere/cottage_layouts/recipe.json',
        'native_art_rescaled':False,'household_assignments':None})
    print('Built 6x6, 8x6 and 10x6 furnished layouts; all furnishing approaches reachable by a 24x12 floor probe.')


if __name__=='__main__':build()
