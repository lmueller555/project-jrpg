"""Review sanctuary overlap through normal movement and controlled render poses.

The focused movie omits transit between problem areas, but every recorded and
unrecorded step uses the production player, contacts, collision and camera.
Only the separate before/after pose stills assign a standalone renderer actor.
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
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from elden_vale_sanctuary import SanctuaryReserveWorld
from main import Game, Player, camera_for
from npc_routines import find_path
from overworld_travel import TOWN_EXIT, WORLD_ID
from tools.capture_overworld_sanctuary import Movie, regional_path
from tools.capture_sanctuary_reserve import path, photograph, state, walk

OUT = ROOT/'docs/reviews/sanctuary_depth'
RESERVE_ID = 'elden_vale_sanctuary'
HALL_ID = 'elden_vale_sanctuary_hall'


def controlled_poses(output):
    """Use the exact pre-fix world/camera/idle registration for comparison."""
    world = SanctuaryReserveWorld(ROOT/'assets/maps/elden_vale_sanctuary/map.json')
    player = Player(world);player.facing = 'front'
    records = {}
    for name, feet in (('north_oak', (348, 88)), ('open_ground', (300, 360)),
                       ('basin', (750, 318))):
        player.position.update(feet)
        assert world.can_stand(feet), ('Comparison feet are blocked', feet)
        canvas = pygame.Surface((480, 320))
        world.draw(canvas, camera_for(feet, world.size), player, 0)
        filename = 'after_'+name+'.png'
        pygame.image.save(pygame.transform.scale(canvas, (960, 640)), output/filename)
        records[name] = {'file': filename, 'feet': list(feet),
                         'source': 'Production World.draw, actual Caelan idle_front at controlled feet'}
    contact = Image.new('RGB', (960, 1038), '#15251d')
    draw = ImageDraw.Draw(contact)
    font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'), 18)
    labels = {'north_oak': ('Over the branches', 'Behind the branches'),
              'open_ground': ('Erased on open ground', 'Visible on open ground'),
              'basin': ('Boots over the rim', 'Behind the rim')}
    for row, name in enumerate(('north_oak', 'open_ground', 'basin')):
        feet = records[name]['feet']
        camera = camera_for(feet, world.size)
        center = ((feet[0]-camera[0])*2, (feet[1]-camera[1]-12)*2)
        crop = (center[0]-200, center[1]-133, center[0]+200, center[1]+133)
        for column, label in enumerate(('before', 'after')):
            source = output/(label+'_'+name+'.png')
            if not source.is_file():source = OUT/(label+'_'+name+'.png')
            if source.is_file():
                with Image.open(source) as image:
                    contact.paste(image.convert('RGB').crop(crop).resize((480, 320), Image.Resampling.NEAREST),
                                  (column*480, row*346+26))
            draw.text((column*480+10, row*346+3), label.title()+' | '+labels[name][column],
                      font=font, fill='#f4e6b9')
    contact.save(output/'before_after.png')
    return records


def capture(output=OUT, movie_enabled=True):
    output.mkdir(parents=True, exist_ok=True)
    paths = ('assets/terrain/elden_vale_sanctuary/ground.png',
             'assets/maps/elden_vale_sanctuary/map.json',
             'assets/terrain/elden_vale_sanctuary_hall/ground.png')
    report = {'source': 'Production Game movement, collision, contacts and draw',
              'disposable_save_and_settings': True, 'quest_or_equipment_seeding': False,
              'ordinary_movement_only': True, 'transit_omitted_from_movie': True,
              'input_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths},
              'sections': [], 'views': {}}
    movie = None
    with tempfile.TemporaryDirectory(prefix='sanctuary-depth-') as temporary:
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=Path(temporary)/'journey.json',
                    settings_path=Path(temporary)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0;pygame.event.clear()
        route = find_path(game.town, game.player.position, TOWN_EXIT, game.town.probe_size, None)
        assert route is not None
        assert walk(game, route, game.town.data['id'], transfer=WORLD_ID)
        game.update(.4, (0, 0), False)
        baseline = state(game)
        region = game.world
        road = next(r for r in region.region['roads'] if r['id'] == 'sanctuary_approach')
        walk(game, regional_path(region, game.player.position, region._tile_point(road['points'][0])), WORLD_ID)
        assert walk(game, [region._tile_point(p) for p in road['points']], WORLD_ID, transfer=RESERVE_ID)
        game.update(.4, (0, 0), False)

        def move(point, record=False):
            world = game.world
            walk(game, path(world, game.player.position, point), world.data['id'],
                 movie=movie if record else None)

        def still(name):
            game.update(.15, (0, 0), False)
            report['views'][name] = photograph(game, output, name+'.png')
            if movie:movie.hold(game, .7)

        def section(name, start, sequence):
            move(start)
            beginning = movie.frames/movie.fps if movie else 0
            for label, point in sequence:
                move(point, record=True)
                still(label)
            report['sections'].append({'name': name, 'start_seconds': beginning,
                'end_seconds': movie.frames/movie.fps if movie else 0,
                'points': [list(start), *[list(point) for _, point in sequence]]})
            assert state(game) == baseline, ('Progress changed', name)

        if movie_enabled:movie = Movie(output/'depth_walk.mp4')
        try:
            section('Entrance arch: behind, open passage and front', (444, 642), (
                ('arch_behind', (444, 615)), ('arch_opening', (444, 654)),
                ('arch_front', (444, 711))))
            section('Grove: clear ground and both sides of the bench', (310, 372), (
                ('clear_ground', (300, 360)), ('bench_behind', (271, 260)),
                ('bench_front', (271, 330))))
            section('Northern oak: crossing the rear path in both directions', (288, 84), (
                ('north_oak_behind', (348, 88)), ('north_oak_far_side', (418, 102)),
                ('north_oak_return', (288, 84))))
            section('Court: basin, planter and cloister front', (750, 318), (
                ('basin_behind', (750, 318)), ('basin_front', (750, 378)),
                ('planter_behind', (704, 340)), ('planter_front', (704, 382)),
                ('cloister_front', (660, 330))))
            hall = next(door for door in game.world.doors if door.data['id'] == 'sanctuary_hall')
            move(game.world.data['public_approaches']['hall'])
            assert walk(game, [hall.data['anchor']], RESERVE_ID, transfer=HALL_ID)
            game.update(.4, (0, 0), False)
            section('Hall: behind and in front of the south-west plant', (62, 288), (
                ('hall_plant_behind', (62, 288)), ('hall_plant_front', (74, 319))))
            assert state(game) == baseline
            assert not game.combat.active
            report['progression_unchanged'] = True
            report['saved_journey_valid'] = bool(game.save_progress() and game._read_saved_journey() is not None)
            assert report['saved_journey_valid']
            if movie:
                movie.finish()
                report['movie'] = {'file': 'depth_walk.mp4', 'fps': movie.fps,
                                   'frames': movie.frames, 'seconds': movie.frames/movie.fps}
                movie = None
            report['controlled_comparisons'] = controlled_poses(output)
            for name, digest in report['input_sha256'].items():
                assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
        finally:
            if movie is not None:movie.finish()
            game.music.stop();pygame.quit()
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    (output/'README.md').write_text('''# Sanctuary scenery depth correction

![Before and after controlled production-renderer poses](before_after.png)

[Focused gameplay review](depth_walk.mp4)

The movie follows normal production movement through the entrance arch, west
grove, northern oak, basin and flower planter, cloister and hall plant. Transit
between these areas is walked normally and omitted from the focused edit.
The player, camera, collision, contacts and door transitions are unchanged.

The before/after stills isolate actual Caelan at identical native feet and camera
positions in the production World renderer. Before stills retain the previous
implementation from main at `7cfb637914337706a94a14127a65a00a79f7f86f`.
They demonstrate the missing northern crown, the open-grass cutout that erased
Caelan, and the basin whose rim did not obscure his rear pose.

[Verification](verification.json) records the ordinary route, frame times,
unchanged progression and valid disposable save. No player save or settings
file is used. Reproduce current views with
`python tools/capture_sanctuary_depth.py`; historical before stills are retained.
''')
    print(json.dumps({'output': str(output), 'movie': report.get('movie'),
                      'progression_unchanged': report['progression_unchanged']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--no-movie', action='store_true')
    args = parser.parse_args();capture(args.out, not args.no_movie)
