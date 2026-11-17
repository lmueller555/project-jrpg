"""Native regional material seams, geometry masks and repaired water exclusion."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import unittest
from pathlib import Path
import pygame
from rendering import layer, draw
from regional_terrain_hd import RegionalTerrainHD, canonical_mask, tile_phase

ROOT=Path(__file__).resolve().parents[1]

class FixtureWorld:
    def __init__(self):
        self.region={'terrain_hd':{'enabled':True},'terrain':{'rivers':[]}}
        self.repaired=False
    def _tile_image(self,key):
        return pygame.image.load(str(ROOT/'assets/terrain/overworld/elden_vale/hd/tiles'/f'{key}.png')).convert_alpha()
    @staticmethod
    def _draw_path(target,color,points,width):
        from overworld_world import OverworldWorld
        OverworldWorld._draw_path(target,color,points,width)
    @staticmethod
    def _tile_rect(rect):return pygame.Rect(*(round(v*24) for v in rect))
    @staticmethod
    def _feature_intersects(points,rect,padding=0):
        xs,ys=zip(*points)
        return rect.colliderect(pygame.Rect(min(xs)*24-padding,min(ys)*24-padding,
                               (max(xs)-min(xs))*24+padding*2+1,
                               (max(ys)-min(ys))*24+padding*2+1))
    def _bridge_repaired(self):return self.repaired

class RegionalTerrainHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((1,1))
    @classmethod
    def tearDownClass(cls):pygame.display.quit()
    def setUp(self):
        self.world=FixtureWorld();self.art=RegionalTerrainHD(self.world)

    def test_paving_phases_join_across_signed_origins(self):
        whole=layer((96,48));self.art.pattern(whole,'stone_road',(-48,-24))
        joined=layer((96,48))
        for offset in (0,48):
            piece=layer((48,48));self.art.pattern(piece,'stone_road',(-48+offset,-24))
            joined.blit(piece,(offset,0))
        self.assertEqual(pygame.image.tobytes(whole.native,'RGBA'),pygame.image.tobytes(joined.native,'RGBA'))
        self.assertEqual(tile_phase(-1,-1),3)
        self.assertEqual(tile_phase(0,-1),2)
        source=pygame.image.load(str(ROOT/'assets/terrain/eldenmere/stone_paving_hd/surface/phase_2.png')).convert_alpha()
        self.assertEqual(pygame.image.tobytes(whole.native.subsurface((96,0,48,48)),'RGBA'),pygame.image.tobytes(source,'RGBA'))

    def test_native_material_mask_retains_source_detail(self):
        target=layer((48,48))
        self.art.paint(target,'stone_road',lambda mask:draw.circle(mask,'white',(24,24),15),(0,0))
        self.assertEqual(target.native.get_at((0,0)).a,0)
        self.assertEqual(target.native.get_at((48,48)).a,255)
        enlarged=pygame.transform.scale(target,(96,96))
        self.assertNotEqual(pygame.image.tobytes(target.native,'RGBA'),pygame.image.tobytes(enlarged,'RGBA'))
        self.assertEqual(canonical_mask(2),0)
        self.assertEqual(canonical_mask(7),7)

    def test_water_camera_partition_and_reduced_motion(self):
        self.world.region['terrain']['rivers']=[{'points':[[-20,0],[20,0]],'width':4}]
        whole=layer((96,48));self.art.draw_water(whole,(-48,-24),400)
        joined=layer((96,48))
        for offset in (0,48):
            piece=layer((48,48));self.art.draw_water(piece,(-48+offset,-24),400)
            joined.blit(piece,(offset,0))
        self.assertEqual(pygame.image.tobytes(whole.native,'RGBA'),pygame.image.tobytes(joined.native,'RGBA'))
        first=layer((96,48));last=layer((96,48))
        self.art.draw_water(first,(-48,-24),0,True)
        self.art.draw_water(last,(-48,-24),9999,True)
        self.assertEqual(pygame.image.tobytes(first.native,'RGBA'),pygame.image.tobytes(last.native,'RGBA'))
        self.assertNotEqual(pygame.image.tobytes(first.native,'RGBA'),pygame.image.tobytes(whole.native,'RGBA'))

    def test_repaired_deck_is_never_overpainted_by_water(self):
        self.world.region['terrain']['rivers']=[{'points':[[0,-20],[0,20]],'width':4}]
        self.world.region['bridge']={'damage_rect_tiles':[-1,-.5,2,1],'deck_rect_tiles':[-1,-.5,2,1]}
        self.world.repaired=True
        target=layer((96,96));target.fill('#d86040')
        self.art.draw_water(target,(-48,-48),200)
        self.assertEqual(target.native.get_at((96,96))[:3],(216,96,64))
        self.assertNotEqual(target.native.get_at((96,32))[:3],(216,96,64))
        self.assertLessEqual(self.art._mask_cache.bytes,self.art._mask_cache.budget)

    def test_banks_stitch_between_chunks(self):
        river={'points':[[9,-5],[13,7],[20,18]],'width':4}
        self.world.region['terrain']['rivers']=[river]
        whole=layer((768,384));self.art.pattern(whole,'grass_meadow',(0,0))
        self.art.bank(whole,river,0,0)
        joined=layer((768,384))
        for cx in (0,1):
            piece=layer((384,384));self.art.pattern(piece,'grass_meadow',(cx*384,0))
            self.art.bank(piece,river,cx,0);joined.blit(piece,(cx*384,0))
        self.assertEqual(pygame.image.tobytes(whole.native,'RGBA'),pygame.image.tobytes(joined.native,'RGBA'))

    def test_oversized_mask_pair_remains_correct_without_caching(self):
        self.world.region['terrain']['rivers']=[{'points':[[-20,0],[20,0]],'width':4}]
        expected=layer((96,48));self.art.draw_water(expected,(-48,-24),400)
        self.art._mask_cache.clear();self.art._mask_cache.budget=1
        actual=layer((96,48));self.art.draw_water(actual,(-48,-24),400)
        self.assertEqual(pygame.image.tobytes(expected.native,'RGBA'),pygame.image.tobytes(actual.native,'RGBA'))
        self.assertLessEqual(self.art._mask_cache.bytes,1)

    def test_contact_shade_does_not_outline_chunk_crops(self):
        whole=layer((96,48));self.art.pattern(whole,'grass_meadow',(0,0))
        self.art.paint(whole,'stone_road',lambda mask:draw.rect(mask,'white',(0,12,96,24)),(0,0))
        joined=layer((96,48))
        for offset in (0,48):
            piece=layer((48,48));self.art.pattern(piece,'grass_meadow',(offset,0))
            self.art.paint(piece,'stone_road',lambda mask,offset=offset:draw.rect(mask,'white',(-offset,12,96,24)),(offset,0))
            joined.blit(piece,(offset,0))
        self.assertEqual(pygame.image.tobytes(whole.native,'RGBA'),pygame.image.tobytes(joined.native,'RGBA'))
