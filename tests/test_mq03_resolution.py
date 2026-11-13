import tempfile
import unittest
import pygame
from tools.capture_sanctuary_rescue import make_game, seed_victory
from regent_resolution import STAGES
from unittest.mock import patch
from tools.capture_sanctuary_rescue import press

class ResolutionTests(unittest.TestCase):
    def test_closing_stages_save_restore_and_unlock_only_at_end(self):
        with tempfile.TemporaryDirectory() as directory:
            g=make_game(directory,embedded=False)
            try:
                seed_victory(g)
                g.sanctuary_cave.lucan_departed=True
                g.sanctuary_rescue.restore({'version':1,'stage':'evacuated'})
                g._sync_story_party()
                c=g.regent_quest
                for stage in STAGES:
                    self.assertTrue(c.resolution.commit(stage))
                    self.assertEqual(g.quests.status('CH01_MQ04'),'locked')
                    self.assertTrue(c.valid_journey(g.journey_snapshot()))
                    self.assertTrue(g.sanctuary_arrival.valid_journey(g.journey_snapshot()))
                self.assertTrue(c.resolution.commit('done'))
                self.assertEqual(g.quests.status('CH01_MQ03'),'completed')
                self.assertEqual(g.quests.status('CH01_MQ04'),'available')
            finally:g.music.stop();pygame.quit()

    def test_failed_stage_save_restores_quest_and_party(self):
        with tempfile.TemporaryDirectory() as directory:
            g=make_game(directory,embedded=False)
            try:
                seed_victory(g);g.sanctuary_cave.lucan_departed=True
                g.sanctuary_rescue.restore({'version':1,'stage':'evacuated'})
                g._sync_story_party();c=g.regent_quest
                self.assertTrue(c.resolution.commit('resolution_family'))
                before=(c.stage,g.quests.to_dict(),g.party.to_dict(),g.inventory.to_dict())
                with patch.object(g,'save_progress',return_value=False):
                    self.assertFalse(c.resolution.commit('done'))
                self.assertEqual(before,(c.stage,g.quests.to_dict(),g.party.to_dict(),g.inventory.to_dict()))
                self.assertEqual(g.quests.status('CH01_MQ04'),'locked')
            finally:g.music.stop();pygame.quit()

    def test_cancelled_report_does_not_advance(self):
        with tempfile.TemporaryDirectory() as directory:
            g=make_game(directory,embedded=False)
            try:
                seed_victory(g);g.sanctuary_cave.lucan_departed=True
                g.sanctuary_rescue.restore({'version':1,'stage':'evacuated'});g._sync_story_party()
                c=g.regent_quest;g.world=g._scene_by_id('elden_vale_sanctuary')
                self.assertTrue(c.resolution.commit('resolution_report'));c._setup_stage()
                g.player.position.update(772,444)
                self.assertTrue(c.resolution.interact())
                g.social.cancel_script();c.on_dialogue_cancelled('regent_resolution_report')
                self.assertEqual(c.stage,'resolution_report')
                self.assertEqual(g.quests.status('CH01_MQ04'),'locked')
            finally:g.music.stop();pygame.quit()
