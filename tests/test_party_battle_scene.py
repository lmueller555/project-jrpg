"""Party command ownership, visible tells and player-paced battle guidance."""
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
from battle_scene import BattleScene, CombatSprites
from character_attributes import CharacterAttributes
from inventory import Inventory
from ui_style import Painter, UIStyle


class SpriteFixture:
    def __init__(self):
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)
        self.calls = []

    def frame(self, actor, state, elapsed_ms):
        self.calls.append((actor, state))
        return self.image, (24, 42)


class PartyBattleSceneTests(unittest.TestCase):
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
        self.sprites = SpriteFixture()
        self.make_scene()

    def tearDown(self):pygame.quit()

    def make_scene(self, tutorial=False):
        self.model = BattleModel(self.game.attributes, ['aether_dart'],
                                 guest_id='mira', enemy_id='ridgeback_tusker',
                                 rng=random.Random(4))
        self.scene = BattleScene(self.game, self.model, sprites=self.sprites,
                                 battlefield='millrace', tutorial=tutorial)
        self.draw()

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return ((point[0]-(width-480*scale)//2)/scale,
                (point[1]-(height-320*scale)//2)/scale)

    def click(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        position = (round((width-480*scale)//2+point[0]*scale),
                    round((height-320*scale)//2+point[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.scene.handle_event(pygame.event.Event(kind, button=1, pos=position))

    def key(self, key, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def make_both_ready(self):
        for member in self.model.party:member.atb = 1
        self.scene.update(0)
        self.draw()

    def test_two_character_columns_keep_independent_values_and_command_ownership(self):
        self.make_both_ready()
        self.assertEqual(set(self.scene.party_rows), {'player', 'mira'})
        player = self.scene.party_rows['player']
        guest = self.scene.party_rows['mira']
        self.assertEqual(player['column'].top, guest['column'].top)
        self.assertEqual(player['column'].width, guest['column'].width)
        self.assertLessEqual(player['column'].right, guest['column'].left)
        self.assertLessEqual(guest['column'].right, self.scene.commands_panel.left)
        self.assertFalse(player['row'].colliderect(guest['row']))
        self.assertIn('aether_dart', self.scene._command_actions())
        self.click(self.scene.party_rows['mira']['row'].center)
        self.draw()
        self.assertEqual(self.model.ready_actor, 'mira')
        self.assertNotIn('aether_dart', self.scene._command_actions())
        self.key(pygame.K_TAB)
        self.assertEqual(self.model.ready_actor, 'player')
        self.key(pygame.K_TAB)
        self.assertEqual(self.model.ready_actor, 'mira')
        self.click(self.scene.command_rects['attack'].center)
        self.assertEqual((self.model.current_action.actor, self.model.current_action.action),
                         ('mira', 'bolt_shot'))
        self.assertEqual(self.model.player.atb, 1)
        self.assertEqual(self.model.combatant('mira').atb, 0)

    def test_tutorial_waits_for_acknowledgement_without_clicking_through_to_attack(self):
        self.make_scene(tutorial=True)
        self.scene.update(20)
        self.draw()
        self.assertTrue(self.scene.tutorial_active)
        ready_actor = self.model.ready_actor
        before = (self.scene._elapsed, tuple(member.atb for member in self.model.party),
                  self.model.enemy.atb, self.model.player.hp, self.model.enemy.hp)
        self.scene.update(100)
        self.assertEqual((self.scene._elapsed, tuple(member.atb for member in self.model.party),
                          self.model.enemy.atb, self.model.player.hp, self.model.enemy.hp), before)
        self.click(self.scene.command_rects['attack'].center)
        self.assertTrue(self.scene.tutorial_active)
        self.assertIsNone(self.model.current_action)
        first = self.scene.tutorial_text
        self.key(pygame.K_RETURN, repeat=True)
        self.assertEqual(self.scene.tutorial_text, first)
        while self.scene.tutorial_active:
            self.draw();self.click(self.scene.tutorial_continue_rect.center)
        self.assertIsNone(self.model.current_action)
        self.assertEqual(self.model.phase, 'ready')
        self.assertEqual(self.model.ready_actor, ready_actor)
        self.click(self.scene.command_rects['attack'].center)
        self.assertEqual(self.model.current_action.actor, ready_actor)

    def test_real_preparation_event_identifies_guard_target_and_freezes_the_tell(self):
        self.make_scene(tutorial=True)
        self.model.enemy.atb = 1
        self.model._enemy_action_index = 1
        self.scene.update(.45)
        self.draw()
        self.assertEqual(self.model.telegraphed_target, 'player')
        self.assertIn('Caelan', self.scene.tutorial_text)
        self.assertEqual(self.scene._pose('enemy')[0], 'prepare')
        elapsed = self.model.current_action.elapsed
        self.scene.update(10)
        self.assertEqual(self.model.current_action.elapsed, elapsed)
        self.key(pygame.K_RETURN)
        self.assertFalse(self.scene.tutorial_active)
        self.scene._tutorial_event({'type': 'telegraph', 'target': 'player'})
        self.assertFalse(self.scene.tutorial_active)

    def test_focus_and_manual_pause_preserve_open_guidance(self):
        self.make_scene(tutorial=True);self.scene.update(20)
        first = self.scene.tutorial_text
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.key(pygame.K_RETURN)
        self.assertEqual(self.scene.tutorial_text, first)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.scene.paused)
        self.assertEqual(self.scene.tutorial_text, first)
        self.key(pygame.K_RETURN)
        self.assertNotEqual(self.scene.tutorial_text, first)
        self.assertIsNone(self.model.current_action)

    def test_incapacitated_guest_has_own_pose_and_does_not_end_caelans_battle(self):
        self.model.combatant('mira').hp = 1
        self.model.enemy.atb = 1
        self.scene.update(.5)
        self.assertEqual(self.model.combatant('mira').hp, 0)
        self.assertFalse(self.model.ended)
        self.assertEqual(self.scene._pose('mira')[0], 'hurt')
        self.scene.update(.18)
        self.assertEqual(self.scene._pose('mira')[0], 'defeat')
        self.assertNotEqual(self.scene._pose('player')[0], 'defeat')
        self.assertEqual(self.scene._popups[0]['target'], 'mira')

    def test_two_columns_capped_values_and_shared_commands_fit_accessible_windows(self):
        for member in self.model.party:
            member.attributes.update(hp=9999, mp=999)
            member.hp, member.mp = 9999, 999
        self.make_both_ready()
        # Large text may scroll the last command out of the initial viewport.
        # Keyboard selection must reveal that command with its wrapped label.
        while self.scene._command_actions()[self.scene.selected] != 'aether_dart':
            self.key(pygame.K_DOWN)
        original = Painter.text
        for size in ((480, 320), (960, 640), (1440, 810)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            for text_scale in (1.0, 1.5):
                records = []
                self.game.audio.set_text_scale(text_scale)

                def record(painter, text, *args, **kwargs):
                    rect = original(painter, text, *args, **kwargs)
                    records.append((str(text), rect));return rect

                with self.subTest(size=size, text_scale=text_scale):
                    with patch.object(Painter, 'text', record):self.draw()
                    self.assertFalse(any(text == 'ATB' for text, _ in records))
                    for label in ('HP 9999/9999', 'MP 999/999'):
                        self.assertEqual(sum(text == label and any(row['row'].contains(rect)
                                                                  for row in self.scene.party_rows.values())
                                             for text, rect in records), 2)
                    self.assertFalse(any(text == 'NAME' for text, _ in records))
                    for row in self.scene.party_rows.values():
                        for rect in row.values():self.assertTrue(self.scene.panel_rect.contains(rect))
                        self.assertLessEqual(row['name'].right, row['atb'].left)
                        self.assertLessEqual(abs(row['name'].centery-row['atb'].centery), 1)
                        self.assertLessEqual(row['atb'].bottom, row['hp_text'].top)
                        self.assertLessEqual(row['hp'].bottom, row['mp_text'].top)
                        self.assertLessEqual(row['mp'].bottom, row['interactable'].top)
                        for key in ('name', 'atb', 'hp_text', 'mp_text', 'hp', 'mp'):
                            self.assertTrue(row['row'].contains(row[key]), (key, row))
                        self.assertLessEqual(row['row'].bottom, row['interactable'].top)
                        self.assertGreater(row['interactable'].height, row['row'].height)
                        for bar, label in (('hp', 'hp_text'), ('mp', 'mp_text')):
                            self.assertLessEqual(row[bar].right, row[label].left)
                            self.assertLessEqual(abs(row[bar].centery-row[label].centery), 1)
                    for actor, row in self.scene.party_rows.items():
                        for label in (self.model.combatant(actor).name, 'HP 9999/9999', 'MP 999/999'):
                            rect = next(rect for text, rect in records
                                        if text == label and row['row'].contains(rect))
                            self.assertTrue(self.scene.panel_rect.contains(rect), (label, rect))
                    player = self.scene.party_rows['player']
                    guest = self.scene.party_rows['mira']
                    self.assertEqual(player['column'].width, guest['column'].width)
                    self.assertEqual(player['column'].top, guest['column'].top)
                    self.assertLessEqual(player['column'].right, guest['column'].left)
                    self.assertLessEqual(guest['column'].right, self.scene.commands_panel.left)
                    self.assertTrue(player['interactable'].contains(self.scene.gear.rect))
                    self.assertGreaterEqual(self.scene.gear.rect.width, 48)
                    self.assertEqual(self.scene.gear.rect.width, self.scene.gear.rect.height)
                    for rect in self.scene.command_rects.values():
                        self.assertTrue(self.scene.commands_panel.contains(rect))
                        self.assertFalse(any(rect.colliderect(row['row'])
                                             for row in self.scene.party_rows.values()))
                    for label, rect in records:
                        if rect.colliderect(self.scene.commands_panel):
                            self.assertTrue(self.scene.commands_panel.contains(rect),
                                            (label, rect, self.scene.commands_panel))
                    for line in self.scene._command_lines['aether_dart']:
                        self.assertTrue(any(text == line and self.scene.command_rects['aether_dart'].contains(rect)
                                            for text, rect in records))
                    self.assertLess(self.scene._positions()['player'].y, self.scene.panel_rect.top)

    def test_encounter_art_loads_lazily_and_preserves_authored_native_canvas(self):
        sprites = CombatSprites()
        self.assertEqual(set(sprites.actors), {'caelan', 'bat'})
        mira, anchor = sprites.frame('mira', 'attack', 400)
        self.assertEqual((mira.get_size(), anchor), ((64, 64), (32, 54)))
        tusker, anchor = sprites.frame('ridgeback_tusker', 'charge', 500)
        self.assertEqual((tusker.get_size(), anchor), ((96, 72), (48, 62)))
        self.assertEqual(set(sprites.actors), {'caelan', 'bat', 'mira', 'ridgeback_tusker'})

    def test_defeat_names_the_actual_safe_return_location(self):
        self.model.phase = 'defeat'
        self.assertEqual(self.scene._detail_text(), 'Return to the safe approach.')
        bat = BattleScene(self.game, BattleModel(self.game.attributes), sprites=self.sprites)
        bat.model.phase = 'defeat'
        self.assertEqual(bat._detail_text(), 'Return to Eldenmere.')


if __name__ == '__main__':unittest.main()
