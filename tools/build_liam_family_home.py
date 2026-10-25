"""Add the family cottage locally without rebuilding existing NPC scenes."""
from pathlib import Path

from PIL import Image, ImageDraw

from build_eldenmere_stream import read_json,write_json
from build_eldenmere_terrain import BITS,OFFSETS,normalize_mask
from build_eldenmere_cottage_layouts import source_object
from build_building_interiors import compile_room,room_spawn,portal

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'assets/maps/eldenmere/liam_house'
TOWN=ROOT/'assets/maps/eldenmere/playable/map.json'
ROOM=ROOT/'assets/maps/eldenmere/building_interiors/rooms/liam_house/map.json'


def opened(path,mode='RGBA'):
    with Image.open(path) as im:return im.convert(mode)


def save(path,image):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
    return path.relative_to(ROOT).as_posix()


def rect_box(rect):
    x,y,w,h=rect;return x,y,x+w,y+h


def exterior(recipe):
    pack=ROOT/recipe['exterior_pack'];meta=read_json(pack/'cottage.json')
    frames=[]
    for i in range(18):
        image=opened(pack/'structure.png')
        for part in ('doors/frame_01.png',f'lantern/frame_{i+1:02}.png',f'smoke/frame_{i+1:02}.png'):
            image.alpha_composite(opened(pack/part))
        frames.append(save(AREA/f'exterior/frame_{i+1:02}.png',image))
    x,y=recipe['position'];dx,dy=meta['door']['position'];w,h=meta['door']['size'];box=(dx,dy,dx+w,dy+h)
    background=opened(pack/'structure.png').crop(box);doors=[]
    for i,record in enumerate(meta['door']['opening']['frames'],1):
        patch=background.copy();patch.alpha_composite(opened(pack/record['image']).crop(box))
        doors.append(save(AREA/f'doors/frame_{i:02}.png',patch))
    assert opened(ROOT/frames[0]).crop(box).tobytes()==opened(ROOT/doors[0]).tobytes()
    baseline=recipe['ground_rect'][1]+recipe['ground_rect'][3]
    entity={'id':recipe['id'],'position':recipe['position'],'sort_y':baseline,'frames':frames,
            'frame_duration_ms':200,'phase_offset':0}
    entry=[x+dx+w/2,baseline+6]
    return entity,doors,[x+dx,y+dy],entry,w


def extend_paths(data,recipe):
    x,y,w,h=recipe['path_rect_tiles'];added={(xx,yy) for yy in range(y,y+h) for xx in range(x,x+w)}
    # Include existing dirt when selecting 47-blob edges at the junction.
    # The approved plan records path cells independently of the rendered art.
    plan=read_json(ROOT/'assets/maps/eldenmere/terrain_foundation/adapted_plan.json')
    from build_eldenmere_blockout import geometry,cells
    original=set(geometry(plan)['roads'])
    for space in plan['spaces']:
        if space['kind'] in ('yard','plots','garden'):original.update(cells(space['rect']))
    all_dirt=original|added
    tiles=ROOT/'assets/terrain/eldenmere/grass_dirt';meta=read_json(tiles/'tileset.json')
    lookup={r['mask']:opened(tiles/r['image']) for r in meta['tiles']}
    fill=[opened(tiles/name) for name in meta['dirt_interiors']['images']]
    patch=Image.new('RGBA',tuple(data['size_pixels']))
    # Repaint the existing lane's adjacent edge tiles so the path joins cleanly.
    affected=added|{(xx+dx,yy+dy) for xx,yy in added for dx,dy in OFFSETS.values() if (xx+dx,yy+dy) in original}
    for xx,yy in sorted(affected):
        raw=sum(BITS[name] for name,(dx,dy) in OFFSETS.items() if (xx+dx,yy+dy) in all_dirt)
        mask=normalize_mask(raw);sprite=fill[(xx+2*yy)%3] if mask==255 else lookup[mask]
        patch.alpha_composite(sprite,(xx*24,yy*24))
    # Restore grass under each affected cell before applying native opaque/
    # transparent tile pixels; repeated builds cannot accumulate edge shadows.
    grass=opened(ROOT/'assets/maps/eldenmere/terrain_foundation/layers/grass.png')
    for relative in dict.fromkeys(data['ground_frames']):
        image=opened(ROOT/relative)
        for xx,yy in affected:
            box=(xx*24,yy*24,(xx+1)*24,(yy+1)*24)
            image.paste(grass.crop(box),(xx*24,yy*24))
        image.alpha_composite(patch);save(ROOT/relative,image.convert('RGB'))
    allowed=opened(ROOT/data['navigation_allowed'],'L')
    for xx,yy in affected:allowed.paste(255,(xx*24,yy*24,(xx+1)*24,(yy+1)*24))
    data['navigation_allowed']=save(AREA/'allowed_routes.png',allowed)
    blocked=opened(ROOT/data['collision'],'L');blocked.paste(255,rect_box(recipe['ground_rect']))
    save(ROOT/data['collision'],blocked)
    save(AREA/'path_overlay.png',patch)


