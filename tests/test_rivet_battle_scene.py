"""Rivet's compact field UI and Mira's real Overclock command path."""
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
from battle_scene import BattleScene, MP_BLUE
from character_attributes import CharacterAttributes
from ui_style import MUTED, Painter, UIStyle


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


class RivetBattleSceneTests(unittest.TestCase):
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
        self.model = BattleModel(self.game.attributes, ['aether_edge', 'aether_dart'],
                                 guest_id='mira', enemy_id='ridgeback_tusker',
                                 rng=random.Random(4))
        self.sprites = FieldSprites()
        self.scene = BattleScene(self.game, self.model, sprites=self.sprites,
                                 battlefield='millrace')
        self.bot = self.model.bot_for('mira')
        self.mira = self.model.combatant('mira')
        self.draw()

    def tearDown(self):pygame.quit()

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def key(self, key, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))

    def click(self, point):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1, pos=point))

    def ready_mira(self):
        self.mira.atb = 1
        self.scene.update(0)
        self.draw()
        self.assertEqual(self.model.ready_actor, 'mira')

    def open_overclock(self):
        self.ready_mira()
        self.click(self.scene.command_rects['skills'].center)
        self.assertEqual(list(self.scene.command_rects), ['overclock', 'back'])

    def texts(self):
        records = []
        original = Painter.text

        def capture(painter, text, *args, **kwargs):
            rect = original(painter, text, *args, **kwargs)
            records.append((str(text), rect, kwargs.get('color')))
            return rect

        with patch.object(Painter, 'text', capture):self.draw()
        return records

    def resources(self):
        return (self.model.phase, tuple((member.hp, member.mp, member.atb)
                                        for member in self.model.party),
                self.model.enemy.hp, self.model.enemy.atb,
                self.bot.atb, self.bot.haste_turns)

    def test_bot_deploys_with_own_empty_atb_and_no_party_or_health_row(self):
        self.assertEqual(self.bot.atb, 0)
        self.assertFalse(hasattr(self.bot, 'hp'))
        self.assertFalse(hasattr(self.bot, 'mp'))
        self.assertEqual(set(self.scene.party_rows), {'player', 'mira'})
        self.assertEqual(set(self.scene.bot_status['rivet']), {'panel', 'name', 'atb', 'haste'})
        self.assertIn(('rivet', 'deploy'), self.sprites.calls)
        labels = [text for text, _, _ in self.texts()]
        self.assertIn('Rivet ATB', labels)
        self.assertIn('Haste · 0', labels)
        self.assertEqual(labels.count('HP'), 1)
        self.ready_mira()
        before = self.resources()
        self.click(self.scene.bot_status['rivet']['panel'].center)
        self.click(tuple(self.scene._positions()['rivet']))
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.model.ready_actor, 'mira')

    def test_bot_bar_tracks_its_gauge_independently(self):
        self.bot.atb, self.mira.atb, self.model.player.atb = .63, .23, .11
        with patch.object(BattleScene, '_bar', wraps=BattleScene._bar) as bars:
            self.draw()
        gauge = self.scene.bot_status['rivet']['atb']
        calls = [call for call in bars.call_args_list if call.args[1] == gauge]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[2], .63)

    def test_overclock_input_costs_five_mp_once_and_applies_at_impact(self):
        self.open_overclock()
        self.assertEqual(self.scene._detail_text(), '5 MP · Haste: +50% ATB for 8 bot turns.')
        original_mp = self.mira.mp
        hp = tuple(member.hp for member in self.model.party), self.model.enemy.hp
        point = self.scene.command_rects['overclock'].center
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        self.scene.handle_event(down)
        self.scene.handle_event(down)
        self.key(pygame.K_RETURN, repeat=True)
        action = self.model.current_action
        self.assertEqual((action.actor, action.action, action.target), ('mira', 'overclock', 'rivet'))
        self.assertEqual((self.mira.mp, self.mira.atb), (original_mp-5, 0))
        self.scene.update(.49)
        self.assertEqual(self.bot.haste_turns, 0)
        self.assertEqual(self.scene._pose('mira')[0], 'overclock')
        self.assertEqual(self.scene._pose('rivet')[0], 'overclock')
        self.scene.update(.01)
        self.assertEqual(self.bot.haste_turns, 8)
        self.assertEqual((tuple(member.hp for member in self.model.party), self.model.enemy.hp), hp)
        self.assertEqual(self.scene._popups[-1]['text'], 'Haste')
        self.assertIn(('Haste · 8', MP_BLUE), [(text, color) for text, _, color in self.texts()])

    def test_insufficient_mp_and_back_keep_all_resources_and_gauges_paused(self):
        self.open_overclock()
        self.mira.mp = 4
        self.bot.atb, self.bot.haste_turns = .5, 6
        before = self.resources()
        records = self.texts()
        self.assertEqual(next(color for text, _, color in records if text == 'Overclock'), MUTED)
        self.click(self.scene.command_rects['overclock'].center)
        self.assertEqual(self.scene._notice, 'Not enough MP.')
        self.scene.update(100)
        self.assertEqual(self.resources(), before)
        self.click(self.scene.command_rects['back'].center)
        self.assertEqual(self.scene.command_menu, 'root')
        self.assertEqual(self.resources(), before)

    def test_haste_counter_counts_completed_bot_actions_to_zero(self):
        self.open_overclock()
        self.click(self.scene.command_rects['overclock'].center)
        self.scene.update(.9)
        self.model.enemy.hp = 999999
        for remaining in range(8, 0, -1):
            with self.subTest(remaining=remaining):
                self.assertIn('Haste · '+str(remaining), [text for text, _, _ in self.texts()])
                for member in self.model.party:member.atb = 0
                self.model.enemy.atb = 0
                self.bot.atb = 1
                self.scene.update(0)
                self.assertEqual(self.model.current_action.actor, 'rivet')
                self.scene.update(.4)
                self.assertEqual(self.bot.haste_turns, remaining)
                self.scene.update(.4)
                self.assertEqual(self.bot.haste_turns, remaining-1)
        self.assertIn(('Haste · 0', MUTED), [(text, color) for text, _, color in self.texts()])

    def test_field_status_and_labels_fit_large_text_and_avoid_party_bodies(self):
        self.open_overclock()
        self.bot.haste_turns = 8
        for scale in (1.0, 1.5):
            self.game.audio.set_text_scale(scale)
            for menu in ('root', 'skills'):
                self.scene._set_menu(menu)
                records = self.texts()
                with self.subTest(scale=scale, menu=menu):
                    row = self.scene.bot_status['rivet']
                    self.assertTrue(self.canvas.get_rect().contains(row['panel']))
                    self.assertFalse(row['panel'].colliderect(self.scene.panel_rect))
                    for label in ('Rivet ATB', 'Haste · 8'):
                        bounds = next(rect for text, rect, _ in records if text == label)
                        self.assertTrue(row['panel'].contains(bounds), (label, row, bounds))
                    positions = self.scene._positions()
                    bodies = {}
                    for identifier, actor in (('player', 'caelan'), ('mira', 'mira'), ('rivet', 'rivet')):
                        image, anchor = self.sprites.frames[actor]
                        bounds = image.get_bounding_rect()
                        point = positions[identifier]
                        bodies[identifier] = pygame.Rect(round(point.x+(bounds.x-anchor[0])*2),
                                                        round(point.y+(bounds.y-anchor[1])*2),
                                                        bounds.width*2, bounds.height*2)
                        self.assertFalse(row['panel'].colliderect(bodies[identifier]))
                    self.assertFalse(bodies['rivet'].colliderect(bodies['mira']))
                    self.assertFalse(bodies['rivet'].colliderect(bodies['player']))
                    for text, rect, _ in records:
                        self.assertTrue(self.canvas.get_rect().contains(rect), (text, rect))

    def test_owner_ko_suspends_bot_without_health_assumptions(self):
        self.mira.hp = 0
        self.bot.atb, self.bot.haste_turns = .5, 3
        self.scene.update(0)
        self.assertEqual(self.scene._pose('rivet')[0], 'suspend')
        self.assertIsNone(self.model.active_bot('mira'))
        before = self.bot.atb, self.bot.haste_turns
        self.scene.update(.2)
        self.assertEqual((self.bot.atb, self.bot.haste_turns), before)
        self.assertIn(('Rivet ATB', MUTED), [(text, color) for text, _, color in self.texts()])

    def test_mira_fires_from_home_while_rivet_jabs_and_returns(self):
        self.ready_mira()
        home = self.scene._positions()['mira'].copy()
        self.click(self.scene.command_rects['attack'].center)
        self.scene.update(.4)
        self.assertEqual(self.model.current_action.action, 'bolt_shot')
        self.assertEqual(self.scene._positions()['mira'], home)
        self.scene.update(.4)
        for member in self.model.party:member.atb = 0
        self.model.enemy.atb = 0
        self.bot.atb = 1
        self.scene.update(0)
        home = self.scene._positions()['rivet'].copy()
        self.scene.update(.4)
        self.assertLess(self.scene._positions()['rivet'].x, home.x)
        self.scene.update(.4)
        self.assertEqual(self.scene._positions()['rivet'], home)

    def test_pause_focus_and_result_clear_bot_status_without_leaking_commands(self):
        self.open_overclock()
        before = self.resources()
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.update(100)
        self.assertEqual(self.resources(), before)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.scene.command_menu, 'skills')
        self.model.enemy.hp = 0
        self.model._result('victory')
        self.draw()
        self.assertEqual(self.scene.bot_status, {})
        self.assertEqual(self.scene._pose('rivet')[0], 'victory')
        self.assertEqual(self.scene.command_menu, 'root')


if __name__ == '__main__':unittest.main()
