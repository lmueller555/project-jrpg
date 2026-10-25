"""Display-resolution text, bundled glyph coverage and logical UI geometry."""
import hashlib
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from ui_style import UIStyle, FOREST, IVORY, BRASS, draw_ambient_speech


class UIStyleTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.game = SimpleNamespace(audio=SimpleNamespace(text_scale=1.0, effects_volume=0))
        self.style = UIStyle(self.game)

    def tearDown(self):pygame.quit()

    def test_text_is_rasterized_at_output_resolution_with_antialiased_edges(self):
        canvas = pygame.Surface((1440, 960))
        canvas.fill(FOREST)
        painter = self.style.painter(canvas)
        actual = painter.font().actual
        self.assertEqual(painter.scale, 3)
        expected = actual.render('Illuminating Eldenmere', True, IVORY)
        result = painter.text('Illuminating Eldenmere', (12, 14))
        reference = pygame.Surface(expected.get_size())
        reference.fill(FOREST)
        reference.blit(expected, (0, 0))
        rendered = canvas.subsurface((36, 42, *expected.get_size()))
        self.assertEqual(pygame.image.tobytes(rendered, 'RGB'),
                         pygame.image.tobytes(reference, 'RGB'))
        self.assertGreater(actual.get_height(), 27)
        self.assertGreater(result.width, 0)
        colors = {rendered.get_at((x, y))[:3]
                  for y in range(rendered.get_height()) for x in range(rendered.get_width())}
        self.assertGreater(len(colors), 15)

    def test_difficult_letters_and_punctuation_have_distinct_glyphs(self):
        font = self.style.painter(pygame.Surface((1440, 960))).font().actual
        hashes = []
        for letter in 'Il1O0':
            image = font.render(letter, True, IVORY)
            hashes.append(hashlib.sha256(pygame.image.tobytes(image, 'RGBA')).hexdigest())
        self.assertEqual(len(set(hashes)), 5)
        for symbol in '“”‘’…—é':
            self.assertIsNotNone(font.coverage.get_metrics(symbol)[0])

    def test_missing_atkinson_symbols_use_real_bundled_fallback_glyphs(self):
        font = self.style.painter(pygame.Surface((1440, 960))).font().actual
        self.assertIsNone(font.coverage.get_metrics('→')[0])
        forward = font.render('→', True, IVORY)
        backward = font.render('←', True, IVORY)
        self.assertNotEqual(pygame.image.tobytes(forward, 'RGBA'),
                            pygame.image.tobytes(backward, 'RGBA'))
        mixed = font.render('Continue →', True, IVORY)
        self.assertEqual(mixed.get_size(), font.size('Continue →'))
        self.assertTrue(mixed.get_bounding_rect().height)

    def test_text_scale_reflows_wrapping_without_clipping_long_words(self):
        canvas = pygame.Surface((960, 640))
        painter = self.style.painter(canvas)
        text = 'Serene asked Caelan to visit the households before the festival.'
        normal = painter.wrap(text, 130)
        self.game.audio.text_scale = 1.5
        large = painter.wrap(text, 130)
        self.assertGreater(len(large), len(normal))
        for line in large:
            self.assertLessEqual(painter.font().size(line)[0], 130)
        for line in painter.wrap('m'*100, 70):
            self.assertLessEqual(painter.font().size(line)[0], 70)
        self.assertEqual(''.join(painter.wrap('m'*100, 70)), 'm'*100)

    def test_logical_coordinates_survive_letterboxing_and_clipping(self):
        canvas = pygame.Surface((1200, 800))
        painter = self.style.painter(canvas, (640, 360))
        self.assertEqual(painter.bounds.size, (640, 360))
        self.assertEqual(painter.point((0, 0)), (0, 62))
        painter.clip((10, 20, 100, 50))
        self.assertEqual(canvas.get_clip(), painter.area((10, 20, 100, 50)))
        painter.clip(None)
        self.assertEqual(canvas.get_clip(), canvas.get_rect())

    def test_panel_and_portrait_drawing_do_not_modify_source_art(self):
        canvas = pygame.Surface((960, 640))
        painter = self.style.painter(canvas)
        source = pygame.Surface((24, 36), pygame.SRCALPHA)
        source.fill('#ad5f3b')
        original = pygame.image.tobytes(source, 'RGBA')
        painter.panel((10, 10, 180, 100))
        painter.image(source, (20, 20, 48, 72))
        self.assertEqual(pygame.image.tobytes(source, 'RGBA'), original)
        self.assertEqual(canvas.get_at((20, 20))[:3], pygame.Color(BRASS)[:3])
        self.assertEqual(canvas.get_at((42, 42))[:3], (173, 95, 59))

    def test_menu_sounds_respect_effects_mute_and_missing_device(self):
        with patch('pygame.mixer.init') as initialize:
            self.style.sound('confirm')
            initialize.assert_not_called()
        self.game.audio.effects_volume = .5
        with patch('pygame.mixer.get_init', return_value=None), \
                patch('pygame.mixer.init', side_effect=pygame.error('device missing')):
            self.style.sound('confirm')

    def _ambient_actor(self, position):
        image = pygame.Surface((24, 36), pygame.SRCALPHA)
        image.fill('#a25d38')
        return SimpleNamespace(position=pygame.Vector2(position), draw_anchor=(12, 30),
                               sprite=lambda elapsed: image)

    def test_ambient_speech_preserves_native_world_crop_coordinates(self):
        target = pygame.Surface((720, 480))
        self.game.ui = self.style
        self.game.ui_surface = pygame.Surface((960, 640))
        actor = self._ambient_actor((640, 200))
        rect = draw_ambient_speech(self.game, target, (0, 0), actor, ['Want to play, Daisy?'])
        self.assertIsNotNone(rect)
        self.assertGreater(rect.centerx, 600)
        self.assertTrue(target.get_rect().contains(rect))
        self.assertNotEqual(target.get_at(rect.center)[:3], (0, 0, 0))
        self.assertFalse(hasattr(self.game, 'small_font'))

    def test_ambient_speech_draws_display_resolution_text_without_locking_game(self):
        from liam_daisy_play import LiamDaisyPlay
        from liam_blocks import LiamBlocks
        target = pygame.Surface((1440, 960))
        self.game.ui = self.style
        self.game.ui_surface = target
        actor = self._ambient_actor((240, 200))
        world = object()
        play = object.__new__(LiamDaisyPlay)
        play.game, play.liam, play.state = self.game, actor, 'invite'
        # SimpleNamespace is unhashable; the draw path only requires lookup.
        class Membership:
            def __getitem__(self, key):return world
        play.worlds = Membership()
        play.draw(target, (0, 0), world)
        rect = draw_ambient_speech(self.game, target, (0, 0), actor, ['Want to play, Daisy?'])
        self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(rect))
        actual = self.style.painter(target).area(rect)
        self.assertGreater(actual.centerx, 600)
        self.assertNotEqual(target.get_at(actual.center)[:3], (0, 0, 0))
        block = object.__new__(LiamBlocks)
        block.game, block.liam, block.state, block.home = self.game, actor, 'react', world
        self.game.audio.text_scale = 1.5
        block.draw(target, (0, 0), world)
        self.assertEqual((play.state, block.state), ('invite', 'react'))
        self.assertFalse(hasattr(self.game, 'social'))


if __name__ == '__main__':unittest.main()
