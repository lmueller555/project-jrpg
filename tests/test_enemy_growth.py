"""Enemy growth preserves the approved reference and keeps unauthored AI explicit."""
from copy import deepcopy
import unittest

from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from enemy_growth import (CONCEPT_IDS, ENEMY_STAT_CAPS, MAX_ENEMY_HP,
                          REFERENCE_CHARACTER_IDS, STAT_PROFILE_IDS,
                          baseline_enemy_stats, build_enemy_stats,
                          load_archetypes, raw_baseline_enemy_stats)
from leveling import character_stats


class EnemyGrowthTests(unittest.TestCase):
    def test_approved_level_one_and_level_one_hundred_anchors(self):
        self.assertEqual(list(baseline_enemy_stats(1).values()),
                         [180, 41, 11, 12, 13, 13, 13, 12, 13, 11, 12])
        self.assertEqual(list(baseline_enemy_stats(100).values()),
                         [50000, 535, 255, 268, 273, 288, 290, 127, 270, 213, 240])

    def test_steeper_hp_curve_matches_approved_checkpoints(self):
        expected = {1: 180, 10: 845, 25: 4067, 50: 14228,
                    75: 29684, 90: 41310, 100: 50000}
        for level, hp in expected.items():
            with self.subTest(level=level):
                self.assertEqual(baseline_enemy_stats(level)['hp'], hp)

    def test_all_levels_are_monotonic_and_bounded(self):
        previous = None
        for level in range(1, 101):
            current = baseline_enemy_stats(level)
            with self.subTest(level=level):
                self.assertEqual(tuple(current), ATTRIBUTE_IDS)
                for key in ATTRIBUTE_IDS:
                    self.assertIs(type(current[key]), int)
                    self.assertGreaterEqual(current[key], 1 if key == 'hp' else 0)
                    self.assertLessEqual(current[key], ENEMY_STAT_CAPS[key])
                    if previous:self.assertGreaterEqual(current[key], previous[key])
            previous = current

    def test_reference_averages_unrounded_character_curves(self):
        # At level 11, averaging already-rounded character Spirit gives 25.4,
        # which would round to 32 after scaling. The approved raw reference is 31.
        rounded_reference = sum(character_stats(name, 11)['spr']
                                for name in REFERENCE_CHARACTER_IDS)/5
        self.assertEqual(rounded_reference, 25.4)
        self.assertEqual(baseline_enemy_stats(11)['spr'], 31)
        self.assertAlmostEqual(raw_baseline_enemy_stats(100)['def'], 287.5)
        self.assertEqual(baseline_enemy_stats(100)['def'], 288)

    def test_reference_does_not_depend_on_live_character_modifiers(self):
        before = baseline_enemy_stats(50)
        attributes = CharacterAttributes()
        self.assertTrue(attributes.set_modifiers('equipment', {'str': 200, 'mag': 300}))
        self.assertTrue(attributes.set_current(hp=1, mp=0))
        self.assertEqual(baseline_enemy_stats(50), before)
        self.assertEqual(REFERENCE_CHARACTER_IDS,
                         ('caelan', 'mira', 'lucan', 'rhea', 'edran'))

    def test_author_multipliers_apply_before_rounding_and_caps(self):
        values = build_enemy_stats(100, multipliers={'mag': 1.5, 'spr': 2, 'speed': .5})
        self.assertEqual(values['mag'], 401)
        self.assertEqual(values['spr'], 545)
        self.assertEqual(values['speed'], 63)
        self.assertEqual(values['hp'], 50000)
        weights = {'hp': 20, 'str': 4, 'mag': 0, 'mp': 3, 'speed': 3}
        original = dict(weights)
        capped = build_enemy_stats(100, multipliers=weights)
        self.assertEqual(capped['hp'], 1000000)
        self.assertEqual(capped['str'], 999)
        self.assertEqual(capped['mag'], 0)
        self.assertEqual(capped['mp'], 999)
        self.assertEqual(capped['speed'], 255)
        self.assertEqual(weights, original)
        self.assertEqual(build_enemy_stats(100, multipliers={'hp': MAX_ENEMY_HP})['hp'], MAX_ENEMY_HP)
        self.assertEqual(build_enemy_stats(1, multipliers={'hp': 1e-20})['hp'], 1)

    def test_multipliers_are_explicit_and_invalid_values_fail_cleanly(self):
        with self.assertRaises(TypeError):build_enemy_stats(1)
        invalid = [None, [], 2, {'attack': 2}, {'str': -1}, {'hp': 0},
                   {'hp': False}, {'speed': True}, {'str': float('nan')},
                   {'str': float('inf')}, {'str': -float('inf')},
                   {'str': '2'}, {'str': {}}, {'str': 10**1000}]
        before = baseline_enemy_stats(1)
        for weights in invalid:
            with self.subTest(weights=repr(weights)[:80]):
                with self.assertRaises(ValueError):build_enemy_stats(1, multipliers=weights)
                self.assertEqual(baseline_enemy_stats(1), before)

    def test_level_validation_is_strict_and_outputs_are_independent(self):
        for level in (0, 101, True, False, 1.0, '1', None, [], {}):
            with self.subTest(level=level):
                with self.assertRaises(ValueError):baseline_enemy_stats(level)
                with self.assertRaises(ValueError):raw_baseline_enemy_stats(level)
        values = baseline_enemy_stats(50)
        raw = raw_baseline_enemy_stats(50)
        values['hp'] = raw['hp'] = 0
        self.assertEqual(baseline_enemy_stats(50)['hp'], 14228)


class EnemyArchetypeCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_archetypes()

    def test_approved_twenty_concepts_and_ten_profiles_have_no_invented_weights(self):
        self.assertEqual(tuple(self.catalog['stat_profiles']), STAT_PROFILE_IDS)
        self.assertEqual(tuple(self.catalog['concepts']), CONCEPT_IDS)
        self.assertEqual(len(self.catalog['concepts']), 20)
        self.assertEqual(self.catalog['runtime_binding'], 'metadata_only')
        for profile in self.catalog['stat_profiles'].values():
            self.assertIsNone(profile['multipliers'])
        for concept in self.catalog['concepts'].values():
            self.assertIn(concept['stat_profile'], self.catalog['stat_profiles'])
            self.assertIn(concept['fighting_style'], self.catalog['fighting_styles'])

    def test_bat_and_boar_references_separate_stats_from_behavior(self):
        references = self.catalog['enemy_references']
        self.assertEqual(references['bat']['stat_profile'], 'hybrid')
        self.assertEqual(references['bat']['fighting_style'], 'physical_magical_alternation')
        self.assertEqual(references['ridgeback_tusker']['stat_profile'], 'brute')
        self.assertEqual(references['ridgeback_tusker']['fighting_style'], 'telegraphed_windup')
        for enemy in references.values():self.assertIsNone(enemy['species_adjustments'])

    def test_behavior_requirements_are_explicit_metadata(self):
        styles = self.catalog['fighting_styles']
        self.assertEqual(styles['physical_magical_alternation']['implementation'], 'existing_pattern')
        self.assertEqual(styles['telegraphed_windup']['implementation'], 'existing_pattern')
        self.assertIn('enemy_healing_actions', styles['ally_healing']['requirements'])
        self.assertIn('interception_rules', styles['ally_interception']['requirements'])
        self.assertIn('atb_reduction_actions', styles['atb_disruption']['requirements'])
        self.assertIn('multi_enemy_encounters', self.catalog['concepts']['swarmer']['requirements'])

    def test_catalog_input_and_exports_are_not_mutated(self):
        original = deepcopy(self.catalog)
        exported = load_archetypes(self.catalog)
        exported['stat_profiles']['balanced']['description'] = 'Changed'
        exported['enemy_references']['bat']['stat_profile'] = 'caster'
        self.assertEqual(self.catalog, original)
        self.assertEqual(load_archetypes(), original)

    def test_invalid_schema_and_dangling_references_fail_without_changes(self):
        records = [[], {}, {**self.catalog, 'version': True},
                   {**self.catalog, 'runtime_binding': 'live_ai'},
                   {**self.catalog, 'reference_characters': ['caelan']}]
        for section, identifier, field, value in (
                ('stat_profiles', 'brute', 'multipliers', {'str': 2}),
                ('stat_profiles', 'brute', 'high_stats', ['unknown']),
                ('stat_profiles', 'brute', 'high_stats', ['str', 'str']),
                ('stat_profiles', 'brute', 'low_stats', ['str']),
                ('fighting_styles', 'ally_healing', 'implementation', 'implemented'),
                ('fighting_styles', 'ally_healing', 'requirements', [False]),
                ('concepts', 'mender', 'stat_profile', 'unknown'),
                ('concepts', 'mender', 'fighting_style', 'unknown'),
                ('concepts', 'mender', 'stat_profile', []),
                ('enemy_references', 'bat', 'fighting_style', None),
                ('enemy_references', 'bat', 'species_adjustments', {'eva': 1.1})):
            record = deepcopy(self.catalog)
            record[section][identifier][field] = value
            records.append(record)
        for section in ('stat_profiles', 'concepts', 'enemy_references'):
            record = deepcopy(self.catalog)
            record[section].pop(next(iter(record[section])))
            records.append(record)
        for record in records:
            with self.subTest(record=repr(record)[:100]):
                before = deepcopy(record)
                with self.assertRaises(ValueError):load_archetypes(record)
                self.assertEqual(record, before)


if __name__ == '__main__':unittest.main()
