"""Review five household plots against their clean pre-PR baseline.

Native initialized-Game views use disclosed clear-ground fixtures. Walking,
running, all five household doorways and Continue use production code with
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

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_households'
PREFIX = 'settlement.households.'
GROUND_PREFIX = 'assets/maps/eldenmere/town_hd/town/chunks/'
ALLOWED_FIELDS = {'entities', 'collision', 'ground_overlays', 'overview',
                  'settlement_households'}
HOUSE_IDS = ('liam_house', 'home_a', 'home_b', 'home_c', 'elira')
PRIOR_LEDGERS = ('settlement_dressing', 'settlement_workyards', 'settlement_commons')
DETAILS = (
    ('liam_house_frontage', (287.5,570), (287.5,558)),
    ('home_a_frontage', (215.5,762), (215.5,750)),
    ('home_b_frontage', (503.5,714), (503.5,702)),
    ('home_c_frontage', (263.5,1122), (263.5,1110)),
    ('elira_frontage', (671.5,1002), (671.5,990)),
    ('mira_frontage', (636,474), (636,462)),
    ('halden_frontage', (1007.5,666), (1007.5,654)),
)


def households_entities(town):
    return [record for record in town['entities'] if record['id'].startswith(PREFIX)]


def parcel_rectangles(ledger):
    if ledger['district']!='commons_households':
        raise AssertionError('Household parcels must remain in the commons household district')
    parcels = {item['id']:item['scope_rect'] for item in ledger['parcels']}
    if len(parcels) != len(ledger['parcels']) or set(parcels) != set(HOUSE_IDS):
        raise AssertionError('Household ledger must own exactly five unique named parcels')
    dx,dy,dw,dh = ledger['scope_rect']
    for name, rect in parcels.items():
        x,y,w,h = rect
        if (any(type(value) is not int for value in rect) or min(w,h) <= 0
                or x < dx or y < dy or x+w > dx+dw or y+h > dy+dh):
            raise AssertionError(('Invalid logical household parcel',name,rect))
        for other, other_rect in parcels.items():
            if name != other and pygame.Rect(rect).colliderect(other_rect):
                raise AssertionError(('Household parcel scopes overlap',name,other))
    return parcels


def parcel_mask(size, parcels, camera=(0,0)):
    result = Image.new('L',size);painter=ImageDraw.Draw(result)
    cx,cy=camera
    for x,y,w,h in parcels.values():
        painter.rectangle((round((x-cx)*2),round((y-cy)*2),
                           round((x+w-cx)*2)-1,round((y+h-cy)*2)-1),fill=255)
    return result


def contains(rect, other):
    x,y,w,h=rect;ox,oy,ow,oh=other
    return x<=ox and y<=oy and ox+ow<=x+w and oy+oh<=y+h


def ground_coverage(town, ledger, parcels):
    """Each garden cell's complete one-tile material fringe fits one parcel."""
    size=tuple(value*2 for value in town['size_pixels'])
    mask=Image.new('L',size);painter=ImageDraw.Draw(mask);tile=town['tile_size']
    cells=[]
    for cell in ledger['ground_cells']:
        if len(cell)!=2 or any(type(value) is not int for value in cell):
            raise AssertionError(('Invalid garden cell',cell))
        x,y=cell;rect=[(x-1)*tile,(y-1)*tile,3*tile,3*tile]
        owners=[name for name,scope in parcels.items() if contains(scope,rect)]
        if len(owners)!=1:
            raise AssertionError(('Complete garden material fringe must fit one parcel',cell,owners))
        painter.rectangle((rect[0]*2,rect[1]*2,(rect[0]+rect[2])*2-1,(rect[1]+rect[3])*2-1),fill=255)
        cells.append({'cell':cell,'parcel':owners[0],'logical_fringe_rect':rect})
    if len({tuple(item['cell']) for item in cells}) != len(cells):
        raise AssertionError('Duplicate household ground cell')
    if np.any((np.asarray(mask)!=0)&(np.asarray(parcel_mask(size,parcels))==0)):
        raise AssertionError('Garden material fringe leaves the actual parcel union')
    return mask,cells


