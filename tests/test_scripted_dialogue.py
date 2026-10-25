"""Story pages own conversation progression without freezing player controls."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import pygame
from social import SocialSystem


class ScriptedDialogueTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((480, 320))
        self.actor = Mock(data={'id': 'mother_serene'},
                          position=pygame.Vector2(288, 214),
                          request_conversation=Mock(), end_conversation=Mock())
        self.game = SimpleNamespace(
            town=SimpleNamespace(image=lambda path: pygame.Surface((72, 72), pygame.SRCALPHA)),
            world=SimpleNamespace(npcs=[self.actor]),
            player=SimpleNamespace(position=pygame.Vector2(288, 231), facing='back',
                                   moving=True, walk_ms=350),
            map_open=False, transfer_cooldown=0, save_progress=Mock())
        self.social = SocialSystem(self.game)

    def tearDown(self):pygame.quit()

    def test_script_owns_conversation_without_stopping_player_or_ambient_actor(self):
        lines = [{'speaker': 'tomas', 'text': "Caelan? You're awake, aren't you?"},
                 {'speaker': 'caelan', 'text': "I'm getting up."}]
        self.assertTrue(self.social.start_script(lines, identifier='morning_knock'))
        self.assertTrue(self.social.locked)
        self.assertTrue(self.social.active)
        self.assertTrue(self.social.scripted)
        self.assertIsNone(self.social.actor)
        self.assertFalse(self.social.choosing)
        self.assertEqual(self.social.script_identifier, 'morning_knock')
        self.assertEqual(self.social.page['speaker'], 'tomas')
        self.assertTrue(self.game.player.moving)
        self.assertEqual(self.game.player.walk_ms, 350)
        self.social.update((0, -1))
        self.actor.request_conversation.assert_not_called()
        self.assertFalse(self.social.start(self.actor))
        self.social.draw(pygame.Surface((480, 320)), 0)
        self.social.click(None)
        self.assertEqual(self.social.page['speaker'], 'caelan')

    def test_completion_callback_runs_once_after_unlock(self):
        states = []
        def finished():
            states.append((self.social.locked, self.social.scripted, self.social.active))
        self.social.start_script([{'speaker': 'serene', 'text': 'Sit and eat.'}], finished)
        self.social.advance()
        self.assertEqual(states, [(False, False, False)])
        self.assertIsNone(self.social.page)
        self.assertIsNone(self.social.conversation)
        self.assertIsNone(self.social.script_identifier)
        self.social.advance()
        self.assertFalse(self.social.click((1, 1)))
        self.assertEqual(len(states), 1)
        self.actor.end_conversation.assert_not_called()
        self.game.save_progress.assert_not_called()
        self.assertEqual(self.social.flags, set())
        self.assertEqual(self.social.blocked, set())

    def test_callback_can_start_the_following_scene_without_being_cleared(self):
        following = [{'speaker': 'caelan', 'text': "I'm getting up."}]
        self.social.start_script(
            [{'speaker': 'tomas', 'text': "Breakfast won't wait forever!"}],
            lambda: self.social.start_script(following, identifier='following'),
            identifier='first')
        self.social.advance()
        self.assertTrue(self.social.scripted)
        self.assertEqual(self.social.script_identifier, 'following')
        self.assertEqual(self.social.page['speaker'], 'caelan')

    def test_cancellation_does_not_fire_a_story_callback_or_cancel_ambient_dialogue(self):
        finished = Mock()
        self.social.start_script([{'speaker': 'serene', 'text': 'Sit and eat.'}], finished)
        self.assertTrue(self.social.cancel_script())
        self.assertFalse(self.social.cancel_script())
        self.assertFalse(self.social.locked)
        finished.assert_not_called()
        self.social.actor = self.actor
        self.assertFalse(self.social.cancel_script())
        self.assertIs(self.social.actor, self.actor)

    def test_invalid_or_busy_script_start_does_not_replace_the_current_pages(self):
        invalid = ([], None, [{'speaker': 'unknown', 'text': 'Hello.'}],
                   [{'speaker': 'serene', 'text': ''}],
                   [{'speaker': 'serene', 'text': 'Hello.', 'cue': {}}])
        for lines in invalid:
            self.assertFalse(self.social.start_script(lines))
            self.assertFalse(self.social.locked)
        self.assertFalse(self.social.start_script([{'speaker': 'serene', 'text': 'Hello.'}], 42))
        self.assertTrue(self.social.start_script([{'speaker': 'serene', 'text': 'First.'}]))
        pages = self.social.pages
        self.assertFalse(self.social.start_script([{'speaker': 'tomas', 'text': 'Second.'}]))
        self.assertIs(self.social.pages, pages)
        self.assertEqual(self.social.page['speaker'], 'serene')

    def test_opening_gate_blocks_ambient_start_but_allows_scripted_dialogue(self):
        self.game.opening = SimpleNamespace(can_speak=Mock(return_value=False))
        self.assertFalse(self.social.start(self.actor))
        self.assertFalse(self.social.locked)
        self.social.update((0, -1))
        self.assertFalse(self.social.locked)
        self.actor.request_conversation.assert_not_called()
        self.game.opening.can_speak.assert_called_with('mother_serene')
        self.assertTrue(self.social.start_script([
            {'speaker': 'tomas', 'text': "Breakfast won't wait forever!"}]))
        self.assertTrue(self.social.scripted)
        self.assertTrue(self.social.locked)

    def test_scene_cue_is_forwarded_only_to_the_lines_first_wrapped_page(self):
        self.social.start_script([{'speaker': 'tomas', 'cue': 'push_plate',
                                  'text': ' '.join(['breakfast']*70)}])
        self.assertGreater(len(self.social.pages), 1)
        self.assertEqual(self.social.pages[0]['cue'], 'push_plate')
        self.assertTrue(all('cue' not in page for page in self.social.pages[1:]))
        for page in self.social.pages:
            self.assertLessEqual(len(page['lines']), 3)
            for line in page['lines']:
                self.assertLessEqual(self.social.font.size(line)[0], 224)

    def test_text_size_change_reflows_current_passage_and_retains_stable_cue_identity(self):
        text = ' '.join(['breakfast']*70)
        self.social.start_script([{'speaker': 'tomas', 'cue': 'push_plate', 'text': text},
                                  {'speaker': 'caelan', 'text': 'I am coming.'}])
        self.social.advance()
        before = dict(self.social.page)
        self.game.audio = SimpleNamespace(text_scale=1.5, effects_volume=0)
        after = self.social.page
        self.assertEqual(after['source_line'], before['source_line'])
        self.assertLessEqual(after['offset'], before['offset'])
        self.assertGreater(after['end'], before['offset'])
        self.assertTrue(all(self.social.font.size(line)[0] <= 224 for line in after['lines']))
        cue_pages = [page for page in self.social.pages if 'cue' in page]
        self.assertEqual(len(cue_pages), 1)
        self.assertEqual(cue_pages[0]['source_line'], 0)

    def test_reflow_keeps_explicit_quest_choice_pending(self):
        import main
        game = main.Game(fullscreen=False, start_on_title=False)
        game.world = game._scene_by_id('sanctuary_dining')
        game.player.position.update(288, 231)
        actor = next(actor for actor in game.persistent_npcs if actor.data['id'] == 'mother_serene')
        game.social.start(actor)
        for _ in range(60):
            if game.social.choosing:break
            game.social.advance()
        self.assertTrue(game.social.choosing)
        game.audio.set_text_scale(1.5)
        game.social.refresh_layout()
        self.assertTrue(game.social.choosing)
        self.assertEqual(game.social.page_index, len(game.social.pages)-1)
        self.assertEqual(game.quests.status('CH01_MQ01'), 'available')
        self.assertEqual(len(game.social.choice_rects), 2)

    def test_real_event_batch_cannot_advance_both_scenes_or_skip_with_held_click(self):
        import main
        game = main.Game(fullscreen=False, start_on_title=False)
        game.title.music_enabled = False
        pygame.event.clear()
        calls = []
        def following():
            calls.append('finished')
            game.social.start_script([{'speaker': 'serene', 'text': 'Next scene.'}])
        game.social.start_script([{'speaker': 'tomas', 'text': 'First scene.'}], following)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                     pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=(1, 1)))
        self.assertTrue(game.handle_events())
        self.assertEqual(calls, ['finished'])
        self.assertTrue(game.social.scripted)
        self.assertEqual(game.social.page['speaker'], 'serene')
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 1)))
        game.handle_events()
        self.assertFalse(game.social.locked)


if __name__ == '__main__':unittest.main()
