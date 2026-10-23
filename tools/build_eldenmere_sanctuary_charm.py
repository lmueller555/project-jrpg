"""Add source-derived garden props and separate sanctuary animation layers for review."""
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged
from build_eldenmere_foliage import nearest
from build_eldenmere_blockout import geometry
import build_eldenmere_town as town

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/eldenmere/sanctuary_charm'
OUTPUT = ROOT/'assets/terrain/eldenmere/sanctuary_charm'
TERRAIN = ROOT/'assets/terrain/eldenmere'
BASE = ROOT/'assets/maps/eldenmere/terrain_foundation'


def save(path, image):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def exact_gif(path, images, durations, loop=0):
    """Encode exact RGB colors, without Pillow's approximate palette matching."""
    colors = sorted(set().union(*(set(im.get_flattened_data()) for im in images)))
    assert len(colors) <= 256, f'{len(colors)} colors would lose native pixel values'
    lookup = {c: i for i, c in enumerate(colors)}
    palette = [channel for c in colors for channel in c] + [0]*(768-len(colors)*3)
    frames = []
    for im in images:
        p = Image.frombytes('P', im.size, bytes(lookup[c] for c in im.get_flattened_data()))
        p.putpalette(palette); frames.append(p)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=loop, disposal=1, optimize=False)


def native_props(recipe):
    materials = read_json(TERRAIN/'sanctuary/palette.json')['materials']
    leaves = read_json(TERRAIN/'foliage/palette.json')['materials']['leaves']
    colors = {k: [rgba(v) for v in ramp.values()] for k, ramp in materials.items()}
    colors['leaves'] = [rgba(v) for v in leaves.values()]
    concept = town.opened(SOURCE/recipe['source']); props = {}
    for spec in recipe['props']:
        sample = concept.crop(spec['crop']).resize(tuple(spec['size']), Image.Resampling.NEAREST)
        image = Image.new('RGBA', sample.size)
        for y in range(image.height):
            for x in range(image.width):
                r, g, b, a = sample.getpixel((x, y))
                if a < recipe['alpha_threshold']: continue
                if spec['id'] == 'flagstones': ramp = colors['stone']
                elif g > r+2 and g > b+8: ramp = colors['leaves']
                elif spec['id'] == 'provision_basket' and min(r, g, b)>145 and max(r,g,b)-min(r,g,b)<60:
                    ramp = colors['plaster'] + colors['lamplight']
                else: ramp = colors['outline'] + colors['wood']
                image.putpixel((x,y), nearest((r,g,b), ramp))
        props[spec['id']] = image
        save(SOURCE/'parts'/f"{spec['id']}_native.png", image)
        save(OUTPUT/'props'/f"{spec['id']}.png", image)
    write_json(OUTPUT/'palette.json', {'materials': {**materials, 'leaves': leaves}})
    return props, colors


def plant_layers(native, kind, colors):
    """Keep containers/stems fixed; move only sampled, classified leaf pixels."""
    fixed = native.copy(); leaf = Image.new('RGBA', native.size)
    leaves = set(colors['leaves'])
    for y in range(native.height):
        for x in range(native.width):
            p = native.getpixel((x,y))
            if p not in leaves: continue
            if kind == 'herb_planter' and y >= 12: continue
            # Inset column makes room for the one-pixel eastward movement.
            if x >= native.width-1: continue
            leaf.putpixel((x,y),p)
            fixed.putpixel((x,y),(0,0,0,0))
    save(OUTPUT/'props'/f'{kind}_fixed.png',fixed)
    save(OUTPUT/'props'/f'{kind}_leaves.png',leaf)
    frames=[]
    for phase, dx in enumerate(read_json(SOURCE/'recipe.json')['wind_offsets']):
        image=fixed.copy();image.alpha_composite(leaf,(dx,0))
        # Woody stems and the entire planter box retain the exact rest pixels.
        for y in range(native.height):
            for x in range(native.width):
                p=native.getpixel((x,y))
                if p[3] and p not in leaves: image.putpixel((x,y),p)
        save(OUTPUT/f'props/{kind}_frames/frame_{phase+1:02}.png',image);frames.append(image)
    assert frames[0].tobytes()==native.tobytes()
    return frames


