"""The title's real replay route cannot become a persistent journey."""
import copy
import gc
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
from cutscene_gallery import GALLERY_ENTRIES
from main import Game
from save_game import SaveStore


class GallerySessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='gallery-session-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'
        self.settings_path = Path(self.directory.name)/'settings.json'
        self.backend = MagicMock()
        self.backend.get_busy.return_value = True
        stream = patch('pygame.mixer.music', self.backend)
        stream.start();self.addCleanup(stream.stop)
        self.games = []

    def tearDown(self):
        for game in self.games:
            if game.gallery_session is not None:game.gallery_session.close()
            game.opening_audio.reset();game.regional_audio.reset();game.music.stop()
        self.games.clear()
        pygame.quit()
        gc.collect()

    def game(self, *, title=True):
        game = Game(fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.settings_path)
        game.audio.effects_volume = 0
        self.games.append(game)
        pygame.event.clear()
        return game

    def saved_payload(self, *, legacy=False):
        seed = self.game(title=False)
        self.assertTrue(seed.save_progress())
        payload = json.loads(self.path.read_text())
        if legacy:
            payload = {key: payload[key] for key in (
                'version', 'quests', 'dialogue_flags', 'player', 'exterior_position')}
            self.path.write_text(json.dumps(payload, indent=1)+'\n', encoding='utf-8')
        seed.music.stop()
        return payload

    def key(self, game, key, *following, repeat=False):
        events = [pygame.event.Event(pygame.KEYDOWN, key=key, repeat=repeat),
                  pygame.event.Event(pygame.KEYUP, key=key), *following]
        for event in events:pygame.event.post(event)
        return game.handle_events()

    def launch(self, game, identifier='later_journey'):
        self.assertTrue(game.open_gallery())
        self.assertTrue(game.launch_gallery_scene(identifier))
        self.assertIsNotNone(game.gallery_session)
        return game.gallery_session

    def snapshot(self, game):
        return {
            'world': id(game.world),
            'overworld': id(game._overworld_world),
            'scene_cache': tuple((str(path), id(scene)) for path, scene in game.scenes.items()),
            'position': tuple(game.player.position),
            'clock': game.elapsed_ms,
            'progress': game._progress_signature(),
            'saved': copy.deepcopy(game.saved_journey),
            'actors': tuple((str(path), tuple((id(actor), tuple(actor.position),
                            tuple(actor.blocker) if hasattr(actor, 'blocker') else None)
                            for actor in scene.npcs))
                            for path, scene in game.scenes.items()),
        }

    def finish(self, game, maximum=2500):
        for _ in range(maximum):
            session = game.gallery_session
            if session is None:return
            child = session.game
            if child.social.active or child.regent_arrival.dialogue is not None and child.regent_arrival.active:
                self.assertTrue(self.key(game, pygame.K_SPACE))
            game.update(.1, (1, 0), True)
        self.fail('Preview did not return to the catalogue')

    def test_catalogue_opening_freezes_world_and_creates_no_save(self):
        game = self.game()
        before = self.snapshot(game)
        self.assertTrue(game.open_gallery())
        game.update(5, (1, 1), True)
        game.draw()
        self.assertTrue(game.on_title)
        self.assertTrue(game.on_gallery)
        self.assertEqual(self.snapshot(game), before)
        self.assertFalse(self.path.exists())
        self.assertFalse(self.settings_path.exists())
        self.assertFalse(game.save_progress())

    def test_current_save_settings_and_continue_survive_different_previews(self):
        payload = self.saved_payload()
        settings = dict(version=1, music_volume=.4, effects_volume=.2,
                        last_music=.4, last_effects=.2, text_scale=1.25,
                        reduced_motion=True, tracker_visible=False)
        self.settings_path.write_text(json.dumps(settings, indent=3)+'\n', encoding='utf-8')
        saved_bytes = self.path.read_bytes();settings_bytes = self.settings_path.read_bytes()
        game = self.game();before = self.snapshot(game)
        for entry in GALLERY_ENTRIES:
            with self.subTest(entry=entry.id):
                session = self.launch(game, entry.id)
                self.assertIsNot(session.game.audio, game.audio)
                self.assertEqual(session.game.audio.to_dict(), game.audio.to_dict())
                self.assertFalse(session.game.audio.store.enabled)
                game.update(.05)
                self.assertTrue(self.key(game, pygame.K_ESCAPE))
                self.assertEqual(self.snapshot(game), before)
                self.assertEqual(self.path.read_bytes(), saved_bytes)
                self.assertEqual(self.settings_path.read_bytes(), settings_bytes)
                del session
                gc.collect()
        game.close_gallery()
        self.assertTrue(game.begin_journey(True))
        self.assertEqual(game.world.data['id'], payload['player']['scene'])
        self.assertEqual(list(game.player.position), payload['player']['position'])
        self.assertEqual(game.quests.to_dict(), payload['quests'])
        self.assertFalse(game.opening_cinematic.active)

    def test_legacy_save_remains_byte_identical_until_normal_continue(self):
        payload = self.saved_payload(legacy=True)
        raw = self.path.read_bytes()
        game = self.game()
        self.assertTrue(game.has_saved_journey)
        self.launch(game, 'mill_small_spell')
        self.finish(game)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertEqual(game.saved_journey, payload)
        game.close_gallery()
        self.assertTrue(game.begin_journey(True))
        self.assertEqual(game.quests.to_dict(), payload['quests'])
        self.assertEqual(game.world.data['id'], payload['player']['scene'])

    def test_invalid_save_is_not_replaced_by_preview_or_quit(self):
        raw = b'{old journey interrupted before closing brace\n'
        self.path.write_bytes(raw)
        game = self.game();error = game.save_error
        self.assertFalse(game.has_saved_journey)
        self.launch(game, 'morning_wake')
        self.finish(game)
        self.assertEqual(game.save_error, error)
        self.assertEqual(self.path.read_bytes(), raw)
        self.launch(game)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        self.assertFalse(game.save_progress())
        self.assertEqual(self.path.read_bytes(), raw)

    def test_preview_save_guard_holds_even_if_store_is_accidentally_enabled(self):
        game = self.game()
        session = self.launch(game, 'morning_wake')
        child = session.game
        self.assertTrue(child._is_gallery_preview)
        self.assertFalse(child.save_store.enabled)
        child.save_store = SaveStore(self.path)
        with patch.object(child.save_store, 'write', wraps=child.save_store.write) as write:
            self.assertFalse(child.save_progress())
            game.update(.2)
            write.assert_not_called()
        self.assertFalse(self.path.exists())
        self.assertIsNone(game.saved_journey)

    def test_staged_completion_cannot_leak_props_actors_rewards_or_flags(self):
        game = self.game();before = self.snapshot(game)
        session = self.launch(game, 'lantern_finishing')
        self.assertIsNot(session.game.town, game.town)
        self.assertIsNot(session.game.inventory, game.inventory)
        self.assertIsNot(session.game.social, game.social)
        self.finish(game)
        self.assertTrue(game.on_gallery)
        self.assertEqual(self.snapshot(game), before)
        self.assertFalse(self.path.exists())

    def test_restart_constructs_fresh_world_and_preserves_selected_entry(self):
        game = self.game()
        first = self.launch(game)
        game.update(8)
        old_world = first.game.town
        self.assertGreater(first.game.opening_cinematic.elapsed, 0)
        self.assertTrue(self.key(game, pygame.K_r))
        second = game.gallery_session
        self.assertIsNot(second, first)
        self.assertIsNot(second.game.town, old_world)
        self.assertEqual(second.entry.id, first.entry.id)
        self.assertEqual(second.game.opening_cinematic.elapsed, 0)
        self.assertFalse(first.game.opening_cinematic.active)
        first.close()  # An obsolete owner must not stop the replacement stream.
        self.assertTrue(second.game.music._owns_stream())
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertIsNone(game.gallery_session)
        self.assertFalse(self.path.exists())

    def test_escape_consumes_same_batch_and_does_not_launch_again(self):
        game = self.game()
        self.launch(game)
        enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False)
        self.assertTrue(self.key(game, pygame.K_ESCAPE, enter, enter))
        self.assertIsNone(game.gallery_session)
        self.assertTrue(game.on_gallery)
        self.assertEqual(game.title.fade, 0)
        self.assertFalse(game.pause.is_open)
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertFalse(game.on_gallery)
        self.assertTrue(game.on_title)

    def test_title_gallery_and_back_transitions_consume_same_batch(self):
        game = self.game()
        game.title.selected = game.title.options.index('Gallery')
        enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False)
        self.assertTrue(self.key(game, pygame.K_RETURN, enter))
        self.assertTrue(game.on_gallery)
        self.assertIsNone(game.gallery_session)
        self.assertTrue(self.key(game, pygame.K_ESCAPE, enter))
        self.assertFalse(game.on_gallery)
        self.assertTrue(game.on_title)
        self.assertIsNone(game.gallery_session)
        self.assertEqual(game.title.fade, 0)

    def test_production_skip_returns_without_starting_the_opening_morning(self):
        game = self.game();before = self.snapshot(game)
        session = self.launch(game)
        game.draw()
        child = session.game
        point = child.opening_cinematic.skip_rect.center
        scale, _, origin = child._ensure_ui_surface()
        screen = (round(origin[0]+point[0]*scale)+session.viewport_rect.x,
                  round(origin[1]+point[1]*scale)+session.viewport_rect.y)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=screen))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False))
        self.assertTrue(game.handle_events())
        game.update(.7)
        self.assertIsNone(game.gallery_session)
        self.assertFalse(child.social.active)
        self.assertNotEqual(child.opening.stage, 'wake')
        self.assertEqual(self.snapshot(game), before)
        self.assertFalse(self.path.exists())

    def test_natural_completion_keeps_gallery_selection_and_scroll(self):
        game = self.game()
        self.assertTrue(game.open_gallery())
        game.gallery.selected = 10
        game.gallery.scroll = 170
        self.assertTrue(game.launch_gallery_scene('later_journey'))
        session = game.gallery_session
        for _ in range(int(session.game.opening_cinematic.duration)+3):
            if game.gallery_session is None:break
            game.update(1)
        self.assertIsNone(game.gallery_session)
        self.assertEqual(game.gallery.selected, 10)
        self.assertEqual(game.gallery.scroll, 170)
        self.assertTrue(game.on_gallery)

    def test_dialogue_advances_once_per_input_batch_without_world_menu_access(self):
        game = self.game()
        child = self.launch(game, 'morning_wake').game
        self.assertTrue(child.social.active)
        before = child.social.page_index
        events = [pygame.event.Event(pygame.KEYDOWN, key=code, repeat=False)
                  for code in (pygame.K_SPACE, pygame.K_e, pygame.K_SPACE)]
        for event in events:pygame.event.post(event)
        self.assertTrue(game.handle_events())
        self.assertEqual(child.social.page_index, before+1)
        for key in (pygame.K_i, pygame.K_m, pygame.K_j, pygame.K_w):
            self.assertTrue(self.key(game, key))
        self.assertFalse(child.inventory_ui.is_open)
        self.assertFalse(child.quest_ui.journal_open)
        self.assertFalse(child.map_open)
        self.assertFalse(child.pause.is_open)

    def test_two_e_presses_on_final_grain_dialogue_page_cannot_start_world_interaction(self):
        game = self.game();before = self.snapshot(game)
        session = self.launch(game, 'grain_extra_sack')
        child = session.game
        farm = child.world.grain_farm
        self.assertEqual(child.social.script_identifier, 'grain_farm_extra_sack')
        for _ in range(100):
            game.draw()
            if child.social.page_index == len(child.social.pages)-1:break
            self.assertTrue(self.key(game, pygame.K_SPACE))
        else:self.fail('The production grain exchange never reached its final page')
        self.assertTrue(child.social.active)
        self.assertFalse(farm.state['exchange_read'])
        second_press = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False)
        with patch.object(child.overworld_travel, 'interact',
                          wraps=child.overworld_travel.interact) as interact:
            self.assertTrue(self.key(game, pygame.K_e, second_press))
            # Both inputs belong to the conversation visible at batch start.
            # Its first acknowledgement closes it; the second must not fall
            # through to a nearby worker's ordinary greeting.
            interact.assert_not_called()
        self.assertFalse(child.social.active)
        self.assertNotEqual(child.social.script_identifier, 'grain_farm_greeting')
        self.assertTrue(farm.state['exchange_read'])
        self.assertEqual(farm.stage, 'help_approach')
        self.finish(game)
        self.assertTrue(session.playback.finished)
        self.assertTrue(farm.state['scene_done'])
        self.assertIsNone(game.gallery.error)
        self.assertEqual(self.snapshot(game), before)
        self.assertFalse(self.path.exists())

    def test_every_registered_scene_completes_with_rendered_dialogue_and_real_input(self):
        game = self.game();before = self.snapshot(game)
        for entry in GALLERY_ENTRIES:
            with self.subTest(entry=entry.id):
                session = self.launch(game, entry.id)
                child = session.game
                for frame in range(4000):
                    # Render and acknowledge through the actual fractional
                    # preview viewport. Reflowing against a different input
                    # canvas previously reset long dialogue to the same page.
                    if frame % 3 == 0:
                        game.draw()
                        if game.gallery_session is None:break
                        if child.social.active or child.regent_arrival.active:
                            self.assertTrue(self.key(game, pygame.K_SPACE))
                    game.update(.1)
                    if game.gallery_session is None:break
                self.assertIsNone(game.gallery_session,
                                  'Rendered dialogue and input must agree on page layout')
                self.assertIsNone(game.gallery.error)
                self.assertTrue(session.playback.finished)
                self.assertTrue(session.closed)
                self.assertEqual(self.snapshot(game), before)
                self.assertFalse(self.path.exists())
                del session, child
                gc.collect()

    def test_preview_never_ticks_incidental_world_encounters(self):
        game = self.game()
        child = self.launch(game, 'morning_wake').game
        with patch.object(child.combat, 'tick_world') as encounter:
            game.update(.1, (1, 1), True)
            encounter.assert_not_called()
        self.assertFalse(child.combat.active)

    def test_focus_and_music_ownership_return_to_title_after_exit(self):
        game = self.game()
        child = self.launch(game).game
        self.assertTrue(child.music._owns_stream())
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(game.handle_events());game.update(.1)
        self.assertFalse(game._music_focused)
        self.assertTrue(child.music.paused)
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertTrue(game.music._owns_stream())
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertTrue(game.music.paused)
        self.assertFalse(child.music._owns_stream())
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(game.handle_events());game.update(.1)
        self.assertFalse(game.music.paused)

    def test_cinematic_pause_key_uses_production_pause_without_exiting(self):
        game = self.game()
        child = self.launch(game).game
        game.update(3)
        elapsed = child.opening_cinematic.elapsed
        self.assertTrue(self.key(game, pygame.K_p))
        self.assertTrue(child.opening_cinematic.paused)
        self.assertTrue(child.music.paused)
        game.update(4)
        self.assertEqual(child.opening_cinematic.elapsed, elapsed)
        self.assertTrue(self.key(game, pygame.K_p, repeat=True))
        self.assertTrue(child.opening_cinematic.paused)
        self.assertTrue(self.key(game, pygame.K_p))
        self.assertFalse(child.opening_cinematic.paused)
        game.update(.25)
        self.assertGreater(child.opening_cinematic.elapsed, elapsed)
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertIsNone(game.gallery_session)

    def test_world_scene_focus_loss_pauses_music_and_morning_ambience(self):
        game = self.game()
        session = self.launch(game, 'morning_wake')
        child = session.game
        game.update(.1)
        clock = child.elapsed_ms
        page = child.social.page_index
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False))
        with patch.object(session.playback, '_drive') as drive:
            self.assertTrue(game.handle_events());game.update(2)
            drive.assert_not_called()
        self.assertTrue(child.music.paused)
        self.assertTrue(child.opening_audio._paused)
        self.assertEqual(child.elapsed_ms, clock)
        self.assertEqual(child.social.page_index, page)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertTrue(game.handle_events());game.update(.1)
        self.assertFalse(child.music.paused)
        self.assertFalse(child.opening_audio._paused)
        self.assertGreater(child.elapsed_ms, clock)

    def test_toolbar_click_restart_and_back_follow_scaled_hit_targets(self):
        game = self.game()
        first = self.launch(game)
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, w=800, h=800))
        self.assertTrue(game.handle_events());game.draw()
        point = first._painter().point(first.restart_rect.center)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(game.handle_events())
        second = game.gallery_session
        self.assertIsNot(second, first)
        game.draw()
        point = second._painter().point(second.back_rect.center)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(game.handle_events())
        self.assertIsNone(game.gallery_session)
        self.assertTrue(game.on_gallery)

    def test_fullscreen_toggle_remains_with_parent_after_preview(self):
        game = self.game()
        child = self.launch(game).game
        self.assertTrue(self.key(game, pygame.K_F11))
        self.assertTrue(game.fullscreen)
        self.assertTrue(child.fullscreen)
        self.assertIsNot(child.window, game.window)
        self.assertEqual(child.window.get_size(), game.gallery_session.viewport_rect.size)
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertTrue(game.fullscreen)
        with patch('pygame.display.set_mode', wraps=pygame.display.set_mode) as mode:
            self.assertTrue(self.key(game, pygame.K_F11))
            mode.assert_called_once_with((960, 640), pygame.RESIZABLE)
        self.assertFalse(game.fullscreen)
        # SDL dummy retains its desktop surface after fullscreen; verify the
        # actual requested restoration as the existing display tests do.
        self.assertEqual(game.windowed_size, (960, 640))

    def test_resize_updates_preview_and_parent_without_replacing_journey(self):
        game = self.game();before = self.snapshot(game)
        child = self.launch(game).game
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, w=1100, h=750))
        self.assertTrue(game.handle_events());game.draw()
        self.assertEqual(game.window.get_size(), (1100, 750))
        self.assertIsNot(child.window, game.window)
        self.assertEqual(child.window.get_size(), game.gallery_session.viewport_rect.size)
        self.assertTrue(self.key(game, pygame.K_ESCAPE));game.draw()
        self.assertEqual(game.window.get_size(), (1100, 750))
        self.assertEqual(self.snapshot(game), before)

    def test_reserved_toolbar_and_scene_input_fit_small_wide_and_tall_windows(self):
        game = self.game();game.audio.text_scale = 1.5
        for size in ((960, 640), (480, 320), (1920, 810), (800, 800)):
            with self.subTest(size=size):
                game.window = pygame.display.set_mode(size, pygame.RESIZABLE)
                session = self.launch(game)
                game.draw()
                child = session.game
                self.assertTrue(game.window.get_rect().contains(session.viewport_rect))
                self.assertGreaterEqual(session.viewport_rect.top,
                                        session._painter().area(session.bar_rect).bottom)
                scale, pixels, origin = child._ensure_ui_surface()
                self.assertTrue(child.window.get_rect().contains(pygame.Rect(origin, pixels)))
                point = child.opening_cinematic.skip_rect.center
                local = (round(origin[0]+point[0]*scale), round(origin[1]+point[1]*scale))
                recovered = child.to_canvas(local)
                self.assertLess(pygame.Vector2(recovered).distance_to(point), 2)
                screen = (local[0]+session.viewport_rect.x, local[1]+session.viewport_rect.y)
                for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    pygame.event.post(pygame.event.Event(kind, button=1, pos=screen))
                self.assertTrue(game.handle_events())
                game.update(.7)
                self.assertIsNone(game.gallery_session)
                del session, child
                gc.collect()

    def test_arrival_audio_and_controller_resources_are_released(self):
        game = self.game()
        game.audio.effects_volume = 1
        child = self.launch(game, 'regent_arrival').game
        game.update(.2)
        owned = list(child.regent_arrival.audio.channels)
        self.assertTrue(owned, 'The actual dummy mixer must receive arrival cues')
        with patch.object(child.regent_arrival.audio, 'stop', wraps=child.regent_arrival.audio.stop) as stop:
            self.assertTrue(self.key(game, pygame.K_ESCAPE))
            stop.assert_called()
        self.assertFalse(child.regent_arrival.active)
        self.assertEqual(child.regent_arrival.audio.channels, [])
        self.assertEqual(child.opening_audio._channels, [])
        self.assertEqual(child.opening_audio._fading_channels, [])
        self.assertEqual(child.regional_audio.voices, {})
        self.assertTrue(all(channel.get_sound() is not sound or not channel.get_busy()
                            for channel, sound in owned))
        self.assertTrue(game.music._owns_stream())

    def test_regional_previews_release_owned_voices_without_stopping_other_audio(self):
        game = self.game();game.audio.effects_volume = 1
        before = self.snapshot(game)
        for identifier in ('grain_extra_sack', 'bridge_tea', 'garden_quiet_care'):
            with self.subTest(entry=identifier):
                child = self.launch(game, identifier).game
                sentinel = pygame.mixer.Sound(buffer=bytes(4096))
                unrelated = sentinel.play(loops=-1)
                self.assertIsNotNone(unrelated)
                try:
                    # Grain's dialogue station is intentionally outside the
                    # ambience radius. Its first sound is the real sack contact.
                    for _ in range(300):
                        if child.social.active:self.assertTrue(self.key(game, pygame.K_SPACE))
                        game.update(.1)
                        if child.regional_audio.voices or game.gallery_session is None:break
                    self.assertIsNotNone(child._overworld_world)
                    self.assertTrue(child.regional_audio.voices,
                                    'The actual dummy mixer must receive a regional voice')
                    owned = [(channel, sound) for _, channel, sound, _
                             in child.regional_audio.voices.values()]
                    self.assertTrue(self.key(game, pygame.K_ESCAPE))
                    self.assertEqual(child.regional_audio.voices, {})
                    self.assertEqual(child.regional_audio.cooldowns, {})
                    self.assertTrue(all(channel.get_sound() is not sound or not channel.get_busy()
                                        for channel, sound in owned))
                    self.assertIs(unrelated.get_sound(), sentinel)
                    self.assertTrue(unrelated.get_busy())
                    self.assertTrue(game.music._owns_stream())
                    self.assertEqual(self.snapshot(game), before)
                finally:
                    sentinel.stop()
                    if game.gallery_session is not None:game.gallery_session.close()
                del child
                gc.collect()

    def test_quit_during_preview_closes_audio_without_saving(self):
        game = self.game()
        child = self.launch(game, 'morning_wake').game
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(game.handle_events())
        self.assertIsNone(game.gallery_session)
        self.assertFalse(game.save_progress())
        self.assertFalse(child.music._owns_stream())
        self.assertFalse(game.music.playing)
        self.assertEqual(child.opening_audio._channels, [])
        self.assertFalse(self.path.exists())

    def test_unknown_entry_and_nested_launch_leave_existing_session_intact(self):
        game = self.game()
        self.assertTrue(game.open_gallery())
        self.assertFalse(game.launch_gallery_scene('unwritten_future_scene'))
        self.assertIsNone(game.gallery_session)
        self.assertTrue(game.launch_gallery_scene('later_journey'))
        current = game.gallery_session
        self.assertFalse(game.launch_gallery_scene('morning_wake'))
        self.assertIs(game.gallery_session, current)

    def test_failed_scene_start_returns_to_usable_gallery_and_parent_music(self):
        game = self.game();before = self.snapshot(game)
        self.assertTrue(game.open_gallery())
        with patch('cutscene_gallery.GalleryEntry.start', side_effect=ValueError('Missing scene asset')):
            self.assertFalse(game.launch_gallery_scene('later_journey'))
        self.assertIsNone(game.gallery_session)
        self.assertIn('Missing scene asset', game.gallery.error)
        self.assertEqual(self.snapshot(game), before)
        self.assertTrue(game.music._owns_stream())
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertTrue(game.launch_gallery_scene('later_journey'))
        self.assertTrue(self.key(game, pygame.K_ESCAPE))
        self.assertFalse(self.path.exists())

    def test_missing_arrival_layer_during_draw_restores_gallery_and_saved_journey(self):
        self.saved_payload()
        saved_bytes = self.path.read_bytes()
        game = self.game();before = self.snapshot(game)
        session = self.launch(game, 'regent_arrival')
        child = session.game
        with patch.object(child.regent_arrival, '_load', side_effect=FileNotFoundError('Missing arrival layer')):
            game.draw()
        self.assertTrue(session.closed)
        self.assertIsNone(game.gallery_session)
        self.assertTrue(game.on_gallery)
        self.assertIn('Missing arrival layer', game.gallery.error)
        self.assertTrue(game.music._owns_stream())
        self.assertEqual(game.music.desired_track, 'eldenmere')
        self.assertFalse(child.music._owns_stream())
        self.assertEqual(child.regent_arrival.audio.channels, [])
        self.assertEqual(self.path.read_bytes(), saved_bytes)
        self.assertEqual(self.snapshot(game), before)


if __name__ == '__main__':unittest.main()