def compare_baseline(baseline, folder):
    original,town=read(baseline/'town.json'),read(framework.TOWN)
    ledger=town['settlement_households'];parcels=parcel_rectangles(ledger)
    entities=households_entities(town)
    if entities!=ledger['entities'] or len({item['id'] for item in entities})!=len(entities):
        raise AssertionError('Household registry must exactly own unique live entities')
    if [item for item in town['entities'] if not item['id'].startswith(PREFIX)]!=original['entities']:
        raise AssertionError('An existing entity changed')
    for key in (*PRIOR_LEDGERS,'grass','settlement_streets','cartography'):
        if town[key]!=original[key]:
            raise AssertionError(('Existing district/grass/street ownership changed',key))
    if ledger.get('retired_grass_ids') or ledger.get('retired_grass_records'):
        raise AssertionError('PR6 cannot retire existing grass')
    if ledger.get('ground_entities'):
        raise AssertionError('Flat household entities need explicit coverage registration')
    placements={item['id']:item for item in ledger['placements']}
    if len(placements)!=len(ledger['placements']) or set(placements)!={item['id'] for item in entities}:
        raise AssertionError('Placement and live entity owners differ')
    for entity in entities:
        owner=placements[entity['id']]['parcel']
        if owner not in parcels:
            raise AssertionError(('Unknown entity parcel',entity['id'],owner))
        rect=[*entity['position'],*entity['logical_size']]
        if entity['artwork_pixels_per_world_pixel']!=2 or not contains(parcels[owner],rect):
            raise AssertionError(('Artwork leaves its native household parcel',entity['id'],owner))
        for path in frame_paths(entity):
            with Image.open(ROOT/path) as art:
                if art.size!=tuple(round(value*2) for value in entity['logical_size']):
                    raise AssertionError(('Household artwork lost native density',entity['id'],path))
    changed_fields=sorted(key for key in original.keys()|town.keys() if original.get(key)!=town.get(key))
    if set(changed_fields)-ALLOWED_FIELDS:
        raise AssertionError(('Unrelated map fields changed',changed_fields))
    previous=read(baseline/'observations.json')['production'];current=framework.production_snapshot()
    allowed={current['town_map'],town['collision'],town['overview'],original['overview']}
    images=set(framework.image_paths(entities));old_files=previous['active_files'];new_files=current['active_files']
    changed_files=sorted(path for path in old_files.keys()|new_files.keys() if old_files.get(path)!=new_files.get(path))
    unexpected=[path for path in changed_files if path not in allowed and not path.startswith(GROUND_PREFIX)
                and not(path in images and path not in old_files)]
    if unexpected:
        raise AssertionError(('Existing non-ground artwork changed',unexpected))
    with Image.open(baseline/'collision.png') as raw:before_collision=raw.convert('L')
    expected=before_collision.copy();painter=ImageDraw.Draw(expected)
    supports=ledger['solid_footprints']
    if len({support['id'] for support in supports})!=len(supports):
        raise AssertionError('Duplicate household solid support')
    if {item['id'] for item in supports}!={item['id'] for item in placements.values() if item['collision']=='solid'}:
        raise AssertionError('Explicit solid placements and declared support owners differ')
    for support in supports:
        sx,sy,sw,sh=support['rect']
        if any(type(value) is not int for value in (sx,sy,sw,sh)) or min(sw,sh)<=0:
            raise AssertionError(('Invalid integer logical support',support))
        if support['id'] not in placements:
            raise AssertionError(('Support lacks placement owner',support['id']))
        owner=placements[support['id']]['parcel']
        if not contains(parcels[owner],support['rect']):
            raise AssertionError(('Support leaves its named parcel',support))
        painter.rectangle((sx,sy,sx+sw-1,sy+sh-1),fill=255)
    with Image.open(ROOT/town['collision']) as raw:collision=raw.convert('L')
    if collision.size!=expected.size or collision.tobytes()!=expected.tobytes():
        raise AssertionError('Collision is not exactly baseline union declared household supports')
    if (baseline/'navigation_allowed.png').read_bytes()!=(ROOT/town['navigation_allowed']).read_bytes():
        raise AssertionError('Navigation changed')
    mask,cells=ground_coverage(town,ledger,parcels);coverage=np.asarray(mask)!=0
    for name,rect in parcels.items():
        x,y,w,h=rect
        mask.crop((x*2,y*2,(x+w)*2,(y+h)*2)).save(folder/(name+'_ground_coverage.png'))
    phases=[]
    for phase in range(6):
        after=native_ground(town,phase*200)
        with Image.open(baseline/f'ground_phase_{phase}.png') as raw:before=raw.convert('RGBA')
        if before.size!=after.size:raise AssertionError('Native ground dimensions changed')
        changes=np.any(np.asarray(before)!=np.asarray(after),axis=2)
        item={'phase':phase,'elapsed_ms':phase*200,'changed_native_pixels':int(np.count_nonzero(changes)),
              'changed_outside_household_garden_fringe':int(np.count_nonzero(changes&~coverage)),
              'before_rgba_sha256':framework.digest(before.tobytes()),'after_rgba_sha256':framework.digest(after.tobytes())}
        phases.append(item)
        if item['changed_outside_household_garden_fringe']:
            raise AssertionError(('Ground changed outside parcel-owned garden material fringes',item))
    for stale in folder.glob('before_*.png'):stale.unlink()
    for path in sorted(baseline.glob('*.png')):
        if path.name.startswith('ground_phase_') or path.name in {'collision.png','navigation_allowed.png','protection_plan_diagnostic.png'}:continue
        shutil.copyfile(path,folder/('before_'+path.name))
    for source,dest in (('observations.json','before_observations.json'),('town.json','before_town.json'),
                        ('baseline_revision.json','before_revision.json'),('household_details.json','before_household_details.json')):
        shutil.copyfile(baseline/source,folder/dest)
    return {'baseline_revision':read(baseline/'baseline_revision.json'),'changed_map_fields':changed_fields,
            'changed_active_files':changed_files,'parcels':ledger['parcels'],
            'existing_entities_unchanged':True,'existing_non_ground_artwork_unchanged':True,
            'all_three_prior_ledgers_unchanged':True,'grass_unchanged':True,
            'street_ledger_and_cartography_unchanged':True,'new_entity_ids':[item['id'] for item in entities],
            'solid_footprints':supports,'collision_exact_additive_delta':True,
            'collision_added_logical_pixels':int(np.count_nonzero(np.asarray(collision)!=np.asarray(before_collision))),
            'navigation_identical_bytes':True,'garden_cells':cells,'material_fringe_tiles':1,
            'ground_coverage_native_pixels':int(np.count_nonzero(coverage)),'ground_phases':phases}


