"""A later sanctuary scene keeps exclusive control of the actual Serene."""
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

from main import Game
from tools.capture_lantern_quest import seed_previous_quests


class SereneStoryHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.game = Game(fullscreen=False, start_on_title=False, save_path=None,
                         settings_path=Path(self.temp.name)/'settings.json')
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        seed_previous_quests(self.game)
        self.quest = self.game.regent_quest;self.serene = self.quest.serene

    def tearDown(self):pygame.quit()

    def borrow(self):
        self.quest.handoff_serene()
        hall = self.game._scene_by_id('sanctuary_hall')
        self.quest._place(self.serene, hall, hall.data['spawn'])
        self.serene.facing = 'right';self.serene.moving = True
        self.serene.story_paused = True;self.serene.story_following = True
        self.pose = pygame.Surface((24, 36), pygame.SRCALPHA)
        self.serene.story_sprite = self.pose;self.serene.story_draw_anchor = (12, 30)
        self.serene.conversation_ready = True
        return hall, self.serene.position.copy()

    def assert_borrowed_state(self, hall, position):
        self.assertIs(self.game._routine_worlds[self.serene], hall)
        self.assertIn(self.serene, hall.npcs)
        self.assertEqual(sum(self.serene in world.npcs for world in self.game.scenes.values()), 1)
        self.assertEqual(self.serene.position, position)
        self.assertIs(self.serene.story_sprite, self.pose)
        self.assertEqual(self.serene.story_draw_anchor, (12, 30))
        self.assertEqual(self.serene.facing, 'right')
        self.assertTrue(self.serene.moving)
        self.assertTrue(self.serene.story_paused)
        self.assertTrue(self.serene.story_following)
        self.assertTrue(self.serene.conversation_ready)

    def test_visit_claim_staging_and_update_do_not_reclaim_borrowed_serene(self):
        hall, position = self.borrow()
        self.quest._claim();self.quest._setup_stage(force=True)
        self.quest.update(.2);self.quest._pose_owned()
        self.assert_borrowed_state(hall, position)
        self.assertEqual(self.quest.stage, 'done')
        self.assertTrue(self.quest._venn_returned)
        self.assertTrue(self.quest._delivery_done)

    def test_handoff_is_idempotent_and_old_conversations_do_not_touch_serene(self):
        hall, position = self.borrow()
        self.quest.handoff_serene()
        self.assertIsNone(self.quest.try_conversation(self.serene))
        self.assertIs(self.quest.marker_for('mother_serene'), NotImplemented)
        self.assertTrue(self.quest._speak('aldric_after'))
        self.assertNotIn(self.serene, self.game.social.blocked)
        while self.game.social.active:self.game.social.advance()
        self.assert_borrowed_state(hall, position)
        self.quest.on_dialogue_cancelled('regent_aldric_after')
        self.assert_borrowed_state(hall, position)

    def test_releasing_the_visit_does_not_clear_the_later_scenes_pose(self):
        hall, position = self.borrow()
        self.quest.release_pose()
        self.assertFalse(self.quest._owned)
        self.assert_borrowed_state(hall, position)

    def test_restoring_the_visit_resets_transient_handoff_before_later_restore(self):
        self.borrow()
        self.assertTrue(self.quest.restore({'version': 1, 'stage': 'done'}))
        self.assertFalse(self.quest._serene_handed_off)
        self.assertFalse(self.quest._tomas_handed_off)
        self.assertIs(self.game._routine_worlds[self.serene], self.game.town)
        self.assertLess(self.serene.position.distance_to(self.quest.points['serene']), 1)
        self.assertIsNot(self.serene.story_sprite, self.pose)
        self.assertIsNotNone(self.quest.try_conversation(self.serene))

    def test_new_game_resets_handoff_and_returns_serene_to_opening(self):
        self.borrow()
        self.assertTrue(self.game.begin_journey(False))
        self.assertFalse(self.quest._serene_handed_off)
        self.assertFalse(self.quest._tomas_handed_off)
        self.assertFalse(self.quest._owned)
        self.assertEqual(self.game.quests.status('CH01_MQ03'), 'locked')
        self.assertEqual(self.game.opening.stage, 'wake')
        self.assertEqual(self.game._routine_worlds[self.serene].data['id'], 'sanctuary_dining')


if __name__ == '__main__':unittest.main()
