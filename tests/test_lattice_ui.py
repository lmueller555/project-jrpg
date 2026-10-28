"""Lattice inspection, explicit transaction confirmation and accessible layout."""
import os
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from aether_lattice import AetherLattice
from audio_settings import AudioSettings
from character_attributes import CharacterAttributes
from inventory import Inventory
from lattice_progression import LatticeProgression
from lattice_ui import LatticeUI
from pause_menu import PauseMenu
from ui_style import UIStyle, Painter, GOLD


class LatticeUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    ui_surface=pygame.Surface((960, 640)), audio=AudioSettings(),
                                    attributes=CharacterAttributes(), inventory=Inventory(),
                                    lattice=AetherLattice(), _mouse_held=False)
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = self.to_canvas
        self.progression = LatticeProgression(self.game.lattice, self.game.inventory,
                                             {'caelan': self.game.attributes})
        self.game.move_lattice = self.progression.move
        self.game.activate_lattice = self.progression.activate
        self.game.lattice_move_reason = self.progression.move_reason
        self.game.lattice_activation_reason = self.progression.activation_reason
        self.screen = LatticeUI(self.game)
        self.game.lattice_ui = self.screen
        self.pause = PauseMenu(self.game)
        self.screen.open()
        self.screen.draw(self.game.ui_surface)

    def tearDown(self):pygame.quit()

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        p = ((point[0]-(width-480*scale)//2)/scale,
             (point[1]-(height-320*scale)//2)/scale)
        return p if 0 <= p[0] < 480 and 0 <= p[1] < 320 else None

    def point(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+logical[0]*scale),
                round((height-320*scale)//2+logical[1]*scale))

    def key(self, key, **extra):
        self.screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False, **extra))

    def release(self, key):
        self.screen.handle_event(pygame.event.Event(pygame.KEYUP, key=key))

    def advance(self, seconds):
        for _ in range(math.floor(seconds*60)):
            self.screen.update(1/60)
        remainder = seconds-math.floor(seconds*60)/60
        if remainder > 0:self.screen.update(remainder)

    def navigate(self, keys, seconds):
        for key in keys:self.key(key)
        self.advance(seconds)
        for key in keys:self.release(key)

    def select_first_hp(self):
        self.navigate_to(self.screen.board.nodes['hp_01']['position'])
        self.advance(self.screen.CAMERA_DURATION)

    def navigate_to(self, target):
        """Steer to an authored point, keeping navigation held through turns."""
        delta = pygame.Vector2(target)-self.screen.cursor_position
        horizontal = pygame.K_RIGHT if delta.x > 0 else pygame.K_LEFT
        vertical = pygame.K_DOWN if delta.y > 0 else pygame.K_UP
        if delta.x:
            self.key(horizontal)
            self.advance(abs(delta.x)*self.screen.zoom/self.screen.CURSOR_SPEED)
            if delta.y:self.key(vertical)
            self.release(horizontal)
        elif delta.y:self.key(vertical)
        if delta.y:
            self.advance(abs(delta.y)*self.screen.zoom/self.screen.CURSOR_SPEED)
            self.release(vertical)

    def click(self, logical):
        point = self.point(logical)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))

    def wheel(self, logical, amount):
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=self.point(logical),
                                                    rel=(0, 0), buttons=(0, 0, 0)))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=amount, x=0))

    def world_at(self, logical):
        return self.screen.pan+(pygame.Vector2(logical)-pygame.Vector2(self.screen.map_rect.center))/self.screen.zoom

    def snapshots(self):
        return (self.game.lattice.to_dict(), self.game.inventory.to_dict(), self.game.attributes.to_dict())

    def test_inspection_and_cursor_navigation_never_move_or_spend(self):
        before = self.snapshots()
        self.select_first_hp()
        self.assertEqual(self.screen.selected, 'hp_01')
        self.assertEqual(self.game.lattice.state()['position'], 'origin')
        for _ in self.game.lattice.board.nodes:self.key(pygame.K_TAB)
        self.assertEqual(self.screen.selected, 'hp_01')
        self.screen.fit_board()
        self.advance(self.screen.ZOOM_DURATION)
        self.click(self.screen.node_position('mp_01'))
        self.assertEqual(self.screen.selected, 'mp_01')
        self.assertEqual(self.snapshots(), before)

    def test_move_and_activation_require_confirm_and_show_exact_costs(self):
        self.assertTrue(self.progression.award_battle_rewards('ui-battle', {'caelan': 20}, {'aether_emerald': 1}))
        self.select_first_hp()
        before = self.snapshots()
        self.key(pygame.K_m)
        self.assertEqual(self.screen.pending, ('move', 'hp_01'))
        self.assertIn('Spend 1 Step (1 available).', self.screen.confirmation_text())
        self.assertEqual(self.snapshots(), before)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.screen.is_open)
        self.assertIsNone(self.screen.pending)
        self.assertEqual(self.snapshots(), before)
        self.key(pygame.K_m);self.key(pygame.K_RETURN)
        self.assertEqual(self.game.lattice.state()['position'], 'hp_01')
        self.assertEqual(self.game.lattice.rank(), 2)
        self.assertEqual(self.game.lattice.steps(), 0)
        self.key(pygame.K_a)
        text = ' '.join(self.screen.confirmation_text())
        self.assertIn('HP: 140 → 160', text)
        self.assertIn('Aether Emerald ×1 (1 owned)', text)
        self.assertIn('Current HP remains 140', text)
        self.assertEqual(self.game.inventory.quantity('aether_emerald'), 1)
        self.click(self.screen.cancel_rect.center)
        self.assertIsNone(self.screen.pending)
        self.assertEqual(self.game.attributes.value('hp'), 140)
        self.key(pygame.K_a);self.click(self.screen.confirm_rect.center)
        self.assertEqual(self.game.attributes.value('hp'), 160)
        self.assertEqual(self.game.attributes.current_hp, 140)
        self.assertEqual(self.game.inventory.quantity('aether_emerald'), 0)
        self.key(pygame.K_a)
        self.assertIsNone(self.screen.pending)
        self.assertIn('activated', self.screen.message.lower())

    def test_unavailable_actions_and_blank_nodes_remain_inspectable(self):
        before = self.snapshots()
        self.screen._select('hp_01')
        self.key(pygame.K_m)
        self.assertIsNone(self.screen.pending)
        self.assertIn('Step', self.screen.message)
        self.assertTrue(self.screen.notice_open)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.screen.notice_open)
        self.assertTrue(self.screen.is_open)
        self.screen._select('mend_01')
        self.assertIn('5', self.game.lattice_move_reason('mend_01'))
        self.assertIn('Mend', ' '.join(self.screen.detail_text()))
        self.assertEqual(self.snapshots(), before)
        self.assertTrue(self.progression.award_battle_rewards('blank-test', {'caelan': 75}, {}))
        self.screen._select('blank_01');self.key(pygame.K_m);self.key(pygame.K_RETURN)
        self.assertEqual(self.game.lattice.state()['position'], 'blank_01')
        before = self.snapshots()
        self.key(pygame.K_a)
        self.assertIsNone(self.screen.pending)
        self.assertEqual(self.snapshots(), before)

    def test_pan_zoom_fit_and_help_do_not_modify_progress(self):
        before = self.snapshots()
        self.screen.fit_board()
        self.advance(self.screen.ZOOM_DURATION)
        for identifier in self.game.lattice.board.nodes:
            self.assertTrue(self.screen.map_rect.contains(pygame.Rect(*self.screen.node_position(identifier), 1, 1)))
        old = self.screen.zoom
        self.key(pygame.K_PLUS)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertGreater(self.screen.zoom, old)
        start = self.screen.map_rect.center
        point = self.point(start)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        end = (point[0]+30, point[1]+10)
        pan = self.screen.pan.copy()
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(30, 10), buttons=(1, 0, 0)))
        self.advance(.04)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end))
        self.assertNotEqual(self.screen.pan, pan)
        old = self.screen.zoom
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1, x=0))
        self.advance(self.screen.ZOOM_DURATION)
        self.assertGreater(self.screen.zoom, old)
        self.key(pygame.K_F1)
        self.assertTrue(self.screen.help_open)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.screen.help_open)
        self.assertTrue(self.screen.is_open)
        self.assertEqual(self.snapshots(), before)

    def test_free_cursor_snaps_to_nearest_node_then_eases_camera(self):
        before = self.snapshots()
        self.key(pygame.K_RIGHT)
        self.advance(.4)
        self.assertTrue(self.screen.navigating)
        cursor = self.screen.cursor_position.copy()
        nearest = min(self.screen.board.nodes, key=lambda identifier:
                      pygame.Vector2(self.screen.board.nodes[identifier]['position']).distance_squared_to(cursor))
        pan = self.screen.pan.copy()
        self.release(pygame.K_RIGHT)
        self.assertFalse(self.screen.navigating)
        self.assertEqual(self.screen.selected, nearest)
        self.assertEqual(self.screen.cursor_position,
                         pygame.Vector2(self.screen.board.nodes[nearest]['position']))
        self.assertEqual(self.screen.pan, pan)
        target = pygame.Vector2(self.screen.board.nodes[nearest]['position'])
        initial_distance = pan.distance_to(target)
        self.assertGreater(initial_distance, 0)
        self.screen.update(self.screen.CAMERA_DURATION/3)
        self.assertLess(self.screen.pan.distance_to(target), initial_distance)
        self.assertGreater(self.screen.pan.distance_to(target), 0)
        self.advance(self.screen.CAMERA_DURATION)
        self.assertLess(self.screen.node_position(nearest).distance_to(self.screen.map_rect.center), .001)
        self.assertEqual(self.snapshots(), before)

    def test_keyboard_can_explore_distant_rank_locked_nodes_without_travel(self):
        before = self.snapshots()
        self.navigate_to(self.screen.board.nodes['lck_02']['position'])
        self.advance(self.screen.CAMERA_DURATION)
        self.assertEqual(self.screen.selected, 'lck_02')
        self.assertIn('8', self.game.lattice_move_reason('lck_02'))
        self.assertEqual(self.game.lattice.state()['position'], 'origin')
        self.assertEqual(self.game.lattice.steps(), 0)
        self.assertEqual(self.snapshots(), before)

    def test_opposite_keys_and_partial_release_do_not_stick_or_accelerate(self):
        start = self.screen.cursor_position.copy()
        self.key(pygame.K_RIGHT);self.key(pygame.K_LEFT)
        self.advance(.15)
        self.assertEqual(self.screen.cursor_position, start)
        self.release(pygame.K_LEFT)
        self.advance(.15)
        self.assertGreater(self.screen.cursor_position.x, start.x)
        self.assertTrue(self.screen.navigating)
        self.release(pygame.K_UP)
        self.assertTrue(self.screen.navigating)
        self.release(pygame.K_RIGHT)
        self.assertFalse(self.screen.navigating)
        selected = self.screen.selected
        self.advance(.4)
        self.assertEqual(self.screen.selected, selected)

    def test_diagonal_cursor_speed_matches_cardinal_and_ignores_key_repeat(self):
        start = self.screen.cursor_position.copy()
        self.key(pygame.K_RIGHT)
        self.screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=True))
        self.advance(.2)
        horizontal = self.screen.cursor_position.distance_to(start)
        self.release(pygame.K_RIGHT)
        self.screen.close();self.screen.open()
        start = self.screen.cursor_position.copy()
        self.key(pygame.K_RIGHT);self.key(pygame.K_UP)
        self.advance(.2)
        diagonal = self.screen.cursor_position.distance_to(start)
        self.assertAlmostEqual(diagonal, horizontal, places=5)
        self.release(pygame.K_RIGHT);self.release(pygame.K_UP)

    def test_click_and_tab_redirect_an_in_progress_camera_without_a_jump(self):
        self.screen.fit_board()
        self.advance(self.screen.ZOOM_DURATION)
        self.click(self.screen.node_position('mp_01'))
        initial = self.screen.pan.copy()
        target = pygame.Vector2(self.screen.board.nodes['mp_01']['position'])
        self.assertEqual(self.screen.selected, 'mp_01')
        self.assertNotEqual(initial, target)
        self.screen.update(.04)
        self.assertLess(self.screen.pan.distance_to(target), initial.distance_to(target))
        intermediate = self.screen.pan.copy()
        self.key(pygame.K_TAB)
        self.assertEqual(self.screen.pan, intermediate)
        ids = tuple(self.screen.board.nodes)
        following = ids[(ids.index('mp_01')+1) % len(ids)]
        self.assertEqual(self.screen.selected, following)
        self.advance(self.screen.CAMERA_DURATION)
        self.assertLess(self.screen.node_position(following).distance_to(self.screen.map_rect.center), .001)

    def test_drag_release_uses_nearest_cursor_node_in_letterboxed_window(self):
        before = self.snapshots()
        self.game.window = pygame.display.set_mode((1440, 810))
        self.game.ui_surface = pygame.Surface((960, 640))
        self.screen.draw(self.game.ui_surface)
        start = self.point(self.screen.map_rect.center)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        end = (start[0]-100, start[1]+30)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(-100, 30), buttons=(1, 0, 0)))
        self.assertTrue(self.screen.navigating)
        cursor = self.screen.cursor_position.copy()
        nearest = min(self.screen.board.nodes, key=lambda identifier:
                      pygame.Vector2(self.screen.board.nodes[identifier]['position']).distance_squared_to(cursor))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end))
        self.assertEqual(self.screen.selected, nearest)
        self.assertFalse(self.screen.navigating)
        self.advance(self.screen.CAMERA_DURATION)
        self.assertLess(self.screen.node_position(nearest).distance_to(self.screen.map_rect.center), .001)
        self.assertEqual(self.snapshots(), before)

    def test_focus_help_confirmation_and_close_clear_navigation(self):
        self.key(pygame.K_RIGHT);self.advance(.2)
        self.screen.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(self.screen.navigating)
        cursor = self.screen.cursor_position.copy()
        self.advance(.3)
        self.assertEqual(self.screen.cursor_position, cursor)
        self.key(pygame.K_RIGHT);self.key(pygame.K_F1)
        self.assertTrue(self.screen.help_open)
        self.assertFalse(self.screen.navigating)
        self.key(pygame.K_DOWN);self.key(pygame.K_ESCAPE)
        self.assertFalse(self.screen.help_open)
        self.assertFalse(self.screen.navigating)
        self.assertTrue(self.progression.award_battle_rewards('modal-keys', {'caelan': 20}, {}))
        self.screen._select('hp_01', center=True)
        self.key(pygame.K_m)
        self.assertIsNotNone(self.screen.pending)
        self.key(pygame.K_RIGHT)
        self.assertFalse(self.screen.navigating)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.screen.navigating)
        self.key(pygame.K_RIGHT);self.screen.close()
        self.assertFalse(self.screen.navigating)
        self.screen.open();self.advance(.4)
        self.assertEqual(self.screen.selected, 'origin')
        self.assertEqual(self.screen.cursor_position, pygame.Vector2(self.screen.board.nodes['origin']['position']))

    def test_selected_node_pulses_and_reduced_motion_uses_static_emphasis(self):
        self.advance(self.screen.CAMERA_DURATION)
        self.screen.draw(self.game.ui_surface)
        center = self.screen.node_position(self.screen.selected)*2
        region = pygame.Rect(0, 0, 72, 72);region.center = center
        first = pygame.image.tobytes(self.game.ui_surface.subsurface(region), 'RGB')
        self.advance(.25)
        self.screen.draw(self.game.ui_surface)
        second = pygame.image.tobytes(self.game.ui_surface.subsurface(region), 'RGB')
        self.assertNotEqual(first, second)
        self.game.audio.set_reduced_motion(True)
        self.screen.draw(self.game.ui_surface)
        first = pygame.image.tobytes(self.game.ui_surface.subsurface(region), 'RGB')
        self.advance(.4)
        self.screen.draw(self.game.ui_surface)
        second = pygame.image.tobytes(self.game.ui_surface.subsurface(region), 'RGB')
        self.assertEqual(first, second)
        self.screen._select('hp_01', center=True)
        self.advance(self.screen.CAMERA_DURATION)
        self.assertLess(self.screen.node_position('hp_01').distance_to(self.screen.map_rect.center), .001)

    def test_keyboard_zoom_is_smooth_and_keeps_selected_node_centered(self):
        before = self.snapshots()
        self.select_first_hp()
        start = self.screen.zoom
        self.key(pygame.K_PLUS)
        target = self.screen.target_zoom
        self.assertGreater(target, start)
        self.assertEqual(self.screen.zoom, start)
        self.advance(self.screen.ZOOM_DURATION/3)
        self.assertGreater(self.screen.zoom, start)
        self.assertLess(self.screen.zoom, target)
        self.assertLess(self.screen.node_position('hp_01').distance_to(self.screen.map_rect.center), .001)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, target)
        self.click(self.screen.zoom_out_rect.center)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, start)
        self.assertEqual(self.snapshots(), before)

    def test_rapid_zoom_retargets_from_rendered_scale_and_accumulates_requests(self):
        start = self.screen.zoom
        self.key(pygame.K_PLUS);self.key(pygame.K_PLUS)
        self.assertAlmostEqual(self.screen.target_zoom, start*1.2*1.2)
        self.assertEqual(self.screen.zoom, start)
        self.advance(.04)
        intermediate = self.screen.zoom
        self.key(pygame.K_MINUS)
        target = self.screen.target_zoom
        self.assertAlmostEqual(target, start*1.2)
        self.assertEqual(self.screen.zoom, intermediate)
        self.advance(.04)
        self.assertLess(abs(self.screen.zoom-target), abs(intermediate-target))
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, target)

    def test_wheel_zoom_preserves_point_under_pointer_in_scaled_letterboxed_windows(self):
        before = self.snapshots()
        for size in ((960, 640), (1440, 810), (800, 800)):
            with self.subTest(size=size):
                self.game.window = pygame.display.set_mode(size)
                scale = max(1, min(size[0]//480, size[1]//320))
                self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
                self.screen.reset();self.screen.open();self.screen.draw(self.game.ui_surface)
                pointer = (self.screen.map_rect.left+48, self.screen.map_rect.top+44)
                world = self.world_at(pointer)
                initial = self.screen.zoom
                self.wheel(pointer, 2)
                self.assertEqual(self.screen.zoom, initial)
                for _ in range(12):
                    self.screen.update(1/60)
                    self.assertLess(self.world_at(pointer).distance_to(world), .001)
                self.assertGreater(self.screen.zoom, initial)
                self.assertEqual(self.screen.selected, 'origin')
        self.assertEqual(self.snapshots(), before)

    def test_zoom_limits_do_not_drift_or_change_progression(self):
        before = self.snapshots()
        for _ in range(40):self.key(pygame.K_PLUS)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, self.screen.MAX_ZOOM)
        pan = self.screen.pan.copy()
        self.key(pygame.K_PLUS);self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, self.screen.MAX_ZOOM)
        self.assertEqual(self.screen.pan, pan)
        for _ in range(40):self.key(pygame.K_MINUS)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, self.screen.MIN_ZOOM)
        pan = self.screen.pan.copy()
        self.key(pygame.K_MINUS);self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, self.screen.MIN_ZOOM)
        self.assertEqual(self.screen.pan, pan)
        self.assertEqual(self.snapshots(), before)

    def test_fit_and_reset_animate_to_overview_and_selected_detail(self):
        before = self.snapshots()
        self.select_first_hp()
        start_zoom, start_pan = self.screen.zoom, self.screen.pan.copy()
        self.key(pygame.K_f)
        self.assertEqual(self.screen.zoom, start_zoom)
        self.assertEqual(self.screen.pan, start_pan)
        self.advance(self.screen.ZOOM_DURATION/3)
        self.assertLess(self.screen.zoom, start_zoom)
        self.assertNotEqual(self.screen.pan, start_pan)
        self.advance(self.screen.ZOOM_DURATION)
        for identifier in self.screen.board.nodes:
            self.assertTrue(self.screen.map_rect.collidepoint(self.screen.node_position(identifier)), identifier)
        self.key(pygame.K_0)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, 1.0)
        self.assertLess(self.screen.node_position('hp_01').distance_to(self.screen.map_rect.center), .001)
        self.click(self.screen.zoom_out_rect.center);self.advance(self.screen.ZOOM_DURATION)
        self.click(self.screen.reset_zoom_rect.center);self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, 1.0)
        self.assertEqual(self.snapshots(), before)

    def test_wheel_outside_map_and_in_help_or_confirmation_does_not_zoom(self):
        self.screen._select('mend_01', center=True)
        self.screen.draw(self.game.ui_surface)
        target = self.screen.target_zoom
        self.wheel((20, self.screen.map_rect.top-8), -2)
        self.assertEqual(self.screen.target_zoom, target)
        self.key(pygame.K_F1)
        self.wheel(self.screen.map_rect.center, -2)
        self.key(pygame.K_PLUS)
        self.assertEqual(self.screen.target_zoom, target)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.progression.award_battle_rewards('zoom-confirm', {'caelan': 20}, {}))
        self.screen._select('hp_01', center=True);self.key(pygame.K_m)
        self.assertIsNotNone(self.screen.pending)
        before = self.snapshots()
        self.wheel(self.screen.map_rect.center, 3)
        self.key(pygame.K_PLUS);self.key(pygame.K_0);self.key(pygame.K_f)
        self.assertEqual(self.screen.target_zoom, target)
        self.assertEqual(self.screen.pending, ('move', 'hp_01'))
        self.assertEqual(self.snapshots(), before)

    def test_selection_and_free_cursor_override_pointer_zoom_anchor(self):
        before = self.snapshots()
        pointer = (self.screen.map_rect.left+42, self.screen.map_rect.top+42)
        self.wheel(pointer, 2);self.advance(.04)
        pan = self.screen.pan.copy()
        self.key(pygame.K_TAB)
        self.assertEqual(self.screen.pan, pan)
        self.advance(max(self.screen.CAMERA_DURATION, self.screen.ZOOM_DURATION))
        self.assertEqual(self.screen.selected, 'hp_01')
        self.assertLess(self.screen.node_position('hp_01').distance_to(self.screen.map_rect.center), .001)
        self.wheel(pointer, -2);self.advance(.04)
        self.key(pygame.K_RIGHT);self.advance(.25)
        self.assertTrue(self.screen.navigating)
        cursor = self.screen.cursor_position.copy()
        nearest = min(self.screen.board.nodes, key=lambda identifier:
                      pygame.Vector2(self.screen.board.nodes[identifier]['position']).distance_squared_to(cursor))
        self.release(pygame.K_RIGHT)
        self.advance(max(self.screen.CAMERA_DURATION, self.screen.ZOOM_DURATION))
        self.assertEqual(self.screen.selected, nearest)
        self.assertLess(self.screen.node_position(nearest).distance_to(self.screen.map_rect.center), .001)
        self.assertEqual(self.snapshots(), before)

    def test_zoom_toolbar_fits_large_text_and_reduced_motion_finishes_immediately(self):
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.game.audio.set_text_scale(1.5)
        self.game.audio.set_reduced_motion(True)
        self.screen.draw(self.game.ui_surface)
        controls = (self.screen.zoom_out_rect, self.screen.zoom_in_rect,
                    self.screen.fit_rect, self.screen.reset_zoom_rect)
        for rect in controls:self.assertTrue(self.screen.map_rect.contains(rect))
        for index, rect in enumerate(controls):
            self.assertTrue(all(not rect.colliderect(other) for other in controls[index+1:]))
        self.key(pygame.K_PLUS)
        self.assertEqual(self.screen.zoom, self.screen.target_zoom)
        self.key(pygame.K_f)
        self.assertEqual(self.screen.zoom, self.screen.target_zoom)
        self.key(pygame.K_KP0)
        self.assertEqual(self.screen.zoom, 1.0)
        self.assertLess(self.screen.node_position(self.screen.selected).distance_to(self.screen.map_rect.center), .001)

    def test_internal_connections_curve_and_external_connections_stay_straight(self):
        curved = max((edge for edge in self.screen.board.edges if 'curve' in edge),
                     key=lambda edge: pygame.Vector2(edge['curve']).distance_to(
                         (pygame.Vector2(self.screen.board.nodes[edge['from']]['position'])+
                          pygame.Vector2(self.screen.board.nodes[edge['to']]['position']))/2))
        straight = next(edge for edge in self.screen.board.edges if 'curve' not in edge)
        before = self.snapshots()
        for zoom in (.1, .8, 2.0):
            with self.subTest(zoom=zoom):
                self.screen.zoom = self.screen.target_zoom = zoom
                points = self.screen.edge_points(curved)
                self.assertGreaterEqual(len(points), 4)
                self.assertEqual(points[0], self.screen.node_position(curved['from']))
                self.assertEqual(points[-1], self.screen.node_position(curved['to']))
                start, end = points[0], points[-1]
                direction = end-start
                deviation = max(abs((point-start).cross(direction))/direction.length() for point in points)
                self.assertGreater(deviation, .1)
                self.assertEqual(self.screen.edge_points(straight),
                                 [self.screen.node_position(straight['from']),
                                  self.screen.node_position(straight['to'])])
        self.assertEqual(self.snapshots(), before)

    def test_route_highlight_and_rank_dashes_follow_the_curved_path(self):
        self.screen._select('hp_01', center=True)
        first = next(edge for edge in self.screen.board.edges
                     if {edge['from'], edge['to']} == {'origin', 'hp_01'})
        locked = next(edge for edge in self.screen.board.edges if 'curve' in edge and edge is not first)
        with patch.dict(locked, {'min_rank': 999}), patch.object(self.screen, '_draw_path') as draw_path:
            self.screen._draw_map(self.game.ui.painter(self.game.ui_surface))
        calls = {(tuple(call.args[2][0]), tuple(call.args[2][-1])): call
                 for call in draw_path.call_args_list}
        highlighted = calls[(tuple(self.screen.node_position(first['from'])),
                             tuple(self.screen.node_position(first['to'])))]
        self.assertEqual(highlighted.args[1], GOLD)
        self.assertGreaterEqual(len(highlighted.args[2]), 4)
        self.assertFalse(highlighted.kwargs.get('dashed', False))
        gate = calls[(tuple(self.screen.node_position(locked['from'])),
                      tuple(self.screen.node_position(locked['to'])))]
        self.assertTrue(gate.kwargs['dashed'])
        self.assertGreaterEqual(len(gate.args[2]), 4)

    def test_confirmations_and_pause_rows_fit_all_text_sizes(self):
        self.assertTrue(self.progression.award_battle_rewards('layout-test', {'caelan': 20}, {'aether_emerald': 1}))
        self.screen._select('hp_01');self.key(pygame.K_m);self.key(pygame.K_RETURN);self.key(pygame.K_a)
        for size in ((480, 320), (960, 640), (1440, 810)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            for text_scale in (1.0, 1.25, 1.5):
                with self.subTest(size=size, text_scale=text_scale):
                    self.game.audio.set_text_scale(text_scale)
                    painter = self.game.ui.painter(self.game.ui_surface)
                    self.screen.draw(self.game.ui_surface)
                    self.assertFalse(self.screen.confirm_panel.colliderect(self.screen.close_rect))
                    self.assertTrue(pygame.Rect(8, 8, 464, 304).contains(self.screen.confirm_panel))
                    self.assertTrue(self.screen.confirm_panel.contains(self.screen.confirm_rect))
                    self.assertTrue(self.screen.confirm_panel.contains(self.screen.cancel_rect))
                    for line in self.screen._confirmation_layout(painter)[0]:
                        self.assertLessEqual(painter.font('small').size(line)[0], self.screen.confirm_view.width)
                    self.key(pygame.K_END)
                    self.assertEqual(self.screen.confirm_scroll, self.screen.confirm_max_scroll)
                    self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())
                    for row in self.pause.rows:
                        self.assertTrue(pygame.Rect(126, 24, 228, 282).contains(row))
                        self.assertLess(row.bottom, 288)

    def test_full_width_map_and_hover_leave_the_lattice_unobstructed(self):
        before = self.snapshots()
        original_text = Painter.text
        for size in ((480, 320), (960, 640), (1440, 810)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            for text_scale in (1.0, 1.5):
                with self.subTest(size=size, text_scale=text_scale):
                    self.game.audio.set_text_scale(text_scale)
                    self.screen.draw(self.game.ui_surface)
                    self.assertTrue(self.screen.map_rect.collidepoint((440, 230)))
                    self.assertTrue(self.screen.map_rect.collidepoint((32, 230)))
                    self.assertGreater(self.screen.map_rect.width, 480*.9)
                    self.assertTrue(pygame.Rect(8, 8, 464, 304).contains(self.screen.map_rect))
                    self.screen.fit_board();self.advance(self.screen.ZOOM_DURATION)
                    for identifier in self.screen.board.nodes:
                        self.assertTrue(self.screen.map_rect.collidepoint(self.screen.node_position(identifier)))
                    self.screen._select('mend_01', center=True)
                    self.advance(self.screen.CAMERA_DURATION)
                    self.screen.handle_event(pygame.event.Event(
                        pygame.MOUSEMOTION, pos=self.point(self.screen.node_position('mend_01')),
                        rel=(0, 0), buttons=(0, 0, 0)))
                    with patch.object(Painter, 'text', autospec=True, side_effect=original_text) as draw_text:
                        self.screen.draw(self.game.ui_surface)
                    rendered = [call.args[1] for call in draw_text.call_args_list]
                    self.assertNotIn('Mend', rendered)
                    self.assertNotIn('M: Move', rendered)
                    self.assertNotIn('A: Activate', rendered)
                    self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())
        self.assertEqual(self.snapshots(), before)

    def test_former_action_button_space_is_read_only_map_for_clicks_and_drags(self):
        self.assertTrue(self.progression.award_battle_rewards(
            'reclaimed-map-space', {'caelan': 10000}, {'aether_emerald': 1}))
        for index, point in enumerate(((382, 264), (382, 292))):
            with self.subTest(former_button=index):
                if index:self.assertTrue(self.progression.move('hp_01'))
                self.screen._select('hp_01', center=True)
                self.advance(self.screen.CAMERA_DURATION)
                before = self.snapshots()
                world = self.world_at(point)
                nearest = min(self.screen.board.nodes, key=lambda identifier:
                              pygame.Vector2(self.screen.board.nodes[identifier]['position']).distance_squared_to(world))
                self.click(point)
                self.assertEqual(self.screen.selected, nearest)
                self.assertIsNone(self.screen.pending)
                self.assertFalse(self.screen.notice_open)
                self.assertEqual(self.snapshots(), before)
        before = self.snapshots()
        start, end = self.point((382, 264)), self.point((425, 225))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=end,
                                                    rel=(end[0]-start[0], end[1]-start[1]), buttons=(1, 0, 0)))
        self.assertTrue(self.screen.navigating)
        self.advance(.04)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end))
        self.assertFalse(self.screen.navigating)
        self.assertIsNone(self.screen.pending)
        self.assertFalse(self.screen.notice_open)
        self.assertEqual(self.snapshots(), before)

    def test_pause_overlay_cancels_pending_then_returns_without_spending(self):
        self.pause.open();self.pause.selected = self.pause.options.index('Aether Lattice')
        self.pause.activate()
        self.assertEqual(self.pause.overlay, 'lattice')
        self.assertTrue(self.progression.award_battle_rewards('cancel-test', {'caelan': 20}, {}))
        self.screen._select('hp_01');self.key(pygame.K_m)
        before = self.snapshots()
        self.pause.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        self.assertIsNone(self.screen.pending)
        self.assertTrue(self.screen.is_open)
        self.pause.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        self.assertFalse(self.screen.is_open)
        self.assertTrue(self.pause.is_open)
        self.assertIsNone(self.pause.overlay)
        self.assertEqual(self.snapshots(), before)


if __name__ == '__main__':unittest.main()
