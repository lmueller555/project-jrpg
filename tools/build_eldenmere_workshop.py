"""Export Mira's workshop and review it in the approved, animated town."""
from array import array
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import nearest
from build_eldenmere_blockout import geometry, cells
from build_eldenmere_terrain import BITS, OFFSETS, normalize_mask
import build_eldenmere_town as town
import build_eldenmere_sanctuary_charm as charm

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/workshop'
OUTPUT=ROOT/'assets/terrain/eldenmere/workshop'
TERRAIN=OUTPUT.parent
BASE=ROOT/'assets/maps/eldenmere/terrain_foundation'
CHARM=TERRAIN/'sanctuary_charm'


def save(path,image):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)


def materials():
    palette=read_json(TERRAIN/'cottage/palette.json')['materials']
    palette.update(read_json(ROOT/'assets/source/terrain/eldenmere/cottage_variants/recipe.json')['variants'][0]['palette'])
    palette['outline']={'base':'#45382d'}
    return palette


def export_art(recipe):
    palette=materials();ramps={k:[rgba(v) for v in ramp.values()] for k,ramp in palette.items()}
    reference=town.opened(SOURCE/recipe['source']);structure=Image.new('RGBA',tuple(recipe['frame_size']))
    roof_mask=Image.new('L',reference.size);ImageDraw.Draw(roof_mask).polygon(recipe['landmarks']['roof_polygon'],fill=255)
    for band in recipe['bands']:
        l,t,r,b=band['crop'];w,h=band['size'];sample=reference.crop((l,t,r,b)).resize((w,h),Image.Resampling.NEAREST)
        part=Image.new('RGBA',sample.size)
        for y in range(h):
            for x in range(w):
                red,green,blue,alpha=sample.getpixel((x,y))
                if alpha<recipe['alpha_threshold']:continue
                sx=int(l+(x+.5)*(r-l)/w);sy=int(t+(y+.5)*(b-t)/h)
                cl,ct,cr,cb=recipe['landmarks']['chimney']
                if max(red,green,blue)<70:ramp=ramps['outline']
                elif band['id']=='sign_bracket':ramp=ramps['outline']+ramps['iron']
                elif cl<=sx<cr and ct<=sy<cb:ramp=ramps['outline']+ramps['stone']
                elif roof_mask.getpixel((sx,sy)):ramp=ramps['outline']+ramps['roof']
                elif blue>red+2 and green>red+3:ramp=ramps['outline']+ramps['glass']
                elif sy>=865 and red-green<25:ramp=ramps['outline']+ramps['stone']
                elif red>145 and green>125 and blue>95 and red-green<45 and green-blue<65:
                    ramp=ramps['outline']+ramps['plaster']
                else:ramp=ramps['outline']+ramps['wood']
                part.putpixel((x,y),nearest((red,green,blue),ramp))
        save(SOURCE/f"parts/{band['id']}.png",part)
        structure.alpha_composite(part,tuple(band['position']))
    props={};concept=town.opened(SOURCE/recipe['props_source'])
    for spec in recipe['props']:
        sample=concept.crop(spec['crop']).resize(tuple(spec['size']),Image.Resampling.NEAREST)
        part=Image.new('RGBA',sample.size)
        for y in range(part.height):
            for x in range(part.width):
                red,green,blue,alpha=sample.getpixel((x,y))
                if alpha<recipe['alpha_threshold']:continue
                if max(red,green,blue)<70:ramp=ramps['outline']
                elif max(red,green,blue)-min(red,green,blue)<22 or green>red+2:
                    ramp=ramps['outline']+ramps['iron']
                else:ramp=ramps['outline']+ramps['wood']
                part.putpixel((x,y),nearest((red,green,blue),ramp))
        props[spec['id']]=part;save(SOURCE/f"parts/{spec['id']}_native.png",part)
        save(OUTPUT/f"props/{spec['id']}.png",part)
    position=[a-b for a,b in zip(recipe['ground_position'],recipe['ground_rect'][:2])]
    rack=next(p for p in recipe['props'] if p['id']=='tool_rack')
    structure.alpha_composite(props['tool_rack'],tuple(a-b for a,b in zip(rack['position'],position)))
    save(OUTPUT/'structure.png',structure)
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':palette})
    return structure,props,position


