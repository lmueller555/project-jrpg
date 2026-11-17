"""Live regional density, preserved geometry, streaming and scenery contracts."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from overworld_world import OverworldWorld, REGION_FILE
from rendering import layer

ROOT=Path(__file__).resolve().parents[1]

class EldenValeHDIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((960,640))
    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_active_registry_preserves_existing_gameplay_topology(self):
        region=json.loads(REGION_FILE.read_text())
        baseline=json.loads((ROOT/'assets/source/maps/overworld/elden_vale/hd_integration/preserved_geometry.json').read_text())
        for key,expected in baseline['fields'].items():
            actual=hashlib.sha256(json.dumps(region[key],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            self.assertEqual(actual,expected,key)
        for key in ('clearance_paths','safe_clearings'):
            for record in baseline['existing_'+key]:self.assertIn(record,region[key])
        registry=json.loads((ROOT/region['hd_art_manifest']).read_text())
        self.assertEqual(registry['integration_status'],'integrated')
        self.assertEqual(len(region['design_layout']['areas']),6)
        self.assertEqual(region['design_layout']['antlers']['collision'],'none; do not solidify the hillside')
        self.assertTrue(region['terrain_hd']['enabled'])

    def test_no_new_solid_ground_from_hd_or_reservations(self):
        region=json.loads(REGION_FILE.read_text());baseline=copy.deepcopy(region)
        baseline.pop('terrain_hd');baseline.pop('hd_art_manifest');baseline.pop('design_layout')
        frozen=json.loads((ROOT/'assets/source/maps/overworld/elden_vale/hd_integration/preserved_geometry.json').read_text())
        baseline['clearance_paths']=frozen['existing_clearance_paths'];baseline['safe_clearings']=frozen['existing_safe_clearings']
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'old.json';path.write_text(json.dumps(baseline))
            old=OverworldWorld(path);new=OverworldWorld()
            for coordinate in [(0,-2),(-1,0),(-7,1),(-8,-1),(-3,-5),(5,-5),(1,-6),(1,6),(-1,3),(3,3)]:
                before=old._collision_chunk(*coordinate);after=new._collision_chunk(*coordinate).copy()
                after.erase(before,(0,0))
                self.assertEqual(after.count(),0,coordinate)
            for gate in new.gates:self.assertFalse(new.can_stand(gate['position']))
            self.assertFalse(new._bridge_repaired())

    def test_native_chunk_retains_detail_and_lru_stays_bounded(self):
        world=OverworldWorld(render_budget_bytes=7*1024*1024,collision_cache_limit=3,metadata_cache_limit=3)
        chunk=world._render_chunk(0,-2)
        self.assertEqual(chunk.native.get_size(),(768,768))
        enlarged=pygame.transform.scale(chunk,(768,768))
        self.assertNotEqual(pygame.image.tobytes(chunk.native,'RGB'),pygame.image.tobytes(enlarged,'RGB'))
        for coordinate in [(0,-2),(-1,0),(-7,1),(5,-5),(-3,-5)]:world._render_chunk(*coordinate)
        self.assertLessEqual(world.cache_stats['render_bytes'],7*1024*1024)
        self.assertLessEqual(world.cache_stats['metadata_chunks'],3)

    def test_registered_scenery_breeze_and_still_frames_keep_feet(self):
        world=OverworldWorld()
        first,anchor=world._prop_image('oak_a',0)
        self.assertTrue(hasattr(first,'native'))
        self.assertEqual(first.get_size(),(48,60))
        self.assertEqual(anchor,(24,60))
        frames=[world._prop_image('oak_a',time)[0] for time in range(0,5400,600)]
        self.assertGreater(len({pygame.image.tobytes(image.native,'RGBA') for image in frames}),1)
        for image in frames:
            self.assertEqual(world._prop_image('oak_a')[1],anchor)
            self.assertEqual(pygame.image.tobytes(first.native.subsurface((0,112,96,8)),'RGBA'),
                             pygame.image.tobytes(image.native.subsurface((0,112,96,8)),'RGBA'))
        world.reduced_motion=True
        self.assertIs(world._prop_image('oak_a',0)[0],world._prop_image('oak_a',9999)[0])

    def test_world_water_still_and_bridge_fact_remain_independent(self):
        world=OverworldWorld();camera=(-122*24,-10*24)
        def water(time):
            target=layer((480,320));world._draw_water(target,camera,time)
            return pygame.image.tobytes(target.native,'RGBA')
        self.assertNotEqual(water(0),water(200))
        world.reduced_motion=True
        self.assertEqual(water(0),water(9999))
        world.set_progress({'CH01_OPENING_REGION_RELEASED'})
        self.assertFalse(world._bridge_repaired())
        for gate in world.gates:self.assertFalse(world._gate_open(gate))

    def test_game_focus_and_pause_freeze_regional_time_and_movement(self):
        from main import Game
        with tempfile.TemporaryDirectory() as directory:
            game=Game(fullscreen=False,start_on_title=True,
                      save_path=Path(directory)/'journey.json',
                      settings_path=Path(directory)/'settings.json')
            self.addCleanup(game.music.stop)
            game.on_title=False;game.opening.restore({'version':1,'stage':'disabled'})
            game.world=game.overworld_world;game.player.position.update(288,-552)
            game.opening_fade=game.transfer_cooldown=0
            self.assertTrue(game.world.data['pause_on_focus_loss'])
            game.update(.1,(0,0),False)
            before=(game.elapsed_ms,tuple(game.player.position))
            game._music_focused=False;game.update(.5,(1,0),True)
            self.assertEqual((game.elapsed_ms,tuple(game.player.position)),before)
            game._music_focused=True;game.pause.is_open=True
            game.update(.5,(1,0),True)
            self.assertEqual((game.elapsed_ms,tuple(game.player.position)),before)
            game.pause.is_open=False;game.update(.1,(0,1),False)
            self.assertGreater(game.elapsed_ms,before[0])
            self.assertNotEqual(tuple(game.player.position),before[1])
            game.audio.set_reduced_motion(True);game.draw()
            self.assertTrue(game.world.reduced_motion)
