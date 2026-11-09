"""Actual title-to-quest input, normal gameplay, and disposable session safety."""
import copy
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from main import Game
from quest_playtest import QUEST_ORDER


class QuestPlaytestSessionTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name)/'journey.json'
        self.settings = Path(folder.name)/'settings.json'
        self.parent = Game(window_size=(960, 640), fullscreen=False,
                           save_path=self.path, settings_path=self.settings)
        self.parent.audio.set_music(0)
        self.parent.audio.set_effects(0)
        pygame.event.clear()

    def tearDown(self):
        if self.parent.quest_playtest_session is not None:
            self.parent.quest_playtest_session.close()
        self.parent.opening_audio.reset()
        self.parent.regional_audio.reset()
        self.parent.music.stop()
        pygame.quit()

    def key(self, key, *following, repeat=False):
        return self.parent.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat),
            pygame.event.Event(pygame.KEYUP, key=key), *following])

    def click(self, point):
        return self.parent.handle_events([
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)])

    def launch(self, identifier='CH01_MQ02'):
        self.assertTrue(self.parent.open_quest_playtests())
        self.assertTrue(self.parent.launch_quest_playtest(identifier),
                        self.parent.quest_playtest_menu.error)
        return self.parent.quest_playtest_session

    def snapshot(self):
        return (self.parent._progress_signature(), self.parent.elapsed_ms,
                tuple(self.parent.player.position), id(self.parent.world),
                copy.deepcopy(self.parent.saved_journey),
                self.path.read_bytes() if self.path.exists() else None,
                self.settings.read_bytes() if self.settings.exists() else None)

    def game_point(self, session, logical):
        scale, _, origin = session.game._ensure_ui_surface()
        return (round(session.viewport_rect.x+origin[0]+logical[0]*scale),
                round(session.viewport_rect.y+origin[1]+logical[1]*scale))

    def tick(self, seconds=.05):
        self.parent.update(seconds, (0, 0), False)

    def read(self, session, limit=1200):
        game = session.game
        for _ in range(limit):
            if game.mill_gift.active:
                self.key(pygame.K_SPACE)
            elif game.social.active:
                if game.social.choosing:
                    self.parent.draw()
                    self.click(self.game_point(session, game.social.choice_rects[0].center))
                else:
                    self.key(pygame.K_SPACE)
            elif not game.mill_quest.encounter_cutscene_active:
                return
            self.tick()
        self.fail(('Dialogue did not finish', game.social.script_identifier))

    def test_title_button_and_catalogue_work_without_a_save_and_discard_input_tail(self):
        self.parent.title.selected = self.parent.title.quest_playtest_index
        self.key(pygame.K_RETURN,
                 pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False))
        self.assertTrue(self.parent.on_title)
        self.assertTrue(self.parent.on_quest_playtest)
        self.assertIsNone(self.parent.quest_playtest_session)
        self.assertFalse(self.parent.has_saved_journey)
        self.parent.draw()
        self.key(pygame.K_END)
        self.assertEqual(self.parent.quest_playtest_menu.selected_entry.id, 'CH01_MQ04')
        self.key(pygame.K_KP_ENTER,
                 pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False))
        session = self.parent.quest_playtest_session
        self.assertIsNotNone(session)
        self.assertEqual(session.game.quests.status('CH01_MQ04'), 'available')
        self.assertFalse(session.game.social.active)
        self.key(pygame.K_F9)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.parent.on_quest_playtest)
        self.assertEqual(self.parent.title.selected, self.parent.title.quest_playtest_index)

    def test_all_starts_keep_parent_memory_save_and_settings_untouched(self):
        for saved in (False, True):
            with self.subTest(saved=saved):
                if saved:
                    self.parent.on_title = False
                    self.assertTrue(self.parent.save_progress())
                    self.parent.on_title = True
                before = self.snapshot()
                for identifier in QUEST_ORDER:
                    session = self.launch(identifier)
                    self.assertIsNot(session.game.world, self.parent.world)
                    self.assertIsNot(session.game.audio, self.parent.audio)
                    self.assertIsNot(session.game.quests, self.parent.quests)
                    self.tick(.2)
                    self.parent.draw()
                    session.game.audio.set_text_scale(1.5)
                    session.game.audio.set_music(.3)
                    session.game.save_progress()
                    self.key(pygame.K_F9)
                    self.assertEqual(self.snapshot(), before)
                    self.assertEqual(self.parent.has_saved_journey, saved)

    def test_each_opening_can_be_accepted_through_normal_gameplay(self):
        for identifier in QUEST_ORDER:
            with self.subTest(quest=identifier):
                session = self.launch(identifier)
                game = session.game
                for _ in range(10):
                    self.tick()
                if identifier == 'CH01_MQ01':
                    for _ in range(30):
                        self.parent.update(.05, (0, -1), False)
                        if game.social.active:
                            break
                elif identifier == 'CH01_MQ03':
                    self.parent.draw()
                    self.click(self.game_point(session, game.regent_arrival.skip_rect.center))
                    self.assertFalse(game.regent_arrival.active)
                    serene = game.regent_quest.serene
                    for offset in ((0, 22), (0, 16), (-16, 0), (16, 0)):
                        point = serene.position+offset
                        if game.world.can_stand(point):
                            game.player.position.update(point)
                            break
                    self.key(pygame.K_e)
                else:
                    self.key(pygame.K_e)
                self.assertTrue(game.social.active, identifier)
                self.read(session)
                self.assertEqual(game.quests.status(identifier), 'active')
                self.assertIsNone(game.save_error)
                self.key(pygame.K_F9)

    def test_normal_movement_encounters_hud_and_menus_are_not_gallery_restricted(self):
        session = self.launch()
        game = session.game
        self.assertFalse(game._is_gallery_preview)
        before = game.player.position.copy()
        with patch.object(game.combat, 'tick_world', wraps=game.combat.tick_world) as tick_world:
            self.parent.update(.1, (-1, 0), False)
            tick_world.assert_called()
        self.assertNotEqual(game.player.position, before)
        with patch.object(game.quest_ui, 'draw_tracker', wraps=game.quest_ui.draw_tracker) as tracker:
            self.parent.draw()
            tracker.assert_called_once()
        for key, check in (
                (pygame.K_i, lambda: game.inventory_ui.is_open),
                (pygame.K_j, lambda: game.quest_ui.journal_open),
                (pygame.K_m, lambda: game.map_open)):
            self.key(key)
            self.assertTrue(check())
            self.parent.draw()
            self.key(pygame.K_ESCAPE)
            self.assertFalse(check())
        self.key(pygame.K_ESCAPE)
        self.assertTrue(game.pause.is_open)
        self.parent.draw()

    def test_restart_discards_progress_and_does_not_forward_event_tail(self):
        session = self.launch()
        before = session.game._progress_signature()
        self.assertTrue(session.game.accept_quest('CH01_MQ02'))
        self.key(pygame.K_F10,
                 pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False))
        replacement = self.parent.quest_playtest_session
        self.assertIsNot(replacement, session)
        self.assertTrue(session.closed)
        self.assertEqual(replacement.game._progress_signature(), before)
        self.assertFalse(replacement.game.social.active)
        self.key(pygame.K_F10, repeat=True)
        self.assertIs(self.parent.quest_playtest_session, replacement)
        self.key(pygame.K_F9, repeat=True)
        self.assertIs(self.parent.quest_playtest_session, replacement)

    def test_pause_restart_and_quest_list_actions_do_not_quit_the_app(self):
        session = self.launch()
        self.key(pygame.K_ESCAPE)
        session.game.pause.selected = session.game.pause.options.index('Restart Quest')
        self.key(pygame.K_RETURN)
        other = self.parent.quest_playtest_session
        self.assertIsNot(other, session)
        self.assertTrue(session.closed)
        self.key(pygame.K_ESCAPE)
        other.game.pause.selected = other.game.pause.options.index('Quest List')
        self.assertTrue(self.key(pygame.K_RETURN))
        self.assertIsNone(self.parent.quest_playtest_session)
        self.assertTrue(self.parent.on_quest_playtest)
        self.assertTrue(self.parent.on_title)

    def test_real_battle_and_victory_rewards_work_without_a_save_file(self):
        before = self.snapshot()
        session = self.launch('CH01_MQ04')
        game = session.game
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.camera.reset()
        self.assertTrue(game.combat.interact(random.Random(7)))
        scene = game.combat.scene
        for _ in range(3000):
            if scene.model.ended:
                break
            if scene.model.waiting_for_player:
                self.parent.draw()
                self.assertIn('attack', scene.command_rects)
                self.click(self.game_point(session, scene.command_rects['attack'].center))
            else:
                self.tick(.1)
        self.assertEqual(scene.model.phase, 'victory')
        for _ in range(200):
            if game.combat.spoils is not None and game.combat.spoils.awarded:
                break
            self.tick(.05)
        self.assertIsNotNone(game.combat.spoils)
        self.assertTrue(game.combat.spoils.awarded, scene.result_error)
        self.assertTrue(game.battle_rewards.has_receipt(game.combat.receipt_id))
        self.parent.draw()
        self.key(pygame.K_F10)
        self.assertTrue(session.closed)
        self.assertFalse(self.parent.quest_playtest_session.game.combat.active)
        self.key(pygame.K_F9)
        self.assertEqual(self.snapshot(), before)

    def test_fullscreen_is_host_owned_and_playtest_can_return_after_resizing(self):
        session = self.launch()
        with patch.object(self.parent, 'toggle_fullscreen', wraps=self.parent.toggle_fullscreen) as toggle:
            self.key(pygame.K_F11)
            toggle.assert_called_once_with()
        self.assertEqual(session.game.fullscreen, self.parent.fullscreen)
        self.assertEqual(session.game.window.get_size(), session.viewport_rect.size)
        self.parent.draw()
        self.key(pygame.K_F11)
        self.key(pygame.K_F9)
        self.assertTrue(self.parent.on_quest_playtest)
        self.parent.draw()

    def test_pause_display_setting_uses_the_host_display_instead_of_replacing_it(self):
        session = self.launch()
        game = session.game
        self.key(pygame.K_ESCAPE)
        game.pause.selected = game.pause.settings_index
        self.key(pygame.K_RETURN)
        self.assertTrue(game.pause.settings)
        game.pause.selected = 0
        with patch.object(self.parent, 'toggle_fullscreen', wraps=self.parent.toggle_fullscreen) as toggle:
            self.key(pygame.K_RETURN)
            toggle.assert_called_once_with()
        self.assertEqual(game.fullscreen, self.parent.fullscreen)
        self.assertEqual(game.window.get_size(), session.viewport_rect.size)
        self.parent.draw()

    def test_scaled_pause_mouse_input_and_settings_work_below_the_toolbar(self):
        session = self.launch()
        for size in ((480, 320), (1100, 750)):
            self.parent.handle_events([pygame.event.Event(pygame.VIDEORESIZE, w=size[0], h=size[1])])
            game = session.game
            game.audio.set_text_scale(1.5)
            self.key(pygame.K_ESCAPE)
            for _ in range(game.pause.settings_index):
                self.key(pygame.K_DOWN)
            self.parent.draw()
            point = self.game_point(session, game.pause.rows[game.pause.settings_index].center)
            self.click(point)
            self.assertTrue(game.pause.settings)
            self.parent.draw()
            game.pause.selected = 1
            before = self.parent.audio.music_volume
            self.key(pygame.K_RIGHT)
            self.assertEqual(self.parent.audio.music_volume, before)
            self.key(pygame.K_ESCAPE)
            self.key(pygame.K_ESCAPE)
            self.assertFalse(game.pause.is_open)
            self.assertEqual(game._input_offset, session.viewport_rect.topleft)

    def test_toolbar_restart_and_return_buttons_consume_clicks(self):
        session = self.launch('CH01_MQ03')
        self.parent.draw()
        self.click(session._painter().point(session.restart_rect.center))
        other = self.parent.quest_playtest_session
        self.assertTrue(session.closed)
        self.assertTrue(other.game.regent_arrival.active)
        self.click(other._painter().point(other.back_rect.center))
        self.assertTrue(other.closed)
        self.assertIsNone(self.parent.quest_playtest_session)

    def test_focus_loss_freezes_playtest_and_blocks_restart_until_refocused(self):
        session = self.launch()
        self.parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        before = session.game.elapsed_ms
        self.parent.update(4, (1, 0), True)
        self.assertEqual(session.game.elapsed_ms, before)
        self.key(pygame.K_F10)
        self.assertIs(self.parent.quest_playtest_session, session)
        self.parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.parent.update(.2, (-1, 0), False)
        self.assertGreater(session.game.elapsed_ms, before)

    def test_missing_start_and_runtime_failure_return_to_a_readable_selector(self):
        self.parent.open_quest_playtests()
        before = self.snapshot()
        with patch('quest_playtest_session.prepare_quest', side_effect=ValueError('bad start')):
            self.assertFalse(self.parent.launch_quest_playtest('CH01_MQ02'))
        self.assertIsNone(self.parent.quest_playtest_session)
        self.assertIn('bad start', self.parent.quest_playtest_menu.error)
        self.assertEqual(self.snapshot(), before)
        self.parent.draw()
        self.key(pygame.K_ESCAPE)
        session = self.launch()
        with patch.object(session.game, 'update', side_effect=ValueError('bad world')):
            self.tick()
        self.assertTrue(session.closed)
        self.assertIsNone(self.parent.quest_playtest_session)
        self.assertIn('bad world', self.parent.quest_playtest_menu.error)
        self.parent.draw()
        self.assertFalse(self.parent.launch_quest_playtest('unknown'))
        self.assertIn('Unsupported', self.parent.quest_playtest_menu.error)

    def test_selector_accessible_layout_no_thumbnails_and_no_changes_to_normal_menus(self):
        self.parent.open_quest_playtests()
        menu = self.parent.quest_playtest_menu
        for size in ((480, 320), (1280, 720)):
            self.parent.window = pygame.display.set_mode(size)
            for scale in (1, 1.25, 1.5):
                self.parent.audio.set_text_scale(scale)
                menu._select(3)
                with patch.object(menu, '_thumbnail', side_effect=AssertionError('no quest thumbnails')):
                    self.parent.draw()
                self.assertGreaterEqual(menu.rows[3].clip(menu.viewport).height, 30)
                self.assertLessEqual(menu.viewport.bottom+7, menu.play_rect.top)
                self.assertFalse(menu.play_rect.colliderect(menu.back_rect))
        self.parent.close_quest_playtests()
        self.assertNotIn('Quest List', self.parent.pause.options)
        self.assertNotIn('Restart Quest', self.parent.pause.options)
        self.assertTrue(self.parent.open_gallery())
        self.parent.draw()
        self.parent.close_gallery()
        self.parent.draw()

    def test_quit_closes_session_without_creating_a_journey(self):
        session = self.launch('CH01_MQ04')
        self.assertFalse(self.parent.handle_events([pygame.event.Event(pygame.QUIT)]))
        self.assertTrue(session.closed)
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
