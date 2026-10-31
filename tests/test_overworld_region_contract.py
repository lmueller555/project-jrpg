"""Exercise the shipped region through the same full foot masks as movement."""
import os
from collections import deque
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame

from main import Player
from overworld_world import OverworldWorld, TILE_SIZE


class OverworldRegionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((480,320))
        cls.world = OverworldWorld(collision_cache_limit=256,metadata_cache_limit=256)

    @classmethod
    def tearDownClass(cls):pygame.display.quit()

    def setUp(self):self.world.set_progress(set())

    def player(self, tile):
        # Use production movement and its pixel substeps without reloading the
        # unchanged detailed-town character animation catalogue for each probe.
        actor = Player.__new__(Player)
        actor.position = pygame.Vector2(tile)*TILE_SIZE
        actor.facing = 'front';actor.moving = actor.running = False;actor.walk_ms = 0
        return actor

    def test_full_probe_reaches_local_landmarks_but_not_the_far_bank_or_outer_routes(self):
        world = self.world
        start = tuple(round(value/TILE_SIZE) for value in world.town_exit)
        queue = deque([start]);reachable = {start};checked = {start}
        self.assertTrue(world.can_stand(world.town_exit))
        # The modest opening enclosure is tested on the native tile grid. This
        # is deliberately unrelated to the potentially enormous region bounds.
        while queue:
            x,y = queue.popleft()
            for point in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if point in checked:continue
                checked.add(point)
                if not (-140 <= point[0] <= 140 and -110 <= point[1] <= 110):continue
                if world.can_stand((point[0]*TILE_SIZE,point[1]*TILE_SIZE)):
                    reachable.add(point);queue.append(point)
        for landmark in world.region['landmarks']:
            self.assertIn(tuple(landmark['tile_position']),reachable,landmark['id'])
        self.assertIn(tuple(world.region['bridge']['east_approach_tile']),reachable)
        self.assertNotIn(tuple(world.region['bridge']['west_approach_tile']),reachable)
        for gate in world.region['gates']:
            x,y = gate['tile_position']
            self.assertIn((x,y+6 if y<0 else y-6),reachable)
            self.assertNotIn((x,y-6 if y<0 else y+6),reachable)
        self.assertTrue(all(-96 < y < 96 for _,y in reachable),'A wall or checkpoint can be bypassed')
        self.assertNotIn((-140,0),reachable)
        self.assertNotIn((140,0),reachable)

    def test_running_diagonally_cannot_bypass_checkpoints_or_swim_across_rivers(self):
        world = self.world
        for gate in world.region['gates']:
            x,y = gate['tile_position'];inside = y+6 if y<0 else y-6
            for horizontal in (-1,0,1):
                player = self.player((x,inside))
                player.update((horizontal,-1 if y<0 else 1),4,world,running=True)
                if y<0:self.assertGreater(player.position.y,y*TILE_SIZE)
                else:self.assertLess(player.position.y,y*TILE_SIZE)
        player = self.player((105,0))
        player.update((1,0),6,world,running=True)
        self.assertLess(player.position.x,130*TILE_SIZE)
        player = self.player((-98,30))
        player.update((-1,0),6,world,running=True)
        self.assertGreaterEqual(player.position.x,-102*TILE_SIZE+12)

    def test_release_does_not_create_an_unauthored_route_or_repair_the_bridge(self):
        world = self.world
        world.set_progress({'CH01_OPENING_REGION_RELEASED'})
        for gate in world.gates:self.assertFalse(world.can_stand(gate['position']))
        bridge = world.region['bridge']
        self.assertFalse(world.can_stand(world._tile_point(bridge['tile_position'])))
        world.set_progress({bridge['repair_flag']})
        self.assertTrue(world.can_stand(world._tile_point(bridge['tile_position'])))
        player = self.player((-98,30))
        player.update((-1,0),7,world,running=True)
        self.assertLess(player.position.x,-122*TILE_SIZE)
        for gate in world.gates:self.assertFalse(world.can_stand(gate['position']))

    def test_return_landing_shows_the_miniature_and_is_outside_the_entry_trigger(self):
        world = self.world
        self.assertFalse(world.town_entry_rect.colliderect(world.probe_rect(world.town_exit)))
        self.assertTrue(world.can_stand(world.town_exit))
        town = world._tile_point(world.region['town']['tile_position'])
        self.assertGreater(world.town_exit[1],town[1])
        self.assertLess(world.town_exit[1]-town[1],160)
        self.assertTrue(world.art_available)
