"""The authored seal constructs its strokes without changing its ground geometry."""
import math
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import numpy as np
import pygame

from ice_reaper_action import IceReaperActionStage, PerspectiveCamera
from ice_reaper_rune import RuneSeal

ROOT=Path(__file__).resolve().parents[1]

class RuneConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.rune=RuneSeal(ROOT/'assets/story/ice_reaper_rune/rune.png')
    @classmethod
    def tearDownClass(cls): pygame.quit()

    def test_entire_reveal_keeps_the_same_final_world_footprint(self):
        for time in (16.3,16.45,16.9,17.2,17.6,19.8):
            state=self.rune.state(time)
            self.assertEqual(state['world_radius'],8.2)
            self.assertEqual(state['center'],[-3.,.035,0.])
            self.assertEqual(state['geometry_scale'],1.)

    def test_partial_strokes_stay_registered_to_the_authored_full_drawing(self):
        # A small copy of the whole drawing would put many pixels between the
        # final authored strokes. Every partial pixel must be on its final line.
        for time in (16.45,16.7,16.95,17.2,17.45):
            partial=self.rune.reveal_mask(time)
            self.assertTrue(partial.any())
            self.assertFalse((partial & ~self.rune.stroke).any())
            self.assertLess(partial.sum(),self.rune.stroke.sum())

    def test_construction_is_monotonic_and_finishes_before_shoulder_pan(self):
        previous=np.zeros_like(self.rune.stroke)
        for time in np.linspace(16.3,17.6,45):
            current=self.rune.reveal_mask(float(time))
            self.assertFalse((previous & ~current).any())
            previous=current
        np.testing.assert_array_equal(previous,self.rune.stroke)
        self.assertEqual(self.rune.state(17.6)['stage'],'complete')
        self.assertEqual(self.rune.state(17.6)['coverage'],1.)

    def test_branches_reach_the_rings_before_the_circumference_closes(self):
        branches=self.rune.stroke & (self.rune.radius>.6)&(self.rune.radius<.78)
        ring=self.rune.stroke & (self.rune.radius>.96)&(self.rune.radius<1.01)
        self.assertTrue(branches.any() and ring.any())
        self.assertLess(float(np.median(self.rune.arrival[branches])),float(np.max(self.rune.arrival[ring])))
        self.assertGreater(float(np.max(self.rune.arrival[ring])),1.)

    def test_inner_and_outer_rings_trace_in_opposing_directions(self):
        def arrival(radius,angle):
            delta=np.abs((self.rune.angle-angle+math.pi)%math.tau-math.pi)
            pixels=self.rune.stroke&(abs(self.rune.radius-radius)<.018)&(delta<.035)
            self.assertTrue(pixels.any())
            return float(np.median(self.rune.arrival[pixels]))
        self.assertLess(arrival(.825,0),arrival(.825,math.pi))
        self.assertLess(arrival(.945,math.pi),arrival(.945,0))

    def test_ink_texture_reveals_add_strokes_without_scaling_or_erasing(self):
        previous=np.zeros_like(self.rune.alpha)
        for textures in self.rune.textures:
            alpha=textures[0][:,:,3]
            self.assertTrue(np.all(alpha>=previous))
            previous=alpha
        self.assertGreater(int(np.count_nonzero(previous)),self.rune.stroke_count)

    def test_paused_or_revisited_time_produces_identical_pixels(self):
        camera=PerspectiveCamera((1.,11.,12.),(-3.,.035,0),260)
        canvas=pygame.Surface((480,320))
        def frame(time,reduced=False):
            canvas.fill('#a8c5dd');self.rune.draw(canvas,camera,time,reduced)
            return pygame.image.tobytes(canvas,'RGB')
        for time in (16.8,17.15,18.3,19.8):
            before=frame(time);frame(17.55)
            self.assertEqual(before,frame(time))
        self.assertEqual(frame(18.1,True),frame(19.8,True))

    def test_completion_pulse_brightens_without_integer_wrap_or_dark_flash(self):
        camera=PerspectiveCamera((-3.,18.,15.),(-3.,.035,0),250)
        levels=[]
        for time in (17.6,17.72):
            canvas=pygame.Surface((480,320));canvas.fill('black')
            self.rune.draw(canvas,camera,time)
            levels.append(float(pygame.surfarray.array3d(canvas)[:,:,0].sum()))
        self.assertGreater(levels[0],0)
        self.assertGreaterEqual(levels[1],levels[0]*.95)

    def test_cached_projection_is_independent_of_reveal_time(self):
        camera=PerspectiveCamera((1.,11.,12.),(-3.,.035,0),260)
        canvas=pygame.Surface((480,320))
        before=self.rune._projection(canvas,camera)
        self.rune.draw(canvas,camera,16.7)
        self.rune.draw(canvas,camera,19.)
        after=self.rune._projection(canvas,camera)
        self.assertIs(before,after)
        self.assertEqual(before[-1],after[-1])

if __name__=='__main__':unittest.main()
