"""Captured gear gestures, charging slowdown, and settled combat ownership."""
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel, ENEMY_PATH
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from gear_state import GEM_ORDER, REQUIRED_GEMS
from test_aether_edge_battle_model import FixedVariance
from ui_style import UIStyle


class EmptySprites:
    def __init__(self):
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)

    def frame(self, actor, state, elapsed_ms):
        return self.image, (24, 42)


class GearBattleSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((480, 320)),
                                    ui_surface=pygame.Surface((480, 320)),
                                    audio=AudioSettings(), attributes=CharacterAttributes())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: point
        self.canvas = pygame.Surface((480, 320))
        self.make_scene()

    def tearDown(self):
        pygame.quit()

    def make_scene(self, *, active_gem='water', tutorial=False, learned=('aether_edge',)):
        enemies = json.loads(ENEMY_PATH.read_text())
        if not tutorial:
            enemies['enemies']['ridgeback_tusker']['attributes'].update(
                hp=1000000, str=0, mag=0, speed=0)
        self.model = BattleModel(self.game.attributes, learned, rng=FixedVariance(),
                                 weapon_equipped=True, guest_id='mira',
                                 enemy_id='ridgeback_tusker', enemy_data=enemies,
                                 active_gem=active_gem, spellblade_tutorial=tutorial)
        self.scene = BattleScene(self.game, self.model, sprites=EmptySprites(),
                                 battlefield='millrace', tutorial=tutorial)
        self.draw()

    def draw(self):
        self.scene.draw(self.canvas, self.game.ui_surface)

    def key(self, key):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))

    def pointer(self, kind, point, button=1):
        properties = {'pos': point}
        if kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            properties['button'] = button
        elif kind == pygame.MOUSEMOTION:
            properties.update(rel=(0, 0), buttons=(1, 0, 0))
        self.scene.handle_event(pygame.event.Event(kind, **properties))

    def click(self, point):
        self.pointer(pygame.MOUSEBUTTONDOWN, point)
        self.pointer(pygame.MOUSEBUTTONUP, point)

    def ready(self):
        for member in self.model.party:
            member.atb = 1
        self.scene.update(0)
        self.draw()

    def resources(self):
        return [(actor.identifier, actor.hp, actor.mp, actor.atb)
                for actor in (*self.model.party, self.model.enemy)]

    def gauges(self):
        return [actor.atb for actor in (*self.model.party, *self.model.bots, self.model.enemy)]

    def gear_points(self):
        rect = self.scene.gear.rect
        # The gear's pointer mapping uses the native mechanism's (24,25) hub.
        return ((rect.left+rect.width/2, rect.top+rect.height*9/48),
                (rect.left+rect.width*40/48, rect.top+rect.height*25/48))

    def start_turn(self):
        top, right = self.gear_points()
        self.pointer(pygame.MOUSEBUTTONDOWN, top)
        self.pointer(pygame.MOUSEMOTION, right)
        return right

    def acknowledge(self):
        while self.scene.tutorial_active:
            self.key(pygame.K_RETURN)

    def test_hover_slows_every_charging_gauge_and_leaves_ready_choices_frozen(self):
        bot = self.model.bot_for()
        bot.haste_turns = 8
        actors = (*self.model.party, bot, self.model.enemy)
        self.pointer(pygame.MOUSEMOTION, self.scene.gear.rect.center)
        self.assertEqual(self.scene.atb_multiplier, .25)
        self.scene.update(.4)
        for actor in actors:
            self.assertAlmostEqual(actor.atb, self.model.atb_rate(actor)*.1)
        before = {actor.identifier: actor.atb for actor in actors}
        self.pointer(pygame.MOUSEMOTION, (479, 1))
        self.assertEqual(self.scene.atb_multiplier, 1)
        self.scene.update(.4)
        for actor in actors:
            self.assertAlmostEqual(actor.atb, before[actor.identifier]+self.model.atb_rate(actor)*.4)
        self.ready()
        self.pointer(pygame.MOUSEMOTION, self.scene.gear.rect.center)
        before = self.gauges()
        self.scene.update(10000)
        self.assertEqual(self.gauges(), before)

    def test_hover_slowdown_applies_to_charging_after_caelans_action_finishes_mid_frame(self):
        for other_atb in (0, .99):
            with self.subTest(other_atb=other_atb):
                self.make_scene()
                bot = self.model.bot_for()
                bot.haste_turns = 8
                others = (self.model.combatant('mira'), bot, self.model.enemy)
                for actor in others:
                    actor.atb = other_atb
                self.model.player.atb = 1
                self.scene.update(0)
                self.assertTrue(self.model.choose_action('attack'))
                before = {actor.identifier: actor.atb
                          for actor in (*self.model.party, bot, self.model.enemy)}
                self.pointer(pygame.MOUSEMOTION, self.scene.gear.rect.center)
                self.assertFalse(self.scene.gear_enabled)
                self.assertEqual(self.scene.atb_multiplier, .25)
                duration = self.model.current_action.duration
                self.scene.update(duration+.1)
                self.assertIsNone(self.model.current_action)
                self.assertEqual(self.model.phase, 'charging')
                self.assertEqual(self.model.last_action.elapsed, duration)
                for actor in (*self.model.party, bot, self.model.enemy):
                    self.assertAlmostEqual(actor.atb, before[actor.identifier]+
                                           self.model.atb_rate(actor)*.1*.25)
                    self.assertLess(actor.atb, 1)
                self.assertEqual(bot.haste_turns, 8)

    def test_window_resize_reprojects_hover_and_cancels_an_unfinished_gesture(self):
        def to_canvas(point):
            width, height = self.game.window.get_size()
            scale = max(1, min(width//480, height//320))
            return ((point[0]-(width-480*scale)//2)/scale,
                    (point[1]-(height-320*scale)//2)/scale)

        self.game.to_canvas = to_canvas
        self.pointer(pygame.MOUSEMOTION, self.scene.gear.rect.center)
        self.assertEqual(self.scene.atb_multiplier, .25)
        self.game.window = pygame.display.set_mode((960, 640))
        self.game.ui_surface = pygame.Surface((960, 640))
        self.scene.update(.4)
        self.assertFalse(self.scene.gear.hovered)
        self.assertEqual(self.scene.atb_multiplier, 1)
        for actor in (*self.model.party, *self.model.bots, self.model.enemy):
            self.assertAlmostEqual(actor.atb, self.model.atb_rate(actor)*.4)

        self.ready()
        top, right = self.gear_points()
        self.pointer(pygame.MOUSEBUTTONDOWN, (top[0]*2, top[1]*2))
        self.pointer(pygame.MOUSEMOTION, (right[0]*2, right[1]*2))
        self.assertTrue(self.scene.gear.dragging)
        before = self.resources()
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.scene.update(.2)
        self.assertFalse(self.scene.gear.dragging)
        self.assertFalse(self.scene.gear.settling)
        self.assertFalse(self.model.gear_settling)
        self.assertEqual(self.model.active_gem, 'water')
        self.assertEqual(self.scene.gear.active_gem, 'water')
        self.assertEqual(self.resources(), before)
        # A late release from the old viewport cannot select the adjacent actor.
        self.pointer(pygame.MOUSEBUTTONUP, self.scene.party_rows['mira']['row'].center)
        self.assertEqual(self.model.ready_actor, 'player')
        self.assertIsNone(self.model.current_action)

    def test_drag_captures_party_row_release_without_spending_or_switching_owner(self):
        self.ready()
        before = self.resources()
        self.start_turn()
        mira = self.scene.party_rows['mira']['row'].center
        self.pointer(pygame.MOUSEMOTION, mira)
        self.pointer(pygame.MOUSEBUTTONUP, mira)
        self.assertFalse(self.scene.gear.dragging)
        self.assertTrue(self.scene.gear.settling)
        self.assertEqual(self.model.ready_actor, 'player')
        self.assertIsNone(self.model.current_action)
        self.scene.update(.1)
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.model.ready_actor, 'player')
        self.assertEqual(self.model.active_gem, self.scene.gear.active_gem)

    def test_release_outside_seats_once_then_persists_and_skills_use_the_settled_gem(self):
        self.ready()
        self.game.character_abilities = SimpleNamespace(set_active_gem=Mock(return_value=True))
        self.game.save_progress = Mock()
        before = self.resources()
        self.start_turn()
        rect = self.scene.gear.rect
        outside = (rect.right+100, rect.top+rect.height*25/48)
        self.pointer(pygame.MOUSEBUTTONUP, outside)
        self.assertEqual(self.model.active_gem, 'water')
        self.assertTrue(self.model.gear_settling)
        self.scene.update(.099)
        self.assertEqual(self.model.active_gem, 'water')
        self.scene.update(.001)
        self.assertEqual(self.model.active_gem, 'nature')
        self.assertFalse(self.model.gear_settling)
        self.assertEqual(self.resources(), before)
        self.game.character_abilities.set_active_gem.assert_called_once_with('nature')
        self.game.save_progress.assert_called_once_with()
        self.scene.update(.5)
        self.game.save_progress.assert_called_once_with()
        self.click(self.scene.command_rects['skills'].center)
        self.click(self.scene.command_rects['aether_edge'].center)
        self.assertEqual(self.model.current_action.active_gem, 'nature')
        self.assertEqual(self.model.player.mp, 26)

    def test_keyboard_preview_blocks_keypad_command_until_seated_or_cancelled(self):
        self.ready()
        before = self.resources()
        self.key(pygame.K_g)
        self.key(pygame.K_RIGHT)
        self.assertNotEqual(self.scene.gear.preview_gem, self.model.active_gem)
        self.key(pygame.K_KP_ENTER)
        self.assertIsNone(self.model.current_action)
        self.assertEqual(self.resources(), before)
        self.scene.update(.1)
        self.assertEqual(self.model.active_gem, self.scene.gear.active_gem)

    def test_pause_focus_loss_and_escape_cancel_uncommitted_rotation(self):
        for focus_loss in (False, True):
            with self.subTest(focus_loss=focus_loss):
                self.make_scene()
                self.ready()
                self.start_turn()
                if focus_loss:
                    self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
                else:
                    self.key(pygame.K_ESCAPE)
                before = self.resources()
                self.assertTrue(self.scene.paused)
                self.assertFalse(self.scene.gear.dragging)
                self.assertFalse(self.scene.gear.settling)
                self.assertFalse(self.model.gear_settling)
                self.assertEqual(self.model.active_gem, 'water')
                self.assertEqual(self.scene.gear.active_gem, self.model.active_gem)
                self.scene.update(100)
                self.assertEqual(self.resources(), before)

    def test_reduced_motion_seat_then_immediate_pause_cannot_desync_model_and_widget(self):
        self.ready()
        self.game.audio.set_reduced_motion(True)
        right = self.start_turn()
        self.pointer(pygame.MOUSEBUTTONUP, right)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.scene.paused)
        self.assertEqual(self.model.active_gem, self.scene.gear.active_gem)
        self.assertFalse(self.model.gear_settling)

    def test_action_and_results_lock_gear_and_cannot_leave_pending_settlement(self):
        self.ready()
        self.click(self.scene.command_rects['attack'].center)
        self.assertEqual(self.model.current_action.actor, 'player')
        before = self.model.active_gem
        right = self.start_turn()
        self.pointer(pygame.MOUSEBUTTONUP, right)
        self.assertFalse(self.scene.gear.dragging)
        self.assertEqual(self.model.active_gem, before)
        self.scene.update(self.model.current_action.duration)
        self.model._result('victory')
        self.scene.update(0)
        self.assertFalse(self.scene.gear_enabled)
        self.assertFalse(self.model.gear_settling)
        self.assertEqual(self.scene.gear.active_gem, self.model.active_gem)

    def test_result_entered_during_a_gesture_restores_the_last_committed_focus(self):
        self.ready()
        right = self.start_turn()
        self.pointer(pygame.MOUSEBUTTONUP, right)
        self.assertTrue(self.scene.gear.settling)
        self.model._result('victory')
        self.scene.update(.2)
        self.assertFalse(self.scene.gear.dragging)
        self.assertFalse(self.scene.gear.settling)
        self.assertFalse(self.model.gear_settling)
        self.assertEqual(self.model.active_gem, 'water')
        self.assertEqual(self.scene.gear.active_gem, 'water')

    def test_aether_edge_snapshot_and_damage_are_identical_under_all_four_gems(self):
        damage = []
        for gem in GEM_ORDER:
            with self.subTest(gem=gem):
                self.make_scene(active_gem=gem)
                self.ready()
                self.click(self.scene.command_rects['skills'].center)
                self.click(self.scene.command_rects['aether_edge'].center)
                self.assertEqual(self.model.current_action.active_gem, gem)
                self.scene.update(self.model.current_action.impact_at)
                damage.append(self.model.current_action.damage)
                self.assertEqual(self.model.player.mp, 26)
                self.assertEqual(sum(popup['target'] == 'enemy' for popup in self.scene._popups), 1)
        self.assertEqual(len(set(damage)), 1)

    def test_tutorial_uses_only_blue_focus_and_automatically_discovers_aether(self):
        self.make_scene(tutorial=True, learned=())
        self.scene.update(1000)
        self.acknowledge()
        self.assertEqual(self.model.spellblade_stage, 'guard')
        self.click(self.scene.command_rects['guard'].center)
        for _ in range(30):
            self.scene.update(1000)
            self.acknowledge()
            if self.model.waiting_for_player and self.model.spellblade_stage == 'first_edge':
                break
        self.assertEqual(self.model.spellblade_stage, 'first_edge')
        self.assertIn('gear_instruction', self.scene._tutorial_seen)
        self.click(self.scene.command_rects['skills'].center)
        self.assertEqual(self.model.skill_actions(), ['aqua_edge'])
        self.assertNotIn('nature_edge', self.scene.command_rects)
        self.assertNotIn('flame_edge', self.scene.command_rects)
        self.click(self.scene.command_rects['aqua_edge'].center)
        self.assertEqual(self.model.current_action.action, 'aqua_edge_attempt')
        self.scene.update(.9)
        self.acknowledge()
        self.assertEqual(self.model.spellblade_stage, 'second_edge')
        self.scene.update(0)
        self.assertEqual(self.model.current_action.action, 'aether_edge')
        self.scene.update(self.model.current_action.impact_at)
        self.assertTrue(self.model.aether_edge_discovered)
        self.assertEqual(self.model.learned_abilities, frozenset(['aether_edge']))
        self.assertEqual(self.model.player.mp, 26)


if __name__ == '__main__':
    unittest.main()
