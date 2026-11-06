"""Review ordinary movement beyond sanctuary roads, with disposable saves.

Every gameplay view and transfer uses the production Game. A* is used only for
unrecorded travel between areas; the recorded grass/arch demonstrations steer
straight across the former road edges. The collision comparison is a separately
labelled diagnostic laid over the unchanged source painting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game
from npc_routines import find_path
from overworld_travel import TOWN_EXIT, WORLD_ID
from test_reserve_free_roam import VISIBLE_GROUND, full_foot_flood
from tools.capture_overworld_sanctuary import Movie, regional_path
from tools.capture_sanctuary_reserve import (
    finish_dialogue, path, photograph, restore, state, walk, whole_scene)

OUT = ROOT/'docs/reviews/sanctuary_free_roam'
RESERVE_ID = 'elden_vale_sanctuary'
HALL_ID = 'elden_vale_sanctuary_hall'


def collision_clear_count(mask, world, step=6):
    """Compare mask exports with the same full feet, excluding NPC bodies."""
    total = 0
    for y in range(step, world.size[1], step):
        for x in range(step, world.size[0], step):
            rect = world.probe_rect((x, y))
            if (rect.left >= 0 and rect.top >= 0 and rect.right <= world.size[0]
                    and rect.bottom <= world.size[1]
                    and mask.overlap(world.probe, rect.topleft) is None):
                total += 1
    return total


def collision_diagnostic(output):
    """Overlay exported pixel masks; never modify a runtime art asset."""
    ground = Image.open(ROOT/'assets/terrain/elden_vale_sanctuary/ground.png').convert('RGBA')
    font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), 22)
    result = Image.new('RGB', (ground.width*2, ground.height+44), '#14271e')
    draw = ImageDraw.Draw(result)
    for column, (title, source) in enumerate((
            ('Before: blocked pixels tinted red', output/'before_collision.png'),
            ('After: visible physical boundaries', ROOT/'assets/maps/elden_vale_sanctuary/collision.png'))):
        base = ground if column == 0 else Image.open(output/'reserve_overview.png').convert('RGBA')
        mask = Image.open(source).convert('L')
        alpha = mask.point(lambda value: 100 if value else 0)
        color = Image.new('RGBA', ground.size, '#ff234e');color.putalpha(alpha)
        picture = Image.alpha_composite(base, color).convert('RGB')
        result.paste(picture, (column*ground.width, 44))
        draw.text((column*ground.width+14, 10), title, font=font, fill='#f4e6bf')
    result.save(output/'collision_before_after.png')


def capture(output=OUT, movie_enabled=True):
    output.mkdir(parents=True, exist_ok=True)
    historical = output/'before_collision.png'
    if not historical.exists():
        historical.write_bytes((OUT/'before_collision.png').read_bytes())
    inputs = ('assets/maps/elden_vale_sanctuary/map.json',
              'assets/maps/elden_vale_sanctuary/collision.png',
              'assets/terrain/elden_vale_sanctuary/ground.png',
              'assets/terrain/elden_vale_cave_barrier/barrier.png')
    inputs += tuple(path.relative_to(ROOT).as_posix() for path in sorted(
        (ROOT/'assets/terrain/elden_vale_cloister_openings').rglob('*'))
        if path.is_file() and path.suffix in {'.png', '.json'})
    digests = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in inputs}
    report = {'source': 'Production Game movement, Player.update, collision, contacts, doors and draw',
              'disposable_save_and_settings': True, 'quest_or_equipment_seeding': False,
              'player_probe': [24, 12], 'transit_omitted_from_movie': True,
              'recorded_grass_crossings_use_direct_steering': True,
              'input_sha256': digests, 'views': {}, 'sections': [], 'inspections': {},
              'public_approaches': {}, 'continue': []}
    movie = None
    with tempfile.TemporaryDirectory(prefix='sanctuary-free-roam-') as temporary:
        save = Path(temporary)/'journey.json';settings = Path(temporary)/'settings.json'
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=save, settings_path=settings)
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0;pygame.event.clear()
        route = find_path(game.town, game.player.position, TOWN_EXIT, game.town.probe_size, None)
        assert route is not None, 'Town exit is unreachable'
        assert walk(game, route, game.town.data['id'], transfer=WORLD_ID)
        game.update(.4, (0, 0), False)
        report['town_exit_contact'] = True
        baseline = state(game);region = game.world
        site = next(p for p in region.region['landmarks'] if p['id'] == 'ridge_sanctuary')
        report['overworld_miniature'] = site['tile_position']
        assert site['tile_position'] == [90, -66], site
        road = next(r for r in region.region['roads'] if r['id'] == 'sanctuary_approach')
        walk(game, regional_path(region, game.player.position, region._tile_point(road['points'][0])), WORLD_ID)
        assert walk(game, [region._tile_point(p) for p in road['points']], WORLD_ID, transfer=RESERVE_ID)
        game.update(.4, (0, 0), False)
        report['miniature_contact_entered_reserve'] = True

        def move(point, record=False, direct=False):
            points = [point] if direct else path(game.world, game.player.position, point)
            walk(game, points, game.world.data['id'], movie=movie if record else None)

        def still(name, hold=.75):
            game.update(.12, (0, 0), False)
            report['views'][name] = photograph(game, output, name+'.png')
            if movie:movie.hold(game, hold)

        def section(name, start, points):
            move(start)
            beginning = movie.frames/movie.fps if movie else 0
            if movie:movie.hold(game, .6)
            for label, point in points:
                move(point, record=True, direct=True)
                still(label)
            report['sections'].append({'name': name, 'start_seconds': beginning,
                'end_seconds': movie.frames/movie.fps if movie else 0,
                'direct_steering_points': [list(start), *[list(point) for _, point in points]]})
            assert state(game) == baseline, ('Progression changed', name)

        def inspect(key, record=False):
            target = game.sanctuary_reserve.targets[key]
            move(target['approach'], record=record)
            game.update(.01, pygame.Vector2(target['position'])-game.player.position, False)
            game.update(.05, (0, 0), False)
            assert game.sanctuary_reserve._nearby()[0] == key, ('Wrong inspection target', key)
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False));game.handle_events()
            pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_e));game.handle_events()
            assert game.social.script_identifier == 'sanctuary_reserve_'+key
            if record:
                still('cave_inspection', 2)
            report['inspections'][key] = {'feet': list(game.player.position), 'pages': finish_dialogue(game)}
            assert state(game) == baseline, ('Inspection changed progression', key)

        reserve = game.world
        clear, reached = full_foot_flood(reserve)
        report['full_foot_flood'] = {'grid_step': 6, 'every_edge_pixel_checked': True,
                                   'clear_nodes': len(clear), 'arrival_connected_nodes': len(reached),
                                   'connected_sample_area_pixels': len(reached)*36}
        old = pygame.mask.from_threshold(pygame.image.load(str(historical)).convert(),
                                         (255, 255, 255, 255), (1, 1, 1, 255))
        report['collision_export_comparison'] = {'grid_step': 6,
            'same_full_player_probe': [24, 12], 'npc_bodies_omitted_from_both_counts': True,
            'before_clear_nodes': collision_clear_count(old, reserve),
            'after_clear_nodes': collision_clear_count(reserve.blocked, reserve)}
        report['visible_ground'] = {}
        for label, point in VISIBLE_GROUND.items():
            assert reserve.can_stand(point), (label, point)
            rect = reserve.probe_rect(point)
            report['visible_ground'][label] = {'feet': list(point),
                'blocked_before': old.overlap(reserve.probe, rect.topleft) is not None,
                'clear_after': True}

        # Exercise every authored public approach with the actual active NPCs.
        for key, point in reserve.data['public_approaches'].items():
            move(point)
            report['public_approaches'][key] = list(game.player.position)
        for key in ('boundary', 'caretaker', 'visitor_slate', 'visitor_plum', 'grove', 'survey'):
            inspect(key)
        move(reserve.data['spawn'])
        if movie_enabled:movie = Movie(output/'free_roam_walk.mp4')
        try:
            still('arrival', 1)
            section('Leave the northern path for the open grass behind the hall', (430, 96), (
                ('north_grass', (430, 73)), ('north_shoulder', (510, 82)),
                ('behind_hall', (510, 120)), ('behind_hall_roof', (510, 180))))
            section('Freely cross the shaded grove lawn', (250, 400), (
                ('free_grass', (220, 400)), ('grove_grass_north', (220, 370)),
                ('grove_path_edge', (250, 370)), ('grove_return', (250, 400))))
            section('Cross the former road edge on southern grass', (339, 603), (
                ('formerly_blocked_grass', (309, 603)), ('grove_south_lawn', (309, 571)),
                ('grove_lawn_edge', (336, 571)), ('south_grass_return', (339, 603))))
            move((309, 603))
            before = list(game.player.position)
            assert report['visible_ground']['south-west flowers and grass']['blocked_before']
            game = restore(game, save, settings)
            assert list(game.player.position) == before
            move((339, 603), record=True, direct=True)
            report['continue'].append({'scene': RESERVE_ID, 'feet': before,
                'formerly_blocked_location_preserved': True, 'ordinary_movement_after_continue': True})
            still('continue_on_grass', .8)

            start = (666, 326);move(start)
            beginning = movie.frames/movie.fps if movie else 0
            for name, point, back in (
                    ('cloister_west', (666, 302), (666, 326)),
                    ('cloister_middle_west', (717, 302), (717, 320)),
                    ('cloister_middle_east', (771, 302), (771, 315))):
                move(back, record=True)
                move(point, record=True, direct=True);still(name)
                move((point[0],291), record=True, direct=True);still(name+'_inside', .45)
                move(back, record=True, direct=True)
            move((824,330), record=True);still('cloister_workstation')
            for point in ((822,303), (808,309), (843,315), (875,309)):
                assert not game.world.can_stand(point), ('Workstation accepts player feet', point)
            report['sections'].append({'name': 'Ordinary front entry into three open cloister bays',
                'start_seconds': beginning, 'end_seconds': movie.frames/movie.fps if movie else 0,
                'open_bays': [[666,302], [717,302], [771,302]],
                'rear_floor_feet': [[666,291], [717,291], [771,291]],
                'east_workstation_remains_solid': True})
            section('Walk the clear margins around the survey', (917, 634), (
                ('survey_margin', (917, 610)), ('survey_grass', (959, 625)),
                ('survey_margin_return', (917, 610))))

            move((1008, 406));beginning = movie.frames/movie.fps if movie else 0
            if movie:movie.hold(game, .6)
            for _ in range(45):
                game.update(.04, (0, -1), False)
                if movie:movie.sample(game, .04)
            stopped = list(game.player.position)
            assert 382 <= stopped[1] <= 384, ('Cave collision is not aligned to visible rail', stopped)
            still('visible_cave_barrier', 1.2)
            report['cave_barrier'] = {'front_apron': [1008,406], 'stopped_feet': stopped,
                'visible_footprint': reserve.data['cave_barrier']['footprint'],
                'ordinary_forward_input_blocked': True}
            move((1008, 406), record=True, direct=True);inspect('cave', record=True)
            report['sections'].append({'name': 'Visible cave rail stops forward movement; inspect from the front',
                'start_seconds': beginning, 'end_seconds': movie.frames/movie.fps if movie else 0})
            whole_scene(game, output/'reserve_overview.png')

            door = next(d for d in game.world.doors if d.data['id'] == 'sanctuary_hall')
            move(game.world.data['public_approaches']['hall'])
            assert walk(game, [door.data['anchor']], RESERVE_ID, movie=movie, transfer=HALL_ID)
            game.update(.4, (0, 0), False);still('hall_entry', 1)
            for key in ('records', 'remembrance', 'cabinet'):inspect(key)
            game = restore(game, save, settings)
            report['continue'].append({'scene': HALL_ID, 'feet': list(game.player.position),
                                      'location_and_progression_preserved': True})
            still('hall_continue', 1)
            if movie:
                movie.finish()
                report['movie'] = {'file': 'free_roam_walk.mp4', 'fps': movie.fps,
                                   'frames': movie.frames, 'seconds': movie.frames/movie.fps}
                movie = None
                assert 35 <= report['movie']['seconds'] <= 50, report['movie']
            move((288, 328))
            door = next(d for d in game.world.doors if d.data['id'] == 'reserve_exit')
            assert walk(game, [door.data['anchor']], HALL_ID, transfer=RESERVE_ID)
            game.update(.4, (0, 0), False)
            assert walk(game, path(game.world, game.player.position, game.world.data['reserve_exit']['position']),
                        RESERVE_ID, transfer=WORLD_ID)
            game.update(.4, (0, 0), False);still('overworld_return', 0)
            assert state(game) == baseline, 'Visit changed quest, inventory, flags, abilities or music'
            assert not game.combat.active
            report['hall_entry_and_exit_contacts'] = True
            report['reserve_return_contact'] = True
            report['progression_unchanged'] = True
            report['saved_journey_valid'] = bool(game.save_progress() and game._read_saved_journey() is not None)
            assert report['saved_journey_valid']
            for name, digest in digests.items():
                assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, ('Capture input changed', name)
        finally:
            if movie is not None:movie.finish()
            game.music.stop();pygame.quit()

    collision_diagnostic(output)
    contact = Image.new('RGB', (1440, 640), '#14271e')
    for index, name in enumerate(('free_grass', 'cloister_middle_west', 'visible_cave_barrier')):
        with Image.open(output/(name+'.png')) as picture:
            contact.paste(picture.resize((480,320), Image.Resampling.NEAREST), (index*480, 0))
        lower_name = 'north_grass' if index == 0 else 'survey_margin' if index == 1 else 'hall_entry'
        with Image.open(output/(lower_name+'.png')) as picture:
            contact.paste(picture.resize((480,320), Image.Resampling.NEAREST), (index*480, 320))
    contact.save(output/'scene_contact.png')
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    (output/'README.md').write_text(f'''# Sanctuary free exploration review

![Production gameplay views: free grass, cloister, cave rail, northern shoulder, survey and hall](scene_contact.png)

[Focused ordinary gameplay, 35–50 seconds](free_roam_walk.mp4) · [Full reserve](reserve_overview.png)

The actual Game leaves Eldenmere through its southern contact, walks the regional
approach to the sanctuary miniature at tile **(90, −66)**, and enters the reserve.
All ten public approaches and all seven exterior conversations/observations are
reached with ordinary movement. The movie omits travel between demonstration
areas and directly steers across the former corridor edges on northern grass,
the shaded grove, southern lawn and survey margin. It enters the three open
cloister bays from the court. Their stone columns and back wall, and the eastern
garden workstation, remain solid.
Localized floor patches replace the three former low masonry panels, matching
the walkable openings to the visible paving.
The [newly accessible cloister floor](cloister_middle_west.png) keeps Caelan
visible in front, while [ground behind the projecting hall roof](behind_hall_roof.png)
correctly leaves him occluded by the building.

The cave's visible keeper rail stops forward movement at the front apron. Its
inspection remains available from outside. No dungeon entrance or reward is
created. The player enters and leaves the separate hall through its ordinary
door, reads all three hall observations, and returns through the southern
reserve contact to the overworld. Quest, inventory, flags, abilities and music
remain unchanged; no quest or equipment state is seeded.

Disposable Save/Continue resumes both in the hall and at **(309, 603)** on grass
blocked by the previous collision export. That location is preserved exactly
and the player can immediately walk away. Normal player saves/settings are
never opened. A separate regression also loads an existing version-one save
with that historical location and checks ordinary movement after Continue.

![Collision diagnostic: exported blockers tinted red over the previous painting and current production scene](collision_before_after.png)

This comparison is a diagnostic overlay, not replacement scenery. The full-foot
flood samples the entire map with the production **24×12** player probe and
checks every pixel of each grid edge. Independent grass samples come from the
retained painting, including formerly blocked lawn and shoulders; cloister
samples use the reviewed floor patches. Negative movement checks retain the hall
walls, well/basin, roots, cliff faces, perimeter wall and cave rail as solids.
With the same full feet and a six-pixel grid, clear collision-export samples
increase from **{report['collision_export_comparison']['before_clear_nodes']:,}**
to **{report['collision_export_comparison']['after_clear_nodes']:,}**. NPC bodies
are omitted from both comparison counts.

[Verification and exact route positions](verification.json). Reproduce with
`python tools/capture_reserve_free_roam.py`; run regressions with
`PYTHONPATH=tests python -m unittest test_reserve_free_roam`.
''')
    print(json.dumps({'output': str(output), 'movie': report.get('movie'),
                      'public_approaches': len(report['public_approaches']),
                      'inspections': len(report['inspections']), 'progression_unchanged': True}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--no-movie', action='store_true')
    args = parser.parse_args();capture(args.out, not args.no_movie)
