"""The real New Game route owns its cinematic before the first checkpoint."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from main import Game
import speech_bubble


class OpeningCinematicGameplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='opening-cinematic-gameplay-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.backend = MagicMock()
        self.backend.get_busy.return_value = True
        stream = patch('pygame.mixer.music', self.backend)
        stream.start()
        self.addCleanup(stream.stop)

    def tearDown(self):
        pygame.quit()

    def game(self, *, title=True, size=(960, 640)):
        game = Game(window_size=size, fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def frame(self, game, seconds=0):
        game.update(seconds, (0, 0), False)

    def events(self, game, *events):
        for event in events:
            pygame.event.post(event)
        self.assertTrue(game.handle_events())

    def key(self, game, code, *, repeat=False):
        self.events(game, pygame.event.Event(pygame.KEYDOWN, key=code, repeat=repeat),
                    pygame.event.Event(pygame.KEYUP, key=code))

    def start(self, game):
        self.key(game, pygame.K_RETURN)
        self.frame(game, .7)
        self.assertFalse(game.on_title)
        self.assertTrue(game.opening_cinematic.active)
        self.assertEqual(game.music.desired_track, 'opening_leitmotif')
        return game.opening_cinematic

    def assert_bedroom(self, game):
        self.assertFalse(game.opening_cinematic.active)
        self.assertEqual(game.world.data['id'], 'sanctuary_bedroom')
        self.assertEqual(game.opening.stage, 'wake')
        self.assertEqual(game.social.script_identifier, 'opening_wake')
        self.assertEqual(game.social.page_index, 0)
        self.assertEqual(' '.join(game.social.page['lines']),
                         "Caelan? You're awake, aren't you?")
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertFalse(game.music.paused)

    def click_skip(self, game, *, following=()):
        game.draw()  # Layout follows the current native/display size.
        button = game.opening_cinematic.skip_rect
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = (round((width-480*scale)//2+button.centerx*scale),
                 round((height-320*scale)//2+button.centery*scale))
        self.events(game, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
                    pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point),
                    *following)

    def test_title_new_game_starts_leitmotif_and_does_not_write_a_checkpoint(self):
        game = self.game()
        self.start(game)
        self.assertFalse(self.path.exists())
        self.assertIsNone(game.saved_journey)
        self.assertNotEqual(game.opening.stage, 'wake')
        self.assertFalse(game.social.active)
        self.assertFalse(game.pause.is_open)
        self.assertEqual(self.backend.play.call_args.args, (-1,))
        self.assertTrue(str(self.backend.load.call_args.args[0]).endswith('dare_to_dream_leitmotif.ogg'))

    def test_portrait_dialogue_reuses_gameplay_art_without_starting_a_conversation(self):
        game = self.game()
        scene = self.start(game)
        before = (game.social.actor, list(game.social.pages), game.social.page_index,
                  game.social.script_identifier, set(game.social.flags))
        for speaker in ('Caelan', 'Mira'):
            record = next(record for record in scene.data['dialogue']
                          if record['speaker'] == speaker)
            scene.elapsed = record['start']+.1
            with patch.object(speech_bubble, 'draw_dialogue_frame',
                              wraps=speech_bubble.draw_dialogue_frame) as frame:
                game.draw()
            profile = game.social.data['speakers'][speaker.lower()]
            self.assertIs(frame.call_args.args[2], game.social.portraits[profile['portrait']])
            elapsed = scene.elapsed
            center = scene.caption_rect.center
            self.events(game, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                                 pos=(center[0]*2, center[1]*2)),
                        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1,
                                           pos=(center[0]*2, center[1]*2)))
            self.assertEqual(scene.elapsed, elapsed)
            self.assertFalse(game.social.active)
            self.assertEqual((game.social.actor, game.social.pages, game.social.page_index,
                              game.social.script_identifier, game.social.flags), before)
            self.assertFalse(self.path.exists())
        self.click_skip(game)
        self.assert_bedroom(game)

    def test_cinematic_freezes_world_quests_and_morning_ambience(self):
        game = self.game()
        self.start(game)
        position = game.player.position.copy()
        elapsed = game.elapsed_ms
        opening = game.opening.to_dict()
        quests = game.quests.to_dict()
        npcs = [(npc, npc.position.copy()) for npc in game.persistent_npcs]
        for _ in range(20):
            game.update(.25, (1, 1), True)
        self.assertEqual(game.player.position, position)
        self.assertEqual(game.elapsed_ms, elapsed)
        self.assertEqual(game.opening.to_dict(), opening)
        self.assertEqual(game.quests.to_dict(), quests)
        self.assertTrue(all(npc.position == original for npc, original in npcs))
        self.assertFalse(self.path.exists())
        self.assertFalse(game.save_progress())

    def test_natural_finish_starts_exact_bedroom_and_saves_only_present_facts(self):
        game = self.game()
        scene = self.start(game)
        for _ in range(int(scene.duration*2)+4):
            if not scene.active:
                break
            self.frame(game, .5)
        self.assert_bedroom(game)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['player']['scene'], 'sanctuary_bedroom')
        self.assertEqual(saved['opening'], {'version': 1, 'stage': 'wake'})
        self.assertNotIn('opening_cinematic', saved)
        self.assertNotIn('opening_leitmotif', json.dumps(saved))

    def test_skip_click_cannot_advance_wake_dialogue_or_open_pause_in_same_batch(self):
        game = self.game()
        self.start(game)
        self.click_skip(game, following=(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False),
        ))
        self.assert_bedroom(game)
        self.assertFalse(game.pause.is_open)

    def test_escape_pauses_and_resumes_scene_and_same_music_stream(self):
        game = self.game()
        scene = self.start(game)
        self.frame(game, 3)
        starts = self.backend.play.call_count
        loads = self.backend.load.call_count
        self.key(game, pygame.K_ESCAPE)
        self.assertTrue(scene.paused)
        self.assertTrue(game.music.paused)
        elapsed = scene.elapsed
        self.frame(game, 4)
        self.assertEqual(scene.elapsed, elapsed)
        self.assertFalse(game.pause.is_open)
        self.key(game, pygame.K_ESCAPE)
        self.assertFalse(scene.paused)
        self.assertFalse(game.music.paused)
        self.frame(game, .5)
        self.assertGreater(scene.elapsed, elapsed)
        self.assertEqual(self.backend.play.call_count, starts)
        self.assertEqual(self.backend.load.call_count, loads)
        self.assertGreater(self.backend.pause.call_count, 0)
        self.assertGreater(self.backend.unpause.call_count, 0)

    def test_repeated_escape_does_not_toggle_pause(self):
        game = self.game()
        scene = self.start(game)
        self.key(game, pygame.K_ESCAPE)
        self.key(game, pygame.K_ESCAPE, repeat=True)
        self.assertTrue(scene.paused)
        self.assertTrue(game.music.paused)

    def test_focus_loss_freezes_scene_and_focus_gain_preserves_manual_pause(self):
        game = self.game()
        scene = self.start(game)
        self.frame(game, 2)
        self.events(game, pygame.event.Event(pygame.WINDOWFOCUSLOST))
        elapsed = scene.elapsed
        self.frame(game, 3)
        self.assertEqual(scene.elapsed, elapsed)
        self.assertTrue(game.music.paused)
        self.events(game, pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.frame(game, .25)
        self.assertGreater(scene.elapsed, elapsed)
        self.key(game, pygame.K_ESCAPE)
        self.events(game, pygame.event.Event(pygame.WINDOWFOCUSLOST),
                    pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        elapsed = scene.elapsed
        self.frame(game, 2)
        self.assertTrue(scene.paused)
        self.assertTrue(game.music.paused)
        self.assertEqual(scene.elapsed, elapsed)

    def test_skip_is_available_while_paused_and_returns_to_unpaused_bedroom(self):
        game = self.game()
        self.start(game)
        self.key(game, pygame.K_ESCAPE)
        self.click_skip(game)
        self.assert_bedroom(game)

    def test_sky_and_helmet_shots_skip_through_the_real_event_handoff(self):
        for event in ('flare_burst', 'helmet_zoom_start'):
            with self.subTest(event=event):
                game = self.game()
                scene = self.start(game)
                scene.elapsed = scene.data['events'][event]+.1
                game.draw()
                self.key(game, pygame.K_ESCAPE)
                self.assertTrue(scene.paused)
                self.assertTrue(game.music.paused)
                self.click_skip(game, following=(pygame.event.Event(
                    pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False),))
                self.assert_bedroom(game)
                saved = json.loads(self.path.read_text())
                self.assertNotIn('opening_cinematic', saved)
                self.assertEqual(saved['opening'], {'version': 1, 'stage': 'wake'})

    def test_skip_hit_testing_tracks_resize_and_letterboxing(self):
        game = self.game()
        self.start(game)
        self.events(game, pygame.event.Event(pygame.VIDEORESIZE, w=1180, h=740))
        self.assertEqual(game.window.get_size(), (1180, 740))
        self.click_skip(game)
        self.assert_bedroom(game)

    def test_fullscreen_hotkey_remains_global_without_advancing_cinematic(self):
        game = self.game()
        scene = self.start(game)
        elapsed = scene.elapsed
        self.key(game, pygame.K_F11)
        self.assertTrue(game.fullscreen)
        self.assertTrue(scene.active)
        self.assertEqual(scene.elapsed, elapsed)
        game.draw()
        self.key(game, pygame.K_F11)
        self.assertFalse(game.fullscreen)
        self.click_skip(game)
        self.assert_bedroom(game)

    def test_gameplay_hotkeys_do_not_open_menus_during_cinematic(self):
        game = self.game()
        self.start(game)
        for code in (pygame.K_i, pygame.K_m, pygame.K_j, pygame.K_e, pygame.K_SPACE):
            self.key(game, code)
        self.assertFalse(game.map_open)
        self.assertFalse(game.quest_ui.journal_open)
        self.assertFalse(game.inventory_ui.is_open)
        self.assertFalse(game.social.active)
        self.assertTrue(game.opening_cinematic.active)

    def test_quitting_cinematic_does_not_create_a_save(self):
        game = self.game()
        self.start(game)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        self.assertFalse(self.path.exists())

    def test_quitting_new_cinematic_preserves_an_existing_journey_byte_for_byte(self):
        game = self.game()
        self.assertTrue(game.begin_journey(False, show_cinematic=False))
        before = self.path.read_bytes()
        previous = json.loads(before)
        self.assertTrue(game.begin_journey(False))
        self.frame(game, 3)
        self.assertFalse(game.save_progress())
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(game.saved_journey, previous)

    def test_continue_restores_checkpoint_without_replaying_cinematic(self):
        original = self.game()
        self.assertTrue(original.begin_journey(False, show_cinematic=False))
        game = self.game()
        game.title.selected = 1
        self.key(game, pygame.K_RETURN)
        self.frame(game, .7)
        self.assert_bedroom(game)
        self.assertNotEqual(game.music.desired_track, 'opening_leitmotif')

    def test_another_new_game_restarts_cinematic_without_overwriting_until_skip(self):
        game = self.game()
        self.start(game)
        self.click_skip(game)
        before = self.path.read_bytes()
        self.assertTrue(game.begin_journey(False))
        self.assertTrue(game.opening_cinematic.active)
        self.assertEqual(game.opening_cinematic.elapsed, 0)
        self.assertEqual(game.music.desired_track, 'opening_leitmotif')
        self.assertEqual(self.path.read_bytes(), before)
        self.click_skip(game)
        self.assert_bedroom(game)


if __name__ == '__main__':
    unittest.main()
