"""All attribute symbols remain distinct and bounded in the shared UI."""
import os
from types import SimpleNamespace
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from attribute_icons import ICON_IDS, draw_attribute_icon
from character_attributes import ATTRIBUTE_IDS
from ui_style import INK, IVORY, UIStyle


class AttributeIconTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(audio=SimpleNamespace(text_scale=1.0))
        self.style = UIStyle(self.game)

    def tearDown(self):
        pygame.quit()

    def test_every_attribute_has_a_distinct_nonempty_symbol_at_menu_sizes(self):
        self.assertEqual(ICON_IDS, ATTRIBUTE_IDS)
        for scale in (1, 2, 3):
            for side in (12, 14, 16):
                for color in (INK, IVORY):
                    with self.subTest(scale=scale, side=side, color=color):
                        designs = set()
                        for identifier in ICON_IDS:
                            canvas = pygame.Surface((48*scale, 48*scale), pygame.SRCALPHA)
                            painter = self.style.painter(canvas, (48, 48))
                            logical = pygame.Rect(10, 12, side, side)
                            target = draw_attribute_icon(painter, identifier, logical, color)
                            bounds = canvas.get_bounding_rect()
                            self.assertGreater(bounds.width*bounds.height, 0)
                            self.assertTrue(target.contains(bounds), (identifier, target, bounds))
                            designs.add(pygame.image.tobytes(canvas, 'RGBA'))
                        self.assertEqual(len(designs), len(ATTRIBUTE_IDS))

    def test_icon_respects_existing_clip_and_restores_it(self):
        for identifier in ICON_IDS:
            canvas = pygame.Surface((96, 96), pygame.SRCALPHA)
            painter = self.style.painter(canvas, (48, 48))
            clip = pygame.Rect(26, 24, 9, 24)
            canvas.set_clip(clip)
            draw_attribute_icon(painter, identifier, (10, 12, 16, 16), IVORY)
            self.assertEqual(canvas.get_clip(), clip)
            bounds = canvas.get_bounding_rect()
            if bounds.width and bounds.height:self.assertTrue(clip.contains(bounds))

    def test_icon_uses_foreground_color_and_does_not_erase_background(self):
        canvas = pygame.Surface((48, 48), pygame.SRCALPHA)
        canvas.fill((31, 49, 27, 255))
        painter = self.style.painter(canvas, (48, 48))
        draw_attribute_icon(painter, 'spr', (10, 12, 16, 16), IVORY)
        colors = {canvas.get_at((x, y))[:3] for x in range(48) for y in range(48)}
        self.assertEqual(colors, {(31, 49, 27), pygame.Color(IVORY)[:3]})

    def test_nonsquare_rect_centers_symbol_and_invalid_arguments_are_explicit(self):
        canvas = pygame.Surface((96, 96), pygame.SRCALPHA)
        painter = self.style.painter(canvas, (48, 48))
        target = draw_attribute_icon(painter, 'hp', (4, 8, 30, 14), INK)
        self.assertEqual(target, painter.area((12, 8, 14, 14)))
        with self.assertRaises(ValueError):draw_attribute_icon(painter, 'unknown', (0, 0, 12, 12), INK)
        with self.assertRaises(ValueError):draw_attribute_icon(painter, 'hp', (0, 0, 0, 12), INK)


if __name__ == '__main__':
    unittest.main()
