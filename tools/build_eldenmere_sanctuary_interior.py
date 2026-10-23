"""Build a story-led sanctuary interior review from retained art and approved kits."""
from pathlib import Path
import re
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba
from build_eldenmere_foliage import nearest
from build_eldenmere_cottage_hearth import mix
import build_eldenmere_cottage_layouts as layouts
import build_eldenmere_town as town
import build_eldenmere_sanctuary_charm as charm

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary_interior'
OUTPUT=ROOT/'assets/terrain/eldenmere/sanctuary_interior'
TERRAIN=OUTPUT.parent
INTERIOR=TERRAIN/'cottage_interior'
STORY=ROOT/'docs/narrative/game_01/CH01_MQ01.md'
PACK_META={'cottage_furniture':'furniture.json','cottage_storage':'storage.json','cottage_kitchen':'kitchen.json'}


def save(path,image):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)


def palette():
    p=read_json(TERRAIN/'cottage/palette.json')['materials']
    p.update(outline={'base':'#45382d'},sage={'shadow':'#566b50','base':'#7b9065','light':'#a1ae83'},
             mauve={'shadow':'#796c88','base':'#a08caf','light':'#bca5c6'},
             bronze=read_json(TERRAIN/'sanctuary/palette.json')['materials']['bronze'])
    return p


def export_props(recipe):
    p=palette();ramps={k:[rgba(v) for v in ramp.values()] for k,ramp in p.items()}
    sources={k:town.opened(SOURCE/v) for k,v in recipe['sources'].items()};props={}
    for spec in recipe['props']:
        sample=sources[spec['source']].crop(spec['crop']).resize(tuple(spec['size']),Image.Resampling.NEAREST)
        image=Image.new('RGBA',sample.size)
        for y in range(image.height):
            for x in range(image.width):
                r,g,b,a=sample.getpixel((x,y))
                if a<128:continue
                if max(r,g,b)<80:ramp=ramps['outline']
                elif spec['material']=='iron':ramp=ramps['iron']+ramps['wood'] if r>g+12 else ramps['iron']
                elif g>r+3 and g>b+7:ramp=ramps['sage']
                elif b>g+4 and r>g+5:ramp=ramps['mauve']
                elif b>r+3 and g>r+3:ramp=ramps['glass']+ramps['iron']
                elif r>150 and g>130 and b>100 and r-g<55 and g-b<70:ramp=ramps['plaster']
                elif spec['id']=='medicine_tray' and x<10 and y<13:ramp=ramps['bronze']+ramps['wood']
                elif spec['material']=='textile':ramp=ramps['sage']+ramps['plaster']+ramps['outline']
                elif max(r,g,b)-min(r,g,b)<20:ramp=ramps['iron']+ramps['glass']
                else:ramp=ramps['wood']+ramps['dirt']
                image.putpixel((x,y),nearest((r,g,b),ramps['outline']+ramp))
        props[spec['id']]=image
        save(SOURCE/f"parts/{spec['id']}_native.png",image);save(OUTPUT/f"props/{spec['id']}.png",image)
    # This small existing puff supplies the steam glyph; all source pixels are retained.
    glyph=town.opened(TERRAIN/'cottage/smoke/frame_01.png').crop((88,45,93,50))
    save(SOURCE/'parts/steam_glyph.png',glyph);save(OUTPUT/'props/steam_glyph.png',glyph)
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':p})
    return props,glyph


