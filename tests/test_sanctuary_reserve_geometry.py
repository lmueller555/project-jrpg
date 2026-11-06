"""Ground-foot travel through the reserve uses its shipped art and collision."""
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from elden_vale_sanctuary import SanctuaryReserveWorld
from main import Player
from npc_routines import find_path
from tools.build_elden_vale_sanctuary import products

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/elden_vale_sanctuary/map.json'


class SanctuaryReserveGeometryTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480,320))
        self.world = SanctuaryReserveWorld(MAP)
        self.player = Player(self.world)

    def tearDown(self):pygame.quit()

    def walk(self,target):
        route = find_path(self.world,self.player.position,target,self.world.probe_size,None)
        self.assertIsNotNone(route, target)
        for point in route:
            target_point = pygame.Vector2(point)
            for _ in range(2000):
                delta = target_point-self.player.position
                if delta.length() < .05:break
                self.player.update(delta,min(.05,delta.length()/72),self.world)
                self.assertTrue(self.world.can_stand(self.player.position))
            else:self.fail(f'Player did not reach {point} from {self.player.position}')
        self.assertLess(self.player.position.distance_to(target),.1)

    def test_shipped_geometry_is_reproducible(self):
        for name,body in products().items():self.assertEqual((MAP.parent/name).read_bytes(),body,name)
        self.assertEqual(self.world.size,(1152,768))
        self.assertEqual(self.world.probe_size,(24,12))

    def test_every_public_approach_is_reached_by_ordinary_full_foot_movement(self):
        for name,point in self.world.data['public_approaches'].items():
            with self.subTest(name=name):
                self.player.position.update(self.world.data['spawn'])
                self.walk(point)

    def test_the_complete_woodland_circuit_is_continuously_walkable(self):
        for index,point in enumerate(self.world.data['loop_waypoints']):
            with self.subTest(waypoint=index):self.walk(point)

    def test_scenery_and_unimplemented_cave_depth_are_solid(self):
        for name,point in self.world.data['blocked_probes'].items():
            with self.subTest(name=name):self.assertFalse(self.world.can_stand(point))
        self.assertEqual(self.world.data['world_links'],[])
        self.assertTrue(all('cave' not in door['id'] for door in self.world.data['doors']))

    def test_tree_contacts_match_drawn_roots_while_canopy_routes_remain_open(self):
        # Contacts measured from the retained artwork, independently of the
        # generated collider records. A projecting trunk is not a ground wall.
        for point in ((320,147),(321,512),(297,631),(910,275),(749,588),
                      (200,353),(844,424),(642,485)):
            with self.subTest(root=point):self.assertFalse(self.world.can_stand(point))
        for point in ((348,88),(300,360),(204,334)):
            with self.subTest(clear_route=point):self.assertTrue(self.world.can_stand(point))

    def test_hall_threshold_and_reserve_exit_have_clear_player_landings(self):
        hall = self.world.doors[0]
        self.assertEqual(hall.data['arrival_door'],'reserve_exit')
        self.assertTrue(self.world.can_stand(hall.data['anchor']))
        self.assertTrue(hall.can_enter(hall.data['anchor'],(0,-1)))
        self.assertFalse(hall.can_enter(hall.data['anchor'],(0,1)))
        self.assertTrue(self.world.can_stand(self.world.data['reserve_exit']['position']))
        self.assertGreater(pygame.Vector2(self.world.data['spawn']).distance_to(
            self.world.data['reserve_exit']['position']),self.world.data['reserve_exit']['radius']+24)


if __name__=='__main__':unittest.main()
