"""Expression readability, eye-light timing, and seamless scene registration."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from pathlib import Path
import unittest

import pygame

from rhea_awakening_closeup import RheaAwakeningCloseup


ROOT = Path(__file__).resolve().parents[1]


class RheaAwakeningCloseupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480,320))
        cls.closeup = RheaAwakeningCloseup(ROOT/'assets/story/ice_reaper_rhea_closeup')

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def render(self, time, reduced=False):
        surface = pygame.Surface((480,320))
        surface.fill((24,37,58))
        self.closeup.draw(surface,time,reduced=reduced,
                          target_eyes=((219,135),(231,135)))
        return pygame.image.tobytes(surface,'RGB')

    def test_extra_second_keeps_eyes_closed_while_strain_builds(self):
        samples = ((15.2,'neutral_closed'), (15.7,'strain_begin'),
                   (16.0,'strain_mid'), (16.3,'strain_peak'))
        for time, expression in samples:
            with self.subTest(time=time):
                state = self.closeup.state(time)
                self.assertEqual(state['expression'],expression)
                self.assertTrue(state['eyes_closed'])
                self.assertEqual(state['eye_glow'],0)
                self.assertEqual(state['gleam_strength'],0)
        self.assertAlmostEqual(self.closeup.OPEN-self.closeup.START,1.3)

    def test_new_drawings_progress_from_strain_to_angry_open_eyes(self):
        self.assertEqual(self.closeup.state(16.45)['expression'],'opening_01')
        self.assertEqual(self.closeup.state(16.6)['expression'],'opening_02')
        self.assertEqual(self.closeup.state(16.8)['expression'],'angry_open')
        self.assertEqual(self.closeup.state(16.94)['expression'],'angry_hold')
        self.assertFalse(self.closeup.state(16.45)['eyes_closed'])
        drawings = [pygame.image.tobytes(frame,'RGBA')
                    for frame in self.closeup.frames.values()]
        self.assertEqual(len(set(drawings)),8,'Every expression must be authored distinctly')

    def test_gleam_peaks_during_opening_then_leaves_a_sustained_glow(self):
        peak = self.closeup.state(16.62)
        self.assertGreater(peak['gleam_strength'],.95)
        self.assertGreater(peak['eye_glow'],.5)
        self.assertEqual(self.closeup.state(16.3)['gleam_strength'],0)
        self.assertEqual(self.closeup.state(16.95)['gleam_strength'],0)
        self.assertEqual(self.closeup.state(17.25)['eye_glow'],1)

    def test_close_crop_contains_extended_body_below_the_viewport(self):
        for time in (15.1,15.8,16.8):
            geometry = self.closeup.geometry((480,320),time)
            self.assertGreater(geometry['bottom'].y,480)
            for eye in geometry['eyes']:
                self.assertTrue(190 < eye.x < 290)
                self.assertTrue(90 < eye.y < 160)

    def test_final_reframe_matches_world_eye_registration(self):
        targets = ((219,135),(231,135))
        geometry = self.closeup.geometry((480,320),17.3,target_eyes=targets)
        for actual, target in zip(geometry['eyes'],targets):
            self.assertLess(actual.distance_to(target),.001)
        self.assertEqual(geometry['pullback'],1)
        self.assertEqual(self.closeup.state(17.3)['overlay_alpha'],0)
        self.assertFalse(self.closeup.state(17.3)['active'])

    def test_hold_does_not_start_fading_before_the_angry_expression_reads(self):
        self.assertEqual(self.closeup.state(16.94)['overlay_alpha'],1)
        values = [self.closeup.state(t)['overlay_alpha']
                  for t in (17.04,17.1,17.2,17.3)]
        self.assertEqual(values[0],1)
        self.assertEqual(values[-1],0)
        self.assertTrue(all(a > b for a,b in zip(values,values[1:])))

    def test_revisiting_frame_and_reduced_motion_are_deterministic(self):
        for reduced in (False,True):
            before = self.render(16.62,reduced)
            self.render(17.2,reduced)
            self.render(15.2,reduced)
            self.assertEqual(before,self.render(16.62,reduced))
        self.assertNotEqual(self.render(16.62,False),self.render(16.62,True))

    def test_draw_does_not_read_assets_and_outside_insert_is_untouched(self):
        from unittest.mock import patch
        with patch('pygame.image.load',side_effect=AssertionError('draw loaded an asset')):
            self.render(16.7)
        base = pygame.Surface((480,320))
        base.fill((20,30,40))
        expected = pygame.image.tobytes(base,'RGB')
        for time in (15.0,17.3,20.0):
            self.closeup.draw(base,time)
            self.assertEqual(pygame.image.tobytes(base,'RGB'),expected)


if __name__ == '__main__':
    unittest.main()
