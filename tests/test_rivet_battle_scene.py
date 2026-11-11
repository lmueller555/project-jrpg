"""Retired bot visuals never reappear in live Mira combat.

FieldSprites is retained here because several presentation suites share this
small renderer fixture until the phase-three asset cleanup.
"""
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
from ui_style import Painter, UIStyle


class FieldSprites:
    def __init__(self):
        self.calls = []
        self.frames = {}
        for actor, size, anchor, body in (
                ('caelan', (48, 48), (24, 42), (16, 6, 18, 36)),
                ('mira', (64, 64), (32, 54), (9, 18, 37, 36)),
                ('rivet', (32, 32), (16, 28), (4, 4, 24, 24)),
                ('ridgeback_tusker', (96, 72), (48, 62), (4, 8, 88, 54))):
            image = pygame.Surface(size, pygame.SRCALPHA)
            image.fill('#f1cd77', body)
            self.frames[actor] = image, anchor

    def frame(self, actor, state, elapsed_ms):
        self.calls.append((actor, state))
        return self.frames[actor]


class RetiredBotBattleSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((480, 320)),
            ui_surface=pygame.Surface((480, 320)), audio=AudioSettings(),
            attributes=CharacterAttributes())
        self.game.audio.set_effects(0);self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: point
        self.canvas = pygame.Surface((480, 320))
        self.model = BattleModel(self.game.attributes, guest_id='mira',
            enemy_id='ridgeback_tusker', rng=random.Random(4))
        self.sprites = FieldSprites()
        self.scene = BattleScene(self.game, self.model, sprites=self.sprites, battlefield='millrace')

    def tearDown(self):pygame.quit()

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def test_rendering_has_two_party_rows_and_no_bot_body_or_haste_text(self):
        texts = []
        original = Painter.text
        def record(painter, text, *args, **kwargs):
            texts.append(str(text));return original(painter, text, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.draw()
        self.assertEqual(set(self.scene.party_rows), {'player', 'mira'})
        self.assertFalse(any(actor == 'rivet' for actor, state in self.sprites.calls))
        self.assertFalse(any('Rivet' in text or 'Overclock' in text or 'Haste' in text for text in texts))
        self.assertEqual(sum(text.startswith('HP ') for text in texts), 2)

    def test_miras_normal_turn_draws_her_attack_without_an_independent_bot(self):
        self.model.player.atb = self.model.enemy.atb = 0
        self.model.combatant('mira').atb = 1
        self.scene.update(0)
        self.assertTrue(self.model.choose_action('attack'))
        self.scene.update(.3);self.draw()
        self.assertIn(('mira', 'attack'), self.sprites.calls)
        self.assertFalse(any(actor == 'rivet' for actor, state in self.sprites.calls))
        self.assertEqual(self.model.current_action.actor, 'mira')

    def test_pause_and_focus_loss_freeze_the_actual_character_action(self):
        self.model.combatant('mira').atb = 1;self.scene.update(0)
        self.assertTrue(self.model.choose_action('attack'))
        self.scene.update(.1)
        elapsed = self.model.current_action.elapsed
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.update(5.)
        self.assertEqual(self.model.current_action.elapsed, elapsed)
        self.assertEqual(self.model.bots, ())


if __name__ == '__main__':unittest.main()
