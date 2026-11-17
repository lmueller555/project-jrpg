"""The live shared fire stays rooted at every phase, loop seam and draw depth."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
from types import SimpleNamespace
import json
import unittest
import pygame
from rendering import WorldCanvas

ROOT=Path(__file__).resolve().parents[1]
BANK='assets/terrain/eldenmere/sanctuary_dining_hd/props/'
ROOMS=('liam_house','halden','elira','venn','home_a','home_b','home_c','mira','mill','school','sanctuary_dining')


class HearthRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from main import World
        pygame.init();pygame.display.set_mode((1,1))
        cls.world=World(ROOT/'assets/maps/eldenmere/building_interiors/rooms/liam_house/map.json')
        cls.record=next(e for e in cls.world.entities if e['id']=='hearth')
        sprite=pygame.Surface((24,36),pygame.SRCALPHA);sprite.fill('magenta')
        cls.actor=SimpleNamespace(position=pygame.Vector2(350,100),draw_anchor=[12,30],
                                  story_visible=False,sprite=lambda:sprite)
        cls.view=WorldCanvas((480,320))

    @classmethod
    def tearDownClass(cls):
        cls.world=None;cls.record=None;cls.view=None;cls.actor=None
        pygame.quit()

    def setUp(self):
        self.world.reduced_motion=False;self.actor.story_visible=False

    def draw(self,elapsed):
        self.world.draw(self.view,(0,0),self.actor,elapsed,False)
        return self.view.native

    def test_all_live_consumers_keep_the_same_clock_registration_and_depth(self):
        expected=[BANK+f'hearth_frame_{i:02}.png' for i in range(1,5)]
        found=[]
        for name in ROOMS:
            data=json.loads((ROOT/f'assets/maps/eldenmere/building_interiors/rooms/{name}/map.json').read_text())
            hearth=next(e for e in data['entities'] if e['id']=='hearth')
            self.assertEqual(hearth['frames'],expected,name)
            self.assertEqual((hearth['frame_duration_ms'],hearth['phase_offset'],hearth['reduced_motion_frame']),(300,0,0),name)
            self.assertEqual((hearth['position'][1],hearth['sort_y'],hearth['sort_priority']),(24,92,0),name)
            self.assertEqual(hearth['artwork_pixels_per_world_pixel'],2,name)
            for light in data['entities']:
                if 'light' in light['id']:
                    self.assertLess(light['sort_y'],hearth['sort_y'])
            found.append(name)
        self.assertEqual(len(found),11)

    def test_runtime_phase_boundaries_and_three_repeated_loops(self):
        # Compare the opaque local aperture through the actual World compositor.
        x,y=self.record['position'];rect=pygame.Rect(x*2+29,y*2+90,40,37)
        for elapsed in (0,299.9,300,599.9,600,900,1199.9,1200,1500,1800,2100,2399.9,
                        2400,2700,3000,3300,3599.9,3600,1000000):
            phase=int(elapsed//300)%4
            expected=pygame.image.load(str(ROOT/self.record['frames'][phase])).subsurface((29,90,40,37))
            actual=self.draw(elapsed).subsurface(rect)
            for row in range(rect.height):
                for column in range(rect.width):
                    pixel=expected.get_at((column,row))
                    if pixel.a==255:
                        self.assertEqual(actual.get_at((column,row)),pixel,(elapsed,column,row))

    def test_reduced_motion_freezes_the_complete_hearth_not_just_the_flame(self):
        self.world.update_grass(0,reduced_motion=True)
        x,y=self.record['position'];rect=pygame.Rect(x*2+29,y*2+90,40,37)
        still=pygame.image.tobytes(self.draw(0).subsurface(rect),'RGB')
        for elapsed in (300,600,900,1200,999999):
            self.assertEqual(pygame.image.tobytes(self.draw(elapsed).subsurface(rect),'RGB'),still)
        self.world.update_grass(0,reduced_motion=False)
        self.assertNotEqual(pygame.image.tobytes(self.draw(600).subsurface(rect),'RGB'),still)

    def test_fire_is_occluded_with_its_hearth_at_the_existing_actor_depth(self):
        self.actor.story_visible=True
        for elapsed in (0,300,600,900,1200):
            self.actor.position.update(350,80)  # actor baseline 86, behind hearth 92
            behind=self.draw(elapsed).get_at((700,156))
            self.assertNotEqual(behind,pygame.Color('magenta'))
            self.actor.position.update(350,92)  # actor baseline 98, in front
            self.assertEqual(self.draw(elapsed).get_at((700,156)),pygame.Color('magenta'))
