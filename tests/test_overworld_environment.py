"""Materials and composed scenery remain stable across streaming seams."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame

from overworld_world import OverworldWorld


class OverworldEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((480,320))

    @classmethod
    def tearDownClass(cls):pygame.display.quit()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        tile = pygame.Surface((24,24));tile.fill('#914646')
        pygame.draw.rect(tile,'#d7c359',(0,0,12,12))
        pygame.draw.rect(tile,'#326f5b',(12,12,12,12))
        self.tile = self.root/'material.png';pygame.image.save(tile,self.tile)
        prop = pygame.Surface((18,28),pygame.SRCALPHA);prop.fill('#516c36')
        self.prop = self.root/'prop.png';pygame.image.save(prop,self.prop)
        base = {'version':1,'tiles':{'grass':{'image':str(self.tile)}},
                'props':{'legacy_marker':{'image':str(self.prop),'foot_anchor':[9,28]}}}
        self.base = self.root/'base.json';self.base.write_text(json.dumps(base))
        names = ('oak_a','oak_b','oak_c','conifer_a','conifer_b','fern','shrub','sapling','log','stump','bird_1','bird_2')
        detail = {'version':1,'tiles':{'grain':{'image':str(self.tile)}},
                  'props':{name:{'image':str(self.prop),'foot_anchor':[9,28]} for name in names}}
        self.detail = self.root/'detail.json';self.detail.write_text(json.dumps(detail))

    def world(self, **changes):
        data = {'version':1,'id':'auratia.overworld','name':'Fixture','kind':'overworld',
                'tile_size':24,'chunk_size':16,'bounds_tiles':[-32,-32,64,64],
                'spawn_tile':[0,0],'terrain':{'rivers':[],'forests':[],'fields':[],'hills':[]},
                'roads':[],'walls':[],'gates':[],'landmarks':[],
                'art_manifest':str(self.base),'detail_art_manifest':str(self.detail)}
        data.update(changes)
        path = self.root/'region.json';path.write_text(json.dumps(data))
        return OverworldWorld(path,metadata_cache_limit=2,collision_cache_limit=2)

    def test_detail_art_extends_base_without_removing_existing_assets(self):
        world = self.world()
        self.assertIn('legacy_marker',world._art['props'])
        self.assertIn('oak_a',world._art['props'])
        self.assertIn('grass',world._art['tiles'])
        self.assertIn('grain',world._art['tiles'])
        self.assertEqual(world._prop_image('legacy_marker')[0].get_size(),(18,28))
        self.assertEqual(world._prop_image('oak_a')[1],(9,28))

    def test_rotated_crop_material_matches_a_single_continuous_render_across_negative_seam(self):
        world = self.world()
        for angle in (-30,30,90):
            with self.subTest(angle=angle):
                complete = pygame.Surface((768,384),pygame.SRCALPHA)
                left = pygame.Surface((384,384),pygame.SRCALPHA)
                right = pygame.Surface((384,384),pygame.SRCALPHA)
                world.environment.pattern(complete,'grain',(-384,-384),angle)
                world.environment.pattern(left,'grain',(-384,-384),angle)
                world.environment.pattern(right,'grain',(0,-384),angle)
                stitched = pygame.Surface((768,384),pygame.SRCALPHA)
                stitched.blit(left,(0,0));stitched.blit(right,(384,0))
                self.assertEqual(pygame.image.tobytes(complete,'RGBA'),pygame.image.tobytes(stitched,'RGBA'))
                # A rotated swatch must cover the ground continuously rather
                # than leaving transparent diamond-shaped gaps at its corners.
                self.assertEqual(pygame.mask.from_surface(complete).count(),768*384)

    def test_clustered_forest_variety_and_placement_survive_eviction_and_avoid_paths(self):
        world = self.world(terrain={'rivers':[],'fields':[],'hills':[],
                           'forests':[{'id':'grove','polygon':[[-31,-31],[31,-31],[31,31],[-31,31]],
                                       'style':'mixed','density':'dense'}]},
                           roads=[{'id':'path','kind':'foot','surface':'dirt','width':2,
                                   'points':[[-31,0],[31,0]]}])
        coordinates = [(-1,-1),(0,-1),(-1,0),(0,0)]
        def snapshot(coord):
            return [(p['id'],p['key'],p['position'],bool(p.get('solid'))) for p in world._chunk_metadata(*coord)['props']]
        original = {coord:snapshot(coord) for coord in coordinates}
        for coord in reversed(coordinates):self.assertEqual(snapshot(coord),original[coord])
        keys = {key for props in original.values() for _,key,_,_ in props}
        self.assertTrue({'oak_a','oak_b','oak_c','conifer_a','conifer_b'} <= keys)
        self.assertGreaterEqual(len(keys & {'fern','shrub','sapling','log','stump'}),3)
        for props in original.values():
            for _,_,point,solid in props:
                if solid:self.assertGreater(abs(point[1]),24*(1+1.3))
        self.assertLessEqual(world.cache_stats['metadata_chunks'],2)

    def test_polished_region_keeps_bounded_residency_across_a_thousand_chunks(self):
        world = self.world(bounds_tiles=[-8000,-16,16000,32],spawn_tile=[0,8])
        world._render_cache.limit = 2*384*384*4
        for cx in range(-500,500):
            world._render_chunk(cx,0)
            self.assertTrue(world.can_stand((cx*384+192,192)))
        stats = world.cache_stats
        self.assertLessEqual(stats['render_chunks'],2)
        self.assertLessEqual(stats['metadata_chunks'],2)
        self.assertLessEqual(stats['collision_chunks'],2)
        self.assertLessEqual(stats['render_bytes'],2*384*384*4)

    def test_ambient_frames_move_visually_without_changing_authored_feet(self):
        world = self.world()
        prop = {'key':'bird_1','position':(48,72),'solid':(8,6),
                'animation':{'frames':['bird_1','bird_2'],'frame_ms':80},
                'motion':'flutter','amplitude':2}
        original = dict(prop)
        frames = [world.environment.prop_frame(prop,time) for time in (0,80,160,240,320)]
        self.assertEqual({key for key,_ in frames},{'bird_1','bird_2'})
        self.assertTrue(all(abs(point[0]-48)<=2 and abs(point[1]-72)<=2 for _,point in frames))
        self.assertEqual(prop,original)


if __name__ == '__main__':unittest.main()
