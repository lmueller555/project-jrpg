"""Physical staging, modal input and checkpoint contracts for the polished morning."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import main
import test_opening_gameplay as opening_helpers
from quests import OPENING_QUEST


class PolishedOpeningTests(unittest.TestCase):
    def setUp(self):
        self.h = opening_helpers.OpeningGameplayTests('test_new_game_wakes_in_bedroom_and_gates_quest_until_breakfast')
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def tearDown(self):
        pygame.quit()

    def tick_until(self, game, predicate, *, advance=True, limit=2400):
        for _ in range(limit):
            if predicate():
                return
            if advance and game.social.scripted:
                self.h.key(game, pygame.K_SPACE)
            game.update(1/60, (0, 0), False)
        self.fail(('Scene did not reach expected beat', game.opening.stage,
                   game.opening.action_name, game.opening._phase))

    @staticmethod
    def furnishings(game):
        room = game._scene_by_id('sanctuary_dining')
        positions = {e['id']: tuple(e['position']) for e in room.entities
                     if e['id'] in ('chair_west', 'chair_east', 'table')}
        return positions, pygame.mask.Mask.copy(room.blocked)

    def test_fast_reading_preserves_every_action_and_fixed_furniture(self):
        game = self.h.new_game()
        positions, mask = self.furnishings(game)
        self.assertEqual(positions['chair_west'], (120, 174))
        self.assertEqual(positions['chair_east'], (192, 174))
        actions = []
        cues = []
        visible = []
        original_update = game.update
        original_drain = game.opening.drain_sound_events

        def drain():
            result = original_drain()
            cues.extend(result)
            return result

        def update(*args, **kwargs):
            original_update(*args, **kwargs)
            action = game.opening.action_name
            if action and (not actions or actions[-1] != action):
                actions.append(action)
            position = getattr(game.player, 'story_position', None) or game.player.position
            if getattr(game.player, 'story_visible', True):
                visible.append((game.world.data['id'], action, tuple(position)))
            current, current_mask = self.furnishings(game)
            self.assertEqual(current, positions)
            self.assertEqual(current_mask.count(), mask.count())
            self.assertEqual(current_mask.overlap_area(mask, (0, 0)), mask.count())

        game.update = update
        with patch.object(game.opening, 'drain_sound_events', side_effect=drain):
            self.h.enter_breakfast(game)
            self.assertEqual(game.social.script_identifier, 'opening_greeting')
            self.assertFalse(hasattr(game.player, 'story_sprite'))
            self.h.finish_breakfast(game)
        for required in ('wake_up', 'walk_to_breakfast', 'sit', 'plate', 'eat', 'cup', 'stand'):
            self.assertIn(required, actions)
        indices = [actions.index(name) for name in ('wake_up', 'walk_to_breakfast', 'sit', 'plate', 'eat', 'cup', 'stand')]
        self.assertEqual(indices, sorted(indices))
        for cue in ('bedsheet', 'chair', 'plate', 'bite', 'cup', 'footstep'):
            self.assertIn(cue, cues)
        for previous, current in zip(visible, visible[1:]):
            # Both action interiors and their pose-family handoffs stay bounded.
            # Real doorway transfers are intentional cuts between different rooms.
            if previous[0] == current[0]:
                self.assertLessEqual(pygame.Vector2(previous[2]).distance_to(current[2]), 4.0,
                                     (previous, current))
        self.assertFalse(game.opening.in_action)
        self.assertFalse(game.opening.locks_player)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')
        self.assertEqual(game.quests.states[OPENING_QUEST]['completed_objectives'], [])

    def test_camera_keeps_full_world_view_when_prose_finishes_before_actions(self):
        game = self.h.new_game()
        self.h.enter_breakfast(game)
        game.update(.4, (0, 0), False)
        self.tick_until(game, lambda: game.opening.action_name == 'eat')
        # Finish the short seated lines before the visible eating motion ends.
        while game.social.scripted:
            self.h.key(game, pygame.K_SPACE)
        self.assertEqual(game.opening.stage, 'breakfast')
        self.assertTrue(game.opening.locks_player)
        self.assertFalse(game.social.locked)
        game.update(1/60, (0, 0), False)
        # Camera follows the physical player pose rather than reserving a
        # lower panel; dialogue completion itself cannot change the viewport.
        self.assertEqual(game.camera.framing_height, 320)
        self.h.finish_breakfast(game)
        previous = game.camera.position()
        game.update(1/60, (0, 0), False)
        self.assertLessEqual(abs(game.camera.position()[1]-previous[1]), 20)
        game.update(.5, (0, 0), False)
        self.assertGreater(game.camera.framing_height, 310)

    def test_steering_leaves_unread_breakfast_after_cup_and_stand_without_clicks(self):
        game = self.h.new_game()
        self.h.enter_breakfast(game)
        self.tick_until(game, lambda: game.social.script_identifier == 'opening_breakfast')
        # Leave both meal and cup prose unread. Held movement must complete
        # physical gestures and restore normal walking without further clicks.
        actions = set()
        displayed = set()
        previous = pygame.Vector2(getattr(game.player, 'story_position', None) or game.player.position)
        for _ in range(600):
            actions.add(game.opening.action_name)
            displayed.add(game.social.script_identifier)
            game.update(1/60, (0, 1), False)
            current = pygame.Vector2(getattr(game.player, 'story_position', None) or game.player.position)
            self.assertLessEqual(current.distance_to(previous), 4.0)
            previous = current
            if game.opening.stage == 'assignment' and game.player.moving:
                break
        else:
            self.fail('Unread seated dialogue trapped player movement')
        self.assertTrue({'plate', 'eat', 'cup', 'stand'} <= actions)
        self.assertTrue({'opening_breakfast', 'opening_kindness'} <= displayed)
        self.assertFalse(game.social.locked)
        self.assertFalse(game.opening.locks_player)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')

    def test_single_movement_tap_also_finishes_standing_after_unread_breakfast(self):
        game = self.h.new_game()
        self.h.enter_breakfast(game)
        self.tick_until(game, lambda: game.social.script_identifier == 'opening_breakfast')
        game.update(1/60, (0, 1), False)
        for _ in range(600):
            if game.opening.stage == 'assignment':break
            game.update(1/60, (0, 0), False)
        self.assertEqual(game.opening.stage, 'assignment')
        self.assertFalse(game.social.locked)
        self.assertFalse(game.opening.locks_player)
        self.assertFalse(hasattr(game.player, 'story_position'))
        self.assertTrue(game.world.can_stand(game.player.position))

    def test_pause_freezes_getup_sitting_and_eating_and_resume_does_not_advance(self):
        game = self.h.new_game()
        for beat in ('wake_up', 'sit', 'eat'):
            if beat == 'sit':
                self.tick_until(game, lambda: game.opening.stage == 'explore')
                self.h.walk_to(game, (144, 306), new_scene='sanctuary_hall')
                self.h.walk_to(game, (264, 78), new_scene='sanctuary_dining')
            self.tick_until(game, lambda: game.opening.action_name == beat)
            self.h.key(game, pygame.K_ESCAPE)
            self.assertTrue(game.pause.is_open)
            game.update(0, (0, 0), False)
            def snapshot():
                return (game.elapsed_ms, game.opening.stage, game.opening.action_name,
                        game.opening._action_time, tuple(game.player.position),
                        tuple(getattr(game.player, 'story_position', ())),
                        game.social.page_index, game.camera.position(),
                        game.camera.framing_height, game.opening_audio._elapsed,
                        tuple(actor.state_ms for actor in game.persistent_npcs))
            before = snapshot()
            self.h.click(game, (1, 1))
            for _ in range(30):
                game.update(1/30, (1, 0), True)
            self.assertEqual(snapshot(), before)
            self.assertTrue(game.opening_audio._paused)
            self.h.key(game, pygame.K_ESCAPE)
            self.assertFalse(game.pause.is_open)
            self.assertEqual(snapshot(), before)
            game.update(1/60, (0, 0), False)
            self.assertGreater(game.elapsed_ms, before[0])
            self.assertFalse(game.opening_audio._paused)

    def test_resume_input_is_modal_and_only_explicit_quit_returns_false(self):
        game = self.h.new_game()
        page = game.social.page_index
        self.h.key(game, pygame.K_ESCAPE)
        self.assertTrue(game.pause.is_open)
        # Enter selects Resume, without advancing the scene's page.
        self.h.key(game, pygame.K_RETURN)
        self.assertFalse(game.pause.is_open)
        self.assertEqual(game.social.page_index, page)
        self.h.key(game, pygame.K_ESCAPE)
        # Journal and Map are now available before Settings and Quit. Navigate
        # to the explicit Quit entry rather than relying on the old row count.
        for _ in range(game.pause.options.index('Quit')):
            self.h.key(game, pygame.K_DOWN)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        self.assertFalse(game.handle_events())
        saved = json.loads(self.h.path.read_text())
        self.assertEqual(saved['opening'], {'version': 1, 'stage': 'wake'})
        self.assertEqual(saved['quests'], game.quests.to_dict())

    def test_continue_mid_motion_replays_scene_without_duplicate_quest_acceptance(self):
        game = self.h.new_game()
        self.h.enter_breakfast(game)
        self.tick_until(game, lambda: game.opening.action_name == 'cup')
        self.assertTrue(game.save_progress())
        restored = self.h.continue_game()
        self.assertEqual(restored.opening.stage, 'breakfast')
        self.assertEqual(restored.social.script_identifier, 'opening_greeting')
        self.assertEqual(restored.social.page_index, 0)
        self.assertEqual(restored.quests.status(OPENING_QUEST), 'available')
        self.assertIsNone(restored.quest_ui.current_notice)
        self.h.finish_breakfast(restored)
        self.h.approach_serene(restored)
        self.h.click(restored, restored.social.choice_rects[0].center)
        self.assertEqual(restored.quests.status(OPENING_QUEST), 'active')
        self.assertEqual(restored.opening.stage, 'acceptance')
        self.h.finish_script(restored)
        self.assertEqual(restored.opening.stage, 'done')
        self.assertEqual(restored.quests.states[OPENING_QUEST]['completed_objectives'], [])

    def test_double_clicking_resume_cannot_advance_dialogue_in_the_same_batch(self):
        game = self.h.game(title=False)
        self.assertTrue(game.social.start_script([
            {'speaker': 'caelan', 'text': 'First page.'},
            {'speaker': 'caelan', 'text': 'Second page.'}], identifier='pause_input_check'))
        game.pause.open()
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        x, y = game.pause.rows[0].center
        point = (round((width-480*scale)//2+x*scale),
                 round((height-320*scale)//2+y*scale))
        # Both physical clicks were queued while the pause menu was visible.
        # Closing it must consume the rest of that batch, not treat click two
        # as dialogue input on the scene beneath it.
        for _ in range(2):
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(game.handle_events())
        self.assertFalse(game.pause.is_open)
        self.assertTrue(game.social.scripted)
        self.assertEqual(game.social.page_index, 0)
        self.h.click(game, (1, 1))
        self.assertEqual(game.social.page_index, 1)
        self.assertTrue(game.social.locked)

    def test_tracker_stays_hidden_during_getup_and_pause_then_returns_with_control(self):
        game = self.h.new_game()
        while game.social.scripted:
            self.h.key(game, pygame.K_SPACE)
            game.update(1/60, (0, 0), False)
        self.assertEqual(game.opening.stage, 'wake')
        self.assertTrue(game.opening.in_action)
        self.assertTrue(game.opening.locks_player)
        self.assertFalse(game.social.locked)
        canvas = pygame.Surface(main.VIEW_SIZE)
        canvas.fill('#35544a')
        blank = pygame.image.tobytes(canvas, 'RGB')
        game.quest_ui.draw_tracker(canvas)
        self.assertEqual(pygame.image.tobytes(canvas, 'RGB'), blank)
        self.h.finish_script(game)
        self.assertEqual(game.opening.stage, 'explore')
        game.quest_ui.draw_tracker(canvas)
        self.assertNotEqual(pygame.image.tobytes(canvas, 'RGB'), blank)
        canvas.fill('#35544a')
        game.pause.open()
        game.quest_ui.draw_tracker(canvas)
        self.assertEqual(pygame.image.tobytes(canvas, 'RGB'), blank)

    def test_legacy_assignment_landing_is_rechecked_after_cast_staging(self):
        game = self.h.game(title=False)
        game.world = game._scene_by_id('sanctuary_dining')
        # This floor point was clear in the preceding layout/schedule. The
        # revised breakfast staging reserves it for Tomas after restore.
        game.player.position.update(238, 200)
        self.assertTrue(game.world.can_stand(game.player.position))
        self.assertTrue(game.save_progress())
        snapshot = json.loads(self.h.path.read_text())
        snapshot['opening'] = {'version': 1, 'stage': 'assignment'}
        self.h.path.write_text(json.dumps(snapshot))
        restored = self.h.continue_game()
        self.assertEqual(restored.world.data['id'], 'sanctuary_dining')
        self.assertEqual(restored.opening.stage, 'assignment')
        self.assertEqual(restored.quests.status(OPENING_QUEST), 'available')
        self.assertTrue(restored.world.can_stand(restored.player.position))
        self.assertNotEqual(tuple(restored.player.position), (238, 200))
        self.h.assert_single_cast(restored)
        checkpoint = json.loads(self.h.path.read_text())
        self.assertEqual(checkpoint['player']['position'], list(restored.player.position))
        self.assertEqual(checkpoint['opening']['stage'], 'assignment')

    def test_launcher_settings_persist_independently_from_story_checkpoint(self):
        settings = Path(self.h.directory.name)/'settings.json'
        game = main.Game(fullscreen=False, start_on_title=False, settings_path=settings)
        game.audio.set_music(0)
        game.audio.set_effects(.3)
        self.assertFalse(self.h.path.exists())
        restored = main.Game(fullscreen=False, start_on_title=False, settings_path=settings)
        self.assertEqual(restored.audio.music_volume, 0)
        self.assertAlmostEqual(restored.audio.effects_volume, .3)
        restored.audio.set_effects(0)
        restored.audio.set_music(.5)
        self.assertAlmostEqual(restored.audio.music_volume, .5)
        self.assertEqual(restored.audio.effects_volume, 0)


if __name__ == '__main__':
    unittest.main()
