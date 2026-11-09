"""The Sanctuary visitor room reuses pixel modules and has safe physical routes."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Player, World
from npc_routines import find_path
from tools.build_sanctuary_relief_room import build
from tools.build_sanctuary_reserve_hall import build as build_hall


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/elden_vale_sanctuary_relief/map.json'
HALL = ROOT/'assets/maps/elden_vale_sanctuary_hall/map.json'


class SanctuaryReliefMapTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.display.set_mode((480, 320))
        self.world = World(MAP)

    def tearDown(self):
        pygame.quit()

    def test_native_pixel_recipes_reproduce_room_and_hall_exports(self):
        build(check=True)
        build_hall(check=True)
        self.assertEqual(self.world.data['authoring'], 'native_pixel_asset_modules')
        self.assertEqual(self.world.data['tile_size'], 24)
        self.assertEqual(self.world.size, (336, 288))
        self.assertEqual(self.world.probe_size, (24, 12))
        for source in self.world.data['source_assets']:
            with self.subTest(source=source['path']):
                self.assertTrue(source['path'].startswith('assets/terrain/eldenmere/'))
                self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(),
                                 source['sha256'])
        hall = World(HALL)
        for source in hall.data['door_source_assets']:
            self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(),
                             source['sha256'])

    def test_every_bed_attendant_and_exit_route_is_full_foot_walkable(self):
        metadata = self.world.data['relief_room']
        # Include the real attendant's small foot blocker when proving paths.
        x, y = metadata['attendant']['position']
        attendant = SimpleNamespace(blocker=pygame.Rect(x-5, y-3, 10, 6))
        self.world.npcs.append(attendant)
        player = Player(self.world)
        for target in (metadata['bed_approach'], metadata['attendant_approach'],
                       self.world.data['spawn'], self.world.doors[0].data['anchor']):
            with self.subTest(target=target):
                self.assertTrue(self.world.can_stand(target))
                route = find_path(self.world, player.position, target, self.world.probe_size, None)
                self.assertIsNotNone(route)
                for point in route:
                    for _ in range(1000):
                        delta = pygame.Vector2(point)-player.position
                        if delta.length() < .1:break
                        before = player.position.copy()
                        player.update(delta, min(.05, delta.length()/72), self.world)
                        self.assertNotEqual(player.position, before)
                        self.assertTrue(self.world.can_stand(player.position))
                    else:self.fail(f'Blocked relief route at {point}')
                self.assertLess(player.position.distance_to(target), .1)

    def test_bed_and_care_furniture_are_solid_at_their_ground_footprints(self):
        footprints = {record['id']:pygame.Rect(record['rect'])
                      for record in self.world.data['object_footprints']}
        self.assertEqual(footprints['visitor_bed'], pygame.Rect(56,128,32,48))
        for identifier, rect in footprints.items():
            with self.subTest(prop=identifier):
                self.assertFalse(self.world.can_stand(rect.center))
        for point in ((104,150), (72,190), (168,248), (240,202)):
            self.assertTrue(self.world.can_stand(point), point)

    def test_hall_side_door_and_room_exit_are_reciprocal_and_running_cannot_overshoot(self):
        hall = World(HALL)
        entrance = next(door for door in hall.doors if door.data['id'] == 'relief_room')
        exit_door = self.world.doors[0]
        self.assertEqual(entrance.data['destination'], MAP.relative_to(ROOT).as_posix())
        self.assertEqual(exit_door.data['destination'], HALL.relative_to(ROOT).as_posix())
        self.assertEqual(entrance.data['arrival_door'], exit_door.data['id'])
        self.assertEqual(exit_door.data['arrival_door'], entrance.data['id'])
        self.assertTrue(self.world.can_stand(entrance.data['spawn']))
        self.assertTrue(hall.can_stand(exit_door.data['spawn']))
        self.assertEqual(len(entrance.frames), 5)
        entrance.force_open()
        player = Player(hall)
        player.position.update(hall.data['public_approaches']['relief_room'])
        player.update((0,-1), .6, hall, running=True)
        self.assertLessEqual(abs(player.position.y-entrance.data['entry_y']), 1)
        self.assertTrue(entrance.can_enter(player.position, (0,-1)))
        player = Player(self.world)
        player.update((0,1), .6, self.world, running=True)
        self.assertLessEqual(abs(player.position.y-exit_door.data['entry_y']), 1)
        self.assertTrue(exit_door.can_enter(player.position, (0,1)))

    def test_the_hall_keeps_all_older_public_routes_and_adds_the_relief_room(self):
        hall = World(HALL)
        for target in hall.data['destinations'].values():
            with self.subTest(target=target):
                self.assertTrue(hall.can_stand(target))
                self.assertIsNotNone(find_path(hall, hall.data['spawn'], target,
                                               hall.probe_size, None))
        self.assertEqual(hall.doors[0].data['id'], 'reserve_exit')
        self.assertEqual(hall.data['destinations']['records'], [476,278])
        self.assertEqual(hall.data['destinations']['remembrance_table'], [288,178])

    def test_room_has_no_random_encounter_or_quest_trigger_ownership(self):
        self.assertEqual(self.world.data['npcs'], [])  # Controller owns the attendant.
        self.assertEqual(self.world.data['quests'], [])
        self.assertNotIn('encounters', self.world.data)
        self.assertNotIn('random_encounters', self.world.data)
        self.assertEqual(self.world.data['exterior_map_position'], [535,345])


if __name__ == '__main__':
    unittest.main()