def building_layers(recipe):
    original=town.opened(TERRAIN/'sanctuary/closed.png')
    structure=original.copy();rect=recipe['lantern_rect'];x,y,w,h=rect
    body=original.crop(town.box(rect))
    # The copied wall patch is restored by the rest pose, and leaves the attachment fixed.
    structure.paste(rgba('#e1d6bc'),town.box(rect))
    warm=body.copy();px,py,pw,ph=recipe['lantern_pane']
    for yy in range(py,py+ph):
        for xx in range(px,px+pw):
            if original.getpixel((xx,yy))==rgba('#e1d6bc'):
                warm.putpixel((xx-x,yy-y),rgba('#f5d99a'))
    save(OUTPUT/'layers/structure.png',structure)
    frames=[];lit_frames=[]
    for phase,dx in enumerate(recipe['lantern_offsets']):
        day=Image.new('RGBA',original.size);lit=day.copy()
        day.alpha_composite(body,(x+dx,y));lit.alpha_composite(warm,(x+dx,y))
        save(OUTPUT/f'layers/lantern/frame_{phase+1:02}.png',day)
        save(OUTPUT/f'layers/lantern_lit/frame_{phase+1:02}.png',lit)
        frames.append(day);lit_frames.append(lit)
    rest=structure.copy();rest.alpha_composite(frames[0])
    assert rest.tobytes()==original.tobytes(),'Rest lantern must restore the exact original exterior'
    smoke=[];ox,oy=recipe['smoke_origin']
    for phase in range(18):
        layer=Image.new('RGBA',original.size)
        # Reuse the approved eastward smoke, whose original emission point is (90,47).
        layer.alpha_composite(town.opened(TERRAIN/f'cottage/smoke/frame_{phase+1:02}.png'),(ox-90,oy-47))
        save(OUTPUT/f'layers/smoke/frame_{phase+1:02}.png',layer);smoke.append(layer)
    bell_mask=Image.new('L',original.size);ImageDraw.Draw(bell_mask).polygon(recipe['bell_polygon'],fill=255)
    bell=Image.new('RGBA',original.size);bell.paste(original,(0,0),bell_mask)
    no_bell=original.copy();no_bell.paste((0,0,0,0),(0,0),bell_mask)
    save(OUTPUT/'layers/bell_fixed_structure.png',no_bell)
    save(OUTPUT/'layers/bell_rest.png',bell)
    bells=[]
    for phase,tilt in enumerate(recipe['bell_offsets']):
        layer=Image.new('RGBA',original.size)
        for yy in range(60,76):
            dx=round(tilt*(yy-59)/16)
            layer.alpha_composite(bell.crop((0,yy,216,yy+1)),(dx,yy))
        save(OUTPUT/f'layers/bell_cue/frame_{phase+1:02}.png',layer)
        frame=no_bell.copy();frame.alpha_composite(layer);bells.append(frame)
    assert bells[0].tobytes()==original.tobytes(),'Rest bell must reconstruct the approved exterior'
    return structure,frames,lit_frames,smoke,bells


def vegetation(recipe):
    result=[]
    for spec in recipe['foliage']:
        path=TERRAIN/spec['pack']
        meta=read_json(path/('foliage.json' if spec['pack'].startswith('foliage/') else 'plant.json'))
        frames=[town.opened(path/r['image']) for r in meta['wind']['frames']]
        result.append({**spec,'frames':frames,'sort_y':spec['position'][1]+frames[0].height})
    return result


def planning_access(recipe):
    blocked=town.opened(BASE/'navigation/blocking.png').convert('L')
    allowed=town.opened(BASE/'navigation/allowed_routes.png').convert('L')
    blockers=[]
    for p in recipe['props']:
        if 'ground_rect' in p:
            x,y=p['position'];gx,gy,w,h=p['ground_rect']
            blockers.append({'id':p['id'],'rect':[x+gx,y+gy,w,h]})
    blockers.extend({'id':p['id'],'rect':p['blocker']} for p in recipe['foliage'] if 'blocker' in p)
    for p in blockers:blocked.paste(255,town.box(p['rect']))
    # Independent local flood fill uses the same full-width actor probe as the town plan.
    free=set()
    for y in range(288,420,2):
        for x in range(228,494,2):
            if allowed.getpixel((x,y)) and not blocked.crop((x-12,y-6,x+12,y+6)).getbbox():free.add((x,y))
    start=(384,312);q=deque([start]);reached={start}
    while q:
        x,y=q.popleft()
        for v in ((x+2,y),(x-2,y),(x,y+2),(x,y-2)):
            if v in free and v not in reached:reached.add(v);q.append(v)
    destinations={'threshold':recipe['hero_foot'],'stair_landing':[384,348],
                  'below_stairs':[384,402],'conversation_west':[344,312],
                  'conversation_east':[434,324],'bench_approach':[290,342]}
    for name,p in destinations.items():assert tuple(p) in reached,f'Blocked full-width approach: {name}'
    save(OUTPUT/'navigation/blocking.png',blocked)
    write_json(OUTPUT/'navigation/access.json',{'blockers':blockers,'probe':[24,12],
        'grid_step':2,'start':list(start),'destinations':destinations,'reachable_centres':len(reached),
        'engine_collision_implemented':False})


