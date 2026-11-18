"""Mechanical flight/impact geometry is seekable and stays on model boundaries."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from bolt_shot_fx import BoltShotEffects, GLINT_SECONDS, SPARK_SECONDS, FLECK_SECONDS, DUST_SECONDS
from mira_combat_art import MiraCombatArt


class BoltShotEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):pygame.init();pygame.display.set_mode((480, 320))
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def setUp(self):self.fx = BoltShotEffects();self.art = MiraCombatArt()
    def shot(self, age, resolved=False):
        return self.art.shot(age, .4, (404, 180), (126, 138), resolved=resolved)
    def render(self, age, reduced=False):
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        self.fx.draw_flight(canvas, self.shot(age), reduced_motion=reduced)
        return canvas

    def test_leading_tip_is_muzzle_at_release_and_shoulder_at_contact_boundary(self):
        self.assertIsNone(self.fx.flight(self.shot(.279999)))
        sample = self.fx.flight(self.shot(.28))
        self.assertEqual(sample['tip'], self.shot(.28)['origin'])
        self.assertEqual(sample['smear_length'], 0)
        self.assertEqual(sample['fragments'], [])
        arrival = self.fx.flight(self.shot(.4-1e-9))
        self.assertAlmostEqual(arrival['tip'][0], 126., places=4)
        self.assertAlmostEqual(arrival['tip'][1], 138., places=4)
        self.assertIsNone(self.fx.flight(self.shot(.4)))
        self.assertIsNone(self.fx.flight(self.shot(.35, True)))
        self.assertFalse(self.render(.4).get_bounding_rect())

    def test_solid_contour_and_short_sharp_smear_move_without_a_full_path_beam(self):
        first, next_frame = self.fx.flight(self.shot(.32)), self.fx.flight(self.shot(.34))
        self.assertNotEqual(first['tip'], next_frame['tip'])
        self.assertLessEqual(first['smear_length'], 16)
        self.assertGreater(len(first['fragments']), 0)
        self.assertNotEqual(first['fragments'], next_frame['fragments'])
        self.assertLess(self.render(.34).get_bounding_rect().width, 65)
        alpha = pygame.surfarray.array_alpha(self.render(.34))
        self.assertGreater((alpha == 255).sum(), 15)

    def test_reduced_motion_retains_pointed_physical_bolt_without_smear_or_fragments(self):
        normal = self.fx.flight(self.shot(.34))
        quiet = self.fx.flight(self.shot(.34), reduced_motion=True)
        self.assertEqual(normal['tip'], quiet['tip'])
        self.assertEqual(quiet['smear_length'], 0)
        self.assertEqual(quiet['fragments'], [])
        self.assertTrue(self.render(.34, True).get_bounding_rect())
        self.assertLess(self.render(.34, True).get_bounding_rect().width,
                        self.render(.34).get_bounding_rect().width)

    def test_contact_components_decay_on_different_event_owned_clocks(self):
        point = (126, 138)
        sample = self.fx.impact(point, 0)
        self.assertEqual(sample['glint'], 1)
        self.assertTrue(sample['sparks']);self.assertTrue(sample['flecks'])
        self.assertFalse(self.fx.impact(point, -.001)['glint'])
        self.assertFalse(self.fx.impact(point, GLINT_SECONDS)['glint'])
        self.assertTrue(self.fx.impact(point, .08)['sparks'])
        self.assertFalse(self.fx.impact(point, SPARK_SECONDS)['sparks'])
        self.assertTrue(self.fx.impact(point, .2)['flecks'])
        self.assertFalse(self.fx.impact(point, FLECK_SECONDS)['flecks'])
        self.assertTrue(self.fx.impact(point, .3)['dust'])
        self.assertFalse(self.fx.impact(point, DUST_SECONDS)['dust'])
        self.assertLess(self.fx.impact(point, .05)['flecks'][0]['point'][1], point[1])
        self.assertGreater(self.fx.impact(point, .27)['flecks'][0]['point'][1], point[1])
        quiet = self.fx.impact(point, .02, reduced_motion=True)
        self.assertTrue(quiet['glint']);self.assertEqual(len(quiet['sparks']), 2)
        self.assertFalse(quiet['flecks']);self.assertFalse(quiet['dust'])

    def test_seek_repeat_local_bounds_and_no_asset_reads_or_accumulation(self):
        def pixels():return pygame.image.tobytes(self.render(.34), 'RGBA')
        expected = pixels();layer = self.fx._layer
        with patch('pygame.image.load', side_effect=AssertionError('render-time I/O')):
            for age in (.8, .3, .4, .28):self.render(age)
            self.assertEqual(pixels(), expected)
        self.assertIs(self.fx._layer, layer)
        for age in (0., .02, .08, .2, .4, .48):
            canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
            self.fx.draw_impact(canvas, (126, 138), age)
            bounds = canvas.get_bounding_rect()
            if bounds:self.assertTrue(pygame.Rect(100, 115, 52, 46).contains(bounds))
        for bad in (True, float('inf'), float('nan')):
            with self.assertRaises(ValueError):self.fx.impact((126, 138), bad)


if __name__ == '__main__':unittest.main()
