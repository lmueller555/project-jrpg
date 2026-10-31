"""Composed groves, ground contacts and bridge art agree across streaming."""
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame

from overworld_world import OverworldWorld


class OverworldCompositionEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((480,320))

    @classmethod
    def tearDownClass(cls):pygame.display.quit()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        def image(name,size,color):
            surface = pygame.Surface(size,pygame.SRCALPHA);surface.fill(color)
            path = self.root/name;pygame.image.save(surface,path)
            return str(path)
        grass = image('grass.png',(24,24),'#5a7846')
        leaf = image('leaf.png',(24,24),'#524129')
        tree = image('tree.png',(48,60),'#345735')
        rock = image('rock.png',(96,64),'#8a8e7c')
        bridge = image('bridge.png',(288,144),'#a09a7b')
        self.base = self.root/'base.json'
        self.base.write_text(json.dumps({'version':1,'tiles':{'grass':{'image':grass}},
                                        'props':{'broken_bridge':{'image':rock,'foot_anchor':[48,64]}}}))
        keys = ('oak_a','oak_b','oak_c','conifer_a','conifer_b','fern','shrub','sapling','log','stump')
        self.detail = self.root/'detail.json'
        self.detail.write_text(json.dumps({'version':1,
            'tiles':{key:{'image':leaf if key=='leaf_litter' else grass}
                     for key in ('grass_meadow','grass_lush','grass_dry','leaf_litter')},
            'props':{**{key:{'image':tree,'foot_anchor':[24,60]} for key in keys},
                     'ridge':{'image':rock,'foot_anchor':[48,64]}}}))
        self.wide_record = {'image':bridge,'foot_anchor':[144,94],
                            'deck_top_px':34,'deck_bottom_px':106,'deck_clear_width_px':72}
        self.composition = self.root/'composition.json'
        self.composition.write_text(json.dumps({'version':1,'props':{'broken_bridge_wide':self.wide_record}}))

    def world(self, **changes):
        data = {'version':1,'id':'auratia.overworld','name':'Fixture','kind':'overworld',
                'tile_size':24,'chunk_size':16,'bounds_tiles':[-32,-32,64,64],
                'spawn_tile':[0,0],'terrain':{'rivers':[],'fields':[],'hills':[],'forests':[]},
                'roads':[],'walls':[],'gates':[],'landmarks':[],
                'art_manifest':str(self.base),'detail_art_manifest':str(self.detail),
                'composition_art_manifest':str(self.composition)}
        data.update(changes)
        path = self.root/'region.json';path.write_text(json.dumps(data))
        return OverworldWorld(path,metadata_cache_limit=2,collision_cache_limit=2)

    @staticmethod
    def forest():
        return {'id':'grove','polygon':[[-31,-31],[31,-31],[31,31],[-31,31]],
                'style':'mixed','density':'dense','composition':'groves'}

    def test_bridge_art_extension_selects_the_wide_surface_and_rejects_misalignment(self):
        bridge = {'id':'bridge','tile_position':[-8,8],'repair_flag':'REPAIRED',
                  'damage_rect_tiles':[-14,3,12,8],'deck_rect_tiles':[-14,5.5,12,3],
                  'deck_width_tiles':3,'deck_center_tile_y':7,
                  'broken_art_key':'broken_bridge_wide'}
        world = self.world(bridge=bridge)
        props = list(world._static_props(world.bounds))
        self.assertIn('broken_bridge_wide',{prop['key'] for prop in props})
        self.assertNotIn('broken_bridge',{prop['key'] for prop in props})
        self.assertEqual(world._prop_image('broken_bridge_wide')[1],(144,94))
        with self.assertRaisesRegex(ValueError,'collision deck'):
            self.world(bridge={**bridge,'deck_rect_tiles':[-14,5.5,12,2]})
        altered = {**self.wide_record,'foot_anchor':[144,96]}
        self.composition.write_text(json.dumps({'version':1,'props':{'broken_bridge_wide':altered}}))
        with self.assertRaisesRegex(ValueError,'artwork roadway is not aligned'):
            self.world(bridge=bridge)

    def test_stands_have_overlapping_neighbours_and_stable_foot_ownership(self):
        world = self.world(terrain={'rivers':[],'fields':[],'hills':[],
                                   'forests':[self.forest()]})
        coords = [(-1,-1),(0,-1),(-1,0),(0,0)]
        snapshots = {};stands = defaultdict(list);ids = []
        for coord in coords:
            props = world._chunk_metadata(*coord)['props']
            snapshots[coord] = [(p['id'],p['key'],p['position']) for p in props]
            for prop in props:
                x,y = prop['position']
                self.assertEqual((math.floor(x/384),math.floor(y/384)),coord)
                ids.append(prop['id'])
                if prop.get('crown_ground'):stands[prop['grove_id']].append(prop['position'])
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(any(len(points)>=5 for points in stands.values()))
        self.assertTrue(any(math.dist(a,b)<42 for points in stands.values()
                            for index,a in enumerate(points) for b in points[index+1:]))
        for coord in reversed(coords):
            self.assertEqual([(p['id'],p['key'],p['position'])
                              for p in world._chunk_metadata(*coord)['props']],snapshots[coord])
        self.assertLessEqual(world.cache_stats['metadata_chunks'],2)

    def test_leaf_ground_remains_local_to_crowns_instead_of_covering_the_forest(self):
        world = self.world(terrain={'rivers':[],'fields':[],'hills':[],
                                   'forests':[self.forest()]})
        surface = world._render_chunk(-1,-1)
        leaf = pygame.mask.from_threshold(surface,pygame.Color('#524129'),(1,1,1,255)).count()
        grass = pygame.mask.from_threshold(surface,pygame.Color('#5a7846'),(1,1,1,255)).count()
        self.assertGreater(leaf,100)
        self.assertGreater(grass,leaf)

    def test_crown_and_connected_ridge_ground_match_across_negative_chunk_seam(self):
        world = self.world(terrain={'rivers':[],'fields':[],
            'forests':[self.forest()],
            'hills':[{'id':'ridge','polygon':[[-31,-31],[31,-31],[31,31],[-31,31]],
                      'style':'rocky_ridge','ground_treatment':'localized'}]},
            decorations=[{'id':'shelf','key':'ridge','tile_position':[-1,-6],'solid':[70,12]}])
        player = SimpleNamespace(story_visible=False,position=(0,0))
        whole = pygame.Surface((768,384));left = pygame.Surface((384,384));right = left.copy()
        world.draw(whole,(-384,-384),player,730,False)
        world.draw(left,(-384,-384),player,730,False)
        world.draw(right,(0,-384),player,730,False)
        stitched = whole.copy();stitched.blit(left,(0,0));stitched.blit(right,(384,0))
        self.assertEqual(pygame.image.tobytes(whole,'RGB'),pygame.image.tobytes(stitched,'RGB'))


if __name__ == '__main__':unittest.main()
