"""Add the public school locally; preserve existing rooms, NPCs and water routes."""
from pathlib import Path
from PIL import Image
from build_eldenmere_stream import read_json,write_json
from build_eldenmere_terrain import BITS,OFFSETS,normalize_mask
from build_building_interiors import compile_room,room_spawn,portal
from build_liam_family_home import opened,save,overview,rect_box

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'assets/maps/eldenmere/school'
TOWN=ROOT/'assets/maps/eldenmere/playable/map.json'
ROOM=ROOT/'assets/maps/eldenmere/building_interiors/rooms/school/map.json'
TERRAIN=ROOT/'assets/terrain/eldenmere'


def cells(rect):
    x,y,w,h=rect;return {(xx,yy) for xx in range(x,x+w) for yy in range(y,y+h)}


def paths(data,layout):
    from build_eldenmere_blockout import geometry,cells as plan_cells
    plan=read_json(ROOT/'assets/maps/eldenmere/terrain_foundation/adapted_plan.json')
    original=set(geometry(plan)['roads'])
    for space in plan['spaces']:
        if space['kind'] in ('yard','plots','garden'):original.update(plan_cells(space['rect']))
    well=read_json(ROOT/'assets/maps/eldenmere/well_square/layout.json')
    original.update(map(tuple,well['added_dirt_cells']))
    original.update(cells(read_json(ROOT/'assets/maps/eldenmere/liam_house/house.json')['path_rect_tiles']))
    added=set().union(*(cells(rect) for rect in layout['path_rects_tiles']))
    all_dirt=original|added
    affected=added|{(x+dx,y+dy) for x,y in added for dx,dy in OFFSETS.values() if (x+dx,y+dy) in original}
    pack=TERRAIN/'grass_dirt';meta=read_json(pack/'tileset.json')
    lookup={r['mask']:opened(pack/r['image']) for r in meta['tiles']}
    fill=[opened(pack/p) for p in meta['dirt_interiors']['images']]
    grass=opened(ROOT/'assets/maps/eldenmere/terrain_foundation/layers/grass.png')
    patch=Image.new('RGBA',tuple(data['size_pixels']))
    paving=Image.new('RGBA',tuple(data['size_pixels']))
    for position in well['paving_positions']:paving.alpha_composite(opened(ROOT/well['paving_source']),tuple(position))
    for x,y in sorted(affected):
        raw=sum(BITS[name] for name,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in all_dirt)
        mask=normalize_mask(raw);image=fill[(x+2*y)%3] if mask==255 else lookup[mask]
        patch.alpha_composite(image,(x*24,y*24))
    for path in dict.fromkeys(data['ground_frames']):
        image=opened(ROOT/path)
        for x,y in affected:
            box=(x*24,y*24,(x+1)*24,(y+1)*24);image.paste(grass.crop(box),(x*24,y*24))
        image.alpha_composite(patch)
        # Restore existing well-square flagstones only inside repainted cells.
        # This keeps the approved paving and avoids accumulating alpha edges.
        for xx,yy in affected:
            box=(xx*24,yy*24,(xx+1)*24,(yy+1)*24)
            image.alpha_composite(paving.crop(box),(xx*24,yy*24))
        save(ROOT/path,image.convert('RGB'))
    allowed=opened(ROOT/data['navigation_allowed'],'L')
    for x,y in added:allowed.paste(255,(x*24,y*24,(x+1)*24,(y+1)*24))
    data['navigation_allowed']=save(AREA/'allowed_routes.png',allowed)
    save(AREA/'path_overlay.png',patch)


def plant(kind,position,identifier,flowers=False):
    directory=TERRAIN/('grass_flowers' if flowers else 'foliage')/kind
    meta=read_json(directory/('plant.json' if flowers else 'foliage.json'))
    frames=[(directory/f['image']).relative_to(ROOT).as_posix() for f in meta['wind']['frames']]
    x,y=position;fx,fy,fw,fh=meta['ground_rect']
    entity={'id':'school.'+identifier,'position':position,'sort_y':y+fy+fh,'sort_priority':0,
            'frames':frames,'frame_duration_ms':600,'phase_offset':0}
    return entity,None if flowers else [x+fx,y+fy,fw,fh]


def yard(data):
    result=[];solid=[]
    for kind,pos,name,flowers in [('tree',[536,648],'shade_tree',False),
                                ('shrub',[746,718],'east_shrub',False),
                                ('flowers_yellow',[604,734],'west_flowers',True),
                                ('flowers_violet',[726,734],'east_flowers',True)]:
        entity,rect=plant(kind,pos,name,flowers);result.append(entity)
        if rect:solid.append(rect)
    original=next(e for e in data['entities'] if e['id']=='sanctuary.bench')
    result.append({**original,'id':'school.bench','position':[698,742],'sort_y':772})
    solid.append([700,760,48,6])
    return result,solid


def build():
    layout=read_json(AREA/'layout.json');data=read_json(TOWN)
    from build_eldenmere_school_exterior import build as build_exterior
    from build_eldenmere_school_interior import build as build_interior
    build_exterior();build_interior()
    exterior=read_json(TERRAIN/'school/exterior/school.json')
    data['entities']=[e for e in data['entities'] if e['id']!='school' and not e['id'].startswith('school.')]
    paths(data,layout)
    x,y=layout['position'];fx,fy,fw,fh=exterior['ground_rect'];baseline=y+fy+fh
    frames=exterior['frames']
    entity={'id':'school','position':[x,y],'sort_y':baseline,'frames':frames,
            'frame_duration_ms':exterior['frame_duration_ms'],'phase_offset':0}
    data['entities'].append(entity)
    props,blockers=yard(data);data['entities'].extend(props)
    assert blockers==layout['yard_blockers'],(blockers,layout['yard_blockers'])
    blocked=opened(ROOT/data['collision'],'L')
    for rect in [layout['ground_rect'],*blockers]:blocked.paste(255,rect_box(rect))
    save(ROOT/data['collision'],blocked)
    directory=TERRAIN/'school/interior';meta,room,room_blocked=compile_room(directory,'school')
    spawn=room_spawn(meta,room_blocked)
    center=meta['entry_rect'][0]+meta['entry_rect'][2]/2
    room.update(id='school',name='Eldenmere school',spawn=spawn,teacher='liam_mother',
                overview=data['overview'],school_layout=(AREA/'layout.json').relative_to(ROOT).as_posix())
    room['doors']=[portal('courtyard',[center,meta['entry_rect'][1]-6],'south',
                          TOWN.relative_to(ROOT).as_posix(),layout['approach'],'school',width=24)]
    write_json(ROOM,room)
    dx,dy=exterior['door']['position'];width=exterior['door']['size'][0]
    door=portal('school',[x+dx+width/2,baseline+6],'north',ROOM.relative_to(ROOT).as_posix(),spawn,
                'courtyard',exterior['door']['frames'],[x+dx,y+dy],'school',width)
    data['doors']=[d for d in data.get('doors',[]) if d['id']!='school']+[door]
    data['interior_scenes']['school']=ROOM.relative_to(ROOT).as_posix()
    data['landmarks']=[p for p in data['landmarks'] if p['id']!='school']+[
        {'id':'school','name':'Village school','position':layout['approach']}]
    data['destinations']['school']=layout['approach']
    data['layout_additions']=list(dict.fromkeys(data.get('layout_additions',[])+[(AREA/'layout.json').relative_to(ROOT).as_posix()]))
    overview(data);write_json(TOWN,data)
    print('Added school, shaded yard, well-square path and enterable 16x12 classroom.')


if __name__=='__main__':build()
