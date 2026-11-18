"""Review production emerald terrain through ordinary Game movement and travel.

Town and Sanctuary photographs/movie use a disposable new exploration journey.
The upstream overview is separately labelled as an initialized World fixture;
it does not claim to demonstrate the quest-gated trail transfer.
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

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game, Player, World, camera_for, VIEW_SIZE
from npc_routines import find_path
from overworld_travel import TOWN_EXIT, WORLD_ID
from tools.capture_overworld_sanctuary import regional_path, frame
from tools.capture_sanctuary_reserve import path

OUT = ROOT/'docs/reviews/grass_rollout'
MAPS = ('assets/maps/eldenmere/playable/map.json',
        'assets/maps/elden_vale_sanctuary/map.json',
        'assets/maps/eldenmere/upstream/map.json')


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def source_hashes():
    """Fingerprint map/pack references and implementation used by this review."""
    pending = [ROOT/name for name in (*MAPS, 'assets/terrain/grass/assets.json',
        'main.py', 'interactive_grass.py', 'overworld_travel.py',
        'tools/capture_grass_rollout.py', 'tools/capture_sanctuary_reserve.py',
        'tools/capture_overworld_sanctuary.py', 'tools/grass_terrain.py',
        'tools/build_grass_assets.py', 'tools/build_grass_demo_assets.py',
        'tools/build_playable_eldenmere.py',
        'tools/build_elden_vale_sanctuary_art.py', 'tools/build_elden_vale_sanctuary.py',
        'tools/build_mill_quest.py')]
    pending.extend((ROOT/'assets/source/terrain/grass').rglob('*'))
    seen = set()
    while pending:
        file = pending.pop()
        if file in seen or not file.is_file():continue
        seen.add(file)
        if file.suffix != '.json':continue
        def collect(value):
            if isinstance(value, dict):
                for item in value.values():collect(item)
            elif isinstance(value, list):
                for item in value:collect(item)
            elif isinstance(value, str) and value.startswith('assets/'):
                candidate = ROOT/value
                if candidate.is_file() and candidate not in seen:pending.append(candidate)
        collect(json.loads(file.read_text()))
    for facing in ('front', 'back', 'left', 'right'):
        seen.add(ROOT/f'assets/characters/caelan/idle_{facing}.png')
        for gait in ('walk', 'run'):
            seen.update(file for file in (ROOT/f'assets/characters/caelan/{gait}_{facing}').rglob('*')
                        if file.is_file())
    return {str(file.relative_to(ROOT)): digest(file) for file in sorted(seen)}


class Movie:
    def __init__(self, destination):
        executable = shutil.which('ffmpeg')
        if executable is None:raise RuntimeError('FFmpeg is required for this review')
        self.fps = 20
        self.frames = 0
        self.elapsed = self.next_frame = 0.
        self.process = subprocess.Popen([executable, '-y', '-loglevel', 'error',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '960x640', '-r', str(self.fps),
            '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)],
            stdin=subprocess.PIPE)

    def sample(self, game, seconds):
        self.elapsed += seconds
        if self.next_frame > self.elapsed+1e-6:return
        picture = frame(game)
        while self.next_frame <= self.elapsed+1e-6:
            self.process.stdin.write(picture.tobytes())
            self.frames += 1
            self.next_frame += 1/self.fps

    def finish(self):
        self.process.stdin.close()
        if self.process.wait() != 0:raise RuntimeError('Review video encoding failed')


def compare_body(game, observation):
    """Compare only grass enabled/disabled at the same real movement state."""
    world, player = game.world, game.player
    if world.grass is None:return
    camera = camera_for(player.position, world.size)
    bare, covered = pygame.Surface(VIEW_SIZE), pygame.Surface(VIEW_SIZE)
    actors = game.party_travel.actors()
    world.grass.enabled = False
    try:world.draw(bare, camera, player, game.elapsed_ms, include_ui=False, party_actors=actors)
    finally:world.grass.enabled = True
    world.draw(covered, camera, player, game.elapsed_ms, include_ui=False, party_actors=actors)
    sprite = player.sprite()
    mask = pygame.mask.from_surface(sprite)
    anchor = world.data['player_draw_anchor']
    origin = (round(player.position.x)-anchor[0]-camera[0],
              round(player.position.y)-anchor[1]-camera[1])
    changed_legs = 0
    for y in range(sprite.get_height()):
        for x in range(sprite.get_width()):
            if not mask.get_at((x, y)):continue
            pixel = x+origin[0], y+origin[1]
            if not bare.get_rect().collidepoint(pixel):continue
            changed = bare.get_at(pixel) != covered.get_at(pixel)
            if y < 25:
                observation['upper_body_pixel_checks'] += 1
                observation['upper_body_occluded_pixels'] += int(changed)
                assert not changed, ('Grass covered upper body', world.data['id'],
                                     list(player.position), player.facing, x, y)
            else:changed_legs += int(changed)
    observation['leg_overlap_frames'] += bool(changed_legs)
    observation['frames_checked'] += 1


def walk(game, points, scene, *, running=False, movie=None, observe=None, transfer=None):
    for target in points:
        target = pygame.Vector2(target)
        for _ in range(2400):
            if transfer and game.world.data['id'] == transfer:return True
            assert game.world.data['id'] == scene, ('Unexpected scene transfer', scene, game.world.data['id'])
            delta = target-game.player.position
            if delta.length() < .4:break
            before = game.player.position.copy()
            seconds = min(.05, delta.length()/(108 if running else 72))
            game.update(seconds, delta, running)
            if movie:movie.sample(game, seconds)
            if observe:observe()
            if transfer and game.world.data['id'] == transfer:return True
            assert game.player.position != before, ('Walking stalled', scene, list(before), list(target))
            assert game.world.can_stand(game.player.position), list(game.player.position)
            assert not game.combat.active, 'Review route encountered combat'
        else:raise AssertionError(('Movement budget exceeded', scene, list(target)))
    return bool(transfer and game.world.data['id'] == transfer)


def choose_patch(game):
    world = game.world
    ordered = sorted(world.grass.clumps,
                     key=lambda clump: pygame.Vector2(clump.position).distance_squared_to(game.player.position))
    for clump in ordered:
        root = pygame.Vector2(clump.position)
        if any(root.distance_to(npc.position) < 72 for npc in world.npcs):continue
        if not all(world.can_stand((root.x+dx, root.y)) for dx in range(-48, 49)):continue
        if not all(world.can_stand((root.x, root.y+dy)) for dy in range(-24, 1)):continue
        try:route = path(world, game.player.position, root+(-48, 0))
        except AssertionError:continue
        return clump, route
    raise AssertionError(('No reachable grass review patch', world.data['id']))


def photograph(game, output, name):
    game.location_seconds = 0
    game.quest_ui.current_notice = None
    game.quest_ui.notices.clear()
    frame(game).save(output/name)
    camera = game.camera.position()
    return {'file': name, 'scene': game.world.data['id'], 'feet': list(game.player.position),
            'facing': game.player.facing,
            'window_feet': [round((game.player.position.x-camera[0])*2),
                            round((game.player.position.y-camera[1])*2)],
            'source': 'production Game.draw after ordinary movement'}


def review_patch(game, output, prefix, movie):
    clump, route = choose_patch(game)
    scene = game.world.data['id']
    walk(game, route, scene)
    root = pygame.Vector2(clump.position)
    record = {'scene': scene, 'clump': clump.identifier, 'root': list(root),
              'upper_body_pixel_checks': 0, 'upper_body_occluded_pixels': 0,
              'leg_overlap_frames': 0, 'frames_checked': 0, 'max_strength': 0.,
              'views': {}}
    def observe():
        record['max_strength'] = max(record['max_strength'], clump.strength)
        if clump.occupants:compare_body(game, record)
    def hold(seconds):
        for _ in range(round(seconds*20)):
            game.update(.05, (0, 0), False)
            movie.sample(game, .05)
            observe()
    hold(1)
    walk(game, [root], scene, movie=movie, observe=observe)
    hold(1.5)
    assert clump.occupants, ('Standing did not occupy target grass', scene, clump.identifier)
    record['views']['standing'] = photograph(game, output, prefix+'_standing.png')
    walk(game, [root+(48, 0)], scene, running=True, movie=movie, observe=observe)
    walk(game, [root], scene, running=True, movie=movie, observe=observe)
    record['views']['running'] = photograph(game, output, prefix+'_running.png')
    hold(1)
    walk(game, [root+(0, -24)], scene, movie=movie, observe=observe)
    walk(game, [root], scene, movie=movie, observe=observe)
    record['views']['front'] = photograph(game, output, prefix+'_front.png')
    hold(1)
    walk(game, [root+(-48, 0)], scene, movie=movie, observe=observe)
    hold(1.5)
    assert not clump.occupants and clump.strength == 0, ('Grass did not recover', clump.identifier)
    record['recovered_after_exit'] = True
    record['views']['recovered'] = photograph(game, output, prefix+'_recovered.png')
    assert record['max_strength'] >= 1.9
    assert record['upper_body_pixel_checks'] > 0 and record['upper_body_occluded_pixels'] == 0
    assert record['leg_overlap_frames'] > 0
    return record


def upstream_view(game, output):
    """Explicit scene-initialized fixture using production World/Player only."""
    world = World(ROOT/MAPS[2], image_cache=game.town._images)
    player = Player(world)
    assert world.grass is not None
    roots = sorted(world.grass.clumps,
                   key=lambda clump: pygame.Vector2(clump.position).distance_squared_to(player.position))
    root = next(clump for clump in roots if world.can_stand(clump.position))
    player.position.update(root.position)
    world.update_grass(.4, player)
    surface = pygame.Surface(VIEW_SIZE)
    world.draw(surface, camera_for(player.position, world.size), player, 0, include_ui=False)
    surface = pygame.transform.scale(surface, (960, 640))
    pygame.image.save(surface, output/'upstream_fixture.png')
    return {'file': 'upstream_fixture.png', 'scene': world.data['id'],
            'feet': list(player.position), 'source': 'initialized production World/Player fixture',
            'ordinary_quest_transfer_demonstrated': False}


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Production grass sources changed; recapture.'
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, 'Artifact changed: '+name
    assert report['ordinary_movement_and_travel'] and report['disposable_save_and_settings']
    assert report['progression_unchanged'] and report['map_files_unchanged_during_capture']
    for scene in report['patches'].values():
        assert scene['upper_body_pixel_checks'] > 0 and scene['upper_body_occluded_pixels'] == 0
        assert scene['leg_overlap_frames'] > 0 and scene['max_strength'] >= 1.9
        assert scene['recovered_after_exit']
    assert report['travel']['entered_overworld'] and report['travel']['entered_sanctuary']
    assert report['movie']['frames'] > 0 and report['movie']['size'] == [960, 640]
    print('Production grass movement, travel, body visibility, recovery and fingerprints verified.')


def capture(output):
    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    maps_before = {name: digest(ROOT/name) for name in MAPS}
    report = {'source': 'production Game movement, contact transfers and renderer',
              'ordinary_movement_and_travel': True, 'disposable_save_and_settings': True,
              'quest_or_equipment_seeding': False, 'patches': {}, 'travel': {}}
    movie = Movie(output/'emerald_grass.mp4')
    try:
        with tempfile.TemporaryDirectory(prefix='production-grass-review-') as temporary:
            game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                        save_path=Path(temporary)/'journey.json',
                        settings_path=Path(temporary)/'settings.json')
            game.audio.set_music(0);game.audio.set_effects(0)
            game.opening_fade = game.transfer_cooldown = 0
            pygame.event.clear()
            baseline = (game.quests.to_dict(), game.inventory.to_dict(), set(game.social.flags))
            report['patches']['town'] = review_patch(game, output, 'town', movie)
            route = find_path(game.town, game.player.position, TOWN_EXIT, game.town.probe_size, None)
            assert route is not None
            assert walk(game, route, game.town.data['id'], transfer=WORLD_ID)
            report['travel']['entered_overworld'] = True
            game.update(.4, (0, 0), False)
            region = game.world
            road = next(road for road in region.region['roads'] if road['id'] == 'sanctuary_approach')
            walk(game, regional_path(region, game.player.position, region._tile_point(road['points'][0])), WORLD_ID)
            road_points = [region._tile_point(point) for point in road['points']]
            assert walk(game, road_points, WORLD_ID, transfer='elden_vale_sanctuary')
            report['travel']['entered_sanctuary'] = True
            game.update(.4, (0, 0), False)
            report['patches']['sanctuary'] = review_patch(game, output, 'sanctuary', movie)
            assert (game.quests.to_dict(), game.inventory.to_dict(), set(game.social.flags)) == baseline
            report['progression_unchanged'] = True
            report['upstream_fixture'] = upstream_view(game, output)
    finally:
        movie.finish()
        pygame.quit()
    assert source_hashes() == before, 'Source changed during capture; regenerate on frozen sources.'
    assert {name: digest(ROOT/name) for name in MAPS} == maps_before
    report['map_files_unchanged_during_capture'] = True
    report['source_sha256'] = before
    report['movie'] = {'file': 'emerald_grass.mp4', 'fps': movie.fps,
                       'frames': movie.frames, 'seconds': movie.frames/movie.fps,
                       'size': [960, 640], 'silent': True,
                       'long_transit_omitted': True}
    names = ('town_standing.png', 'town_running.png', 'sanctuary_standing.png', 'upstream_fixture.png')
    contact = Image.new('RGB', (960, 688), '#173f31')
    painter = ImageDraw.Draw(contact)
    font = ImageFont.load_default(size=14)
    labels = ('Eldenmere: standing', 'Eldenmere: running',
              'Sanctuary: standing', 'Upstream: initialized scene fixture')
    for index, (name, label) in enumerate(zip(names, labels)):
        x, y = index%2*480, index//2*344
        painter.text((x+8, y+5), label, font=font, fill='#edf0dc')
        with Image.open(output/name) as picture:
            contact.paste(picture.resize((480, 320), Image.Resampling.NEAREST), (x, y+24))
    contact.save(output/'contact_sheet.png')
    detail = Image.new('RGB', (768, 304), '#173f31')
    painter = ImageDraw.Draw(detail)
    for index, (scene, pose) in enumerate((('town', 'standing'), ('town', 'running'),
                                          ('sanctuary', 'standing'), ('sanctuary', 'running'))):
        record = report['patches'][scene]['views'][pose]
        x, y = record['window_feet']
        with Image.open(output/record['file']) as picture:
            crop = picture.crop((x-48, y-100, x+48, y+36))
            detail.paste(crop.resize((192, 272), Image.Resampling.NEAREST), (index*192, 32))
        painter.text((index*192+8, 8), scene.title()+': '+pose, font=font, fill='#edf0dc')
    detail.save(output/'grass_detail.png')
    report['artifact_sha256'] = {file.name: digest(file) for file in sorted(output.iterdir())
                               if file.suffix in ('.png', '.mp4')}
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    (output/'README.md').write_text('''# Emerald grass in the game\n\n![Production grass review](contact_sheet.png)\n\n[Walking, running, standing and recovery](emerald_grass.mp4)\n\n![Unpainted crops from the production screenshots](grass_detail.png)\n\nThe town and Sanctuary views use an ordinary disposable new exploration journey,\nproduction Game movement and the normal town/overworld/Sanctuary contacts. Long\ntravel segments are omitted from the silent video. No quests, equipment or\ncharacter poses are seeded. Detail views are integer-enlarged crops of those\nactual screenshots. The upstream still is explicitly an initialized production\nWorld/Player fixture; it does not demonstrate the quest-gated transfer.\n\nGrass parts during walking and running, remains parted while standing and\nrecovers after leaving. Every occupied review frame compares grass enabled and\ndisabled at the same real pose: opaque sprite pixels above row 25 remain identical,\nwhile lower-body overlap is observed. The [verification record](verification.json)\nretains counts, actual coordinates and final source/artifact fingerprints.\n\nRegenerate with `python tools/capture_grass_rollout.py`; verify with\n`python tools/capture_grass_rollout.py --check`. Captures use temporary save and\nsettings paths and do not modify journey files or map assets.\n''')
    check(output)
    print(json.dumps({'movie': report['movie'], 'patches': report['patches']}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.check:check(args.output)
    else:capture(args.output)


if __name__ == '__main__':main()
