"""Lattice node clicks, contextual purchases and unobstructed exploration."""
import os
import math
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from aether_lattice import AetherLattice, LatticeBoard
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


    def select(self, identifier):
        self.screen._select(identifier, center=True)
        self.advance(self.screen.CAMERA_DURATION)
        self.screen.draw(self.game.ui_surface)

    def reward(self, rp=20, drops=None):
        self.assertTrue(self.progression.award_battle_rewards(
            'ui-fixture', {'caelan': rp}, drops or {}))

    def click_action(self, action):
        self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen.action_preview()['action'], action)
        self.assertIsNotNone(self.screen.action_rect)
        self.click(self.screen.action_rect.center)
        self.screen.draw(self.game.ui_surface)

    def resize(self, size, text_scale=1.0):
        self.game.window = pygame.display.set_mode(size)
        scale = max(1, min(size[0]//480, size[1]//320))
        self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
        self.game.audio.set_text_scale(text_scale)
        self.screen.draw(self.game.ui_surface)

    def test_node_clicks_and_cursor_navigation_never_spend(self):
        before = self.snapshots()
        self.select_first_hp()
        self.assertEqual(self.screen.selected, 'hp_01')
        self.assertEqual(self.game.lattice.state()['position'], 'origin')
        self.screen.fit_board();self.advance(self.screen.ZOOM_DURATION)
        self.click(self.screen.node_position('mp_01'))
        self.assertEqual(self.screen.selected, 'mp_01')
        self.assertEqual(self.snapshots(), before)

    def test_blank_map_click_does_not_select_a_distant_nearest_node(self):
        self.select('hp_01')
        before, selected, pan = self.snapshots(), self.screen.selected, self.screen.pan.copy()
        point = next((x, y) for x in range(30, 450, 20)
                     for y in range(self.screen.map_rect.top+12, 290, 20)
                     if self.screen._node_at((x, y)) is None)
        self.click(point);self.advance(.3)
        self.assertEqual(self.screen.selected, selected)
        self.assertEqual(self.screen.pan, pan)
        self.assertEqual(self.snapshots(), before)

    def test_click_selection_does_not_execute_the_new_context_button(self):
        self.reward(drops={'aether_emerald': 1})
        self.screen.fit_board();self.advance(self.screen.ZOOM_DURATION)
        before = self.snapshots()
        self.click(self.screen.node_position('hp_01'))
        self.advance(self.screen.CAMERA_DURATION)
        self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen.selected, 'hp_01')
        self.assertEqual(self.screen.action_preview()['action'], 'move')
        self.assertEqual(self.snapshots(), before)

    def test_move_and_activation_clicks_show_costs_and_execute_directly(self):
        self.reward(drops={'aether_emerald': 1})
        self.select('hp_01')
        before = self.snapshots()
        preview = self.screen.action_preview()
        self.assertEqual((preview['action'], preview['node'], preview['button']),
                         ('move', 'hp_01', 'Move'))
        self.assertIn('1 Step', ' '.join(preview['lines']))
        self.assertEqual(self.snapshots(), before)
        self.click_action('move')
        self.assertEqual(self.game.lattice.state()['position'], 'hp_01')
        self.assertEqual(self.game.lattice.steps(), 0)
        self.assertEqual(self.game.lattice.rank(), 2)
        preview = self.screen.action_preview()
        self.assertEqual(preview['action'], 'activate')
        self.assertEqual(preview['button'], 'Activate')
        text = ' '.join(preview['lines'])
        self.assertIn('140', text)
        self.assertIn('240', text)
        self.assertIn('Aether Emerald', text)
        self.click_action('activate')
        self.assertEqual(self.game.attributes.value('hp'), 240)
        self.assertEqual(self.game.attributes.current_hp, 140)
        self.assertEqual(self.game.inventory.quantity('aether_emerald'), 0)
        self.assertIsNone(self.screen.action_preview())
        self.assertIsNone(self.screen.action_rect)

    def test_activation_displays_and_consumes_the_entire_crystal_bundle(self):
        node = self.screen.board.nodes['hp_01']
        with patch.dict(node['cost'], {'aether_emerald': 2, 'aether_sapphire': 1}, clear=True):
            self.reward(drops={'aether_emerald': 2, 'aether_sapphire': 1})
            self.assertTrue(self.progression.move('hp_01'))
            self.select('hp_01')
            text = ' '.join(self.screen.action_preview()['lines'])
            self.assertIn('Aether Emerald', text)
            self.assertIn('Aether Sapphire', text)
            self.click_action('activate')
            self.assertEqual(self.game.inventory.quantity('aether_emerald'), 0)
            self.assertEqual(self.game.inventory.quantity('aether_sapphire'), 0)
            self.assertEqual(self.game.attributes.value('hp'), 240)

    def test_ability_activation_uses_the_context_button(self):
        self.reward(10000, {'aether_diamond': 10})
        self.assertTrue(self.progression.move('mend_01'))
        self.select('mend_01')
        text = ' '.join(self.screen.action_preview()['lines'])
        self.assertIn('Mend', text)
        self.assertIn('Aether Diamond', text)
        self.click_action('activate')
        self.assertIn('mend', self.game.lattice.learned_abilities())
        self.assertIsNone(self.screen.action_preview())

    def test_migrated_converted_node_displays_its_preserved_earned_hp_reward(self):
        def selected_icon():
            with patch('lattice_ui.draw_attribute_icon') as draw_icon:
                self.screen.draw(self.game.ui_surface)
            center = self.screen.node_position('hp_05')
            return [call.args[1] for call in draw_icon.call_args_list
                    if pygame.Vector2(call.args[2].center).distance_to(center) < 1]

        self.select('hp_05')
        self.assertEqual(self.screen.board.nodes['hp_05']['stat'], 'mp')
        self.assertEqual(selected_icon(), ['mp'])
        path = Path(__file__).resolve().parents[1]/'assets/progression/aether_lattice_v2.json'
        old = AetherLattice(LatticeBoard(json.loads(path.read_text())))
        progression = LatticeProgression(old, self.game.inventory, {'caelan': self.game.attributes})
        self.assertTrue(progression.award_battle_rewards(
            'converted_node_legacy', {'caelan': 10000}, {'aether_emerald': 1}))
        self.assertTrue(progression.move('hp_05'))
        self.assertTrue(progression.activate('hp_05'))
        earned = old.board.nodes['hp_05']['amount']
        maximum = 140+earned
        self.assertTrue(self.game.attributes.set_current(hp=maximum-7))
        attributes = self.game.attributes.to_dict()
        current = AetherLattice()
        self.assertTrue(current.restore(old.to_dict()))
        self.assertTrue(self.game.attributes.restore(attributes, lattice_bonuses=current.bonuses()))
        self.game.lattice = current
        self.progression = LatticeProgression(current, self.game.inventory, {'caelan': self.game.attributes})
        self.game.move_lattice = self.progression.move
        self.game.activate_lattice = self.progression.activate
        self.game.lattice_move_reason = self.progression.move_reason
        self.game.lattice_activation_reason = self.progression.activation_reason
        self.select('hp_05')
        before = self.snapshots()
        self.assertEqual(selected_icon(), ['hp'])
        self.assertIn('HP +'+str(earned), self.screen.detail_text())
        self.assertNotIn('MP +'+str(self.screen.board.nodes['hp_05']['amount']), self.screen.detail_text())
        self.assertEqual((self.game.attributes.value('hp'), self.game.attributes.current_hp),
                         (maximum, maximum-7))
        self.assertIsNone(self.screen.action_preview())
        self.assertEqual(self.snapshots(), before)

    def test_unaffordable_locked_and_current_blank_nodes_have_no_action(self):
        before = self.snapshots()
        for identifier in ('origin', 'hp_01', 'mend_01'):
            with self.subTest(identifier=identifier):
                self.select(identifier)
                self.assertIsNone(self.screen.action_preview())
                self.assertIsNone(self.screen.context_rect)
                self.assertIsNone(self.screen.action_rect)
        self.assertEqual(self.snapshots(), before)
        self.reward(75)
        self.select('blank_01')
        self.assertEqual(self.screen.action_preview()['action'], 'move')
        self.click_action('move')
        self.assertEqual(self.game.lattice.state()['position'], 'blank_01')
        self.assertIsNone(self.screen.action_preview())
        self.select('hp_01');self.click_action('move')
        self.assertIsNone(self.screen.action_preview())  # No Emerald for activation.

    def test_removed_shortcuts_do_not_select_zoom_purchase_or_confirm(self):
        self.reward(drops={'aether_emerald': 1})
        self.select('hp_01')
        before = self.snapshots()
        camera, zoom, selected = self.screen.pan.copy(), self.screen.zoom, self.screen.selected
        for key in (pygame.K_TAB, pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS,
                    pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_f, pygame.K_0,
                    pygame.K_KP0, pygame.K_m, pygame.K_a, pygame.K_RETURN,
                    pygame.K_KP_ENTER):
            with self.subTest(key=key):
                self.key(key);self.key(key, mod=pygame.KMOD_SHIFT)
                self.advance(.25)
                self.assertEqual(self.screen.selected, selected)
                self.assertEqual(self.screen.zoom, zoom)
                self.assertEqual(self.screen.pan, camera)
                self.assertEqual(self.snapshots(), before)
        self.click_action('move')
        before = self.snapshots()
        self.key(pygame.K_a);self.key(pygame.K_RETURN)
        self.assertEqual(self.snapshots(), before)
        self.assertEqual(self.game.attributes.value('hp'), 140)

    def test_stale_move_button_cannot_become_activate_without_redraw(self):
        self.reward(drops={'aether_emerald': 1})
        self.select('hp_01')
        old_point = self.screen.action_rect.center
        self.assertTrue(self.progression.move('hp_01'))
        before = self.snapshots()
        self.click(old_point)
        self.assertEqual(self.snapshots(), before)
        self.assertEqual(self.game.attributes.value('hp'), 140)
        self.screen.draw(self.game.ui_surface)
        self.click_action('activate')
        self.assertEqual(self.game.attributes.value('hp'), 240)

    def test_stale_move_button_cannot_use_a_changed_route_cost(self):
        self.reward(10000)
        self.select('blank_01')
        old_point = self.screen.action_rect.center
        displayed_lines = self.screen.action_preview()['lines']
        self.assertTrue(self.progression.move('hp_01'))
        self.assertNotEqual(self.screen.action_preview()['lines'], displayed_lines)
        before = self.snapshots()
        self.click(old_point)
        self.assertEqual(self.snapshots(), before)
        self.assertEqual(self.game.lattice.state()['position'], 'hp_01')
        self.screen.draw(self.game.ui_surface)
        self.click_action('move')
        self.assertEqual(self.game.lattice.state()['position'], 'blank_01')

    def test_stale_move_button_cannot_spend_missing_steps(self):
        self.reward(45)
        self.select('hp_01')
        old_point = self.screen.action_rect.center
        self.assertTrue(self.progression.move('hp_01'))
        self.assertTrue(self.progression.move('origin'))
        self.assertEqual(self.game.lattice.steps(), 0)
        before = self.snapshots()
        self.click(old_point)
        self.assertEqual(self.snapshots(), before)
        self.screen.draw(self.game.ui_surface)
        self.assertIsNone(self.screen.action_preview())
        self.assertIsNone(self.screen.action_rect)

    def test_stale_activation_button_cannot_spend_missing_crystals(self):
        self.reward(drops={'aether_emerald': 1})
        self.assertTrue(self.progression.move('hp_01'))
        self.select('hp_01')
        old_point = self.screen.action_rect.center
        self.assertTrue(self.game.inventory.consume_bundle({'aether_emerald': 1}))
        before = self.snapshots()
        self.click(old_point)
        self.assertEqual(self.snapshots(), before)
        self.assertEqual(self.game.attributes.value('hp'), 140)
        self.screen.draw(self.game.ui_surface)
        self.assertIsNone(self.screen.action_preview())
        self.assertIsNone(self.screen.action_rect)

    def test_held_mouse_press_cannot_chain_move_and_activation(self):
        self.reward(drops={'aether_emerald': 1})
        self.select('hp_01')
        point = self.point(self.screen.action_rect.center)
        press = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        self.screen.handle_event(press)
        self.assertEqual(self.game.lattice.state()['position'], 'hp_01')
        self.screen.draw(self.game.ui_surface)
        for _ in range(3):
            self.screen.handle_event(press)
            if self.screen.action_rect:
                self.screen.handle_event(pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(self.screen.action_rect.center)))
        self.assertEqual(self.game.attributes.value('hp'), 140)
        self.assertEqual(self.game.inventory.quantity('aether_emerald'), 1)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))
        self.click_action('activate')
        self.assertEqual(self.game.attributes.value('hp'), 240)

    def test_context_hides_during_navigation_and_help(self):
        self.reward(drops={'aether_emerald': 1})
        self.select('hp_01')
        before = self.snapshots()
        self.assertIsNotNone(self.screen.action_rect)
        self.key(pygame.K_RIGHT)
        self.screen.draw(self.game.ui_surface)
        self.assertIsNone(self.screen.action_preview())
        self.assertIsNone(self.screen.action_rect)
        self.release(pygame.K_RIGHT);self.advance(.25)
        self.key(pygame.K_F1)
        self.screen.draw(self.game.ui_surface)
        self.assertTrue(self.screen.help_open)
        self.assertIsNone(self.screen.action_preview())
        self.assertIsNone(self.screen.action_rect)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.screen.help_open)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.screen.is_open)
        self.assertFalse(self.screen.help_open)
        self.assertEqual(self.snapshots(), before)

    def test_clicks_redirect_camera_from_the_current_rendered_position(self):
        self.screen.fit_board();self.advance(self.screen.ZOOM_DURATION)
        self.click(self.screen.node_position('mp_01'))
        initial = self.screen.pan.copy()
        target = pygame.Vector2(self.screen.board.nodes['mp_01']['position'])
        self.assertEqual(self.screen.selected, 'mp_01')
        self.assertNotEqual(initial, target)
        self.screen.update(.04)
        self.assertLess(self.screen.pan.distance_to(target), initial.distance_to(target))
        intermediate = self.screen.pan.copy()
        identifier = next(identifier for identifier in self.screen.board.nodes
                          if identifier != 'mp_01' and self.screen.map_rect.collidepoint(
                              self.screen.node_position(identifier)))
        self.click(self.screen.node_position(identifier))
        self.assertEqual(self.screen.pan, intermediate)
        self.assertEqual(self.screen.selected, identifier)
        self.advance(self.screen.CAMERA_DURATION)
        self.assertLess(self.screen.node_position(identifier).distance_to(self.screen.map_rect.center), .001)

    def test_camera_grab_freezes_existing_motion_and_ignores_wheel_until_release(self):
        self.screen._select('hp_01', center=True)
        self.wheel(self.screen.map_rect.center, 1);self.advance(.04)
        start = pygame.Vector2(self.screen.map_rect.center)+(42, -18)
        pan, zoom = self.screen.pan.copy(), self.screen.zoom
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(start)))
        self.advance(.3)
        self.assertEqual(self.screen.pan, pan)
        self.assertEqual(self.screen.zoom, zoom)
        end = start+(-20, 8)
        world = self.world_at(start)
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEMOTION, pos=self.point(end), rel=(0, 0), buttons=(1, 0, 0)))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=2, x=0))
        self.advance(.3)
        self.assertEqual(self.screen.zoom, zoom)
        self.assertLess(self.world_at(end).distance_to(world), .001)
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=self.point(end)))
        self.wheel(self.screen.map_rect.center, 1);self.advance(self.screen.ZOOM_DURATION)
        self.assertGreater(self.screen.zoom, zoom)

    def test_camera_drags_with_owned_resources_do_not_purchase(self):
        self.reward(10000, {'aether_emerald': 5})
        self.assertTrue(self.progression.move('hp_01'))
        self.select('hp_01')
        before = self.snapshots()
        for delta in ((-36, -20), (30, 16)):
            start = pygame.Vector2(self.screen.map_rect.center)+(-36, -24)
            end = start+delta
            self.screen.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(start)))
            self.screen.handle_event(pygame.event.Event(
                pygame.MOUSEMOTION, pos=self.point(end), rel=(0, 0), buttons=(1, 0, 0)))
            self.advance(.2)
            self.assertTrue(self.screen.navigating)
            self.assertIsNone(self.screen.action_preview())
            self.screen.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONUP, button=1, pos=self.point(end)))
            self.advance(self.screen.CAMERA_DURATION)
            self.assertEqual(self.snapshots(), before)

    def test_focus_help_and_close_clear_arrow_navigation(self):
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
        self.key(pygame.K_RIGHT);self.screen.close()
        self.assertFalse(self.screen.navigating)
        self.screen.open();self.advance(.4)
        self.assertEqual(self.screen.selected, 'origin')
        self.assertEqual(self.screen.cursor_position, pygame.Vector2(self.screen.board.nodes['origin']['position']))

    def test_wheel_zoom_is_smooth_at_selected_center(self):
        before = self.snapshots()
        self.select('hp_01')
        start = self.screen.zoom
        self.wheel(self.screen.map_rect.center, 1)
        target = self.screen.target_zoom
        self.assertGreater(target, start)
        self.assertEqual(self.screen.zoom, start)
        self.advance(self.screen.ZOOM_DURATION/3)
        self.assertGreater(self.screen.zoom, start)
        self.assertLess(self.screen.zoom, target)
        self.assertLess(self.screen.node_position('hp_01').distance_to(self.screen.map_rect.center), .001)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, target)
        self.wheel(self.screen.map_rect.center, -1);self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, start)
        self.assertEqual(self.snapshots(), before)

    def test_rapid_wheel_zoom_retargets_without_jumps(self):
        start = self.screen.zoom
        pointer = self.screen.map_rect.center
        self.wheel(pointer, 1);self.wheel(pointer, 1)
        self.assertAlmostEqual(self.screen.target_zoom, start*1.2*1.2)
        self.assertEqual(self.screen.zoom, start)
        self.advance(.04)
        intermediate = self.screen.zoom
        self.wheel(pointer, -1)
        target = self.screen.target_zoom
        self.assertAlmostEqual(target, start*1.2)
        self.assertEqual(self.screen.zoom, intermediate)
        self.advance(.04)
        self.assertLess(abs(self.screen.zoom-target), abs(intermediate-target))
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, target)

    def test_wheel_zoom_limits_do_not_drift_or_change_progression(self):
        before = self.snapshots()
        for _ in range(8):self.wheel(self.screen.map_rect.center, 10)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, self.screen.MAX_ZOOM)
        pan = self.screen.pan.copy()
        self.wheel(self.screen.map_rect.center, 1);self.advance(self.screen.ZOOM_DURATION)
        self.assertEqual(self.screen.pan, pan)
        for _ in range(8):self.wheel(self.screen.map_rect.center, -10)
        self.advance(self.screen.ZOOM_DURATION)
        self.assertAlmostEqual(self.screen.zoom, self.screen.MIN_ZOOM)
        pan = self.screen.pan.copy()
        self.wheel(self.screen.map_rect.center, -1);self.advance(self.screen.ZOOM_DURATION)
        self.assertEqual(self.screen.pan, pan)
        self.assertEqual(self.snapshots(), before)

    def test_wheel_outside_map_and_in_help_scrolls_without_zooming(self):
        self.select('mend_01')
        target = self.screen.target_zoom
        self.wheel((20, self.screen.map_rect.top-8), -2)
        self.assertEqual(self.screen.target_zoom, target)
        self.key(pygame.K_F1)
        self.screen.draw(self.game.ui_surface)
        self.wheel(self.screen.map_rect.center, -2)
        self.assertEqual(self.screen.target_zoom, target)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.screen.help_open)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.screen.help_open)
        self.assertTrue(self.screen.is_open)

    def test_click_and_free_cursor_override_pointer_zoom_anchor(self):
        before = self.snapshots()
        pointer = (self.screen.map_rect.left+42, self.screen.map_rect.top+42)
        self.wheel(pointer, 2);self.advance(.04)
        pan = self.screen.pan.copy()
        self.click(self.screen.node_position('hp_01'))
        self.assertEqual(self.screen.pan, pan)
        self.advance(max(self.screen.CAMERA_DURATION, self.screen.ZOOM_DURATION))
        self.assertEqual(self.screen.selected, 'hp_01')
        self.assertLess(self.screen.node_position('hp_01').distance_to(self.screen.map_rect.center), .001)
        self.wheel(pointer, -2);self.advance(.04)
        self.key(pygame.K_RIGHT);self.advance(.25)
        cursor = self.screen.cursor_position.copy()
        nearest = min(self.screen.board.nodes, key=lambda identifier:
                      pygame.Vector2(self.screen.board.nodes[identifier]['position']).distance_squared_to(cursor))
        self.release(pygame.K_RIGHT)
        self.advance(max(self.screen.CAMERA_DURATION, self.screen.ZOOM_DURATION))
        self.assertEqual(self.screen.selected, nearest)
        self.assertLess(self.screen.node_position(nearest).distance_to(self.screen.map_rect.center), .001)
        self.assertEqual(self.snapshots(), before)

    def test_reduced_motion_wheel_and_selection_finish_immediately(self):
        self.resize((480, 320), 1.5)
        self.game.audio.set_reduced_motion(True)
        self.wheel(self.screen.map_rect.center, 2)
        self.assertEqual(self.screen.zoom, self.screen.target_zoom)
        self.screen._select('hp_01', center=True)
        self.assertLess(self.screen.node_position('hp_01').distance_to(self.screen.map_rect.center), .001)

    def test_affordable_route_highlight_and_rank_dashes_follow_curves(self):
        self.reward()
        self.select('hp_01')
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

    def test_unaffordable_selection_does_not_highlight_a_travel_preview(self):
        self.select('hp_01')
        with patch.object(self.screen, '_draw_path') as draw_path:
            self.screen._draw_map(self.game.ui.painter(self.game.ui_surface))
        self.assertTrue(all(call.args[1] != GOLD for call in draw_path.call_args_list))

    def test_context_and_pause_rows_fit_all_text_and_window_sizes(self):
        self.reward(drops={'aether_emerald': 1})
        self.select('hp_01')
        for action in ('move', 'activate'):
            for size in ((480, 320), (960, 640), (1440, 810)):
                for text_scale in (1.0, 1.25, 1.5):
                    with self.subTest(action=action, size=size, text_scale=text_scale):
                        self.resize(size, text_scale)
                        self.screen.center_on('hp_01', immediate=True)
                        self.screen.draw(self.game.ui_surface)
                        self.assertEqual(self.screen.action_preview()['action'], action)
                        self.assertTrue(self.screen.map_rect.contains(self.screen.context_rect))
                        self.assertTrue(self.screen.context_rect.contains(self.screen.action_rect))
                        self.assertFalse(self.screen.context_rect.collidepoint(self.screen.node_position('hp_01')))
                        self.assertFalse(self.screen.context_rect.colliderect(self.screen.close_rect))
                        for line in self.screen._context_layout(self.screen._painter())[0]:
                            self.assertLessEqual(self.screen._painter().font('small').size(line)[0],
                                                 self.screen.context_rect.width-12)
                        self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())
                        for row in self.pause.rows:
                            self.assertTrue(pygame.Rect(126, 24, 228, 282).contains(row))
            if action == 'move':self.assertTrue(self.progression.move('hp_01'))

    def test_full_activation_bundle_fits_minimum_window_with_large_text(self):
        node = self.screen.board.nodes['hp_01']
        with patch.dict(node['cost'], {'aether_emerald': 2, 'aether_sapphire': 1}, clear=True):
            self.reward(drops={'aether_emerald': 2, 'aether_sapphire': 1})
            self.assertTrue(self.progression.move('hp_01'))
            self.resize((480, 320), 1.5)
            self.select('hp_01')
            lines, height = self.screen._context_layout(self.screen._painter())
            text = ' '.join(lines)
            self.assertIn('Aether Emerald', text)
            self.assertIn('Aether Sapphire', text)
            self.assertTrue(self.screen.map_rect.contains(self.screen.context_rect))
            self.assertTrue(self.screen.context_rect.contains(self.screen.action_rect))
            self.assertLessEqual(self.screen.context_rect.top+8+len(lines)*height,
                                 self.screen.action_rect.top)
            self.assertFalse(self.screen.context_rect.collidepoint(self.screen.node_position('hp_01')))
            self.click_action('activate')
            self.assertEqual(self.game.attributes.value('hp'), 240)
            self.assertEqual(self.game.inventory.quantity('aether_emerald'), 0)
            self.assertEqual(self.game.inventory.quantity('aether_sapphire'), 0)

    def test_toolbar_and_persistent_instructions_are_not_rendered(self):
        before = self.snapshots()
        original_text, original_button = Painter.text, Painter.button
        for size in ((480, 320), (960, 640), (1440, 810)):
            for text_scale in (1.0, 1.5):
                with self.subTest(size=size, text_scale=text_scale):
                    self.resize(size, text_scale)
                    self.assertGreater(self.screen.map_rect.width, 480*.9)
                    self.assertTrue(self.screen.map_rect.collidepoint((440, 230)))
                    self.assertTrue(self.screen.map_rect.collidepoint((32, 290)))
                    self.select('mend_01')
                    with patch.object(Painter, 'text', autospec=True, side_effect=original_text) as texts, \
                         patch.object(Painter, 'button', autospec=True, side_effect=original_button) as buttons:
                        self.screen.draw(self.game.ui_surface)
                    rendered = [call.args[1] for call in texts.call_args_list]
                    labels = [call.args[2] for call in buttons.call_args_list]
                    for removed in ('M: Move', 'A: Activate', 'Enter confirms', '100%', 'Fit', '+', '−'):
                        self.assertNotIn(removed, rendered)
                        self.assertNotIn(removed, labels)
                    self.assertIsNone(self.screen.action_rect)
                    self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())
        self.assertEqual(self.snapshots(), before)

    def test_old_toolbar_space_is_ordinary_map_for_clicks_and_drags(self):
        before = self.snapshots()
        for point in ((36, 286), (64, 286), (162, 286), (232, 286), (382, 264)):
            selected = self.screen.selected
            node = self.screen._node_at(point)
            self.click(point)
            self.advance(.25)
            self.assertEqual(self.screen.selected, node or selected)
            self.assertEqual(self.snapshots(), before)
        start, end = self.point((232, 286)), self.point((300, 225))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=end,
                                                    rel=(end[0]-start[0], end[1]-start[1]), buttons=(1, 0, 0)))
        self.assertTrue(self.screen.navigating)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end))
        self.assertFalse(self.screen.navigating)
        self.assertEqual(self.snapshots(), before)

    def test_pause_escape_returns_without_spending_or_a_confirmation_modal(self):
        self.pause.open();self.pause.selected = self.pause.options.index('Aether Lattice')
        self.pause.activate()
        self.assertEqual(self.pause.overlay, 'lattice')
        self.reward()
        self.select('hp_01')
        before = self.snapshots()
        self.pause.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        self.assertFalse(self.screen.is_open)
        self.assertTrue(self.pause.is_open)
        self.assertIsNone(self.pause.overlay)
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

    def test_camera_grab_keeps_world_under_pointer_at_each_scale_and_zoom(self):
        before = self.snapshots()
        for size in ((480, 320), (960, 640), (1440, 810), (800, 800)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            for zoom in (.12, .8, 2.0):
                with self.subTest(size=size, zoom=zoom):
                    self.screen.reset();self.screen.open()
                    self.screen._select('focused_strike_01', center=True)
                    self.screen._zoom_to(zoom)
                    self.advance(self.screen.ZOOM_DURATION)
                    self.screen.draw(self.game.ui_surface)
                    start = pygame.Vector2(self.screen.map_rect.center)+(40, -24)
                    end = start+(-12, 6)
                    world = self.world_at(start)
                    pan = self.screen.pan.copy()
                    self.screen.handle_event(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(start)))
                    self.assertEqual(self.screen.pan, pan)
                    self.screen.handle_event(pygame.event.Event(
                        pygame.MOUSEMOTION, pos=self.point(end), rel=(0, 0), buttons=(1, 0, 0)))
                    self.assertLess(self.world_at(end).distance_to(world), .001)
                    self.assertGreater(self.screen.pan.distance_to(pan), 0)
                    held_pan = self.screen.pan.copy()
                    self.advance(.4)
                    self.assertEqual(self.screen.pan, held_pan)
                    self.assertLess(self.world_at(end).distance_to(world), .001)
                    self.screen.handle_event(pygame.event.Event(
                        pygame.MOUSEBUTTONUP, button=1, pos=self.point(end)))
        self.assertEqual(self.snapshots(), before)

    def test_drag_threshold_preserves_the_entire_pointer_displacement(self):
        self.screen._select('focused_strike_01', center=True)
        self.advance(self.screen.CAMERA_DURATION)
        start = pygame.Vector2(self.screen.map_rect.center)+(32, -20)
        world, pan = self.world_at(start), self.screen.pan.copy()
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(start)))
        for distance in (1, 2):
            self.screen.handle_event(pygame.event.Event(
                pygame.MOUSEMOTION, pos=self.point(start+(distance, 0)),
                rel=(2, 0), buttons=(1, 0, 0)))
            self.advance(.05)
            self.assertEqual(self.screen.pan, pan)
        end = start+(3, 0)
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEMOTION, pos=self.point(end), rel=(2, 0), buttons=(1, 0, 0)))
        self.assertLess(self.world_at(end).distance_to(world), .001)
        self.assertNotEqual(self.screen.pan, pan)
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=self.point(end)))

    def test_slight_pointer_jitter_is_a_click_without_camera_motion_while_held(self):
        self.screen.fit_board();self.advance(self.screen.ZOOM_DURATION)
        start = pygame.Vector2(self.point(self.screen.node_position('mp_01')))
        pan = self.screen.pan.copy()
        before = self.snapshots()
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEMOTION, pos=start+(2, 0), rel=(2, 0), buttons=(1, 0, 0)))
        self.advance(.3)
        self.assertEqual(self.screen.pan, pan)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=start+(2, 0)))
        self.assertEqual(self.screen.selected, 'mp_01')
        self.assertEqual(self.screen.pan, pan)
        self.advance(self.screen.CAMERA_DURATION)
        self.assertLess(self.screen.node_position('mp_01').distance_to(self.screen.map_rect.center), .001)
        self.assertEqual(self.snapshots(), before)

    def test_camera_drag_release_selects_center_nearest_and_eases_without_a_jump(self):
        self.screen._select('focused_strike_01', center=True)
        self.advance(self.screen.CAMERA_DURATION)
        start = pygame.Vector2(self.screen.map_rect.center)+(50, -30)
        end = start+(-24, 12)
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(start)))
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEMOTION, pos=self.point(end), rel=(0, 0), buttons=(1, 0, 0)))
        pan = self.screen.pan.copy()
        nearest = min(self.screen.board.nodes, key=lambda identifier:
                      (pan.distance_squared_to(self.screen.board.nodes[identifier]['position']), identifier))
        self.screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=self.point(end)))
        self.assertFalse(self.screen.navigating)
        self.assertEqual(self.screen.selected, nearest)
        self.assertEqual(self.screen.pan, pan)
        target = pygame.Vector2(self.screen.board.nodes[nearest]['position'])
        self.assertGreater(pan.distance_to(target), .001)
        self.advance(self.screen.CAMERA_DURATION/3)
        self.assertGreater(self.screen.pan.distance_to(target), .001)
        self.assertLess(self.screen.pan.distance_to(target), pan.distance_to(target))
        self.advance(self.screen.CAMERA_DURATION)
        self.assertLess(self.screen.node_position(nearest).distance_to(self.screen.map_rect.center), .001)

    def test_focus_help_and_close_stop_camera_drag_without_stale_mouse_motion(self):
        before = self.snapshots()
        for interruption in ('focus', 'help', 'close'):
            with self.subTest(interruption=interruption):
                self.screen.close();self.screen.open()
                start = pygame.Vector2(self.screen.map_rect.center)
                end = start+(-30, 12)
                self.screen.handle_event(pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, button=1, pos=self.point(start)))
                self.screen.handle_event(pygame.event.Event(
                    pygame.MOUSEMOTION, pos=self.point(end), rel=(0, 0), buttons=(1, 0, 0)))
                if interruption == 'focus':
                    self.screen.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
                elif interruption == 'help':self.key(pygame.K_F1)
                else:self.screen.close()
                self.assertFalse(self.screen.navigating)
                self.advance(.3)
                pan = self.screen.pan.copy()
                self.screen.handle_event(pygame.event.Event(
                    pygame.MOUSEMOTION, pos=self.point(end+(-60, 30)), rel=(0, 0), buttons=(1, 0, 0)))
                self.advance(.3)
                self.assertEqual(self.screen.pan, pan)
                if self.screen.help_open:self.key(pygame.K_ESCAPE)
                self.screen.handle_event(pygame.event.Event(
                    pygame.MOUSEBUTTONUP, button=1, pos=self.point(end)))
        self.assertEqual(self.snapshots(), before)

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


if __name__ == '__main__':unittest.main()
