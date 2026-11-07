"""Retired save rewards survive once without restoring an obsolete system."""
from copy import deepcopy
import json
import unittest

from character_attributes import ATTRIBUTE_CAPS, ATTRIBUTE_IDS, CharacterAttributes
from legacy_save import REWARDS_PATH, migrate_retired_progression


def retired_ledger(version=3):
    # These paths were captured from the original board implementation. No
    # original board module or asset is needed to import this old save.
    if version == 1:
        visited = ['blank_01', 'blank_05', 'def_02', 'hp_01', 'mend_01', 'origin', 'spr_02']
        activated, position, spent = ['hp_01', 'mend_01'], 'mend_01', 6
    else:
        visited = ['aether_dart_01', 'blank_01', 'blank_34', 'blank_35', 'def_04',
                   'hp_01', 'hp_04', 'mp_01', 'origin', 'str_01']
        activated, position, spent = ['aether_dart_01', 'hp_01'], 'aether_dart_01', 9
    state = {'rp': 1000000, 'spent_steps': spent, 'position': position,
             'visited': visited, 'activated': activated}
    if version == 3:state['legacy_activated'] = []
    return {'version': 2 if version == 3 else 1, 'board_id': 'caelan_starter',
            'board_version': version, 'characters': {'caelan': state},
            'receipts': ['legacy:paid']}


def legacy_journey(version=3, attribute_version=3):
    record = CharacterAttributes().to_dict()
    record['version'] = attribute_version
    paid_hp = 100 if version == 3 else 20
    if attribute_version < 3:record['attributes']['hp'] += paid_hp
    record['current_hp'] = 140+paid_hp-13
    record['current_mp'] = 7
    return {'version': 1, 'aether_lattice': retired_ledger(version),
            'character_attributes': record,
            'party': {'characters': {'caelan': deepcopy(record)}, 'keep': 'party facts'},
            'inventory': {'keep': ['paid crystals remain spent']},
            'quests': {'keep': ['quest progress']}}