def board(native,title,subtitle,footer,scale=4):
    image=Image.new('RGB',(native.width*scale,native.height*scale+112),'#e8edf2')
    d=ImageDraw.Draw(image);d.fontmode='1'
    d.text((24,14),title,font=town.font(26,True),fill='#243529')
    d.text((24,52),subtitle,font=town.font(20),fill='#53696e')
    image.paste(enlarged(native.convert('RGB'),scale),(0,84))
    d.text((24,image.height-24),footer,font=town.font(18),fill='#53696e')
    return image


def build():
    recipe=read_json(SOURCE/'recipe.json');props,colors=native_props(recipe)
    plants={kind:plant_layers(props[kind],kind,colors) for kind in ('herb_planter','corner_vine')}
    structure,lantern,lit_lantern,smoke,bells=building_layers(recipe)
    vegetation_assets=vegetation(recipe);planning_access(recipe)
    plan=read_json(BASE/'adapted_plan.json');geo=geometry(plan)
    foundation=read_json(ROOT/'assets/source/maps/eldenmere/terrain_foundation/recipe.json')
    buildings=town.building_assets(foundation,plan)
    sanctuary=next(b for b in buildings if b['id']=='sanctuary')
    sanctuary.update(position=recipe['building_position'],prefab_size=[216,216],placeholder=False)
    building_frames=[];lit_building_frames=[]
    for tick in range(54):
        image=structure.copy();image.alpha_composite(lantern[tick%18]);image.alpha_composite(smoke[tick%18])
        lit=structure.copy();lit.alpha_composite(lit_lantern[tick%18]);lit.alpha_composite(smoke[tick%18])
        phase=tick//3%9
        for spec in recipe['props']:
            if spec['id'] not in plants:continue
            for position in spec.get('positions',[spec.get('position')]):
                point=tuple(a-b for a,b in zip(position,recipe['building_position']))
                image.alpha_composite(plants[spec['id']][phase],point)
                lit.alpha_composite(plants[spec['id']][phase],point)
        building_frames.append(image);lit_building_frames.append(lit)
    sanctuary['frames']=building_frames
    grass=town.opened(BASE/'layers/grass.png');base=grass.copy()
    base.alpha_composite(town.opened(BASE/'layers/paths.png'))
    # Walkable flagstones are below buildings, garden props and actors.
    stones=next(p for p in recipe['props'] if p['id']=='flagstones')
    base.alpha_composite(props['flagstones'],tuple(stones['position']))
    masonry=town.opened(BASE/'layers/masonry.png');water,tiles=town.stream_tiles(geo)
    channels=town.channels(plan,geo);bridges=town.bridge_assets(plan)
    scene_frames=[];records=[];warm_crop=None
    for tick in range(54):
        environment=town.render_environment(tick,base,grass,masonry,water,tiles,channels,buildings,bridges)
        ground_items=[]
        for spec in recipe['props']:
            if spec['id'] in ('bench','provision_basket'):
                ground_items.append({**spec,'image':props[spec['id']],'sort_y':spec['position'][1]+spec['size'][1]})
        for spec in vegetation_assets:
            phase=(tick//3+spec['phase_offset'])%9
            ground_items.append({**spec,'image':spec['frames'][phase]})
        for spec in sorted(ground_items,key=lambda r:r['sort_y']):
            environment.alpha_composite(spec['image'],tuple(spec['position']))
        native=town.with_actor(environment,bridges,recipe['hero_foot'])
        crop=native.crop(town.box(recipe['review_crop']))
        name=f'scene_frames/frame_{tick+1:02}.png';save(OUTPUT/name,crop)
        scene_frames.append(crop);records.append({'image':name,'duration_ms':200,
          'smoke_phase':tick%18,'wind_phase':tick//3%9,'lantern_offset':recipe['lantern_offsets'][tick%18]})
        if tick==0:
            overview=town.with_actor(environment,bridges,foundation['main_hero_foot'])
            save(OUTPUT/'town_native.png',overview)
            save(OUTPUT/'town_review.png',board(overview,'ELDENMERE / sanctuary garden / review',
                'New garden at the sanctuary; existing town terrain and buildings reused.',
                'Art placement review / native 24px terrain and 24 x 36 character / 2x',2))
            # A separate warm-lantern art variant keeps the daylight ambient loop unlit.
            warm=environment.copy();warm.alpha_composite(lit_building_frames[0],tuple(recipe['building_position']))
            warm=town.with_actor(warm,bridges,recipe['hero_foot'])
            warm_crop=warm.crop((340,224,420,288))
            day_crop=native.crop((340,224,420,288))
    title='ELDENMERE / sanctuary charm / review'
    subtitle='Shaded bench, kitchen herbs and provision basket / Caelan for scale / 4x'
    footer='Eastward breeze 5.4s / smoke 3.6s / shared loop 10.8s / ambient bell stays still'
    boards=[board(im,title,subtitle,footer) for im in scene_frames]
    save(OUTPUT/'sanctuary_review.png',boards[0])
    exact_gif(OUTPUT/'sanctuary_review.gif',boards,200)
    # Compare the lantern inserts separately, without pretending to implement time of day.
    pair=Image.new('RGB',(176,80),'#c5c2b4');pair.paste(day_crop,(4,12));pair.paste(warm_crop,(92,12))
    save(OUTPUT/'lantern_variants.png',board(pair,'Entrance lantern / unlit and warm inserts',
        'Daylight insert (left) / optional warm pane (right)',
        'Separate art variants; time-of-day lighting is not implemented.',8))
    bell_boards=[]
    for image in bells:
        cell=Image.new('RGBA',(64,88),'#70935a')
        cell.alpha_composite(image,(-18,-12))
        bell_boards.append(board(cell.convert('RGB'),'Sanctuary bell / event cue',
            'Brief swing; normally still','One-shot cue; review repeats after a pause.',8))
    exact_gif(OUTPUT/'bell_cue.gif',bell_boards,[100]*8+[1000])
    write_json(OUTPUT/'charm.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
      'building_position':recipe['building_position'],'building_frame_size':[216,216],
      'base_sanctuary':'../sanctuary/sanctuary.json','base_town':'assets/maps/eldenmere/terrain_foundation/scene.json',
      'props':recipe['props'],'foliage':recipe['foliage'],'wind':{'direction':'E','cycle_duration_ms':5400,
      'moving_parts':'leaves only','fixed_parts':['containers','roots','stems','bench','basket','tree trunk','ground shadows']},
      'smoke':{'source':'../cottage/smoke','source_origin':[90,47],'origin':recipe['smoke_origin'],'cycle_duration_ms':3600},
      'lantern':{'rect':recipe['lantern_rect'],'bracket_fixed':True,'max_sway_pixels':1,'cycle_duration_ms':3600,
                 'day':'layers/lantern','warm':'layers/lantern_lit','ambient_lit':False},
      'bell':{'ambient':'still','cue':'layers/bell_cue','cue_loop':False,'frame_duration_ms':100,'frame_count':9,
              'poses':recipe['bell_offsets'],'max_swing_pixels':2,'pivot':[47,59]},
      'door':'closed; approved original pixels','cycle_duration_ms':10800,'loop':True,'frames':records,
      'review_crop':recipe['review_crop'],'review_scale':4,'hero_foot':recipe['hero_foot'],
      'planning_navigation':'navigation/access.json','engine_interactions_implemented':False,
      'source_recipe':'../../../source/terrain/eldenmere/sanctuary_charm/recipe.json'})
    print('Built sanctuary garden, 54-frame ambient loop, warm lantern insert and one-shot bell cue.')


if __name__=='__main__':build()
