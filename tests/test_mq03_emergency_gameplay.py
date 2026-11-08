"""Actual MQ03 acknowledgements, cancellation, companions and regional travel."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from tools.capture_mq03_emergency import Driver, RESERVE, cast_visibility
from quests import REGENT_QUEST, LANTERN_QUEST


def survivors(game):
    return [actor for world in game.scenes.values() for actor in world.npcs
            if 'survivor' in actor.data['id']]


class MQ03EmergencyGameplayTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(pygame.quit)
        self.driver=Driver(temporary.name)

    def test_discussion_cancel_and_report_continue_never_commit_unread_dialogue(self):
        driver=self.driver;driver.meal()
        driver.game.social.blocked.clear()
        self.assertTrue(driver.quest.interact())
        self.assertEqual(driver.game.social.script_identifier,'regent_discussion')
        driver.game.social.cancel()
        self.assertEqual(driver.quest.stage,'hosted')
        self.assertEqual(driver.game.quests.objective_status(REGENT_QUEST,'speak_serene'),'active')
        driver.interact('discussion')
        self.assertEqual(driver.quest.stage,'interruption')
        before=[tuple(actor.position) for actor in survivors(driver.game)]
        self.assertEqual(len(before),1)
        driver.game.pause.is_open=True
        driver.tick(.8)
        self.assertEqual([tuple(actor.position) for actor in survivors(driver.game)],before)
        self.assertEqual(driver.quest.stage,'interruption')
        driver.game.pause.is_open=False
        driver.until(lambda:driver.quest.stage=='attack_report' and driver.game.social.active)
        self.assertEqual(len(survivors(driver.game)),1)
        self.assertIsNone(driver.game.music.desired_track)
        driver.game.social.advance()
        driver.game.social.cancel()
        self.assertEqual(driver.quest.stage,'attack_report')
        driver.continue_saved()
        self.assertEqual(driver.quest.stage,'attack_report')
        self.assertIsNone(driver.game.music.desired_track)
        self.assertEqual(len(survivors(driver.game)),1)
        self.assertFalse(driver.game.quests.status(LANTERN_QUEST)=='available')
        driver.game.social.blocked.clear()
        if not driver.game.social.active:
            self.assertTrue(driver.quest.interact())
        self.assertEqual(driver.game.social.script_identifier,'regent_attack_report')
        def check_music(identifier,line,page):
            driver.tick()
            self.assertEqual(driver.game.music.desired_track,
                             None if page['source_line'] < 3 else 'battle')
        driver.read_current(on_page=check_music)
        self.assertEqual(driver.quest.stage,'departure')
        driver.continue_saved()
        self.assertEqual(driver.quest.stage,'departure')
        self.assertEqual(driver.game.music.desired_track,'battle')
        driver.tick()
        self.assertNotEqual(driver.game.social.script_identifier,'regent_attack_report')
        self.assertEqual(len(survivors(driver.game)),1)

    def test_real_outing_preserves_mira_and_resumes_five_cast_at_pending_arrival(self):
        driver=self.driver
        mira=driver.game.party.characters['mira']
        self.assertTrue(mira.apply_growth({'str':5,'m_def':4}))
        mira.set_current(hp=85,mp=4)
        resources=mira.to_dict()
        driver.meal();driver.attack_report();driver.departure()
        driver.travel(driver.game.town)
        authored_mira=driver.game.mill_quest.mira
        driver.walk(driver.clear(driver.game.town,authored_mira.position+(0,28)))
        if not driver.game.social.active:self.assertTrue(driver.quest.interact())
        self.assertEqual(driver.game.social.script_identifier,'regent_mira_departure')
        driver.game.social.cancel()
        self.assertEqual(driver.quest.stage,'rejoin_mira')
        self.assertNotIn('mira',driver.game.party.active_ids)
        self.assertFalse(driver.game.party.members['mira']['available'])
        self.assertEqual(driver.game.party.characters['mira'].to_dict(),resources)
        driver.rejoin_mira()
        self.assertIs(driver.game.party.characters['mira'],mira)
        self.assertEqual(driver.game.party.current_event_id,'mq03_sanctuary')
        self.assertEqual(set(driver.game.party.required_ids),{'caelan','mira'})
        self.assertIn('mira',driver.game.party.active_ids)
        self.assertNotIn('lucan',driver.game.party.members)
        self.assertEqual(driver.game.party.characters['mira'].to_dict(),resources)
        driver.continue_saved()
        self.assertEqual(driver.quest.stage,'sanctuary_travel')
        self.assertEqual(driver.game.party.current_event_id,'mq03_sanctuary')
        self.assertEqual(driver.game.party.characters['mira'].to_dict(),resources)
        driver.arrive()
        self.assertEqual(driver.game.world.data['id'],RESERVE)
        self.assertEqual(driver.game.quests.status(REGENT_QUEST),'active')
        self.assertEqual(driver.game.quests.status(LANTERN_QUEST),'locked')
        self.assertFalse(driver.quest.locks_player)
        self.assertFalse(driver.game.combat.active)
        for actor in (driver.quest.aldric,driver.quest.lucan,driver.quest.clerk):
            self.assertIs(driver.quest._world(actor),driver.game.world)
            self.assertTrue(actor.story_visible)
            self.assertEqual(sum(actor in world.npcs for world in driver.game.scenes.values()),1)
            self.assertTrue(driver.game.world.can_stand(actor.position,actor.probe_size,actor))
        self.assertEqual([actor.identifier for actor in driver.game.party_travel.actors()].count('mira'),1)

        self.assertFalse(driver.game.world.can_stand((1008,365)))
        driver.continue_saved(settle=False)
        self.assertEqual(driver.quest.stage,'sanctuary_arrival_pending')
        self.assertEqual(driver.game.music.desired_track,'battle')
        self.assertEqual(driver.game.world.data['id'],RESERVE)
        self.assertEqual(driver.game.party.characters['mira'].to_dict(),resources)
        self.assertEqual(driver.game.quests.status(LANTERN_QUEST),'locked')
        self.assertFalse(driver.game.combat.active)
        self.assertNotIn('lucan',driver.game.party.members)
        self.assertEqual([actor.identifier for actor in driver.game.party_travel.actors()].count('mira'),1)
        visible=cast_visibility(driver.game)
        self.assertEqual(set(visible),{'caelan','mira','aldric','lucan','regent_clerk'})
        self.assertTrue(all(record['visible_pixels']>0 for record in visible.values()))

    def test_interrupting_care_scene_does_not_softlock_if_player_occupies_a_station(self):
        # Position initialization is confined to this adversarial test. The
        # retained production review reaches every station by ordinary movement.
        for index,name in enumerate(('survivor_rest','serene_aid')):
            with self.subTest(station=name):
                driver=(self.driver if index==0 else
                        Driver(Path(self.driver.directory)/'occupied-serene'))
                driver.meal()
                self.assertTrue(driver.quest.interact())
                target=driver.quest.points[name]
                self.assertTrue(driver.game.world.can_stand(target))
                driver.game.player.position.update(target)
                driver.read_current()
                self.assertEqual(driver.quest.stage,'interruption')
                driver.until(lambda:driver.quest.stage=='attack_report' and driver.game.social.active)
                player_feet=driver.game.world.probe_rect(driver.game.player.position)
                for actor in (*survivors(driver.game),driver.quest.serene):
                    if actor in driver.game.world.npcs:
                        self.assertFalse(player_feet.colliderect(
                            driver.game.world.probe_rect(actor.position,actor.probe_size)))


if __name__=='__main__':unittest.main()
