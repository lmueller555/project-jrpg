"""Regional geometry and caches stay correct without allocating a whole world."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from overworld_world import OverworldWorld
from bridge_condition import BridgeCondition
from camera_director import CameraDirector
from social import clear_sight


TILE = 24
CHUNK_TILES = 16
CHUNK_PIXELS = TILE * CHUNK_TILES


class OverworldStreamingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((480, 320))

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'region.json'

    def manifest(self, **changes):
        record = {
            'version': 1,
            'id': 'auratia.overworld',
            'name': 'Fixture region',
            'kind': 'overworld',
            'continent': 'Merovar',
            'region': 'fixture',
            'tile_size': TILE,
            'chunk_size': CHUNK_TILES,
            'bounds_tiles': [-32, -32, 64, 64],
            'spawn_tile': [-8, -8],
            'player_probe_size': [24, 12],
            'terrain': {'rivers': [], 'forests': [], 'fields': [], 'hills': []},
            'roads': [],
            'walls': [],
            'gates': [],
            'landmarks': [],
        }
        record.update(changes)
        self.path.write_text(json.dumps(record), encoding='utf-8')
        return record

    def world(self, **options):
        return OverworldWorld(path=self.path, **options)

    def bridge_manifest(self, **changes):
        return self.manifest(terrain={
            'rivers': [{'id': 'west_boundary', 'points': [[0, -32], [0, 32]], 'width': 3}],
            'forests': [], 'fields': [], 'hills': [],
        }, bridge={
            'id': 'west_bridge', 'tile_position': [0, 4],
            'repair_flag': 'WEST_BRIDGE_REPAIRED',
            'damage_rect_tiles': [-6, 2, 12, 4],
            'deck_rect_tiles': [-6, 2, 12, 4],
        }, **changes)

    def condition(self, phase):
        return BridgeCondition(phase=phase, origin='explicit')

    def test_negative_global_coordinates_and_probe_bounds(self):
        self.manifest(landmarks=[{
            'id': 'western_marker', 'name': 'Western marker',
            'tile_position': [-12, -6], 'kind': 'landmark',
        }])
        world = self.world()
        self.assertEqual(world.bounds, pygame.Rect(-768, -768, 1536, 1536))
        self.assertEqual(world.size, (1536, 1536))
        self.assertEqual(tuple(world.data['spawn']), (-192, -192))
        self.assertEqual(tuple(world.data['landmarks'][0]['position']), (-288, -144))
        self.assertTrue(world.can_stand((-192, -192)))
        self.assertTrue(world.can_stand((0, 0)))
        # A centre inside the region is insufficient when its feet cross its edge.
        for position in ((-768, 0), (767, 0), (0, -768), (0, 767),
                         (-769, 0), (768, 0), (0, -769), (0, 768)):
            with self.subTest(position=position):
                self.assertFalse(world.can_stand(position))
        for position in ((-769, 0), (768, 0), (0, -769), (0, 768)):
            self.assertTrue(world.is_blocked_at(position))

    def test_camera_and_sight_use_the_negative_origin_collision_contract(self):
        self.manifest(terrain={
            'rivers': [{'id': 'river', 'points': [[0,-32],[0,32]], 'width': 2}],
            'forests': [], 'fields': [], 'hills': [],
        })
        world = self.world()
        player = SimpleNamespace(position=pygame.Vector2(-700,-700))
        camera = CameraDirector(SimpleNamespace(world=world,player=player))
        self.assertEqual(camera.position(),(-768,-768))
        self.assertTrue(clear_sight(world,pygame.Vector2(-180,-100),pygame.Vector2(-60,-100)))
        self.assertFalse(clear_sight(world,pygame.Vector2(-60,-100),pygame.Vector2(60,-100)))
        self.assertFalse(clear_sight(world,pygame.Vector2(-800,-100),pygame.Vector2(-760,-100)))
        player.position.update(-1,-100);camera.reset();before=camera.position()
        player.position.update(1,-100);camera.update(1/60)
        self.assertIs(camera._world,world)
        self.assertLess(camera.position()[0],-239,'A chunk seam must not cut to the new player position')
        self.assertGreaterEqual(camera.position()[0],before[0])

    def test_decoration_is_stable_after_metadata_eviction_and_progress_changes(self):
        self.manifest(terrain={
            'rivers': [], 'fields': [], 'hills': [],
            'forests': [{'id':'woods','polygon':[[-32,-32],[32,-32],[32,32],[-32,32]]}],
        })
        world = self.world(metadata_cache_limit=1)
        original = world._chunk_metadata(-2,-2)['props']
        self.assertGreater(len(original),0)
        for coord in ((1,1),(-1,1),(1,-1)):world._chunk_metadata(*coord)
        world.set_progress({'unrelated_dialogue_flag'})
        self.assertEqual(world._chunk_metadata(-2,-2)['props'],original)

    def test_collision_probes_span_chunk_edges_and_four_chunk_corner(self):
        self.manifest(terrain={
            'rivers': [{'id': 'seam_river', 'points': [[0, -32], [0, 32]], 'width': 2}],
            'forests': [], 'fields': [], 'hills': [],
        }, walls=[{
            'id': 'seam_wall', 'y': 0, 'x0': -32, 'x1': 32,
            'gate_x': 24, 'gate_width': 4,
        }])
        world = self.world(collision_cache_limit=2)
        for position in ((0, -96), (0, 96), (-96, 0), (96, 0), (0, 0)):
            with self.subTest(position=position):
                self.assertTrue(world.is_blocked_at(position))
                self.assertFalse(world.can_stand(position))
        # The same four loaded quadrants have clear ground away from the cross.
        for position in ((-96, -96), (96, -96), (-96, 96), (96, 96)):
            self.assertTrue(world.can_stand(position))
        # The default 24px-wide feet overlap the river even with a clear centre.
        self.assertFalse(world.can_stand((-30, 96)))
        self.assertFalse(world.can_stand((30, 96)))
        self.assertTrue(world.can_stand((-60, 96)))
        self.assertTrue(world.can_stand((60, 96)))
        # Eviction and a changed query order cannot change seam collision.
        for position in ((0, 0), (96, 0), (0, -96), (-96, 0)):
            self.assertFalse(world.can_stand(position))
        self.assertLessEqual(world.cache_stats['collision_chunks'], 2)

    def test_wide_river_covers_a_chunk_even_when_its_centreline_is_outside_it(self):
        self.manifest(terrain={
            'rivers':[{'id':'offchunk_river','points':[[-1,-32],[-1,32]],'width':4}],
            'forests':[],'fields':[],'hills':[],
        })
        world=self.world()
        # The centre is at x=-24, but the 96px stroke reaches x=+24. It must
        # render and collide inside chunk (0,0), far from either endpoint.
        self.assertTrue(world.is_blocked_at((12,96)))
        self.assertFalse(world.can_stand((30,96)))
        self.assertTrue(world.can_stand((60,96)))
        rendered=world._render_chunk(0,0)
        self.assertEqual(rendered.get_at((12,96)),world._tile_image('water').get_at((12,0)))

    def test_gate_needs_story_clearance_and_an_authored_destination(self):
        def gate(identifier, x, ready):
            return {
                'id': identifier, 'tile_position': [x, 0],
                'rect_tiles': [x - 2, -1, 4, 2],
                'clearance_flag': 'REGION_RELEASED', 'destination_ready': ready,
                'guard_tiles': [[x - 2, 2], [x + 2, 2]], 'label': 'Road checkpoint',
            }
        self.manifest(gates=[gate('ready_gate', -8, True), gate('future_gate', 8, False)])
        world = self.world()
        ready = (-8 * TILE, 0)
        future = (8 * TILE, 0)
        self.assertFalse(world.can_stand(ready))
        self.assertFalse(world.can_stand(future))
        world.set_progress({'REGION_RELEASED'})
        self.assertTrue(world.can_stand(ready))
        self.assertFalse(world.can_stand(future))
        # Removing clearance must invalidate already-built collision too.
        world.set_progress(set())
        self.assertFalse(world.can_stand(ready))

    def test_bridge_repair_is_independent_and_survives_cache_eviction(self):
        self.manifest(terrain={
            'rivers': [{'id': 'west_boundary', 'points': [[0, -32], [0, 32]], 'width': 3}],
            'forests': [], 'fields': [], 'hills': [],
        }, bridge={
            'id': 'west_bridge', 'tile_position': [0, 4],
            'orientation': 'east_west', 'repair_flag': 'WEST_BRIDGE_REPAIRED',
            'damage_rect_tiles': [-6, 2, 12, 4],
            'deck_rect_tiles': [-6, 2, 12, 4],
        }, gates=[{
            'id': 'checkpoint', 'tile_position': [12, 12],
            'rect_tiles': [10, 11, 4, 2], 'clearance_flag': 'REGION_RELEASED',
            'destination_ready': True, 'guard_tiles': [[10, 14], [14, 14]],
            'label': 'Road checkpoint',
        }])
        world = self.world(collision_cache_limit=1, metadata_cache_limit=1,
                           render_budget_bytes=CHUNK_PIXELS * CHUNK_PIXELS * 4)
        bridge = (0, 4 * TILE)
        gate = (12 * TILE, 12 * TILE)
        self.assertFalse(world.can_stand(bridge))
        world.set_progress({'REGION_RELEASED'})
        self.assertFalse(world.can_stand(bridge))
        self.assertTrue(world.can_stand(gate))
        world.set_progress({'WEST_BRIDGE_REPAIRED'})
        self.assertTrue(world.can_stand(bridge))
        self.assertFalse(world.can_stand(gate))
        for cx, cy in ((-2, -2), (1, 1), (-1, 1), (1, -1)):
            world._chunk_metadata(cx, cy)
            world._collision_chunk(cx, cy)
            world._render_chunk(cx, cy)
        self.assertTrue(world.can_stand(bridge))
        # Repair supplies a crossing only on its deck; the river remains solid.
        self.assertFalse(world.can_stand((0, -4 * TILE)))
        # Durable flags reconstruct the same state in a completely fresh cache.
        restored = self.world(progress_flags={'WEST_BRIDGE_REPAIRED'})
        self.assertTrue(restored.can_stand(bridge))
        self.assertFalse(restored.can_stand(gate))

    def test_explicit_bridge_condition_controls_cached_collision_and_survives_flag_updates(self):
        self.bridge_manifest()
        world = self.world(progress_flags={'WEST_BRIDGE_REPAIRED'},
                           bridge_condition=self.condition('destroyed'))
        bridge = (0, 4*TILE)
        self.assertFalse(world.can_stand(bridge))
        damaged = world._render_chunk(0, 0)
        revision = world._revision
        world.set_progress({'WEST_BRIDGE_REPAIRED'}, bridge_condition=self.condition('intact'))
        self.assertEqual(world._revision, revision+1)
        self.assertEqual(world.cache_stats['render_chunks'], 0)
        self.assertEqual(world.cache_stats['collision_chunks'], 0)
        self.assertTrue(world.can_stand(bridge))
        self.assertFalse(world.can_stand((0, -4*TILE)), 'Only the deck cuts through river collision')
        self.assertIsNot(world._render_chunk(0, 0), damaged)
        revision = world._revision
        world.set_progress({'UNRELATED_FACT'})
        self.assertEqual(world.bridge_condition.phase, 'intact')
        self.assertEqual(world._revision, revision)
        world.set_progress(set(), bridge_condition=self.condition('destroyed'))
        self.assertFalse(world.can_stand(bridge))

    def test_intact_to_restored_invalidates_chunks_even_though_both_are_passable(self):
        self.bridge_manifest()
        snapshot = self.condition('intact').to_dict()
        world = self.world(bridge_condition=snapshot, collision_cache_limit=1,
                           render_budget_bytes=CHUNK_PIXELS*CHUNK_PIXELS*4)
        snapshot['phase'] = 'destroyed'
        self.assertEqual(world.bridge_condition.phase, 'intact', 'The constructor copies its input snapshot')
        self.assertTrue(world.can_stand((0, 4*TILE)))
        world._render_chunk(0, 0)
        revision = world._revision
        world.set_progress(set(), bridge_condition=self.condition('restored'))
        self.assertEqual(world._revision, revision+1)
        self.assertEqual(world.cache_stats['render_chunks'], 0)
        self.assertEqual(world.cache_stats['collision_chunks'], 0)
        for cx, cy in ((1, 1), (-1, -1), (1, -1)):
            world._collision_chunk(cx, cy)
            world._render_chunk(cx, cy)
        self.assertTrue(world.can_stand((0, 4*TILE)))
        self.assertEqual(world.bridge_condition.phase, 'restored')

    def test_bridge_scorch_changes_with_phase_without_hiding_unrelated_damage(self):
        from overworld_environment import EnvironmentDetail

        def scar(identifier, x):
            return {'id': identifier, 'polygon': [[x, 5], [x+2, 5], [x+2, 9], [x, 9]]}

        self.manifest(terrain={'rivers': [], 'forests': [], 'fields': [], 'hills': [],
            'scorched': [scar('broken_bridge_east_bank', 2), scar('broken_bridge_west_bank', 6),
                         scar('unrelated_burn', 10)]},
            roads=[{'id': 'road', 'points': [[0, 7], [15, 7]], 'width': 1}])
        # Test both the artless fixture path and EnvironmentDetail.ground's
        # separate material layer, including scars beside and across a road.
        for detailed in (False, True):
            with self.subTest(environment_detail=detailed):
                world = self.world(bridge_condition=self.condition('intact'))
                if detailed:world.environment = EnvironmentDetail(world)
                samples = [(x*TILE, round(y*TILE)) for x in (3, 7, 11) for y in (5.5, 7)]
                intact = [world._render_chunk(0, 0).get_at(p) for p in samples]
                world.set_progress(set(), bridge_condition=self.condition('destroyed'))
                destroyed = [world._render_chunk(0, 0).get_at(p) for p in samples]
                world.set_progress(set(), bridge_condition=self.condition('restored'))
                restored = [world._render_chunk(0, 0).get_at(p) for p in samples]
                self.assertEqual(restored, destroyed, 'Restoring the crossing does not erase its scars')
                for before, after in zip(intact[:4], destroyed[:4]):self.assertNotEqual(before, after)
                self.assertEqual(intact[4:], destroyed[4:], 'Unrelated scorched ground is phase independent')

    def test_absent_sparse_chunk_is_solid_even_inside_region_bounds(self):
        self.manifest(bounds_tiles=[-16, -16, 48, 48], spawn_tile=[8, 8],
                      chunk_whitelist=[[0, 0]])
        world = self.world()
        self.assertTrue(world.can_stand((8 * TILE, 8 * TILE)))
        for position in ((-8 * TILE, 8 * TILE), (24 * TILE, 8 * TILE),
                         (8 * TILE, -8 * TILE), (8 * TILE, 24 * TILE)):
            self.assertTrue(world.is_blocked_at(position))
            self.assertFalse(world.can_stand(position))
        # Feet touching a missing neighbour cannot cross before it is authored.
        self.assertFalse(world.can_stand((CHUNK_PIXELS - 1, 8 * TILE)))

    def test_thousand_chunks_keep_render_collision_and_metadata_caches_bounded(self):
        self.manifest(bounds_tiles=[-8000, -16, 16000, 32], spawn_tile=[0, 8])
        chunk_bytes = CHUNK_PIXELS * CHUNK_PIXELS * 4
        budget = 2 * chunk_bytes + 1024
        world = self.world(render_budget_bytes=budget,
                           collision_cache_limit=3, metadata_cache_limit=5)
        for cx in range(-500, 500):
            world._chunk_metadata(cx, 0)
            mask = world._collision_chunk(cx, 0)
            surface = world._render_chunk(cx, 0)
            self.assertEqual(mask.get_size(), (CHUNK_PIXELS, CHUNK_PIXELS))
            self.assertEqual(surface.get_size(), (CHUNK_PIXELS, CHUNK_PIXELS))
            if cx % 100 == 0:
                stats = world.cache_stats
                self.assertLessEqual(stats['render_bytes'], budget)
                self.assertLessEqual(stats['render_chunks'], 2)
                self.assertLessEqual(stats['collision_chunks'], 3)
                self.assertLessEqual(stats['metadata_chunks'], 5)
        stats = world.cache_stats
        self.assertGreater(stats['render_chunks'], 0)
        self.assertLessEqual(stats['render_bytes'], budget)
        self.assertLessEqual(stats['render_chunks'], 2)
        self.assertLessEqual(stats['collision_chunks'], 3)
        self.assertLessEqual(stats['metadata_chunks'], 5)
        # Revisiting an evicted negative chunk reloads correctly within the cap.
        self.assertTrue(world.can_stand((-7992 * TILE, 8 * TILE)))
        self.assertEqual(world._render_chunk(-500, 0).get_size(),
                         (CHUNK_PIXELS, CHUNK_PIXELS))
        self.assertLessEqual(world.cache_stats['render_bytes'], budget)


if __name__ == '__main__':
    unittest.main()
