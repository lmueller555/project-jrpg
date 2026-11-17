"""Explicit layer/native visibility contracts without production activation."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
import pygame
from landmark_layers import LandmarkLayers
from rendering import WorldCanvas

class LandmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((960,640))
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        image=pygame.Surface((1600,160),pygame.SRCALPHA);image.fill((160,150,130,255))
        image.set_at((1521,81),(0,0,0,255))
        pygame.image.save(image,self.root/'beam.png')
        self.record={'image':'beam.png','logical_size':[800,80],
                     'artwork_pixels_per_world_pixel':2,'position':[-750,0],
                     'layer':'overhead','collision':'none','occlusion_mask':'beam.png'}
    def tearDown(self):self.temp.cleanup()
    def test_complete_bounds_cull_even_when_root_is_far_outside_view(self):
        layers=LandmarkLayers(self.root,[self.record]);target=WorldCanvas((80,80),pygame.SRCALPHA)
        layers.draw(target,(0,0),'overhead')
        self.assertEqual(target.native.get_at((21,81)),(0,0,0,255))
        self.assertEqual(len(list(layers.visible(pygame.Rect(800,0,80,80),'overhead'))),0)
    def test_story_position_companions_and_interactions_cut_only_locally(self):
        layers=LandmarkLayers(self.root,[self.record]);actor=SimpleNamespace(position=(700,700),story_position=(20,50))
        target=WorldCanvas((80,80),pygame.SRCALPHA)
        layers.draw(target,(0,0),'overhead',actors=[actor])
        self.assertLess(target.native.get_at((40,64)).a,100)
        self.assertEqual(target.native.get_at((4,4)).a,255)
        first=pygame.image.tobytes(target.native,'RGBA')
        target.fill((0,0,0,0));layers.draw(target,(0,0),'overhead',interaction_points=[(20,32)])
        self.assertEqual(first,pygame.image.tobytes(target.native,'RGBA'))
        self.assertEqual(layers.image(self.record).native.get_at((1540,64)).a,255)
    def test_positions_do_not_grow_cache_and_work_is_viewport_bounded(self):
        layers=LandmarkLayers(self.root,[self.record],budget=4*1024*1024)
        target=WorldCanvas((80,80),pygame.SRCALPHA)
        for x in range(250):layers.draw(target,(0,0),'overhead',interaction_points=[(x,30)])
        self.assertLessEqual(layers.sources.bytes,layers.sources.budget)
        self.assertEqual(len(layers.sources),2)
        self.assertLessEqual(layers.working_bytes,80*80*4*18)
    def test_explicit_roles_and_no_artwork_collision(self):
        with self.assertRaises(ValueError):LandmarkLayers(self.root,[{**self.record,'layer':'ordinary'}])
        with self.assertRaises(ValueError):LandmarkLayers(self.root,[{**self.record,'collision':'alpha'}])
    def test_layer_filtering(self):
        layers=LandmarkLayers(self.root,[self.record]);target=WorldCanvas((80,80),pygame.SRCALPHA)
        layers.draw(target,(0,0),'ground')
        self.assertEqual(pygame.mask.from_surface(target.native).count(),0)

    def test_zero_authored_mask_preserves_opaque_drawing(self):
        mask=pygame.Surface((1600,160));mask.fill((0,0,0))
        pygame.image.save(mask,self.root/'mask.png')
        layers=LandmarkLayers(self.root,[{**self.record,'occlusion_mask':'mask.png'}])
        target=WorldCanvas((80,80),pygame.SRCALPHA)
        layers.draw(target,(0,0),'overhead',interaction_points=[(20,32)])
        self.assertEqual(target.native.get_at((40,64)).a,255)

    def test_half_unit_origin_survives_cutaway_and_camera_edge(self):
        layers=LandmarkLayers(self.root,[{**self.record,'position':[-750.5,-.5]}])
        target=WorldCanvas((80,80),pygame.SRCALPHA)
        layers.draw(target,(0,0),'overhead',interaction_points=[(5,5)])
        self.assertEqual(target.native.get_at((20,80)),(0,0,0,255))

    def test_distant_vista_never_reads_as_walkable_lawn_prop(self):
        record={**self.record,'layer':'distant','viewing_area_logical':[0,100,800,500],'vista_fade_margin_logical':20}
        layers=LandmarkLayers(self.root,[record]);target=WorldCanvas((80,80),pygame.SRCALPHA)
        viewer=SimpleNamespace(position=(20,80))
        layers.draw(target,(0,0),'distant',viewer=viewer)
        self.assertEqual(pygame.mask.from_surface(target.native).count(),0)
        viewer.position=(20,120);layers.draw(target,(0,0),'distant',viewer=viewer)
        self.assertEqual(target.native.get_at((4,4)).a,255)
        target.fill((0,0,0,0));viewer.position=(20,110)
        layers.draw(target,(0,0),'distant',viewer=viewer)
        self.assertTrue(120<=target.native.get_at((4,4)).a<=135)
        self.assertEqual(len(layers.sources),1)
