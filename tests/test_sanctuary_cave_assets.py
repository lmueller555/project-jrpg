"""The live continuous cave must support full-foot travel and honest scenery."""
from collections import Counter, deque
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import numpy as np
from PIL import Image
import pygame
from main import World

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/sanctuary_cave/map.json'
TREASURES = frozenset(('cave_vein_cache', 'cave_grotto_pack', 'cave_grotto_chest',
                       'cave_keeper_chest', 'cave_overlook_cache', 'cave_quiet_cache'))
COLORS = frozenset(('red', 'blue', 'green', 'white', 'orange', 'purple'))
MAIN_ROOMS = frozenset(('entrance', 'vein_gallery', 'splitstone_hollow',
                        'deep_gallery', 'quiet_shelf', 'echo_chamber'))


def clear_segment(world, first, last):
    """Sample every native pixel with the complete player ground footprint."""
    count = max(1, math.ceil(math.dist(first, last)))
    return all(world.can_stand((first[0]+(last[0]-first[0])*i/count,
                                first[1]+(last[1]-first[1])*i/count))
               for i in range(count+1))


class CaveAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.world = World(MAP)
        cls.cave = cls.world.data['cave']
        source = ROOT/cls.world.data['build']['source_recipe']
        cls.spec = json.loads(source.read_text())
        cls.packs = {key: json.loads((ROOT/path).read_text())
                     for key, path in cls.spec['manifests'].items()}

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_continuous_map_rebuilds_and_uses_the_approved_expanded_pack(self):
        result = subprocess.run([sys.executable, 'tools/build_continuous_sanctuary_cave.py',
                                 '--check'], cwd=ROOT, capture_output=True, text=True,
                                timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(self.world.data['id'], 'sanctuary_cave')
        self.assertEqual(tuple(self.world.probe_size), (24, 12))
        self.assertEqual(len(self.cave['links']), 1)
        self.assertEqual(self.cave['links'][0]['destination'], 'elden_vale_sanctuary')
        for path, expected in self.world.data['build']['source_sha256'].items():
            self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)
        for key in ('base', 'gems', 'structure', 'water', 'geology', 'micro'):
            self.assertTrue(self.spec['manifests'][key].startswith('assets/terrain/limestone_cave/'))
        placed = self.cave['placed_modules']
        self.assertTrue({'structure', 'water', 'geology'} <=
                        {record['pack'] for record in placed} |
                        ({'water'} if self.cave.get('water_tiles') else set()))
        for record in placed:
            if record['pack'] == 'keeper':
                self.assertEqual(record['module'], 'flagstones')
                self.assertIn('assets/terrain/eldenmere/sanctuary_charm/props/flagstones.png',
                              self.world.data['build']['source_sha256'])
                continue
            self.assertIn(record['module'], self.packs[record['pack']]['modules'], record)

    def test_main_spaces_two_rewarding_loops_and_future_encounters_are_authored(self):
        rooms = {room['id']: room for room in self.cave['rooms']}
        self.assertTrue(MAIN_ROOMS <= set(rooms))
        self.assertTrue({'reflecting_grotto', 'keepers_recess', 'raised_shelf'} <= set(rooms))
        self.assertEqual({loop['id'] for loop in self.cave['loops']},
                         {'reflecting_grotto', 'keepers_recess'})
        points = self.cave['navigation_points']
        for loop in self.cave['loops']:
            route = self.cave['routes'][loop['route']]
            self.assertNotEqual(loop['branch'], loop['rejoin'])
            self.assertIn(points[loop['branch']], route)
            self.assertIn(points[loop['rejoin']], route)
            self.assertGreater(len(route), 3)
        encounters = self.cave['encounter_spaces']
        self.assertEqual(Counter(space['route'] for space in encounters),
                         Counter({'main': 4, 'reflecting_loop': 1, 'keeper_loop': 1}))
        for space in encounters:
            radius = space['radius']
            self.assertGreaterEqual(radius, 48)
            for angle in range(0, 360, 30):
                point = (space['center'][0]+radius*math.cos(math.radians(angle)),
                         space['center'][1]+radius*math.sin(math.radians(angle)))
                self.assertTrue(self.world.can_stand(point), (space['id'], point))
        arena = self.cave['arena']
        self.assertEqual(arena['status'], 'story_boss')
        self.assertEqual((arena['enemy_id'], arena['level']), ('vespermaw', 7))
        x, y, width, height = arena['bounds']
        self.assertGreaterEqual(width, 300)
        self.assertGreaterEqual(height, 180)
        for px in range(x+12, x+width-11, 12):
            for py in range(y+6, y+height-5, 12):
                self.assertTrue(self.world.can_stand((px, py)), ('arena', px, py))
        self.assertFalse(self.world.data.get('npcs'), 'Encounter spaces must not create unapproved enemies')

    def test_full_foot_paths_reach_every_room_treasure_exit_and_legacy_landing(self):
        world = self.world
        spawn = tuple(world.data['spawn'])
        start = tuple(round(value/6)*6 for value in spawn)
        self.assertTrue(clear_segment(world, spawn, start))
        seen = {start}
        queue = deque([start])
        while queue:
            first = queue.popleft()
            for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)):
                last = first[0]+dx, first[1]+dy
                if last in seen or not (0 <= last[0] < world.size[0] and
                                        0 <= last[1] < world.size[1]):
                    continue
                if clear_segment(world, first, last):
                    seen.add(last)
                    queue.append(last)
        targets = list(self.cave['navigation_points'].values())
        targets += [record['approach'] for record in self.cave['treasures']]
        targets += [record.get('approach', record['position']) for record in self.cave['links']]
        targets += [record.get('approach', record['position']) for record in self.cave['inspections']]
        targets += [record['center'] for record in self.cave['encounter_spaces']]
        targets += list(self.cave['legacy_landings'].values())
        self.assertEqual(set(self.cave['legacy_landings']),
                         {'sanctuary_cave_entrance', 'sanctuary_cave_hollow', 'sanctuary_cave_depths'})
        for target in targets:
            with self.subTest(target=target):
                self.assertTrue(world.can_stand(target), 'Authored station is blocked')
                nearby = (point for point in seen if math.dist(point, target) <= 9)
                self.assertTrue(any(clear_segment(world, point, target) for point in nearby),
                                'Station is disconnected or reachable only by a collision jump')
        for name, route in self.cave['routes'].items():
            for first, last in zip(route, route[1:]):
                self.assertTrue(clear_segment(world, first, last), (name, first, last))

    def test_main_passage_clearance_ramp_and_solid_landmarks_match_the_art(self):
        checks = self.cave['traversal_checks']
        self.assertGreaterEqual(len(checks['clearance_stations']), 5)
        for station in checks['clearance_stations']:
            width = station['width']
            self.assertGreaterEqual(width, 72)
            axis = station.get('axis')
            probes = ((width, 12),) if axis == 'horizontal' else (
                     ((24, width),) if axis == 'vertical' else ((width, 12), (24, width)))
            self.assertTrue(any(self.world.can_stand(station['position'], probe) for probe in probes),
                            station)
        ramp = checks['ramp_checks']
        for first, last in ((ramp['lower'], ramp['middle']), (ramp['middle'], ramp['upper'])):
            self.assertTrue(clear_segment(self.world, first, last), 'The ramp blocks its own shelf')
        self.assertTrue(checks['solid_points'])
        for record in checks['solid_points']:
            self.assertFalse(self.world.can_stand(record['position']), record)
        for point in ((0, 0), (12, 12), (self.world.size[0]-12, self.world.size[1]-12)):
            self.assertFalse(self.world.can_stand(point))

    def test_high_overlook_cannot_be_entered_by_walking_around_the_ramp(self):
        world = self.world
        ramp = self.cave['traversal_checks']['ramp_checks']
        start = tuple(ramp['upper'])
        goal = tuple(ramp['lower'])
        x, y = ramp['middle']
        original = world.blocked
        world.blocked = original.copy()
        # Close only the authored 48px walkable notch. If the player can still
        # leave the shelf, surrounding floor is allowing an invisible climb.
        world.blocked.draw(pygame.Mask((48, 1), fill=True), (x-24, y))
        try:
            seen = {start}
            queue = deque([start])
            while queue:
                first = queue.popleft()
                self.assertFalse(math.dist(first, goal) <= 9 and clear_segment(world, first, goal),
                                 'Raised shelf can be reached around the ramp')
                for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)):
                    last = first[0]+dx, first[1]+dy
                    if last in seen or not (0 <= last[0] < world.size[0] and
                                            0 <= last[1] < world.size[1]):
                        continue
                    if clear_segment(world, first, last):
                        seen.add(last)
                        queue.append(last)
        finally:
            world.blocked = original

    def test_animated_pool_tiles_use_their_authored_solid_water_regions(self):
        entities = {entity['id']: entity for entity in self.world.data['entities']}
        with Image.open(ROOT/self.world.data['collision']) as image:
            solid = np.array(image.convert('L')) > 0
        water = self.cave['water_tiles']
        self.assertGreaterEqual(len(water), 12)
        wet_pixels = 0
        for record in water:
            module = self.packs['water']['modules'][record['module']]
            entity = entities[record['entity_id']]
            self.assertEqual(entity['frames'], module['frames'])
            self.assertEqual(len(entity['frames']), 6)
            with Image.open(ROOT/module['water_mask']) as image:
                mask = np.array(image.convert('L')) > 0
            x, y = entity['position']
            height, width = mask.shape
            self.assertTrue(solid[y:y+height, x:x+width][mask].all(), record)
            wet_pixels += int(mask.sum())
        self.assertGreater(wet_pixels, 5000)

    def test_six_treasure_receipts_keep_physical_chests_and_matching_states(self):
        self.assertEqual({record['id'] for record in self.cave['treasures']}, TREASURES)
        self.assertEqual(len(self.cave['treasures']), 6)
        entities = {entity['id']: entity for entity in self.world.data['entities']}
        for treasure in self.cave['treasures']:
            entity = entities[treasure['entity_id']]
            self.assertEqual(set(entity['state_images']), {'closed', 'open'})
            sizes = []
            for path in entity['state_images'].values():
                with Image.open(ROOT/path) as image:
                    sizes.append(image.size)
            self.assertEqual(sizes[0], sizes[1])
            x, y, width, height = entity['footprint']
            self.assertFalse(self.world.can_stand((x+width/2, y+height/2)), treasure['id'])
            self.assertTrue(self.world.can_stand(treasure['approach']), treasure['id'])

    def test_all_six_microcrystal_colors_are_embedded_and_share_bounded_lights(self):
        lights = self.cave['lights']
        self.assertLessEqual(len(lights), 32)
        self.assertGreater(len(lights), 6)
        solid = np.array(Image.open(ROOT/self.world.data['collision']).convert('L')) > 0
        colors = set()
        total = 0
        fields = [entity for entity in self.world.data['entities'] if 'light_index' in entity]
        self.assertGreaterEqual(len(fields), 20)
        for entity in fields:
            module = self.packs[entity['source_pack']]['modules'][entity['source_module']]
            self.assertTrue(entity['source_module'].startswith(('wall_gem.', 'micro.')))
            self.assertFalse(entity.get('footprint') or entity.get('footprints'))
            colors.add(module['gem_color'])
            total += module['crystal_count']
            self.assertEqual(len(entity['frames']), 6)
            source = lights[entity['light_index']]
            self.assertEqual(source['color'], module['color'])
            x, y = entity['position']
            for bx, by, width, height in module['core_components']:
                self.assertLessEqual(width, 4)
                self.assertLessEqual(height, 5)
                self.assertTrue(solid[y+by:y+by+height, x+bx:x+bx+width].all(),
                                (entity['id'], 'Microcrystal projects onto open floor'))
        self.assertEqual(colors, COLORS)
        self.assertGreaterEqual(total, 500)
        for light in lights:
            self.assertEqual(self.world.blocked.get_at(tuple(light['position'])), 0, light)


if __name__ == '__main__':
    unittest.main()
