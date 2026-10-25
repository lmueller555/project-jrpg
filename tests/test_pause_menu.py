"""Real modal menu input, volume separation and letterboxed hit testing."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from audio_settings import AudioSettings
from pause_menu import PauseMenu


class PauseMenuTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((1100, 750)),
                                    audio=AudioSettings(), fullscreen=False,
                                    _mouse_held=True, save_progress=Mock(), toggle_fullscreen=Mock())
        self.menu = PauseMenu(self.game)

    def tearDown(self):pygame.quit()

    def key(self, key, repeat=False):
        return self.menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))

    def point(self, native):
        width,height=self.game.window.get_size()
        scale=max(1,min(width//480,height//320))
        return (round((width-480*scale)//2+native[0]*scale),
                round((height-320*scale)//2+native[1]*scale))

    def click(self, native):
        point=self.point(native)
        result=self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
        self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point))
        return result

    def test_escape_resumes_and_settings_escape_returns_to_pause(self):
        self.menu.open()
        self.assertTrue(self.menu.is_open)
        self.assertFalse(self.game._mouse_held)
        self.game.save_progress.assert_called_once_with()
        self.assertTrue(self.key(pygame.K_DOWN))
        self.assertTrue(self.key(pygame.K_RETURN))
        self.assertTrue(self.menu.settings)
        self.assertTrue(self.key(pygame.K_ESCAPE))
        self.assertFalse(self.menu.settings)
        self.assertTrue(self.menu.is_open)
        self.assertTrue(self.key(pygame.K_ESCAPE))
        self.assertFalse(self.menu.is_open)

    def test_quit_requires_deliberate_selection_and_repeat_does_not_activate(self):
        self.menu.open()
        self.menu.selected=2
        self.assertTrue(self.key(pygame.K_RETURN, repeat=True))
        self.assertTrue(self.menu.is_open)
        self.assertFalse(self.key(pygame.K_RETURN))
        self.assertTrue(self.menu.is_open)
        self.assertTrue(self.key(pygame.K_ESCAPE))
        self.assertFalse(self.menu.is_open)

    def test_keyboard_and_mouse_volume_controls_are_independent(self):
        self.menu.open();self.menu.selected=1;self.key(pygame.K_RETURN)
        self.menu.selected=1
        self.key(pygame.K_LEFT)
        self.assertAlmostEqual(self.game.audio.music_volume,.9)
        self.assertEqual(self.game.audio.effects_volume,1)
        effects=self.menu.settings_rows[2]
        self.click((effects.left+12,effects.centery))
        self.assertAlmostEqual(self.game.audio.effects_volume,.9)
        self.assertAlmostEqual(self.game.audio.music_volume,.9)
        self.click(effects.center)
        self.assertEqual(self.game.audio.effects_volume,0)
        self.key(pygame.K_RETURN)
        self.assertAlmostEqual(self.game.audio.effects_volume,.9)
        self.menu.selected=0;self.key(pygame.K_RETURN)
        self.game.toggle_fullscreen.assert_called_once_with()

    def test_mouse_hitboxes_follow_integer_scaling_and_ignore_black_borders(self):
        for size in ((1100,750),(1440,810),(800,800)):
            with self.subTest(size=size):
                self.game.window=pygame.display.set_mode(size)
                self.menu.open()
                self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(0,0)))
                self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=(0,0)))
                self.assertTrue(self.menu.is_open)
                self.assertTrue(self.click(self.menu.rows[1].center))
                self.assertTrue(self.menu.settings)
                canvas=pygame.Surface((480,320))
                self.menu.draw(canvas)
                self.assertNotEqual(canvas.get_at((110,57))[:3],(0,0,0))
                self.assertTrue(self.click(self.menu.settings_rows[3].center))
                self.assertFalse(self.menu.settings)
                self.assertTrue(self.click(self.menu.rows[0].center))
                self.assertFalse(self.menu.is_open)

    def test_held_click_does_not_reactivate_underlying_menu(self):
        self.menu.open()
        point=self.point(self.menu.rows[1].center)
        down=pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point)
        self.assertTrue(self.menu.handle_event(down))
        self.assertTrue(self.menu.settings)
        for _ in range(3):self.assertTrue(self.menu.handle_event(down))
        self.assertTrue(self.menu.settings)
        self.assertEqual(self.game.audio.music_volume,1)


if __name__ == '__main__':unittest.main()
