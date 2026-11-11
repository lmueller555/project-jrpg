"""Real cave walking, saved random encounters and durable multi-enemy returns."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from cave_random_encounters import CaveRandomEncounters
from main import Game
from overworld_travel import HALL_ID, RESERVE_ID, WORLD_ID, OverworldTravel
from post_battle import valid_pending_snapshot
from quests import REGENT_QUEST, LANTERN_QUEST
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from tools.capture_mq03_emergency import Driver
from test_mill_battle_gameplay import finish_spoils_presentation


class CaveRandomGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reach the unfinished Sanctuary handoff through real quest input once.
        # Every test starts from an independent copy of that valid journey.
        with tempfile.TemporaryDirectory(prefix='cave-random-story-') as directory:
            driver = Driver(directory)
            driver.meal();driver.attack_report();driver.departure();driver.rejoin_mira();driver.arrive()
            # These independent counter/reward cases begin after the new
            # Blue-gem lesson. Its actual story/input arc has dedicated tests.
            if not driver.game.character_abilities.has_weapon():
                assert driver.game.character_abilities.acquire_weapon('caelan', 'caelan_gearblade')
            driver.game.character_abilities.learn_ability('caelan', 'aqua_edge')
            assert driver.game.cave_lesson.restore({'version': 1,
                'resonance_seen': True, 'battle_cleared': True, 'deferred': False})
            driver.walk(RESERVE_ENTRY_APPROACH)
            driver.game.handle_events([
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False),
                pygame.event.Event(pygame.KEYUP, key=pygame.K_e)])
            driver.until(lambda:not driver.game.transfer_cooldown)
            assert driver.game.world.data['id'] == 'sanctuary_cave'
            assert driver.game.save_progress()
            cls.journey = json.loads(driver.save.read_text())
        pygame.quit()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='cave-random-gameplay-')
        self.addCleanup(temporary.cleanup)
        self.addCleanup(pygame.quit)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.path.write_text(json.dumps(self.journey))
        self.game = self.load()

    def load(self):
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        self.assertTrue(game.has_saved_journey, game.save_error)
        self.assertTrue(game.begin_journey(True), game.save_error)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def story(self, game=None):
        game = game or self.game
        self.assertEqual(game.world.data['id'], 'sanctuary_cave')
        self.assertEqual(game.regent_quest.stage, 'sanctuary_arrival_pending')
        self.assertEqual(game.quests.status(REGENT_QUEST), 'active')
        self.assertEqual(game.quests.status(LANTERN_QUEST), 'locked')
        self.assertEqual(game.party.current_event_id, 'mq03_sanctuary')
        self.assertIn('mira', game.party.active_ids)
        self.assertEqual(game.music.desired_track,
                         'battle' if game.combat.active and not game.combat.post_phase
                         else 'sanctuary_cave')

    def position(self, point=(456, 1280)):
        # Test-only placement chooses a clear start; only subsequent production
        # Player.update movement can spend the encounter distance.
        self.assertTrue(self.game.world.can_stand(point))
        self.game.player.position.update(point)
        self.game.player.moving = self.game.player.running = False
        self.game.camera.reset()

    def near_trigger(self, remaining=1):
        self.game.cave_random_encounters.reset(41)
        record = self.game.cave_random_encounters.to_dict()
        record['remaining'] = remaining
        record['was_safe'] = False
        self.assertTrue(self.game.cave_random_encounters.restore(record))

    def trigger(self):
        self.position()
        self.near_trigger()
        before = self.game.player.position.copy()
        world = self.game.world
        self.game.update(.05, (1, 0), False)
        self.assertTrue(self.game.combat.active)
        self.assertIs(self.game.world, world)
        self.assertAlmostEqual(self.game.player.position.x-before.x, 1, places=6)
        self.assertAlmostEqual(self.game.player.position.y, before.y, places=6)
        self.assertEqual(self.game.cave_random_encounters.pending['position'],
                         list(self.game.player.position))
        return self.game.combat

    def enter_battle(self, game=None):
        game = game or self.game
        owner = game.combat
        for _ in range(30):
            if owner.entry_phase == 'loading':break
            game.update(.05, (0, 0), False)
        self.assertEqual(owner.entry_phase, 'loading')
        self.assertIsNone(owner.model)
        # Updating alone must never race past an unseen loading screen.
        for _ in range(3):game.update(.1, (0, 0), False)
        self.assertIsNone(owner.model)
        self.assertFalse(owner.entry.loading_presented)
        game.draw()
        self.assertTrue(owner.entry.loading_presented)
        self.assertIsNone(owner.model)
        game.update(.01, (0, 0), False)
        self.assertIsNotNone(owner.model, getattr(owner.entry, 'error', ''))
        return owner.model

    def settle_reveal(self, game=None):
        game = game or self.game
        for _ in range(30):
            if not game.combat.transitioning:return
            game.update(.05, (0, 0), False)
        self.fail('Battle reveal did not complete')

    def four_enemy_ticket(self):
        for seed in range(1000):
            core = CaveRandomEncounters(seed)
            ticket = core.advance(1000, (1680, 970))
            if ticket is not None and len(ticket['members']) == 4:
                return core.to_dict(), ticket
        self.fail('The approved deep pool never produced a four-enemy formation')

    def start_four(self):
        record, ticket = self.four_enemy_ticket()
        self.position(ticket['position'])
        self.assertTrue(self.game.cave_random_encounters.restore(record))
        self.assertTrue(self.game.combat.start_cave(ticket))
        model = self.enter_battle()
        self.assertEqual(len(model.enemies), 4)
        self.settle_reveal()
        return self.game.combat

    def finish_spoils(self, game):
        owner = game.combat
        for _ in range(100):
            if owner.post_phase == 'spoils' and owner.spoils.ready:break
            game.update(.05, (0, 0), False)
        self.assertEqual(owner.post_phase, 'spoils')
        self.assertTrue(owner.spoils.ready)
        finish_spoils_presentation(game)
        owner.spoils.dismissed = True
        game.update(0, (0, 0), False)
        self.assertFalse(owner.active)

    def test_only_actual_eligible_player_travel_spends_distance_and_continue_preserves_it(self):
        self.position()
        self.near_trigger(200)
        core = self.game.cave_random_encounters
        original = core.to_dict()
        self.game.update(.5, (0, 0), False)
        self.assertEqual(core.to_dict(), original)
        self.position((470, 1280))
        self.game.update(0, (0, 0), False)
        self.assertEqual(core.to_dict(), original, 'Test placement must not count as walking')
        self.game.pause.is_open = True
        self.game.update(.5, (1, 0), True)
        self.assertEqual(core.to_dict(), original)
        self.game.pause.is_open = False
        self.game.map_open = True
        self.game.update(.5, (1, 0), True)
        self.assertEqual(core.to_dict(), original)
        self.game.map_open = False
        self.game._music_focused = False
        self.game.update(.2, (1, 0), False)
        self.assertEqual(core.to_dict(), original)
        self.game._music_focused = True
        start = self.game.player.position.copy()
        self.game.update(.1, (1, 0), False)
        moved = self.game.player.position.distance_to(start)
        self.assertGreater(moved, 0)
        self.assertAlmostEqual(core.to_dict()['remaining'], original['remaining']-moved, places=6)
        snapshot = core.to_dict()
        self.assertTrue(self.game.save_progress())
        restored = self.load()
        self.assertEqual(restored.cave_random_encounters.to_dict(), snapshot)
        self.story(restored)

    def test_trigger_is_durable_and_freezes_world_through_cutscene_then_real_loading(self):
        owner = self.trigger()
        self.assertEqual(owner.entry_phase, 'cutscene')
        self.assertIsNone(owner.scene)
        ticket = deepcopy(self.game.cave_random_encounters.pending)
        state = self.game.cave_random_encounters.to_dict()
        position = list(self.game.player.position)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['cave_random_encounters']['pending'], ticket)
        owner.entry.paused = True
        for _ in range(3):self.game.update(.2, (1, 0), True)
        self.assertEqual(owner.entry.elapsed, 0)
        self.assertEqual(list(self.game.player.position), position)
        self.assertEqual(self.game.cave_random_encounters.to_dict(), state)
        owner.entry.paused = False
        model = self.enter_battle()
        atb = dict(model.initial_atb_values)
        self.assertTrue(atb and all(0 <= value <= .5 for value in atb.values()))
        self.assertEqual(len(model.enemies), len(ticket['members']))
        self.assertEqual(owner.scene.battlefield, ticket['battlefield'])
        restored = self.load()
        self.assertEqual(restored.cave_random_encounters.pending, ticket)
        self.assertEqual(restored.cave_random_encounters.to_dict(), state)
        self.assertEqual(list(restored.player.position), position)
        resumed = self.enter_battle(restored)
        self.assertEqual(resumed.initial_atb_values, atb)
        self.story(restored)

    def test_diagonal_collision_slide_never_checkpoints_an_unstandable_trigger_position(self):
        self.position((1804.8, 768.4))
        self.near_trigger(.2)
        self.game.update(1/72, (-1, 1), False)
        self.assertTrue(self.game.combat.active)
        point = list(self.game.player.position)
        self.assertTrue(self.game.world.can_stand(point), point)
        pending = self.game.cave_random_encounters.pending
        self.assertEqual(pending['position'], point)
        self.assertTrue(self.game.cave_random_encounters.valid_ticket(pending))
        restored = self.load()
        self.assertEqual(list(restored.player.position), point)
        self.assertEqual(restored.cave_random_encounters.pending, pending)

    def test_real_straight_diagonal_and_wall_slide_distance_is_frame_rate_independent(self):
        cases = (
            ('straight-short', (456, 1280), (1, 0), .04, 10),
            ('straight-long', (456, 1280), (1, 0), .4, 1),
            ('diagonal-short', (456, 1280), (1, 1), .04, 10),
            ('diagonal-long', (456, 1280), (1, 1), .4, 1),
            ('collision-slide', (1804.8, 768.4), (1, -1), 1/72, 1),
            ('blocked-corner', (1804.8, 768.4), (1, 1), 1/72, 1),
            ('collision-corner', (1804.8, 768.4), (-1, 1), 1/72, 1),
        )
        lengths = {}
        for name, start, direction, seconds, count in cases:
            with self.subTest(movement=name):
                self.position(start)
                self.near_trigger(200)
                for _ in range(count):self.game.update(seconds, direction, False)
                length = self.game.player.position.distance_to(start)
                spent = 200-self.game.cave_random_encounters.to_dict()['remaining']
                if name == 'blocked-corner':self.assertEqual(length, 0)
                else:self.assertGreater(length, 0)
                self.assertFalse(self.game.combat.active)
                self.assertAlmostEqual(spent, length, places=6)
                self.assertTrue(self.game.world.can_stand(self.game.player.position))
                lengths[name] = spent
        self.assertAlmostEqual(lengths['straight-short'], lengths['straight-long'], places=6)
        self.assertAlmostEqual(lengths['diagonal-short'], lengths['diagonal-long'], places=6)
        self.assertAlmostEqual(lengths['straight-long'], lengths['diagonal-long'], places=6)

    def test_four_enemy_victory_resumes_spoils_once_preserves_caelan_ko_and_all_resources(self):
        owner = self.start_four()
        position = list(self.game.player.position)
        facing = self.game.player.facing
        ticket = deepcopy(self.game.cave_random_encounters.pending)
        inventory = self.game.inventory.to_dict()
        owner.model.player.hp = 0
        owner.model.player.mp = 2
        mira = owner.model.combatant('mira')
        mira.hp = 97;mira.mp = 3
        for enemy in owner.model.enemies:enemy.hp = 0
        owner.model._result('victory')
        self.assertTrue(owner._begin_victory())
        self.assertEqual(self.game.music.desired_track, 'sanctuary_cave')
        pending = owner.snapshot()
        for item, quantity in pending['rewards']['drops'].items():
            inventory['items'][item] = inventory['items'].get(item, 0)+quantity
        self.assertEqual(pending['kind'], 'cave')
        self.assertEqual(pending['encounter'], ticket)
        self.assertEqual(pending['resources'], {'hp': 0, 'mp': 2})
        saved = json.loads(self.path.read_text())
        self.assertTrue(valid_pending_snapshot(pending, saved))
        self.assertTrue(OverworldTravel.valid_journey(saved))
        for remote_scene in (WORLD_ID, RESERVE_ID, HALL_ID):
            with self.subTest(forged_scene=remote_scene):
                forged = deepcopy(saved)
                forged['player']['scene'] = remote_scene
                self.assertFalse(OverworldTravel.valid_journey(forged))
        forged = deepcopy(saved)
        forged['post_battle']['kind'] = 'bat'
        self.assertFalse(OverworldTravel.valid_journey(forged))
        restored = self.load()
        self.assertEqual(restored.combat.post_phase, 'spoils')
        self.assertEqual(restored.music.desired_track, 'sanctuary_cave')
        self.assertEqual(len(restored.combat.model.enemies), 4)
        self.assertTrue(all(enemy.hp == 0 for enemy in restored.combat.model.enemies))
        self.assertEqual((restored.attributes.current_hp, restored.attributes.current_mp), (0, 2))
        self.assertEqual((restored.party.characters['mira'].current_hp,
                          restored.party.characters['mira'].current_mp), (97, 3))
        self.assertTrue(restored.battle_rewards.has_receipt(ticket['receipt']))
        self.assertEqual(restored.inventory.to_dict(), inventory)
        receipt_state = restored.battle_rewards.to_dict()
        again = self.load()
        self.assertEqual(again.music.desired_track, 'sanctuary_cave')
        self.assertEqual(again.battle_rewards.to_dict(), receipt_state)
        self.assertEqual(again.inventory.to_dict(), inventory)
        self.finish_spoils(again)
        self.assertEqual(list(again.player.position), position)
        self.assertEqual(again.player.facing, facing)
        fresh = again.cave_random_encounters.to_dict()
        self.assertIsNone(fresh['pending'])
        self.assertTrue(16*24 <= fresh['remaining'] <= 36*24)
        self.assertEqual(again.battle_rewards.to_dict(), receipt_state)
        self.story(again)

    def test_flee_and_defeat_return_without_rewards_and_roll_one_new_distance(self):
        for outcome in ('fled', 'defeat'):
            with self.subTest(outcome=outcome):
                if outcome == 'defeat':
                    self.path.write_text(json.dumps(self.journey))
                    self.game = self.load()
                owner = self.start_four()
                position = list(self.game.player.position)
                initial = {key: (member.current_hp, member.current_mp)
                           for key, member in self.game.party.characters.items()}
                if outcome == 'fled':
                    owner.model.player.hp = 0;owner.model.player.mp = 1
                    owner.model.combatant('mira').hp = 81
                    owner.model.combatant('mira').mp = 2
                else:
                    for member in owner.model.party:member.hp = member.mp = 0
                owner.model._result(outcome)
                owner.scene.dismissed = True
                self.assertTrue(owner._settle())
                self.assertFalse(owner.active)
                self.assertEqual(list(self.game.player.position), position)
                self.assertEqual(self.game.battle_rewards.to_dict()['receipts'], [])
                state = self.game.cave_random_encounters.to_dict()
                self.assertIsNone(state['pending'])
                self.assertTrue(16*24 <= state['remaining'] <= 36*24)
                if outcome == 'fled':
                    self.assertEqual((self.game.attributes.current_hp, self.game.attributes.current_mp), (0, 1))
                    self.assertEqual((self.game.party.characters['mira'].current_hp,
                                      self.game.party.characters['mira'].current_mp), (81, 2))
                else:
                    self.assertEqual({key: (member.current_hp, member.current_mp)
                                      for key, member in self.game.party.characters.items()}, initial)
                restored = self.load()
                self.assertFalse(restored.combat.active)
                self.assertEqual(restored.cave_random_encounters.to_dict(), state)
                self.story(restored)

    def test_failed_return_save_rolls_back_resources_and_distance_then_retries_once(self):
        owner = self.start_four()
        before = self.game.cave_random_encounters.to_dict()
        resources = self.game.party.to_dict()
        owner.model.player.hp -= 7
        owner.model.player.mp = 1
        owner.model.combatant('mira').hp = 81
        owner.model.combatant('mira').mp = 2
        owner.model._result('fled')
        owner.scene.dismissed = True
        expected = CaveRandomEncounters(0)
        self.assertTrue(expected.restore(before))
        self.assertTrue(expected.finish(before['pending']['receipt']))
        with patch.object(self.game.save_store, 'write', return_value=False):
            self.assertFalse(owner._settle())
        self.assertTrue(owner.active)
        self.assertFalse(owner.scene.dismissed)
        self.assertEqual(self.game.party.to_dict(), resources)
        self.assertEqual(self.game.cave_random_encounters.to_dict(), before)
        self.assertEqual(self.game.battle_rewards.to_dict()['receipts'], [])
        owner.scene.dismissed = True
        self.assertTrue(owner._settle())
        self.assertEqual(self.game.cave_random_encounters.to_dict(), expected.to_dict())
        self.assertEqual(self.game.attributes.current_hp,
                         resources['characters']['caelan']['current_hp']-7)
        self.assertEqual((self.game.attributes.current_mp,
                          self.game.party.characters['mira'].current_hp,
                          self.game.party.characters['mira'].current_mp), (1, 81, 2))
        self.assertEqual(self.load().cave_random_encounters.to_dict(), expected.to_dict())


if __name__ == '__main__':
    unittest.main()
