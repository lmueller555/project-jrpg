"""Applied rig ownership, bounded old-save import and actual Continue behavior."""
from copy import deepcopy
import gc
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from mira_rig_state import MiraRigState, migrate_mira_rig


DEFAULT = {'weapons': 2, 'protection': 2, 'support': 2}
OFFENSIVE = {'weapons': 3, 'protection': 2, 'support': 1}
RETIRED = {'version': 1, 'loadouts': {
    'mira': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}}}


class MiraRigStateTests(unittest.TestCase):
    def test_applied_state_round_trips_without_sharing_mutable_values(self):
        owner = MiraRigState()
        self.assertEqual(owner.to_dict(), {'version': 1, 'allocation': DEFAULT})
        source = dict(OFFENSIVE)
        self.assertTrue(owner.set_allocation(source))
        source['weapons'] = 0
        exposed = owner.allocation;exposed['weapons'] = 0
        saved = owner.to_dict()
        restored = MiraRigState();self.assertTrue(restored.restore(saved))
        saved['allocation']['support'] = 0
        self.assertEqual(owner.allocation, OFFENSIVE)
        self.assertEqual(restored.allocation, OFFENSIVE)

    def test_invalid_state_is_rejected_atomically_without_coercion(self):
        owner = MiraRigState();owner.set_allocation(OFFENSIVE)
        invalid_allocations = [None, [], True, {}, {'weapons': 6},
            {'weapons': True, 'protection': 2, 'support': 3},
            {'weapons': 3., 'protection': 2, 'support': 1},
            {'weapons': 7, 'protection': 0, 'support': -1},
            {'weapons': 3, 'protection': 1, 'support': 1},
            {**DEFAULT, 'unknown': 0}]
        for value in invalid_allocations:
            with self.subTest(allocation=value):
                self.assertFalse(owner.set_allocation(value))
                self.assertFalse(owner.restore({'version': 1, 'allocation': value}))
                self.assertEqual(owner.allocation, OFFENSIVE)
        for value in (None, [], True, {}, {'version': True, 'allocation': DEFAULT},
                      {'version': 2, 'allocation': DEFAULT},
                      {'version': 1, 'allocation': DEFAULT, 'draft': DEFAULT}):
            with self.subTest(snapshot=value):
                self.assertFalse(owner.restore(value))
                self.assertEqual(owner.allocation, OFFENSIVE)
        self.assertTrue(MiraRigState.valid_journey({}))
        self.assertTrue(MiraRigState.valid_journey({'mira_rig': owner.to_dict()}))
        self.assertFalse(MiraRigState.valid_journey({'mira_rig': None}))
        self.assertFalse(MiraRigState.valid_journey(None))

    def test_known_legacy_loadouts_normalize_without_touching_progress_or_pending_rewards(self):
        for block in (RETIRED, {'version': 1, 'loadouts': {}}):
            for version in (1, 2, 3):
                with self.subTest(block=block, pending_version=version):
                    original = {'bot_loadouts': deepcopy(block),
                        'inventory': {'items': {'potion': 3, 'ether': 2}},
                        'party': {'active': ['caelan', 'mira']},
                        'character_levels': {'earned_xp': 5740},
                        'character_abilities': {'learned_abilities': {'caelan': ['aqua_edge']}},
                        'post_battle': {'version': version, 'receipt': 'unchanged',
                            'item_costs': {'potion': 1}, 'rewards': {'drops': {'ether': 1}}}}
                    before = deepcopy(original)
                    migrated = migrate_mira_rig(original)
                    self.assertEqual(original, before)
                    self.assertNotIn('bot_loadouts', migrated)
                    self.assertEqual(migrated['mira_rig'], MiraRigState().to_dict())
                    for key in original:
                        if key != 'bot_loadouts':self.assertEqual(migrated[key], before[key])
                    migrated['inventory']['items']['potion'] = 100
                    self.assertEqual(original, before)

    def test_modern_state_is_preserved_and_unknown_old_records_remain_invalid(self):
        modern = {'mira_rig': {'version': 1, 'allocation': OFFENSIVE},
                  'character_abilities': {'learned_abilities': {'mira': ['unrecognized']}}}
        migrated = migrate_mira_rig(modern)
        self.assertEqual(migrated, modern)  # Modern validators decide learned-history validity.
        self.assertIsNot(migrated, modern)
        malformed = [None, [], True, {}, {'version': True, 'loadouts': {}},
                     {'version': 2, 'loadouts': {}}, {'version': 1, 'loadouts': None},
                     {'version': 1, 'loadouts': {}, 'extra': 1}]
        for change in ({'ability_id': 'unknown'}, {'bot_id': 'other'}, {'extra': 1}):
            value = deepcopy(RETIRED);value['loadouts']['mira'].update(change);malformed.append(value)
        value = deepcopy(RETIRED);value['loadouts']['lucan'] = value['loadouts'].pop('mira')
        malformed.append(value)
        for block in malformed:
            original = {'bot_loadouts': block};before = deepcopy(original)
            with self.subTest(block=block), self.assertRaises(ValueError):migrate_mira_rig(original)
            self.assertEqual(original, before)
        for value in (None, [], True):
            with self.assertRaises(ValueError):migrate_mira_rig(value)


