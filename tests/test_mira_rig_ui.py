"""Preview-local routing, deliberate commits and compact accessible layouts."""
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from mira_rig_ui import CHANNELS, MiraRigUI
from ui_style import UIStyle


class MiraRigUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):
        self.widget = MiraRigUI()
        self.widget.layout((200, 220, 120, 69))

    def key(self, key):
        return self.widget.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def click(self, point):
        result = self.widget.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), point)
        self.widget.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1), point)
        return result

    def test_invalid_allocations_and_free_power_cannot_overdraw_the_six_unit_budget(self):
        for value in ({'weapons': True, 'protection': 2, 'support': 3},
                      {'weapons': 7, 'protection': 0, 'support': -1},
                      {'weapons': 3, 'protection': 1, 'support': 1}):
            with self.assertRaises(ValueError):MiraRigUI(value)
        before = self.widget.allocation
        self.assertFalse(self.widget.adjust('weapons', 1))
        self.assertTrue(self.widget.adjust('support', -1))
        self.assertFalse(self.widget.commit())
        self.assertEqual(self.widget.allocation, before)
        self.assertTrue(self.widget.adjust('weapons', 1))
        self.assertTrue(self.widget.commit())
        self.assertEqual(self.widget.allocation, {'weapons': 3, 'protection': 2, 'support': 1})
        exposed = self.widget.allocation;exposed['weapons'] = 0
        self.assertEqual(self.widget.allocation['weapons'], 3)

    def test_keyboard_only_changes_focused_preview_and_escape_discards_draft(self):
        self.assertFalse(self.key(pygame.K_LEFT))
        self.click(self.widget.channel_rects['weapons'].center)
        self.assertTrue(self.key(pygame.K_LEFT))
        self.assertEqual(self.widget.available, 1)
        self.key(pygame.K_DOWN);self.key(pygame.K_RIGHT);self.key(pygame.K_RETURN)
        self.assertEqual(self.widget.allocation, {'weapons': 1, 'protection': 3, 'support': 2})
        self.key(pygame.K_LEFT);self.key(pygame.K_ESCAPE)
        self.assertFalse(self.widget.focused)
        self.assertFalse(self.widget.dirty)
        self.assertEqual(self.widget.available, 0)

    def test_mouse_edits_and_cancel_never_changes_applied_preview_until_commit(self):
        self.click(self.widget.buttons[('support', '-')].center)
        self.click(self.widget.buttons[('weapons', '+')].center)
        self.assertEqual(self.widget.allocation['weapons'], 2)
        self.click(self.widget.buttons['cancel'].center)
        self.assertEqual(self.widget.draft, self.widget.allocation)
        self.click(self.widget.buttons[('support', '-')].center)
        self.click(self.widget.buttons[('weapons', '+')].center)
        self.click(self.widget.buttons['apply'].center)
        self.assertEqual(self.widget.allocation['weapons'], 3)
        before = self.widget.draft
        self.widget.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), enabled=False)
        self.assertEqual(self.widget.draft, before)
        self.assertFalse(self.widget.focused)

    def test_normal_and_enlarged_text_hit_regions_fit_three_member_console(self):
        for width in (117, 180):
            for text_scale in (1., 1.5):
                with self.subTest(width=width, text_scale=text_scale):
                    game = SimpleNamespace(audio=SimpleNamespace(text_scale=text_scale))
                    surface = pygame.Surface((960, 640), pygame.SRCALPHA)
                    painter = UIStyle(game).painter(surface)
                    rect = pygame.Rect(200, 220, width, 69 if text_scale == 1 else 96)
                    self.widget.draw(painter, rect, focused=True)
                    for region in (*self.widget.buttons.values(), *self.widget.channel_rects.values()):
                        self.assertTrue(rect.contains(region), (rect, region))
                    for key in CHANNELS:
                        self.assertFalse(self.widget.buttons[(key, '-')].colliderect(
                            self.widget.buttons[(key, '+')]))
                        self.assertEqual(len(self.widget.pip_rects[key]), 6)
                        for pip in self.widget.pip_rects[key]:
                            self.assertTrue(self.widget.channel_rects[key].contains(pip))
                            self.assertLess(pip.right, self.widget.buttons[(key, '-')].left)
                        expected = key.title()+' 2' if width == 180 else key[0].upper()+' 2'
                        self.assertEqual(self.widget.channel_labels[key], expected)

    def test_window_focus_loss_releases_input_capture_without_committing_draft(self):
        self.click(self.widget.buttons[('support', '-')].center)
        self.assertTrue(self.widget.dirty)
        before = self.widget.allocation
        self.widget.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(self.widget.focused)
        self.assertEqual(self.widget.allocation, before)
        self.assertFalse(self.key(pygame.K_RETURN))


if __name__ == '__main__':unittest.main()
