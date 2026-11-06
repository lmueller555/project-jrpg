"""Ground-foot travel through the reserve uses its shipped art and collision."""
import os
import json
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

    def walk_direct(self,start,target):
        self.player.position.update(start)
        target = pygame.Vector2(target)
        for _ in range(2000):
            delta = target-self.player.position
            if delta.length()<.05:break
            self.player.update(delta,min(.05,delta.length()/72),self.world)
            self.assertTrue(self.world.can_stand(self.player.position))
        self.assertLess(self.player.position.distance_to(target),.1)

    def test_shipped_geometry_is_reproducible(self):
        for name,body in products().items():self.assertEqual((MAP.parent/name).read_bytes(),body,name)
        self.assertEqual(self.world.size,(1152,768))
        self.assertEqual(self.world.probe_size,(24,12))

    def test_open_cloister_replaces_its_old_depth_without_changing_other_scenery(self):
        original = json.loads((ROOT/'assets/terrain/elden_vale_sanctuary/art.json').read_text())
        entities = {entity['id']:entity for entity in self.world.data['entities']}
        self.assertEqual(len(entities),len(self.world.data['entities']))
        self.assertNotIn('cloister_depth',entities)
        self.assertIn('sanctuary_cloister_openings_ground',entities)
        self.assertIn('cloister_open_roof_arches',entities)
        self.assertIn('cloister_preserved_east_stock',entities)
        for entity in original['entities']:
            if entity['id']=='cloister_depth':continue
            with self.subTest(retained_scenery=entity['id']):
                self.assertEqual(entities[entity['id']],entity)

    def test_every_public_approach_is_reached_by_ordinary_full_foot_movement(self):
        for name,point in self.world.data['public_approaches'].items():
            with self.subTest(name=name):
                self.player.position.update(self.world.data['spawn'])
                self.walk(point)

    def test_the_complete_woodland_circuit_is_continuously_walkable(self):
        for index,point in enumerate(self.world.data['loop_waypoints']):
            with self.subTest(waypoint=index):self.walk(point)

    def test_visible_off_path_ground_is_open_across_broad_patches(self):
        # Native rectangles measured from clear grass/stone in ground.png.
        # Every sample uses the production 24x12 feet, including both sides of
        # the former path-corridor edges. These are independent of the recipe.
        patches = {
            'northwest_shoulder':(420,74,20,12),
            'north_hall_shoulder':(504,111,28,14),
            'northeast_shoulder':(948,138,20,16),
            'east_loop_grass':(1080,299,14,22),
            'western_grove_grass':(213,380,18,18),
            'forecourt_west':(408,395,24,18),
            'forecourt_east':(792,358,20,14),
            'southern_grove_grass':(296,566,22,18),
            'southwest_grass':(302,594,22,16),
            'arrival_grass':(509,574,20,14),
            'survey_west_grass':(788,580,20,16),
            'survey_center_grass':(906,604,24,16),
            'survey_east_grass':(1048,592,10,4),
        }
        for name,(x,y,width,height) in patches.items():
            for px in range(x,x+width+1,2):
                for py in range(y,y+height+1,2):
                    with self.subTest(patch=name,point=(px,py)):
                        self.assertTrue(self.world.can_stand((px,py)))

    def test_cloister_arches_have_full_width_ground_access(self):
        for x in (666,718,772):
            with self.subTest(bay=x):
                self.walk_direct((x,328),(x,291))
                self.assertFalse(self.world.can_stand((x,286)))
        for point in ((641,302),(691,302),(745,302),(797,302),(848,302),
                      (715,289),(822,303),(808,309),(843,315),(875,309)):
            with self.subTest(actual_column_or_wall=point):
                self.assertFalse(self.world.can_stand(point))
        self.assertTrue(self.world.can_stand((824,330)))

    def test_cliff_top_bottom_and_slope_routes_are_open_around_stone_faces(self):
        for point in ((710,380),(710,478),(544,470),(562,500),
                      (920,414),(958,448),(1008,406)):
            with self.subTest(clear_ground=point):
                self.assertTrue(self.world.can_stand(point))
        for point in ((698,437),(750,423),(963,544)):
            with self.subTest(visible_rock=point):
                self.assertFalse(self.world.can_stand(point))

    def test_visible_boundary_and_cave_barrier_stop_feet_without_closing_the_exit(self):
        for point in ((430,42),(12,400),(1133,390),(330,670),(670,699),
                      (1008,371)):
            with self.subTest(physical_boundary=point):
                self.assertFalse(self.world.can_stand(point))
        self.assertEqual(self.world.data['cave_barrier']['footprint'],[974,364,70,13])
        self.assertTrue(any(entity['id']=='sanctuary_cave_safety_barrier'
                            for entity in self.world.data['entities']))
        self.walk_direct((444,642),(444,735))

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
