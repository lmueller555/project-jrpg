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


def pixel_components(mask):
    """Measure the actual eight-connected mineral pixels, not sprite canvases."""
    pending = {tuple(point) for point in np.argwhere(mask)}
    components = []
    while pending:
        start = pending.pop()
        queue = [start]
        points = [start]
        while queue:
            y, x = queue.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    other = y+dy, x+dx
                    if other in pending:
                        pending.remove(other)
                        queue.append(other)
                        points.append(other)
        ys, xs = zip(*points)
        components.append((min(xs), min(ys), max(xs)-min(xs)+1, max(ys)-min(ys)+1))
    return components


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

    def test_hundreds_of_microcrystals_are_recessed_in_walls_and_light_the_floor(self):
        """Shrinking six icons cannot substitute for mineral-rich cave walls."""
        spec = json.loads(CHAMBER_SOURCE.read_text())
        floor = Image.new('L', self.world.size)
        ImageDraw.Draw(floor).polygon([tuple(point) for point in spec['floor_outline']], fill=255)
        entities = [record for record in self.world.data['entities'] if 'light_index' in record]
        self.assertGreaterEqual(len(entities), 12, 'The walls need many irregular mineral seams')
        present = set()
        color_patches = {color: 0 for color in GEM_COLORS}
        total_crystals = 0
        for entity in entities:
            with self.subTest(gem=entity['id']):
                name = entity['source_module']
                self.assertTrue(name.startswith('wall_gem.'),
                                'Standing crystal clusters must be replaced by wall microcrystals')
                module = self.wall_gems['modules'][name]
                color = module['gem_color']
                present.add(color)
                color_patches[color] += 1
                total_crystals += module['crystal_count']
                self.assertIn(color, GEM_COLORS)
                self.assertFalse(module.get('footprints'))
                self.assertFalse(entity.get('footprint') or entity.get('footprints'),
                                 'An embedded gem must not become a floor obstacle')
                x, y = entity['position']
                ax, ay = module['anchor']
                anchor = x+ax, y+ay
                self.assertEqual(floor.getpixel(anchor), 0, 'Gem anchor is on open floor')
                self.assertEqual(self.world.blocked.get_at(anchor), 1)
                for bx, by, width, height in module['core_components']:
                    core = floor.crop((x+bx, y+by, x+bx+width, y+by+height))
                    self.assertFalse(np.any(np.array(core)),
                                     'A microcrystal projects onto the traversable floor')
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
        self.assertTrue(all(count >= 2 for count in color_patches.values()),
                        'Each color needs scattered seams, not one isolated gemstone')
        self.assertGreaterEqual(total_crystals, 250,
                                'The chamber needs hundreds of embedded microcrystals')
        self.assertEqual(self.world.data['cave']['microcrystal_count'], total_crystals)

    def test_microcrystals_stay_tiny_and_separate_while_brightness_pulses(self):
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
                self.assertLess(np.count_nonzero(alpha)/alpha.size, .35,
                                'A mineral seam should preserve the actual wall beneath it')
                for frame in frames[1:]:
                    self.assertTrue(np.array_equal(alpha, frame[:, :, 3]),
                                    'Pulsing changes the rock silhouette')
                rects = module['core_components']
                self.assertEqual(module['crystal_count'], len(rects))
                self.assertGreaterEqual(len(rects), 15)
                self.assertLessEqual(len(rects), 35)
                core = np.zeros(alpha.shape, dtype=bool)
                small = 0
                for x, y, width, height in rects:
                    self.assertTrue(0 <= x < x+width <= module['size'][0])
                    self.assertTrue(0 <= y < y+height <= module['size'][1])
                    self.assertTrue(1 <= width <= 4 and 1 <= height <= 5,
                                    'An individual microcrystal exceeds the native pixel scale')
                    small += width <= 3 and height <= 3
                    core[y:y+height, x:x+width] = True
                self.assertGreaterEqual(small, len(rects)*.5,
                                        'Most facets should be only a few native pixels')
                # Animated pixels isolate the mineral from fixed crevices and
                # lips. Measure their real exported shape to catch a large gem
                # hidden behind misleading crystal-count metadata.
                mineral = np.any(np.stack([frame[:, :, :3] != frames[0][:, :, :3]
                                          for frame in frames[1:]]), axis=(0, 3)) & (alpha > 0)
                self.assertTrue(mineral.any())
                self.assertFalse(np.any(mineral & ~core), 'A facet escaped its declared native bounds')
                components = pixel_components(mineral)
                self.assertEqual(len(components), len(rects),
                                 'Grains disappeared or merged into a larger gemstone')
                for x, y, width, height in components:
                    self.assertLessEqual(width, 4)
                    self.assertLessEqual(height, 5)
                # A straight row of equally spaced icons would still read as
                # placed jewels. Real seams need a varied vertical spread and
                # irregular grain spacing within the unchanged wall.
                centers = [(x+width/2, y+height/2) for x, y, width, height in rects]
                self.assertGreaterEqual(len({y for x, y in centers}), 5)
                gaps = np.diff(sorted({x for x, y in centers}))
                self.assertGreaterEqual(len(set(gaps)), 3)
                brightness = [frame[:, :, :3][mineral].mean() for frame in frames]
                self.assertGreater(brightness[-1], brightness[0]+5,
                                   'A facet shimmer alone is not a brightness pulse')
                for first, last in zip(brightness, brightness[1:]):
                    self.assertGreaterEqual(last, first-.1)
                stone = ~mineral & (alpha > 0)
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

    def test_retained_review_preserves_original_sources_and_artifacts(self):
        from tools.review_archive import check_review_archive
        # PR148's retained report pins the exact isolated review sources. Live
        # deployment is now authorized; it must not rewrite this old evidence.
        report = check_review_archive(
            REVIEW, 'e7086d1edc23d3b9a1542f32e94c8b6670474a5b8893447048b76aefd8f3ab20',
            'live_world_snapshot_sha256')
        self.assertTrue(report['ordinary_movement_only'])
        self.assertTrue(report['no_save_or_settings_files'])
        self.assertTrue(report['walking_seen'] and report['running_seen'])
        self.assertGreaterEqual(report['microcrystals']['total'], 250)
        self.assertEqual(report['microcrystals']['total'],
                         self.world.data['cave']['microcrystal_count'])
        self.assertLessEqual(report['microcrystals']['max_width'], 4)
        self.assertLessEqual(report['microcrystals']['max_height'], 5)
        self.assertTrue(report['reduced_motion_static'])
        self.assertGreater(report['pulse']['max_mean'], report['pulse']['min_mean'])
        self.assertEqual({gem['color'] for gem in report['wall_gems']}, GEM_COLORS)


if __name__ == '__main__':unittest.main()
