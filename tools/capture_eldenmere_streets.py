"""Review the ground-only settlement street pass against a pre-build baseline.

Uses native initialized-Game screenshots, disposable saves, and production
Game.update movement. Static player/camera placements are disclosed fixtures;
quests, NPCs and scenery are not manufactured. The historical framework capture
keeps its stricter identity-only contract and is reused without modification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import capture_eldenmere_settlement_framework as framework

import numpy as np
from PIL import Image
import pygame

from npc_routines import find_path

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_streets'
ALLOWED_MAP_FIELDS = {'ground_overlays', 'overview', 'cartography', 'settlement_streets'}
GROUND_PREFIX = 'assets/maps/eldenmere/town_hd/town/chunks/'


def native_ground(town, elapsed_ms):
    """Compose only the exact live ground overlays at their native density."""
    image = Image.new('RGBA', tuple(value*2 for value in town['size_pixels']))
    for record in town['ground_overlays']:
        frames = record.get('frames') or [record['image']]
        index = int(elapsed_ms//record.get('frame_duration_ms', 200)) % len(frames)
        with Image.open(ROOT/frames[index]) as source:
            picture = source.convert('RGBA')
        expected = tuple(value*2 for value in record['logical_size'])
        if picture.size != expected:
            raise AssertionError(('Ground density mismatch', record['id'], picture.size, expected))
        image.alpha_composite(picture, tuple(round(value*2) for value in record['position']))
    if image.getchannel('A').getextrema() != (255, 255):
        raise AssertionError('Live ground assembly is not fully covered')
    return image


def compare_baseline(baseline, folder):
    previous = json.loads((baseline/'observations.json').read_text())['production']
    original = json.loads((baseline/'town.json').read_text())
    town = json.loads(framework.TOWN.read_text())
    current = framework.production_snapshot()
    changed_fields = sorted(key for key in original.keys() | town.keys()
                            if original.get(key) != town.get(key))
    unexpected = set(changed_fields)-ALLOWED_MAP_FIELDS
    if unexpected:
        raise AssertionError(('Non-street map fields changed', sorted(unexpected)))
    # Only the complete compiled road network is added to existing cartography.
    old_cartography = original.get('cartography', {})
    new_cartography = {key: value for key, value in town.get('cartography', {}).items()
                       if key != 'street_network'}
    if old_cartography != new_cartography:
        raise AssertionError('Unrelated cartography changed')
    allowed_files = {current['town_map'], original['overview'], town['overview']}
    old_files, new_files = previous['active_files'], current['active_files']
    changed_files = sorted(path for path in old_files.keys() | new_files.keys()
                           if old_files.get(path) != new_files.get(path))
    unexpected_files = [path for path in changed_files
                        if path not in allowed_files and not path.startswith(GROUND_PREFIX)]
    if unexpected_files:
        raise AssertionError(('Non-ground active artwork changed', unexpected_files))
    masks = {}
    for key in ('collision', 'navigation_allowed'):
        before = (baseline/(key+'.png')).read_bytes()
        after = (ROOT/town[key]).read_bytes()
        masks[key] = {'identical_bytes': before == after,
                      'sha256': framework.digest(after), 'bytes': len(after)}
        if before != after:
            raise AssertionError((key, 'changed'))
    coverage_path = ROOT/town['settlement_streets']['coverage_image']
    with Image.open(coverage_path) as source:
        if source.mode != 'L':
            raise AssertionError(('Coverage must be native L', source.mode))
        coverage = np.asarray(source) != 0
    expected_size = tuple(value*2 for value in town['size_pixels'])
    if (coverage.shape[1], coverage.shape[0]) != expected_size:
        raise AssertionError('Coverage does not use native ground dimensions')
    phases = []
    for phase in range(6):
        after = native_ground(town, phase*200)
        with Image.open(baseline/f'ground_phase_{phase}.png') as source:
            before = source.convert('RGBA')
        if before.size != after.size:
            raise AssertionError(('Ground dimensions changed', phase))
        changed = np.any(np.asarray(before) != np.asarray(after), axis=2)
        outside = int(np.count_nonzero(changed & ~coverage))
        phases.append({'phase': phase, 'elapsed_ms': phase*200,
                       'changed_native_pixels': int(np.count_nonzero(changed)),
                       'changed_outside_coverage': outside,
                       'before_rgba_sha256': framework.digest(before.tobytes()),
                       'after_rgba_sha256': framework.digest(after.tobytes())})
        if outside:
            raise AssertionError(('Ground changed outside compiled coverage', phases[-1]))
    # Keep the full metadata witness and original native screenshots in the PR.
    shutil.copyfile(baseline/'observations.json', folder/'before_observations.json')
    shutil.copyfile(baseline/'town.json', folder/'before_town.json')
    for source in sorted(baseline.glob('*.png')):
        if source.name.startswith('ground_phase_') or source.name in {
                'collision.png', 'navigation_allowed.png', 'protection_plan_diagnostic.png'}:
            continue
        shutil.copyfile(source, folder/('before_'+source.name))
    return {'changed_map_fields': changed_fields,
            'unchanged_map_fields': sorted(set(original)-set(changed_fields)),
            'changed_active_files': changed_files,
            'non_ground_active_artwork_unchanged': True,
            'existing_cartography_unchanged': True,
            'collision_and_navigation': masks,
            'coverage': {'image': town['settlement_streets']['coverage_image'],
                         'sha256': framework.digest(coverage_path.read_bytes()),
                         'native_size': list(expected_size),
                         'native_pixels': int(np.count_nonzero(coverage))},
            'ground_phases': phases}


def gameplay_capture(folder, *, movement=True):
    """Draw the actual map and drive inputs along existing accessible routes."""
    report = {'fixture': 'Fresh initialized Game; opening disabled; clear-ground route starts. '
              'Existing NPCs and quest state remain active. No seeded quests or replacement art.',
              'routes': []}
    with tempfile.TemporaryDirectory(prefix='eldenmere-streets-review-') as directory:
        temporary = Path(directory)
        game = framework.Game(fullscreen=False, window_size=(960, 640), start_on_title=True,
                              save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
        try:
            game.on_title = False
            game.opening.restore({'version': 1, 'stage': 'disabled'})
            game.opening_fade = game.transfer_cooldown = 0
            game.audio.set_music(0);game.audio.set_effects(0)
            game.world = game.town
            initial = framework.canonical(framework.meaningful_state(game))
            game.player.position.update((528, 1512))
            game.location_label = None;game.location_seconds = 0
            game.saves.notice_seconds = 0
            game.map_open = True
            game.map_ui.reset()
            game.draw()
            pygame.image.save(game.window, str(folder/'town_map.png'))
            report['town_map'] = {'native_size': list(game.window.get_size()),
                                  'compiled_street_records': len(game.town.data['cartography']['street_network'])}
            game.map_open = False

            def follow(label, route, running):
                start = route[0]
                if not game.town.can_stand(start):
                    raise AssertionError(('Blocked route fixture', label, start))
                game.player.position.update(start)
                game.player.moving = game.player.running = False
                game.camera.reset();game.transfer_cooldown = 0
                trace = [list(game.player.position)]
                crossing_frames = {}
                waypoint_count = replans = 0
                for target in route[1:]:
                    target = pygame.Vector2(target)
                    for attempt in range(5):
                        path = find_path(game.world, game.player.position, target,
                                         game.world.probe_size, None)
                        if not path:
                            raise AssertionError(('No production path', label, list(game.player.position), list(target)))
                        blocked = False
                        for waypoint in path:
                            waypoint_count += 1
                            goal = pygame.Vector2(waypoint)
                            for _ in range(3000):
                                delta = goal-game.player.position
                                if delta.length() < .01:
                                    break
                                before = game.player.position.copy()
                                game.update(min(1/30, delta.length()/(108 if running else 72)), delta, running)
                                if game.world is not game.town:
                                    raise AssertionError(('Unexpected scene transfer', label, game.world.data['id']))
                                if not game.world.can_stand(game.player.position):
                                    raise AssertionError(('Unsafe movement', label, list(game.player.position)))
                                trace.append([round(value, 4) for value in game.player.position])
                                if label.startswith('two_bridge_loop') and abs(game.player.position.x-840) < 2:
                                    for crossing, y in (('upper_bridge', 480), ('lower_bridge', 1032)):
                                        if abs(game.player.position.y-y) < 1 and crossing not in crossing_frames:
                                            game.draw()
                                            filename = 'movement_'+label+'_'+crossing+'.png'
                                            pygame.image.save(game.window, str(folder/filename))
                                            crossing_frames[crossing] = filename
                                if before.distance_to(game.player.position) < .001:
                                    blocked = True
                                    break
                            else:
                                raise AssertionError(('Movement frame budget', label))
                            if blocked:
                                break
                        if not blocked:
                            break
                        replans += 1
                        # Keep actors present; allow the production clock to move
                        # a temporary obstruction before another collision query.
                        game.update(.2, (0, 0), False)
                    else:
                        raise AssertionError(('Movement remained blocked', label, trace[-1]))
                    if game.player.position.distance_to(target) > .02:
                        raise AssertionError(('Route missed its goal', label, list(target)))
                game.draw()
                image_name = 'movement_'+label+'.png'
                pygame.image.save(game.window, str(folder/image_name))
                return {'label': label, 'running': running, 'declared_goals': route,
                        'production_waypoints': waypoint_count, 'replans': replans,
                        'update_frames': len(trace)-1, 'trace': trace,
                        'native_crossing_frames': crossing_frames,
                        'native_end_frame': image_name, 'passed': True}

            if movement:
                routes = [
                    ('southern_spine', [[504, 1104], [504, 1320], [528, 1368], [528, 1572]]),
                    ('two_bridge_loop', [[384, 480], [936, 480], [936, 1032], [384, 1032], [384, 480]]),
                ]
                for record in game.town.data['cartography']['street_network']:
                    if record['role'] == 'desire':
                        routes.append((record['id'].rsplit('.', 1)[-1], record['points']))
                for label, route in routes:
                    for running in (False, True):
                        for reverse in (False, True):
                            name = label+('_run' if running else '_walk')+('_return' if reverse else '')
                            points = list(reversed(route)) if reverse else route
                            report['routes'].append(follow(name, points, running))
            report['quest_party_inventory_flags_unchanged'] = initial == framework.canonical(framework.meaningful_state(game))
            if not report['quest_party_inventory_flags_unchanged']:
                raise AssertionError('Street movement changed gameplay progress')
        finally:
            game.music.stop();pygame.quit()
    return report


def capture(folder, baseline=None, *, movement=True):
    folder.mkdir(parents=True, exist_ok=True)
    production = framework.production_snapshot()
    comparison = compare_baseline(baseline, folder) if baseline is not None else None
    framework.capture(folder)
    report = json.loads((folder/'observations.json').read_text())
    report['scope'] = 'Ground-only street integration; native Game fixtures and production movement; no quest playthrough.'
    report['baseline_comparison'] = comparison
    report['gameplay'] = gameplay_capture(folder, movement=movement)
    if framework.production_snapshot() != production:
        raise AssertionError('Production inputs changed during capture; rerun after build finishes')
    report['capture_png_sha256'] = {path.name: framework.digest(path.read_bytes())
                                   for path in sorted(folder.glob('*.png'))}
    (folder/'observations.json').write_text(json.dumps(report, indent=2)+'\n')
    comparison_text = '; six ground phases verified inside coverage' if comparison is not None else ''
    print(f"Street review: {len(report['views'])} native views, "
          f"{len(report['gameplay']['routes'])} movement routes{comparison_text}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-dir', '--baseline', type=Path,
                        help='Pre-build observations.json, town.json, collision/navigation and ground_phase_0..5.png')
    parser.add_argument('--skip-movement', action='store_true', help='Capture native fixtures and comparison only')
    args = parser.parse_args()
    capture(args.output.resolve(), args.baseline_dir.resolve() if args.baseline_dir else None,
            movement=not args.skip_movement)
