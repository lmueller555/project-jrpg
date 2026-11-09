"""Production walking, continuous cave exploration and durable MQ03 saves."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from quests import REGENT_QUEST, LANTERN_QUEST
from sanctuary_cave import SCENE_ID, LEGACY_SCENES, REWARDS
from tools.capture_mq03_emergency import Driver


class CaveGameplayTests(unittest.TestCase):
    def setUp(self):
        # This suite isolates terrain, discoveries and following. Real random
        # battle entry/settlement is exercised in test_cave_random_gameplay.
        encounters=patch('main.Game._cave_encounters_available',return_value=False)
        encounters.start()
        self.addCleanup(encounters.stop)
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

    def assert_gathered(self):
        """The real following actors negotiate the same floor as the player."""
        game = self.driver.game
        escorts = game.regent_quest.sanctuary_escorts
        def gathered():
            mira = next((actor for actor in game.party_travel.actors()
                         if actor.identifier == 'mira'), None)
            return (all(actor.position.distance_to(game.player.position) < 160 for actor in escorts)
                    and mira is not None and mira.position.distance_to(game.player.position) < 80)
        self.driver.until(gathered, seconds=12)
        self.assert_pending_party()
        for actor in escorts:
            self.assertTrue(game.world.can_stand(actor.position, actor.probe_size, actor),
                            (actor.data['id'], list(actor.position)))
        mira = next(actor for actor in game.party_travel.actors() if actor.identifier == 'mira')
        self.assertLess(mira.position.distance_to(game.player.position), 80)
        self.assertTrue(game.world.can_stand(mira.position))

    def guard_continuous_walk(self):
        world = self.driver.game.world
        def observe(seconds):
            game = self.driver.game
            self.assertIs(game.world, world, 'Walking between cave rooms loaded another scene')
            self.assertEqual(game.transfer_cooldown, 0)
            self.assertTrue(world.can_stand(game.player.position))
        self.driver.observer = observe
        return world

    def open_treasure(self, identifier):
        game = self.driver.game
        treasure = next(item for item in game.world.data['cave']['treasures']
                        if item['id'] == identifier)
        self.driver.walk(treasure['approach'])
        before = {item:game.inventory.quantity(item) for item in REWARDS[identifier]}
        self.key(pygame.K_e)
        self.acknowledge()
        self.assertIn(identifier, game.sanctuary_cave.to_dict()['opened'])
        for item, count in REWARDS[identifier].items():
            self.assertEqual(game.inventory.quantity(item), before[item]+count)
        inventory = game.inventory.to_dict()
        self.key(pygame.K_e)
        self.acknowledge()
        self.assertEqual(game.inventory.to_dict(), inventory)
        entity = next(record for record in game.world.entities
                      if record['id'] == treasure.get('entity_id', identifier))
        self.assertEqual(entity['state'], 'open')

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

    def test_real_walking_explores_one_instance_and_preserves_pending_mq03_on_continue(self):
        driver = self.driver
        driver.meal();driver.attack_report();driver.departure();driver.rejoin_mira();driver.arrive()
        self.assert_pending_party()
        self.assertTrue(driver.game.party.attributes('caelan').set_current(hp=75, mp=4))
        self.assertTrue(driver.game.party.attributes('mira').set_current(hp=121, mp=7))
        party = driver.game.party.to_dict()
        # The public cave approach is reached through the production reserve.
        from sanctuary_cave import RESERVE_ENTRY_APPROACH
        driver.walk(RESERVE_ENTRY_APPROACH)
        self.assertIn('cave', driver.game.sanctuary_cave.interaction_hint().lower())
        self.key(pygame.K_e)
        self.assertEqual(driver.game.world.data['id'], SCENE_ID)
        driver.until(lambda:not driver.game.transfer_cooldown)
        world = self.guard_continuous_walk()
        cave = world.data['cave']
        points = cave['navigation_points']
        transitions = list(driver.transitions)
        self.assertEqual({link['destination'] for link in cave['links']}, {'elden_vale_sanctuary'})
        self.assertFalse(LEGACY_SCENES.intersection(scene.data['id'] for scene in driver.game.scenes.values()))
        # Both optional loops, the raised spur and the arena are reached by
        # ordinary input. Every room stays in the original world instance.
        itinerary = (
            ('vein_gallery', 'cave_vein_cache'),
            ('reflecting_grotto', 'cave_grotto_pack'),
            ('reflecting_grotto', 'cave_grotto_chest'),
            ('upper_passage', None),
            ('splitstone_hollow', None),
            ('raised_shelf', 'cave_overlook_cache'),
            ('splitstone_hollow', None),
            ('keepers_recess', 'cave_keeper_chest'),
            ('deep_passage', None),
            ('deep_gallery', None),
            ('quiet_shelf', 'cave_quiet_cache'),
            ('echo_chamber', None),
        )
        for room, treasure in itinerary:
            with self.subTest(room=room, treasure=treasure):
                driver.walk(points[room])
                if treasure:self.open_treasure(treasure)
                self.assert_gathered()
                self.assertEqual(driver.game.party.to_dict(), party)
        self.assertEqual(driver.transitions, transitions)
        self.assertEqual(set(driver.game.sanctuary_cave.to_dict()['opened']), set(REWARDS))
        inventory = driver.game.inventory.to_dict()
        position = list(driver.game.player.position)
        driver.observer = None
        driver.continue_saved()
        self.assertEqual(driver.game.world.data['id'], SCENE_ID)
        self.assertEqual(list(driver.game.player.position), position)
        self.assertEqual(driver.game.inventory.to_dict(), inventory)
        self.assertEqual(driver.game.party.to_dict(), party)
        self.assert_pending_party()
        for treasure in cave['treasures']:
            entity = next(record for record in driver.game.world.entities
                          if record['id'] == treasure.get('entity_id', treasure['id']))
            self.assertEqual(entity['state'], 'open')

        # Each supported former room save resumes in its matching area. Full
        # receipt, resource, inventory and story state survive the migration.
        saved = json.loads(driver.save.read_text())
        for legacy in sorted(LEGACY_SCENES):
            with self.subTest(legacy=legacy):
                old = json.loads(json.dumps(saved))
                old['player']['scene'] = legacy
                old['player']['position'] = [410, 600]
                driver.save.write_text(json.dumps(old))
                driver.game = driver.new_game(True)
                self.assertTrue(driver.game.has_saved_journey)
                self.assertTrue(driver.game.begin_journey(True))
                driver.until(lambda:not driver.game.opening_fade and not driver.game.transfer_cooldown)
                self.assertEqual(driver.game.world.data['id'], SCENE_ID)
                self.assertEqual(list(driver.game.player.position), cave['legacy_landings'][legacy])
                self.assertEqual(driver.game.inventory.to_dict(), inventory)
                self.assertEqual(driver.game.party.to_dict(), party)
                self.assertEqual(set(driver.game.sanctuary_cave.to_dict()['opened']), set(REWARDS))
                self.assert_pending_party()

        self.guard_continuous_walk()
        for point in reversed(cave['routes']['main']):driver.walk(point)
        self.assert_gathered()
        driver.observer = None
        self.use_link('elden_vale_sanctuary')
        self.assert_pending_party()
        driver.continue_saved()
        self.assert_pending_party()
        self.assertEqual(set(driver.game.sanctuary_cave.to_dict()['opened']), set(REWARDS))
        self.assertEqual(driver.game.inventory.to_dict(), inventory)


if __name__ == '__main__':unittest.main()
