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
        for _ in range(self.menu.settings_index):self.assertTrue(self.key(pygame.K_DOWN))
        self.assertTrue(self.key(pygame.K_RETURN))
        self.assertTrue(self.menu.settings)
        self.assertTrue(self.key(pygame.K_ESCAPE))
        self.assertFalse(self.menu.settings)
        self.assertTrue(self.menu.is_open)
        self.assertTrue(self.key(pygame.K_ESCAPE))
        self.assertFalse(self.menu.is_open)

    def test_quit_requires_deliberate_selection_and_repeat_does_not_activate(self):
        self.menu.open()
        self.menu.selected=self.menu.options.index('Quit')
        self.assertTrue(self.key(pygame.K_RETURN, repeat=True))
        self.assertTrue(self.menu.is_open)
        self.assertFalse(self.key(pygame.K_RETURN))
        self.assertTrue(self.menu.is_open)
        self.assertTrue(self.key(pygame.K_ESCAPE))
        self.assertFalse(self.menu.is_open)

    def test_keyboard_and_mouse_volume_controls_are_independent(self):
        self.menu.open();self.menu.selected=self.menu.settings_index;self.key(pygame.K_RETURN)
        self.menu.selected=1
        self.key(pygame.K_LEFT)
        self.assertAlmostEqual(self.game.audio.music_volume,.9)
        self.assertEqual(self.game.audio.effects_volume,1)
        effects=self.menu.settings_rows[2]
        track=self.menu.slider_rects[2]
        self.click((track.left-14,effects.centery))
        self.assertAlmostEqual(self.game.audio.effects_volume,.9)
        self.assertAlmostEqual(self.game.audio.music_volume,.9)
        self.click((effects.left+30,effects.centery))
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
                self.assertTrue(self.click(self.menu.rows[self.menu.settings_index].center))
                self.assertTrue(self.menu.settings)
                canvas=pygame.Surface((480,320))
                self.menu.draw(canvas)
                self.assertNotEqual(canvas.get_at((110,57))[:3],(0,0,0))
                self.assertTrue(self.click(self.menu.settings_rows[7].center))
                self.assertFalse(self.menu.settings)
                self.assertTrue(self.click(self.menu.rows[0].center))
                self.assertFalse(self.menu.is_open)

    def test_held_click_does_not_reactivate_underlying_menu(self):
        self.menu.open()
        point=self.point(self.menu.rows[self.menu.settings_index].center)
        down=pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point)
        self.assertTrue(self.menu.handle_event(down))
        self.assertTrue(self.menu.settings)
        for _ in range(3):self.assertTrue(self.menu.handle_event(down))
        self.assertTrue(self.menu.settings)
        self.assertEqual(self.game.audio.music_volume,1)

    def test_plus_minus_and_drag_sliders_adjust_the_correct_channel(self):
        self.menu.open();self.menu.selected=self.menu.settings_index;self.key(pygame.K_RETURN)
        self.menu.selected=1
        self.key(pygame.K_MINUS)
        self.assertAlmostEqual(self.game.audio.music_volume,.9)
        self.key(pygame.K_KP_PLUS)
        self.assertEqual(self.game.audio.music_volume,1)
        self.menu.draw(pygame.Surface((960,640)))
        track=self.menu.slider_rects[2]
        point=self.point((track.left+track.width*.25,track.centery))
        self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
        self.assertAlmostEqual(self.game.audio.effects_volume,.25,delta=.01)
        target=self.point((track.left+track.width*.75,track.centery))
        self.menu.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=target,rel=(0,0),buttons=(1,0,0)))
        self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=target))
        self.assertAlmostEqual(self.game.audio.effects_volume,.75,delta=.01)
        self.assertEqual(self.game.audio.music_volume,1)
        self.assertIsNone(self.menu.settings_panel.dragging)

    def test_text_preferences_and_controls_remain_reachable_at_minimum_size(self):
        self.game.window=pygame.display.set_mode((480,320))
        self.menu.open();self.menu.selected=self.menu.settings_index;self.key(pygame.K_RETURN)
        self.menu.selected=3
        self.key(pygame.K_RIGHT);self.key(pygame.K_RIGHT)
        self.assertEqual(self.game.audio.text_scale,1.5)
        self.menu.selected=4;self.key(pygame.K_RETURN)
        self.assertTrue(self.game.audio.reduced_motion)
        self.menu.selected=5;self.key(pygame.K_RETURN)
        self.assertFalse(self.game.audio.tracker_visible)
        self.menu.selected=6;self.key(pygame.K_RETURN)
        self.assertTrue(self.menu.settings_panel.controls)
        self.menu.draw(pygame.Surface((480,320)))
        self.assertTrue(pygame.Rect(0,0,480,320).contains(self.menu.settings_panel.controls_back))
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.menu.settings_panel.controls)
        self.menu.selected=7
        self.menu.draw(pygame.Surface((480,320)))
        self.assertTrue(self.menu.settings_panel.viewport.contains(self.menu.settings_rows[7]))
        self.key(pygame.K_RETURN)
        self.assertFalse(self.menu.settings)


if __name__ == '__main__':unittest.main()
