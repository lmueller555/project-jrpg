"""Production input, cave travel and durable exploration during pending MQ03."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from quests import REGENT_QUEST, LANTERN_QUEST
from tools.capture_mq03_emergency import Driver


SCENES = ('sanctuary_cave_entrance', 'sanctuary_cave_hollow', 'sanctuary_cave_depths')


class CaveGameplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(pygame.quit)
        self.driver = Driver(directory.name)

    def key(self, key):
        game = self.driver.game
        self.assertTrue(game.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)]))

    def acknowledge(self):
        if self.driver.game.social.active:self.driver.read_current()

    def use_link(self, destination):
        driver = self.driver
        link = next(link for link in driver.game.world.data['cave']['links']
                    if link['destination'] == destination)
        driver.walk(link['position'])
        self.key(pygame.K_e)
        self.assertEqual(driver.game.world.data['id'], destination)
        driver.until(lambda:not driver.game.transfer_cooldown)
        self.assertTrue(driver.game.world.can_stand(driver.game.player.position))

    def assert_pending_party(self):
        game = self.driver.game
        quest = game.regent_quest
        self.assertEqual(quest.stage, 'sanctuary_arrival_pending')
        self.assertEqual(game.quests.status(REGENT_QUEST), 'active')
        self.assertEqual(game.quests.status(LANTERN_QUEST), 'locked')
        self.assertEqual(game.music.desired_track, 'battle')
        self.assertFalse(game.combat.active)
        self.assertEqual(game.party.current_event_id, 'mq03_sanctuary')
        self.assertIn('mira', game.party.active_ids)
        self.assertNotIn('lucan', game.party.members)
        for actor in quest.sanctuary_escorts:
            self.assertIs(quest._world(actor), game.world)
            self.assertTrue(actor.story_visible)
            self.assertEqual(sum(actor in world.npcs for world in game.scenes.values()), 1)
        self.assertEqual([actor.identifier for actor in game.party_travel.actors()].count('mira'), 1)

    def test_old_save_without_cave_state_continues_without_granting_treasure(self):
        driver = self.driver
        before = driver.game.inventory.to_dict()
        saved = json.loads(driver.save.read_text())
        saved.pop('sanctuary_cave', None)
        driver.save.write_text(json.dumps(saved))
        driver.game = driver.new_game(True)
        self.assertTrue(driver.game.has_saved_journey)
        self.assertTrue(driver.game.begin_journey(True))
        self.assertEqual(driver.game.sanctuary_cave.to_dict(), {'version':1, 'opened':[]})
        self.assertEqual(driver.game.inventory.to_dict(), before)

    def test_invalid_cave_receipts_reject_save_without_rewriting_it(self):
        driver = self.driver
        original = json.loads(driver.save.read_text())
        for opened in (['unknown'], ['cave_vein_cache', 'cave_vein_cache'], [True]):
            with self.subTest(opened=opened):
                saved = dict(original)
                saved['sanctuary_cave'] = {'version':1, 'opened':opened}
                raw = json.dumps(saved)
                driver.save.write_text(raw)
                game = driver.new_game(True)
                self.assertFalse(game.has_saved_journey)
                self.assertIsNotNone(game.save_error)
                self.assertEqual(driver.save.read_text(), raw)

    def test_real_entry_all_six_rewards_scene_continues_and_return_preserve_pending_mq03(self):
        driver = self.driver
        driver.meal();driver.attack_report();driver.departure();driver.rejoin_mira();driver.arrive()
        self.assert_pending_party()
        # The public cave approach is reached through the production reserve.
        from sanctuary_cave import RESERVE_ENTRY_APPROACH
        driver.walk(RESERVE_ENTRY_APPROACH)
        self.assertIn('cave', driver.game.sanctuary_cave.interaction_hint().lower())
        self.key(pygame.K_e)
        self.assertEqual(driver.game.world.data['id'], SCENES[0])
        driver.until(lambda:not driver.game.transfer_cooldown)
        seen = set()
        for index, scene in enumerate(SCENES):
            self.assertEqual(driver.game.world.data['id'], scene)
            for treasure in driver.game.world.data['cave']['treasures']:
                with self.subTest(scene=scene, treasure=treasure['id']):
                    driver.walk(treasure['approach'])
                    before = sum(driver.game.inventory.to_dict()['items'].values())
                    self.key(pygame.K_e)
                    self.acknowledge()
                    self.assertIn(treasure['id'], driver.game.sanctuary_cave.to_dict()['opened'])
                    seen.add(treasure['id'])
                    inventory = driver.game.inventory.to_dict()
                    self.assertGreater(sum(inventory['items'].values()), before)
                    self.key(pygame.K_e);self.acknowledge()
                    self.assertEqual(driver.game.inventory.to_dict(), inventory)
                    entity = next(record for record in driver.game.world.entities
                                  if record['id'] == treasure.get('entity_id', treasure['id']))
                    self.assertEqual(entity['state'], 'open')
            inventory = driver.game.inventory.to_dict()
            position = list(driver.game.player.position)
            driver.continue_saved()
            self.assertEqual(driver.game.world.data['id'], scene)
            self.assertEqual(list(driver.game.player.position), position)
            self.assertEqual(driver.game.inventory.to_dict(), inventory)
            self.assertEqual(set(driver.game.sanctuary_cave.to_dict()['opened']), seen)
            self.assert_pending_party()
            for treasure in driver.game.world.data['cave']['treasures']:
                driver.walk(treasure['approach'])
                self.key(pygame.K_e);self.acknowledge()
                self.assertEqual(driver.game.inventory.to_dict(), inventory)
            if index < len(SCENES)-1:self.use_link(SCENES[index+1])
        self.assertEqual(len(seen), 6)
        self.use_link(SCENES[1]);self.use_link(SCENES[0]);self.use_link('elden_vale_sanctuary')
        self.assert_pending_party()
        driver.continue_saved()
        self.assert_pending_party()
        self.assertEqual(set(driver.game.sanctuary_cave.to_dict()['opened']), seen)


if __name__ == '__main__':unittest.main()