def animation(recipe,structure,props):
    smoke=[];sign=[];sx,sy=recipe['sign_position'];ox,oy=recipe['smoke_origin']
    for phase in range(18):
        layer=Image.new('RGBA',structure.size)
        layer.alpha_composite(town.opened(TERRAIN/f'cottage/smoke/frame_{phase+1:02}.png'),(ox-90,oy-47))
        smoke.append(layer);save(OUTPUT/f'smoke/frame_{phase+1:02}.png',layer)
    plaque=props['cog_sign']
    for phase,tilt in enumerate(recipe['sign_offsets']):
        layer=Image.new('RGBA',structure.size)
        for y in range(plaque.height):
            # The top ring stays attached while the lower sign shifts by at most one pixel.
            dx=round(tilt*y/(plaque.height-1))
            layer.alpha_composite(plaque.crop((0,y,plaque.width,y+1)),(sx+dx,sy+y))
        sign.append(layer);save(OUTPUT/f'sign/frame_{phase+1:02}.png',layer)
    rest=structure.copy();rest.alpha_composite(sign[0]);save(OUTPUT/'closed.png',rest)
    frames=[]
    for tick in range(recipe['frame_count']):
        image=structure.copy();image.alpha_composite(sign[tick//3%9]);image.alpha_composite(smoke[tick%18])
        frames.append(image);save(OUTPUT/f'frames/frame_{tick+1:02}.png',image)
    return frames


def sanctuary_assets():
    """Read approved layers directly; never rebuild or modify the sanctuary pack."""
    recipe=read_json(ROOT/'assets/source/terrain/eldenmere/sanctuary_charm/recipe.json')
    frames=[];structure=town.opened(CHARM/'layers/structure.png')
    for tick in range(54):
        image=structure.copy()
        for kind in ('lantern','smoke'):image.alpha_composite(town.opened(CHARM/f'layers/{kind}/frame_{tick%18+1:02}.png'))
        for spec in recipe['props']:
            if spec['id'] not in ('herb_planter','corner_vine'):continue
            sprite=town.opened(CHARM/f"props/{spec['id']}_frames/frame_{tick//3%9+1:02}.png")
            for pos in spec.get('positions',[spec.get('position')]):
                image.alpha_composite(sprite,tuple(a-b for a,b in zip(pos,recipe['building_position'])))
        frames.append(image)
    items=[]
    for spec in recipe['props']:
        if spec['id'] in ('bench','provision_basket'):
            items.append({**spec,'frames':[town.opened(CHARM/f"props/{spec['id']}.png")],
                          'sort_y':spec['position'][1]+spec['size'][1]})
    items+=charm.vegetation(recipe)
    return recipe,frames,items


def apron(recipe,base,grass):
    existing=read_json(BASE/'scene.json')['ground']['dirt_cells']
    dirt={tuple(r['cell']) for r in existing};added=set(cells(recipe['apron_tiles']))-dirt
    dirt|=added;affected={(x+dx,y+dy) for x,y in added for dx in (-1,0,1) for dy in (-1,0,1)}
    meta=read_json(TERRAIN/'grass_dirt/tileset.json')
    tiles={r['mask']:town.opened(TERRAIN/'grass_dirt'/r['image']) for r in meta['tiles']}
    fills=[town.opened(TERRAIN/'grass_dirt'/p) for p in meta['dirt_interiors']['images']]
    result=base.copy();records=[]
    for x,y in sorted(affected):
        pos=(x*24,y*24);result.paste(grass.crop((pos[0],pos[1],pos[0]+24,pos[1]+24)),pos)
        if (x,y) not in dirt:continue
        raw=sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in dirt)
        mask=normalize_mask(raw);sprite=fills[(x+2*y)%3] if mask==255 else tiles[mask]
        result.alpha_composite(sprite,pos);records.append({'cell':[x,y],'mask':mask})
    return result,{'added_cells':[list(c) for c in sorted(added)],'retiled_cells':records,
                   'changed_tile_bounds':[[x,y] for x,y in sorted(affected)]}


def reachable(blocked,allowed,start):
    w,h=blocked.size;stride=w+1;integral=array('I',[0])*((w+1)*(h+1));pixels=blocked.tobytes()
    for y in range(h):
        total=0;row=(y+1)*stride;previous=y*stride
        for x in range(w):
            total+=bool(pixels[y*w+x]);integral[row+x+1]=integral[previous+x+1]+total
    free=set()
    for y in range(6,h-5,2):
        for x in range(12,w-11,2):
            if not allowed.getpixel((x,y)):continue
            l,r=x-12,x+12;t,b=y-6,y+6
            count=integral[b*stride+r]-integral[t*stride+r]-integral[b*stride+l]+integral[t*stride+l]
            if not count:free.add((x,y))
    reached=set();queue=deque([tuple(start)])
    while queue:
        p=queue.popleft()
        if p in reached or p not in free:continue
        reached.add(p);x,y=p;queue.extend(((x-2,y),(x+2,y),(x,y-2),(x,y+2)))
    return reached


def navigation(recipe):
    blocked=town.opened(CHARM/'navigation/blocking.png').convert('L')
    allowed=town.opened(BASE/'navigation/allowed_routes.png').convert('L');blockers=[]
    for p in recipe['props']:
        if 'ground_rect' not in p:continue
        x,y=p['position'];gx,gy,w,h=p['ground_rect'];r=[x+gx,y+gy,w,h]
        blocked.paste(255,town.box(r));blockers.append({'id':p['id'],'rect':r})
    allowed.paste(255,town.box([v*24 for v in recipe['apron_tiles']]))
    assert not blocked.crop(town.box(recipe['conversation_rect'])).getbbox(),'Conversation space is blocked'
    start=[384,312];reached=reachable(blocked,allowed,start)
    destinations=read_json(BASE/'scene.json')['navigation']['destinations']
    destinations.update(workshop_door=recipe['hero_foot'],workbench=recipe['workbench_approach'],mira_scale=recipe['mira_foot'],
                        conversation_left=[624,456],conversation_right=[648,456],woodland_lane=[720,420])
    for name,p in destinations.items():assert tuple(p) in reached,f'Actor cannot reach {name}: {p}'
    save(OUTPUT/'navigation/blocking.png',blocked);save(OUTPUT/'navigation/allowed_routes.png',allowed)
    mask=Image.new('L',blocked.size)
    for p in reached:mask.putpixel(p,255)
    save(OUTPUT/'navigation/reachable_centres.png',mask)
    write_json(OUTPUT/'navigation/access.json',{'probe_size':[24,12],'grid_step':2,'start':start,
        'blockers':blockers,'destinations':destinations,'reachable_centres':len(reached),
        'conversation_rect':recipe['conversation_rect'],'engine_collision_implemented':False})


def review_gif(path,images,title,subtitle,footer,scale):
    """Encode native pixels first, then enlarge palette indices without color loss."""
    template=charm.board(images[0],title,subtitle,footer,scale)
    colors=sorted(set(template.get_flattened_data()).union(*(set(im.get_flattened_data()) for im in images)))
    assert len(colors)<=256,f'{len(colors)} GIF colors would require approximation'
    lookup={c:i for i,c in enumerate(colors)};palette=[v for c in colors for v in c]+[0]*(768-len(colors)*3)
    def indexed(im):
        p=Image.frombytes('P',im.size,bytes(lookup[c] for c in im.get_flattened_data()));p.putpalette(palette);return p
    shell=indexed(template);frames=[]
    for native in images:
        frame=shell.copy();frame.paste(indexed(native).resize((native.width*scale,native.height*scale),Image.Resampling.NEAREST),(0,84))
        frames.append(frame)
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=200,loop=0,disposal=1,optimize=False)
    save(path.with_suffix('.png'),template)


