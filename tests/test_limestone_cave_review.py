"""The limestone proposal must be walkable, reproducible and isolated."""
from collections import deque
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import numpy as np
from PIL import Image, ImageDraw
import pygame

from main import Player, camera_for
from sanctuary_cave_world import SanctuaryCaveWorld


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/limestone_cave_review/map.json'
PACK = ROOT/'assets/terrain/limestone_cave/assets.json'
WALL_GEMS = ROOT/'assets/terrain/limestone_cave/wall_gems/assets.json'
CHAMBER_SOURCE = ROOT/'assets/source/maps/limestone_cave_review/recipe.json'
REVIEW = ROOT/'docs/reviews/limestone_cave'
GEM_COLORS = frozenset(('red', 'blue', 'green', 'white', 'orange', 'purple'))


def clear_segment(world, first, last):
    """Check every native pixel along an edge with the full player footprint."""
    count = max(1, math.ceil(math.dist(first, last)))
    return all(world.can_stand((first[0]+(last[0]-first[0])*i/count,
                                first[1]+(last[1]-first[1])*i/count))
               for i in range(count+1))


class LimestoneCaveReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.world = SanctuaryCaveWorld(MAP)
        cls.player = Player(cls.world)
        cls.player.facing = 'front'
        cls.player.moving = False
        cls.pack = json.loads(PACK.read_text())
        cls.wall_gems = json.loads(WALL_GEMS.read_text())

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def render(self, clock, *, visible=True):
        actor = self.player if visible else SimpleNamespace(
            position=self.player.position, story_visible=False)
        camera = camera_for(self.player.position, self.world.size)
        image = pygame.Surface((480, 320))
        self.world.draw(image, camera, actor, clock, False)
        return image

    def test_builds_reproduce_and_native_materials_reference_real_assets(self):
        for builder in ('tools/build_limestone_cave_assets.py',
                        'tools/build_wall_gems.py',
                        'tools/build_limestone_cave_chamber.py'):
            result = subprocess.run([sys.executable, builder, '--check'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        for material, minimum in (('dry', 12), ('damp', 8), ('gravel', 8), ('silt', 4)):
            paths = self.pack['materials'][material]['tiles']
            self.assertGreaterEqual(len(paths), minimum, material)
            for path in paths:
                with Image.open(ROOT/path) as image:self.assertEqual(image.size, (24, 24))
        for manifest in (self.pack, self.wall_gems):
            for module in manifest['modules'].values():
                for path in module['frames']:
                    with Image.open(ROOT/path) as image:
                        self.assertEqual(image.size, tuple(module['size']), path)
            for path, expected in manifest['inputs'].items():
                self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)
            for path, expected in manifest['artifacts'].items():
                self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)
        for path, expected in self.world.data['build']['source_sha256'].items():
            self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)

    def test_six_gem_colors_are_recessed_in_walls_and_light_the_exposed_floor(self):
        """A floor obstacle with a gem sprite cannot satisfy embedded wall art."""
        spec = json.loads(CHAMBER_SOURCE.read_text())
        floor = Image.new('L', self.world.size)
        ImageDraw.Draw(floor).polygon([tuple(point) for point in spec['floor_outline']], fill=255)
        entities = [record for record in self.world.data['entities'] if 'light_index' in record]
        self.assertTrue(entities)
        present = set()
        for entity in entities:
            with self.subTest(gem=entity['id']):
                name = entity['source_module']
                self.assertTrue(name.startswith('wall_gem.'),
                                'Standing crystal clusters must be replaced by wall gems')
                module = self.wall_gems['modules'][name]
                color = module['gem_color']
                present.add(color)
                self.assertIn(color, GEM_COLORS)
                self.assertFalse(module.get('footprints'))
                self.assertFalse(entity.get('footprint') or entity.get('footprints'),
                                 'An embedded gem must not become a floor obstacle')
                x, y = entity['position']
                ax, ay = module['anchor']
                anchor = x+ax, y+ay
                self.assertEqual(floor.getpixel(anchor), 0, 'Gem anchor is on open floor')
                self.assertEqual(self.world.blocked.get_at(anchor), 1)
                bx, by, width, height = module['emission_bounds']
                core = floor.crop((x+bx, y+by, x+bx+width, y+by+height))
                self.assertLess(np.count_nonzero(np.array(core))/core.width/core.height, .1,
                                'The gem body projects onto the traversable floor')
                source = self.world.data['cave']['lights'][entity['light_index']]
                self.assertEqual(source['color'], module['color'])
                red, green, blue = source['color']
                if color == 'red':self.assertGreater(red, max(green, blue))
                elif color == 'blue':self.assertGreater(blue, max(red, green))
                elif color == 'green':self.assertGreater(green, max(red, blue))
                elif color == 'white':
                    self.assertGreater(min(red, green, blue), 160)
                    self.assertLess(max(red, green, blue)-min(red, green, blue), 64)
                elif color == 'orange':
                    self.assertGreater(red, green)
                    self.assertGreater(green, blue)
                    self.assertGreater(green, red*.4)
                elif color == 'purple':self.assertGreater(min(red, blue), green)
                self.assertEqual(source.get('entity_id'), entity['id'])
                self.assertEqual(floor.getpixel(tuple(source['position'])), 255,
                                 'Wall light must have an exposed floor root')
                self.assertEqual(self.world.blocked.get_at(tuple(source['position'])), 0)
        self.assertEqual(present, GEM_COLORS)

    def test_wall_gem_pulse_brightens_facets_without_moving_the_stone_or_silhouette(self):
        families = set()
        for name, module in self.wall_gems['modules'].items():
            with self.subTest(module=name):
                families.add(module['gem_color'])
                frames = []
                for path in module['frames']:
                    with Image.open(ROOT/path) as image:
                        frames.append(np.array(image.convert('RGBA')))
                self.assertEqual(len(frames), 6)
                alpha = frames[0][:, :, 3]
                self.assertTrue(set(np.unique(alpha)) <= {0, 255})
                self.assertTrue(np.any(alpha), 'Gem module cannot be transparent')
                for frame in frames[1:]:
                    self.assertTrue(np.array_equal(alpha, frame[:, :, 3]),
                                    'Pulsing changes the rock silhouette')
                x, y, width, height = module['emission_bounds']
                self.assertTrue(0 <= x < x+width <= module['size'][0])
                self.assertTrue(0 <= y < y+height <= module['size'][1])
                core = np.zeros(alpha.shape, dtype=bool)
                core[y:y+height, x:x+width] = True
                mineral = core & (alpha > 0)
                self.assertTrue(mineral.any())
                brightness = [frame[:, :, :3][mineral].mean() for frame in frames]
                self.assertGreater(brightness[-1], brightness[0]+5,
                                   'A facet shimmer alone is not a brightness pulse')
                for first, last in zip(brightness, brightness[1:]):
                    self.assertGreaterEqual(last, first-.1)
                stone = ~core & (alpha > 0)
                for frame in frames[1:]:
                    self.assertTrue(np.array_equal(frames[0][stone], frame[stone]),
                                    'Surrounding limestone changes independently of world light')
        self.assertEqual(families, GEM_COLORS)

    def test_every_review_station_and_route_has_a_full_foot_path(self):
        world = self.world
        self.assertEqual(tuple(world.probe_size), (24, 12))
        spawn = tuple(world.data['spawn'])
        start = tuple(round(value/6)*6 for value in spawn)
        self.assertTrue(clear_segment(world, spawn, start), 'Spawn cannot reach the review circuit')
        seen = {start}
        queue = deque([start])
        while queue:
            first = queue.popleft()
            for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)):
                last = first[0]+dx, first[1]+dy
                if last in seen or not (0 <= last[0] < world.size[0] and
                                        0 <= last[1] < world.size[1]):continue
                if clear_segment(world, first, last):
                    seen.add(last)
                    queue.append(last)
        cave = world.data['cave']
        targets = list(cave['review_points'].values())
        targets.extend(point for route in cave['routes'].values() for point in route)
        self.assertGreaterEqual(len(cave['review_points']), 5)
        for target in targets:
            with self.subTest(target=target):
                self.assertTrue(world.can_stand(target), 'Authored station is blocked')
                nearby = (point for point in seen if math.dist(point, target) <= 9)
                self.assertTrue(any(clear_segment(world, target, point) for point in nearby),
                                'Station is disconnected or only reachable by a probe jump')

    def test_solid_water_walls_and_formation_bases_match_the_visible_scene(self):
        checks = self.world.data['cave']['review_checks']
        self.assertTrue(checks['solid_points'])
        for record in checks['solid_points']:
            with self.subTest(solid=record['id']):
                self.assertFalse(self.world.can_stand(record['position']))
        self.assertFalse(self.world.can_stand((0, 0)))
        for record in self.world.data['entities']:
            if 'footprint' not in record:continue
            x, y, width, height = record['footprint']
            if width and height:
                self.assertFalse(self.world.can_stand((x+width/2, y+height/2)), record['id'])

    def test_crystal_breath_changes_ground_and_keeps_caelan_readable(self):
        world = self.world
        world.reduced_motion = False
        self.player.position.update(world.data['cave']['review_checks']['light_station'])
        camera = camera_for(self.player.position, world.size)
        samples = [self.render(clock) for clock in range(0, 6000, 500)]
        values = np.array([pygame.surfarray.array3d(image) for image in samples], dtype=np.int16)
        # Floor samples exclude all scenery and the actor: a shimmering crystal
        # sprite alone cannot satisfy the environmental-lighting requirement.
        actor_rect = self.player.sprite().get_rect(topleft=(
            round(self.player.position.x)-12, round(self.player.position.y)-30))
        floor_pixels = []
        for x in range(8, 472, 8):
            for y in range(8, 312, 8):
                point = x+camera[0], y+camera[1]
                if (world.can_stand(point) and not actor_rect.collidepoint(point)
                        and not any(record['rect'].collidepoint(point) for record in world.entities)):
                    floor_pixels.append((x, y))
        self.assertGreater(len(floor_pixels), 20)
        ranges = np.ptp(values, axis=0).sum(axis=2)
        self.assertGreater(np.percentile([ranges[x, y] for x, y in floor_pixels], 80), 8)
        darkest = min(range(len(samples)), key=lambda index:values[index].mean())
        bare = self.render(darkest*500, visible=False)
        difference = pygame.surfarray.array3d(samples[darkest]) != pygame.surfarray.array3d(bare)
        self.assertGreater(np.any(difference, axis=2).sum(), 80,
                           'Caelan disappears into the scenery at the light trough')
        repeated = pygame.surfarray.array3d(self.render(6000))
        for x, y in floor_pixels:
            self.assertTrue(np.array_equal(values[0, x, y], repeated[x, y]),
                            'Ground illumination does not repeat after six seconds')

    def test_foreground_depth_and_reduced_motion_use_the_real_world_renderer(self):
        checks = self.world.data['cave']['review_checks']
        self.assertTrue(checks['depth_cases'])
        self.world.reduced_motion = True
        for case in checks['depth_cases']:
            with self.subTest(formation=case['id']):
                for feet_key, pixel_key, hidden in (('feet', 'hidden_pixel', True),
                                                    ('visible_feet', 'visible_pixel', False)):
                    self.player.position.update(case[feet_key])
                    self.assertTrue(self.world.can_stand(self.player.position))
                    camera = camera_for(self.player.position, self.world.size)
                    shown, bare = self.render(0), self.render(0, visible=False)
                    x, y = case[pixel_key]
                    screen = round(x-camera[0]), round(y-camera[1])
                    self.assertEqual(shown.get_at(screen) == bare.get_at(screen), hidden)
        self.player.position.update(checks['light_station'])
        first = self.render(0)
        self.assertEqual(pygame.image.tobytes(first, 'RGB'),
                         pygame.image.tobytes(self.render(19321), 'RGB'))
        self.world.reduced_motion = False

    def test_review_has_not_changed_live_levels_or_player_journeys(self):
        from tools.capture_limestone_cave import world_hashes, check
        protected = world_hashes()
        result = subprocess.run(['git', 'diff', 'HEAD', '--name-only'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        untracked = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'],
                                   cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(untracked.returncode, 0, untracked.stderr)
        changed = set(result.stdout.splitlines()) | set(untracked.stdout.splitlines())
        self.assertFalse(changed & set(protected),
                         'The isolated proposal changed production sources or assets')
        report = json.loads((REVIEW/'verification.json').read_text())
        self.assertEqual(protected, report['live_world_snapshot_sha256'])
        self.assertTrue(report['ordinary_movement_only'])
        self.assertTrue(report['no_save_or_settings_files'])
        self.assertTrue(report['walking_seen'] and report['running_seen'])
        check(REVIEW)


if __name__ == '__main__':unittest.main()
