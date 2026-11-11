"""Live power routing, ally skills and authoritative wearable-rig presentation."""
import os
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from inventory import Inventory
from ui_style import UIStyle


class MiraRigSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
            ui_surface=pygame.Surface((960, 640)), audio=AudioSettings(),
            attributes=CharacterAttributes(), inventory=Inventory.new_journey())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.canvas = pygame.Surface((480, 320))
        self.model = BattleModel(self.game.attributes, guest_id='mira',
                                 enemy_id='ridgeback_tusker', rng=random.Random(4))
        self.scene = BattleScene(self.game, self.model, battlefield='millrace')
        self.draw()

    def tearDown(self):pygame.quit()

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def key(self, key):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def click(self, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1,
                pos=(round(point[0]*2), round(point[1]*2))))

    def ready(self, actor='mira'):
        self.model.phase = 'charging';self.model.current_action = None
        for member in (*self.model.party, *self.model.enemies):member.atb = 0.
        self.model.combatant(actor).atb = 1.;self.model.update(0)
        self.scene._sync_commands();self.draw()

    def command(self, key):
        actions = self.scene._command_actions()
        self.scene.selected = actions.index(key)
        self.scene._confirm();self.draw()

    def allocation(self, value):
        self.assertTrue(self.model.set_rig_allocation(value))
        self.draw()

    def test_mouse_drafts_do_not_change_model_until_apply_and_failed_apply_keeps_draft(self):
        self.ready()
        self.click(self.scene.rig.buttons[('support', '-')].center)
        self.click(self.scene.rig.buttons[('weapons', '+')].center)
        self.assertEqual(self.model.rig_allocation, dict.fromkeys(('weapons', 'protection', 'support'), 2))
        before = self.model.combatant('mira').mp
        with patch.object(self.model, 'set_rig_allocation', return_value=False):
            self.click(self.scene.rig.buttons['apply'].center)
        self.assertTrue(self.scene.rig.dirty)
        self.assertEqual(self.scene.rig.allocation['weapons'], 2)
        self.click(self.scene.rig.buttons['apply'].center)
        self.assertEqual(self.model.rig_allocation, {'weapons': 3, 'protection': 2, 'support': 1})
        self.assertEqual(self.model.combatant('mira').mp, before)
        self.assertIsNone(self.model.current_action)

    def test_keyboard_focus_esc_cancel_and_actor_switch_do_not_submit_a_combat_action(self):
        self.ready()
        self.key(pygame.K_m);self.assertTrue(self.scene.rig.focused)
        self.key(pygame.K_LEFT);self.key(pygame.K_DOWN);self.key(pygame.K_RIGHT)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.scene.paused)
        self.assertFalse(self.scene.rig.dirty)
        self.key(pygame.K_m);self.key(pygame.K_LEFT)
        self.model.player.atb = 1.
        self.key(pygame.K_TAB)
        self.assertFalse(self.scene.rig.focused)
        self.assertFalse(self.scene.rig.dirty)
        self.assertEqual(self.model.ready_actor, 'player')
        self.assertIsNone(self.model.current_action)

    def test_repair_cancel_and_invalid_recipient_keep_mp_then_party_row_confirms_healing(self):
        self.ready();self.allocation({'weapons': 0, 'protection': 3, 'support': 3})
        self.model.player.hp = 20
        mira = self.model.combatant('mira');before_mp = mira.mp
        self.command('skills');self.command('repair_pulse')
        self.assertEqual(self.scene.command_menu, 'skill_targets')
        self.command('ally:mira')
        self.assertIsNone(self.model.current_action)
        self.assertEqual(mira.mp, before_mp)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.scene.command_menu, 'skills')
        self.assertEqual(mira.mp, before_mp)
        self.command('repair_pulse')
        self.click(self.scene.party_rows['player']['row'].center)
        action = self.model.current_action
        self.assertEqual((action.action, action.target), ('repair_pulse', 'player'))
        self.scene.update(action.impact_at)
        self.assertGreater(self.model.player.hp, 20)
        self.assertEqual(mira.mp, before_mp-4)
        self.assertTrue(any(popup.get('healing') and popup['target'] == 'player'
                            for popup in self.scene._popups))

    def test_item_recipient_flow_remains_independent_from_ally_skill_selection(self):
        self.ready();self.model.player.hp = 20
        self.command('items');self.command('item:potion')
        self.assertEqual(self.scene.command_menu, 'item_targets')
        self.click(self.scene.party_rows['player']['row'].center)
        self.assertEqual(self.model.current_action.action, 'item:potion')
        self.scene.update(.5)
        self.assertEqual(self.model.player.hp, 120)
        self.assertEqual(self.model.item_spent, {'potion': 1})

    def test_skills_are_visible_when_unpowered_and_routing_updates_reasons(self):
        self.ready();self.command('skills')
        actions = self.scene._command_actions()
        for key in ('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'):
            self.assertIn(key, actions)
        self.assertTrue(self.scene._command_reason('charged_bolt'))
        self.assertFalse(self.scene._command_reason('impact_bolt'))
        self.allocation({'weapons': 3, 'protection': 1, 'support': 2})
        self.assertFalse(self.scene._command_reason('charged_bolt'))
        self.assertTrue(self.scene._command_reason('impact_bolt'))

    def test_authored_skill_contact_matches_damage_clock_and_projectile_ends_at_impact(self):
        self.ready();self.allocation({'weapons': 3, 'protection': 1, 'support': 2})
        self.assertTrue(self.model.choose_action('charged_bolt'))
        action = self.model.current_action
        self.scene.update(.5)
        geometry = self.scene._rig_skill_geometry()
        self.assertIsNotNone(geometry['fraction'])
        origin = geometry['origin'].copy()
        self.scene.update(.05)
        self.assertEqual(self.scene._rig_skill_geometry()['origin'], origin)
        self.scene.update(action.impact_at-action.elapsed)
        self.assertTrue(action.resolved)
        self.assertIsNone(self.scene._rig_skill_geometry()['fraction'])
        state, time = self.scene._pose('mira')
        self.assertEqual(state, 'charged_bolt')
        self.assertAlmostEqual(time, self.scene.mira_art.animations[state]['contact_ms'])
        self.draw()

    def test_barrier_display_uses_actual_pool_and_turns_and_clears_on_ko(self):
        self.ready();self.allocation({'weapons': 0, 'protection': 3, 'support': 3})
        self.assertTrue(self.model.choose_action('bulwark'))
        action = self.model.current_action
        self.scene.update(action.impact_at);self.draw()
        mira = self.model.combatant('mira')
        self.assertGreater(mira.barrier, 0)
        self.assertEqual(mira.barrier_turns, 2)
        self.assertIn('mira', self.scene.barrier_badges)
        self.assertLess(self.scene.barrier_badges['mira'].bottom, self.scene.panel_rect.top)
        mira.hp = 0;self.model.update(0);self.draw()
        self.assertNotIn('mira', self.scene.barrier_badges)


if __name__ == '__main__':unittest.main()
