"""Compact battle table, resource readability and rendered gauge behavior."""
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
from ui_style import FOREST_DARK, GOLD, Painter, UIStyle


class EmptySprites:
    def __init__(self):
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)

    def frame(self, actor, state, elapsed_ms):
        return self.image, (24, 42)


class BattleStatusUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((480, 320)),
                                    ui_surface=pygame.Surface((480, 320)),
                                    audio=AudioSettings(), attributes=CharacterAttributes(),
                                    inventory=Inventory())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.canvas = pygame.Surface((480, 320))
        self.make_scene()

    def tearDown(self):
        pygame.quit()

    def make_scene(self):
        self.model = BattleModel(self.game.attributes, ['aether_dart'], rng=random.Random(4))
        self.scene = BattleScene(self.game, self.model, sprites=EmptySprites())
        self.draw()

    def draw(self):
        self.scene.draw(self.canvas, self.game.ui_surface)

    def row(self, rect):
        painter = self.game.ui.painter(self.game.ui_surface)
        return [self.game.ui_surface.get_at(painter.point((x, rect.centery)))[:3]
                for x in range(rect.left+1, rect.right-1)]

    def text_bounds(self):
        records = []
        original = Painter.text

        def capture(painter, text, *args, **kwargs):
            bounds = original(painter, text, *args, **kwargs)
            records.append((str(text), bounds))
            return bounds

        with patch.object(Painter, 'text', capture):
            self.draw()
        return records

    def test_health_color_changes_at_half_and_quarter_health(self):
        # 140 HP makes both threshold boundaries exact whole numbers.
        groups = {'green': [], 'yellow': [], 'red': []}
        for hp, group in ((140, 'green'), (71, 'green'), (70, 'yellow'),
                          (36, 'yellow'), (35, 'red'), (1, 'red')):
            with self.subTest(hp=hp):
                self.model.player.hp = hp
                self.draw()
                row = self.row(self.scene.hp_rect)
                color = row[0]
                red, green, blue = color
                if group == 'green':
                    self.assertGreater(green, red)
                    self.assertGreater(green, blue)
                elif group == 'yellow':
                    self.assertGreater(red, blue)
                    self.assertGreater(green, blue)
                else:
                    self.assertGreater(red, green)
                    self.assertGreater(red, blue)
                groups[group].append(color)
                self.assertLessEqual(abs(row.count(color)-len(row)*hp/140), 1)
        for colors in groups.values():
            self.assertEqual(len(set(colors)), 1)
        self.assertEqual(len({colors[0] for colors in groups.values()}), 3)

    def test_mana_is_blue_and_resource_bars_empty_at_zero(self):
        self.model.player.mp = 15
        self.draw()
        row = self.row(self.scene.mp_rect)
        blue = row[0]
        self.assertGreater(blue[2], blue[0])
        self.assertGreater(blue[2], blue[1])
        self.assertLessEqual(abs(row.count(blue)-len(row)/2), 1)

        self.model.player.hp = self.model.player.mp = 0
        self.draw()
        dark = pygame.Color(FOREST_DARK)[:3]
        self.assertEqual(set(self.row(self.scene.hp_rect)), {dark})
        self.assertEqual(set(self.row(self.scene.mp_rect)), {dark})

        # A zero MP capacity is a valid character profile, too.
        self.model.player.attributes['mp'] = 0
        self.draw()
        self.assertEqual(set(self.row(self.scene.mp_rect)), {dark})

    def test_compact_atb_stays_yellow_while_charging_and_ready(self):
        for fraction in (.25, .75, 1):
            with self.subTest(fraction=fraction):
                if fraction == 1:
                    self.scene.update(20)
                    self.assertEqual(self.model.phase, 'ready')
                self.model.player.atb = fraction
                self.draw()
                row = self.row(self.scene.atb_rect)
                yellow = pygame.Color(GOLD)[:3]
                self.assertLessEqual(abs(row.count(yellow)-len(row)*fraction), 1)
                self.assertLessEqual(self.scene.atb_rect.width, 64)
                self.assertLessEqual(self.scene.atb_rect.height, 8)
                self.assertLessEqual(self.scene.atb_rect.right, self.scene.name_rect.left)
                self.assertLessEqual(abs(self.scene.atb_rect.centery-self.scene.name_rect.centery), 1)

    def test_shared_headers_and_compact_height_show_only_actual_party_members(self):
        for learned in ((), ('aether_dart',)):
            self.model = BattleModel(self.game.attributes, learned, rng=random.Random(4))
            self.scene = BattleScene(self.game, self.model, sprites=EmptySprites())
            self.scene.update(20)
            for size in ((480, 320), (960, 640)):
                self.game.window = pygame.display.set_mode(size)
                self.game.ui_surface = pygame.Surface(size)
                self.game.audio.set_text_scale(1.0)
                with self.subTest(learned=learned, size=size):
                    records = self.text_bounds()
                    labels = [text for text, _ in records]
                    self.assertLessEqual(self.scene.panel_rect.height, 80)
                    self.assertGreaterEqual(self.scene.panel_rect.top, 232)
                    headers = []
                    for heading in ('ATB', 'NAME', 'HP', 'MP'):
                        matching = [rect for text, rect in records if text == heading]
                        self.assertEqual(len(matching), 1, heading)
                        headers.append(matching[0])
                    self.assertEqual(headers, sorted(headers, key=lambda rect: rect.left))
                    self.assertEqual(labels.count('Caelan'), 1)
                    self.assertFalse(any('ally' in text.lower() or text.upper() in ('BARRIER', 'LIMIT')
                                         for text in labels))
                    self.assertEqual(len(self.scene.command_rects), 4 if learned else 3)

    def test_status_and_maximum_resources_fit_table_columns_at_every_scale(self):
        self.assertTrue(self.game.attributes.set_modifiers('ui-test', {'hp': 9999, 'mp': 999}))
        self.assertTrue(self.game.attributes.set_current(hp=9999, mp=999))
        self.make_scene()
        self.scene.update(20)
        for size in ((480, 320), (960, 640), (1440, 810), (800, 800)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            for text_scale in (1.0, 1.5):
                with self.subTest(size=size, text_scale=text_scale):
                    self.game.audio.set_text_scale(text_scale)
                    records = self.text_bounds()
                    name = next(rect for text, rect in records if text == 'Caelan')
                    hp = next(rect for text, rect in records
                              if text.replace(' ', '') == '9999/9999')
                    mp = next(rect for text, rect in records
                              if text.replace(' ', '') == '999/999')
                    headers = {text: rect for text, rect in records
                               if text in ('ATB', 'NAME', 'HP', 'MP')}
                    for rect in (name, hp, mp, self.scene.hp_rect,
                                 self.scene.mp_rect, self.scene.atb_rect):
                        self.assertTrue(self.scene.panel_rect.contains(rect))
                        for command in self.scene.command_rects.values():
                            self.assertFalse(command.colliderect(rect))
                    self.assertLessEqual(self.scene.atb_rect.right, name.left)
                    self.assertLessEqual(name.right, hp.left)
                    self.assertLessEqual(hp.right, mp.left)
                    self.assertEqual(self.scene.hp_rect.top, self.scene.mp_rect.top)
                    for heading, value, bar in (('HP', hp, self.scene.hp_rect),
                                                ('MP', mp, self.scene.mp_rect)):
                        self.assertLessEqual(headers[heading].bottom, value.top)
                        self.assertLessEqual(value.bottom, bar.top)
                        self.assertGreaterEqual(value.left, bar.left)
                        self.assertLessEqual(value.right, bar.right)
                    commands = list(self.scene.command_rects.items())
                    for index, (identifier, command) in enumerate(commands):
                        self.assertTrue(self.scene.panel_rect.contains(command))
                        self.assertLess(command.right, self.scene.atb_rect.left)
                        if index:
                            self.assertEqual(command.left, commands[index-1][1].left)
                            self.assertGreaterEqual(command.top, commands[index-1][1].bottom)
                        label = {'attack': 'Attack', 'guard': 'Guard', 'flee': 'Flee',
                                 'aether_dart': 'Dart · 4 MP'}[identifier]
                        label_bounds = next(rect for text, rect in records if text == label)
                        self.assertTrue(command.contains(label_bounds),
                                        (label, command, label_bounds))

    def test_result_and_retry_actions_remain_on_left_with_status_visible(self):
        self.game.audio.set_text_scale(1.5)
        self.scene.update(20)
        self.assertTrue(self.model.choose_action('flee'))
        self.scene.update(1)
        self.assertEqual(self.model.phase, 'fled')
        for error in ('', 'Rewards could not be collected. Try again.'):
            self.scene.result_error = error
            records = self.text_bounds()
            self.assertLessEqual(self.scene.continue_rect.right, 240)
            self.assertTrue(self.scene.panel_rect.contains(self.scene.continue_rect))
            status = (self.scene.name_rect, self.scene.atb_rect,
                      self.scene.hp_rect, self.scene.mp_rect)
            for text, rect in records:
                if text.upper() in ('ESCAPED', 'VICTORY', 'DEFEATED') or text in ('Continue', 'Try again'):
                    self.assertLess(rect.right, self.scene.atb_rect.left)
                    self.assertTrue(self.scene.panel_rect.contains(rect))
                elif text.startswith('Rewards '):
                    self.assertTrue(self.canvas.get_rect().contains(rect))
                    self.assertTrue(all(not rect.colliderect(value) for value in status))
            self.assertFalse(self.scene.continue_rect.colliderect(self.scene.hp_rect))
            self.assertFalse(self.scene.continue_rect.colliderect(self.scene.mp_rect))

        # A compact result block must still show the complete reward, including
        # the crystal name and quantity, rather than clipping wrapped lines.
        self.make_scene()
        self.scene.update(20)
        self.model.enemy.hp = 1
        self.assertTrue(self.model.choose_action('attack'))
        self.scene.update(1)
        self.assertEqual(self.model.phase, 'victory')
        records = self.text_bounds()
        visible = ' '.join(text for text, _ in records)
        for word in ('20', 'RP', 'Aether', 'Emerald'):
            self.assertIn(word, visible)
        self.assertRegex(visible, r'×\s*1')
        for text, rect in records:
            self.assertTrue(self.canvas.get_rect().contains(rect), (text, rect))


if __name__ == '__main__':
    unittest.main()
