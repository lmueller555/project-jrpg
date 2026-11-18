"""Review the southern arrival pockets against their clean pre-PR baseline.

Native initialized-Game views use disclosed clear-ground fixtures. Walking,
running, both business doorways and Continue use production code with
residents present. Only disposable save positions are changed for blocked-checkpoint
recovery fixtures; gameplay progress and production inputs remain untouched.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import capture_eldenmere_settlement_framework as framework
from tools.capture_eldenmere_streets import native_ground
from tools.capture_eldenmere_workyards import read, frame_paths

import numpy as np
from PIL import Image, ImageDraw
import pygame

from npc_routines import find_path

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_arrival'
PREFIX = 'settlement.arrival.'
GROUND_PREFIX = 'assets/maps/eldenmere/town_hd/town/chunks/'
ALLOWED_FIELDS = {'entities','collision','overview','settlement_arrival'}
HOUSE_IDS = ('inn','item_shop')
PRIOR_LEDGERS = ('settlement_dressing','settlement_workyards','settlement_commons','settlement_households','settlement_growing')
PARCELS = {'inn_frontage':[384,1392,96,72], 'shop_frontage':[576,1392,48,72],
           'west_approach':[432,1600,48,32], 'east_approach':[576,1584,48,48]}
DETAILS = (
    ('southern_spine_junction',(504,1320),(516,1320)),
    ('business_lane_junction',(528,1512),(528,1488)),
    ('southern_return',(528,1572),(528,1548)),
    ('southern_exit_contact',(528,1620),(528,1596)),
    ('inn_frontage',(288,1506),(288,1464)),
    ('item_shop_frontage',(669,1506),(669,1464)),
    ('inn_service_access',(192,1512),(216,1476)),
    ('shop_service_access',(744,1512),(744,1476)),
    ('western_south_approach',(384,1200),(384,1248)),
)


def arrival_entities(town):
    return [record for record in town['entities'] if record['id'].startswith(PREFIX)]


def parcel_rectangles(ledger):
    parcels={item['id']:item['scope_rect'] for item in ledger['parcels']}
    if (ledger['district']!='southern_arrival' or ledger['scope_rect']!=[72,1104,744,528]
            or len(parcels)!=len(ledger['parcels']) or parcels!=PARCELS):
        raise AssertionError('Arrival must stay within the four reviewed southern pockets')
    for name,rect in parcels.items():
        for other,other_rect in parcels.items():
            if name!=other and pygame.Rect(rect).colliderect(other_rect):
                raise AssertionError(('Arrival pockets overlap',name,other))
    return parcels


def parcel_mask(size, parcels, camera=(0,0)):
    result=Image.new('L',size);painter=ImageDraw.Draw(result);cx,cy=camera
    for x,y,w,h in parcels.values():
        painter.rectangle((round((x-cx)*2),round((y-cy)*2),round((x+w-cx)*2)-1,round((y+h-cy)*2)-1),fill=255)
    return result


def contains(rect,other):
    x,y,w,h=rect;ox,oy,ow,oh=other
    return x<=ox and y<=oy and ox+ow<=x+w and oy+oh<=y+h


def preserve(source,destination):
    """Avoid rewriting identical baseline witnesses while tests read them."""
    raw=source.read_bytes()
    if destination.exists() and destination.read_bytes()==raw:return
    temporary=destination.with_name(destination.name+'.tmp');temporary.write_bytes(raw);temporary.replace(destination)


def compare_baseline(baseline,folder):
    original,town=read(baseline/'town.json'),read(framework.TOWN);ledger=town['settlement_arrival']
    parcels=parcel_rectangles(ledger);entities=arrival_entities(town)
    if len(entities)!=10 or entities!=ledger['entities'] or len({item['id'] for item in entities})!=10:
        raise AssertionError('Arrival must own exactly ten unique live prop/plant entities')
    if [item for item in town['entities'] if not item['id'].startswith(PREFIX)]!=original['entities']:
        raise AssertionError('Existing entity ownership changed')
    for key in (*PRIOR_LEDGERS,'grass','settlement_streets','cartography'):
        if town[key]!=original[key]:raise AssertionError(('Previous district/grass/street ownership changed',key))
    if (ledger['ground_cells'] or ledger.get('ground_entities') or ledger.get('retired_grass_ids')
            or ledger.get('retired_grass_records')):
        raise AssertionError('Arrival cannot change ground or retire grass')
    placements={item['id']:item for item in ledger['placements']}
    if len(placements)!=10 or set(placements)!={item['id'] for item in entities}:
        raise AssertionError('Arrival placement and entity owners differ')
    for entity in entities:
        owner=placements[entity['id']]['parcel']
        if (owner not in parcels or entity['artwork_pixels_per_world_pixel']!=2
                or not contains(parcels[owner],[*entity['position'],*entity['logical_size']])):
            raise AssertionError(('Artwork leaves its native arrival pocket',entity['id'],owner))
        paths=frame_paths(entity)+([entity['reduced_motion_image']] if entity.get('reduced_motion_image') else [])
        for path in paths:
            with Image.open(ROOT/path) as raw:
                if raw.size!=tuple(round(v*2) for v in entity['logical_size']):
                    raise AssertionError(('Arrival source artwork lost native density',entity['id'],path))
    changed_fields=sorted(key for key in original.keys()|town.keys() if original.get(key)!=town.get(key))
    if set(changed_fields)-ALLOWED_FIELDS:raise AssertionError(('Unrelated map metadata changed',changed_fields))
    previous=read(baseline/'observations.json')['production'];current=framework.production_snapshot()
    allowed={current['town_map'],town['collision'],town['overview'],original['overview']}
    images=set(framework.image_paths(entities));old_files=previous['active_files'];new_files=current['active_files']
    changed_files=sorted(path for path in old_files.keys()|new_files.keys() if old_files.get(path)!=new_files.get(path))
    unexpected=[path for path in changed_files if path not in allowed and not(path in images and path not in old_files)]
    if unexpected:raise AssertionError(('Existing production artwork changed',unexpected))
    with Image.open(baseline/'collision.png') as raw:before_collision=raw.convert('L')
    expected=before_collision.copy();painter=ImageDraw.Draw(expected);supports=ledger['solid_footprints']
    if (len(supports)!=2 or {item['id'] for item in supports}
            !={item['id'] for item in placements.values() if item['collision']=='solid'}):
        raise AssertionError('Only the two explicit arrival containers may add collision')
    for support in supports:
        x,y,w,h=support['rect']
        if any(type(v) is not int for v in (x,y,w,h)) or min(w,h)<=0:raise AssertionError(('Invalid support',support))
        owner=placements[support['id']]['parcel']
        if not contains(parcels[owner],support['rect']):raise AssertionError(('Support leaves pocket',support))
        painter.rectangle((x,y,x+w-1,y+h-1),fill=255)
    with Image.open(ROOT/town['collision']) as raw:collision=raw.convert('L')
    if collision.size!=expected.size or collision.tobytes()!=expected.tobytes():
        raise AssertionError('Collision is not exactly baseline union the two declared container supports')
    if (baseline/'navigation_allowed.png').read_bytes()!=(ROOT/town['navigation_allowed']).read_bytes():
        raise AssertionError('Navigation changed')
    added=int(np.count_nonzero(np.asarray(collision)!=np.asarray(before_collision)))
    if added!=200:raise AssertionError(('Arrival supports must add exactly200logicalpixels',added))
    phases=[]
    for phase in range(6):
        after=native_ground(town,phase*200)
        with Image.open(baseline/f'ground_phase_{phase}.png') as raw:before=raw.convert('RGBA')
        if before.size!=after.size or before.tobytes()!=after.tobytes():
            raise AssertionError(('Arrival changed native ground',phase))
        phases.append({'phase':phase,'elapsed_ms':phase*200,'changed_native_pixels':0,
            'before_rgba_sha256':framework.digest(before.tobytes()),'after_rgba_sha256':framework.digest(after.tobytes())})
    for path in sorted(baseline.glob('*.png')):
        if path.name.startswith('ground_phase_') or path.name in {'collision.png','navigation_allowed.png','protection_plan_diagnostic.png'}:continue
        preserve(path,folder/('before_'+path.name))
    for source,destination in (('observations.json','before_observations.json'),('town.json','before_town.json'),
            ('baseline_revision.json','before_revision.json'),('arrival_details.json','before_arrival_details.json'),
            ('collision.png','before_collision.png')):
        preserve(baseline/source,folder/destination)
    return {'baseline_revision':read(baseline/'baseline_revision.json'),'changed_map_fields':changed_fields,'changed_active_files':changed_files,
        'parcels':ledger['parcels'],'existing_entities_unchanged':True,'all_five_prior_ledgers_unchanged':True,
        'grass_streets_cartography_unchanged':True,'travel_services_quest_metadata_unchanged':True,
        'existing_artwork_and_ground_files_unchanged':True,'solid_footprints':supports,
        'collision_exact_additive_delta':True,'collision_added_logical_pixels':added,'navigation_identical_bytes':True,
        'new_entity_ids':[item['id'] for item in entities],'ground_phases':phases}


def compare_view_scope(baseline,folder,capture):
    previous=read(baseline/'observations.json')
    parcels=parcel_rectangles(read(framework.TOWN)['settlement_arrival']);results=[]
    for name,fixture in capture['views'].items():
        if fixture!=previous['views'][name]:raise AssertionError(('Production camera fixture changed',name))
        with Image.open(baseline/(name+'.png')) as raw:before=np.asarray(raw.convert('RGB'))
        with Image.open(folder/(name+'.png')) as raw:after=np.asarray(raw.convert('RGB'))
        mask=np.asarray(parcel_mask((after.shape[1],after.shape[0]),parcels,fixture['camera_logical']))!=0
        changes=np.any(before!=after,axis=2)
        item={'name':name,'changed_native_pixels':int(np.count_nonzero(changes)),
              'changed_outside_parcel_union':int(np.count_nonzero(changes&~mask))}
        results.append(item)
        if item['changed_outside_parcel_union']:raise AssertionError(('Native view changed outside actual parcel union',item))
    return results


def gameplay_capture(folder, *, baseline=None, movement=True):
    report = {'fixture':'Fresh production Game, opening disabled, disposable saves/settings, disclosed clear-ground starts. '
              'Residents and routines remain active; no quests, actors or scenery are replaced.',
              'routes':[],'details':[],'doorway_roundtrips':[],'ambient_conversations':[],
              'frontage_view_comparison':[],'animated_prop_frames':[]}
    fixtures = DETAILS
    if baseline is not None:
        details = read(baseline/'arrival_details.json')
        fixtures = tuple((name,tuple(item['actual_player_logical']),tuple(item['camera_focus_logical']))
                         for name,item in details['views'].items())
    with tempfile.TemporaryDirectory(prefix='eldenmere-arrival-review-') as directory:
        temporary = Path(directory)
        options = dict(fullscreen=False,window_size=(960,640),start_on_title=True,
                       save_path=temporary/'journey.json',settings_path=temporary/'settings.json')
        game = framework.Game(**options)
        try:
            game.on_title=False;game.opening.restore({'version':1,'stage':'disabled'})
            game.opening_fade=game.transfer_cooldown=0
            game.audio.set_music(0);game.audio.set_effects(0);game.world=game.town
            initial = framework.canonical(framework.meaningful_state(game))

            def place(point, focus=None):
                if game.world is not game.town or not game.town.can_stand(point):
                    raise AssertionError(('Blocked arrival fixture', point))
                game.player.position.update(point);game.player.moving=game.player.running=False
                game.player.walk_ms=0;game.location_label=None;game.location_seconds=0
                game.saves.notice_seconds=game.transfer_cooldown=0;game.camera.reset()
                if focus is not None:game.camera.focus(focus,duration=0)

            def choose(candidates, label, focus=None):
                for _ in range(30):
                    for point in candidates:
                        if game.town.can_stand(point):
                            place(point,focus)
                            return {'label':label,'candidates':[list(p) for p in candidates],'selected':list(point)}
                    game.update(.2,(0,0),False)
                raise AssertionError(('No clear arrival fixture after waiting for actors', label))

            for name,point,focus in fixtures:
                px,py = point
                chosen = choose((point,(px+8,py),(px-8,py),(px,py+8),(px,py-8)),name,focus)
                game.player.facing='back'
                item = {'name':name,'start_fixture':chosen,'baseline_player_logical':list(point),
                        'player_logical':list(game.player.position),'focus_logical':list(focus),
                        'camera_logical':list(game.camera.position())}
                for reduced in (False,True):
                    game.audio.set_reduced_motion(reduced);game._update_grass(0)
                    pictures=[]
                    for elapsed in (0,600):
                        game.elapsed_ms=elapsed;game.draw()
                        if game.window.get_size() != (960,640):raise AssertionError('Non-native arrival view')
                        pictures.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
                    name_out=name+('_reduced' if reduced else '')+'.png';pictures[0].save(folder/name_out)
                    changes=framework.changed_pixels(*pictures)
                    if reduced and changes:
                        raise AssertionError(('Reduced-motion arrival view changed',name,changes))
                    item['reduced' if reduced else 'normal']={'image':name_out,'changed_pixels_at_600ms':changes,
                        'first_rgb_sha256':framework.digest(pictures[0].tobytes()),
                        'second_rgb_sha256':framework.digest(pictures[1].tobytes())}
                    if not reduced and baseline is not None:
                        prior=details['views'][name]
                        if (list(game.player.position)!=prior['actual_player_logical']
                                or list(game.camera.position())!=prior['camera_logical']):
                            raise AssertionError(('Protected baseline frontage fixture changed',name,chosen))
                        with Image.open(baseline/(name+'.png')) as raw:
                            first=np.asarray(raw.convert('RGB'))
                        after=np.asarray(pictures[0]);delta=np.any(first!=after,axis=2)
                        parcels=parcel_rectangles(game.town.data['settlement_arrival'])
                        mask=np.asarray(parcel_mask(pictures[0].size,parcels,game.camera.position()))!=0
                        check={'name':name,'changed_native_pixels':int(np.count_nonzero(delta)),
                               'changed_outside_parcel_union':int(np.count_nonzero(delta&~mask))}
                        report['frontage_view_comparison'].append(check)
                        if check['changed_outside_parcel_union']:
                            raise AssertionError(('Native frontage changed outside actual parcel union',check))
                report['details'].append(item)
            game.audio.set_reduced_motion(False);game._update_grass(0)

            # Actual native crops show every source-authored phase of new
            # animated props. No source frames are enlarged or composited over
            # a manufactured scene. Normal cadence is sampled by elapsed time;
            # reduced motion must hold the same native crop through the cycle.
            placements={item['id']:item for item in game.town.data['settlement_arrival']['placements']}
            for entity in arrival_entities(game.town.data):
                paths=frame_paths(entity)
                cadence=entity['frame_duration_ms']
                if type(cadence) is not int or cadence<=0:raise AssertionError('Invalid animated prop cadence')
                parcel=placements[entity['id']]['parcel']
                ex,ey=entity['position'];ew,eh=entity['logical_size']
                focus=(ex+ew/2,ey+eh/2)
                start=choose(((528,1536),(528,1572),(528,1512)),entity['id']+'_frames',focus)
                cx,cy=game.camera.position()
                crop=tuple(round(value*2) for value in (ex-cx,ey-cy,ex+ew-cx,ey+eh-cy))
                if not (0<=crop[0]<crop[2]<=960 and 0<=crop[1]<crop[3]<=640):
                    raise AssertionError(('Animated native crop leaves the actual viewport',entity['id'],crop))
                entry={'entity':entity['id'],'parcel':parcel,'frame_duration_ms':cadence,
                       'start_fixture':start,'camera_logical':[cx,cy],'native_crop':list(crop),'frames':[]}
                offset=entity.get('phase_offset',0);entry['phase_offset']=offset
                for index in range(len(paths)):
                    source_index=(index+offset)%len(paths);path=paths[source_index]
                    game.elapsed_ms=index*cadence;game.draw()
                    picture=Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')).crop(crop)
                    filename=entity['id'].replace('.','_')+f'_phase_{source_index}.png';picture.save(folder/filename)
                    with Image.open(ROOT/path) as raw:source_picture=raw.convert('RGBA')
                    source_pixels=source_picture.tobytes();source_array=np.asarray(source_picture)
                    mismatches=int(np.count_nonzero(np.any(np.asarray(picture)!=source_array[:,:,:3],axis=2)
                                                       & (source_array[:,:,3]==255)))
                    if mismatches:
                        raise AssertionError(('Native prop phase does not match its source opaque pixels',entity['id'],source_index,mismatches))
                    entry['frames'].append({'index':source_index,'sample_index':index,'elapsed_ms':index*cadence,'source_image':path,
                        'source_file_sha256':framework.digest((ROOT/path).read_bytes()),
                        'source_rgba_sha256':framework.digest(source_pixels),'image':filename,
                        'opaque_source_pixel_mismatches':mismatches,
                        'actual_rgb_sha256':framework.digest(picture.tobytes())})
                source_unique=len({item['source_rgba_sha256'] for item in entry['frames']})
                actual_unique=len({item['actual_rgb_sha256'] for item in entry['frames']})
                if source_unique>1 and actual_unique<2:
                    raise AssertionError(('Authored animated prop has no visible normal motion',entity['id']))
                entry['source_distinct_frames']=source_unique
                entry['actual_distinct_frames']=actual_unique
                game.audio.set_reduced_motion(True);game._update_grass(0)
                reduced=[]
                for time in (0,cadence*(len(paths)-1)):
                    game.elapsed_ms=time;game.draw()
                    reduced.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')).crop(crop))
                if framework.changed_pixels(*reduced):raise AssertionError(('Reduced prop phases moved',entity['id']))
                filename=entity['id'].replace('.','_')+'_reduced.png';reduced[0].save(folder/filename)
                entry['reduced']={'image':filename,'changed_native_pixels':0,
                    'actual_rgb_sha256':framework.digest(reduced[0].tobytes())}
                still_path=entity.get('reduced_motion_image') or paths[entity.get('reduced_motion_frame',0)]
                with Image.open(ROOT/still_path) as raw:still=raw.convert('RGBA')
                still_array=np.asarray(still)
                mismatches=int(np.count_nonzero(np.any(np.asarray(reduced[0])!=still_array[:,:,:3],axis=2)
                                               & (still_array[:,:,3]==255)))
                if mismatches:raise AssertionError(('Reduced native prop does not match its source idle',entity['id'],mismatches))
                entry['reduced'].update(source_image=still_path,
                    source_file_sha256=framework.digest((ROOT/still_path).read_bytes()),
                    source_rgba_sha256=framework.digest(still.tobytes()),opaque_source_pixel_mismatches=mismatches)
                report['animated_prop_frames'].append(entry)
                game.audio.set_reduced_motion(False);game._update_grass(0)

            report['prop_actor_depth']=[]
            for support in game.town.data['settlement_arrival']['solid_footprints']:
                entity=next(item for item in arrival_entities(game.town.data) if item['id']==support['id'])
                sx,sy,sw,sh=support['rect'];center=sx+sw/2
                paths=frame_paths(entity);phase=entity.get('phase_offset',0)%len(paths)
                with Image.open(ROOT/paths[phase]) as raw:prop=raw.convert('RGBA')
                for side,point in (('behind',(center,sy-6)),('front',(center,sy+sh+6))):
                    fixture=choose((point,(point[0]-2,point[1]),(point[0]+2,point[1])),
                                   entity['id']+'_'+side,(center,sy))
                    game.player.facing='front';game.elapsed_ms=0;game.draw()
                    filename=entity['id'].replace('.','_')+'_player_'+side+'.png'
                    pygame.image.save(game.window,str(folder/filename))
                    frame=np.asarray(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
                    sprite=game.player.sprite();native=getattr(sprite,'native',sprite)
                    actor=Image.frombytes('RGBA',native.get_size(),pygame.image.tobytes(native,'RGBA'))
                    cx,cy=game.camera.position();px,py=(round(v) for v in game.player.position);anchor=game.player.draw_anchor
                    actor_layer=Image.new('RGBA',(960,640));prop_layer=Image.new('RGBA',(960,640))
                    actor_layer.alpha_composite(actor,(round((px-anchor[0]-cx)*2),round((py-anchor[1]-cy)*2)))
                    ex,ey=entity['position'];prop_layer.alpha_composite(prop,(round((ex-cx)*2),round((ey-cy)*2)))
                    actor_pixels=np.asarray(actor_layer);prop_pixels=np.asarray(prop_layer)
                    overlap=(actor_pixels[:,:,3]==255)&(prop_pixels[:,:,3]==255)
                    expected_pixels=prop_pixels[:,:,:3] if side=='behind' else actor_pixels[:,:,:3]
                    mismatches=int(np.count_nonzero(np.any(frame!=expected_pixels,axis=2)&overlap))
                    count=int(np.count_nonzero(overlap))
                    if not count or mismatches:raise AssertionError(('Actual prop/player depth mismatch',entity['id'],side,count,mismatches))
                    report['prop_actor_depth'].append({'entity':entity['id'],'side':side,'fixture':fixture,
                        'source_prop_image':paths[phase],'source_phase':phase,'opaque_overlap_pixels':count,
                        'opaque_overlap_mismatches':mismatches,'image':filename,
                        'actual_player_facing':'front','camera_logical':[cx,cy]})

            def diagnostic(label):
                return {'label':label,'position':list(game.player.position),'scene':game.world.data['id'],
                        'social_script':game.social.script_identifier,
                        'nearby_actors':[(actor.data['id'],list(actor.position)) for actor in game.world.npcs
                                         if actor.position.distance_to(game.player.position)<80]}

            def drive(world, target, running, label):
                target=pygame.Vector2(target);trace=[list(game.player.position)];replans=0;waits=0
                for _ in range(30):
                    if game.world is not world:raise AssertionError(('Unexpected scene transfer',diagnostic(label)))
                    if game.player.position.distance_to(target)<.02:
                        return {'target':list(target),'trace':trace,'frames':len(trace)-1,'replans':replans,'wait_seconds':waits}
                    if game.social.scripted:raise AssertionError(('Scripted exchange entered',diagnostic(label)))
                    if game.social.actor is not None:
                        event={'actor':game.social.actor.data['id'],'conversation':(game.social.conversation or {}).get('id'),
                               'route':label,'player_position':list(game.player.position)}
                        if not any(item['actor']==event['actor'] and item['conversation']==event['conversation']
                                   for item in report['ambient_conversations']):
                            report['ambient_conversations'].append(event)
                    # The NPC planner is an even-unit lattice. Door anchors may
                    # be odd or half-unit; append a real-input exact approach.
                    gx,gy=round(target.x/2)*2,round(target.y/2)*2
                    candidates=sorted({(gx+dx,gy+dy) for dx in (-2,0,2) for dy in (-2,0,2)},
                                      key=lambda p:pygame.Vector2(p).distance_squared_to(target))
                    lattice=next((p for p in candidates if world.can_stand(p)),None)
                    path=None if lattice is None else find_path(world,game.player.position,lattice,world.probe_size,None)
                    if path is None:
                        replans+=1;waits+=.2;game.update(.2,(0,0),False);continue
                    if not path or pygame.Vector2(path[-1]).distance_to(target)>.01:path.append(tuple(target))
                    stalled=False
                    for waypoint in path:
                        goal=pygame.Vector2(waypoint)
                        for _ in range(3000):
                            delta=goal-game.player.position
                            if delta.length()<.01:break
                            before=game.player.position.copy()
                            game.update(min(1/30,delta.length()/(108 if running else 72)),delta,running)
                            if game.world is not world or not world.can_stand(game.player.position):
                                raise AssertionError(('Unsafe arrival movement',diagnostic(label)))
                            trace.append([round(v,4) for v in game.player.position])
                            if before.distance_to(game.player.position)<.001:stalled=True;break
                        else:raise AssertionError(('Arrival route frame budget',diagnostic(label)))
                        if stalled:break
                    if not stalled and game.player.position.distance_to(target)<.02:
                        return {'target':list(target),'trace':trace,'frames':len(trace)-1,'replans':replans,'wait_seconds':waits}
                    replans+=1;waits+=.2;game.update(.2,(0,0),False)
                raise AssertionError(('Arrival route remained obstructed',list(target),diagnostic(label)))

            def follow(label, route, running):
                sx,sy=route[0]
                fixture=choose((route[0],(sx+8,sy),(sx-8,sy),(sx,sy+8),(sx,sy-8)),label)
                segments=[drive(game.town,target,running,label) for target in route[1:]]
                return {'label':label,'running':running,'goals':route,'start_fixture':fixture,
                        'segments':segments,'update_frames':sum(item['frames'] for item in segments),
                        'replans':sum(item['replans'] for item in segments),'passed':True}

            if movement:
                routes=(
                    ('full_southern_road',[[528,1104],[528,1320],[528,1368],[528,1488],[528,1572]]),
                    ('inn_access',[[528,1488],[384,1488],[288,1506],[288,1482]]),
                    ('shop_access',[[528,1488],[624,1488],[669,1506],[669,1482]]),
                    ('business_lane',[[240,1512],[384,1512],[528,1512],[708,1512],[768,1512]]),
                    ('western_service_margin',[[384,1320],[384,1488],[192,1512]]),
                    ('eastern_service_margin',[[576,1320],[576,1488],[744,1512]]),
                )
                for name,route in routes:
                    for running in (False,True):
                        for reverse in (False,True):
                            label=name+('_run' if running else '_walk')+('_return' if reverse else '')
                            report['routes'].append(follow(label,list(reversed(route)) if reverse else route,running))
                            print('Passed route:',label,flush=True)
                for door_id in HOUSE_IDS:
                    for running in (False,True):
                        outer=next(door.data for door in game.town.doors if door.data['id']==door_id)
                        x,y=outer['anchor']
                        fixture=choose(((x,y+36),(x+24,y+36),(x-24,y+36),(x,y+54)),door_id+'_doorway')
                        approaches=[drive(game.town,(x,y+12),running,door_id+'_front_door')]
                        entry_frames=exit_frames=0
                        for _ in range(240):
                            game.update(1/60,(0,-1),running);entry_frames+=1
                            if game.world is not game.town:break
                        else:raise AssertionError(('Arrival doorway did not enter',diagnostic(door_id)))
                        interior=game.world
                        if interior.data['id']!=door_id:raise AssertionError(('Doorway entered another scene',door_id,interior.data['id']))
                        back=next(door.data for door in interior.doors if door.data['id']=='courtyard')
                        bx,by=back['anchor']
                        # Liam's existing interior furniture blocks (252,258).
                        # Select a disclosed nearby clear point and reach it by
                        # actual input; never teleport or reset the door guard.
                        candidates=((bx,by-48),(bx,by-36),(bx,by-24),(bx-24,by-24),(bx+24,by-24))
                        clear=None
                        for _ in range(30):
                            clear=next((point for point in candidates if interior.can_stand(point)),None)
                            if clear is not None:break
                            game.update(.2,(0,0),False)
                        if clear is None:raise AssertionError(('No clear interior rearm fixture',door_id))
                        arrival_fixture={'requested':list(candidates[0]),'candidates':[list(p) for p in candidates],
                                         'selected':list(clear),'correction':clear!=candidates[0]}
                        approaches.append(drive(interior,clear,running,door_id+'_clear_arrival'))
                        game.update(.6,(0,0),False)
                        approaches.append(drive(interior,(bx,by-12),running,door_id+'_return_approach'))
                        for _ in range(240):
                            game.update(1/60,(0,1),running);exit_frames+=1
                            if game.world is game.town:break
                        else:raise AssertionError(('Arrival doorway did not return',diagnostic(door_id)))
                        if not game.town.can_stand(game.player.position):raise AssertionError(('Blocked house return',door_id))
                        game.draw();name=door_id+'_roundtrip_'+('run' if running else 'walk')+'.png'
                        pygame.image.save(game.window,str(folder/name))
                        report['doorway_roundtrips'].append({'door':door_id,'running':running,'interior':interior.data['id'],
                            'start_fixture':fixture,'production_approaches':approaches,'entry_update_frames':entry_frames,
                            'clear_arrival_fixture':arrival_fixture,
                            'exit_update_frames':exit_frames,'return_position':list(game.player.position),'clear_ground':True,'image':name})
                        print('Passed doorway:',door_id,'run' if running else 'walk',flush=True)

                # One initial fixture for the entire travel sequence. Every
                # subsequent adjustment, guard rearm and crossing is actual
                # Game.update input; cooldowns and armed flags are never reset.
                travel_start=choose(((528,1104),),'automatic_south_travel_initial')
                road=[drive(game.town,point,False,'automatic_south_travel_road')
                      for point in ((528,1320),(528,1368),(528,1488),(528,1572))]
                report['automatic_travel']={'initial_fixture':travel_start,'full_road_approach':road,'roundtrips':[]}
                regional_world=None

                def travel_state():
                    world=game.world;town=world is game.town
                    probe=world.probe_rect(game.player.position)
                    contact=(game.overworld_travel.town_exit_rect if town else world.town_entry_rect)
                    return {'scene':world.data['id'],'position':[round(v,4) for v in game.player.position],
                        'clear_ground':world.can_stand(game.player.position),'probe':list(probe),
                        'touching':contact.colliderect(probe if town else probe.inflate(2,2)),
                        'cooldown':round(game.transfer_cooldown,6),'town_armed':game.overworld_travel._town_armed,
                        'region_armed':game.overworld_travel._region_armed,'can_travel':game.overworld_travel.can_travel(),
                        'social_locked':game.social.locked,'social_script':game.social.script_identifier,
                        'opening_fade':game.opening_fade,'opening_locked':game.opening.locks_player,
                        'combat_active':game.combat.active}

                for running in (False,True):
                    for lane in (516,528,540):
                        label=f'lane_{lane}_'+('run' if running else 'walk')
                        trace=[{'phase':'start',**travel_state()}]
                        if game.world is not game.town:raise AssertionError('Travel sequence lost the town')
                        # A direct diagonal approach reaches contact before the
                        # .35s cooldown expires on all three quick-run cases.
                        target=pygame.Vector2(lane,1596)
                        for _ in range(240):
                            delta=target-game.player.position
                            if delta.length()<.01:break
                            game.update(min(1/60,delta.length()/(108 if running else 72)),delta,running)
                            if game.world is not game.town or not game.town.can_stand(game.player.position):
                                raise AssertionError(('Unsafe lane alignment',label,travel_state()))
                            trace.append({'phase':'align',**travel_state()})
                        else:raise AssertionError(('Lane alignment budget',label))
                        touched_during_cooldown=False;held=False
                        for _ in range(600):
                            game.update(1/60,(0,0) if held else (0,1),running)
                            trace.append({'phase':'town_contact_wait' if held else 'town_departure',**travel_state()})
                            if game.world is not game.town:break
                            if trace[-1]['touching'] and game.transfer_cooldown>0:
                                touched_during_cooldown=True;held=True
                                if not game.overworld_travel._town_armed:
                                    raise AssertionError(('Town contact failed to rearm during cooldown',label,trace[-1]))
                        else:raise AssertionError(('Automatic town departure stalled',label,trace[-1]))
                        if game.world.data['id']!='auratia.overworld' or not game.world.can_stand(game.player.position):
                            raise AssertionError(('Automatic departure landing invalid',label,travel_state()))
                        if running and not touched_during_cooldown:
                            raise AssertionError(('Quick-run case did not exercise positive cooldown contact',label))
                        if regional_world is None:regional_world=game.world
                        elif game.world is not regional_world:raise AssertionError('Automatic travel duplicated the regional world')
                        departure={'town_exterior_position':list(game.exterior_position),'regional_landing':list(game.player.position),
                                   'cooldown_contact_exercised':touched_during_cooldown}
                        game.draw();region_image='travel_'+label+'_region.png';pygame.image.save(game.window,str(folder/region_image))
                        away=drive(regional_world,(288,-588),running,label+'_regional_walkaway')
                        trace.append({'phase':'region_walkaway',**travel_state()})
                        if not game.overworld_travel._region_armed:
                            raise AssertionError(('Regional contact did not rearm through movement',label,trace[-1]))
                        for _ in range(600):
                            game.update(1/60,(0,-1),running)
                            trace.append({'phase':'region_return',**travel_state()})
                            if game.world is game.town:break
                            if game.world is not regional_world or not game.world.can_stand(game.player.position):
                                raise AssertionError(('Unsafe regional return',label,trace[-1]))
                        else:raise AssertionError(('Automatic regional return stalled',label,trace[-1]))
                        if tuple(game.player.position)!=(528,1572) or not game.town.can_stand(game.player.position):
                            raise AssertionError(('Automatic town return landing invalid',label,trace[-1]))
                        if not all(item['clear_ground'] for item in trace):
                            raise AssertionError(('Automatic travel crossed an unsafe footprint',label))
                        game.draw();town_image='travel_'+label+'_return.png';pygame.image.save(game.window,str(folder/town_image))
                        report['automatic_travel']['roundtrips'].append({'label':label,'lane':lane,'running':running,
                            'trace':trace,'departure':departure,'regional_walkaway':away,'return_position':list(game.player.position),
                            'return_cooldown':game.transfer_cooldown,'region_image':region_image,'return_image':town_image,
                            'no_post_initial_fixture_teleports':True,'same_regional_singleton':True,'passed':True})
                        print('Passed automatic travel:',label,flush=True)

                fixture=choose(((528,1572),(528,1512),(528,1536)),'save_start')
                if not game.save_progress():raise AssertionError(('Arrival save failed',game.save_error))
                saved=deepcopy(game.saved_journey)
                saved_state=framework.canonical(framework.meaningful_state(game))
                expected_ledgers={key:deepcopy(game.town.data[key]) for key in
                                  (*PRIOR_LEDGERS,'settlement_arrival')}
                entity_ids=[item['id'] for item in arrival_entities(game.town.data)]

                def resume(name, payload):
                    if not game.save_store.write(payload):raise AssertionError('Disposable checkpoint write failed')
                    game.music.stop();restored=framework.Game(**options)
                    try:
                        restored.audio.set_music(0);restored.audio.set_effects(0)
                        if not restored.begin_journey(True):raise AssertionError(('Arrival Continue failed',restored.save_error))
                        restored.opening_fade=restored.transfer_cooldown=0
                        ids=[item['id'] for item in arrival_entities(restored.town.data)]
                        if ids!=entity_ids or len(ids)!=len(set(ids)):raise AssertionError('Continue lost/duplicated arrival entities')
                        if any(restored.town.data[key]!=value for key,value in expected_ledgers.items()):
                            raise AssertionError('Continue changed an integrated district ledger')
                        if not restored.world.can_stand(restored.player.position):raise AssertionError('Continue restored blocked ground')
                        supports=restored.town.data['settlement_arrival']['solid_footprints']
                        for support in supports:
                            sx,sy,sw,sh=support['rect']
                            if not all(restored.town.blocked.get_at((px,py))
                                       for py in range(sy,sy+sh) for px in range(sx,sx+sw)):
                                raise AssertionError(('Continue lost support',support['id']))
                        if framework.canonical(framework.meaningful_state(restored))!=saved_state:
                            raise AssertionError('Continue changed quest/party/inventory/flags')
                        if name=='continue_arrival':
                            restored.draw();pygame.image.save(restored.window,str(folder/(name+'.png')))
                        return {'saved_position_fixture':payload['player']['position'],'restored_scene':restored.world.data['id'],
                                'position':list(restored.player.position),'clear_ground':True,'new_entity_ids':ids,
                                'solid_supports_preserved':len(supports),'all_district_ledgers_unchanged':True,
                                'quest_party_inventory_flags_unchanged':True}
                    finally:restored.music.stop()
                report['save_continue']=resume('continue_arrival',saved)
                report['save_continue']['start_fixture']=fixture
                recoveries=[]
                for support in expected_ledgers['settlement_arrival']['solid_footprints']:
                    sx,sy,sw,sh=support['rect'];position=[sx+sw/2,sy+sh/2]
                    if game.town.can_stand(position):raise AssertionError(('Support checkpoint fixture is clear',support['id']))
                    if baseline is not None:
                        with Image.open(baseline/'collision.png') as raw:prior_collision=raw.convert('L')
                        px,py=(round(value) for value in position)
                        if prior_collision.crop((px-12,py-6,px+12,py+6)).getbbox():
                            raise AssertionError(('Older checkpoint fixture was not clear for baseline24x12probe',support['id'],position))
                    payload=deepcopy(saved);payload['player']['position']=position
                    result=resume(support['id'],payload)
                    if result['position']==position:raise AssertionError('Blocked checkpoint position did not recover')
                    recoveries.append({'support':support['id'],'baseline_24x12_collision_clear':True if baseline is not None else None,
                        'fixture':'Disposable older-checkpoint player coordinate inside new support; all progress fields unchanged.',**result})
                report['blocked_checkpoint_recoveries']=recoveries
            report['quest_party_inventory_flags_unchanged']=initial==framework.canonical(framework.meaningful_state(game))
            if not report['quest_party_inventory_flags_unchanged']:raise AssertionError('Arrival review changed gameplay progress')
        finally:game.music.stop();pygame.quit()
    return report


def capture(folder, baseline=None, *, movement=True):
    folder.mkdir(parents=True,exist_ok=True)
    production=framework.production_snapshot()
    comparison=compare_baseline(baseline,folder) if baseline is not None else None
    framework.capture(folder)
    report=read(folder/'observations.json')
    report['scope']='Native production arrival fixtures, strict parcel differences, real input/doorway/Continue checks; no quest playthrough.'
    report['baseline_comparison']=comparison
    if baseline is not None:report['native_view_comparison']=compare_view_scope(baseline,folder,report)
    report['gameplay']=gameplay_capture(folder,baseline=baseline,movement=movement)
    if framework.production_snapshot()!=production:raise AssertionError('Production changed during arrival capture')
    report['production_source_unchanged']=True
    report['capture_png_sha256']={path.relative_to(folder).as_posix():framework.digest(path.read_bytes()) for path in sorted(folder.rglob('*.png'))}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Arrival review: {len(report['views'])} native views, {len(report['gameplay']['routes'])} movement checks; "
          f"baseline {'verified' if baseline is not None else 'not requested'}.")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-dir','--baseline',type=Path)
    parser.add_argument('--skip-movement',action='store_true',help='Only static views; omit movement/doorway/Continue checks')
    args=parser.parse_args()
    capture(args.output.resolve(),args.baseline_dir.resolve() if args.baseline_dir else None,movement=not args.skip_movement)