def compare_view_scope(baseline,folder,capture):
    previous=read(baseline/'observations.json')
    parcels=parcel_rectangles(read(framework.TOWN)['settlement_households']);results=[]
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
        details = read(baseline/'household_details.json')
        fixtures = tuple((name,tuple(item['actual_player_logical']),tuple(item['camera_focus_logical']))
                         for name,item in details['views'].items())
    with tempfile.TemporaryDirectory(prefix='eldenmere-households-review-') as directory:
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
                    raise AssertionError(('Blocked household fixture', point))
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
                raise AssertionError(('No clear household fixture after waiting for actors', label))

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
                        if game.window.get_size() != (960,640):raise AssertionError('Non-native household view')
                        pictures.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
                    name_out=name+('_reduced' if reduced else '')+'.png';pictures[0].save(folder/name_out)
                    changes=framework.changed_pixels(*pictures)
                    if reduced and changes:
                        raise AssertionError(('Reduced-motion household view changed',name,changes))
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
                        parcels=parcel_rectangles(game.town.data['settlement_households'])
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
            placements={item['id']:item for item in game.town.data['settlement_households']['placements']}
            for entity in households_entities(game.town.data):
                paths=frame_paths(entity)
                if len(paths)<2:continue
                cadence=entity['frame_duration_ms']
                if type(cadence) is not int or cadence<=0:raise AssertionError('Invalid animated prop cadence')
                parcel=placements[entity['id']]['parcel']
                outer=next(door.data for door in game.town.doors if door.data['id']==parcel)
                dx,dy=outer['anchor'];ex,ey=entity['position'];ew,eh=entity['logical_size']
                focus=(ex+ew/2,ey+eh/2)
                start=choose(((dx,dy+36),(dx+8,dy+36),(dx-8,dy+36)),entity['id']+'_frames',focus)
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
                                raise AssertionError(('Unsafe household movement',diagnostic(label)))
                            trace.append([round(v,4) for v in game.player.position])
                            if before.distance_to(game.player.position)<.001:stalled=True;break
                        else:raise AssertionError(('Household route frame budget',diagnostic(label)))
                        if stalled:break
                    if not stalled and game.player.position.distance_to(target)<.02:
                        return {'target':list(target),'trace':trace,'frames':len(trace)-1,'replans':replans,'wait_seconds':waits}
                    replans+=1;waits+=.2;game.update(.2,(0,0),False)
                raise AssertionError(('Household route remained obstructed',list(target),diagnostic(label)))

            def follow(label, route, running):
                sx,sy=route[0]
                fixture=choose((route[0],(sx+8,sy),(sx-8,sy),(sx,sy+8),(sx,sy-8)),label)
                segments=[drive(game.town,target,running,label) for target in route[1:]]
                return {'label':label,'running':running,'goals':route,'start_fixture':fixture,
                        'segments':segments,'update_frames':sum(item['frames'] for item in segments),
                        'replans':sum(item['replans'] for item in segments),'passed':True}

            if movement:
                routes=(
                    ('liam_house_access',[[384,552],[336,552],[287.5,546]]),
                    ('home_a_access',[[384,768],[216,768],[215.5,738]]),
                    ('home_b_access',[[384,720],[504,720],[503.5,690]]),
                    ('home_c_access',[[504,1128],[312,1128],[263.5,1128],[263.5,1098]]),
                    ('elira_access',[[624,1032],[648,1008],[671.5,978]]),
                    ('liam_daisy_perimeter',[[232,552],[360,552],[360,620],[232,620],[232,552]]),
                    ('commons_connection',[[384,768],[384,864],[456,900],[526,900],[576,900],[636,804],[672,738]]),
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
                        else:raise AssertionError(('Household doorway did not enter',diagnostic(door_id)))
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
                        else:raise AssertionError(('Household doorway did not return',diagnostic(door_id)))
                        if not game.town.can_stand(game.player.position):raise AssertionError(('Blocked house return',door_id))
                        game.draw();name=door_id+'_roundtrip_'+('run' if running else 'walk')+'.png'
                        pygame.image.save(game.window,str(folder/name))
                        report['doorway_roundtrips'].append({'door':door_id,'running':running,'interior':interior.data['id'],
                            'start_fixture':fixture,'production_approaches':approaches,'entry_update_frames':entry_frames,
                            'clear_arrival_fixture':arrival_fixture,
                            'exit_update_frames':exit_frames,'return_position':list(game.player.position),'clear_ground':True,'image':name})
                        print('Passed doorway:',door_id,'run' if running else 'walk',flush=True)

                fixture=choose(((576,914),(636,804),(672,756)),'save_start')
                if not game.save_progress():raise AssertionError(('Household save failed',game.save_error))
                saved=deepcopy(game.saved_journey)
                saved_state=framework.canonical(framework.meaningful_state(game))
                expected_ledgers={key:deepcopy(game.town.data[key]) for key in
                                  (*PRIOR_LEDGERS,'settlement_households')}
                entity_ids=[item['id'] for item in households_entities(game.town.data)]

                def resume(name, payload):
                    if not game.save_store.write(payload):raise AssertionError('Disposable checkpoint write failed')
                    game.music.stop();restored=framework.Game(**options)
                    try:
                        restored.audio.set_music(0);restored.audio.set_effects(0)
                        if not restored.begin_journey(True):raise AssertionError(('Household Continue failed',restored.save_error))
                        restored.opening_fade=restored.transfer_cooldown=0
                        ids=[item['id'] for item in households_entities(restored.town.data)]
                        if ids!=entity_ids or len(ids)!=len(set(ids)):raise AssertionError('Continue lost/duplicated household entities')
                        if any(restored.town.data[key]!=value for key,value in expected_ledgers.items()):
                            raise AssertionError('Continue changed an integrated district ledger')
                        if not restored.world.can_stand(restored.player.position):raise AssertionError('Continue restored blocked ground')
                        supports=restored.town.data['settlement_households']['solid_footprints']
                        for support in supports:
                            sx,sy,sw,sh=support['rect']
                            if not all(restored.town.blocked.get_at((px,py))
                                       for py in range(sy,sy+sh) for px in range(sx,sx+sw)):
                                raise AssertionError(('Continue lost support',support['id']))
                        if framework.canonical(framework.meaningful_state(restored))!=saved_state:
                            raise AssertionError('Continue changed quest/party/inventory/flags')
                        if name=='continue_households':
                            restored.draw();pygame.image.save(restored.window,str(folder/(name+'.png')))
                        return {'saved_position_fixture':payload['player']['position'],'restored_scene':restored.world.data['id'],
                                'position':list(restored.player.position),'clear_ground':True,'new_entity_ids':ids,
                                'solid_supports_preserved':len(supports),'all_district_ledgers_unchanged':True,
                                'quest_party_inventory_flags_unchanged':True}
                    finally:restored.music.stop()
                report['save_continue']=resume('continue_households',saved)
                report['save_continue']['start_fixture']=fixture
                recoveries=[]
                for support in expected_ledgers['settlement_households']['solid_footprints']:
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
            if not report['quest_party_inventory_flags_unchanged']:raise AssertionError('Household review changed gameplay progress')
        finally:game.music.stop();pygame.quit()
    return report


def capture(folder, baseline=None, *, movement=True):
    folder.mkdir(parents=True,exist_ok=True)
    production=framework.production_snapshot()
    comparison=compare_baseline(baseline,folder) if baseline is not None else None
    framework.capture(folder)
    report=read(folder/'observations.json')
    report['scope']='Native production household fixtures, strict parcel differences, real input/doorway/Continue checks; no quest playthrough.'
    report['baseline_comparison']=comparison
    if baseline is not None:report['native_view_comparison']=compare_view_scope(baseline,folder,report)
    report['gameplay']=gameplay_capture(folder,baseline=baseline,movement=movement)
    if framework.production_snapshot()!=production:raise AssertionError('Production changed during households capture')
    report['production_source_unchanged']=True
    report['capture_png_sha256']={path.name:framework.digest(path.read_bytes()) for path in sorted(folder.glob('*.png'))}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Households review: {len(report['views'])} native views, {len(report['gameplay']['routes'])} movement checks; "
          f"baseline {'verified' if baseline is not None else 'not requested'}.")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-dir','--baseline',type=Path)
    parser.add_argument('--skip-movement',action='store_true',help='Only static views; omit movement/doorway/Continue checks')
    args=parser.parse_args()
    capture(args.output.resolve(),args.baseline_dir.resolve() if args.baseline_dir else None,movement=not args.skip_movement)