def resolve(record,recipe):
    pack=record['pack'];name=record['sprite'];floor=None
    if pack in PACK_META:
        meta=read_json(TERRAIN/pack/PACK_META[pack]);spec=next(s for s in meta['sprites'] if s['id']==name)
        path=TERRAIN/pack/spec['image'];floor=spec.get('floor_rect')
    elif pack=='sanctuary_charm':
        path=TERRAIN/pack/f'props/{name}.png'
        floor=[4,20,40,10] if name=='bench' else None
    else:
        spec=next(s for s in recipe['props'] if s['id']==name);path=OUTPUT/f'props/{name}.png'
        floor=spec.get('floor_rect')
    if 'parent' in record:floor=None
    x,y=record['position'];image=town.opened(path)
    return {**record,'image_from_repo_root':str(path.relative_to(ROOT)),'frame_size':list(image.size),
            'floor_rect':None if floor is None else [x+floor[0],y+floor[1],*floor[2:]],
            'sort_y':0 if floor is None else y+floor[1]+floor[3]}


def approved_inspections():
    text=STORY.read_text();section=text.split('**Optional inspect lines:**',1)[1].split('**Exit:**',1)[0]
    return dict(re.findall(r'^- (.*?) — Caelen: "(.*?)"$',section,re.M))


def room_shell(room):
    layout={'floor_tiles':room['floor_tiles'],'supports':room['supports'],
            'window_positions':room['windows'],'partition':None}
    floor,walls,fixtures,partition,structure=layouts.shell(layout,room['entry'])
    # Widen the hall's threshold using exact approved stone slices, without rescaling.
    ex,ey,ew,eh=room['entry'];walls.paste((0,0,0,0),(ex,ey,ex+ew,ey+eh))
    threshold=town.opened(INTERIOR/'tiles/entry_threshold.png')
    for offset in range(0,ew,24):walls.alpha_composite(threshold.crop((0,0,min(24,ew-offset),8)),(ex+offset,ey))
    for p in room['portals']:
        if p['side']=='north':fixtures.alpha_composite(town.opened(INTERIOR/'parts/door.png'),tuple(p['door_position']))
    structure=Image.new('RGBA',floor.size,'#24302d')
    for layer in (floor,walls,fixtures):structure.alpha_composite(layer)
    return floor,walls,fixtures,structure


def light_masks(room,floor):
    base=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_interior/recipe.json')
    glass={rgba(c) for c in base['palette']['glass'].values()};window=town.opened(INTERIOR/'parts/window.png')
    mask=Image.new('L',window.size);mask.putdata([255 if p in glass else 0 for p in window.get_flattened_data()])
    projection=mask.resize((30,24),Image.Resampling.NEAREST);day=Image.new('L',floor.size);glow=day.copy()
    for wx,wy in room['windows']:
        for y in range(24):
            for x in range(30):
                px,py=wx+6+x+y//3,78+y
                if projection.getpixel((x,y)) and floor.getpixel((px,py))[3]:day.putpixel((px,py),255)
    if 'hearth_position' in room:
        hx,hy=room['hearth_position']
        for y in range(hy+65,hy+86):
            for x in range(hx+2,hx+48):
                distance=((x+.5-(hx+25))/23)**2+((y+.5-(hy+75.5))/10.5)**2
                if distance<=1 and floor.getpixel((x,y))[3]:glow.putpixel((x,y),255 if distance<=.45 else 128)
    return day,glow