def build():
    recipe=read_json(SOURCE/'recipe.json');structure,props,position=export_art(recipe)
    frames=animation(recipe,structure,props);navigation(recipe)
    plan=read_json(BASE/'adapted_plan.json');geo=geometry(plan)
    foundation=read_json(ROOT/'assets/source/maps/eldenmere/terrain_foundation/recipe.json')
    buildings=town.building_assets(foundation,plan)
    sanctuary,sanctuary_frames,items=sanctuary_assets()
    next(b for b in buildings if b['id']=='sanctuary').update(position=sanctuary['building_position'],frames=sanctuary_frames,placeholder=False)
    workshop=next(b for b in buildings if b['id']=='mira')
    assert workshop['ground_rect_pixels']==recipe['ground_position']+recipe['ground_rect'][2:]
    workshop.update(position=position,frames=frames,prefab_size=recipe['frame_size'],placeholder=False)
    grass=town.opened(BASE/'layers/grass.png');base=grass.copy();base.alpha_composite(town.opened(BASE/'layers/paths.png'))
    base,apron_meta=apron(recipe,base,grass)
    stones=next(p for p in sanctuary['props'] if p['id']=='flagstones')
    base.alpha_composite(town.opened(CHARM/'props/flagstones.png'),tuple(stones['position']))
    for p in recipe['props']:
        if 'ground_rect' in p:items.append({**p,'frames':[props[p['id']]],'sort_y':p['position'][1]+p['size'][1]})
    for p in recipe['grass']:
        pack=TERRAIN/p['pack'];meta=read_json(pack/'plant.json')
        items.append({**p,'frames':[town.opened(pack/r['image']) for r in meta['wind']['frames']],
                      'sort_y':p['position'][1]+24})
    masonry=town.opened(BASE/'layers/masonry.png');water,tiles=town.stream_tiles(geo)
    channels=town.channels(plan,geo);bridges=town.bridge_assets(plan)
    mira=town.opened(ROOT/'assets/characters/mira/idle_front.png');crops=[];records=[]
    for tick in range(54):
        environment=town.render_environment(tick,base,grass,masonry,water,tiles,channels,buildings,bridges)
        for p in sorted(items,key=lambda p:p['sort_y']):
            phase=(tick//3+p.get('phase_offset',0))%len(p['frames'])
            environment.alpha_composite(p['frames'][phase],tuple(p['position']))
        environment.alpha_composite(mira,(recipe['mira_foot'][0]-12,recipe['mira_foot'][1]-30))
        native=town.with_actor(environment,bridges,recipe['hero_foot'])
        crop=native.crop(town.box(recipe['review_crop']));crops.append(crop)
        name=f'scene_frames/frame_{tick+1:02}.png';save(OUTPUT/name,crop)
        records.append({'image':name,'duration_ms':200,'smoke_phase':tick%18,'sign_phase':tick//3%9})
        if tick==0:
            overview=town.with_actor(environment,bridges,foundation['main_hero_foot'])
            save(OUTPUT/'town_native.png',overview)
            save(OUTPUT/'town_review.png',charm.board(overview,'ELDENMERE / Mira workshop / review',
                'Workshop replaces its reserved placeholder; approved sanctuary and town retained.',
                '24px terrain / native character sprites / exterior art and placement review',2))
    review_gif(OUTPUT/'workshop_review.gif',crops,'ELDENMERE / Mira workshop exterior / review',
        'Terracotta roof, repair bench and cog sign / Caelan and Mira for scale / 4x',
        'Smoke 3.6s / sign and grass 5.4s / shared loop 10.8s / clear approach to upper crossing',recipe['review_scale'])
    cell=Image.new('RGBA',(216,204),'#c5c2b4');cell.alpha_composite(frames[0],(16,0))
    for p in recipe['props']:
        if 'ground_rect' in p:
            cell.alpha_composite(props[p['id']],(p['position'][0]-position[0]+16,p['position'][1]-position[1]))
    cell.alpha_composite(town.opened(ROOT/'assets/characters/caelan/idle_front.png'),(76,160))
    save(OUTPUT/'exterior_review.png',charm.board(cell.convert('RGB'),'Mira workshop / native exterior and yard',
        '120 x 72 ground / 28px doorway / fixed tools and repair parts / 6x',
        'First exterior review; separate workshop interior follows later.',6))
    write_json(OUTPUT/'workshop.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'prefab_size':recipe['frame_size'],'ground_rect':recipe['ground_rect'],'ground_tiles':[5,3],
        'position':position,'ground_position':recipe['ground_position'],'structure':'structure.png','closed':'closed.png',
        'door':{'rect':recipe['door_rect'],'state':'closed','planned_clear_width':28,'animated':False},
        'components':recipe['bands'],'props':recipe['props'],'grass':recipe['grass'],'apron':apron_meta,
        'smoke':{'origin':recipe['smoke_origin'],'source':'../cottage/smoke','source_origin':[90,47],
                 'cycle_duration_ms':3600,'frame_count':18,'frame_duration_ms':200,'direction':'E'},
        'sign':{'position':recipe['sign_position'],'cycle_duration_ms':5400,'frame_count':9,
                'frame_duration_ms':600,'offsets':recipe['sign_offsets'],'max_displacement_pixels':1,
                'bracket_fixed':True,'attachment_ring_fixed':True},
        'cycle_duration_ms':10800,'loop':True,'frames':records,'native_building_frames':'frames',
        'review_crop':recipe['review_crop'],'review_scale':recipe['review_scale'],'hero_foot':recipe['hero_foot'],
        'mira_foot':recipe['mira_foot'],'actor_anchor':[12,30],'planning_navigation':'navigation/access.json',
        'sanctuary_pack':'../sanctuary_charm/charm.json','base_town':'assets/maps/eldenmere/terrain_foundation/scene.json',
        'source_recipe':'../../../source/terrain/eldenmere/workshop/recipe.json','engine_interactions_implemented':False,
        'interior_included':False,'mill_quest_solution_defined':False})
    print('Built Mira workshop, six props, 54-frame review, town overview and full-width route checks.')


if __name__=='__main__':build()
