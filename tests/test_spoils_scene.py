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
from character_progression import CharacterProgression
from inventory import Inventory
from leveling import CharacterLevel, MAX_TOTAL_XP
from party_state import PartyState
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
        self.rewards = {'drops': {'aether_emerald': 1}}
        self.scene = SpoilsScene(self.game, self.rewards)

    def tearDown(self):pygame.quit()

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return ((point[0]-(width-480*scale)//2)/scale,
                (point[1]-(height-320*scale)//2)/scale)

    def key(self, key, *, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat))
        self.scene.handle_event(pygame.event.Event(pygame.KEYUP, key=key))

    def click(self, point, *, release=True):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        pos = (round((width-480*scale)//2+point[0]*scale),
               round((height-320*scale)//2+point[1]*scale))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        if release:
            self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))

    def draw(self):self.scene.draw(self.canvas, self.game.ui_surface)

    def progression_scene(self, amount=600, *, hp=None):
        self.game.party = PartyState(self.game.attributes)
        for identifier in ('mira', 'lucan'):self.game.party.recruit(identifier)
        self.game.character_progression = CharacterProgression(self.game.party)
        hp = hp or {'caelan': 50, 'mira': 80, 'lucan': 70}
        plan = self.game.character_progression.preview(amount, self.game.party.active_ids, hp)
        self.scene = SpoilsScene(self.game, self.rewards, progression=plan)
        return plan

    def test_pending_rewards_cannot_be_dismissed_or_granted_by_the_view(self):
        before = self.game.inventory.to_dict()
        self.draw();self.key(pygame.K_RETURN);self.click(self.scene.continue_rect.center)
        self.assertFalse(self.scene.dismissed)
        self.assertFalse(self.scene.retry_requested)
        self.assertFalse(self.scene.awarded)
        self.assertEqual(self.game.inventory.to_dict(), before)

    def test_authoritative_awards_are_snapshotted_and_continue_requires_fresh_input(self):
        self.draw();self.click(self.scene.continue_rect.center, release=False)
        actual = {'drops': {'aether_emerald': 2}}
        self.scene.set_awarded(actual)
        actual['drops']['aether_emerald'] = 50
        self.click(self.scene.continue_rect.center, release=False)
        self.assertFalse(self.scene.dismissed)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
        self.assertEqual(self.scene.rewards, {'drops': {'aether_emerald': 2}})
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
        rewards = {'drops': {key: 999999 for key in definitions}}
        self.scene = SpoilsScene(self.game, rewards)
        self.scene.set_awarded()
        for size in ((480, 320), (960, 640), (1440, 810)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            self.game.audio.set_text_scale(1.5)
            self.draw()
            self.assertGreater(self.scene.max_scroll, 0)
            self.assertLess(self.scene.title_rect.bottom, self.scene.items_view.top)
            self.assertFalse(hasattr(self.scene, 'experience_rect'))
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

    def test_zero_rewards_have_clear_item_only_empty_state(self):
        self.scene = SpoilsScene(self.game, {'drops': {}})
        self.scene.set_awarded()
        labels = []
        original = Painter.text
        def record(painter, text, *args, **kwargs):
            labels.append(str(text));return original(painter, text, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.draw()
        for label in ('Spoils of Battle', 'Items',
                      'No items recovered.', 'Continue'):
            self.assertIn(label, labels)
        self.assertFalse(any(token in label for label in labels
                             for token in ('EXP', 'Gil', 'RP', 'Resonance', 'Attunement')))
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

    def test_exp_animation_carries_over_multiple_levels_without_mutating_the_award(self):
        plan = self.progression_scene()
        before = self.game.character_progression.to_dict()
        self.scene.set_awarded()
        self.scene.update(1.2)
        for identifier in plan['active_ids']:
            displayed = self.scene.displayed_progress(identifier)
            self.assertGreater(displayed['total_xp'], 0)
            self.assertLess(displayed['total_xp'], 600)
            self.assertGreater(displayed['level'], 1)
            self.assertGreaterEqual(displayed['fill'], 0)
            self.assertLessEqual(displayed['fill'], 1)
        self.scene.update(2)
        for identifier in plan['active_ids']:
            displayed = self.scene.displayed_progress(identifier)
            self.assertEqual(displayed['total_xp'], 600)
            self.assertEqual(displayed['level'], plan['characters'][identifier]['new_level'])
        self.assertEqual(self.game.character_progression.to_dict(), before)
        self.assertEqual(self.scene.progression, plan)

    def test_confirm_finishes_bars_then_requires_fresh_acknowledgement_for_each_character(self):
        self.progression_scene()
        self.scene.set_awarded()
        self.key(pygame.K_RETURN)
        self.assertEqual(self.scene.animation_progress, 1)
        self.assertEqual(self.scene.level_up['character_id'], 'caelan')
        self.assertFalse(self.scene.dismissed)
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        self.assertEqual(self.scene.level_up['character_id'], 'mira')
        # A second synthetic key-down without a release cannot consume Lucan.
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        self.assertEqual(self.scene.level_up['character_id'], 'mira')
        self.scene.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))
        self.key(pygame.K_RETURN)
        self.assertEqual(self.scene.level_up['character_id'], 'lucan')
        self.key(pygame.K_RETURN)
        self.assertIsNone(self.scene.level_up)
        self.assertTrue(self.scene.presentation_complete)
        self.assertFalse(self.scene.dismissed)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.scene.dismissed)

    def test_level_up_sound_is_once_per_character_and_reward_retries_do_not_replay_it(self):
        self.progression_scene()
        with patch('spoils_audio.SpoilsAudio') as audio:
            self.scene.set_awarded()
            self.scene.finish_animation()
            self.assertEqual(audio.return_value.level_up.call_count, 1)
            self.scene.update(1)
            self.scene.set_error('Save failed.')
            self.scene.set_awarded()
            self.assertEqual(audio.return_value.level_up.call_count, 1)
            self.key(pygame.K_RETURN)
            self.assertEqual(audio.return_value.level_up.call_count, 2)

    def test_ko_and_max_level_cards_do_not_animate_or_open_growth_sheets(self):
        self.progression_scene(hp={'caelan': 0, 'mira': 40, 'lucan': 20})
        progress = self.game.character_progression
        progress.records['mira'] = CharacterLevel('mira', MAX_TOTAL_XP)
        progress.records['lucan'] = CharacterLevel('lucan', MAX_TOTAL_XP)
        plan = progress.preview(600, self.game.party.active_ids,
                                {'caelan': 0, 'mira': 40, 'lucan': 20})
        self.scene = SpoilsScene(self.game, self.rewards, progression=plan)
        self.scene.set_awarded()
        self.assertEqual(self.scene.animation_progress, 1)
        self.assertTrue(self.scene.presentation_complete)
        labels = []
        original = Painter.text
        def record(painter, text, *args, **kwargs):
            labels.append(str(text));return original(painter, text, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.draw()
        self.assertIn('KO — No EXP', labels)
        self.assertIn('MAX LEVEL', labels)
        self.assertIsNone(self.scene.level_up)

    def test_growth_sheet_black_before_green_after_and_scrolls_all_eleven_attributes(self):
        plan = self.progression_scene()
        self.scene.set_awarded();self.scene.finish_animation()
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.game.audio.set_text_scale(1.5)
        labels = []
        original = Painter.text
        def record(painter, text, *args, **kwargs):
            labels.append((str(text), kwargs.get('color')))
            return original(painter, text, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.draw()
        self.assertGreater(self.scene.stat_max_scroll, 0)
        self.assertIn((format(plan['characters']['caelan']['stats_before']['hp'], ','), '#000000'), labels)
        self.assertIn((format(plan['characters']['caelan']['stats_after']['hp'], ','), '#176b37'), labels)
        self.key(pygame.K_END)
        with patch.object(Painter, 'text', record):self.draw()
        self.assertEqual(self.scene.stat_scroll, self.scene.stat_max_scroll)
        self.assertIn(('Lck', '#302c24'), labels)
        self.assertFalse(self.scene.stat_view.colliderect(self.scene.level_continue_rect))

    def test_reduced_motion_skips_fill_but_preserves_level_up_acknowledgements(self):
        self.game.audio.reduced_motion = True
        self.progression_scene()
        self.scene.set_awarded()
        self.assertEqual(self.scene.animation_progress, 1)
        self.assertIsNotNone(self.scene.level_up)
        self.assertFalse(self.scene.presentation_complete)
        self.assertFalse(self.scene.dismissed)

    def test_item_cap_and_description_remain_visible_separately_from_exp(self):
        self.progression_scene(amount=60)
        self.scene.loot = {'offered': {'aether_emerald': 3},
                           'received': {'aether_emerald': 1}, 'lost': {'aether_emerald': 2}}
        self.scene.set_awarded();self.scene.finish_animation()
        labels = []
        original = Painter.text
        def record(painter, text, *args, **kwargs):
            labels.append(str(text));return original(painter, text, *args, **kwargs)
        with patch.object(Painter, 'text', record):self.draw()
        self.assertIn('2 lost: bag full', labels)
        self.key(pygame.K_TAB)
        self.assertEqual(self.scene._hovered_item, 'aether_emerald')
        self.draw()
        self.assertFalse(self.scene.dismissed)


if __name__ == '__main__':unittest.main()
