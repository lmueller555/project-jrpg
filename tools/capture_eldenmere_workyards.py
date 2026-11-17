"""Review workshop and mill-yard dressing through production rendering and movement.

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
from PIL import Image, ImageChops, ImageDraw
import pygame

from npc_routines import find_path

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_workyards'
PREFIX = 'settlement.workyards.'
GROUND_PREFIX = 'assets/maps/eldenmere/town_hd/town/chunks/'
ALLOWED_FIELDS = {'entities', 'grass', 'collision', 'ground_overlays', 'overview',
                  'settlement_workyards'}
DETAILS = (
    ('workshop_front', (670, 470), (636, 420)),
    ('workshop_west', (540, 470), (540, 380)),
    ('mill_landing', (984, 396), (984, 338)),
    ('mill_service', (1032, 496), (1032, 420)),
)


def read(path):
    return json.loads(Path(path).read_text())


def workyard_entities(town):
    return [record for record in town['entities'] if record['id'].startswith(PREFIX)]


def frame_paths(record):
    return record.get('frames') or [record['image']]


def ground_coverage(town, report):
    """Bound dirt transitions and registered flat dressing at native density."""
    size = tuple(value*2 for value in town['size_pixels'])
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    tile = town.get('tile_size', 24)
    for x, y in report['ground_cells']:
        draw.rectangle(((x-1)*tile*2, (y-1)*tile*2,
                        (x+2)*tile*2-1, (y+2)*tile*2-1), fill=255)
    for entity in report.get('ground_entities', []):
        x, y = entity['position']
        for path in frame_paths(entity):
            with Image.open(ROOT/path) as source:
                alpha = source.convert('RGBA').getchannel('A')
            layer = Image.new('L', size)
            layer.paste(alpha, (round(x*2), round(y*2)))
            mask = ImageChops.lighter(mask, layer)
    scope = Image.new('L', size)
    x, y, w, h = report['scope_rect']
    ImageDraw.Draw(scope).rectangle((x*2,y*2,(x+w)*2-1,(y+h)*2-1), fill=255)
    if np.any((np.asarray(mask) != 0) & (np.asarray(scope) == 0)):
        raise AssertionError('Ground transition rim or flat dressing leaves the workyard scope')
    return mask


def compare_baseline(baseline, folder):
    """Verify explicit additions; no unrelated map/art changes are accepted."""
    original = read(baseline/'town.json')
    town = read(framework.TOWN)
    report = town['settlement_workyards']
    new_entities = workyard_entities(town)
    if new_entities != report['entities']:
        raise AssertionError('Dressing registry and actual new entity records differ')
    if len({record['id'] for record in new_entities}) != len(new_entities):
        raise AssertionError('Duplicate workyard entity')
    flat_entities = report.get('ground_entities', [])
    all_new_entities = [*new_entities, *flat_entities]
    if len({record['id'] for record in all_new_entities}) != len(all_new_entities):
        raise AssertionError('World and flat workyard owners overlap')
    if town.get('settlement_dressing') != original.get('settlement_dressing'):
        raise AssertionError('Previously integrated household courtyard ledger changed')
    scope_x,scope_y,scope_w,scope_h=report['scope_rect']
    for entity in all_new_entities:
        x,y=entity['position'];w,h=entity['logical_size']
        if (entity['artwork_pixels_per_world_pixel']!=2 or x<scope_x or y<scope_y
                or x+w>scope_x+scope_w or y+h>scope_y+scope_h):
            raise AssertionError(('New artwork leaves the native workyard scope',entity['id']))
        for path in frame_paths(entity):
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
            raise AssertionError(('Grass retirement leaves the workyard',record['id']))
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
    added_images = set(framework.image_paths(all_new_entities))
    old_files, new_files = previous['active_files'], current['active_files']
    changed_files = sorted(path for path in old_files.keys() | new_files.keys()
                           if old_files.get(path) != new_files.get(path))
    unexpected = [path for path in changed_files
                  if path not in allowed and not path.startswith(GROUND_PREFIX)
                  and not (path in added_images and path not in old_files)]
    if unexpected:
        raise AssertionError(('Existing non-ground artwork changed', unexpected))

    with Image.open(baseline/'collision.png') as source:
        before_collision = source.convert('L')
    expected_collision = before_collision.copy()
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
    added_collision = int(np.count_nonzero(np.asarray(collision) != np.asarray(before_collision)))

    mask = ground_coverage(town, report)
    mask.save(folder/'workyard_ground_coverage.png')
    coverage = np.asarray(mask) != 0
    phases = []
    crossings = read(ROOT/'assets/maps/eldenmere/town_hd/manifest.json')['crossings']
    crossing_checks = []
    for phase in range(6):
        after = native_ground(town, phase*200)
        with Image.open(baseline/f'ground_phase_{phase}.png') as source:
            before = source.convert('RGBA')
        if before.size != after.size:
            raise AssertionError('Ground dimensions changed')
        changed = np.any(np.asarray(before) != np.asarray(after), axis=2)
        outside = int(np.count_nonzero(changed & ~coverage))
        phases.append({'phase': phase, 'changed_native_pixels': int(np.count_nonzero(changed)),
                       'changed_outside_ground_rim': outside,
                       'before_rgba_sha256': framework.digest(before.tobytes()),
                       'after_rgba_sha256': framework.digest(after.tobytes())})
        if outside:
            raise AssertionError(('Ground changes leave the ground transition rim', phases[-1]))
        for name, assembly in crossings.items():
            ox,oy=assembly['position'];x,y,w,h=assembly['walk_surface']
            rect=(round((ox+x)*2),round((oy+y)*2),round((ox+x+w)*2),round((oy+y+h)*2))
            first,second=before.crop(rect),after.crop(rect)
            if first.tobytes()!=second.tobytes():
                raise AssertionError(('Existing crossing surface changed',name,phase))
            crossing_checks.append({'crossing':name,'phase':phase,'identical_native_surface':True,
                                    'surface_rgba_sha256':framework.digest(second.tobytes())})

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
                                ('workyard_details.json','before_workyard_details.json')):
        if (baseline/source).exists():
            shutil.copyfile(baseline/source, folder/destination)
        elif (folder/destination).exists():
            (folder/destination).unlink()
    return {'baseline_revision': read(baseline/'baseline_revision.json'),
            'changed_map_fields': changed_fields, 'changed_active_files': changed_files,
            'existing_entities_unchanged': True, 'existing_non_ground_artwork_unchanged': True,
            'retired_grass_ids': retired, 'new_entity_ids': [item['id'] for item in new_entities],
            'ground_entity_ids': [item['id'] for item in flat_entities],
            'prior_courtyard_unchanged': True,
            'solid_footprints': report['solid_footprints'],
            'collision_exact_additive_delta': True, 'collision_added_logical_pixels':added_collision,
            'navigation_identical_bytes': True, 'crossing_surface_checks':crossing_checks,
            'ground_coverage_native_pixels': int(np.count_nonzero(coverage)),
            'ground_phases': phases}


def compare_view_scope(baseline, folder, capture):
    """Actual native view pixels outside the workyard must remain identical."""
    previous = read(baseline/'observations.json')
    town = read(framework.TOWN)
    x, y, w, h = town['settlement_workyards']['scope_rect']
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
                       'changed_outside_workyard':outside})
        if outside:
            raise AssertionError(('Native view changed outside workyard', result[-1]))
    return result


def gameplay_capture(folder, *, baseline=None, movement=True):
    """Exercise the current working spaces without replacing actors or quests."""
    report = {'fixture': 'Fresh production Game; opening disabled; disclosed clear-ground starts. '
              'Ambient actors remain active. No quest or scenery replacement.',
              'routes': [], 'details': [], 'doorway_roundtrips': [], 'ambient_conversations': []}
    fixtures = DETAILS
    if baseline is not None and (baseline/'workyard_details.json').is_file():
        fixtures = tuple((item['name'], tuple(item['actual_player']), tuple(item['camera_focus']))
                         for item in read(baseline/'workyard_details.json')['fixtures'])
    with tempfile.TemporaryDirectory(prefix='eldenmere-workyards-review-') as directory:
        temporary = Path(directory)
        options = dict(fullscreen=False, window_size=(960,640), start_on_title=True,
                       save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
        game = framework.Game(**options)
        try:
            game.on_title = False
            game.opening.restore({'version': 1, 'stage': 'disabled'})
            game.opening_fade = game.transfer_cooldown = 0
            game.audio.set_music(0);game.audio.set_effects(0)
            game.world = game.town
            initial = framework.canonical(framework.meaningful_state(game))
            bridge_images = {}

            def place(position, focus=None):
                if game.world is not game.town or not game.town.can_stand(position):
                    raise AssertionError(('Blocked workyard review fixture', position))
                game.player.position.update(position)
                game.player.moving = game.player.running = False
                game.player.walk_ms = 0
                game.location_label = None;game.location_seconds = 0
                game.saves.notice_seconds = game.transfer_cooldown = 0
                game.camera.reset()
                if focus is not None:game.camera.focus(focus, duration=0)

            def choose_fixture(candidates, label, focus=None):
                for _ in range(30):
                    for point in candidates:
                        if game.town.can_stand(point):
                            place(point, focus)
                            return {'label': label, 'candidates': [list(p) for p in candidates],
                                    'selected': list(point)}
                    game.update(.2, (0,0), False)
                raise AssertionError(('No clear workyard fixture after waiting for actors', label))

            for name, player, focus in fixtures:
                px,py = player
                candidates = (player, (px+8,py), (px-8,py), (px,py+8), (px,py-8),
                              (px+16,py), (px-16,py), (px,py+16))
                chosen = choose_fixture(candidates, name, focus)
                game.player.facing = 'front'
                item = {'name': name, 'start_fixture': chosen, 'baseline_player_logical': list(player),
                        'player_logical': list(game.player.position), 'focus_logical': list(focus),
                        'camera_logical': list(game.camera.position())}
                for reduced in (False, True):
                    game.audio.set_reduced_motion(reduced);game._update_grass(0)
                    pictures = []
                    for elapsed in (0,600):
                        game.elapsed_ms = elapsed;game.draw()
                        pictures.append(Image.frombytes('RGB',game.window.get_size(),
                                                        pygame.image.tobytes(game.window,'RGB')))
                    filename = name+('_reduced' if reduced else '')+'.png'
                    pictures[0].save(folder/filename)
                    changes = framework.changed_pixels(*pictures)
                    if reduced and changes:
                        raise AssertionError(('Reduced-motion workyard view changed', name, changes))
                    item['reduced' if reduced else 'normal'] = {
                        'image': filename, 'changed_pixels_at_600ms': changes,
                        'first_rgb_sha256': framework.digest(pictures[0].tobytes()),
                        'second_rgb_sha256': framework.digest(pictures[1].tobytes())}
                report['details'].append(item)
            game.audio.set_reduced_motion(False);game._update_grass(0)

            def diagnostic(label):
                return {'label': label, 'position': list(game.player.position),
                        'scene': game.world.data['id'],
                        'social_script': game.social.script_identifier,
                        'social_active': game.social.active, 'social_locked': game.social.locked,
                        'nearby_actors': [(actor.data['id'],list(actor.position))
                                          for actor in game.world.npcs
                                          if actor.position.distance_to(game.player.position)<80]}

            def drive(world, target, running, label):
                """Use production collision/pathfinding, retaining moving residents."""
                target = pygame.Vector2(target)
                trace = [list(game.player.position)];replans = 0
                for _ in range(30):
                    if game.world is not world:
                        raise AssertionError(('Unexpected scene transfer', diagnostic(label)))
                    if game.player.position.distance_to(target)<.02:
                        return {'target': list(target), 'trace': trace,
                                'frames': len(trace)-1, 'replans': replans}
                    if game.social.scripted:
                        raise AssertionError(('Review route entered a scripted exchange', diagnostic(label)))
                    # The legacy social.locked flag reserves an ambient exchange;
                    # it deliberately does not stop movement or ordinary doors.
                    if game.social.actor is not None:
                        conversation=game.social.conversation or {}
                        event={'actor':game.social.actor.data['id'],'conversation':conversation.get('id'),
                               'label':label,'player_position':list(game.player.position)}
                        if not any(item['actor']==event['actor'] and item['conversation']==event['conversation']
                                   for item in report['ambient_conversations']):
                            report['ambient_conversations'].append(event)
                    # The NPC planner searches an even two-unit lattice; real
                    # entrances may keep odd or half-unit anchors. Plan to the
                    # nearest clear lattice point, then walk the short exact
                    # approach with ordinary player input and collision checks.
                    grid=(round(target.x/2)*2,round(target.y/2)*2)
                    candidates=sorted({(grid[0]+dx,grid[1]+dy)
                                       for dx in (-2,0,2) for dy in (-2,0,2)},
                                      key=lambda point:pygame.Vector2(point).distance_squared_to(target))
                    lattice=next((point for point in candidates if world.can_stand(point)),None)
                    path=None if lattice is None else find_path(world,game.player.position,lattice,world.probe_size,None)
                    if path is None:
                        replans += 1;game.update(.2,(0,0),False);continue
                    if not path or pygame.Vector2(path[-1]).distance_to(target)>.01:
                        path.append(tuple(target))
                    stalled = False
                    for waypoint in path:
                        goal = pygame.Vector2(waypoint)
                        for _ in range(3000):
                            delta = goal-game.player.position
                            if delta.length()<.01:break
                            previous = game.player.position.copy()
                            game.update(min(1/30,delta.length()/(108 if running else 72)),delta,running)
                            if game.world is not world or not world.can_stand(game.player.position):
                                raise AssertionError(('Unsafe workyard movement', diagnostic(label)))
                            trace.append([round(v,4) for v in game.player.position])
                            if (world is game.town and 'upper_bridge' in label
                                    and abs(game.player.position.x-840)<2
                                    and abs(game.player.position.y-480)<1
                                    and label not in bridge_images):
                                game.draw();filename='crossing_'+label+'.png'
                                pygame.image.save(game.window,str(folder/filename))
                                bridge_images[label]=filename
                            if previous.distance_to(game.player.position)<.001:
                                stalled = True;break
                        else:raise AssertionError(('Workyard movement frame budget', diagnostic(label)))
                        if stalled:break
                    if not stalled and game.player.position.distance_to(target)<.02:
                        return {'target': list(target), 'trace': trace,
                                'frames': len(trace)-1, 'replans': replans}
                    replans += 1;game.update(.2,(0,0),False)
                raise AssertionError(('Workyard route remained obstructed', diagnostic(label)))

            def follow(label, route, running):
                sx,sy = route[0]
                start = choose_fixture((route[0], (sx+8,sy), (sx-8,sy), (sx,sy+8), (sx,sy-8)), label)
                trace = [list(game.player.position)];segments = []
                for target in route[1:]:
                    segment = drive(game.town,target,running,label)
                    segments.append(segment);trace.extend(segment['trace'][1:])
                game.draw();filename='movement_'+label+'.png'
                pygame.image.save(game.window,str(folder/filename))
                return {'label':label,'running':running,'goals':route,'start_fixture':start,
                        'trace':trace,'update_frames':sum(s['frames'] for s in segments),
                        'replans':sum(s['replans'] for s in segments),'image':filename,
                        'crossing_image':bridge_images.get(label),'passed':True}

            if movement:
                mira = next(door.data for door in game.town.doors if door.data['id']=='mira')
                mill = next(door.data for door in game.town.doors if door.data['id']=='mill')
                mira_front=[mira['anchor'][0],mira['anchor'][1]+12]
                mill_front=[mill['anchor'][0],mill['anchor'][1]+12]
                routes = (
                    ('workshop_contacts',[mira_front,[636,468],[612,468],[594,456],[682,456]]),
                    ('upper_bridge',[[720,480],[936,480],[984,396]]),
                    ('mill_delivery',[mill_front,[984,396],[1032,408],[1044,440],[1044,504],[960,504]]),
                    ('stock_corridor',[[732,354],[732,432],[744,456],[720,528],[636,528]]),
                )
                for name, route in routes:
                    for running in (False,True):
                        for reverse in (False,True):
                            label=name+('_run' if running else '_walk')+('_return' if reverse else '')
                            report['routes'].append(follow(label,list(reversed(route)) if reverse else route,running))

                for door_id in ('mira','mill'):
                    for running in (False,True):
                        outer = next(door.data for door in game.town.doors if door.data['id']==door_id)
                        x,y = outer['anchor']
                        start = choose_fixture(((x,y+36),(x+24,y+36),(x-24,y+36),(x,y+54)),door_id+'_doorway')
                        approaches=[drive(game.town,(x,y+12),running,door_id+'_front_door')]
                        entry_frames=exit_frames=0
                        for _ in range(240):
                            game.update(1/60,(0,-1),running);entry_frames+=1
                            if game.world is not game.town:break
                        else:raise AssertionError(('Workyard doorway did not enter',diagnostic(door_id)))
                        interior = game.world
                        if interior.data['id']!=door_id:
                            raise AssertionError(('Workyard doorway entered unexpected scene',door_id,interior.data['id']))
                        back = next(door.data for door in interior.doors if door.data['id']=='courtyard')
                        bx,by=back['anchor']
                        approaches.append(drive(interior,(bx,by-48),running,door_id+'_clear_arrival'))
                        game.update(.6,(0,0),False)
                        approaches.append(drive(interior,(bx,by-12),running,door_id+'_return_approach'))
                        for _ in range(240):
                            game.update(1/60,(0,1),running);exit_frames+=1
                            if game.world is game.town:break
                        else:raise AssertionError(('Workyard doorway did not return',diagnostic(door_id)))
                        if not game.town.can_stand(game.player.position):
                            raise AssertionError(('Workyard doorway returned onto blocked ground',door_id))
                        game.draw();filename='doorway_'+door_id+('_run' if running else '_walk')+'.png'
                        pygame.image.save(game.window,str(folder/filename))
                        report['doorway_roundtrips'].append({'door':door_id,'running':running,'interior':interior.data['id'],
                            'start_fixture':start,'production_approaches':approaches,
                            'entry_update_frames':entry_frames,'exit_update_frames':exit_frames,
                            'return_position':list(game.player.position),'clear_ground':True,'image':filename})

                save_start=choose_fixture(((670,470),(700,470),(744,480),(984,396)),'save_start')
                if not game.save_progress():raise AssertionError(('Workyard save failed',game.save_error))
                entity_ids=[item['id'] for item in workyard_entities(game.town.data)]
                workyard_report=deepcopy(game.town.data['settlement_workyards'])
                courtyard_report=deepcopy(game.town.data.get('settlement_dressing'))
                saved_state=framework.canonical(framework.meaningful_state(game))
                game.music.stop()
                restored = framework.Game(**options)
                try:
                    restored.audio.set_music(0);restored.audio.set_effects(0)
                    if not restored.begin_journey(True):
                        raise AssertionError(('Workyard Continue failed',restored.save_error))
                    restored.opening_fade=restored.transfer_cooldown=0
                    after_ids=[item['id'] for item in workyard_entities(restored.town.data)]
                    if after_ids!=entity_ids or len(after_ids)!=len(set(after_ids)):
                        raise AssertionError('Continue duplicated or lost workyard entities')
                    if restored.town.data['settlement_workyards']!=workyard_report:
                        raise AssertionError('Continue changed the workyard ledger or flat dressing')
                    if restored.town.data.get('settlement_dressing')!=courtyard_report:
                        raise AssertionError('Continue changed the prior courtyard ledger')
                    if not restored.world.can_stand(restored.player.position):
                        raise AssertionError('Continue restored onto blocked workyard ground')
                    supports=restored.town.data['settlement_workyards']['solid_footprints']
                    for support in supports:
                        sx,sy,w,h=support['rect']
                        if not all(restored.town.blocked.get_at((px,py))
                                   for py in range(sy,sy+h) for px in range(sx,sx+w)):
                            raise AssertionError(('Continue lost workyard support',support['id']))
                    if framework.canonical(framework.meaningful_state(restored))!=saved_state:
                        raise AssertionError('Continue changed quest/party/inventory/flags')
                    restored.draw();pygame.image.save(restored.window,str(folder/'continue_workyards.png'))
                    report['save_continue']={'saved':True,'continued':True,'new_entity_ids':after_ids,
                        'ground_entity_ids':[item['id'] for item in workyard_report.get('ground_entities',[])],
                        'start_fixture':save_start,'position':list(restored.player.position),'clear_ground':True,
                        'solid_footprints_preserved':len(supports),'prior_courtyard_unchanged':True,
                        'quest_party_inventory_flags_unchanged':True}
                finally:restored.music.stop()
            report['quest_party_inventory_flags_unchanged']=initial==framework.canonical(framework.meaningful_state(game))
            if not report['quest_party_inventory_flags_unchanged']:
                raise AssertionError('Workyard review changed gameplay progress')
        finally:game.music.stop();pygame.quit()
    return report


def capture(folder, baseline=None, *, movement=True):
    folder.mkdir(parents=True,exist_ok=True)
    production=framework.production_snapshot()
    comparison=compare_baseline(baseline,folder) if baseline is not None else None
    framework.capture(folder)
    report=read(folder/'observations.json')
    report['scope']='Native production workyard fixtures, strict scoped differences and real input/Continue smoke checks; no quest playthrough.'
    report['baseline_comparison']=comparison
    if baseline is not None:report['native_view_comparison']=compare_view_scope(baseline,folder,report)
    report['gameplay']=gameplay_capture(folder,baseline=baseline,movement=movement)
    if framework.production_snapshot()!=production:
        raise AssertionError('Production changed during workyard capture; rerun after writers finish')
    report['capture_png_sha256']={path.name:framework.digest(path.read_bytes()) for path in sorted(folder.glob('*.png'))}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Workyard review: {len(report['views'])} native views, {len(report['gameplay']['routes'])} movement checks; "
          f"baseline {'verified' if baseline is not None else 'not requested'}.")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-dir','--baseline',type=Path)
    parser.add_argument('--skip-movement',action='store_true',help='Capture static views only; omit walking and Continue smoke checks')
    arguments=parser.parse_args()
    capture(arguments.output.resolve(),arguments.baseline_dir.resolve() if arguments.baseline_dir else None,
            movement=not arguments.skip_movement)
