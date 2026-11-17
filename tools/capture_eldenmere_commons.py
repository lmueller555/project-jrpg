"""Review the civic commons against its clean pre-PR baseline.

Native initialized-Game views use disclosed clear-ground fixtures. Walking,
running, the school doorway and Continue use production code with residents
present. Only disposable save positions are changed for blocked-checkpoint
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
from tools.eldenmere_settlement_streets import _mask

import numpy as np
from PIL import Image, ImageChops, ImageDraw
import pygame

from npc_routines import find_path

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_commons'
PREFIX = 'settlement.commons.'
STREET_PREFIX = 'settlement.street.commons.'
GROUND_PREFIX = 'assets/maps/eldenmere/town_hd/town/chunks/'
ALLOWED_FIELDS = {'entities', 'grass', 'collision', 'ground_overlays', 'overview',
                  'settlement_commons', 'settlement_streets', 'cartography'}
DETAILS = (
    ('commons_well_closeup', (576, 888), (528, 864)),
    ('commons_school_connection', (636, 804), (624, 804)),
    ('commons_west_seating', (456, 900), (456, 864)),
    ('school_entrance_closeup', (672, 756), (648, 720)),
)


def commons_entities(town):
    return [record for record in town['entities'] if record['id'].startswith(PREFIX)]


def ground_coverage(town, ledger):
    """Bound the source civic geometry and its one-material-tile fringe."""
    records = [record for record in town['settlement_streets']['treatments']
               if record['id'].startswith(STREET_PREFIX)]
    if not records:
        raise AssertionError('No explicitly owned civic ground treatment')
    size = tuple(value*2 for value in town['size_pixels'])
    raw = _mask(size, records)
    tile = town['tile_size']*2
    cells = []
    mask = Image.new('L', size)
    painter = ImageDraw.Draw(mask)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if raw.crop((x,y,x+tile,y+tile)).getbbox():
                cells.append([x//tile,y//tile])
                painter.rectangle((x-tile,y-tile,x+tile*2-1,y+tile*2-1), fill=255)
    scope = Image.new('L', size)
    x,y,w,h = ledger['scope_rect']
    ImageDraw.Draw(scope).rectangle((x*2,y*2,(x+w)*2-1,(y+h)*2-1), fill=255)
    if np.any((np.asarray(raw) != 0) & (np.asarray(scope) == 0)):
        raise AssertionError('Source civic material geometry leaves the declared scope')
    # A doorstep near the scope's edge may have a theoretical material fringe
    # beyond it. Accept only the intersection: actual changes must satisfy both
    # the source-material bound and the stricter declared district rectangle.
    return ImageChops.multiply(mask, scope), records, cells


def compare_baseline(baseline, folder):
    original, town = read(baseline/'town.json'), read(framework.TOWN)
    ledger = town['settlement_commons']
    entities = commons_entities(town)
    if entities != ledger['entities'] or len({item['id'] for item in entities}) != len(entities):
        raise AssertionError('Commons registry does not exactly own unique live entities')
    if [item for item in town['entities'] if not item['id'].startswith(PREFIX)] != original['entities']:
        raise AssertionError('Existing entities changed')
    for key in ('settlement_dressing', 'settlement_workyards'):
        if town.get(key) != original.get(key):
            raise AssertionError(('Previously integrated district changed', key))
    x,y,w,h = ledger['scope_rect']
    flat = ledger.get('ground_entities', [])
    if flat:
        raise AssertionError('Civic flat entities need explicit native coverage registration')
    for entity in entities:
        ex,ey = entity['position'];ew,eh = entity['logical_size']
        if (entity['artwork_pixels_per_world_pixel'] != 2 or ex < x or ey < y
                or ex+ew > x+w or ey+eh > y+h):
            raise AssertionError(('Artwork leaves the native civic scope', entity['id']))
        for path in frame_paths(entity):
            with Image.open(ROOT/path) as source:
                if source.size != (round(ew*2), round(eh*2)):
                    raise AssertionError(('Artwork lost native density', entity['id'], path))
    retired = ledger.get('retired_grass_ids', [])
    if len(retired) != len(set(retired)):
        raise AssertionError('Duplicate civic grass retirement')
    prior = original['grass']['instances']
    retired_records = [record for record in prior if record['id'] in retired]
    if sorted(item['id'] for item in retired_records) != sorted(retired):
        raise AssertionError('Retired grass ID is not a pre-existing instance')
    if retired_records != ledger.get('retired_grass_records', []):
        raise AssertionError('Retirement ledger changed original grass records')
    for item in retired_records:
        gx,gy = item['position']
        if not (x <= gx <= x+w and y <= gy <= y+h):
            raise AssertionError(('Retirement leaves civic scope', item['id']))
    grass = deepcopy(original['grass'])
    grass['instances'] = [record for record in prior if record['id'] not in retired]
    if town['grass'] != grass:
        raise AssertionError('Grass changes exceed the retirement ledger')
    changed_fields = sorted(key for key in original.keys() | town.keys()
                            if original.get(key) != town.get(key))
    if set(changed_fields)-ALLOWED_FIELDS:
        raise AssertionError(('Unrelated map fields changed', changed_fields))
    for key in ('treatments', 'cartography'):
        retained = [record for record in town['settlement_streets'][key]
                    if not record['id'].startswith(STREET_PREFIX)]
        if retained != original['settlement_streets'][key]:
            raise AssertionError(('Previous street records changed', key))
    cartography = deepcopy(town['cartography'])
    cartography['street_network'] = [record for record in cartography['street_network']
                                    if not record['id'].startswith(STREET_PREFIX)]
    if cartography != original['cartography']:
        raise AssertionError('Previous cartography changed')

    previous = read(baseline/'observations.json')['production']
    current = framework.production_snapshot()
    allowed = {current['town_map'], town['collision'], town['overview'], original['overview']}
    images = set(framework.image_paths(entities))
    old_files, new_files = previous['active_files'], current['active_files']
    changed_files = sorted(path for path in old_files.keys() | new_files.keys()
                           if old_files.get(path) != new_files.get(path))
    unexpected = [path for path in changed_files if path not in allowed
                  and not path.startswith(GROUND_PREFIX)
                  and not (path in images and path not in old_files)]
    if unexpected:
        raise AssertionError(('Existing non-ground artwork changed', unexpected))
    with Image.open(baseline/'collision.png') as source:
        before_collision = source.convert('L')
    expected = before_collision.copy();painter = ImageDraw.Draw(expected)
    supports = ledger['solid_footprints']
    if len({support['id'] for support in supports}) != len(supports):
        raise AssertionError('Duplicate civic solid support')
    for support in supports:
        sx,sy,sw,sh = support['rect']
        if any(type(v) is not int for v in (sx,sy,sw,sh)) or min(sw,sh) <= 0:
            raise AssertionError(('Invalid logical support', support))
        if not (x <= sx and y <= sy and sx+sw <= x+w and sy+sh <= y+h):
            raise AssertionError(('Support leaves civic scope', support))
        painter.rectangle((sx,sy,sx+sw-1,sy+sh-1), fill=255)
    with Image.open(ROOT/town['collision']) as source:
        collision = source.convert('L')
    if collision.size != expected.size or collision.tobytes() != expected.tobytes():
        raise AssertionError('Collision is not precisely baseline plus declared civic supports')
    if (baseline/'navigation_allowed.png').read_bytes() != (ROOT/town['navigation_allowed']).read_bytes():
        raise AssertionError('Navigation changed')

    mask, treatments, cells = ground_coverage(town, ledger)
    # A tight diagnostic crop avoids adding another complete native town image.
    crop = (x*2,y*2,(x+w)*2,(y+h)*2)
    mask.crop(crop).save(folder/'commons_ground_coverage.png')
    coverage = np.asarray(mask) != 0
    phases = []
    for phase in range(6):
        after = native_ground(town, phase*200)
        with Image.open(baseline/f'ground_phase_{phase}.png') as source:
            before = source.convert('RGBA')
        if before.size != after.size:
            raise AssertionError('Native ground dimensions changed')
        changes = np.any(np.asarray(before) != np.asarray(after), axis=2)
        outside = int(np.count_nonzero(changes & ~coverage))
        item = {'phase':phase, 'elapsed_ms':phase*200,
                'changed_native_pixels':int(np.count_nonzero(changes)),
                'changed_outside_civic_material_fringe':outside,
                'before_rgba_sha256':framework.digest(before.tobytes()),
                'after_rgba_sha256':framework.digest(after.tobytes())}
        phases.append(item)
        if outside:
            raise AssertionError(('Ground changed outside source civic material fringe', item))
    # Keep useful native scene witnesses; huge ground/mask baselines stay in /tmp.
    for stale in folder.glob('before_*.png'):
        stale.unlink()
    for source in sorted(baseline.glob('*.png')):
        if source.name.startswith('ground_phase_') or source.name in {
                'collision.png','navigation_allowed.png','protection_plan_diagnostic.png'}:
            continue
        shutil.copyfile(source, folder/('before_'+source.name))
    for source, destination in (('observations.json','before_observations.json'),
                                ('town.json','before_town.json'),
                                ('baseline_revision.json','before_revision.json'),
                                ('commons_details.json','before_commons_details.json')):
        shutil.copyfile(baseline/source, folder/destination)
    return {'baseline_revision':read(baseline/'baseline_revision.json'),
            'changed_map_fields':changed_fields,'changed_active_files':changed_files,
            'existing_entities_unchanged':True,'existing_non_ground_artwork_unchanged':True,
            'prior_courtyard_and_workyard_ledgers_unchanged':True,
            'previous_streets_and_cartography_unchanged':True,
            'retired_grass_ids':retired,'new_entity_ids':[item['id'] for item in entities],
            'solid_footprints':supports,'collision_exact_additive_delta':True,
            'collision_added_logical_pixels':int(np.count_nonzero(np.asarray(collision) != np.asarray(before_collision))),
            'navigation_identical_bytes':True,'source_civic_treatments':treatments,
            'source_civic_material_cells':cells,'material_fringe_tiles':1,
            'ground_coverage_native_pixels':int(np.count_nonzero(coverage)),
            'ground_coverage_crop_native':list(crop),'ground_phases':phases}


def compare_view_scope(baseline, folder, capture):
    previous = read(baseline/'observations.json')
    x,y,w,h = read(framework.TOWN)['settlement_commons']['scope_rect']
    results = []
    for name, fixture in capture['views'].items():
        if fixture != previous['views'][name]:
            raise AssertionError(('Production camera fixture changed', name))
        with Image.open(baseline/(name+'.png')) as source:
            before = np.asarray(source.convert('RGB'))
        with Image.open(folder/(name+'.png')) as source:
            after = np.asarray(source.convert('RGB'))
        cx,cy = fixture['camera_logical']
        mask = Image.new('L',(after.shape[1],after.shape[0]))
        ImageDraw.Draw(mask).rectangle((round((x-cx)*2),round((y-cy)*2),
                                       round((x+w-cx)*2)-1,round((y+h-cy)*2)-1),fill=255)
        changes = np.any(before != after, axis=2)
        item = {'name':name,'changed_native_pixels':int(np.count_nonzero(changes)),
                'changed_outside_commons':int(np.count_nonzero(changes & (np.asarray(mask) == 0)))}
        results.append(item)
        if item['changed_outside_commons']:
            raise AssertionError(('Native view changed outside commons', item))
    return results


def gameplay_capture(folder, *, baseline=None, movement=True):
    report = {'fixture':'Fresh production Game, opening disabled, disposable saves/settings, disclosed clear-ground starts. '
              'Residents and routines remain active; no quests, actors or scenery are replaced.',
              'routes':[],'details':[],'doorway_roundtrips':[],'ambient_conversations':[]}
    fixtures = DETAILS
    if baseline is not None:
        details = read(baseline/'commons_details.json')
        fixtures = tuple((name,tuple(item['actual_player_logical']),tuple(item['camera_focus_logical']))
                         for name,item in details['views'].items())
    with tempfile.TemporaryDirectory(prefix='eldenmere-commons-review-') as directory:
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
                    raise AssertionError(('Blocked civic fixture', point))
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
                raise AssertionError(('No clear civic fixture after waiting for actors', label))

            for name,point,focus in fixtures:
                px,py = point
                chosen = choose((point,(px+8,py),(px-8,py),(px,py+8),(px,py-8)),name,focus)
                game.player.facing='front'
                item = {'name':name,'start_fixture':chosen,'baseline_player_logical':list(point),
                        'player_logical':list(game.player.position),'focus_logical':list(focus),
                        'camera_logical':list(game.camera.position())}
                for reduced in (False,True):
                    game.audio.set_reduced_motion(reduced);game._update_grass(0)
                    pictures=[]
                    for elapsed in (0,600):
                        game.elapsed_ms=elapsed;game.draw()
                        if game.window.get_size() != (960,640):raise AssertionError('Non-native civic view')
                        pictures.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
                    name_out=name+('_reduced' if reduced else '')+'.png';pictures[0].save(folder/name_out)
                    changes=framework.changed_pixels(*pictures)
                    if reduced and changes:
                        raise AssertionError(('Reduced-motion civic view changed',name,changes))
                    item['reduced' if reduced else 'normal']={'image':name_out,'changed_pixels_at_600ms':changes,
                        'first_rgb_sha256':framework.digest(pictures[0].tobytes()),
                        'second_rgb_sha256':framework.digest(pictures[1].tobytes())}
                report['details'].append(item)
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
                                raise AssertionError(('Unsafe civic movement',diagnostic(label)))
                            trace.append([round(v,4) for v in game.player.position])
                            if before.distance_to(game.player.position)<.001:stalled=True;break
                        else:raise AssertionError(('Civic route frame budget',diagnostic(label)))
                        if stalled:break
                    if not stalled and game.player.position.distance_to(target)<.02:
                        return {'target':list(target),'trace':trace,'frames':len(trace)-1,'replans':replans,'wait_seconds':waits}
                    replans+=1;waits+=.2;game.update(.2,(0,0),False)
                raise AssertionError(('Civic route remained obstructed',list(target),diagnostic(label)))

            def follow(label, route, running):
                sx,sy=route[0]
                fixture=choose((route[0],(sx+8,sy),(sx-8,sy),(sx,sy+8),(sx,sy-8)),label)
                segments=[drive(game.town,target,running,label) for target in route[1:]]
                return {'label':label,'running':running,'goals':route,'start_fixture':fixture,
                        'segments':segments,'update_frames':sum(item['frames'] for item in segments),
                        'replans':sum(item['replans'] for item in segments),'passed':True}

            if movement:
                # Four independent sides reach the existing well and its south
                # pail/contact lane. Paths remain ordinary collision-aware input.
                routes=(
                    ('well_west',[[384,864],[456,864],[480,900],[526,900]]),
                    ('well_north',[[528,756],[528,780],[576,816],[576,900],[526,900]]),
                    ('well_east',[[720,864],[612,864],[576,900],[526,900]]),
                    ('well_south',[[528,1008],[528,948],[526,900]]),
                    ('school_link',[[528,900],[576,900],[636,804],[672,756],[672,738]]),
                    ('household_links',[[503.5,690],[552,714],[552,780],[576,900],[624,978],[671.5,978]]),
                )
                for name,route in routes:
                    for running in (False,True):
                        for reverse in (False,True):
                            label=name+('_run' if running else '_walk')+('_return' if reverse else '')
                            report['routes'].append(follow(label,list(reversed(route)) if reverse else route,running))
                            print('Passed route:',label,flush=True)
                for running in (False,True):
                    outer=next(door.data for door in game.town.doors if door.data['id']=='school')
                    x,y=outer['anchor']
                    fixture=choose(((x,y+36),(x+24,y+36),(x-24,y+36),(x,y+54)),'school_doorway')
                    approaches=[drive(game.town,(x,y+12),running,'school_front_door')]
                    entry_frames=exit_frames=0
                    for _ in range(240):
                        game.update(1/60,(0,-1),running);entry_frames+=1
                        if game.world is not game.town:break
                    else:raise AssertionError(('School doorway did not enter',diagnostic('school')))
                    interior=game.world
                    if interior.data['id']!='school':raise AssertionError('School doorway entered another scene')
                    back=next(door.data for door in interior.doors if door.data['id']=='courtyard')
                    bx,by=back['anchor']
                    approaches.append(drive(interior,(bx,by-48),running,'school_clear_arrival'))
                    game.update(.6,(0,0),False)
                    approaches.append(drive(interior,(bx,by-12),running,'school_return_approach'))
                    for _ in range(240):
                        game.update(1/60,(0,1),running);exit_frames+=1
                        if game.world is game.town:break
                    else:raise AssertionError(('School doorway did not return',diagnostic('school')))
                    if not game.town.can_stand(game.player.position):raise AssertionError('Blocked school return')
                    game.draw();name='school_roundtrip_'+('run' if running else 'walk')+'.png'
                    pygame.image.save(game.window,str(folder/name))
                    report['doorway_roundtrips'].append({'door':'school','running':running,'interior':interior.data['id'],
                        'start_fixture':fixture,'production_approaches':approaches,'entry_update_frames':entry_frames,
                        'exit_update_frames':exit_frames,'return_position':list(game.player.position),'clear_ground':True,'image':name})

                fixture=choose(((576,914),(636,804),(672,756)),'save_start')
                if not game.save_progress():raise AssertionError(('Civic save failed',game.save_error))
                saved=deepcopy(game.saved_journey)
                saved_state=framework.canonical(framework.meaningful_state(game))
                expected_ledgers={key:deepcopy(game.town.data[key]) for key in
                                  ('settlement_dressing','settlement_workyards','settlement_commons')}
                entity_ids=[item['id'] for item in commons_entities(game.town.data)]

                def resume(name, payload):
                    if not game.save_store.write(payload):raise AssertionError('Disposable checkpoint write failed')
                    game.music.stop();restored=framework.Game(**options)
                    try:
                        restored.audio.set_music(0);restored.audio.set_effects(0)
                        if not restored.begin_journey(True):raise AssertionError(('Civic Continue failed',restored.save_error))
                        restored.opening_fade=restored.transfer_cooldown=0
                        ids=[item['id'] for item in commons_entities(restored.town.data)]
                        if ids!=entity_ids or len(ids)!=len(set(ids)):raise AssertionError('Continue lost/duplicated civic entities')
                        if any(restored.town.data[key]!=value for key,value in expected_ledgers.items()):
                            raise AssertionError('Continue changed an integrated district ledger')
                        if not restored.world.can_stand(restored.player.position):raise AssertionError('Continue restored blocked ground')
                        supports=restored.town.data['settlement_commons']['solid_footprints']
                        for support in supports:
                            sx,sy,sw,sh=support['rect']
                            if not all(restored.town.blocked.get_at((px,py))
                                       for py in range(sy,sy+sh) for px in range(sx,sx+sw)):
                                raise AssertionError(('Continue lost support',support['id']))
                        if framework.canonical(framework.meaningful_state(restored))!=saved_state:
                            raise AssertionError('Continue changed quest/party/inventory/flags')
                        if name=='continue_commons':
                            restored.draw();pygame.image.save(restored.window,str(folder/(name+'.png')))
                        return {'saved_position_fixture':payload['player']['position'],'restored_scene':restored.world.data['id'],
                                'position':list(restored.player.position),'clear_ground':True,'new_entity_ids':ids,
                                'solid_supports_preserved':len(supports),'all_district_ledgers_unchanged':True,
                                'quest_party_inventory_flags_unchanged':True}
                    finally:restored.music.stop()
                report['save_continue']=resume('continue_commons',saved)
                report['save_continue']['start_fixture']=fixture
                recoveries=[]
                for support in expected_ledgers['settlement_commons']['solid_footprints']:
                    sx,sy,sw,sh=support['rect'];position=[sx+sw/2,sy+sh/2]
                    if game.town.can_stand(position):raise AssertionError(('Support checkpoint fixture is clear',support['id']))
                    payload=deepcopy(saved);payload['player']['position']=position
                    result=resume(support['id'],payload)
                    if result['position']==position:raise AssertionError('Blocked checkpoint position did not recover')
                    recoveries.append({'support':support['id'],'fixture':'Disposable older-checkpoint player coordinate inside new support; all progress fields unchanged.',**result})
                report['blocked_checkpoint_recoveries']=recoveries
            report['quest_party_inventory_flags_unchanged']=initial==framework.canonical(framework.meaningful_state(game))
            if not report['quest_party_inventory_flags_unchanged']:raise AssertionError('Civic review changed gameplay progress')
        finally:game.music.stop();pygame.quit()
    return report


def capture(folder, baseline=None, *, movement=True):
    folder.mkdir(parents=True,exist_ok=True)
    production=framework.production_snapshot()
    comparison=compare_baseline(baseline,folder) if baseline is not None else None
    framework.capture(folder)
    report=read(folder/'observations.json')
    report['scope']='Native production commons fixtures, strict scoped differences, real input/doorway/Continue checks; no quest playthrough.'
    report['baseline_comparison']=comparison
    if baseline is not None:report['native_view_comparison']=compare_view_scope(baseline,folder,report)
    report['gameplay']=gameplay_capture(folder,baseline=baseline,movement=movement)
    if framework.production_snapshot()!=production:raise AssertionError('Production changed during commons capture')
    report['capture_png_sha256']={path.name:framework.digest(path.read_bytes()) for path in sorted(folder.glob('*.png'))}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Commons review: {len(report['views'])} native views, {len(report['gameplay']['routes'])} movement checks; "
          f"baseline {'verified' if baseline is not None else 'not requested'}.")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-dir','--baseline',type=Path)
    parser.add_argument('--skip-movement',action='store_true',help='Only static views; omit movement/doorway/Continue checks')
    args=parser.parse_args()
    capture(args.output.resolve(),args.baseline_dir.resolve() if args.baseline_dir else None,movement=not args.skip_movement)
