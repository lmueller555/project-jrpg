"""Review the fantasy Sanctuary through real Game movement, contacts and saves.

All character views use an ordinary disposable exploration journey. Long walks
between demonstrations are omitted from the focused movie; no scene assignment,
player teleport, seeded quest or substituted character pose is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game, World, VIEW_SIZE, camera_for
from npc_routines import find_path
from overworld_travel import TOWN_EXIT, WORLD_ID
from tools.capture_overworld_sanctuary import frame, regional_path
from tools.capture_sanctuary_reserve import path, finish_dialogue

OUT = ROOT/'docs/reviews/sanctuary_fantasy'
RESERVE = 'elden_vale_sanctuary'
HALL = 'elden_vale_sanctuary_hall'
MAP = 'assets/maps/elden_vale_sanctuary/map.json'
HALL_MAP = 'assets/maps/elden_vale_sanctuary_hall/map.json'


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def source_hashes():
    names = {
        'main.py', 'elden_vale_sanctuary.py', 'sanctuary_reserve.py',
        'sanctuary_atmosphere.py', 'sanctuary_audio.py', 'regional_audio.py',
        'sanctuary_map.py', 'overworld_travel.py', 'save_game.py',
        'overworld_world.py', 'overworld_environment.py', 'overworld_minimap.py',
        'ui_style.py', 'assets/ui/fonts/DejaVuSans.ttf',
        'interactive_grass.py', 'tools/capture_sanctuary_fantasy.py',
        'tools/capture_sanctuary_reserve.py', 'tools/capture_overworld_sanctuary.py',
        'tools/build_elden_vale_sanctuary.py', 'tools/build_elden_vale_sanctuary_art.py',
        'tools/reserve_stone_kit.py', 'tools/build_sanctuary_reserve_hall.py',
        'tools/build_overworld_sanctuary_art.py', 'tests/test_reserve_free_roam.py',
        MAP, HALL_MAP, 'assets/maps/overworld/elden_vale/region.json',
    }
    names.update(p.relative_to(ROOT).as_posix()
                 for p in (ROOT/'tools').glob('build_sanctuary_*.py'))
    for folder in (
        'assets/source/maps/elden_vale_sanctuary',
        'assets/source/terrain/sanctuary_fantasy',
        'assets/source/terrain/elden_vale_sanctuary_hall',
        'assets/source/terrain/overworld/elden_vale/sanctuary',
        'assets/terrain/sanctuary_fantasy',
        'assets/terrain/elden_vale_sanctuary',
        'assets/terrain/elden_vale_sanctuary_kit',
        'assets/terrain/elden_vale_sanctuary_hall',
        'assets/terrain/overworld/elden_vale/sanctuary',
        'assets/characters/caelan', 'assets/story/sanctuary_reserve',
    ):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*')
                     if p.is_file())
    pending = [ROOT/name for name in names if (ROOT/name).is_file()]
    seen = set()
    while pending:
        file = pending.pop()
        if file in seen:continue
        seen.add(file)
        if file.suffix != '.json':continue
        def collect(value):
            if isinstance(value, dict):
                for item in value.values():collect(item)
            elif isinstance(value, list):
                for item in value:collect(item)
            elif isinstance(value, str) and value.startswith('assets/'):
                source = ROOT/value
                if source.is_file() and source not in seen:pending.append(source)
        collect(json.loads(file.read_text()))
    return {str(file.relative_to(ROOT)): digest(file) for file in sorted(seen)}


def progression(game):
    return {
        'quests': game.quests.to_dict(), 'inventory': game.inventory.to_dict(),
        'flags': sorted(game.social.flags), 'abilities': game.character_abilities.to_dict(),
        'attributes': game.attributes.to_dict(), 'party': game.party.to_dict(),
        'music': game.music.desired_track,
    }


class Movie:
    def __init__(self, destination):
        executable = shutil.which('ffmpeg')
        if executable is None:raise RuntimeError('FFmpeg is required for review video')
        self.fps = 20
        self.frames = 0
        self.elapsed = self.next_frame = 0.
        self.process = subprocess.Popen([
            executable, '-y', '-loglevel', 'error', '-f', 'rawvideo',
            '-pix_fmt', 'rgb24', '-s', '960x640', '-r', str(self.fps), '-i', '-',
            '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination),
        ], stdin=subprocess.PIPE)

    def sample(self, game, seconds):
        self.elapsed += seconds
        if self.elapsed+1e-6 < self.next_frame:return
        picture = frame(game)
        while self.next_frame <= self.elapsed+1e-6:
            self.process.stdin.write(picture.tobytes())
            self.frames += 1
            self.next_frame += 1/self.fps

    def hold(self, game, seconds):
        # Standing remains real simulation: shimmer, breeze and petals advance.
        for _ in range(round(seconds*self.fps)):
            game.update(1/self.fps, (0, 0), False)
            self.sample(game, 1/self.fps)

    def finish(self):
        self.process.stdin.close()
        if self.process.wait() != 0:raise RuntimeError('Review movie encoding failed')


def walk(game, points, scene, *, movie=None, running=False, transfer=None,
         record_near=None):
    final = pygame.Vector2(points[-1]) if points else game.player.position
    travelled = 0.
    for goal in points:
        goal = pygame.Vector2(goal)
        for _ in range(2400):
            if transfer and game.world.data['id'] == transfer:return travelled
            assert game.world.data['id'] == scene, ('Unexpected scene transfer', scene, game.world.data['id'])
            delta = goal-game.player.position
            if delta.length() < .45:break
            previous = game.player.position.copy()
            seconds = min(.04, delta.length()/(108 if running else 72))
            game.update(seconds, delta, running)
            travelled += game.player.position.distance_to(previous)
            if movie and (record_near is None or game.player.position.distance_to(final) <= record_near):
                movie.sample(game, seconds)
            if transfer and game.world.data['id'] == transfer:return travelled
            assert game.player.position != previous, ('Walking stalled', scene, list(previous), list(goal))
            assert game.world.can_stand(game.player.position), list(game.player.position)
            assert not game.combat.active, 'The peaceful Sanctuary review entered combat'
        else:raise AssertionError(('Walking exceeded budget', scene, list(goal)))
    return travelled


def photograph(game, output, name):
    game.location_seconds = 0
    game.quest_ui.current_notice = None
    game.quest_ui.notices.clear()
    frame(game).save(output/name)
    return {'file': name, 'scene': game.world.data['id'],
            'position': list(game.player.position), 'facing': game.player.facing,
            'running': game.player.running, 'elapsed_ms': game.elapsed_ms,
            'size': list(game.window.get_size()), 'source': 'production Game.draw'}


def visibility(game):
    """Observe visible sprite pixels without staging or moving the actor."""
    world, player = game.world, game.player
    camera = camera_for(player.position, world.size)
    blank = pygame.Surface(VIEW_SIZE)
    shown = pygame.Surface(VIEW_SIZE)
    hidden = SimpleNamespace(position=player.position, story_visible=False)
    actors = game.party_travel.actors()
    world.draw(blank, camera, hidden, game.elapsed_ms, False, party_actors=actors)
    world.draw(shown, camera, player, game.elapsed_ms, False, party_actors=actors)
    sprite = player.sprite()
    mask = pygame.mask.from_surface(sprite)
    anchor = world.data['player_draw_anchor']
    origin = (round(player.position.x)-anchor[0]-camera[0],
              round(player.position.y)-anchor[1]-camera[1])
    opaque = visible = upper = upper_visible = 0
    for y in range(sprite.get_height()):
        for x in range(sprite.get_width()):
            if not mask.get_at((x, y)):continue
            point = origin[0]+x, origin[1]+y
            if not shown.get_rect().collidepoint(point):continue
            opaque += 1
            differs = blank.get_at(point) != shown.get_at(point)
            visible += differs
            if y < 25:
                upper += 1
                upper_visible += differs
    return {'opaque_sprite_pixels': opaque, 'visible_sprite_pixels': visible,
            'upper_body_pixels': upper, 'visible_upper_body_pixels': upper_visible}


def overview(game, output):
    world = game.world
    whole = pygame.Surface(world.size)
    hidden = SimpleNamespace(position=game.player.position, story_visible=False)
    for y in range(0, world.size[1], VIEW_SIZE[1]):
        for x in range(0, world.size[0], VIEW_SIZE[0]):
            tile = pygame.Surface(VIEW_SIZE)
            world.draw(tile, (x, y), hidden, game.elapsed_ms, False)
            whole.blit(tile, (x, y))
    pygame.image.save(whole, output)


def placement_diagram(output):
    """Explicit annotation of the actual overview, separate from gameplay art."""
    data = json.loads((ROOT/MAP).read_text())
    recipe = json.loads((ROOT/'assets/source/maps/elden_vale_sanctuary/recipe.json').read_text())
    font_path = str(ROOT/'assets/ui/fonts/DejaVuSans.ttf')
    title = ImageFont.truetype(font_path, 22)
    font = ImageFont.truetype(font_path, 16)
    small = ImageFont.truetype(font_path, 14)
    with Image.open(output/'reserve_overview.png') as source:
        image = source.convert('RGB')
    origin = (64, 88)
    board = Image.new('RGB', (image.width+128, image.height+152), '#123b2e')
    board.paste(image, origin)
    draw = ImageDraw.Draw(board)
    draw.text((24,14), 'Sanctuary placement and access diagram', font=title, fill='#e5edd4')
    draw.text((24,47), 'Annotations over the production overview; this diagram is not a gameplay screenshot.',
              font=small, fill='#bdcdb5')
    def point(value):return origin[0]+value[0], origin[1]+value[1]
    for value in data['public_approaches'].values():
        x,y = point(value)
        draw.rectangle((x-12,y-6,x+11,y+5), outline='#69d7ed', width=2)
    for value in data['loop_waypoints']:
        x,y = point(value)
        draw.ellipse((x-3,y-3,x+3,y+3), fill='#e7c66f', outline='#302d27')
    roots = [record['root'] for record in recipe['fantasy']['tree_replacements']]
    roots.extend(record['root'] for record in recipe['fantasy']['placements']
                 if record['family'] == 'crystals' and record['module'].startswith('crystal.'))
    for value in roots:
        x,y = point(value)
        draw.line((x-5,y,x+5,y), fill='#fff0c7', width=2)
        draw.line((x,y-5,x,y+5), fill='#fff0c7', width=2)
    x,y,w,h = data['cave_barrier']['footprint']
    x,y = point((x,y))
    draw.rectangle((x,y,x+w-1,y+h-1), outline='#edaa72', width=2)
    labels = (
        ('Living memorial grove', (360,276), (84,274)),
        ('Crystal ridge and closed cave', (1008,360), (844,180)),
        ('Hall and open cloister', (665,306), (556,98)),
        ('Confluence spring', (768,388), (720,425)),
        ('Older masonry fragments', (620,495), (505,552)),
        ('Intact surveyed limestone', (934,558), (872,636)),
        ('Southern arrival and return', (444,642), (300,715)),
    )
    for text, target, location in labels:
        lx,ly = point(location)
        tx,ty = point(target)
        width = math.ceil(draw.textlength(text, font=font))+16
        draw.line((tx,ty,lx+width/2,ly+14), fill='#efe5bc', width=2)
        draw.rounded_rectangle((lx,ly,lx+width,ly+29), radius=4,
                               fill='#173e31', outline='#d0c79c', width=1)
        draw.text((lx+8,ly+4),text,font=font,fill='#eef0d7')
    legend_y = origin[1]+image.height+18
    draw.text((24,legend_y), 'Cyan boxes: clear 24×12 public foot approaches   ·   Gold dots: woodland-loop checkpoints',
              font=small,fill='#d9e8c9')
    draw.text((24,legend_y+22), 'Cream crosses: authored tree/crystal roots   ·   Amber outline: existing closed keeper rail',
              font=small,fill='#d9e8c9')
    board.save(output/'placement_sheet.png')
    return {'source':'annotated production overview and authored placement/approach metadata',
            'diagram_only':True, 'public_approaches':len(data['public_approaches']),
            'landmark_roots':len(roots), 'loop_checkpoints':len(data['loop_waypoints'])}


def restore(game, save, settings):
    before = game.world.data['id'], tuple(game.player.position), progression(game)
    assert game.save_progress(), 'Disposable save failed'
    other = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                 save_path=save, settings_path=settings)
    assert other.has_saved_journey and other.begin_journey(True), 'Continue rejected the review save'
    assert (other.world.data['id'], tuple(other.player.position), progression(other)) == before
    other.audio.set_music(0)
    other.audio.set_effects(0)
    # Continue has the ordinary half-second arrival fade, which gates movement.
    other.update(.6, (0, 0), False)
    return other


def key(game, code):
    for event in (pygame.event.Event(pygame.KEYDOWN, key=code, repeat=False),
                  pygame.event.Event(pygame.KEYUP, key=code)):
        pygame.event.post(event)
        game.handle_events()


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Sources changed; recapture the fantasy Sanctuary'
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, 'Review artifact changed: '+name
    assert report['normal_travel_contacts'] and report['round_trip_complete']
    assert report['progression_unchanged'] and report['ordinary_movement_only']
    assert report['continue_reserve'] and report['continue_hall']
    assert report['walked_loop'] and report['free_ground_crossings']
    assert report['cave_barrier']['ordinary_forward_input_blocked']
    assert report['full_foot_flood']['clear_nodes'] == report['full_foot_flood']['arrival_connected_nodes']
    assert report['reduced_motion_reviewed'] and report['walking_seen'] and report['running_seen']
    assert report['atmosphere']['motes'] <= 12 and report['atmosphere']['petals'] <= 5
    assert report['reduced_motion_positions_static']
    assert report['placement_diagram']['diagram_only']
    assert len(report['public_approaches']) >= 10
    if report.get('movie'):assert 30 <= report['movie']['seconds'] <= 60, report['movie']
    print('Fantasy Sanctuary travel, movement, depth views, saves and source/artifact hashes verified.')


def capture(output=OUT, movie_enabled=True):
    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    geometry_before = {name: digest(ROOT/name) for name in (MAP, HALL_MAP)}
    report = {'source': 'Production Game movement, contacts, doors and renderer',
              'source_sha256': before, 'ordinary_movement_only': True,
              'disposable_save_and_settings': True, 'quest_or_equipment_seeding': False,
              'transit_omitted_from_movie': True, 'views': {}, 'depth_views': {},
              'public_approaches': {}, 'normal_travel_contacts': False,
              'walking_seen': False, 'running_seen': False, 'free_ground_crossings': []}
    movie = None
    with tempfile.TemporaryDirectory(prefix='sanctuary-fantasy-review-') as temporary:
        save, settings = Path(temporary)/'journey.json', Path(temporary)/'settings.json'
        game = Game(window_size=(960,640), fullscreen=False, start_on_title=False,
                    save_path=save, settings_path=settings)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        route = find_path(game.town, game.player.position, TOWN_EXIT, game.town.probe_size, None)
        assert route is not None
        walk(game, route, game.town.data['id'], transfer=WORLD_ID)
        assert game.world.data['id'] == WORLD_ID
        game.update(.4, (0,0), False)
        baseline = progression(game)
        world = game.world
        road = next(r for r in world.region['roads'] if r['id'] == 'sanctuary_approach')
        walk(game, regional_path(world, game.player.position, world._tile_point(road['points'][0])), WORLD_ID)
        road_points = [world._tile_point(point) for point in road['points']]
        walk(game, road_points[:-4], WORLD_ID)
        report['views']['regional_miniature'] = photograph(game, output, 'regional_miniature.png')
        walk(game, road_points[-4:], WORLD_ID, transfer=RESERVE)
        assert game.world.data['id'] == RESERVE
        game.update(.4, (0,0), False)
        report['normal_travel_contacts'] = True
        if movie_enabled:movie = Movie(output/'sanctuary_fantasy.mp4')

        def hold(seconds):
            if movie:movie.hold(game, seconds)
            else:
                for _ in range(round(seconds*20)):game.update(.05, (0,0), False)

        def sample(name, seconds=1.3):
            # Let the following camera settle naturally for landmark portraits;
            # gait evidence is photographed immediately during actual movement.
            settle = 0 if name in ('running_on_grass','walking_on_grass') else min(.3,seconds)
            if settle:hold(settle)
            report['views'][name] = photograph(game, output, name+'.png')
            if game.world.data['id'] == RESERVE:report['depth_views'][name] = visibility(game)
            hold(seconds-settle)

        def move(point, *, record=False, running=False, direct=False):
            route = [point] if direct else path(game.world, game.player.position, point)
            travelled = walk(game, route, game.world.data['id'], movie=movie if record else None,
                             running=running, record_near=72)
            if travelled > 2:
                report['running_seen' if running else 'walking_seen'] = True

        try:
            sample('arrival', 1.5)
            reserve = game.world
            for name, point in reserve.data['public_approaches'].items():
                move(point)
                report['public_approaches'][name] = list(game.player.position)
            review = reserve.data.get('fantasy_review_points', {})
            for name, fallback, seconds in (
                ('grove_full', None, 3),
                ('grove_front', reserve.data['public_approaches']['grove'], 3),
                ('grove_behind', None, 1.3),
                ('crystal_front', reserve.data['public_approaches']['cave'], 3),
                ('crystal_behind', None, 1.3),
                ('spring_front', (768,412), 2),
                ('spring_behind', (768,370), 1.3),
            ):
                point = review.get(name, fallback)
                if point is None:continue
                move(point, record=True)
                sample(name, seconds)
            # Independently observed free-ground route remains a direct gait test.
            for start, end, running in (((336,571),(300,571),False),
                                        ((300,571),(336,571),True)):
                move(start)
                move(end, record=True, running=running, direct=True)
                sample('running_on_grass' if running else 'walking_on_grass', .8)
                report['free_ground_crossings'].append({'start':list(start), 'end':list(end),
                                                       'running':running, 'direct_steering':True})
            game = restore(game, save, settings)
            report['continue_reserve'] = True
            for point in game.world.data['loop_waypoints']:move(point)
            report['walked_loop'] = True
            move(game.world.data['public_approaches']['cave'])
            footprint = pygame.Rect(game.world.data['cave_barrier']['footprint'])
            for _ in range(35):
                game.update(.04, (0,-1), False)
                if movie:movie.sample(game, .04)
            stopped = list(game.player.position)
            assert game.world.data['id'] == RESERVE
            assert stopped[1] >= footprint.bottom+game.world.probe_size[1]/2-2
            report['cave_barrier'] = {'footprint':list(footprint), 'stopped_feet':stopped,
                                     'ordinary_forward_input_blocked':True}
            sample('cave_barrier', 1)
            move(game.world.data['public_approaches']['grove'])
            game.audio.set_reduced_motion(True)
            hold(.4)
            game.draw()
            still = game.world.atmosphere.snapshot()
            sample('reduced_motion', 1.5)
            game.draw()
            after_still = game.world.atmosphere.snapshot()
            assert after_still['positions'] == still['positions']
            assert after_still['cached_surfaces'] == still['cached_surfaces']
            report['reduced_motion_positions_static'] = True
            report['atmosphere'] = after_still
            report['reduced_motion_reviewed'] = True
            game.audio.set_reduced_motion(False)
            hold(.2)
            overview(game, output/'reserve_overview.png')
            key(game, pygame.K_m)
            assert game.map_open
            report['views']['local_map'] = photograph(game, output, 'local_map.png')
            key(game, pygame.K_m)
            assert not game.map_open
            move(game.world.data['public_approaches']['hall'], record=True)
            sample('hall_court', 2)
            door = next(d for d in game.world.doors if d.data['id'] == 'sanctuary_hall')
            walk(game, [door.data['anchor']], RESERVE, transfer=HALL, movie=movie)
            assert game.world.data['id'] == HALL
            game.update(.4, (0,0), False)
            sample('hall_interior', 2)
            for identifier in ('records', 'remembrance', 'cabinet'):
                target = game.sanctuary_reserve.targets[identifier]
                move(target['approach'], record=identifier == 'remembrance')
                delta = pygame.Vector2(target['position'])-game.player.position
                game.update(.01, delta, False)
                game.update(.05, (0,0), False)
                assert game.sanctuary_reserve._nearby()[0] == identifier
                key(game, pygame.K_e)
                assert game.social.script_identifier == 'sanctuary_reserve_'+identifier
                if identifier == 'remembrance':sample('hall_remembrance', 1.5)
                finish_dialogue(game)
            overview(game, output/'hall_overview.png')
            game = restore(game, save, settings)
            report['continue_hall'] = True
            move((288,328))
            door = next(d for d in game.world.doors if d.data['id'] == 'reserve_exit')
            walk(game, [door.data['anchor']], HALL, transfer=RESERVE)
            assert game.world.data['id'] == RESERVE
            game.update(.4, (0,0), False)
            move(game.world.data['public_approaches']['cave'])
            sample('cave_final', 2)
            if movie and movie.frames/movie.fps < 42:hold(42-movie.frames/movie.fps)
            exit_point = game.world.data['reserve_exit']['position']
            walk(game, path(game.world,game.player.position,exit_point), RESERVE, transfer=WORLD_ID)
            assert game.world.data['id'] == WORLD_ID
            game.update(.4, (0,0), False)
            region = game.world
            target = (region.town_entry_rect.centerx, region.town_entry_rect.bottom-2)
            exterior = (target[0],region.town_entry_rect.bottom+36)
            walk(game, regional_path(region,game.player.position,exterior), WORLD_ID)
            walk(game, [target], WORLD_ID, transfer=game.town.data['id'])
            assert game.world is game.town
            assert progression(game) == baseline, 'Visit changed progression'
            report['progression_unchanged'] = report['round_trip_complete'] = True
            sys.path.insert(0, str(ROOT/'tests'))
            from test_reserve_free_roam import full_foot_flood
            clear, reached = full_foot_flood(World(ROOT/MAP))
            assert len(clear) == len(reached)
            report['full_foot_flood'] = {'grid_step':6, 'player_probe':[24,12],
                                       'clear_nodes':len(clear), 'arrival_connected_nodes':len(reached),
                                       'every_edge_pixel_checked':True}
            assert {name:digest(ROOT/name) for name in geometry_before} == geometry_before
            report['maps_unchanged_during_capture'] = True
            if movie:
                movie.finish()
                report['movie'] = {'file':'sanctuary_fantasy.mp4', 'fps':movie.fps,
                                   'frames':movie.frames, 'seconds':movie.frames/movie.fps,
                                   'size':[960,640], 'silent':True}
                movie = None
                assert 30 <= report['movie']['seconds'] <= 60, report['movie']
            assert source_hashes() == before, 'Source changed during capture; rerun after freeze'
        finally:
            if movie:movie.finish()
            pygame.quit()
    selected = [('arrival','Arrival'),
                ('grove_full' if 'grove_full' in report['views'] else 'grove_front','Memorial grove'),
                ('grove_behind','Behind the landmark tree'), ('crystal_front','Crystal cave'),
                ('spring_front','Confluence spring'), ('hall_court','Hall and cloister'),
                ('hall_interior','Hall interior'), ('reduced_motion','Reduced motion'),
                ('regional_miniature','Regional miniature')]
    selected = [(name,label) for name,label in selected if name in report['views']]
    rows = math.ceil(len(selected)/3)
    board = Image.new('RGB', (1440, rows*344), '#153e32')
    painter = ImageDraw.Draw(board)
    font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),16)
    for index, (name,label) in enumerate(selected):
        x,y = index%3*480, index//3*344
        with Image.open(output/report['views'][name]['file']) as image:
            board.paste(image.resize((480,320),Image.Resampling.NEAREST),(x,y+24))
        painter.text((x+8,y+3),label,fill='#e5ecce',font=font)
    board.save(output/'contact_sheet.png')
    report['placement_diagram'] = placement_diagram(output)
    report['artifact_sha256'] = {file.name:digest(file) for file in sorted(output.iterdir())
                                 if file.suffix in ('.png','.mp4')}
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'README.md').write_text('''# Fantasy Sanctuary — actual-game review

![Reserve and hall views](contact_sheet.png)

[Walking, running and standing](sanctuary_fantasy.mp4) · [Full reserve](reserve_overview.png) · [Hall overview](hall_overview.png) · [Local map](local_map.png)

[Placement and access diagram](placement_sheet.png) is explicitly annotated;
the other scene photographs remain unpainted production gameplay views.

The screenshots and silent movie use the production Game, character sprites,
camera and renderer. An ordinary disposable exploration journey walks from
Eldenmere through the normal overworld and Sanctuary contacts, visits the grove,
crystal cave, spring, woodland circuit and open grass, then enters the hall and
returns through the ordinary doors and exits. Long transit between demonstrations
is walked normally and omitted from the focused recording. Standing segments
continue real simulation so shimmer, foliage and atmospheric motion remain live.

The review covers walking and running, front/behind landmark views, reduced
motion, the cave's closed keeper rail, optional hall inspections and Save/Continue
in both scenes. Quests, inventory, party, character attributes, dialogue flags,
abilities and desired music remain unchanged. Temporary save/settings files
leave player journeys untouched. The full reserve image stitches bounded
production World.draw views; no scenery or character pose is painted into it.

[Verification](verification.json) retains actual positions, sprite visibility
observations, complete foot-probe connectivity and source/artifact fingerprints.
Reproduce with `python tools/capture_sanctuary_fantasy.py`; verify retained
evidence with `python tools/capture_sanctuary_fantasy.py --check`.
''')
    check(output)
    print(json.dumps({'movie':report.get('movie'), 'views':len(report['views']),
                      'full_foot_flood':report['full_foot_flood'],
                      'round_trip_complete':report['round_trip_complete']}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--no-movie',action='store_true')
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if args.check:check(args.out)
    else:capture(args.out,not args.no_movie)