class MiraRigJourneyTests(unittest.TestCase):
    def setUp(self):
        import pygame
        self.pygame = pygame
        self.directory = tempfile.TemporaryDirectory(prefix='mira-rig-state-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'
        self.settings = Path(self.directory.name)/'settings.json'
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.music.stop();game.opening_audio.reset();game.regional_audio.reset()
        self.games.clear();self.pygame.quit();gc.collect()

    def game(self, title=False):
        from main import Game
        game = Game(fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.settings)
        game.audio.effects_volume = 0;game.audio.music_volume = 0
        self.games.append(game)
        return game

    def test_save_continue_and_new_journey_keep_only_applied_rig_and_do_not_recruit_mira(self):
        game = self.game()
        party_before = game.party.to_dict()
        before = game._progress_signature()
        self.assertTrue(game.mira_rig.set_allocation(OFFENSIVE))
        self.assertNotEqual(before, game._progress_signature())
        self.assertEqual(game.party.to_dict(), party_before)
        self.assertTrue(game.save_progress())
        payload = json.loads(self.path.read_text())
        self.assertEqual(payload['mira_rig'], {'version': 1, 'allocation': OFFENSIVE})
        self.assertNotIn('bot_loadouts', payload)
        restored = self.game(title=True)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.mira_rig.allocation, OFFENSIVE)
        self.assertEqual(restored.party.to_dict(), party_before)
        self.assertTrue(restored.begin_journey(False, show_cinematic=False))
        self.assertEqual(restored.mira_rig.allocation, DEFAULT)

    def test_continue_migrates_old_loadout_once_and_preserves_resources_and_supplies(self):
        game = self.game()
        game.attributes.set_current(hp=77, mp=12)
        self.assertTrue(game.inventory.consume_bundle({'potion': 2}))
        self.assertTrue(game.save_progress())
        payload = json.loads(self.path.read_text())
        payload.pop('mira_rig');payload['bot_loadouts'] = deepcopy(RETIRED)
        self.path.write_text(json.dumps(payload))
        original = self.path.read_bytes()
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertEqual(self.path.read_bytes(), original)  # Inspecting Continue never writes.
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.mira_rig.allocation, DEFAULT)
        self.assertEqual((restored.attributes.current_hp, restored.attributes.current_mp), (77, 12))
        self.assertEqual(restored.inventory.to_dict(), payload['inventory'])
        updated = json.loads(self.path.read_text())
        self.assertNotIn('bot_loadouts', updated)
        self.assertEqual(updated['character_levels'], payload['character_levels'])
        self.assertEqual(updated['quests'], payload['quests'])
        self.assertEqual(updated['battle_rewards'], payload['battle_rewards'])

    def test_bad_modern_or_unrecognized_legacy_record_is_not_offered_as_continue(self):
        game = self.game();self.assertTrue(game.save_progress())
        payload = json.loads(self.path.read_text())
        for field, value in (('mira_rig', None),
                             ('bot_loadouts', {'version': 1, 'loadouts': {'mira': {
                                 'bot_id': 'unrecognized', 'ability_id': 'piston_jab'}}})):
            with self.subTest(field=field):
                bad = deepcopy(payload);bad[field] = value
                self.path.write_text(json.dumps(bad))
                original = self.path.read_bytes()
                self.assertIsNone(game._read_saved_journey())
                self.assertEqual(self.path.read_bytes(), original)


if __name__ == '__main__':unittest.main()
