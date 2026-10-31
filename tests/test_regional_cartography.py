"""Illustrated chart registration, state and residency are independent of world size."""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame

from regional_cartography import (RegionalCartography,get_cartography,
                                   geometry_fingerprint,tile_to_pixel,ROOT)


class RegionalCartographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((960,640))
        cls.region = json.loads((ROOT/'assets/maps/overworld/elden_vale/region.json').read_text())

    @classmethod
    def tearDownClass(cls):pygame.display.quit()

    def test_painted_geography_matches_source_and_signed_coordinates(self):
        chart = RegionalCartography(self.region)
        self.assertTrue(chart.available)
        self.assertEqual(chart.manifest['geometry_sha256'],geometry_fingerprint(self.region))
        self.assertEqual(chart.bounds,(-256,-192,512,384))
        self.assertEqual(chart.focus_bounds,(-140,-110,280,220))
        rect = pygame.Rect(20,30,800,500)
        self.assertEqual(tile_to_pixel((-111,29),rect,(-111,29),2),rect.center)
        point = tile_to_pixel((-124,-96),rect,(-111,29),2)
        self.assertEqual(point,(rect.centerx-26,rect.centery-250))

    def test_render_is_exact_across_viewport_seams_at_negative_origins(self):
        chart = RegionalCartography(self.region)
        for scale in (1.75,3,6):
            with self.subTest(scale=scale):
                full = pygame.Surface((768,384));left = pygame.Surface((384,384));right = pygame.Surface((384,384))
                chart.draw_terrain(full,full.get_rect(),(-32,-32),scale)
                chart.draw_terrain(left,left.get_rect(),(-32-192/scale,-32),scale)
                chart.draw_terrain(right,right.get_rect(),(-32+192/scale,-32),scale)
                joined = pygame.Surface(full.get_size());joined.blit(left,(0,0));joined.blit(right,(384,0))
                self.assertEqual(pygame.image.tobytes(joined,'RGB'),pygame.image.tobytes(full,'RGB'))

    def test_tile_and_icon_caches_stay_bounded_after_eviction_and_zoom(self):
        budget = 3*512*512*4
        chart = RegionalCartography(self.region,cache_budget_bytes=budget)
        target = pygame.Surface((512,512));first = None
        records = [record for record in chart.manifest['tiles'] if record['level']==1]
        bx,by,_,_ = chart.bounds;density = chart.manifest['pixels_per_tile']
        for index,record in enumerate(records):
            center = (bx+(record['x']*512+record['size'][0]/2)/density,
                      by+(record['y']*512+record['size'][1]/2)/density)
            chart.draw_terrain(target,target.get_rect(),center,density)
            if index==0:first = center,pygame.image.tobytes(target,'RGB')
            self.assertLessEqual(chart.cache_stats['tile_bytes'],budget)
        self.assertGreater(chart.cache_stats['tile_loads'],chart.cache_stats['tile_count'])
        chart.draw_terrain(target,target.get_rect(),first[0],density)
        self.assertEqual(pygame.image.tobytes(target,'RGB'),first[1])
        for size in range(8,180,3):
            icon = chart.icon('town',(size,size))
            self.assertIsNotNone(icon)
            self.assertLessEqual(max(icon.get_size()),size)
            self.assertLessEqual(chart.cache_stats['icon_bytes'],chart.cache_stats['icon_budget'])

    def test_ordinary_minimap_draw_does_not_hash_geometry_each_frame(self):
        data = deepcopy(self.region);game = SimpleNamespace(world=SimpleNamespace(region=data))
        chart = get_cartography(game)
        with patch('regional_cartography.geometry_fingerprint',side_effect=AssertionError('Per-frame serialization')):
            for _ in range(5):
                self.assertIs(get_cartography(game),chart)
                self.assertTrue(chart.compatible)
        data['terrain']['fields'].append({'id':'new_plot','polygon':[[0,0],[1,0],[0,1]],'crop':'grain'})
        get_cartography(game,refresh=True)
        self.assertFalse(chart.compatible)

    def test_huge_unpainted_world_uses_display_sized_fallback(self):
        world = SimpleNamespace(data={'bounds_tiles':[-10000000,-10000000,20000000,20000000],
                                      'terrain':{},'roads':[],'walls':[]})
        world.draw = lambda *args: self.fail('Gameplay rendering was requested')
        chart = RegionalCartography(world)
        target = pygame.Surface((208,156))
        self.assertFalse(chart.draw_terrain(target,target.get_rect(),(-1000,-2000),1))
        self.assertEqual(chart.cache_stats['tile_bytes'],0)
        self.assertFalse(chart.compatible)
        self.assertEqual(chart.focus_bounds,tuple(world.data['bounds_tiles']))

    def test_foreign_region_fit_uses_its_own_remote_bounds(self):
        region = {'region_id':'later_region','bounds_tiles':[10000,12000,64,48],
                  'terrain':{},'roads':[],'walls':[]}
        chart = RegionalCartography(region)
        self.assertEqual(chart.focus_bounds,(10000,12000,64,48))
        self.assertFalse(chart.available)
        region['focus_bounds_tiles'] = [10008,12008,24,24]
        chart.refresh()
        self.assertEqual(chart.focus_bounds,(10008,12008,24,24))

    def test_broken_crossing_interrupts_live_road_until_independent_repair(self):
        chart = RegionalCartography(self.region)
        target = pygame.Surface((400,240));rect = target.get_rect();center=(-111,29)
        baseline = pygame.Color('#213429')[:3]
        target.fill(baseline);chart.draw_routes(target,rect,center,4,flags=set())
        self.assertEqual(target.get_at(rect.center)[:3],baseline)
        target.fill(baseline)
        chart.draw_routes(target,rect,center,4,flags={self.region['bridge']['repair_flag']})
        self.assertNotEqual(target.get_at(rect.center)[:3],baseline)
        self.assertNotIn('flags',self.region)

    def test_footpath_dash_phase_is_independent_of_curve_sampling(self):
        data = {'bounds_tiles':[-32,-16,64,32],'terrain':{},'walls':[],
                'roads':[{'kind':'foot','points':[[-20,0],[20,0]],'width':1.2}]}
        chart = RegionalCartography(data)
        target = pygame.Surface((240,120));rect = target.get_rect()
        target.fill('#203126');chart.draw_routes(target,rect,(0,0),3)
        sparse = pygame.image.tobytes(target,'RGB')
        data['roads'][0]['points'] = [[x/2,0] for x in range(-40,41)]
        target.fill('#203126');chart.draw_routes(target,rect,(0,0),3)
        self.assertEqual(pygame.image.tobytes(target,'RGB'),sparse)
        colors = {target.get_at((x,60))[:3] for x in range(61,180)}
        self.assertIn(pygame.Color('#203126')[:3],colors)
        self.assertGreater(len(colors),1)


if __name__=='__main__':unittest.main()
