"""Battle status placement, resource readability and rendered gauge behavior."""
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

    def test_status_and_maximum_resource_labels_fit_on_right_at_every_scale(self):
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
                    labels = [(text, rect) for text, rect in records
                              if text.startswith(('HP ', 'MP '))]
                    self.assertEqual(len(labels), 2)
                    self.assertTrue(any('9999' in text for text, _ in labels))
                    self.assertTrue(any('999' in text for text, _ in labels))
                    for rect in (name, *(rect for _, rect in labels), self.scene.hp_rect,
                                 self.scene.mp_rect, self.scene.atb_rect):
                        self.assertGreaterEqual(rect.left, 240)
                        self.assertTrue(self.scene.panel_rect.contains(rect))
                        for command in self.scene.command_rects.values():
                            self.assertFalse(command.colliderect(rect))
                    self.assertLessEqual(name.bottom, self.scene.hp_rect.top)
                    self.assertLessEqual(self.scene.hp_rect.bottom, self.scene.mp_rect.top)
                    for text, rect in labels:
                        self.assertGreaterEqual(rect.top, name.bottom)
                        for bar in (self.scene.hp_rect, self.scene.mp_rect):
                            self.assertFalse(rect.colliderect(bar))
                    for command in self.scene.command_rects.values():
                        self.assertLessEqual(command.right, 240)
                        self.assertTrue(self.scene.panel_rect.contains(command))

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
            for text, rect in records:
                if text in ('Escaped', 'Continue', 'Try again') or text.startswith('Rewards '):
                    self.assertLessEqual(rect.right, 240)
                    self.assertTrue(self.scene.panel_rect.contains(rect))
                elif text == 'Caelan':
                    self.assertGreater(rect.left, 240)
            self.assertFalse(self.scene.continue_rect.colliderect(self.scene.hp_rect))
            self.assertFalse(self.scene.continue_rect.colliderect(self.scene.mp_rect))


if __name__ == '__main__':
    unittest.main()
