"""Target glove/ring geometry and native pixel rendering without font glyphs."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import unittest

import pygame

from battle_target_marker import (
    FINGER_GAP, FINGER_SIZE, FINGER_TIP, RING_RED,
    draw_target_finger, draw_target_ring, target_finger_image,
    target_marker_geometry,
)


class BattleTargetMarkerTests(unittest.TestCase):
    def test_glove_has_a_long_downward_finger_and_visible_cuff(self):
        image = target_finger_image()
        self.assertEqual(image.get_size(), FINGER_SIZE)
        bounds = image.get_bounding_rect()
        self.assertEqual(bounds.bottom, FINGER_SIZE[1])
        self.assertEqual(image.get_at(FINGER_TIP).a, 255)
        # The folded hand is wide, while its downward-pointing index narrows.
        palm = sum(image.get_at((x, 8)).a > 0 for x in range(image.get_width()))
        fingertip = sum(image.get_at((x, 18)).a > 0 for x in range(image.get_width()))
        self.assertGreater(palm, fingertip * 2)
        self.assertEqual(image.get_at((5, 1)), pygame.Color('#314f40'))

    def test_fingertip_aligns_with_body_center_above_sprite(self):
        body = pygame.Rect(74, 92, 48, 50)
        geometry = target_marker_geometry(body, (90, 148))
        finger = geometry['finger']
        self.assertEqual(finger.left + FINGER_TIP[0], body.centerx)
        self.assertEqual(finger.bottom, body.top - FINGER_GAP)
        self.assertEqual(geometry['ring'].center, (body.centerx, 148))

    def test_ring_scales_with_enemy_footprint_and_stays_bounded(self):
        small = target_marker_geometry((30, 80, 8, 10), (34, 93))['ring']
        big = target_marker_geometry((20, 70, 220, 120), (130, 192))['ring']
        self.assertEqual(small.width, 26)
        self.assertEqual(big.width, 108)
        self.assertLess(small.height, small.width)
        self.assertLess(big.height, big.width)
        self.assertGreater(big.width, small.width)

    def test_markers_fit_single_and_four_enemy_fields(self):
        for field, body in (
            ((5, 66, 470, 135), (20, 91, 220, 100)),
            ((13, 80, 111, 60), (28, 102, 70, 33)),
            ((13, 80, 52, 58), (24, 102, 28, 31)),
            ((10, 80, 25, 15), (20, 82, 8, 10)),
        ):
            with self.subTest(field=field, body=body):
                area = pygame.Rect(field)
                markers = target_marker_geometry(body, (30, 300), bounds=area)
                self.assertTrue(area.contains(markers['finger']))
                self.assertTrue(area.contains(markers['ring']))

    def test_ring_is_red_and_draws_beneath_sprite_without_filling_body(self):
        canvas = pygame.Surface((180, 150), pygame.SRCALPHA)
        body = pygame.Rect(53, 70, 60, 55)
        rect = draw_target_ring(canvas, body, (83, 128))
        red = pygame.Color(RING_RED)
        pixels = sum(canvas.get_at((x, y)) == red
                     for x in range(rect.left, rect.right)
                     for y in range(rect.top, rect.bottom))
        self.assertGreater(pixels, 20)
        self.assertEqual(canvas.get_at(body.center).a, 0)
        self.assertEqual(canvas.get_at(rect.center).a, 0)
        # Normal actor drawing can occlude the ring's back half.
        pygame.draw.rect(canvas, '#123456', body)
        self.assertEqual(canvas.get_at((body.centerx, body.bottom - 1)),
                         pygame.Color('#123456'))

    def test_static_render_is_identical_on_repeated_draws(self):
        first = pygame.Surface((160, 160), pygame.SRCALPHA)
        second = pygame.Surface((160, 160), pygame.SRCALPHA)
        for canvas in (first, second):
            draw_target_ring(canvas, (54, 70, 50, 60), (79, 136), bounds=canvas.get_rect())
            rect = draw_target_finger(canvas, (54, 70, 50, 60), bounds=canvas.get_rect())
            self.assertEqual(rect.size, FINGER_SIZE)
        self.assertEqual(pygame.image.tobytes(first, 'RGBA'),
                         pygame.image.tobytes(second, 'RGBA'))

    def test_invalid_body_or_field_cannot_make_negative_marker_rectangles(self):
        for body, bounds in (((0, 0, 0, 5), None), ((1, 2, 3, 4), (0, 0, 5, 0))):
            with self.assertRaises(ValueError):
                target_marker_geometry(body, (2, 4), bounds=bounds)


if __name__ == '__main__':
    unittest.main()