def interior(recipe,data,entry):
    directory=ROOT/recipe['interior_source']
    meta,room,blocked=compile_room(directory,recipe['id'])
    # The base wide shell retains its partition, windows and lighting.
    next(e for e in room['entities'] if e['id']=='bed')['id']='parents_bed'
    room['destinations']['parents_bed']=room['destinations'].pop('bed')
    room['destinations']['table']=recipe['table_access']
    extras=[source_object(record) for record in recipe['extra_furniture']]
    for obj in extras:
        room['entities'].append({'id':obj['id'],'position':obj['position'],'sort_y':obj['sort_y'],
                                'sort_priority':0,'frames':[obj['image_from_repo_root']],
                                'frame_duration_ms':300,'phase_offset':0})
        if obj.get('floor_rect'):blocked.paste(255,rect_box(obj['floor_rect']))
        room['destinations'][obj['id']]=obj['access']
    room['destinations']['daisy_rest_space']=recipe['daisy_rest_space']
    room['collision']=save(ROOT/room['collision'],blocked)
    spawn=room_spawn(meta,blocked);outside=[entry[0],entry[1]+12]
    threshold=meta['entry_rect'];centre=threshold[0]+threshold[2]/2
    room.update(id=recipe['id'],name=recipe['name'],spawn=spawn,household=recipe['household'],
                overview=data['overview'],household_layout=(AREA/'house.json').relative_to(ROOT).as_posix())
    room['doors']=[portal('courtyard',[centre,threshold[1]-6],'south',TOWN.relative_to(ROOT).as_posix(),
                           outside,recipe['id'],width=threshold[2])]
    write_json(ROOM,room)
    write_json(AREA/'interior_layout.json',{'source_room':room['source_room'],'household':recipe['household'],
                'floor_tiles':recipe['floor_tiles'],'extra_objects':extras,'parents_bed':'bed',
                'table_access':recipe['table_access'],'daisy_rest_space':recipe['daisy_rest_space']})
    return spawn


def overview(data):
    image=opened(ROOT/data['ground_frames'][0])
    for entity in sorted(data['entities'],key=lambda e:(e['sort_y'],e.get('sort_priority',0))):
        path=entity['frames'][entity.get('phase_offset',0)%len(entity['frames'])]
        image.alpha_composite(opened(ROOT/path),tuple(entity['position']))
    for layer in data['foreground']:image.alpha_composite(opened(ROOT/layer['image']),tuple(layer['position']))
    save(ROOT/data['overview'],image.convert('RGB'))
    return image


def build():
    recipe=read_json(AREA/'house.json');data=read_json(TOWN)
    entity,frames,position,entry,width=exterior(recipe)
    data['entities']=[e for e in data['entities'] if e['id']!=recipe['id']]+[entity]
    extend_paths(data,recipe)
    spawn=interior(recipe,data,entry)
    door=portal(recipe['id'],entry,'north',ROOM.relative_to(ROOT).as_posix(),spawn,'courtyard',frames,position,recipe['id'],width)
    data['doors']=[d for d in data['doors'] if d['id']!=recipe['id']]+[door]
    data['interior_scenes'][recipe['id']]=ROOM.relative_to(ROOT).as_posix()
    data['landmarks']=[p for p in data['landmarks'] if p['id']!=recipe['id']]+[
        {'id':recipe['id'],'name':recipe['name'],'position':recipe['landmark_position']}]
    data['destinations'][recipe['id']]=recipe['approach']
    addition=(AREA/'house.json').relative_to(ROOT).as_posix()
    data['layout_additions']=list(dict.fromkeys(data.get('layout_additions',[])+[addition]))
    image=overview(data);write_json(TOWN,data)
    print("Added Liam's wide cottage, path, ten exterior doors and separate 16x10 family interior.")
    return image


if __name__=='__main__':build()
