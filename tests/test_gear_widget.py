"""Captured wheel input, mechanical stops and display-resolution rendering."""
import math
import os
from types import SimpleNamespace
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from gear_state import GEM_ORDER
from gear_widget import GearWidget, QUARTER, SNAP_SECONDS, wrap_angle
from ui_style import UIStyle


class GearWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.widget = GearWidget()
        self.widget.layout((100, 100, 48, 48))

    def event(self, event_type, point=None, **values):
        if event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            values.setdefault('button', 1)
        return self.widget.handle_event(pygame.event.Event(event_type, **values), point)

    def drag_quarter(self, release=(160, 125)):
        self.assertTrue(self.event(pygame.MOUSEBUTTONDOWN, (124, 113)))
        self.assertTrue(self.event(pygame.MOUSEMOTION, (136, 125)))
        self.assertTrue(self.event(pygame.MOUSEBUTTONUP, release))

    def test_pointer_crosses_angle_wrap_by_a_small_delta(self):
        original = self.widget.angle
        self.event(pygame.MOUSEBUTTONDOWN, (112, 124))
        self.event(pygame.MOUSEMOTION, (112, 126))
        self.assertLess(abs(self.widget.angle - original), .2)
        self.assertAlmostEqual(wrap_angle(math.tau + .1), .1)

    def test_release_outside_captures_and_seats_once(self):
        self.drag_quarter()
        self.assertFalse(self.widget.dragging)
        self.assertTrue(self.widget.settling)
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertIsNone(self.widget.update(SNAP_SECONDS * .5))
        self.assertEqual(self.widget.update(SNAP_SECONDS * .5), 'nature')
        self.assertEqual(self.widget.active_gem, 'nature')
        self.assertFalse(self.widget.settling)
        self.assertIsNone(self.widget.update(1))
        self.assertEqual(self.widget.consume_notices().count('seat'), 1)
        self.assertEqual(self.widget.consume_notices(), ())

    def test_release_without_a_logical_point_uses_last_captured_angle(self):
        self.drag_quarter(release=None)
        self.assertEqual(self.widget.update(.2), 'nature')

    def test_cancel_restores_committed_gem_and_discards_unfinished_seat(self):
        self.drag_quarter()
        self.widget.update(.04)
        self.widget.cancel()
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertAlmostEqual(self.widget.angle, -QUARTER)
        self.assertFalse(self.widget.dragging or self.widget.settling)
        self.assertIsNone(self.widget.update(1))
        self.assertEqual(self.widget.consume_notices(), ())

    def test_reduced_motion_snaps_on_release_and_delivers_one_commit(self):
        self.event(pygame.MOUSEBUTTONDOWN, (124, 113))
        self.event(pygame.MOUSEMOTION, (136, 125))
        self.widget.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1),
                                 None, reduced_motion=True)
        self.assertTrue(self.widget.busy)
        self.assertEqual(self.widget.preview_gem, 'nature')
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertEqual(self.widget.update(0, reduced_motion=True), 'nature')
        self.assertFalse(self.widget.busy)
        self.assertEqual(self.widget.active_gem, 'nature')
        self.assertIsNone(self.widget.update(0, reduced_motion=True))
        self.assertEqual(self.widget._burst_remaining, 0)

    def test_reduced_motion_outside_click_before_update_keeps_the_catch_owned(self):
        self.event(pygame.MOUSEBUTTONDOWN, (124, 113))
        self.event(pygame.MOUSEMOTION, (136, 125))
        self.widget.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1),
                                 None, reduced_motion=True)
        self.assertTrue(self.event(pygame.MOUSEBUTTONDOWN, (200, 200)))
        self.assertTrue(self.widget.busy)
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertEqual(self.widget.preview_gem, 'nature')
        self.assertEqual(self.widget.update(0, reduced_motion=True), 'nature')

    def test_outside_click_during_snap_cannot_cancel_or_release_ownership(self):
        self.drag_quarter()
        self.widget.update(.04)
        self.assertTrue(self.event(pygame.MOUSEBUTTONDOWN, (200, 200)))
        self.assertTrue(self.widget.busy)
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertEqual(self.widget.update(.06), 'nature')

    def test_outside_click_cancels_an_unconfirmed_keyboard_preview(self):
        self.widget.focused = True
        self.event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        self.assertFalse(self.event(pygame.MOUSEBUTTONDOWN, (200, 200)))
        self.assertFalse(self.widget.busy or self.widget.focused)
        self.assertEqual(self.widget.preview_gem, self.widget.active_gem)
        self.assertIsNone(self.widget.update(.2))

    def test_reduced_motion_tab_before_update_cancels_cleanly(self):
        self.widget.focused = True
        self.widget.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT),
                                 reduced_motion=True)
        self.widget.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN),
                                 reduced_motion=True)
        self.assertTrue(self.widget.busy)
        self.assertTrue(self.event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertFalse(self.widget.busy or self.widget.focused)
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertEqual(self.widget.preview_gem, 'water')
        self.assertIsNone(self.widget.update(0, reduced_motion=True))

    def test_disabling_cancels_captured_drag_without_committing(self):
        self.event(pygame.MOUSEBUTTONDOWN, (124, 113))
        self.event(pygame.MOUSEMOTION, (136, 125))
        self.widget.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1),
                                 None, enabled=False)
        self.assertFalse(self.widget.dragging or self.widget.focused)
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertIsNone(self.widget.update(1))

    def test_center_press_focuses_without_unstable_rotation(self):
        self.event(pygame.MOUSEBUTTONDOWN, (124, 125))
        self.assertTrue(self.widget.focused)
        self.assertFalse(self.widget.dragging)
        self.event(pygame.MOUSEMOTION, (140, 125))
        self.assertAlmostEqual(self.widget.angle, -QUARTER)

    def test_crossing_center_reanchors_pointer_without_a_jump(self):
        self.event(pygame.MOUSEBUTTONDOWN, (124, 113))
        self.event(pygame.MOUSEMOTION, (124, 125))
        self.event(pygame.MOUSEMOTION, (124, 137))
        self.assertAlmostEqual(self.widget.angle, -QUARTER)

    def test_keyboard_is_explicitly_focused_and_confirms_once(self):
        self.assertFalse(self.event(pygame.KEYDOWN, key=pygame.K_LEFT))
        self.widget.focused = True
        self.assertTrue(self.event(pygame.KEYDOWN, key=pygame.K_LEFT))
        self.assertEqual(self.widget.preview_gem, 'fire')
        self.assertEqual(self.widget.active_gem, 'water')
        self.assertTrue(self.event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(self.widget.update(.1), 'fire')
        self.assertTrue(self.event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(self.widget.focused)

    def test_keyboard_preview_remains_busy_until_keypad_enter_seats(self):
        self.widget.focused = True
        self.event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        self.assertTrue(self.widget.busy)
        self.assertTrue(self.event(pygame.KEYDOWN, key=pygame.K_KP_ENTER))
        self.assertTrue(self.widget.busy)
        self.assertEqual(self.widget.update(.1), 'nature')
        self.assertFalse(self.widget.busy)

    def test_same_slot_click_is_a_catch_without_an_element_change(self):
        self.event(pygame.MOUSEBUTTONDOWN, (124, 113))
        self.event(pygame.MOUSEBUTTONUP, (124, 113))
        self.assertIsNone(self.widget.update(.1))
        self.assertEqual(self.widget.active_gem, 'water')

    def test_nearest_catch_matches_the_preview_at_each_half_slot(self):
        for stop in range(-4, 5):
            self.widget.angle = (stop + .5) * QUARTER
            preview = self.widget.preview_gem
            self.widget._start_snap(False)
            self.widget.update(.1)
            self.assertEqual(self.widget.active_gem, preview)

    def test_native_pixels_scale_crisply_at_multiple_display_sizes(self):
        style = UIStyle(SimpleNamespace(audio=SimpleNamespace(text_scale=1)))
        self.widget.layout((216, 260, 48, 48))
        for gem in GEM_ORDER:
            self.widget.active_gem = gem
            for size in ((480, 320), (960, 640), (1440, 960)):
                surface = pygame.Surface(size)
                surface.fill('#11271f')
                painter = style.painter(surface)
                self.widget.draw(painter, 0, focused=True)
                # Scaling takes each native gear pixel to an exact square block.
                unit = size[0] // 480
                point = painter.point((240, 284))
                color = surface.get_at(point)
                self.assertEqual(color, surface.get_at((point[0] + unit - 1, point[1] + unit - 1)))

    def test_element_bursts_have_different_particle_shapes(self):
        style = UIStyle(SimpleNamespace(audio=SimpleNamespace(text_scale=1)))
        masks = []
        self.widget.layout((24, 24, 48, 48))
        for gem in GEM_ORDER:
            self.widget.active_gem = gem
            self.widget._burst_remaining = .24
            surface = pygame.Surface((96, 96), pygame.SRCALPHA)
            self.widget._draw_burst(style.painter(surface, (96, 96)))
            masks.append(pygame.image.tobytes(surface, 'RGBA')[3::4])
        self.assertEqual(len(set(masks)), 4)

    def test_blue_only_drag_cannot_seat_an_empty_socket(self):
        self.widget = GearWidget(owned_gems=('water',))
        self.widget.layout((100, 100, 48, 48))
        self.drag_quarter()
        self.assertEqual(self.widget.preview_gem, 'water')
        self.assertIsNone(self.widget.update(.2))
        self.assertEqual(self.widget.active_gem, 'water')
        self.widget.focused = True
        for key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.event(pygame.KEYDOWN, key=key)
            self.assertEqual(self.widget.preview_gem, 'water')
        with self.assertRaises(ValueError):self.widget.active_gem = 'fire'

    def test_keyboard_skips_empty_sockets_when_a_later_gem_is_installed(self):
        self.widget = GearWidget(owned_gems=('water', 'fire'))
        self.widget.layout((100, 100, 48, 48))
        self.widget.focused = True
        for expected in ('fire', 'water', 'fire', 'water'):
            self.event(pygame.KEYDOWN, key=pygame.K_LEFT)
            self.assertEqual(self.widget.preview_gem, expected)
            self.event(pygame.KEYDOWN, key=pygame.K_RETURN)
            self.assertEqual(self.widget.update(.1), expected)

    def test_unowned_slots_render_as_empty_settings(self):
        from gear_widget import _mechanism, _point
        empty = _mechanism(0, 1, ('water',))
        full = _mechanism(0, 1)
        for index, gem in enumerate(GEM_ORDER):
            point = _point(12, index * QUARTER)
            if gem == 'water':self.assertEqual(empty.get_at(point), full.get_at(point))
            else:self.assertEqual(tuple(empty.get_at(point))[:3], (24, 43, 38))


if __name__ == '__main__':
    unittest.main()
