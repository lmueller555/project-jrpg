"""Compile doorway poses and actor-free furnished rooms from the approved art."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from build_eldenmere_stream import read_json, write_json, rgba
from build_eldenmere_cottage_hearth import mix
from build_eldenmere_cottage_layouts import source_object
import build_eldenmere_town as town

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/eldenmere/building_interiors'
TERRAIN=ROOT/'assets/terrain/eldenmere'
TOWN=ROOT/'assets/maps/eldenmere/playable/map.json'


def save(path,image):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
    return path.relative_to(ROOT).as_posix()


def poses(closed,double=False):
    """Keep the approved frame fixed; hinge existing leaf pixels inward."""
    w,h=closed.size;inset=2 if w>=24 else 1
    x,y,pw,ph=inset,2,w-2*inset,h-3
    panel=closed.crop((x,y,x+pw,y+ph));frames=[closed.copy()]
    dark=rgba(read_json(TERRAIN/'cottage/palette.json')['materials']['glass']['dark'])
    for fraction in (.75,.5,.25,.05):
        frame=closed.copy();frame.paste(dark,(x,y,x+pw,y+ph))
        if double:
            half=pw//2;left=panel.crop((0,0,half,ph));right=panel.crop((half,0,pw,ph))
            a=max(1,round(half*fraction));b=max(1,round((pw-half)*fraction))
            frame.alpha_composite(left.resize((a,ph),Image.Resampling.NEAREST),(x,y))
            frame.alpha_composite(right.resize((b,ph),Image.Resampling.NEAREST),(x+pw-b,y))
        else:
            frame.alpha_composite(panel.resize((max(1,round(pw*fraction)),ph),Image.Resampling.NEAREST),(x,y))
        frames.append(frame)
    return frames


def write_poses(identifier,frames):
    return [save(OUT/f'doors/{identifier}/frame_{i+1:02}.png',image) for i,image in enumerate(frames)]


def portal(identifier,anchor,side,destination,spawn,arrival,frames=(),position=(0,0),host=None,width=20):
    return {'id':identifier,'anchor':anchor,'entry_y':anchor[1],'entry_side':side,
            'entry_half_width':min(10,max(6,width/2)),'open_radius':30,'close_radius':38,
            'frame_duration_ms':100,'frames':list(frames),'position':list(position),'host':host,
            'requires_open':bool(frames),'destination':destination,'spawn':spawn,
            'arrival_facing':'back' if side=='north' else 'front','arrival_door':arrival}


def lighted_ground(directory,metadata,key,custom=False):
    shell=town.opened(directory/'structure.png').copy()
    if custom:
        shell=Image.new('RGBA',shell.size,'#24302d')
        for name in ('floor','walls','fixtures'):shell.alpha_composite(town.opened(directory/f'{name}.png'))
    records=[];seen={}
    if (directory/'lighting/frame_01.png').is_file():
        for tick in range(36):
            image=shell.copy();image.alpha_composite(town.opened(directory/f'lighting/frame_{tick+1:02}.png'))
            records.append(image)
    else:
        base=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_interior/recipe.json')
        fire=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_hearth/recipe.json')
        daylight=read_json(TERRAIN/'cottage_interior/palette.json')['daylight']
        floor=town.opened(directory/'floor.png')
        day=town.opened(directory/'daylight_mask.png').convert('L')
        glow=town.opened(directory/'floor_glow_mask.png').convert('L')
        wood=[rgba(c) for c in base['palette']['wood'].values()]
        day_pixels=[(x,y,wood.index(floor.getpixel((x,y)))) for y in range(day.height) for x in range(day.width) if day.getpixel((x,y))]
        glow_pixels=[(x,y,glow.getpixel((x,y))) for y in range(glow.height) for x in range(glow.width) if glow.getpixel((x,y))]
        for tick in range(36):
            image=shell.copy();strength=base['light_strengths'][tick//2%9]
            for x,y,index in day_pixels:image.putpixel((x,y),rgba(list(daylight[strength].values())[index]))
            for x,y,level in glow_pixels:
                image.putpixel((x,y),mix(image.getpixel((x,y)),rgba(fire['glow_color']),fire['glow_strengths'][tick%4]*(1 if level==255 else .5)))
            records.append(image)
    paths=[]
    for tick,image in enumerate(records):
        digest=sha256(image.tobytes()).digest()
        if digest not in seen:seen[digest]=save(OUT/f'rooms/{key}/ground/frame_{tick+1:02}.png',image.convert('RGB'))
        paths.append(seen[digest])
    return paths,shell


def compile_room(directory,key,custom_objects=None,elira=False):
    meta=read_json(directory/'room.json')
    objects=deepcopy(meta['objects'] if custom_objects is None else custom_objects)
    ground,shell=lighted_ground(directory,meta,key,custom_objects is not None)
    blocked=Image.new('L',shell.size,255);x,y,w,h=meta['floor_rect']
    blocked.paste(0,(x,y,x+w,y+h))
    if meta.get('partition_rect') and custom_objects is None:blocked.paste(255,town.box(meta['partition_rect']))
    entities=[]
    for obj in objects:
        if obj.get('floor_rect'):blocked.paste(255,town.box(obj['floor_rect']))
        if obj['id']=='hearth':frames=[f'assets/terrain/eldenmere/cottage_hearth/frames/frame_{i+1:02}.png' for i in range(4)]
        elif obj['id']=='step_stool':frames=['assets/terrain/eldenmere/elira_interior/sprites/step_stool.png']
        else:frames=[obj['image_from_repo_root']]
        entities.append({'id':obj['id'],'position':obj['position'],'sort_y':obj.get('sort_y',obj['position'][1]+obj['frame_size'][1]),
                         'sort_priority':1 if 'parent' in obj else 0,'frames':frames,'frame_duration_ms':300,'phase_offset':0})
    if elira:
        extra=read_json(TERRAIN/'elira_interior/room.json')
        entities.append({'id':'lantern_shelf','position':extra['shelf_position'],'sort_y':0,
                         'frames':['assets/terrain/eldenmere/elira_interior/sprites/shelf_with_lantern.png'],
                         'frame_duration_ms':300,'phase_offset':0})
    if meta.get('steam_origin'):
        counter=next(o for o in objects if o['id']=='counter')
        entities.append({'id':'kettle_steam','position':[0,0],'sort_y':counter['sort_y'],'sort_priority':2,
                         'frames':[(directory/f'steam/frame_{i+1:02}.png').relative_to(ROOT).as_posix() for i in range(6)],
                         'frame_duration_ms':300,'phase_offset':0})
    collision=save(OUT/f'rooms/{key}/collision.png',blocked)
    return meta,{'size_pixels':list(shell.size),'size_tiles':meta['floor_tiles'],'tile_size':24,'floor_rect':meta['floor_rect'],
                 'player_probe_size':[24,12],'player_draw_anchor':[12,30],
                 'ground_frames':ground,'ground_frame_duration_ms':300,'entities':entities,
                 'collision':collision,'foreground':[],'landmarks':[],'doors':[],'npcs':[],'quests':[],
                 'kind':'interior','destinations':{o['id']:o['access'] for o in objects if o.get('access')},
                 'source_room':(directory/'room.json').relative_to(ROOT).as_posix()},blocked


def room_spawn(meta,blocked):
    x=meta['entry_rect'][0]+meta['entry_rect'][2]//2
    y=meta['entry_rect'][1]-18
    for dy in range(0,48,2):
        point=[x,y-dy]
        if not blocked.crop((x-12,point[1]-6,x+12,point[1]+6)).getbbox():return point
    raise ValueError(f'No safe room arrival: {meta["id"]}')


def custom_objects(kind):
    base=read_json(TERRAIN/f'cottage_layouts/{"standard" if kind=="workshop" else "wide"}/room.json')
    keep={'cupboard','shelf','washbasin','hearth'} if kind=='workshop' else {'cupboard','shelf','pantry','hearth'}
    objects=[deepcopy(o) for o in base['objects'] if o['id'] in keep]
    records=([{'id':'repair_table','pack':'cottage_furniture','sprite':'table','position':[228,156],'access':[252,210]}]
             if kind=='workshop' else [
                 {'id':'sorting_table','pack':'cottage_furniture','sprite':'table','position':[264,180],'access':[288,168]},
                 {'id':'storage','pack':'cottage_kitchen','sprite':'pantry','position':[36,204],'access':[48,262]},
                 {'id':'storage_b','pack':'cottage_storage','sprite':'cupboard','position':[36,84],'access':[60,144]}])
    objects.extend(source_object(r) for r in records)
    if kind=='workshop':
        objects.append({'id':'workbench','position':[72,132],'frame_size':[36,26],
                        'floor_rect':[74,150,32,8],'sort_y':158,
                        'image_from_repo_root':'assets/terrain/eldenmere/workshop/props/workbench.png'})
    return objects


def build():
    town_map=read_json(TOWN);by_id={e['id']:e for e in town_map['entities']}
    source_map=read_json(ROOT/'assets/maps/eldenmere/terrain_foundation/scene.json')
    building_records={b['id']:b for b in source_map['buildings']}
    town_map['doors']=[]
    room_files={key:(OUT/f'rooms/{key}/map.json').relative_to(ROOT).as_posix() for key in
                ['sanctuary_hall','sanctuary_bedroom','sanctuary_dining','halden','elira','venn','home_a','home_b','home_c','mira','mill']}
    sources={};rooms={};blocks={};metas={}
    assignments={'halden':'standard','elira':'compact','venn':'wide','home_a':'standard','home_b':'standard','home_c':'standard'}
    for building,size in assignments.items():
        key='elira' if building=='elira' else size
        if key not in sources:
            directory=TERRAIN/('elira_interior' if building=='elira' else f'cottage_layouts/{size}')
            if building=='elira':
                # Elira uses the compact shell and its approved extra objects.
                meta=read_json(directory/'room.json')
                result=compile_room(TERRAIN/'cottage_layouts/compact',key,meta['objects'],True)
            else:result=compile_room(directory,key)
            sources[key]=result
        meta,data,blocked=sources[key];metas[building]=meta;rooms[building]=deepcopy(data);blocks[building]=blocked
    for key in ['hall','bedroom','dining']:
        meta,data,blocked=compile_room(TERRAIN/f'sanctuary_interior/{key}',f'sanctuary_{key}')
        name=f'sanctuary_{key}';metas[name]=meta;rooms[name]=data;blocks[name]=blocked
    for name,kind,size in [('mira','workshop','standard'),('mill','mill','wide')]:
        meta,data,blocked=compile_room(TERRAIN/f'cottage_layouts/{size}',name,custom_objects(kind))
        metas[name]=meta;rooms[name]=data;blocks[name]=blocked
    labels={'sanctuary_hall':'Sanctuary hall','sanctuary_bedroom':"Caelan's room",'sanctuary_dining':'Sanctuary dining room',
            'halden':"Halden's cottage",'elira':"Elira's cottage",'venn':'Venn family cottage',
            'home_a':'West cottage','home_b':'Village cottage','home_c':'South cottage','mira':"Mira's workshop",'mill':'Watermill workroom'}
    for building in ['sanctuary','mira','mill',*assignments]:
        entity=by_id[building];image=town.opened(ROOT/entity['frames'][0]);position=entity['position']
        record=building_records[building]
        target='sanctuary_hall' if building=='sanctuary' else building
        if building in assignments:
            pack=ROOT/record['pack'];cottage=read_json(pack/'cottage.json')
            dx,dy=cottage['door']['position'];dw,dh=cottage['door']['size'];rect=[dx,dy,dw,dh]
            background=town.opened(pack/'structure.png').crop(town.box(rect));frames=[]
            for f in cottage['door']['opening']['frames']:
                patch=background.copy();patch.alpha_composite(town.opened(pack/f['image']).crop(town.box(rect)));frames.append(patch)
        else:
            rect=({'sanctuary':[118,156,32,42],'mira':[58,131,28,35],'mill':[26,107,18,31]})[building]
            frames=poses(image.crop(town.box(rect)),building=='sanctuary')
        assert frames[0].tobytes()==image.crop(town.box(rect)).tobytes(),building
        paths=write_poses(building,frames)
        x=position[0]+rect[0]+rect[2]/2;entry_y=entity['sort_y']+6
        anchor=[x,entry_y];outside=[x,entry_y+12]
        spawn=([208,294] if building=='sanctuary' else room_spawn(metas[target],blocks[target]))
        town_map['doors'].append(portal(building,anchor,'north',room_files[target],spawn,'courtyard',paths,
                                        [position[0]+rect[0],position[1]+rect[1]],building,rect[2]))
        if building!='sanctuary':
            entry=metas[target]['entry_rect'];centre=entry[0]+entry[2]/2
            rooms[target]['doors']=[portal('courtyard',[centre,entry[1]-6],'south',TOWN.relative_to(ROOT).as_posix(),outside,building,width=entry[2])]
        else:
            hall=rooms[target];meta=metas[target]
            entry=next(p for p in meta['portals'] if p['id']=='courtyard')
            hall['doors'].append(portal('courtyard',[entry['access'][0],meta['floor_rect'][1]+meta['floor_rect'][3]-6],
                                        'south',TOWN.relative_to(ROOT).as_posix(),outside,building,width=32))
        rooms[target]['spawn']=spawn
    for name in ['bedroom','dining']:
        hall=rooms['sanctuary_hall'];spec=next(p for p in metas['sanctuary_hall']['portals'] if p['id']==name)
        x,y=spec['door_position'];door=town.opened(TERRAIN/'cottage_interior/parts/door.png')
        paths=write_poses('sanctuary_'+name,poses(door))
        destination='sanctuary_'+name;spawn=metas[destination]['portals'][0]['spawn']
        hall['doors'].append(portal(name,[spec['access'][0],78],'north',room_files[destination],spawn,'hall',paths,[x,y],width=24))
        rooms[destination]['spawn']=spawn
        entry=metas[destination]['entry_rect']
        rooms[destination]['doors']=[portal('hall',[entry[0]+entry[2]/2,entry[1]-6],'south',room_files['sanctuary_hall'],spec['spawn'],name,width=24)]
    for key,data in rooms.items():
        data.update(id=key,name=labels[key],overview=town_map['overview'])
        path=ROOT/room_files[key];path.parent.mkdir(parents=True,exist_ok=True)
        write_json(path,data)
    town_map['interior_scenes']=room_files
    write_json(TOWN,town_map)
    print(f'Compiled {len(town_map["doors"])} base exterior doors, {len(rooms)} furnished scenes and sanctuary room links.')
    # Apply the household extension after base rooms/doors are rebuilt.
    # The standalone extension also supports local edits without rewriting
    # existing rooms or their persistent NPC assignments.
    if (ROOT/'assets/maps/eldenmere/liam_house/house.json').is_file():
        from build_liam_family_home import build as build_family_home
        build_family_home()
    if (ROOT/'assets/maps/eldenmere/school/layout.json').is_file():
        from build_eldenmere_school import build as build_school
        build_school()


if __name__=='__main__':build()