def steam_frames(room,glyph,size):
    frames=[];ox,oy=room['steam_origin']
    for phase in range(6):
        image=Image.new('RGBA',size)
        for particle in (0,3):
            age=(phase+particle)%6;image.alpha_composite(glyph,(ox-2+age//3,oy-2-age))
        save(OUTPUT/f"{room['id']}/steam/frame_{phase+1:02}.png",image);frames.append(image)
    return frames


def encode_review(path,template,panels,positions,scale,duration):
    """Encode exact native palette indices before integer enlargement."""
    colors=sorted(set(template.get_flattened_data()).union(*(set(im.get_flattened_data()) for frames in panels for im in frames)))
    assert len(colors)<=256,f'{path.name}: {len(colors)} colors would lose pixel values'
    lookup={c:i for i,c in enumerate(colors)};palette=[v for c in colors for v in c]+[0]*(768-len(colors)*3)
    def indexed(im):
        p=Image.frombytes('P',im.size,bytes(lookup[c] for c in im.get_flattened_data()));p.putpalette(palette);return p
    shell=indexed(template);encoded=[]
    for tick in range(len(panels[0])):
        image=shell.copy()
        for frames,pos in zip(panels,positions,strict=True):
            native=frames[tick];image.paste(indexed(native).resize((native.width*scale,native.height*scale),Image.Resampling.NEAREST),pos)
        encoded.append(image)
    encoded[0].save(path,save_all=True,append_images=encoded[1:],duration=duration,loop=0,disposal=1,optimize=False)
    save(path.with_suffix('.png'),template)


def build_room(recipe,room,glyph,inspections):
    directory=OUTPUT/room['id'];directory.mkdir(parents=True,exist_ok=True)
    floor,walls,fixtures,structure=room_shell(room);objects=[resolve(r,recipe) for r in room['objects']]
    by_id={r['id']:r for r in objects}
    for r in objects:
        if 'parent' in r:
            parent=by_id[r['parent']];r.update(sort_y=parent['sort_y'],access=parent['access'])
        if r.get('inspect_key'):r['approved_inspect_text']=inspections[r['inspect_key']]
    if 'hearth_position' in room:
        hx,hy=room['hearth_position'];objects.append({'id':'hearth','position':[hx,hy],'frame_size':[48,72],
            'floor_rect':[hx+2,hy+48,44,20],'access':[hx+24,hy+86],'sort_y':hy+68,
            'image_from_repo_root':'assets/terrain/eldenmere/cottage_hearth/frames/frame_01.png'})
    floor_rect=[24,72,room['floor_tiles'][0]*24,room['floor_tiles'][1]*24]
    checks=[r for r in objects if r.get('access')]
    checks+=[{'id':'portal_'+p['id'],'access':p['access'],'floor_rect':None} for p in room['portals']]
    checks+=[{'id':'spawn_'+p['id'],'access':p['spawn'],'floor_rect':None} for p in room['portals']]
    checks+=[{'id':'hero','access':room['hero_foot'],'floor_rect':None}]
    for anchor in room['story_anchors']:
        if anchor.get('access'):checks.append({'id':anchor['id'],'access':anchor['access'],'floor_rect':None})
    nav_entry=[room['entry'][0]+room['entry'][2]//2-12,room['entry'][1],24,8]
    blocked,centres,reached=layouts.navigation(structure.size,floor_rect,checks,None,nav_entry,recipe['actor_probe_size'])
    day,glow=light_masks(room,floor)
    for name,image in [('floor',floor),('walls',walls),('fixtures',fixtures),('structure',structure),
                       ('blocking',blocked),('navigable_centres',centres),('daylight_mask',day),('floor_glow_mask',glow)]:save(directory/f'{name}.png',image)
    base=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_interior/recipe.json')
    fire=read_json(ROOT/'assets/source/terrain/eldenmere/cottage_hearth/recipe.json')
    daylight=read_json(INTERIOR/'palette.json')['daylight'];wood=[rgba(c) for c in base['palette']['wood'].values()]
    day_pixels=[(x,y,wood.index(floor.getpixel((x,y)))) for y in range(day.height) for x in range(day.width) if day.getpixel((x,y))]
    glow_pixels=[(x,y,glow.getpixel((x,y))) for y in range(glow.height) for x in range(glow.width) if glow.getpixel((x,y))]
    steam=steam_frames(room,glyph,structure.size) if 'steam_origin' in room else None
    hero=town.opened(ROOT/'assets/characters/caelan/idle_front.png');hx,hy=room['hero_foot'];frames=[];records=[]
    for tick in range(recipe['frame_count']):
        fire_phase=tick%4;day_phase=tick//2%9;strength=base['light_strengths'][day_phase]
        image=structure.copy();lighting=Image.new('RGBA',structure.size)
        for x,y,index in day_pixels:lighting.putpixel((x,y),rgba(list(daylight[strength].values())[index]))
        for x,y,level in glow_pixels:
            lighting.putpixel((x,y),mix(structure.getpixel((x,y)),rgba(fire['glow_color']),fire['glow_strengths'][fire_phase]*(1 if level==255 else .5)))
        image.alpha_composite(lighting);save(directory/f'lighting/frame_{tick+1:02}.png',lighting)
        draws=[]
        for r in objects:
            sprite=town.opened(TERRAIN/f'cottage_hearth/frames/frame_{fire_phase+1:02}.png') if r['id']=='hearth' else town.opened(ROOT/r['image_from_repo_root'])
            draws.append((r['sort_y'],1 if 'parent' in r else 0,sprite,r['position']))
        if steam:
            draws.append((by_id['counter']['sort_y'],2,steam[tick%6],[0,0]))
        draws.append((hy+6,3,hero,[hx-12,hy-30]))
        for _,_,sprite,pos in sorted(draws,key=lambda r:(r[0],r[1])):image.alpha_composite(sprite,tuple(pos))
        native=image.convert('RGB');name=f'scene_frames/frame_{tick+1:02}.png';save(directory/name,native);frames.append(native)
        records.append({'image':name,'duration_ms':recipe['duration_ms'],'fire_phase':fire_phase if 'hearth_position' in room else None,
                        'daylight_phase':day_phase,'steam_phase':tick%6 if steam else None})
    save(directory/'room_native.png',frames[0])
    template=charm.board(frames[0],room['label']+' / sanctuary interior / review',
        f"{room['floor_tiles'][0]} x {room['floor_tiles'][1]} floor / 24px tiles / Caelan for scale / 4x",room['theme'],4)
    encode_review(directory/'room_review.gif',template,[frames],[(0,84)],4,recipe['duration_ms'])
    anchors=[]
    for anchor in room['story_anchors']:
        r={**anchor}
        if r.get('inspect_key'):r['approved_inspect_text']=inspections[r['inspect_key']]
        anchors.append(r)
    write_json(directory/'room.json',{'id':room['id'],'status':recipe['status'],'label':room['label'],'theme':room['theme'],
        'floor_tiles':room['floor_tiles'],'room_size':list(structure.size),'floor_rect':floor_rect,'entry_rect':room['entry'],
        'objects':objects,'portals':room['portals'],'story_anchors':anchors,'hero_foot':room['hero_foot'],'hero_anchor':[12,30],
        'actor_probe_size':recipe['actor_probe_size'],'navigation_start':[room['entry'][0]+room['entry'][2]//2,room['entry'][1]-6],
        'reachable_centres':len(reached),'frames':records,'cycle_duration_ms':10800,'loop':True,'review_scale':4,
        'windows':room['windows'],'hearth_position':room.get('hearth_position'),'steam_origin':room.get('steam_origin'),
        'engine_interactions_implemented':False,'character_sleep_sit_poses_included':False})
    return frames


def connection_plan(recipe):
    image=Image.new('RGB',(1500,660),'#e8edf2');d=ImageDraw.Draw(image);d.fontmode='1'
    d.text((28,18),'SANCTUARY / room connections and story roles',font=town.font(30,True),fill='#243529')
    boxes=[(44,164,444,388),(550,164,950,388),(1056,164,1456,388)]
    for room,bounds in zip(recipe['rooms'],boxes,strict=True):
        d.rounded_rectangle(bounds,radius=14,fill='#d3c6a4',outline='#836347',width=3)
        x,y,_,_=bounds;d.text((x+20,y+20),room['label'].replace('Shared hall and reading nook','Shared hall').replace('Communal kitchen and dining','Kitchen / dining'),font=town.font(24,True),fill='#243529')
        d.text((x+20,y+64),f"{room['floor_tiles'][0]} x {room['floor_tiles'][1]} floor tiles",font=town.font(21),fill='#53696e')
    for left,right in [(444,550),(950,1056)]:
        d.line((left,276,right,276),fill='#53696e',width=4)
        d.polygon([(left,276),(left+12,268),(left+12,284)],fill='#53696e');d.polygon([(right,276),(right-12,268),(right-12,284)],fill='#53696e')
    notes=[['Family drawing / books / notes','Bed, wardrobe and repaired belongings'],['Quiet reading / shared mending','Closed records / room access'],['Three breakfast settings','Medicine / food and oil / care supplies']]
    for bounds,lines in zip(boxes,notes,strict=True):
        for i,line in enumerate(lines):d.text((bounds[0]+20,286+i*32),line,font=town.font(18),fill='#45382d')
    d.line((750,388,750,468),fill='#53696e',width=4);d.rounded_rectangle((570,468,930,550),radius=12,fill='#85a16a',outline='#4f7851',width=3)
    d.text((622,492),'Sanctuary courtyard',font=town.font(25,True),fill='#243529')
    d.text((28,602),'Separate expanded room maps. Door links and landing spaces are planned; game transfers follow integration.',font=town.font(21),fill='#53696e')
    save(OUTPUT/'connections_review.png',image)


def build():
    recipe=read_json(SOURCE/'recipe.json');props,glyph=export_props(recipe);inspections=approved_inspections()
    rendered=[build_room(recipe,room,glyph,inspections) for room in recipe['rooms']]
    scale=2;gap=24;width=sum(frames[0].width*scale for frames in rendered)+gap*4;height=912
    board=Image.new('RGB',(width,height),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
    d.text((24,14),'ELDENMERE / sanctuary interiors / review',font=town.font(29,True),fill='#243529')
    d.text((24,56),'Three separate room maps at the same 2x scale / each view uses Caelan as a scale reference',font=town.font(21),fill='#53696e')
    positions=[];columns=[];x=gap
    for room,frames in zip(recipe['rooms'],rendered,strict=True):
        d.text((x,98),room['label'],font=town.font(23,True),fill='#243529');positions.append((x,136))
        board.paste(frames[0].resize((frames[0].width*2,frames[0].height*2),Image.Resampling.NEAREST),(x,136))
        columns.append({'room':room['id'],'rect':[x,136,frames[0].width*2,frames[0].height*2]})
        d.text((x,824),room['theme'],font=town.font(17),fill='#53696e');x+=frames[0].width*2+gap
    d.text((24,868),'Bedroom <-> shared hall <-> kitchen/dining; hall leads to courtyard / sunlight 5.4s / fire 1.2s / kettle steam 1.8s',font=town.font(20),fill='#53696e')
    encode_review(OUTPUT/'interiors_review.gif',board,rendered,positions,scale,recipe['duration_ms'])
    connection_plan(recipe)
    write_json(OUTPUT/'interiors.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'character_frame_size':[24,36],'rooms':[{'id':r['id'],'label':r['label'],'floor_tiles':r['floor_tiles'],'room':f"{r['id']}/room.json"} for r in recipe['rooms']],
        'props':recipe['props'],'links':recipe['links'],'review_columns':columns,'comparison_scale':2,'individual_scale':4,
        'cycle_duration_ms':10800,'duration_ms':300,'frame_count':36,'loop':True,
        'narrative_reference':'docs/narrative/game_01/CH01_MQ01.md','narrative_files_modified':False,
        'cast_designs_added':False,'later_revelations_displayed':False,'engine_transfers_implemented':False,
        'source_recipe':'../../../source/terrain/eldenmere/sanctuary_interior/recipe.json'})
    print(f"Built sanctuary bedroom 10x10, hall 12x10 and kitchen/dining 16x10; {len(recipe['props'])} story props and synchronized 10.8s reviews.")


if __name__=='__main__':build()
