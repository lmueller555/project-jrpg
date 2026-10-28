"""Lattice inspection, explicit transaction confirmation and accessible layout."""
import os
from types import SimpleNamespace
import unittest

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
from ui_style import UIStyle


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

    def click(self, logical):
        point = self.point(logical)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))

    def snapshots(self):
        return (self.game.lattice.to_dict(), self.game.inventory.to_dict(), self.game.attributes.to_dict())

    def test_inspection_and_cursor_navigation_never_move_or_spend(self):
        before = self.snapshots()
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.screen.selected, 'hp_01')
        self.assertEqual(self.game.lattice.state()['position'], 'origin')
        for _ in self.game.lattice.board.nodes:self.key(pygame.K_TAB)
        self.assertEqual(self.screen.selected, 'hp_01')
        self.screen.fit_board()
        self.click(self.screen.node_position('mp_01'))
        self.assertEqual(self.screen.selected, 'mp_01')
        self.assertEqual(self.snapshots(), before)

    def test_move_and_activation_require_confirm_and_show_exact_costs(self):
        self.assertTrue(self.progression.award_battle_rewards('ui-battle', {'caelan': 20}, {'aether_emerald': 1}))
        self.key(pygame.K_RIGHT)
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
        self.click(self.screen.move_rect.center)
        self.assertIsNone(self.screen.pending)
        self.assertIn('Step', self.screen.message)
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
        for identifier in self.game.lattice.board.nodes:
            self.assertTrue(self.screen.map_rect.contains(pygame.Rect(*self.screen.node_position(identifier), 1, 1)))
        old = self.screen.zoom
        self.key(pygame.K_PLUS)
        self.assertGreater(self.screen.zoom, old)
        start = self.screen.map_rect.center
        point = self.point(start)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        end = (point[0]+30, point[1]+10)
        pan = self.screen.pan.copy()
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(30, 10), buttons=(1, 0, 0)))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end))
        self.assertNotEqual(self.screen.pan, pan)
        old = self.screen.zoom
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1, x=0))
        self.assertGreater(self.screen.zoom, old)
        self.key(pygame.K_F1)
        self.assertTrue(self.screen.help_open)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.screen.help_open)
        self.assertTrue(self.screen.is_open)
        self.assertEqual(self.snapshots(), before)

    def test_details_confirmations_and_pause_rows_fit_all_text_sizes(self):
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
                    self.assertLess(self.screen.confirm_panel.bottom, self.screen.move_rect.top)
                    for line in self.screen._confirmation_layout(painter)[0]:
                        self.assertLessEqual(painter.font('small').size(line)[0], self.screen.confirm_view.width)
                    self.key(pygame.K_END)
                    self.assertEqual(self.screen.confirm_scroll, self.screen.confirm_max_scroll)
                    self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())
                    for row in self.pause.rows:
                        self.assertTrue(pygame.Rect(126, 24, 228, 282).contains(row))
                        self.assertLess(row.bottom, 288)

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
