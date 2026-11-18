"""Compile the approved town and final exteriors into actor-free runtime layers.

This reads the existing art builders' assembly helpers, never their export/build
functions. Running the game does not require Pillow or these tools.
"""
from hashlib import sha256
from io import BytesIO
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

import build_eldenmere_town as town
import build_eldenmere_workshop as workshop
import build_eldenmere_well as well
from build_eldenmere_blockout import geometry
from build_eldenmere_stream import read_json, write_json

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'assets/maps/eldenmere/playable'
BASE=ROOT/'assets/maps/eldenmere/terrain_foundation'
TERRAIN=ROOT/'assets/terrain/eldenmere'
GRASS_SOURCE=ROOT/'assets/source/maps/eldenmere/grass/recipe.json'


def emerald_products():
    """Update only terrain in the fully assembled, checked-in town.

    Later builders add the school, Liam's home and story links to the original
    town compiler. Native coverage masks retain that assembled geometry, rather
    than reconstructing an earlier map and losing those additions.
    """
    from grass_terrain import load_pack, material_images, material_at, remap_legacy_green
    data=read_json(OUTPUT/'map.json');recipe=read_json(GRASS_SOURCE)
    pack=load_pack();materials=material_images(pack);size=tuple(data['size_pixels'])
    if sha256((ROOT/data['collision']).read_bytes()).hexdigest()!=recipe['collision_sha256']:
        raise ValueError('Town navigation changed; review grass coverage before compiling')
    field=Image.new('RGBA',size);family_map=Image.new('RGB',tuple(data['size_tiles']))
    family_names=('lawn','meadow','woodland')
    family_draw=ImageDraw.Draw(family_map)
    family_draw.rectangle((0,0,family_map.width,family_map.height),fill=(family_names.index(recipe['default_family']),0,0))
    for region in recipe['material_regions']:
        family_draw.polygon([tuple(point) for point in region['polygon']],fill=(family_names.index(region['family']),0,0))
    cells=[]
    for y in range(data['size_tiles'][1]):
        row=[]
        for x in range(data['size_tiles'][0]):
            family=family_names[family_map.getpixel((x,y))[0]]
            index,image=material_at(x,y,family,materials,seed=recipe['seed'])
            field.alpha_composite(image,(24*x,24*y));row.append([family,index])
        cells.append(row)
    products={}
    def retain(path,image):
        stream=BytesIO();image.save(stream,format='PNG');products[path]=stream.getvalue()
    masks=[]
    for path,record in zip(data['ground_frames'],recipe['coverage'],strict=True):
        coverage_path=ROOT/record['image']
        if sha256(coverage_path.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Town grass coverage source changed: '+record['image'])
        coverage=Image.open(coverage_path).convert('L')
        if coverage.size!=size:raise ValueError('Grass coverage must match town size')
        masks.append(coverage)
        ground=Image.open(ROOT/path).convert('RGBA')
        ground.paste(field,(0,0),coverage)
        retain(ROOT/path,remap_legacy_green(ground).convert('RGB'))
    entities=[]
    for entity in data['entities']:
        if entity['id'] in recipe['remove_legacy_entities']:continue
        entity=dict(entity)
        if 'flowers' in entity['id']:
            frames=[]
            for path in entity['frames']:
                if path.startswith('assets/terrain/eldenmere/grass_flowers/'):
                    path=path.replace('assets/terrain/eldenmere/grass_flowers/','assets/terrain/grass/flowers/',1)
                else:
                    retain(ROOT/path,remap_legacy_green(Image.open(ROOT/path)))
                frames.append(path)
            entity['frames']=frames
        entities.append(entity)
    data['entities']=entities
    # Full opaque grass coverage avoids dirt, flagstones and water. Collision
    # and visual entity bounds protect buildings, walls, props and approaches.
    coverage=masks[0];collision=Image.open(ROOT/data['collision']).convert('L')
    allowed=Image.open(ROOT/data['navigation_allowed']).convert('L')
    protected=[data['spawn'],*[entry['position'] for entry in data['landmarks']],
               *data['destinations'].values(),*[npc['position'] for npc in data['npcs']]]
    entity_bounds=[]
    for entity in entities:
        w,h=Image.open(ROOT/entity['frames'][0]).size;x,y=entity['position']
        entity_bounds.append((x,y,x+w,y+h))
    def clear(x,y):
        box=(x-12,y-12,x+12,y+6)
        if box[0]<0 or box[1]<0 or box[2]>size[0] or box[3]>size[1]:return False
        if coverage.crop(box).getextrema()!=(255,255):return False
        if collision.crop(box).getbbox() or allowed.crop(box).getbbox():return False
        if any(abs(x-p[0])<recipe['protected_radius'] and abs(y-p[1])<recipe['protected_radius'] for p in protected):return False
        return not any(box[0]<r[2] and box[2]>r[0] and box[1]<r[3] and box[3]>r[1] for r in entity_bounds)
    instances=[];variants=tuple(pack['tall_grass']['variants']);seen=set()
    for patch in recipe['patches']:
        mask=Image.new('L',size);ImageDraw.Draw(mask).polygon([(x*24,y*24) for x,y in patch['polygon']],fill=255)
        x0,y0,x1,y1=mask.getbbox();spacing_x,spacing_y=recipe['clump_spacing']
        for row,y in enumerate(range(y0+10,y1-5,spacing_y)):
            for col,x in enumerate(range(x0+12+(row%2)*11,x1-8,spacing_x)):
                if (x,y) in seen or not mask.getpixel((x,y)) or (row*7+col*3)%11==0 or not clear(x,y):continue
                seen.add((x,y));index=(row+col*3)%len(variants)
                instances.append({'id':f"{patch['id']}.{row}.{col}",'position':[x,y],
                                  'variant':variants[index],'phase_ms':(x*37+y*71)%4800})
    if not instances:raise ValueError('Town grass placements unexpectedly empty')
    data['grass']={'manifest':recipe['pack'],'instances':instances,
                   'source_recipe':GRASS_SOURCE.relative_to(ROOT).as_posix(),
                   'material_cells':cells}
    overview=Image.open(BytesIO(products[ROOT/data['ground_frames'][0]])).convert('RGBA')
    layers=[]
    for entity in entities:
        frame=entity['frames'][entity['phase_offset']%len(entity['frames'])];path=ROOT/frame
        image=Image.open(BytesIO(products[path])) if path in products else Image.open(path)
        layers.append((entity['sort_y'],entity.get('sort_priority',0),image.convert('RGBA'),tuple(entity['position'])))
    ax,ay=pack['tall_grass']['anchor']
    for instance in instances:
        pose=pack['tall_grass']['variants'][instance['variant']]['idle'][0];x,y=instance['position']
        for name,sort_y,priority in (('rear',y-16,-1),('front',y+6,4)):
            layers.append((sort_y,priority,Image.open(ROOT/pose[name]).convert('RGBA'),(x-ax,y-ay)))
    for _,_,image,position in sorted(layers,key=lambda record:record[:2]):overview.alpha_composite(image,position)
    for layer in data['foreground']:overview.alpha_composite(Image.open(ROOT/layer['image']).convert('RGBA'),tuple(layer['position']))
    retain(ROOT/data['overview'],overview.convert('RGB'))
    products[OUTPUT/'map.json']=(json.dumps(data,indent=2)+'\n').encode()
    return products,len(instances)


def compile_emerald(check=False):
    products,count=emerald_products();stale=[]
    for path,content in products.items():
        if check:
            if not path.exists() or path.read_bytes()!=content:stale.append(path.relative_to(ROOT).as_posix())
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    if stale:raise SystemExit('Stale Eldenmere emerald terrain: '+', '.join(stale))
    print(f"{'Verified' if check else 'Compiled'} emerald Eldenmere terrain and {count} nonblocking grass clumps; navigation and story metadata retained.")


def save(path,image):
    path.parent.mkdir(parents=True,exist_ok=True)
    image.save(path)
    return path.relative_to(ROOT).as_posix()


def export_entity(spec,prefix='',duration_ms=200):
    identifier=prefix+spec['id']
    frames=[];seen={}
    for index,frame in enumerate(spec['frames']):
        digest=sha256(frame.tobytes()).digest()
        if digest not in seen:
            seen[digest]=save(OUTPUT/f'entities/{identifier}/frame_{index+1:02}.png',frame)
        frames.append(seen[digest])
    return {'id':identifier,'position':spec['position'],'sort_y':spec['sort_y'],
            'frames':frames,'frame_duration_ms':duration_ms,'phase_offset':spec.get('phase_offset',0)}


def build():
    plan=read_json(BASE/'adapted_plan.json')
    foundation=read_json(ROOT/'assets/source/maps/eldenmere/terrain_foundation/recipe.json')
    recipe=read_json(ROOT/'assets/source/terrain/eldenmere/workshop/recipe.json')
    sanctuary,sanctuary_frames,items=workshop.sanctuary_assets()
    buildings=town.building_assets(foundation,plan)
    next(b for b in buildings if b['id']=='sanctuary').update(
        position=sanctuary['building_position'],frames=sanctuary_frames,placeholder=False)
    metadata=read_json(TERRAIN/'workshop/workshop.json')
    next(b for b in buildings if b['id']=='mira').update(
        position=metadata['position'],frames=[town.opened(TERRAIN/f'workshop/frames/frame_{i+1:02}.png') for i in range(54)],
        placeholder=False)
    assert not any(b['placeholder'] for b in buildings)
    grass=town.opened(BASE/'layers/grass.png')
    base=grass.copy();base.alpha_composite(town.opened(BASE/'layers/paths.png'))
    base,_=workshop.apron(recipe,base,grass)
    flagstones=next(p for p in sanctuary['props'] if p['id']=='flagstones')
    base.alpha_composite(town.opened(TERRAIN/'sanctuary_charm/props/flagstones.png'),tuple(flagstones['position']))
    base=well.apply_square(base,grass)
    ground=[]
    geo=geometry(plan);water,tiles=town.stream_tiles(geo)
    channels=town.channels(plan,geo);bridges=town.bridge_assets(plan)
    masonry=town.opened(BASE/'layers/masonry.png')
    for tick in range(6):
        # No buildings or actors are baked into the ground: roofs can occlude
        # the moving player correctly in the runtime's depth-sorted draw pass.
        image=town.render_environment(tick,base,grass,masonry,water,tiles,channels,[],bridges)
        ground.append(save(OUTPUT/f'ground/frame_{tick+1:02}.png',image.convert('RGB')))
    entities=[export_entity(b) for b in buildings]
    entities.extend(export_entity(p,'sanctuary.',600) for p in items)
    for p in recipe['props']:
        if 'ground_rect' in p:
            spec={**p,'frames':[town.opened(TERRAIN/f"workshop/props/{p['id']}.png")],
                  'sort_y':p['position'][1]+p['size'][1]}
            entities.append(export_entity(spec,'workshop.'))
    for p in recipe['grass']:
        pack=TERRAIN/p['pack'];meta=read_json(pack/'plant.json')
        spec={**p,'frames':[town.opened(pack/f['image']) for f in meta['wind']['frames']],
              'sort_y':p['position'][1]+24}
        entities.append(export_entity(spec,'workshop.',600))
    entities.append(export_entity(well.entity()))
    foreground=[]
    for bridge in bridges:
        foreground.append({'id':bridge['id'],'position':bridge['position'],
                           'image':save(OUTPUT/f"foreground/{bridge['id']}.png",bridge['foreground'])})
    collision=town.opened(TERRAIN/'workshop/navigation/blocking.png').convert('L')
    collision=well.collision_and_routes(collision)
    collision_path=save(OUTPUT/'collision.png',collision)
    access=read_json(TERRAIN/'workshop/navigation/access.json')
    well_recipe=read_json(ROOT/'assets/source/terrain/eldenmere/well/recipe.json')
    destinations={**access['destinations'],**well_recipe['approaches']}
    landmarks=[]
    names={'sanctuary':"Serene’s Home",'mira':"Mira’s workshop",'mill':'Watermill',
           'halden':"Halden’s cottage",'elira':"Elira’s cottage",'venn':'Venn family cottage',
           'commons':'Well square'}
    for key,name in names.items():landmarks.append({'id':key,'name':name,'position':access['destinations'][key]})
    manifest={'id':'eldenmere.playable','size_tiles':plan['size_tiles'],'tile_size':24,
              'size_pixels':list(base.size),'spawn':[384,312],'player_probe_size':[24,12],
              'player_draw_anchor':[12,30],'ground_frames':ground,'ground_frame_duration_ms':200,
              'collision':collision_path,'entities':entities,'foreground':foreground,
              'landmarks':landmarks,'destinations':destinations,
              'layout_source':'assets/maps/eldenmere/well_square/layout.json',
              'original_layout_source':'assets/maps/eldenmere/terrain_foundation/adapted_plan.json',
              'navigation_allowed':'assets/maps/eldenmere/well_square/allowed_routes.png',
              'source_art':['assets/terrain/eldenmere/workshop/workshop.json',
                            'assets/terrain/eldenmere/sanctuary_charm/charm.json',
                            'assets/terrain/eldenmere/well/well.json'],
              'npcs':[{'id':'mira_worker','name':'Mira','routine':'bench_work',
                       'position':[610,448],'probe_size':[8,4],
                       'animation':'assets/characters/mira/work_bench/animation.json',
                       'fitting_position':[594,423],'fitting_sort_y':444},
                      {'id':'sanctuary_gardener','name':'Gardener','routine':'watering',
                       'position':[322,350],'probe_size':[12,8],
                       'animation':'assets/characters/npcs/female_02/gardener/animations.json',
                       'behavior':'assets/maps/eldenmere/routines/gardener.json'}],
              'persistent_npcs':[
                  {'id':'mother_serene','name':'Mother Serene','routine':'sanctuary_schedule',
                   'scene':'sanctuary_dining','position':[288,214],'probe_size':[12,8],
                   'draw_anchor':[12,30],'sprite_root':'assets/characters/serene',
                   'animation':'assets/characters/serene/routines/animations.json',
                   'behavior':'assets/maps/eldenmere/routines/serene.json'}],
              'quests':[]}
    # Clean, actor-free overview used by the in-game map and review.
    overview=town.opened(ROOT/ground[0]).copy()
    for entity in sorted(entities,key=lambda e:e['sort_y']):
        overview.alpha_composite(town.opened(ROOT/entity['frames'][entity['phase_offset']%len(entity['frames'])]),tuple(entity['position']))
    for layer in foreground:overview.alpha_composite(town.opened(ROOT/layer['image']),tuple(layer['position']))
    manifest['overview']=save(OUTPUT/'overview.png',overview.convert('RGB'))
    write_json(OUTPUT/'map.json',manifest)
    from build_building_interiors import build as build_interiors
    build_interiors()
    # The regional sanctuary is a lazy exterior, outside town routines.
    compiled=read_json(OUTPUT/'map.json')
    compiled.setdefault('exterior_scenes',{})['elden_vale_sanctuary']='assets/maps/elden_vale_sanctuary/map.json'
    write_json(OUTPUT/'map.json',compiled)
    print(f'Compiled playable Eldenmere: {base.size}, {len(entities)} depth-sorted objects, six ground phases, no baked actors.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain-only',action='store_true',help='Apply approved emerald grass to the assembled town, preserving later story/building additions')
    parser.add_argument('--check',action='store_true',help='Verify assembled emerald terrain without writing files (requires --terrain-only)')
    args=parser.parse_args()
    if args.check and not args.terrain_only:parser.error('--check requires --terrain-only')
    if args.terrain_only:compile_emerald(args.check)
    else:build()
