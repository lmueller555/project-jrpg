"""Registered bridge art, depth and full-foot traversal use the same phases."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame

from bridge_condition import BridgeCondition
from main import Player
from overworld_world import OverworldWorld


class BridgeLayersWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((480,320))

    @classmethod
    def tearDownClass(cls):pygame.display.quit()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.layers = {'version':1,'canvas':[288,144],'anchor':[144,94],
                       'deck_top_px':34,'deck_bottom_px':106,'phases':{}}
        for phase,color in (('intact','#234ab5'),('destroyed','#234ab5'),('restored','#b56b23')):
            records = {}
            for name,rect,tint,offset in (
                    ('deck',(0,34,288,72),color,None),
                    ('far',(0,22,288,12),'#a52323',-60),
                    ('near',(0,106,288,16),'#238a45',14)):
                image = pygame.Surface((288,144),pygame.SRCALPHA)
                pygame.draw.rect(image,tint,rect)
                if phase == 'destroyed':
                    image.fill((0,0,0,0),(107,0,74,144))
                    # A missing corner beyond the rectangular support contract
                    # must also remain unsafe for the entire foot probe.
                    if name == 'deck':image.fill((0,0,0,0),(95,34,12,24))
                path = self.folder/f'{phase}_{name}.png';pygame.image.save(image,path)
                records[name] = {'image':str(path),'foot_anchor':[144,94]}
                if offset is not None:records[name]['sort_offset'] = offset
            self.layers['phases'][phase] = records
        self.layer_path = self.folder/'layers.json'
        self.layer_path.write_text(json.dumps(self.layers))
        self.record = {
            'version':1,'id':'bridge.fixture','kind':'overworld','name':'Bridge fixture',
            'tile_size':24,'chunk_size':16,'bounds_tiles':[-32,-32,64,64],
            'spawn_tile':[-12,3],'terrain':{'rivers':[
                {'id':'western_boundary_river','width':10,'points':[[0,-32],[0,32]]}],
                'forests':[],'fields':[],'hills':[]},'roads':[],'walls':[],'gates':[],
            'landmarks':[], 'bridge':{
                'tile_position':[0,4],'repair_flag':'REPAIRED','damage_rect_tiles':[-9,0,18,8],
                'deck_rect_tiles':[-9,1.5,18,3],'deck_width_tiles':3,'deck_center_tile_y':3,
                'destroyed_walkable_rect_tiles':[[-9,1.5,179/24,3],[37/24,1.5,179/24,3]],
                'layers_manifest':str(self.layer_path)}}
        self.path = self.folder/'region.json'

    def world(self, phase='intact', **options):
        self.path.write_text(json.dumps(self.record))
        world = OverworldWorld(self.path,bridge_condition=BridgeCondition(phase),**options)
        world.npcs = []
        return world

    @staticmethod
    def player(position):
        actor = Player.__new__(Player)
        actor.position = pygame.Vector2(position)
        actor.facing = 'right';actor.moving = actor.running = False;actor.walk_ms = 0
        return actor

    def test_walk_and_run_cross_both_directions_but_cannot_leave_deck_into_water(self):
        for phase in ('intact','restored'):
            world = self.world(phase)
            for running in (False,True):
                for direction in (-1,1):
                    with self.subTest(phase=phase,running=running,direction=direction):
                        actor = self.player((-direction*240,72))
                        actor.update((direction,0),8,world,running=running)
                        self.assertGreater(actor.position.x*direction,240)
                for vertical in (-1,1):
                    actor = self.player((0,72))
                    actor.update((0,vertical),2,world,running=running)
                    self.assertTrue(world.can_stand(actor.position))
                    self.assertGreaterEqual(round(actor.position.y),42)
                    self.assertLessEqual(round(actor.position.y),102)
                actor = self.player((0,72))
                actor.update((1,-1),.5,world,running=running)
                self.assertTrue(world.can_stand(actor.position))
                self.assertGreaterEqual(round(actor.position.y),42)

    def test_destroyed_ends_are_reachable_but_gap_and_transparent_tips_are_unsafe(self):
        world = self.world('destroyed')
        self.assertTrue(world.can_stand((-90,72)))
        self.assertTrue(world.can_stand((90,72)))
        self.assertFalse(world.can_stand((0,72)))
        self.assertFalse(world.can_stand((-42,48)), 'Missing floor at the fracture is water, not support')
        for direction in (-1,1):
            actor = self.player((-direction*240,72))
            actor.update((direction,0),8,world,running=True)
            self.assertLess(actor.position.x*direction,0)
            self.assertTrue(world.can_stand(actor.position))

    def test_deck_is_below_actor_far_rail_behind_and_near_rail_in_front(self):
        world = self.world()
        body = pygame.Surface((12,100),pygame.SRCALPHA);body.fill('#ed31d2')
        actor = SimpleNamespace(position=pygame.Vector2(0,72),sprite=lambda:body)
        world.data['player_draw_anchor'] = [6,90]
        target = pygame.Surface((480,320));camera = (-240,-32)
        def pixel(x,y):return target.get_at((x-camera[0],y-camera[1]))[:3]
        world.draw(target,camera,actor,0)
        self.assertEqual(pixel(20,60),pygame.Color('#234ab5')[:3])
        self.assertEqual(pixel(0,30),pygame.Color('#ed31d2')[:3], 'Actor must overpaint the far parapet')
        actor.position.y = 102;world.draw(target,camera,actor,0)
        self.assertEqual(pixel(0,109),pygame.Color('#238a45')[:3], 'Near parapet must cover crossing feet')
        actor.position.y = 130;world.draw(target,camera,actor,0)
        self.assertEqual(pixel(0,109),pygame.Color('#ed31d2')[:3], 'An actor south of the bridge is in front')
        world.set_progress(set(),bridge_condition=BridgeCondition('restored'))
        actor.position.x = 300;world.draw(target,camera,actor,0)
        self.assertEqual(pixel(20,60),pygame.Color('#b56b23')[:3])

    def test_phase_change_and_eviction_rebuild_supported_floor(self):
        world = self.world(collision_cache_limit=1,render_budget_bytes=384*384*4)
        self.assertTrue(world.can_stand((0,72)));world._render_chunk(0,0)
        world.set_progress(set(),bridge_condition=BridgeCondition('destroyed'))
        self.assertFalse(world.can_stand((0,72)))
        for cx,cy in ((1,1),(-1,-1),(1,-1)):
            world._collision_chunk(cx,cy);world._render_chunk(cx,cy)
        self.assertTrue(world.can_stand((-90,72)))
        self.assertFalse(world.can_stand((0,72)))
        world.set_progress(set(),bridge_condition=BridgeCondition('intact'))
        self.assertTrue(world.can_stand((0,72)))

    def test_far_bank_enclosure_is_visible_and_does_not_block_the_inner_vale(self):
        self.record['far_bank'] = {'western_river_id':'western_boundary_river',
            'playable_polygon':[[-15,-8],[-3,-8],[-3,12],[-15,12]],
            'boundary_segments':[{'points':[[-15,-8],[-3,-8]],'width_tiles':1.25}]}
        world = self.world()
        self.assertTrue(world.can_stand((-8*24,8*24)))
        self.assertFalse(world.can_stand((-20*24,0)))
        self.assertFalse(world.can_stand((-8*24,-15*24)))
        self.assertTrue(world.can_stand((12*24,-15*24)), 'Eastern land retains its own boundaries')
        self.assertTrue(world.can_stand((0,72)), 'The bridge connector takes priority over the bank polygon')
        self.assertFalse(world.can_stand((-10*24,-8*24)))
        rock = world._render_chunk(-1,-1).get_at((6*24,8*24))
        grass = world._render_chunk(0,-1).get_at((12*24,8*24))
        self.assertNotEqual(rock,grass, 'The solid shelf has a visible terrain band')

    def test_bank_selection_follows_the_nearby_river_bend(self):
        self.record['terrain']['rivers'][0]['points'] = [[-15,-32],[0,0],[15,32]]
        world = self.world()
        self.assertEqual(world.bridge_bank((-12*24,-24*24)),'west')
        self.assertEqual(world.bridge_bank((-8*24,-24*24)),'east')
        self.assertEqual(world.bridge_bank((8*24,24*24)),'west')
        self.assertEqual(world.bridge_bank((12*24,24*24)),'east')

    def test_mismatched_layer_registration_is_rejected(self):
        self.layers['phases']['restored']['near']['foot_anchor'] = [143,94]
        self.layer_path.write_text(json.dumps(self.layers))
        with self.assertRaisesRegex(ValueError,'share their anchor'):self.world()
