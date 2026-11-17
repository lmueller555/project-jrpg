"""Review Serene's courtyard dressing through production rendering and movement.

Fixtures explicitly place the player/camera on clear ground. Ambient NPCs stay
present, and movement uses Game.update with production pathfinding. Disposable
saves isolate the Continue smoke check from the player's journey.
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

import numpy as np
from PIL import Image, ImageDraw
import pygame

from npc_routines import find_path

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_courtyard'
PREFIX = 'settlement.courtyard.'
GROUND_PREFIX = 'assets/maps/eldenmere/town_hd/town/chunks/'
ALLOWED_FIELDS = {'entities', 'grass', 'collision', 'ground_overlays', 'overview',
                  'settlement_dressing'}
DETAILS = (
    ('courtyard_west', (300, 348), (288, 288)),
    ('courtyard_door', (384, 320), (384, 270)),
    ('courtyard_east', (456, 336), (504, 288)),
    ('courtyard_stairs', (384, 396), (384, 360)),
)


def read(path):
    return json.loads(Path(path).read_text())


def courtyard_entities(town):
    return [record for record in town['entities'] if record['id'].startswith(PREFIX)]


def garden_coverage(town, report):
    """A native one-tile transition rim bounds changes to existing ground."""
    size = tuple(value*2 for value in town['size_pixels'])
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    tile = town.get('tile_size', 24)
    for x, y in report['garden_cells']:
        draw.rectangle(((x-1)*tile*2, (y-1)*tile*2,
                        (x+2)*tile*2-1, (y+2)*tile*2-1), fill=255)
    scope = Image.new('L', size)
    x, y, w, h = report['scope_rect']
    ImageDraw.Draw(scope).rectangle((x*2,y*2,(x+w)*2-1,(y+h)*2-1), fill=255)
    if np.any((np.asarray(mask) != 0) & (np.asarray(scope) == 0)):
        raise AssertionError('Garden transition rim leaves the declared courtyard scope')
    return mask


def compare_baseline(baseline, folder):
    """Verify explicit additions; no unrelated map/art changes are accepted."""
    original = read(baseline/'town.json')
    town = read(framework.TOWN)
    report = town['settlement_dressing']
    new_entities = courtyard_entities(town)
    if new_entities != report['entities']:
        raise AssertionError('Dressing registry and actual new entity records differ')
    if len({record['id'] for record in new_entities}) != len(new_entities):
        raise AssertionError('Duplicate courtyard entity')
    scope_x,scope_y,scope_w,scope_h=report['scope_rect']
    for entity in new_entities:
        x,y=entity['position'];w,h=entity['logical_size']
        if (entity['artwork_pixels_per_world_pixel']!=2 or x<scope_x or y<scope_y
                or x+w>scope_x+scope_w or y+h>scope_y+scope_h):
            raise AssertionError(('New artwork leaves the native courtyard scope',entity['id']))
        for path in entity['frames']:
            with Image.open(ROOT/path) as source:
                if source.size!=(round(w*2),round(h*2)):
                    raise AssertionError(('New artwork lost native density',entity['id'],path))
    retained = [record for record in town['entities'] if not record['id'].startswith(PREFIX)]
    if retained != original['entities']:
        raise AssertionError('Existing entity ownership, geometry or artwork changed')
    retired = report['retired_grass_ids']
    if len(set(retired)) != len(retired):
        raise AssertionError('Duplicate grass retirement declaration')
    prior_grass = original['grass']['instances']
    retired_records = [record for record in prior_grass if record['id'] in retired]
    if sorted(record['id'] for record in retired_records) != sorted(retired):
        raise AssertionError('Retirement declares an unknown pre-existing grass instance')
    if retired_records != report['retired_grass_records']:
        raise AssertionError('Retirement ledger does not preserve the original grass records')
    for record in retired_records:
        x,y=record['position']
        if not (scope_x<=x<=scope_x+scope_w and scope_y<=y<=scope_y+scope_h):
            raise AssertionError(('Grass retirement leaves the courtyard',record['id']))
    expected_grass = deepcopy(original['grass'])
    expected_grass['instances'] = [record for record in prior_grass if record['id'] not in retired]
    if town['grass'] != expected_grass:
        raise AssertionError('Grass changes exceed the explicit retirement ledger')
    changed_fields = sorted(key for key in original.keys() | town.keys()
                            if original.get(key) != town.get(key))
    if set(changed_fields)-ALLOWED_FIELDS:
        raise AssertionError(('Unrelated map fields changed', changed_fields))

    current = framework.production_snapshot()
    previous = read(baseline/'observations.json')['production']
    allowed = {current['town_map'], town['collision'], town['overview'], original['overview']}
    added_images = set(framework.image_paths(new_entities))
    old_files, new_files = previous['active_files'], current['active_files']
    changed_files = sorted(path for path in old_files.keys() | new_files.keys()
                           if old_files.get(path) != new_files.get(path))
    unexpected = [path for path in changed_files
                  if path not in allowed and not path.startswith(GROUND_PREFIX)
                  and not (path in added_images and path not in old_files)]
    if unexpected:
        raise AssertionError(('Existing non-ground artwork changed', unexpected))

    with Image.open(baseline/'collision.png') as source:
        expected_collision = source.convert('L')
    painter = ImageDraw.Draw(expected_collision)
    for footprint in report['solid_footprints']:
        x, y, w, h = footprint['rect']
        if any(type(v) is not int for v in (x,y,w,h)) or min(w,h) <= 0:
            raise AssertionError(('Invalid logical solid footprint', footprint))
        painter.rectangle((x,y,x+w-1,y+h-1), fill=255)
    with Image.open(ROOT/town['collision']) as source:
        collision = source.convert('L')
    if collision.size != expected_collision.size or collision.tobytes() != expected_collision.tobytes():
        raise AssertionError('Collision is not precisely baseline plus the declared solid footprints')
    if (baseline/'navigation_allowed.png').read_bytes() != (ROOT/town['navigation_allowed']).read_bytes():
        raise AssertionError('Navigation changed')

    mask = garden_coverage(town, report)
    mask.save(folder/'garden_ground_coverage.png')
    coverage = np.asarray(mask) != 0
    phases = []
    for phase in range(6):
        after = native_ground(town, phase*200)
        with Image.open(baseline/f'ground_phase_{phase}.png') as source:
            before = source.convert('RGBA')
        if before.size != after.size:
            raise AssertionError('Ground dimensions changed')
        changed = np.any(np.asarray(before) != np.asarray(after), axis=2)
        outside = int(np.count_nonzero(changed & ~coverage))
        phases.append({'phase': phase, 'changed_native_pixels': int(np.count_nonzero(changed)),
                       'changed_outside_garden_rim': outside,
                       'before_rgba_sha256': framework.digest(before.tobytes()),
                       'after_rgba_sha256': framework.digest(after.tobytes())})
        if outside:
            raise AssertionError(('Ground changes leave the garden transition rim', phases[-1]))

    for stale in folder.glob('before_*.png'):
        stale.unlink()
    for source in sorted(baseline.glob('*.png')):
        if source.name.startswith('ground_phase_') or source.name in {
                'collision.png', 'navigation_allowed.png', 'protection_plan_diagnostic.png'}:
            continue
        shutil.copyfile(source, folder/('before_'+source.name))
    for source, destination in (('observations.json','before_observations.json'),
                                ('town.json','before_town.json'),
                                ('baseline_revision.json','before_revision.json'),
                                ('courtyard_details.json','before_courtyard_details.json')):
        if (baseline/source).exists():
            shutil.copyfile(baseline/source, folder/destination)
        elif (folder/destination).exists():
            (folder/destination).unlink()
    return {'baseline_revision': read(baseline/'baseline_revision.json'),
            'changed_map_fields': changed_fields, 'changed_active_files': changed_files,
            'existing_entities_unchanged': True, 'existing_non_ground_artwork_unchanged': True,
            'retired_grass_ids': retired, 'new_entity_ids': [item['id'] for item in new_entities],
            'solid_footprints': report['solid_footprints'],
            'collision_exact_additive_delta': True, 'navigation_identical_bytes': True,
            'garden_coverage_native_pixels': int(np.count_nonzero(coverage)),
            'ground_phases': phases}


def compare_view_scope(baseline, folder, capture):
    """Actual native view pixels outside the courtyard must remain identical."""
    previous = read(baseline/'observations.json')
    town = read(framework.TOWN)
    x, y, w, h = town['settlement_dressing']['scope_rect']
    result = []
    for name, fixture in capture['views'].items():
        if fixture != previous['views'][name]:
            raise AssertionError(('Production camera fixture changed', name))
        with Image.open(baseline/(name+'.png')) as raw:
            before = np.asarray(raw.convert('RGB'))
        with Image.open(folder/(name+'.png')) as raw:
            after = np.asarray(raw.convert('RGB'))
        camera_x, camera_y = fixture['camera_logical']
        mask = Image.new('L', (after.shape[1],after.shape[0]))
        ImageDraw.Draw(mask).rectangle((round((x-camera_x)*2),round((y-camera_y)*2),
                                       round((x+w-camera_x)*2)-1,round((y+h-camera_y)*2)-1), fill=255)
        changes = np.any(before != after, axis=2)
        outside = int(np.count_nonzero(changes & (np.asarray(mask) == 0)))
        result.append({'name':name, 'changed_native_pixels':int(np.count_nonzero(changes)),
                       'changed_outside_courtyard':outside})
        if outside:
            raise AssertionError(('Native view changed outside courtyard', result[-1]))
    return result


def gameplay_capture(folder, *, movement=True):
    report = {'fixture':'Fresh production Game; opening disabled; disclosed clear-ground starts. '
              'Ambient actors stay active. No quest or scenery replacements.', 'routes':[], 'details':[]}
    with tempfile.TemporaryDirectory(prefix='eldenmere-courtyard-review-') as directory:
        temporary = Path(directory)
        options = dict(fullscreen=False,window_size=(960,640),start_on_title=True,
                       save_path=temporary/'journey.json',settings_path=temporary/'settings.json')
        game = framework.Game(**options)
        try:
            game.on_title=False;game.opening.restore({'version':1,'stage':'disabled'})
            game.opening_fade=game.transfer_cooldown=0
            game.audio.set_music(0);game.audio.set_effects(0);game.world=game.town
            initial=framework.canonical(framework.meaningful_state(game))

            def place(position, focus=None):
                if not game.town.can_stand(position):
                    raise AssertionError(('Blocked courtyard review fixture',position))
                game.player.position.update(position);game.player.moving=game.player.running=False
                game.player.walk_ms=0;game.location_label=None;game.location_seconds=0
                game.saves.notice_seconds=0;game.transfer_cooldown=0;game.camera.reset()
                if focus is not None:game.camera.focus(focus,duration=0)

            def clear_public_fixture(candidates,label):
                """Choose a disclosed clear start while leaving ambient actors present."""
                for _ in range(20):
                    for position in candidates:
                        if game.town.can_stand(position):
                            place(position)
                            return {'label':label,'candidates':[list(p) for p in candidates],
                                    'selected':list(position)}
                    game.update(.2,(0,0),False)
                raise AssertionError(('No clear public fixture after waiting for ambient actors',label))

            for name, player, focus in DETAILS:
                place(player,focus)
                item={'name':name,'player_logical':list(player),'focus_logical':list(focus)}
                for reduced in (False,True):
                    game.audio.set_reduced_motion(reduced);game._update_grass(0)
                    pictures=[]
                    for elapsed in (0,600):
                        game.elapsed_ms=elapsed;game.draw()
                        pictures.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
                    suffix='_reduced' if reduced else ''
                    filename=name+suffix+'.png';pictures[0].save(folder/filename)
                    key='reduced' if reduced else 'normal'
                    item[key]={'image':filename,'changed_pixels_at_600ms':framework.changed_pixels(*pictures),
                               'first_rgb_sha256':framework.digest(pictures[0].tobytes()),
                               'second_rgb_sha256':framework.digest(pictures[1].tobytes())}
                report['details'].append(item)
            game.audio.set_reduced_motion(False);game._update_grass(0)

            def follow(label, route, running):
                place(route[0]);trace=[list(game.player.position)];replans=0
                for target in route[1:]:
                    for attempt in range(6):
                        path=find_path(game.world,game.player.position,target,game.world.probe_size,None)
                        if path is None:raise AssertionError(('No courtyard path',label,target))
                        stalled=False
                        for point in path:
                            goal=pygame.Vector2(point)
                            for _ in range(3000):
                                delta=goal-game.player.position
                                if delta.length()<.01:break
                                before=game.player.position.copy()
                                game.update(min(1/30,delta.length()/(108 if running else 72)),delta,running)
                                if game.world is not game.town or not game.world.can_stand(game.player.position):
                                    raise AssertionError(('Unsafe courtyard movement',label,list(game.player.position)))
                                trace.append([round(value,4) for value in game.player.position])
                                if before.distance_to(game.player.position)<.001:stalled=True;break
                            else:raise AssertionError(('Courtyard movement budget',label))
                            if stalled:break
                        if not stalled:break
                        replans+=1;game.update(.2,(0,0),False)
                    else:raise AssertionError(('Courtyard route remained obstructed',label,trace[-1]))
                    if game.player.position.distance_to(target)>.02:
                        raise AssertionError(('Courtyard route missed target',label,target))
                game.draw();filename='movement_'+label+'.png';pygame.image.save(game.window,str(folder/filename))
                return {'label':label,'running':running,'goals':route,'trace':trace,
                        'update_frames':len(trace)-1,'replans':replans,'image':filename,'passed':True}

            def door_approach(world,target,running,label):
                """Walk around live household actors rather than through them."""
                frames=replans=0;trace=[list(game.player.position)]
                for attempt in range(30):
                    if game.world is not world:raise AssertionError(('Unexpected approach transfer',label))
                    path=find_path(world,game.player.position,target,world.probe_size,None)
                    if path is None:
                        replans+=1;game.update(.2,(0,0),False);continue
                    stalled=False
                    for waypoint in path:
                        goal=pygame.Vector2(waypoint)
                        for _ in range(3000):
                            delta=goal-game.player.position
                            if delta.length()<.01:break
                            before=game.player.position.copy()
                            game.update(min(1/30,delta.length()/(108 if running else 72)),delta,running)
                            frames+=1;trace.append([round(v,4) for v in game.player.position])
                            if game.world is not world or not world.can_stand(game.player.position):
                                raise AssertionError(('Unsafe doorway approach',label,list(game.player.position)))
                            if before.distance_to(game.player.position)<.001:stalled=True;break
                        else:raise AssertionError(('Doorway approach frame budget',label))
                        if stalled:break
                    if not stalled and game.player.position.distance_to(target)<.02:
                        return {'label':label,'target':list(target),'frames':frames,'replans':replans,'trace':trace}
                    replans+=1;game.update(.2,(0,0),False)
                raise AssertionError(('Live doorway approach remained obstructed',label,list(game.player.position)))

            if movement:
                routes=(('public_apron',[[268,306],[386,306],[444,306]]),
                        ('stairs',[[384,420],[384,336],[432,318]]),
                        ('gardener_crossing',[[340,334],[440,334],[462,334]]),
                        ('eastern_garden_aisle',[[600,252],[600,324],[504,324],[480,336]]))
                for name, route in routes:
                    for running in (False,True):
                        for reverse in (False,True):
                            label=name+('_run' if running else '_walk')+('_return' if reverse else '')
                            report['routes'].append(follow(label,list(reversed(route)) if reverse else route,running))
                report['doorway_roundtrips']=[]
                for running in (False,True):
                    start=clear_public_fixture(((386,330),(410,318),(362,318),(400,330),(372,330)),'doorway_start')
                    entry_frames=exit_frames=0
                    approaches=[door_approach(game.town,(386,306),running,'front_door')]
                    for _ in range(240):
                        game.update(1/60,(0,-1),running);entry_frames+=1
                        if game.world is not game.town:break
                    else:raise AssertionError(('Household doorway did not enter',running,list(game.player.position),
                        game.social.script_identifier,game.social.active,game.social.locked,
                        [(a.data['id'],list(a.position)) for a in game.world.npcs
                         if a.position.distance_to(game.player.position)<80]))
                    interior=game.world
                    if interior.data['id']!='sanctuary_hall':
                        raise AssertionError(('Door entered an unexpected scene',interior.data['id']))
                    return_door=next(door for door in interior.doors if door.data['id']=='courtyard')
                    # Walk clear of the arrival contact to rearm the ordinary
                    # return sensor; never reset a transition guard to force it.
                    clear_y=return_door.data['anchor'][1]-48
                    approaches.append(door_approach(interior,(return_door.data['anchor'][0],clear_y),running,'clear_arrival_contact'))
                    game.update(.6,(0,0),False)
                    approaches.append(door_approach(interior,(return_door.data['anchor'][0],return_door.data['anchor'][1]-12),running,'return_to_door'))
                    for _ in range(240):
                        game.update(1/60,(0,1),running);exit_frames+=1
                        if game.world is game.town:break
                    else:raise AssertionError(('Household doorway did not return',running,list(game.player.position)))
                    if not game.town.can_stand(game.player.position):
                        raise AssertionError('Household doorway returned onto blocked ground')
                    game.draw();name='doorway_'+('run' if running else 'walk')+'.png'
                    pygame.image.save(game.window,str(folder/name))
                    report['doorway_roundtrips'].append({'running':running,'interior':interior.data['id'],
                        'start_fixture':start,
                        'entry_update_frames':entry_frames,'exit_update_frames':exit_frames,
                        'production_approaches':approaches,
                        'return_position':list(game.player.position),'clear_ground':True,'image':name})
                save_fixture=clear_public_fixture(((386,320),(410,318),(362,318),(400,320),(372,320)),'save_start')
                if not game.save_progress():raise AssertionError(('Courtyard save failed',game.save_error))
                before_ids=[item['id'] for item in courtyard_entities(game.town.data)]
                saved_state=framework.canonical(framework.meaningful_state(game))
                game.music.stop()
                restored=framework.Game(**options)
                try:
                    restored.audio.set_music(0);restored.audio.set_effects(0)
                    if not restored.begin_journey(True):raise AssertionError(('Courtyard Continue failed',restored.save_error))
                    restored.opening_fade=restored.transfer_cooldown=0
                    after_ids=[item['id'] for item in courtyard_entities(restored.town.data)]
                    if after_ids!=before_ids or len(set(after_ids))!=len(after_ids):
                        raise AssertionError('Continue duplicated or lost courtyard entities')
                    if not restored.world.can_stand(restored.player.position):
                        raise AssertionError('Continue restored the player into an obstacle')
                    supports=restored.town.data['settlement_dressing']['solid_footprints']
                    for support in supports:
                        x,y,w,h=support['rect']
                        if not all(restored.town.blocked.get_at((px,py))
                                   for py in range(y,y+h) for px in range(x,x+w)):
                            raise AssertionError(('Continue lost courtyard solid support',support['id']))
                    if framework.canonical(framework.meaningful_state(restored))!=saved_state:
                        raise AssertionError('Continue changed quest/party/inventory/flags')
                    restored.draw();pygame.image.save(restored.window,str(folder/'continue_courtyard.png'))
                    report['save_continue']={'saved':True,'continued':True,'new_entity_ids':after_ids,
                                             'start_fixture':save_fixture,
                                             'position':list(restored.player.position),'clear_ground':True,
                                             'solid_footprints_preserved':len(supports),
                                             'quest_party_inventory_flags_unchanged':True}
                finally:restored.music.stop()
            report['quest_party_inventory_flags_unchanged']=initial==framework.canonical(framework.meaningful_state(game))
            if not report['quest_party_inventory_flags_unchanged']:
                raise AssertionError('Courtyard fixture/movement changed gameplay progress')
        finally:game.music.stop();pygame.quit()
    return report


def capture(folder, baseline=None, *, movement=True):
    folder.mkdir(parents=True,exist_ok=True)
    production=framework.production_snapshot()
    comparison=compare_baseline(baseline,folder) if baseline is not None else None
    framework.capture(folder)
    report=read(folder/'observations.json')
    report['scope']='Native production courtyard fixtures, strict scoped differences and real input/Continue smoke checks; no quest playthrough.'
    report['baseline_comparison']=comparison
    if baseline is not None:report['native_view_comparison']=compare_view_scope(baseline,folder,report)
    report['gameplay']=gameplay_capture(folder,movement=movement)
    if framework.production_snapshot()!=production:
        raise AssertionError('Production changed during courtyard capture; rerun after writers finish')
    report['capture_png_sha256']={path.name:framework.digest(path.read_bytes()) for path in sorted(folder.glob('*.png'))}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Courtyard review: {len(report['views'])} native views, {len(report['gameplay']['routes'])} movement checks; "
          f"baseline {'verified' if baseline is not None else 'not requested'}.")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-dir','--baseline',type=Path)
    parser.add_argument('--skip-movement',action='store_true',help='Capture static views only; omit walking and Continue smoke checks')
    arguments=parser.parse_args()
    capture(arguments.output.resolve(),arguments.baseline_dir.resolve() if arguments.baseline_dir else None,
            movement=not arguments.skip_movement)
