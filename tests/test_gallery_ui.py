"""Actual Gallery input, accessible layout and metadata-only thumbnail loading."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pygame

from gallery_ui import GalleryUI
from ui_style import UIStyle, Painter


def entries(count):
    return tuple(SimpleNamespace(id=f'scene_{index}', name=f'The lanterns of Eldenmere {index+1}',
                                 chapter='Chapter 1 · Life in Eldenmere',
                                 description='Caelan and his friends share a quiet moment before the festival.',
                                 thumbnail=f'missing-gallery-thumbnail-{index}.png', controls='Space: dialogue')
                 for index in range(count))


class GalleryUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((1280, 720)),
                                    audio=SimpleNamespace(text_scale=1, effects_volume=0),
                                    launch_gallery_scene=Mock(), close_gallery=Mock())
        self.game.ui = UIStyle(self.game)
        self.gallery = GalleryUI(self.game, entries(30))
        self.gallery.layout(self.gallery._painter())

    def tearDown(self):pygame.quit()

    def key(self, key, repeat=False):
        return self.gallery.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))

    def point(self, point):
        return self.gallery._painter().point(point)

    def click(self, point):
        self.gallery.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(point)))
        self.gallery.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=self.point(point)))

    def test_keyboard_navigation_reveals_selection_in_a_long_catalogue(self):
        self.key(pygame.K_END)
        self.assertEqual(self.gallery.selected, 29)
        self.assertTrue(self.gallery.viewport.contains(self.gallery.rows[29]))
        self.assertEqual(self.gallery.scroll, self.gallery.max_scroll)
        self.key(pygame.K_HOME)
        self.assertEqual(self.gallery.selected, 0)
        self.assertEqual(self.gallery.scroll, 0)
        self.key(pygame.K_PAGEDOWN)
        self.assertGreater(self.gallery.selected, 0)
        self.assertTrue(self.gallery.viewport.contains(self.gallery.rows[self.gallery.selected]))
        self.key(pygame.K_PAGEUP)
        self.assertEqual(self.gallery.selected, 0)
        self.key(pygame.K_UP)
        self.assertEqual(self.gallery.selected, 0)
        self.key(pygame.K_s, repeat=True)
        self.assertEqual(self.gallery.selected, 1)

    def test_wheel_clamps_and_keyboard_recovers_focus_after_manual_scroll(self):
        self.gallery.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-100000))
        self.assertEqual(self.gallery.scroll, self.gallery.max_scroll)
        self.assertEqual(self.gallery.selected, 0)
        self.key(pygame.K_DOWN)
        self.assertTrue(self.gallery.viewport.contains(self.gallery.rows[1]))
        self.gallery.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=100000))
        self.assertEqual(self.gallery.scroll, 0)

    def test_mouse_selection_launch_and_header_do_not_confuse_row_hit_testing(self):
        point = self.point(self.gallery.rows[1].center)
        self.gallery.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=point, rel=(0, 0), buttons=(0, 0, 0)))
        self.assertEqual(self.gallery.selected, 1)
        self.game.launch_gallery_scene.assert_not_called()
        self.click(self.gallery.rows[1].center)
        self.game.launch_gallery_scene.assert_called_once_with('scene_1')
        self.game.launch_gallery_scene.reset_mock()
        self.click((45, 40))
        self.game.launch_gallery_scene.assert_not_called()
        self.key(pygame.K_KP_ENTER)
        self.game.launch_gallery_scene.assert_called_once_with('scene_1')
        self.key(pygame.K_RETURN, repeat=True)
        self.game.launch_gallery_scene.assert_called_once()

    def test_back_button_escape_and_backspace_return_to_title(self):
        self.click(self.gallery.back_rect.center)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_BACKSPACE)
        self.assertEqual(self.game.close_gallery.call_count, 3)

    def test_return_from_playback_preserves_scroll_selection_and_allows_replay(self):
        self.key(pygame.K_END)
        before = self.gallery.selected, self.gallery.scroll
        self.click(self.gallery.play_rect.center)
        self.gallery._mouse_held = True
        self.gallery.resume()
        self.assertEqual((self.gallery.selected, self.gallery.scroll), before)
        self.assertFalse(self.gallery._mouse_held)
        self.click(self.gallery.play_rect.center)
        self.assertEqual(self.game.launch_gallery_scene.call_count, 2)
        self.game.launch_gallery_scene.assert_called_with('scene_29')

    def test_empty_catalogue_is_readable_and_back_remains_available(self):
        self.gallery = GalleryUI(self.game, ())
        with patch.object(Painter, 'text', autospec=True, wraps=Painter.text) as draw_text:
            self.gallery.draw()
        self.assertTrue(any(call.args[1] == 'No scenes yet' for call in draw_text.call_args_list))
        self.key(pygame.K_END)
        self.key(pygame.K_RETURN)
        self.click(self.gallery.play_rect.center)
        self.game.launch_gallery_scene.assert_not_called()
        self.assertEqual(self.gallery.max_scroll, 0)
        self.key(pygame.K_ESCAPE)
        self.game.close_gallery.assert_called_once()

    def test_only_visible_thumbnails_load_and_successes_and_failures_are_cached(self):
        image = pygame.Surface((480, 320))
        with patch('gallery_ui.pygame.image.load', return_value=image) as load:
            self.gallery.draw()
            visible = sum(row.colliderect(self.gallery.viewport) for row in self.gallery.rows)
            self.assertEqual(load.call_count, visible)
            self.gallery.draw()
            self.assertEqual(load.call_count, visible)
            self.key(pygame.K_END)
            self.gallery.draw()
            self.assertGreater(load.call_count, visible)
            self.assertLess(load.call_count, len(self.gallery.entries))
        self.gallery = GalleryUI(self.game, entries(1))
        with patch('gallery_ui.pygame.image.load', side_effect=FileNotFoundError) as load:
            self.gallery.draw()
            self.gallery.draw()
            load.assert_called_once()
        self.assertIsNone(self.gallery._thumbnails[self.gallery.entries[0].thumbnail])

    def test_resize_and_large_text_keep_buttons_and_selected_name_readable(self):
        for size in ((480, 320), (640, 360), (960, 640), (1280, 720), (1920, 810), (800, 800)):
            for text_scale in (1, 1.25, 1.5):
                with self.subTest(size=size, text_scale=text_scale):
                    self.game.window = pygame.display.set_mode(size)
                    self.game.audio.text_scale = text_scale
                    self.key(pygame.K_END)
                    self.gallery.draw()
                    self.assertTrue(self.gallery.panel.contains(self.gallery.back_rect))
                    self.assertTrue(self.gallery.panel.contains(self.gallery.play_rect))
                    self.assertFalse(self.gallery.viewport.colliderect(self.gallery.play_rect))
                    painter = self.gallery._painter()
                    self.assertLessEqual(painter.font(bold=True).size('Play scene')[0]+38,
                                         self.gallery.play_rect.width)
                    self.assertLessEqual(painter.font('small').size(self.gallery._footer_hint)[0],
                                         self.gallery.play_rect.left-48)
                    row = self.gallery.rows[-1]
                    self.assertGreaterEqual(row.top, self.gallery.viewport.top)
                    self.assertLess(row.top, self.gallery.viewport.bottom)
                    actual = self.point(self.gallery.back_rect.center)
                    self.assertTrue(pygame.Rect((0, 0), size).collidepoint(actual))
                    self.assertLess(self.gallery.viewport.top, self.gallery.viewport.bottom)

    def test_failed_scene_message_can_be_dismissed_without_losing_catalogue_position(self):
        self.key(pygame.K_END)
        before = self.gallery.selected, self.gallery.scroll
        self.gallery.error = 'The scene could not be opened. Its required asset is missing.'
        self.gallery.draw()
        self.key(pygame.K_RETURN)
        self.assertIsNone(self.gallery.error)
        self.assertEqual((self.gallery.selected, self.gallery.scroll), before)
        self.game.launch_gallery_scene.assert_not_called()
        self.game.close_gallery.assert_not_called()


if __name__ == '__main__':unittest.main()
