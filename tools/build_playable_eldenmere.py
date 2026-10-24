"""Compile the approved town and final exteriors into actor-free runtime layers.

This reads the existing art builders' assembly helpers, never their export/build
functions. Running the game does not require Pillow or these tools.
"""
from hashlib import sha256
from pathlib import Path

from PIL import Image

import build_eldenmere_town as town
import build_eldenmere_workshop as workshop
from build_eldenmere_blockout import geometry
from build_eldenmere_stream import read_json, write_json

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'assets/maps/eldenmere/playable'
BASE=ROOT/'assets/maps/eldenmere/terrain_foundation'
TERRAIN=ROOT/'assets/terrain/eldenmere'


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
    foreground=[]
    for bridge in bridges:
        foreground.append({'id':bridge['id'],'position':bridge['position'],
                           'image':save(OUTPUT/f"foreground/{bridge['id']}.png",bridge['foreground'])})
    collision=town.opened(TERRAIN/'workshop/navigation/blocking.png').convert('L')
    collision_path=save(OUTPUT/'collision.png',collision)
    access=read_json(TERRAIN/'workshop/navigation/access.json')
    landmarks=[]
    names={'sanctuary':'Sanctuary','mira':"Mira’s workshop",'mill':'Watermill',
           'halden':"Halden’s cottage",'elira':"Elira’s cottage",'venn':'Venn family cottage',
           'commons':'Village commons'}
    for key,name in names.items():landmarks.append({'id':key,'name':name,'position':access['destinations'][key]})
    manifest={'id':'eldenmere.playable','size_tiles':plan['size_tiles'],'tile_size':24,
              'size_pixels':list(base.size),'spawn':[384,312],'player_probe_size':[24,12],
              'player_draw_anchor':[12,30],'ground_frames':ground,'ground_frame_duration_ms':200,
              'collision':collision_path,'entities':entities,'foreground':foreground,
              'landmarks':landmarks,'destinations':access['destinations'],
              'layout_source':'assets/maps/eldenmere/terrain_foundation/adapted_plan.json',
              'source_art':['assets/terrain/eldenmere/workshop/workshop.json',
                            'assets/terrain/eldenmere/sanctuary_charm/charm.json'],
              'npcs':[{'id':'mira_worker','name':'Mira','routine':'bench_work',
                       'position':[610,448],'probe_size':[8,4],
                       'animation':'assets/characters/mira/work_bench/animation.json',
                       'fitting_position':[594,423],'fitting_sort_y':444},
                      {'id':'sanctuary_gardener','name':'Sanctuary gardener','routine':'watering',
                       'position':[322,350],'probe_size':[12,8],
                       'animation':'assets/characters/npcs/female_02/gardener/animations.json',
                       'behavior':'assets/maps/eldenmere/routines/gardener.json'}], 'quests':[]}
    # Clean, actor-free overview used by the in-game map and review.
    overview=town.opened(ROOT/ground[0]).copy()
    for entity in sorted(entities,key=lambda e:e['sort_y']):
        overview.alpha_composite(town.opened(ROOT/entity['frames'][entity['phase_offset']%len(entity['frames'])]),tuple(entity['position']))
    for layer in foreground:overview.alpha_composite(town.opened(ROOT/layer['image']),tuple(layer['position']))
    manifest['overview']=save(OUTPUT/'overview.png',overview.convert('RGB'))
    write_json(OUTPUT/'map.json',manifest)
    from build_building_interiors import build as build_interiors
    build_interiors()
    print(f'Compiled playable Eldenmere: {base.size}, {len(entities)} depth-sorted objects, six ground phases, no baked actors.')


if __name__=='__main__':build()
