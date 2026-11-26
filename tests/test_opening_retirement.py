"""Real legacy checkpoints survive the removal of their scene owners."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from opening_retirement import (OpeningCompatibilityError, RETIRED_OWNERS,
                                SAFE_HOME, STORY_REVISION, migrate_retired_opening)

FIXTURES = Path(__file__).parent/'fixtures/opening_retirement'
EARLY = ('mq01_active', 'mq02_active')
RETIRED = ('mq02_complete', 'mq03_assigned', 'mq03_trio', 'mq03_complete', 'mq04_active')


def checkpoint(name):
    return json.loads((FIXTURES/(name+'.json')).read_text())


class OpeningRetirementTests(unittest.TestCase):
    def test_real_checkpoints_preserve_retained_progress_and_earned_resources(self):
        retained = ('inventory', 'character_attributes', 'character_levels',
                    'character_abilities', 'battle_rewards', 'mira_rig',
                    'sanctuary_boss', 'elemental_bosses', 'cave_random_encounters',
                    'cave_lesson', 'mill_quest', 'opening', 'opening_conclusion',
                    'halden_visit', 'elira_visit', 'venn_visit', 'overworld',
                    'exterior_position', 'save_context')
        for name in (*EARLY, *RETIRED):
            with self.subTest(checkpoint=name):
                before = checkpoint(name)
                result = migrate_retired_opening(before)
                self.assertEqual(result['story_revision'], STORY_REVISION)
                self.assertEqual(set(result['quests']['quests']), {'CH01_MQ01', 'CH01_MQ02'})
                for identifier in ('CH01_MQ01', 'CH01_MQ02'):
                    self.assertEqual(result['quests']['quests'][identifier], before['quests']['quests'][identifier])
                for key in retained:self.assertEqual(result[key], before[key], key)
                self.assertEqual(result['party']['characters'], before['party']['characters'])
                self.assertEqual(result['sanctuary_cave'], {
                    'version': before['sanctuary_cave']['version'],
                    'opened': before['sanctuary_cave']['opened'],
                })
                for key in RETIRED_OWNERS:self.assertNotIn(key, result)
                self.assertEqual(result['player'], before['player'] if name in EARLY else SAFE_HOME)

    def test_normalization_is_nonmutating_detached_and_idempotent(self):
        for name in (*EARLY, *RETIRED):
            with self.subTest(checkpoint=name):
                before = checkpoint(name)
                original = deepcopy(before)
                result = migrate_retired_opening(before)
                self.assertEqual(before, original)
                again = migrate_retired_opening(result)
                self.assertEqual(again, result)
                again['inventory']['items']['potion'] += 1
                self.assertEqual(before, original)
                self.assertNotEqual(again['inventory'], result['inventory'])

    def test_early_mill_event_and_existing_player_station_are_retained(self):
        before = checkpoint('mq02_active')
        result = migrate_retired_opening(before)
        self.assertEqual(result['party'], before['party'])
        self.assertEqual(result['party']['event']['id'], 'mq02')
        self.assertEqual(result['player'], before['player'])

    def test_retired_trio_returns_guests_to_ordinary_availability_without_healing(self):
        before = checkpoint('mq03_trio')
        before['party']['characters']['lucan']['current_hp'] = 19
        before['party']['characters']['mira']['current_mp'] = 3
        result = migrate_retired_opening(before)
        party = result['party']
        self.assertIsNone(party['event'])
        self.assertEqual(party['active'], ['caelan'])
        for identifier in ('mira', 'lucan'):
            self.assertFalse(party['members'][identifier]['available'])
            self.assertTrue(party['members'][identifier]['temporary'])
        self.assertEqual(party['members']['mira']['reason'], 'Working in Eldenmere.')
        self.assertEqual(party['characters'], before['party']['characters'])
        self.assertEqual(result['character_levels'], before['character_levels'])

    def test_permanent_members_and_unrelated_party_events_are_not_rewritten(self):
        before = checkpoint('mq03_trio')
        for identifier in ('mira', 'lucan'):
            before['party']['members'][identifier]['temporary'] = False
        result = migrate_retired_opening(before)
        self.assertIsNone(result['party']['event'])
        self.assertEqual(result['party']['members'], before['party']['members'])
        self.assertEqual(result['party']['active'], before['party']['active'])
        before['party']['event']['id'] = 'unrelated_future_event'
        result = migrate_retired_opening(before)
        self.assertEqual(result['party'], before['party'])

    def test_shared_aqua_edge_focus_and_cave_receipts_are_not_prefix_deleted(self):
        before = checkpoint('mq03_complete')
        before['dialogue_flags'].extend(('CH01_MQ03_AQUA_EDGE_DISCOVERED', 'CH01_MQ04_COMPLETE',
                                         'UNRELATED_FUTURE_FACT'))
        before['sanctuary_cave']['opened'] = ['cave_vein_cache']
        result = migrate_retired_opening(before)
        self.assertIn('CH01_MQ03_AQUA_EDGE_DISCOVERED', result['dialogue_flags'])
        self.assertIn('UNRELATED_FUTURE_FACT', result['dialogue_flags'])
        self.assertNotIn('CH01_MQ03_COMPLETE', result['dialogue_flags'])
        self.assertNotIn('CH01_MQ04_COMPLETE', result['dialogue_flags'])
        self.assertEqual(result['sanctuary_cave']['opened'], ['cave_vein_cache'])
        self.assertEqual(result['battle_rewards'], before['battle_rewards'])
        self.assertEqual(result['character_abilities'], before['character_abilities'])
        self.assertEqual(result['elemental_bosses'], before['elemental_bosses'])

    def test_affected_pending_transactions_are_rejected_before_any_data_changes(self):
        for owner in ('post_battle', 'sanctuary_boss', 'elemental_bosses', 'cave_random_encounters'):
            with self.subTest(owner=owner):
                before = checkpoint('mq03_trio')
                if owner == 'post_battle':before[owner] = {'receipt': 'unsettled'}
                else:before[owner]['pending'] = {'receipt': 'unsettled'}
                original = deepcopy(before)
                with self.assertRaisesRegex(OpeningCompatibilityError, 'settled exploration save'):
                    migrate_retired_opening(before)
                self.assertEqual(before, original)
        before = checkpoint('mq03_complete')
        before['elemental_bosses']['bosses']['embravyr']['pending_acquisition'] = True
        with self.assertRaisesRegex(OpeningCompatibilityError, 'unfinished reward'):
            migrate_retired_opening(before)

    def test_revision_two_does_not_reposition_new_exploration_or_drop_shared_pending_work(self):
        current = migrate_retired_opening(checkpoint('mq03_complete'))
        current['player'] = {'scene': 'sanctuary_cave', 'position': [288, 1660], 'facing': 'back'}
        current['post_battle'] = {'receipt': 'new-independent-encounter'}
        result = migrate_retired_opening(current)
        self.assertEqual(result, current)
        self.assertIsNot(result, current)

    def test_unknown_revision_reports_a_compatibility_problem(self):
        before = checkpoint('mq01_active')
        before['story_revision'] = STORY_REVISION+1
        with self.assertRaisesRegex(OpeningCompatibilityError, 'unsupported story revision'):
            migrate_retired_opening(before)


class OpeningRetirementGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pygame
        from main import Game
        cls.pygame, cls.Game = pygame, Game
        cls.directory = tempfile.TemporaryDirectory(prefix='opening-retirement-')
        folder = Path(cls.directory.name)
        cls.path = folder/'journey.json'
        cls.game = Game(fullscreen=False, start_on_title=True,
                        save_path=cls.path, settings_path=folder/'settings.json')
        cls.game.audio.set_music(0);cls.game.audio.set_effects(0)

    @classmethod
    def tearDownClass(cls):
        cls.game.music.stop();cls.pygame.quit();cls.directory.cleanup()

    def test_every_real_settled_fixture_passes_current_game_validation_and_continue(self):
        game = self.game
        for name in (*EARLY, *RETIRED):
            with self.subTest(checkpoint=name):
                source = checkpoint(name)
                expected = migrate_retired_opening(source)
                accepted = game._validate_journey(source)
                self.assertIsNotNone(accepted, game.save_error)
                self.assertEqual(accepted['story_revision'], STORY_REVISION)
                game.saved_journey = accepted
                self.assertTrue(game.begin_journey(True), game.save_error)
                self.assertEqual(game.world.data['id'], expected['player']['scene'])
                self.assertEqual(list(game.player.position), expected['player']['position'])
                self.assertEqual(game.attributes.current_hp, source['character_attributes']['current_hp'])
                self.assertEqual(game.attributes.current_mp, source['character_attributes']['current_mp'])
                self.assertEqual(game.inventory.to_dict(), source['inventory'])
                self.assertEqual(game.character_progression.to_dict(), source['character_levels'])
                self.assertEqual(game.battle_rewards.to_dict(), source['battle_rewards'])
                self.assertEqual(game.character_abilities.to_dict(), source['character_abilities'])
                self.assertEqual(game.party.to_dict()['characters'], source['party']['characters'])
                rewritten = game.journey_snapshot()
                self.assertEqual(rewritten['story_revision'], STORY_REVISION)
                for owner in RETIRED_OWNERS:self.assertNotIn(owner, rewritten)

    def test_validation_never_writes_or_mutates_an_existing_legacy_file(self):
        path = self.path
        original = (FIXTURES/'mq04_active.json').read_bytes()
        path.write_bytes(original)
        data = json.loads(original)
        before = deepcopy(data)
        self.assertIsNotNone(self.game._validate_journey(data), self.game.save_error)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(data, before)

    def test_real_pending_legacy_battle_is_rejected_with_readable_message(self):
        source = checkpoint('mq03_pending_battle')
        self.assertIsNotNone(source['sanctuary_boss']['pending'])
        before = deepcopy(source)
        self.assertIsNone(self.game._validate_journey(source))
        self.assertIn('settled exploration save', self.game.save_error)
        self.assertEqual(source, before)
