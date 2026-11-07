"""Compose the reserve from native pixel packs and source-derived stone modules.

The retained composition painting is no longer an input. Terrain, independent
objects and their physical ground contacts share the authored placement recipe.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw, ImageFilter

if __package__:
    from .build_eldenmere_terrain import BITS, OFFSETS, normalize_mask
    from .reserve_stone_kit import make_kit
    from .grass_terrain import material_at
else:
    from build_eldenmere_terrain import BITS, OFFSETS, normalize_mask
    from reserve_stone_kit import make_kit
    from grass_terrain import material_at

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT/'assets/source/maps/elden_vale_sanctuary/recipe.json'
OUTPUT = ROOT/'assets/terrain/elden_vale_sanctuary'
KIT = ROOT/'assets/terrain/elden_vale_sanctuary_kit'
TERRAIN = ROOT/'assets/terrain/eldenmere'


def encoded(image):
    stream = BytesIO();image.save(stream, format='PNG');return stream.getvalue()


def exports():
    recipe = json.loads(RECIPE.read_text())
    used = set()
    def read(path):
        path = Path(path)
        used.add(path)
        return json.loads(path.read_text())
    def opened(path):
        path = Path(path)
        used.add(path)
        return Image.open(path).convert('RGBA')
    products = {}
    kit, kit_meta = make_kit()
    for name, image in kit.items():
        # The helper's assets are runtime modules, rather than one scenery plate.
        products['../elden_vale_sanctuary_kit/'+name+'.png'] = encoded(image)
    products['../elden_vale_sanctuary_kit/kit.json'] = (json.dumps(kit_meta,indent=2)+'\n').encode()
    for source in kit_meta['source_sha256']:used.add(ROOT/source)
    used.add(ROOT/'tools/reserve_stone_kit.py')
    used.add(ROOT/'tools/grass_terrain.py')
    width, height = recipe['size_pixels']
    tile = 24
    grass_spec = recipe['grass']
    gm = read(ROOT/grass_spec['manifest'])
    grass = {family:[opened(ROOT/path) for path in record['tiles']]
             for family,record in gm['materials'].items()}
    dirt = {r['mask']:opened(ROOT/r['image']) for r in gm['dirt_transitions']['tiles']}
    fills = [opened(ROOT/path) for path in gm['dirt_transitions']['interiors']]
    ground = Image.new('RGBA', (width,height))
    rng = Random(8713)
    material_tiles = [path for record in gm['materials'].values() for path in record['tiles']]
    material_indices = []
    for y in range(height//tile):
        row = []
        for x in range(width//tile):
            px,py=x*tile+12,y*tile+12
            family=grass_spec['base_material']
            for region in grass_spec['material_regions']:
                cx,cy=region['center'];rx,ry=region['radius']
                if ((px-cx)/rx)**2+((py-cy)/ry)**2 <= 1:
                    family=region['material']
            index,image=material_at(x,y,family,grass)
            ground.alpha_composite(image,(x*tile,y*tile))
            row.append(material_tiles.index(gm['materials'][family]['tiles'][index]))
        material_indices.append(row)
    path_mask = Image.new('L', (width,height))
    draw = ImageDraw.Draw(path_mask)
    for road in recipe['ground']['roads']:
        points = [tuple(point) for point in road['points']]
        draw.line(points, fill=255, width=road['width'], joint='curve')
        radius = road['width']//2
        for x,y in points:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
    x,y,w,h = recipe['ground']['court']
    draw.rounded_rectangle((x,y,x+w-1,y+h-1),radius=24,fill=255)
    path_cells = {(x,y) for y in range(height//tile) for x in range(width//tile)
                  if path_mask.getpixel((x*tile+12,y*tile+12))}
    for x,y in sorted(path_cells):
        mask = normalize_mask(sum(BITS[name] for name,(dx,dy) in OFFSETS.items()
                                  if (x+dx,y+dy) in path_cells))
        ground.alpha_composite(rng.choice(fills) if mask==255 else dirt[mask], (x*tile,y*tile))
    flagstones = opened(TERRAIN/'sanctuary_charm/props/flagstones.png')
    for yy in range(350,425,28):
        for xx in range(456,873,40):
            if rng.random()<.77:ground.alpha_composite(flagstones,(xx+rng.randrange(-3,4),yy))
    # Grass is an independent interactive layer. Only low flowers belong to
    # the ground cache; their stems use the same approved emerald ramp.
    plant_names = ('flowers_white','flowers_yellow','flowers_violet')
    plants = []
    for name in plant_names:
        record=gm['flowers'][name]
        read(ROOT/record['metadata'])
        plants.append(opened(ROOT/record['idle']))
    for x,y,w,h in recipe['garden_patches']:
        for _ in range(max(6,w*h//450)):
            ground.alpha_composite(rng.choice(plants),
                                   (rng.randrange(x,x+w-24),rng.randrange(y,y+h-24)))
    for _ in range(35):
        px,py = rng.randrange(36,width-36),rng.randrange(72,height-72)
        if (px//24,py//24) not in path_cells:
            ground.alpha_composite(rng.choice(plants),(px,py))

    entities, footprints, instances, depth_samples = [], [], [], []
    def add(identifier, asset_id, position, frames, local_footprints=(), sort_y=None, duration=600, phase=0):
        position = list(map(int,position))
        if asset_id in kit:image=kit[asset_id]
        elif frames[0].startswith(OUTPUT.relative_to(ROOT).as_posix()+'/'):
            name=Path(frames[0]).relative_to(OUTPUT.relative_to(ROOT)).as_posix()
            image=Image.open(BytesIO(products[name])).convert('RGBA')
        else:image=opened(ROOT/frames[0])
        rects = [[position[0]+r[0],position[1]+r[1],r[2],r[3]] for r in local_footprints]
        baseline = sort_y if sort_y is not None else max((r[1]+r[3] for r in rects),default=position[1]+image.height)
        record = {'id':identifier,'position':position,'frames':frames,'sort_y':baseline,
                  'frame_duration_ms':duration,'phase_offset':phase}
        entities.append(record)
        instances.append({**deepcopy(record),'asset_id':asset_id,'footprints':rects})
        for index,rect in enumerate(rects):footprints.append({'id':identifier+f'_{index}','entity_id':identifier,'rect':rect})
        return record
    def stone(identifier, asset, pos, solid=(), sort_y=None):
        return add(identifier,asset,pos,[(KIT/(asset+'.png')).relative_to(ROOT).as_posix()],solid,sort_y)

    tree_dir = TERRAIN/'foliage/tree';tree_meta=read(tree_dir/'foliage.json')
    tree_frames=[(tree_dir/r['image']).relative_to(ROOT).as_posix() for r in tree_meta['wind']['frames']]
    for frame in tree_frames:used.add(ROOT/frame)
    tree_variants={}
    for variant,factors in (('sage',(1.,1.,1.)),('deep',(.92,.98,.90)),('warm',(1.08,1.02,.89))):
        paths=[]
        for frame_index,source in enumerate(tree_frames):
            image=opened(ROOT/source)
            if variant!='sage':
                pixels=[]
                for red,green,blue,alpha in image.get_flattened_data():
                    if green>red*.94 and green>blue*1.15:
                        red,green,blue=(min(255,round(value*factor)) for value,factor in zip((red,green,blue),factors))
                    pixels.append((red,green,blue,alpha))
                image.putdata(pixels)
            name=f'foliage/{variant}/frame_{frame_index+1:02}.png'
            products[name]=encoded(image)
            paths.append((OUTPUT/name).relative_to(ROOT).as_posix())
        tree_variants[variant]=paths
    for index,(cx,cy) in enumerate(recipe['tree_roots']):
        # A96px crown can overhang paths; only its24px root has a collision body.
        identifier = f'reserve_tree_{index:02}'
        variant=('sage','deep','sage','warm')[index%4]
        add(identifier,'eldenmere.foliage.tree.'+variant,(cx-48,cy-108),tree_variants[variant],
            [tree_meta['ground_rect']],sort_y=cy+8,phase=index%len(tree_frames))
        if (cx,cy) in ((144,276),(336,420)):
            depth_samples.append({'id':identifier,'entity_id':identifier,
                                  'behind':[cx,cy-38],'front':[cx,cy+34]})
    shrub_dir=TERRAIN/'foliage/shrub'
    shrub_meta=read(shrub_dir/'foliage.json')
    shrub_frames=[(shrub_dir/frame['image']).relative_to(ROOT).as_posix() for frame in shrub_meta['wind']['frames']]
    for cluster_index,(x,y) in enumerate(recipe['shrub_clusters']):
        for index,(dx,dy) in enumerate(((0,0),(18,-8),(32,10))):
            add(f'reserve_shrub_{cluster_index}_{index}','eldenmere.foliage.shrub',[x+dx,y+dy],shrub_frames,[[3,15,18,9]],sort_y=y+dy+24,phase=(cluster_index+index)%len(shrub_frames))
    bench_image = TERRAIN/'sanctuary_charm/props/bench.png'
    for index,pos in enumerate(recipe['benches']):
        add(f'reserve_bench_{index}','eldenmere.bench',pos,[bench_image.relative_to(ROOT).as_posix()],[[4,20,40,10]])
    planter_image = TERRAIN/'sanctuary_charm/props/herb_planter.png'
    for index,pos in enumerate(recipe['planters']):
        add(f'reserve_planter_{index}','eldenmere.herb_planter',pos,[planter_image.relative_to(ROOT).as_posix()],[[2,12,20,6]])

    arch = recipe['architecture']
    # Compatibility footprints are explicit in the kit metadata. All generated
    # module sprites retain transparent openings, rather than rectangular mattes.
    def footprint(name, fallback):
        spec = kit_meta.get('modules',{}).get(name,{})
        return spec.get('footprints',spec.get('collision_rects',fallback))
    hall_pos=arch['hall']
    stone('reserve_hall','hall',hall_pos,
          footprint('hall',[[24,120,104,84],[160,120,104,84],[128,120,32,50]]),345)
    cloister_pos=arch['cloister']
    if 'cloister_floor' in kit:
        ground.alpha_composite(kit['cloister_floor'],(cloister_pos[0],cloister_pos[1]+48))
    stone('reserve_cloister_back','cloister_back_wall',[cloister_pos[0],cloister_pos[1]+48],[[0,0,240,12]],285)
    stone('reserve_cloister_roof','cloister_roof',cloister_pos,[],337)
    stone('reserve_cloister_arches','cloister_arches',[cloister_pos[0],cloister_pos[1]+44],[],337)
    for index,xoffset in enumerate((0,76,152,228)):
        stone(f'reserve_cloister_column_{index}','cloister_column',
              [cloister_pos[0]+xoffset,cloister_pos[1]+44],[[0,56,12,12]],337)
    stone('reserve_entrance_arch','entrance_arch',arch['entrance_arch'],
          footprint('entrance_arch',[[0,80,24,16],[72,80,24,16]]),672)
    cavepos=arch['cave']
    stone('reserve_cave','cave',cavepos,footprint('cave',[[12,64,35,64],[114,64,34,64],[47,60,67,56]]),383)
    stone('reserve_cave_keeper_rail','cave_keeper_rail',[972,329],[[0,30,72,12]],385)
    stone('reserve_survey_seam','ridge',arch['survey_seam'],footprint('ridge',[[4,32,88,30]]),554)
    stone('court_basin','basin',arch['court_basin'],footprint('basin',[[4,22,40,12]]),394)
    stone('reserve_survey_board','survey_board',arch['survey_board'],footprint('survey_board',[[4,22,24,8]]),614)
    stone('reserve_boundary_marker','memorial_marker',arch['boundary_marker'],[[4,18,10,10]],670)
    for index,pos in enumerate(([240,216],[324,240],[180,444])):
        stone(f'reserve_memorial_marker_{index}','memorial_marker',pos,[[4,18,10,10]])
    for index,pos in enumerate(([888,570],[1008,570],[960,594])):
        stone(f'reserve_survey_stake_{index}','survey_stake',pos,[[0,18,8,8]])
    for index,pos in enumerate(recipe['ridge_bands']):
        stone(f'reserve_ridge_band_{index}','ridge',pos,[[4,32,88,30]])
    for index,pos in enumerate(([912,264],[1020,300],[768,450])):
        stone(f'reserve_ridge_rock_{index}','rock_outcrop',pos,footprint('rock_outcrop',[[8,18,48,18]]))

    # Native terraced masonry forms maintained boundary walls, while the ridge
    # uses natural rock modules. The southern opening remains a real doorway.
    wall_file=TERRAIN/'terraces/tiles/wall_front_00.png'
    for index,x in enumerate(list(range(24,396,24))+list(range(492,1128,24))):
        add(f'reserve_south_wall_{index}','eldenmere.masonry.wall',[x,648],
            [wall_file.relative_to(ROOT).as_posix()],[[0,16,24,8]],672)
    wall_side=TERRAIN/'terraces/tiles/wall_side_left.png'
    for side,x in (('west',12),('east',1116)):
        for index,y in enumerate(range(48,648,24)):
            add(f'reserve_{side}_wall_{index}','eldenmere.masonry.side',[x,y],
                [wall_side.relative_to(ROOT).as_posix()],[[4,0,12,24]],y+24)
    wall_back=TERRAIN/'terraces/tiles/wall_back.png'
    for index,x in enumerate(range(24,1128,24)):
        add(f'reserve_north_wall_{index}','eldenmere.masonry.back',[x,24],
            [wall_back.relative_to(ROOT).as_posix()],[[0,12,24,12]],48)
    # The physical map boundary is visible woodland/wall, with a24px central
    # apron at the south for the reserve's world-travel exit.
    footprints += [{'id':'map_west_edge','rect':[0,0,12,height]},
                   {'id':'map_east_edge','rect':[1140,0,12,height]},
                   {'id':'map_north_edge','rect':[0,0,width,48]}]
    # The grass layer has no collision footprint. Its authored patches are
    # clipped away from solid objects, maintained roads and story approaches
    # so the terrain remains readable at doors and gathering points.
    avoid=Image.new('L',(width,height),0)
    avoid_draw=ImageDraw.Draw(avoid)
    for px,py in path_cells:
        avoid_draw.rectangle((px*tile,py*tile,(px+1)*tile-1,(py+1)*tile-1),fill=255)
    for record in footprints:
        x,y,w,h=record['rect']
        avoid_draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
    for rectangle in grass_spec['clear_rects']:
        x,y,w,h=rectangle
        avoid_draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
    for px,py in [recipe['spawn'],recipe['reserve_exit']['position'],
                  *recipe['public_approaches'].values(),*recipe['loop_waypoints'],
                  *[door['anchor'] for door in recipe['doors']]]:
        avoid_draw.ellipse((px-20,py-20,px+20,py+20),fill=255)
    avoid=avoid.filter(ImageFilter.MaxFilter(31))
    grass_instances=[]
    variants=tuple(gm['tall_grass']['variants'])
    plant_rng=Random(1903)
    for patch_index,patch in enumerate(grass_spec['patches']):
        cx,cy=patch['center'];rx,ry=patch['radius']
        for row,py in enumerate(range(cy-ry,cy+ry+1,16)):
            for px in range(cx-rx,cx+rx+1,18):
                x=px+(row%2)*9+plant_rng.randrange(-3,4)
                y=py+plant_rng.randrange(-3,4)
                distance=((x-cx)/rx)**2+((y-cy)/ry)**2
                if distance>1 or plant_rng.random()>.92-.27*distance:continue
                if not (24<=x<width-24 and 48<=y<height-24):continue
                if avoid.getpixel((x,y)):continue
                grass_instances.append({'id':f'reserve_grass_{patch_index}_{row}_{px}',
                    'position':[x,y], 'variant':variants[len(grass_instances)%len(variants)],
                    'phase_ms':plant_rng.randrange(4800)})
    grass_layer={'manifest':grass_spec['manifest'],'instances':grass_instances}
    overview=ground.copy()
    overview_layers=[]
    for record in sorted(entities,key=lambda item:item['sort_y']):
        frame=record['frames'][record['phase_offset']%len(record['frames'])]
        if frame.startswith(KIT.relative_to(ROOT).as_posix()+'/'):
            image=kit[Path(frame).stem]
        elif frame.startswith(OUTPUT.relative_to(ROOT).as_posix()+'/'):
            name=Path(frame).relative_to(OUTPUT.relative_to(ROOT)).as_posix()
            image=Image.open(BytesIO(products[name])).convert('RGBA')
        else:image=opened(ROOT/frame)
        overview_layers.append((record['sort_y'],image,tuple(record['position'])))
    anchor=gm['tall_grass']['anchor']
    for instance in grass_instances:
        pose=gm['tall_grass']['variants'][instance['variant']]['idle'][0]
        x,y=instance['position'];position=(x-anchor[0],y-anchor[1])
        overview_layers.append((y-16,opened(ROOT/pose['rear']),position))
        overview_layers.append((y+6,opened(ROOT/pose['front']),position))
    for _,image,position in sorted(overview_layers,key=lambda row:row[0]):
        overview.alpha_composite(image,position)
    products['ground.png']=encoded(ground.convert('RGB'))
    products['overview.png']=encoded(overview.convert('RGB'))
    for record in entities:
        for frame in record['frames']:
            if not frame.startswith((KIT.relative_to(ROOT).as_posix()+'/',OUTPUT.relative_to(ROOT).as_posix()+'/')):used.add(ROOT/frame)
    used.add(RECIPE)
    sources=[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(used)]
    bays=[{'id':f'cloister_bay_{i+1}','center':[700+i*76,318],
           'inside':[700+i*76,318],'front':[700+i*76,366],'approach':[700+i*76,366]}
          for i in range(3)]
    manifest={'version':2,'implementation':'native_pixel_asset_packs','tile_size':24,
              'size_pixels':[width,height],'ground':(OUTPUT/'ground.png').relative_to(ROOT).as_posix(),
              'overview':(OUTPUT/'overview.png').relative_to(ROOT).as_posix(),
              'entities':entities,'asset_instances':instances,'collision_footprints':footprints,
              'grass':grass_layer,
              'ground_materials':{'manifest':grass_spec['manifest'],
                                  'tiles':material_tiles,'indices':material_indices},
              'source_assets':sources,'source_recipe':RECIPE.relative_to(ROOT).as_posix(),
              'depth_samples':depth_samples,'cloister_bays':bays,
              'kit_metadata':kit_meta}
    products['art.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    return products


def build(check=False):
    products=exports()
    for name,body in products.items():
        path=OUTPUT/name
        if check:
            if not path.is_file() or path.read_bytes()!=body:raise ValueError('Stale native reserve asset: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    if not check:
        # Masked pieces of the removed painting are not part of the new scene.
        import shutil
        if (OUTPUT/'depth').exists():shutil.rmtree(OUTPUT/'depth')
    print(('Verified' if check else 'Exported')+' native reserve pixel-asset composition')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