class RetiredProgressionMigrationTests(unittest.TestCase):
    def test_current_rewards_fold_into_base_and_preserve_depleted_resources(self):
        original = legacy_journey()
        before = deepcopy(original)
        migrated = migrate_retired_progression(original)
        self.assertEqual(original, before)
        self.assertNotIn('aether_lattice', migrated)
        record = migrated['character_attributes']
        self.assertEqual(record['attributes']['hp'], 240)
        self.assertEqual((record['current_hp'], record['current_mp']), (227, 7))
        self.assertEqual(migrated['party']['characters']['caelan'], record)
        self.assertEqual(migrated['battle_rewards'], {'version': 1, 'receipts': ['legacy:paid']})
        self.assertEqual(migrated['character_abilities']['learned_abilities'], {'caelan': ['aether_dart']})
        for field in ('inventory', 'quests'):
            self.assertEqual(migrated[field], original[field])
        attributes = CharacterAttributes()
        self.assertTrue(attributes.restore(record))
        self.assertEqual(attributes.value('hp'), 240)
        self.assertEqual(attributes.current_hp, 227)

    def test_all_three_board_versions_keep_their_actual_paid_rewards(self):
        for version in (1, 2, 3):
            with self.subTest(version=version):
                migrated = migrate_retired_progression(legacy_journey(version))
                self.assertEqual(migrated['character_attributes']['attributes']['hp'],
                                 240 if version == 3 else 160)
                self.assertEqual(migrated['character_abilities']['learned_abilities'],
                                 {'caelan': ['mend' if version == 1 else 'aether_dart']})

    def test_aggregate_attribute_versions_do_not_add_the_same_rewards_twice(self):
        for board in (1, 2, 3):
            for attribute in (1, 2):
                with self.subTest(board=board, attribute=attribute):
                    original = legacy_journey(board, attribute)
                    migrated = migrate_retired_progression(original)
                    self.assertEqual(migrated['character_attributes'], original['character_attributes'])
                    self.assertEqual(migrated['party']['characters']['caelan'], original['character_attributes'])

    def test_tier_migration_provenance_uses_old_paid_reward_family(self):
        original = legacy_journey()
        state = original['aether_lattice']['characters']['caelan']
        state['activated'].append('hp_05')
        state['visited'].append('hp_05')
        state['spent_steps'] += 1
        state['legacy_activated'] = ['hp_05']
        original['character_attributes']['current_hp'] = 250
        original['party']['characters']['caelan'] = deepcopy(original['character_attributes'])
        migrated = migrate_retired_progression(original)
        # In v2 hp_05 paid +30HP; its current v3 reward is +10MP.
        self.assertEqual(migrated['character_attributes']['attributes']['hp'], 270)
        self.assertEqual(migrated['character_attributes']['attributes']['mp'], 30)
        self.assertEqual(migrated['character_attributes']['current_hp'], 250)

    def test_effective_caps_are_preserved_when_raw_rewards_exceed_them(self):
        original = legacy_journey()
        record = original['character_attributes']
        record['attributes'].update(hp=9950, str=999)
        record['current_hp'] = 9999
        state = original['aether_lattice']['characters']['caelan']
        state['activated'].append('str_01')
        original['party']['characters']['caelan'] = deepcopy(record)
        migrated = migrate_retired_progression(original)
        self.assertEqual(migrated['character_attributes']['attributes']['hp'], 9999)
        self.assertEqual(migrated['character_attributes']['attributes']['str'], 999)
        self.assertEqual(migrated['character_attributes']['current_hp'], 9999)
        self.assertTrue(CharacterAttributes().restore(migrated['character_attributes']))

    def test_existing_ability_history_and_equipment_are_merged_without_reset(self):
        original = legacy_journey()
        original['character_abilities'] = {
            'version': 1, 'characters': {'caelan': {'equipped_weapon': 'practice_sword',
                                                   'first_weapon_acquired': True}},
            'deferred_weapon_training': ['caelan'], 'gear_focus': {'caelan': 'water'},
            'learned_abilities': {'caelan': ['mend']}}
        migrated = migrate_retired_progression(original)
        expected = deepcopy(original['character_abilities'])
        expected['learned_abilities'] = {'caelan': ['aether_dart', 'mend']}
        self.assertEqual(migrated['character_abilities'], expected)

    def test_missing_ability_record_stays_unarmed_and_does_not_grant_other_skills(self):
        migrated = migrate_retired_progression(legacy_journey())
        record = migrated['character_abilities']
        self.assertEqual(set(record['characters']), {'caelan', 'mira', 'lucan', 'rhea', 'edran'})
        self.assertTrue(all(value == {'equipped_weapon': None, 'first_weapon_acquired': False}
                            for value in record['characters'].values()))
        self.assertEqual(record['learned_abilities'], {'caelan': ['aether_dart']})

    def test_receipts_merge_and_pending_and_awarded_spoils_keep_their_stage(self):
        for stage in ('pending', 'awarded'):
            with self.subTest(stage=stage):
                original = legacy_journey()
                original['battle_rewards'] = {'version': 1, 'receipts': ['already:new', 'legacy:paid']}
                original['post_battle'] = {'stage': stage, 'receipt': 'legacy:paid',
                                          'rewards': {'rp': 20, 'drops': {'aether_emerald': 1}}}
                migrated = migrate_retired_progression(original)
                self.assertEqual(migrated['battle_rewards']['receipts'], ['already:new', 'legacy:paid'])
                self.assertEqual(migrated['post_battle'], {'stage': stage, 'receipt': 'legacy:paid',
                                                         'rewards': {'drops': {'aether_emerald': 1}}})

    def test_migration_is_idempotent_and_returns_independent_objects(self):
        original = legacy_journey()
        first = migrate_retired_progression(original)
        second = migrate_retired_progression(first)
        self.assertEqual(first, second)
        second['character_attributes']['attributes']['hp'] = 1
        self.assertEqual(first['character_attributes']['attributes']['hp'], 240)
        self.assertEqual(original['character_attributes']['attributes']['hp'], 140)

    def test_unrelated_modern_journey_is_not_reinterpreted_as_xp(self):
        original = {'version': 1, 'character_attributes': CharacterAttributes().to_dict(),
                    'battle_rewards': {'version': 1, 'receipts': ['modern:receipt']},
                    'level_record': {'version': 1, 'character_id': 'caelan', 'total_xp': 200}}
        self.assertEqual(migrate_retired_progression(original), original)

    def test_deeply_nested_valid_json_rejects_as_value_error_without_mutation(self):
        # JSON accepts this depth, while deepcopy needs additional stack frames.
        # The converter's caller can therefore handle it as an ordinary bad save.
        raw = '{"nested":'+'['*600+'0'+']'*600+'}'
        original = json.loads(raw)
        nested = original['nested']
        before = json.dumps(original)
        with self.assertRaises(ValueError):migrate_retired_progression(original)
        self.assertIs(original['nested'], nested)
        self.assertEqual(json.dumps(original), before)

    def test_empty_legacy_record_without_attributes_is_supported(self):
        ledger = retired_ledger()
        ledger['characters']['caelan'] = {'rp': 0, 'spent_steps': 0, 'position': 'origin',
                                          'visited': ['origin'], 'activated': [], 'legacy_activated': []}
        migrated = migrate_retired_progression({'aether_lattice': ledger})
        self.assertEqual(migrated, {'battle_rewards': {'version': 1, 'receipts': ['legacy:paid']}})

    def test_malformed_legacy_records_reject_without_mutation_or_incidental_errors(self):
        baseline = legacy_journey()
        cases = []
        for field, values in {
                'version': (True, 1, 3), 'board_version': (True, 0, 4, '3', []),
                'board_id': ('unknown', None), 'characters': (None, [], {}),
                'receipts': (None, ['duplicate', 'duplicate'], [True], ['x'*129])}.items():
            for value in values:
                bad = deepcopy(baseline);bad['aether_lattice'][field] = value;cases.append(bad)
        for field, values in {
                'rp': (-1, True, 1.5, 1000000000), 'spent_steps': (-1, True, 1000000001),
                'position': ('missing', [], True), 'visited': (None, ['origin', 'origin'], [True]),
                'activated': (['origin'], ['hp_01', 'hp_01'], ['unknown'], [True]),
                'legacy_activated': (['unknown'], ['origin'], [True], ['hp_01', 'hp_01'])}.items():
            for value in values:
                bad = deepcopy(baseline);bad['aether_lattice']['characters']['caelan'][field] = value;cases.append(bad)
        missing = deepcopy(baseline);missing.pop('character_attributes');cases.append(missing)
        mismatch = deepcopy(baseline);mismatch['party']['characters']['caelan']['attributes']['hp'] = 141;cases.append(mismatch)
        invalid_hp = deepcopy(baseline);invalid_hp['character_attributes']['current_hp'] = 241
        invalid_hp['party']['characters']['caelan'] = deepcopy(invalid_hp['character_attributes']);cases.append(invalid_hp)
        for value in (None, {'version': True, 'receipts': []}, {'version': 1, 'receipts': [False]}):
            bad = deepcopy(baseline);bad['battle_rewards'] = value;cases.append(bad)
        for case in cases:
            with self.subTest(case=case):
                before = deepcopy(case)
                with self.assertRaises(ValueError):migrate_retired_progression(case)
                self.assertEqual(case, before)

    def test_compact_archive_contains_only_known_rewards_and_no_graph_or_ui(self):
        archive = json.loads(REWARDS_PATH.read_text())
        self.assertEqual(set(archive), {'version', 'board_id', 'boards'})
        self.assertEqual([len(archive['boards'][str(v)]) for v in (1, 2, 3)], [30, 200, 200])
        self.assertEqual(archive['boards']['2']['hp_05'], ['hp', 30])
        self.assertEqual(archive['boards']['3']['hp_05'], ['mp', 10])
        self.assertEqual(archive['boards']['3']['aether_dart_01'], ['ability', 'aether_dart'])
        for rewards in archive['boards'].values():
            for reward in rewards.values():
                self.assertIsInstance(reward, list)
                self.assertIn(len(reward), (0, 2))


if __name__ == '__main__':unittest.main()
