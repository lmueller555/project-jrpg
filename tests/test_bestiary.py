"""Canonical enemy storage, strict authoring and Cave Bat generation."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bestiary import (FIXED_FIELDS, build_enemy, fixed_enemy_definitions,
                      load_bestiary)
from character_attributes import ATTRIBUTE_IDS


class BestiaryGenerationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_bestiary()

    def test_existing_authored_encounters_keep_their_exact_records(self):
        expected = {
            'bat': {'name': 'Bat', 'attributes': dict(zip(ATTRIBUTE_IDS,
                     (72, 4, 7, 6, 3, 6, 5, 8, 10, 12, 4))),
                    'abilities': ['bite', 'wing_gust'],
                    'rewards': {'drops': {'aether_emerald': 1}}},
            'ridgeback_tusker': {'name': 'Ridgeback Tusker',
                    'attributes': dict(zip(ATTRIBUTE_IDS,
                     (700, 0, 12, 4, 4, 18, 12, 8, 12, 6, 4))),
                    'abilities': ['tusk_strike', 'prepare_charge', 'tusker_charge'],
                    'rewards': {'drops': {'aether_emerald': 1}}}}
        self.assertEqual(fixed_enemy_definitions(), expected)
        self.assertEqual(set(self.catalog['enemies']), {*expected, 'cave_bat'})
        for identifier, record in expected.items():
            generated = build_enemy(identifier)
            self.assertEqual(generated['combat'], record)
            self.assertIsNone(generated['level'])
            self.assertIsNone(generated['xp_reward'])
            self.assertIsNone(generated['behavior'])
            with self.assertRaises(ValueError):build_enemy(identifier, 1)

    def test_cave_bat_matches_every_approved_stat_and_reward(self):
        expected = {
            2: ((73, 5, 13, 14, 11, 13, 13, 13, 14, 15, 13), 84),
            3: ((85, 5, 15, 15, 13, 14, 14, 14, 15, 16, 15), 104)}
        for level, (values, xp) in expected.items():
            with self.subTest(level=level):
                enemy = build_enemy('cave_bat', level)
                self.assertEqual(tuple(enemy['combat']['attributes']), ATTRIBUTE_IDS)
                self.assertEqual(tuple(enemy['combat']['attributes'].values()), values)
                self.assertEqual(enemy['xp_reward'], xp)
                self.assertEqual(enemy['level'], level)
                self.assertEqual(enemy['combat']['name'], 'Cave Bat')
                self.assertEqual(set(enemy['combat']), FIXED_FIELDS)
                self.assertEqual(enemy['fighting_style'], 'physical_magical_alternation')
                self.assertEqual(enemy['behavior'], {
                    'sequence': ['cave_bat_bite', 'cave_bat_wing_gust'],
                    'fallback': 'cave_bat_bite', 'targeting': 'cycle_living_party'})

    def test_pending_loot_and_planned_mechanics_do_not_become_combat_rules(self):
        enemy = build_enemy('cave_bat', 2)
        self.assertEqual(enemy['combat']['rewards'], {'drops': {}})
        self.assertTrue(enemy['metadata']['drops_pending'])
        self.assertIsNone(enemy['metadata']['rewards']['drops'])
        self.assertEqual(enemy['metadata']['habitats'], ['elden_vale_sanctuary_caves'])
        self.assertEqual(enemy['metadata']['planned_mechanics'], {
            'elemental_affinities': {'status': 'planned',
                'multipliers': {'fire': 2, 'water': 1, 'ice': 1, 'nature': 1}},
            'stagger': {'status': 'planned', 'resistance': 'low'}})
        self.assertEqual(enemy['presentation'], {'sprite_id': 'bat',
            'action_aliases': {'cave_bat_bite': 'bite', 'cave_bat_wing_gust': 'wing_gust'}})
        self.assertNotIn('affinities', enemy['combat'])
        self.assertNotIn('xp', enemy['combat']['rewards'])

    def test_boss_records_derive_ten_times_xp_with_only_explicit_stat_adjustments(self):
        catalog = deepcopy(self.catalog)
        boss = catalog['enemies']['cave_bat']
        boss['tier'] = 'boss'
        boss['tier_multipliers'] = {'hp': 2}
        generated = build_enemy('cave_bat', 2, data=catalog)
        self.assertEqual(generated['xp_reward'], 840)
        self.assertEqual(generated['combat']['attributes']['hp'], 146)
        self.assertEqual(generated['combat']['attributes']['str'], 13)

    def test_composition_precedes_caps_and_optional_authored_drops_are_copied(self):
        catalog = deepcopy(self.catalog)
        entry = catalog['enemies']['cave_bat']
        entry['species_multipliers']['str'] = 100
        entry['tier_multipliers']['str'] = .01
        entry['rewards']['drops'] = {'aether_emerald': 1}
        enemy = build_enemy('cave_bat', 2, data=catalog)
        self.assertEqual(enemy['combat']['attributes']['str'], 13)
        self.assertEqual(enemy['combat']['rewards'], {'drops': {'aether_emerald': 1}})
        self.assertFalse(enemy['metadata']['drops_pending'])
        enemy['combat']['rewards']['drops']['aether_emerald'] = 9
        self.assertEqual(catalog['enemies']['cave_bat']['rewards']['drops']['aether_emerald'], 1)

    def test_future_registered_styles_remain_explicit_data(self):
        catalog = deepcopy(self.catalog)
        catalog['enemies']['cave_bat']['fighting_style'] = 'ally_healing'
        generated = build_enemy('cave_bat', 2, data=catalog)
        self.assertEqual(generated['fighting_style'], 'ally_healing')
        self.assertNotIn('ai_enabled', generated['combat'])

    def test_caller_must_select_a_supported_level_and_known_enemy(self):
        for level in (None, 0, 1, 4, 100, True, False, 2.0, '2', [], {}):
            with self.subTest(level=level):
                with self.assertRaises(ValueError):build_enemy('cave_bat', level)
        for identifier in ('missing', '', True, None, [], {}):
            with self.subTest(identifier=identifier):
                with self.assertRaises(ValueError):build_enemy(identifier, 2)

    def test_catalog_and_all_generated_nested_records_are_independent(self):
        before = deepcopy(self.catalog)
        generated = build_enemy('cave_bat', 2, data=self.catalog)
        generated['combat']['attributes']['hp'] = 999
        generated['behavior']['sequence'].clear()
        generated['presentation']['action_aliases'].clear()
        generated['metadata']['planned_mechanics']['stagger']['resistance'] = 'high'
        self.assertEqual(self.catalog, before)
        exported = load_bestiary(self.catalog)
        exported['enemies']['cave_bat']['species_multipliers']['hp'] = 2
        self.assertEqual(self.catalog, before)
        self.assertEqual(build_enemy('cave_bat', 2)['combat']['attributes']['hp'], 73)


class BestiaryValidationTests(unittest.TestCase):
    def setUp(self):self.catalog = load_bestiary()

    def test_invalid_fixed_profiles_and_reward_records_fail(self):
        cases = []
        for field, value in (('name', ''), ('abilities', ['missing']),
                             ('abilities', ['wing_gust']), ('abilities', ['bite', 'bite']),
                             ('rewards', {'rp': 20, 'drops': {}}),
                             ('rewards', {'drops': {'aether_emerald': True}})):
            data = deepcopy(self.catalog)
            data['enemies']['bat'][field] = value
            cases.append(data)
        for stat, value in (('hp', 0), ('mp', -1), ('speed', 256), ('str', 1000)):
            data = deepcopy(self.catalog)
            data['enemies']['bat']['attributes'][stat] = value
            cases.append(data)
        for data in cases:
            before = deepcopy(data)
            with self.subTest(data=data['enemies']['bat']):
                with self.assertRaises(ValueError):load_bestiary(data)
                self.assertEqual(data, before)

    def test_unknown_or_malformed_species_fields_fail_atomically(self):
        cases = [[], {}, {**self.catalog, 'version': True},
                 {**self.catalog, 'enemies': {}}, {**self.catalog, 'extra': 1}]
        fields = [
            ('mode', 'unknown'), ('name', ''), ('description', None), ('family', []),
            ('tier', 'elite'), ('tier', True), ('habitats', []), ('habitats', [['cave']]),
            ('habitats', ['cave', 'cave']), ('level_range', {'min': 3, 'max': 2}),
            ('level_range', {'min': True, 'max': 3}), ('level_range', {'min': 2, 'max': 101}),
            ('archetype', 'unknown'), ('stat_profile', 'unknown'), ('stat_profile', []),
            ('fighting_style', 'unknown'), ('species_multipliers', {'hp': 0}),
            ('species_multipliers', {'str': True}), ('species_multipliers', {'str': float('inf')}),
            ('species_multipliers', {'str': 10**1000}), ('tier_multipliers', {'attack': 2}),
            ('behavior', {'sequence': ['cave_bat_bite'], 'fallback': 'missing', 'targeting': 'cycle_living_party'}),
            ('behavior', {'sequence': ['cave_bat_wing_gust'], 'fallback': 'cave_bat_wing_gust', 'targeting': 'cycle_living_party'}),
            ('behavior', {'sequence': ['cave_bat_bite', 'cave_bat_bite'], 'fallback': 'cave_bat_bite', 'targeting': 'cycle_living_party'}),
            ('behavior', {'sequence': ['cave_bat_bite', 'cave_bat_wing_gust'], 'fallback': 'cave_bat_bite', 'targeting': 'weakest'}),
            ('presentation', {'sprite_id': '../bat', 'action_aliases': {}}),
            ('presentation', {'sprite_id': 'missing', 'action_aliases': {}}),
            ('presentation', {'sprite_id': 'bat', 'action_aliases': {'missing': 'bite'}}),
            ('presentation', {'sprite_id': 'bat', 'action_aliases': {'cave_bat_bite': 'missing'}}),
            ('rewards', {'drops': {'missing': 1}}), ('rewards', {'drops': {'aether_emerald': -1}}),
            ('planned_mechanics', {}), ('encounter_guidance', {'solo_count': True, 'party_count': 2})]
        for field, value in fields:
            data = deepcopy(self.catalog)
            data['enemies']['cave_bat'][field] = value
            cases.append(data)
        for field in self.catalog['enemies']['cave_bat']:
            data = deepcopy(self.catalog)
            del data['enemies']['cave_bat'][field]
            cases.append(data)
        for data in cases:
            before = deepcopy(data)
            with self.subTest(data=repr(data)[:180]):
                with self.assertRaises(ValueError):load_bestiary(data)
                self.assertEqual(data, before)

    def test_bad_planned_values_cannot_enable_unimplemented_mechanics(self):
        for section, field, value in (
                ('elemental_affinities', 'status', 'active'),
                ('elemental_affinities', 'multipliers', {'fire': True}),
                ('elemental_affinities', 'multipliers', {'fire': float('nan')}),
                ('elemental_affinities', 'multipliers', {'fire': 1.5}),
                ('stagger', 'status', 'active'), ('stagger', 'resistance', 99)):
            data = deepcopy(self.catalog)
            data['enemies']['cave_bat']['planned_mechanics'][section][field] = value
            with self.subTest(section=section, field=field):
                with self.assertRaises(ValueError):load_bestiary(data)

    def test_duplicate_json_keys_reject_silent_enemy_or_field_overwrites(self):
        entry = json.dumps(self.catalog['enemies']['cave_bat'])
        documents = [
            '{"version":1,"version":1,"enemies":{}}',
            '{"version":1,"enemies":{"cave_bat":'+entry+',"cave_bat":'+entry+'}}',
            json.dumps(self.catalog).replace('"name": "Cave Bat"', '"name": "Cave Bat", "name": "Other"')]
        with tempfile.TemporaryDirectory(prefix='bestiary-json-') as directory:
            path = Path(directory)/'catalog.json'
            for document in documents:
                path.write_text(document)
                with self.subTest(document=document[:70]), patch('bestiary.CATALOG_PATH', path):
                    with self.assertRaisesRegex(ValueError, 'Duplicate Bestiary key'):
                        load_bestiary()


if __name__ == '__main__':unittest.main()
