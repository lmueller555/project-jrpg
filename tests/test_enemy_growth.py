"""Approved enemy profiles compose once while encounter and AI tuning stay explicit."""
from copy import deepcopy
import unittest

from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from enemy_growth import (CONCEPT_IDS, ENEMY_STAT_CAPS, MAX_ENEMY_HP,
                          REFERENCE_CHARACTER_IDS, STAT_PROFILE_IDS,
                          baseline_enemy_stats, build_enemy_stats,
                          load_archetypes, profile_enemy_stats,
                          profile_multipliers, raw_baseline_enemy_stats)
from leveling import character_stats


APPROVED_PROFILE_ROWS = {
    # HP, MP, STR, MAG, SPR, DEF, MDEF, Speed, Accuracy, Evasion, Luck.
    'balanced': (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    'brute': (1.50, .50, 1.15, .60, .75, 1.10, .75, .75, 1, 1, 1),
    'armored': (1.25, .75, .90, .75, .90, 1.60, .60, .80, 1, 1, 1),
    'warded': (1.10, 1.25, .90, .90, 1.10, .65, 1.60, .90, 1, 1, 1),
    'swift': (.80, .75, 1, .75, .75, .85, .85, 1.40, 1.20, 1, 1),
    'evasive': (.70, .75, .90, .90, .75, .75, .85, 1.15, 1, 1.50, 1),
    'caster': (.75, 1.50, .50, 1.20, 1, .65, 1.10, .90, 1, 1, 1),
    'hybrid': (.95, 1.15, 1.05, 1.05, .80, .90, .90, 1, 1, 1, 1),
    'support': (1, 1.50, .55, .60, 1.35, .90, 1.15, 1, 1, 1, 1),
    'lightweight': (.40, .50, .65, .65, .60, .70, .70, 1, 1, 1, 1),
}


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

    def test_approved_twenty_concepts_and_ten_profiles_have_exact_weights(self):
        self.assertEqual(tuple(self.catalog['stat_profiles']), STAT_PROFILE_IDS)
        self.assertEqual(tuple(self.catalog['concepts']), CONCEPT_IDS)
        self.assertEqual(len(self.catalog['concepts']), 20)
        self.assertEqual(self.catalog['runtime_binding'], 'metadata_only')
        for identifier, profile in self.catalog['stat_profiles'].items():
            self.assertEqual(tuple(profile['multipliers']), ATTRIBUTE_IDS)
            self.assertEqual(tuple(profile['multipliers'].values()),
                             APPROVED_PROFILE_ROWS[identifier])
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
                ('stat_profiles', 'brute', 'multipliers', None),
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

    def test_profile_weights_reject_missing_extra_invalid_and_boolean_values(self):
        invalid = [None, [], True, -1, float('nan'), float('inf'),
                   '1.15', {'value': 1}, 10**1000]
        for value in invalid:
            with self.subTest(value=repr(value)[:80]):
                record = deepcopy(self.catalog)
                record['stat_profiles']['brute']['multipliers']['str'] = value
                original = deepcopy(record)
                with self.assertRaises(ValueError):load_archetypes(record)
                self.assertEqual(record, original)
        for change in ('missing', 'extra', 'zero_hp'):
            with self.subTest(change=change):
                record = deepcopy(self.catalog)
                weights = record['stat_profiles']['brute']['multipliers']
                if change == 'missing':weights.pop('lck')
                elif change == 'extra':weights['attack'] = 1
                else:weights['hp'] = 0
                with self.assertRaises(ValueError):load_archetypes(record)


class NamedEnemyProfileTests(unittest.TestCase):
    def test_all_ten_profiles_grow_monotonically_within_caps_at_every_level(self):
        for identifier in STAT_PROFILE_IDS:
            previous = None
            for level in range(1, 101):
                with self.subTest(profile=identifier, level=level):
                    values = profile_enemy_stats(identifier, level)
                    self.assertEqual(tuple(values), ATTRIBUTE_IDS)
                    for key, value in values.items():
                        self.assertIs(type(value), int)
                        self.assertGreaterEqual(value, 1 if key == 'hp' else 0)
                        self.assertLessEqual(value, ENEMY_STAT_CAPS[key])
                        if previous:self.assertGreaterEqual(value, previous[key])
                    previous = values

    def test_named_balanced_profile_matches_baseline_without_rebalancing(self):
        for level in (1, 11, 25, 50, 75, 100):
            with self.subTest(level=level):
                self.assertEqual(profile_enemy_stats('balanced', level),
                                 baseline_enemy_stats(level))

    def test_approved_examples_use_unrounded_baselines(self):
        expected = {
            'brute': {'hp': 75000, 'str': 293, 'speed': 95},
            'armored': {'hp': 62500, 'def': 460, 'm_def': 174},
            'warded': {'hp': 55000, 'def': 187, 'm_def': 464},
            'swift': {'hp': 40000, 'speed': 177, 'acc': 324},
            'evasive': {'hp': 35000, 'eva': 319},
            'caster': {'hp': 37500, 'mag': 321, 'mp': 803},
            'support': {'hp': 50000, 'spr': 368, 'mp': 803},
            'lightweight': {'hp': 20000, 'str': 166, 'mag': 174},
        }
        for identifier, selected in expected.items():
            with self.subTest(profile=identifier):
                values = profile_enemy_stats(identifier, 100)
                self.assertEqual({key: values[key] for key in selected}, selected)
        # 12.75 Defense ×1.60 =20.4: rounding baseline first would give21.
        self.assertEqual(profile_enemy_stats('armored', 1)['def'], 20)
        self.assertEqual(profile_enemy_stats('brute', 1)['hp'], 270)
        self.assertEqual(profile_enemy_stats('lightweight', 1)['hp'], 72)

    def test_species_and_tier_layers_apply_before_rounding_and_caps(self):
        species, tier = {'eva': .5, 'str': 10, 'hp': MAX_ENEMY_HP}, {'str': .1, 'hp': 1/MAX_ENEMY_HP}
        before = deepcopy((species, tier))
        values = profile_enemy_stats('evasive', 100, species_multipliers=species,
                                     tier_multipliers=tier)
        # 212.5 ×1.5 ×0.5 =159.375; rounding the profile first gives160.
        self.assertEqual(values['eva'], 159)
        self.assertEqual(values['str'], 230)
        self.assertEqual(values['hp'], 35000)
        self.assertEqual((species, tier), before)
        capped = profile_enemy_stats('brute', 100,
                                     species_multipliers={'str': 100, 'mp': 100, 'speed': 100},
                                     tier_multipliers={'hp': 100000})
        self.assertEqual((capped['str'], capped['mp'], capped['speed']), (999, 999, 255))
        self.assertEqual(capped['hp'], MAX_ENEMY_HP)
        zero = profile_enemy_stats('caster', 1, species_multipliers={'mag': 0, 'hp': 1e-20})
        self.assertEqual((zero['mag'], zero['hp']), (0, 1))

    def test_unknown_profiles_and_invalid_layers_are_rejected(self):
        for identifier in (None, True, 1, [], {}, '', 'unknown'):
            with self.subTest(profile=repr(identifier)):
                with self.assertRaises(ValueError):profile_multipliers(identifier)
                with self.assertRaises(ValueError):profile_enemy_stats(identifier, 1)
        for level in (0, 101, True, 1.0, None):
            with self.subTest(level=level):
                with self.assertRaises(ValueError):profile_enemy_stats('brute', level)
        for layer in ([], True, {'attack': 2}, {'hp': 0}, {'mag': -1},
                      {'mag': True}, {'str': float('nan')}, {'str': 10**1000}):
            for argument in ('species_multipliers', 'tier_multipliers'):
                with self.subTest(layer=repr(layer)[:80], argument=argument):
                    with self.assertRaises(ValueError):
                        profile_enemy_stats('brute', 1, **{argument: layer})

    def test_profile_getters_and_results_do_not_expose_shared_mutable_state(self):
        weights = profile_multipliers('brute')
        stats = profile_enemy_stats('brute', 100)
        weights['str'] = stats['str'] = 0
        self.assertEqual(profile_multipliers('brute')['str'], 1.15)
        self.assertEqual(profile_enemy_stats('brute', 100)['str'], 293)
        self.assertEqual(profile_multipliers('balanced'), dict.fromkeys(ATTRIBUTE_IDS, 1))


if __name__ == '__main__':unittest.main()
