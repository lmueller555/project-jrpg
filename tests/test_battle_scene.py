"""Real battle UI input, wait-ATB display and responsive scene rendering."""
import os
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel
from battle_scene import BattleScene
from character_attributes import CharacterAttributes
from inventory import Inventory
from ui_style import UIStyle, Painter


class SpriteFixture:
    def __init__(self):
        self.surface = pygame.Surface((48, 48), pygame.SRCALPHA)
        self.surface.fill((0, 0, 0, 0))
        pygame.draw.rect(self.surface, '#d8c49b', (14, 6, 20, 36))
        self.calls = []

    def frame(self, actor, state, elapsed_ms):
        self.calls.append((actor, state, elapsed_ms))
        return self.surface, (24, 42)


class BattleSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    ui_surface=pygame.Surface((960, 640)),
                                    audio=AudioSettings(), attributes=CharacterAttributes(),
                                    inventory=Inventory())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = self.to_canvas
        self.canvas = pygame.Surface((480, 320))
        self.model = BattleModel(self.game.attributes, rng=random.Random(4))
        self.sprites = SpriteFixture()
        self.scene = BattleScene(self.game, self.model, sprites=self.sprites)
        self.draw()

    def tearDown(self):pygame.quit()

    def point(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return round((width-480*scale)//2+logical[0]*scale), round((height-320*scale)//2+logical[1]*scale)

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        value = ((point[0]-(width-480*scale)//2)/scale,
                 (point[1]-(height-320*scale)//2)/scale)
        return value if 0 <= value[0] < 480 and 0 <= value[1] < 320 else None

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def key(self, key, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))

    def click(self, point):
        pos = self.point(point)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1, pos=pos))

    def ready(self):
        self.scene.update(20)
        self.assertEqual(self.model.phase, 'ready')
        self.draw()

    def test_player_choice_leaves_every_gauge_and_resource_unchanged(self):
        self.ready()
        before = (self.model.player.atb, self.model.enemy.atb,
                  self.model.player.hp, self.model.enemy.hp)
        self.scene.update(100)
        self.assertEqual((self.model.player.atb, self.model.enemy.atb,
                          self.model.player.hp, self.model.enemy.hp), before)
        self.assertEqual(self.model.phase, 'ready')

    def test_enemy_atb_is_not_read_or_drawn_by_the_view(self):
        actual = self.model.enemy

        class EnemyWithoutVisibleGauge:
            def __getattr__(self, key):
                if key == 'atb':raise AssertionError('The view exposed an enemy gauge')
                return getattr(actual, key)

        self.model.enemy = EnemyWithoutVisibleGauge()
        with patch.object(Painter, 'text', autospec=True, wraps=Painter.text) as text:
            self.draw()
        labels = [call.args[1] for call in text.call_args_list]
        self.assertEqual(labels.count('ATB'), 1)
        self.assertNotIn('Enemy ATB', labels)

    def test_charging_clicks_and_keys_cannot_submit_an_action(self):
        self.click(self.scene.command_rects['attack'].center)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.model.phase, 'charging')
        self.assertIsNone(self.model.current_action)

    def test_real_command_click_starts_one_action_without_touching_world_attributes(self):
        original = self.game.attributes.to_dict()
        self.ready()
        pos = self.point(self.scene.command_rects['attack'].center)
        press = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
        self.scene.handle_event(press)
        action = self.model.current_action
        self.assertEqual((action.actor, action.action), ('player', 'attack'))
        for _ in range(3):self.scene.handle_event(press)
        self.assertIs(self.model.current_action, action)
        self.scene.update(.4)
        self.assertLess(self.model.enemy.hp, self.model.enemy.max_hp)
        self.assertEqual(self.game.attributes.to_dict(), original)
        self.assertFalse(self.scene.dismissed)

    def test_command_keyboard_and_repeats_are_gated_by_readiness(self):
        self.ready()
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN, repeat=True)
        self.assertEqual(self.model.phase, 'ready')
        self.key(pygame.K_RETURN)
        self.assertEqual(self.model.current_action.action, 'guard')
        self.assertEqual(self.model.phase, 'acting')

    def test_learned_spell_is_displayed_but_insufficient_mp_never_spends_a_turn(self):
        self.model = BattleModel(self.game.attributes, ['aether_dart'], rng=random.Random(4))
        self.model.player.mp = 3
        self.scene = BattleScene(self.game, self.model, sprites=self.sprites)
        self.ready()
        before = self.model.player.atb, self.model.player.mp
        self.click(self.scene.command_rects['aether_dart'].center)
        self.assertEqual(self.model.phase, 'ready')
        self.assertEqual((self.model.player.atb, self.model.player.mp), before)
        self.assertEqual(self.scene._notice, 'Not enough MP.')

    def test_focus_loss_and_manual_pause_freeze_model_and_visual_time(self):
        self.scene.update(1)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        before = self.model.player.atb, self.model.enemy.atb, self.scene._elapsed
        self.scene.update(10)
        self.assertEqual((self.model.player.atb, self.model.enemy.atb, self.scene._elapsed), before)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.scene.paused)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(self.scene.paused)
        self.click(self.scene.resume_rect.center)
        self.assertFalse(self.scene.paused)
        self.scene.update(1)
        self.assertGreater(self.model.player.atb, before[0])
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.scene.paused)

    def test_terminal_results_wait_for_an_explicit_continue(self):
        self.ready()
        self.click(self.scene.command_rects['flee'].center)
        self.scene.update(1)
        self.assertEqual(self.model.phase, 'fled')
        self.assertFalse(self.scene.dismissed)
        self.draw()
        self.click((10, 10))
        self.assertFalse(self.scene.dismissed)
        self.click(self.scene.continue_rect.center)
        self.assertTrue(self.scene.dismissed)

    def test_result_retry_message_preserves_resources_and_outcome(self):
        self.ready();self.model.enemy.hp = 1
        self.click(self.scene.command_rects['attack'].center)
        self.scene.update(1)
        self.assertEqual(self.model.phase, 'victory')
        self.scene.result_error = 'Rewards could not be collected. Try again.'
        with patch.object(Painter, 'text', autospec=True, wraps=Painter.text) as text:
            self.draw()
        self.assertIn('Try again', [call.args[1] for call in text.call_args_list])
        self.assertFalse(self.scene.dismissed)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.scene.dismissed)

    def test_physical_approach_and_hurt_frames_follow_the_action(self):
        self.ready()
        self.click(self.scene.command_rects['attack'].center)
        self.scene.update(.18)
        self.assertLess(self.scene._positions()['player'].x, 354)
        self.sprites.calls.clear();self.draw()
        self.assertTrue(any(actor == 'caelan' and state == 'attack' for actor, state, _ in self.sprites.calls))
        self.scene.update(.19)
        self.sprites.calls.clear();self.draw()
        self.assertTrue(any(actor == 'bat' and state == 'hurt' for actor, state, _ in self.sprites.calls))

    def test_reduced_motion_keeps_staging_still_but_displays_attack_poses(self):
        self.game.audio.set_reduced_motion(True)
        self.ready();self.click(self.scene.command_rects['attack'].center)
        self.scene.update(.18)
        self.assertEqual(self.scene._positions()['player'], pygame.Vector2(354, 184))
        self.assertEqual(self.scene._positions()['enemy'], pygame.Vector2(126, 170))
        self.sprites.calls.clear();self.draw()
        self.assertIn('attack', [state for _, state, _ in self.sprites.calls])

    def test_status_commands_and_results_fit_scaled_letterboxed_large_text_windows(self):
        self.model = BattleModel(self.game.attributes, ['aether_dart'], rng=random.Random(4))
        self.scene = BattleScene(self.game, self.model, sprites=self.sprites)
        self.ready()
        for size in ((480, 320), (960, 640), (1440, 810), (800, 800)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            for text_scale in (1.0, 1.5):
                with self.subTest(size=size, text_scale=text_scale):
                    self.game.audio.set_text_scale(text_scale)
                    labels = {}
                    original = Painter.text

                    def capture(painter, text, *args, **kwargs):
                        bounds = original(painter, text, *args, **kwargs)
                        labels.setdefault(str(text), []).append(bounds)
                        return bounds

                    with patch.object(Painter, 'text', capture):
                        self.draw()
                    for rect in (*self.scene.command_rects.values(), self.scene.atb_rect,
                                 self.scene.continue_rect):
                        self.assertTrue(self.scene.panel_rect.contains(rect))
                    for identifier, rect in self.scene.command_rects.items():
                        label = {'attack': 'Attack', 'guard': 'Guard', 'flee': 'Flee',
                                 'aether_dart': 'Dart · 4 MP'}[identifier]
                        self.assertEqual(len(labels[label]), 1)
                        self.assertTrue(rect.contains(labels[label][0]),
                                        (label, rect, labels[label][0]))
                    self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())
        self.click(self.scene.command_rects['flee'].center);self.scene.update(1);self.draw()
        self.assertEqual(self.model.phase, 'fled')
        self.assertTrue(self.scene.panel_rect.contains(self.scene.continue_rect))


if __name__ == '__main__':unittest.main()
