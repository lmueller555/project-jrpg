"""Camera-driven landscape continuity, independent of timeline shot labels."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import unittest
from pathlib import Path
import numpy as np
import pygame
from ice_reaper_action import IceReaperActionStage
ROOT=Path(__file__).resolve().parents[1]

class EnvironmentContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.stage=IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue')
    @classmethod
    def tearDownClass(cls): pygame.quit()
    def test_identical_camera_sees_same_landscape_across_all_shots(self):
        camera=self.stage.camera(10.7)
        samples=[]
        for time in (5.5,9.99,11.,13.4,16.7,19.2):
            frame=pygame.Surface((480,320))
            self.stage._background(frame,camera,time)
            samples.append(pygame.image.tobytes(frame,'RGB'))
        self.assertEqual(len(set(samples)),1)
    def test_panorama_wrap_has_no_pixel_seam(self):
        self.assertIsNotNone(self.stage.panorama)
        np.testing.assert_array_equal(self.stage.panorama[0],self.stage.panorama[-1])
    def test_city_has_one_fixed_world_location(self):
        cities=[item for item in self.stage.world_landmarks() if item[0]=='castle']
        self.assertEqual(len(cities),1)
        self.assertEqual(cities[0][1],(-14.,0.,-70.))
    def test_background_is_continuous_at_end_of_rescue_orbit(self):
        frames=[]
        for time in (11.-1e-7,11.):
            frame=pygame.Surface((480,320))
            self.stage._background(frame,self.stage.camera(time),time)
            frames.append(pygame.surfarray.array3d(frame).astype(float))
        self.assertLess(np.abs(frames[0]-frames[1]).mean(),.15)
