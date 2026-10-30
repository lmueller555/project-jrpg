"""Victory celebration and a distinct, accessible rewards view."""
import os
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
from spoils_scene import SpoilsScene
from ui_style import Painter, UIStyle


class SpoilsSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    ui_surface=pygame.Surface((960, 640)),
                                    audio=AudioSettings(), inventory=Inventory(),
                                    attributes=CharacterAttributes())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = self.to_canvas
        self.canvas = pygame.Surface((480, 320))
        self.rewards = {'rp': 30, 'drops': {'aether_emerald': 1}}
        self.scene = SpoilsScene(self.game, self.rewards)

    def tearDown(self):pygame.quit()

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return ((point[0]-(width-480*scale)//2)/scale,
                (point[1]-(height-320*scale)//2)/scale)

    def key(self, key, *, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))

    def click(self, point, *, release=True):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        pos = (round((width-480*scale)//2+point[0]*scale),
               round((height-320*scale)//2+point[1]*scale))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        if release:
            self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def test_pending_rewards_cannot_be_dismissed_or_granted_by_the_view(self):
        before = self.game.inventory.to_dict()
        self.draw();self.key(pygame.K_RETURN);self.click(self.scene.continue_rect.center)
        self.assertFalse(self.scene.dismissed)
        self.assertFalse(self.scene.retry_requested)
        self.assertFalse(self.scene.awarded)
        self.assertEqual(self.game.inventory.to_dict(), before)

    def test_authoritative_awards_are_snapshotted_and_continue_requires_fresh_input(self):
        self.draw();self.click(self.scene.continue_rect.center, release=False)
        actual = {'rp': 12, 'drops': {'aether_emerald': 2}}
        self.scene.set_awarded(actual)
        actual['drops']['aether_emerald'] = 50
        self.click(self.scene.continue_rect.center, release=False)
        self.assertFalse(self.scene.dismissed)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
        self.assertEqual(self.scene.rewards, {'rp': 12, 'drops': {'aether_emerald': 2}})
        self.key(pygame.K_RETURN, repeat=True)
        self.assertFalse(self.scene.dismissed)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.scene.dismissed)

    def test_retry_requests_an_owner_operation_without_leaving_the_screen(self):
        self.scene.set_error('Rewards could not be collected. Please retry.')
        self.draw();self.click(self.scene.retry_rect.center)
        self.assertTrue(self.scene.retry_requested)
        self.assertFalse(self.scene.dismissed)
        self.scene.set_pending()
        self.assertFalse(self.scene.retry_requested)
        self.assertFalse(self.scene.result_error)
        self.key(pygame.K_SPACE)
        self.assertFalse(self.scene.dismissed)
        self.scene.set_awarded()
        self.key(pygame.K_SPACE)
        self.assertTrue(self.scene.dismissed)

    def test_focus_and_escape_pause_preserve_the_awarded_screen(self):
        self.scene.set_awarded();self.scene.update(.25)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.key(pygame.K_RETURN);self.scene.update(10)
        self.assertFalse(self.scene.dismissed)
        self.assertEqual(self.scene._elapsed, .25)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.key(pygame.K_SPACE)
        self.assertFalse(self.scene.dismissed)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.scene.paused)
        self.assertFalse(self.scene.dismissed)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.scene.dismissed)

    def test_long_item_lists_scroll_without_covering_title_or_continue(self):
        definitions = self.game.inventory.definitions
        for index in range(18):
            definitions['test_item_'+str(index)] = {'name': 'A carefully wrapped keepsake with a very long name '+str(index)}
        rewards = {'rp': 999999, 'drops': {key: 999999 for key in definitions}}
        self.scene = SpoilsScene(self.game, rewards)
        self.scene.set_awarded()
        for size in ((480, 320), (960, 640), (1440, 810)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            self.game.audio.set_text_scale(1.5)
            self.draw()
            self.assertGreater(self.scene.max_scroll, 0)
            self.assertLess(self.scene.title_rect.bottom, self.scene.experience_rect.top)
            self.assertLess(self.scene.experience_rect.bottom, self.scene.items_view.top)
            self.assertLess(self.scene.items_view.bottom, self.scene.continue_rect.bottom)
            self.assertTrue(self.scene.panel_rect.contains(self.scene.continue_rect))
            first = set(self.scene.item_rects)
            self.key(pygame.K_END);self.draw()
            self.assertEqual(self.scene.scroll, self.scene.max_scroll)
            self.assertNotEqual(set(self.scene.item_rects), first)
            self.assertTrue(all(self.scene.items_view.contains(rect) for rect in self.scene.item_rects.values()))
            self.key(pygame.K_HOME);self.draw()
            self.assertEqual(self.scene.scroll, 0)
            self.scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-3))
            self.assertGreater(self.scene.scroll, 0)

    def test_zero_rewards_have_a_clear_empty_state_and_existing_progression_name(self):
        self.scene = SpoilsScene(self.game, {'rp': 0, 'drops': {}})
        self.scene.set_awarded()
        labels = []
        original = Painter.text
        def record(painter, text, *args, **kwargs):
            labels.append(str(text));return original(painter, text, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.draw()
        for label in ('Spoils of Battle', 'Resonance Points (RP)', 'Caelan', '+0 RP',
                      'No items recovered.', 'Rewards received.', 'Continue'):
            self.assertIn(label, labels)
        self.assertFalse(any('EXP' in label or 'Gil' in label for label in labels))
        self.key(pygame.K_RETURN)
        self.assertTrue(self.scene.dismissed)

    def test_victory_banner_has_no_in_battle_rewards_or_exit_command(self):
        model = BattleModel(self.game.attributes)
        self.scene = BattleScene(self.game, model)
        model.phase = 'victory';model.enemy.hp = 0
        labels = []
        original = Painter.text
        def record(painter, text, *args, **kwargs):
            labels.append(str(text));return original(painter, text, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.draw()
        self.assertIn('VICTORY', labels)
        self.assertFalse(any('RP' in label or 'Emerald' in label or label == 'Continue' for label in labels))
        self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(self.scene.victory_banner_rect))
        self.key(pygame.K_RETURN);self.click(self.scene.continue_rect.center)
        self.assertFalse(self.scene.dismissed)
        model.phase = 'fled';self.draw();self.key(pygame.K_RETURN)
        self.assertTrue(self.scene.dismissed)


if __name__ == '__main__':unittest.main()
