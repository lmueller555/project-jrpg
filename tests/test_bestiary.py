"""Canonical enemy storage, strict authoring and computed cave species."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bestiary import (ELEMENT_IDS, ELEMENT_NAMES, FIXED_FIELDS, build_enemy,
                      fixed_enemy_definitions, load_bestiary)
from character_attributes import ATTRIBUTE_IDS
from battle_model import load_actions


class BestiaryGenerationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_bestiary()

    def test_existing_authored_encounters_keep_their_exact_records(self):
        expected = {
            'bat': {'name': 'Bat', 'attributes': dict(zip(ATTRIBUTE_IDS,
                     (72, 4, 7, 6, 3, 6, 5, 8, 10, 12, 4))),
                    'abilities': ['bite', 'wing_gust'],
                    'rewards': {'drops': {'aether_emerald': 1}}}}
        self.assertEqual(fixed_enemy_definitions(), expected)
        self.assertEqual(set(self.catalog['enemies']),
                         {*expected, 'ridgeback_tusker', 'cave_bat', 'lithrusk', 'veylume', 'vespermaw', 'embravyr', 'nivareth'})
        for identifier, record in expected.items():
            generated = build_enemy(identifier)
            self.assertEqual(generated['combat'], record)
            self.assertIsNone(generated['level'])
            self.assertIsNone(generated['xp_reward'])
            self.assertIsNone(generated['behavior'])
            with self.assertRaises(ValueError):build_enemy(identifier, 1)

    def test_mq02_tusker_is_a_level_one_brute_boss_without_extra_stat_factors(self):
        from enemy_growth import profile_enemy_stats
        from battle_model import BattleModel
        from character_attributes import CharacterAttributes
        from post_battle import battle_reward_definition
        record = build_enemy('ridgeback_tusker', 1)
        self.assertEqual(record['combat']['attributes'], profile_enemy_stats('brute', 1))
        self.assertEqual(record['combat']['attributes']['hp'], 270)
        self.assertEqual(record['xp_reward'], 240)
        self.assertEqual(record['metadata']['tier'], 'boss')
        self.assertEqual(record['fighting_style'], 'telegraphed_windup')
        self.assertEqual(record['metadata']['species_multipliers'], {})
        self.assertEqual(record['metadata']['tier_multipliers'], {})
        self.assertEqual(record['combat']['abilities'], ['tusk_strike', 'prepare_charge', 'tusker_charge'])
        self.assertEqual(battle_reward_definition('mill'), {'drops': {'aether_emerald': 1}, 'xp': 240})
        for model in (BattleModel(CharacterAttributes(), enemy_id='ridgeback_tusker'),
                      BattleModel.from_bestiary(CharacterAttributes(), 'ridgeback_tusker', 1)):
            self.assertEqual(model.enemy_level, 1)
            self.assertEqual(model.enemy_xp_reward, 240)
            self.assertEqual(model.enemy_definition, record['combat'])
            self.assertIsNone(model._enemy_behavior, 'The original MQ02 targeting must remain in control')
        for level in (None, 2, True):
            with self.assertRaises(ValueError):build_enemy('ridgeback_tusker', level)

    def test_cave_bat_matches_every_approved_stat_and_reward(self):
        expected = {
            2: ((73, 5, 13, 14, 11, 13, 13, 13, 14, 15, 13), 32),
            3: ((85, 5, 15, 15, 13, 14, 14, 14, 15, 16, 15), 37)}
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
        catalog = deepcopy(self.catalog)
        catalog['enemies']['cave_bat']['rewards'] = {'drops': None}
        enemy = build_enemy('cave_bat', 2, data=catalog)
        self.assertEqual(enemy['combat']['rewards'], {'drops': {}})
        self.assertTrue(enemy['metadata']['drops_pending'])
        self.assertIsNone(enemy['metadata']['rewards']['drops'])
        self.assertEqual(enemy['metadata']['habitats'], ['elden_vale_sanctuary_caves'])
        self.assertEqual(enemy['metadata']['planned_mechanics'], {
            'stagger': {'status': 'planned', 'resistance': 'low'}})
        self.assertEqual(enemy['presentation'], {'sprite_id': 'bat',
            'action_aliases': {'cave_bat_bite': 'bite', 'cave_bat_wing_gust': 'wing_gust'}})
        self.assertNotIn('affinities', enemy['combat'])
        self.assertNotIn('elemental_profile', enemy['combat'])
        self.assertNotIn('xp', enemy['combat']['rewards'])

    def test_cave_bat_has_the_complete_approved_elemental_profile(self):
        self.assertEqual(ELEMENT_IDS, ('non_elemental', 'fire', 'electric', 'water',
                                      'ice', 'nature', 'wind', 'holy', 'ground'))
        self.assertEqual(tuple(ELEMENT_NAMES), ELEMENT_IDS)
        self.assertEqual(tuple(ELEMENT_NAMES.values()), (
            'Non-Elemental', 'Fire', 'Electric', 'Water', 'Ice', 'Nature', 'Wind',
            'Holy', 'Ground'))
        for level in (2, 3):
            with self.subTest(level=level):
                enemy = build_enemy('cave_bat', level)
                profile = enemy['metadata']['elemental_profile']
                self.assertEqual(profile['element'], 'non_elemental')
                self.assertEqual(profile['damage_percentages'],
                                 {element: 200 if element == 'fire' else 100
                                  for element in ELEMENT_IDS})
                self.assertEqual(profile['absorption'], {'elements': [], 'healing_percent': 100})
                self.assertIn('wing membranes', profile['design_rationale'])
                self.assertNotIn('elemental_affinities', enemy['metadata']['planned_mechanics'])
        for identifier in ('bat',):
            self.assertNotIn('elemental_profile', build_enemy(identifier)['metadata'])

    def test_new_cave_species_resolve_their_roles_and_full_elemental_profiles(self):
        expected = {
            'lithrusk': {'name': 'Lithrusk', 'levels': (2, 3),
                         'profile': 'armored', 'concept': 'bulwark',
                         'style': 'standard_attacks', 'element': 'ground',
                         'percentages': {'water': 150, 'electric': 50}},
            'veylume': {'name': 'Veylume', 'levels': (3, 4),
                        'profile': 'caster', 'concept': 'arcanist',
                        'style': 'magical_offense', 'element': 'electric',
                        'percentages': {'ground': 200}},
        }
        actions = load_actions()
        for identifier, design in expected.items():
            for level in design['levels']:
                with self.subTest(enemy=identifier, level=level):
                    enemy = build_enemy(identifier, level)
                    metadata = enemy['metadata']
                    stats = enemy['combat']['attributes']
                    self.assertEqual(enemy['combat']['name'], design['name'])
                    self.assertEqual(tuple(stats), ATTRIBUTE_IDS)
                    self.assertEqual(metadata['tier'], 'normal')
                    self.assertEqual(metadata['stat_profile'], design['profile'])
                    self.assertEqual(metadata['archetype'], design['concept'])
                    self.assertEqual(enemy['fighting_style'], design['style'])
                    self.assertEqual(metadata['habitats'], ['elden_vale_sanctuary_caves'])
                    self.assertEqual(metadata['level_range'],
                                     dict(zip(('min', 'max'), design['levels'])))
                    self.assertEqual(enemy['presentation'],
                                     {'sprite_id': identifier, 'action_aliases': {}})
                    self.assertFalse(metadata['presentation_pending'])
                    self.assertFalse(metadata['drops_pending'])
                    self.assertEqual(enemy['combat']['rewards'], {'drops': {}})
                    profile = metadata['elemental_profile']
                    self.assertEqual(profile['element'], design['element'])
                    self.assertEqual(profile['damage_percentages'],
                                     {element: design['percentages'].get(element, 100)
                                      for element in ELEMENT_IDS})
                    self.assertEqual(profile['absorption'],
                                     {'elements': [design['element']], 'healing_percent': 100})
                    self.assertTrue(profile['design_rationale'])
                    self.assertNotIn('elemental_profile', enemy['combat'])
                    self.assertEqual(metadata['planned_mechanics']['stagger']['status'], 'planned')
                    fallback = enemy['behavior']['fallback']
                    self.assertIn(fallback, enemy['behavior']['sequence'])
                    self.assertEqual(actions[fallback]['mp_cost'], 0)
                    self.assertIn(actions[fallback]['kind'], ('physical', 'magical'))
                    self.assertTrue(all(action.startswith(identifier+'_')
                                        for action in enemy['combat']['abilities']))
                    if identifier == 'lithrusk':
                        self.assertGreater(stats['def'], stats['m_def'])
                        self.assertTrue(all(actions[action]['kind'] == 'physical'
                                            for action in enemy['combat']['abilities']))
                    else:
                        self.assertGreater(stats['mag'], stats['str'])
                        paid_spells = [actions[action] for action in enemy['combat']['abilities']
                                       if actions[action]['kind'] == 'magical'
                                       and actions[action]['mp_cost'] > 0]
                        self.assertTrue(paid_spells)
                        self.assertLessEqual(max(action['mp_cost'] for action in paid_spells),
                                             stats['mp'])
                        self.assertLess(stats['mp'], 20)

    def test_new_species_keep_explicit_level_selection_and_detached_records(self):
        for identifier, valid_levels in (('lithrusk', (2, 3)), ('veylume', (3, 4))):
            for level in (None, valid_levels[0]-1, valid_levels[-1]+1, True, 3.0):
                with self.subTest(enemy=identifier, level=level), self.assertRaises(ValueError):
                    build_enemy(identifier, level)
            before = deepcopy(self.catalog)
            enemy = build_enemy(identifier, valid_levels[0], data=self.catalog)
            enemy['combat']['attributes']['hp'] = 1
            enemy['behavior']['sequence'].clear()
            enemy['metadata']['elemental_profile']['absorption']['elements'].clear()
            self.assertEqual(self.catalog, before)
            self.assertEqual(self.catalog['enemies'][identifier]['presentation']['sprite_id'], identifier)

    def test_new_species_level_profiles_and_normal_xp_are_stable(self):
        expected = {
            ('lithrusk', 2): ((120, 0, 11, 10, 13, 23, 8, 10, 14, 12, 13), 32),
            ('lithrusk', 3): ((140, 0, 13, 11, 14, 25, 10, 11, 15, 14, 15), 37),
            ('veylume', 3): ((67, 10, 7, 18, 16, 10, 17, 12, 15, 14, 15), 37),
            ('veylume', 4): ((82, 11, 8, 20, 17, 11, 19, 13, 17, 15, 16), 42),
        }
        for (identifier, level), (stats, xp) in expected.items():
            with self.subTest(enemy=identifier, level=level):
                enemy = build_enemy(identifier, level)
                self.assertEqual(tuple(enemy['combat']['attributes'].values()), stats)
                self.assertEqual(enemy['xp_reward'], xp)

    def test_cave_species_actions_keep_finite_magic_and_explicit_elemental_design(self):
        actions = load_actions()
        lithrusk = build_enemy('lithrusk', 2)
        self.assertEqual(lithrusk['behavior']['sequence'],
                         ['lithrusk_claw_clamp', 'lithrusk_shell_bash'])
        self.assertEqual(lithrusk['behavior']['fallback'], 'lithrusk_claw_clamp')
        for identifier, potency in (('lithrusk_claw_clamp', .65), ('lithrusk_shell_bash', .8)):
            self.assertEqual(actions[identifier]['kind'], 'physical')
            self.assertEqual(actions[identifier]['potency'], potency)
            self.assertEqual(actions[identifier]['mp_cost'], 0)
            self.assertEqual(actions[identifier]['element'], 'non_elemental')
        veylume = build_enemy('veylume', 3)
        self.assertEqual(veylume['behavior']['sequence'],
                         ['veylume_static_spark', 'veylume_gather_charge', 'veylume_veinflash'])
        self.assertEqual(veylume['behavior']['fallback'], 'veylume_static_spark')
        spark, prepare, flash = (actions[key] for key in veylume['behavior']['sequence'])
        self.assertEqual((spark['kind'], spark['potency'], spark['mp_cost'], spark['element']),
                         ('magical', .6, 0, 'electric'))
        self.assertEqual(prepare['kind'], 'prepare')
        self.assertNotIn('element', prepare)
        self.assertEqual((flash['kind'], flash['potency'], flash['mp_cost'], flash['element']),
                         ('magical', 1.0, 4, 'electric'))
        for level in (3, 4):
            self.assertEqual(build_enemy('veylume', level)['combat']['attributes']['mp']//flash['mp_cost'], 2)

    def test_existing_species_and_fixed_encounters_have_ready_presentation(self):
        for identifier, level in (('cave_bat', 2), ('bat', None), ('ridgeback_tusker', 1),
                                  ('lithrusk', 2), ('veylume', 3)):
            with self.subTest(enemy=identifier):
                self.assertFalse(build_enemy(identifier, level)['metadata']['presentation_pending'])

    def test_each_element_can_be_authored_with_arbitrary_damage_percentages(self):
        expected = dict(zip(ELEMENT_IDS, (0, 25, 75, 100, 125, 150, 175.5, 199.99, 200)))
        expected_combat = build_enemy('cave_bat', 2)['combat']
        for element in ELEMENT_IDS:
            with self.subTest(element=element):
                catalog = deepcopy(self.catalog)
                profile = catalog['enemies']['cave_bat']['elemental_profile']
                profile['element'] = element
                profile['damage_percentages'] = deepcopy(expected)
                profile['absorption']['elements'] = [] if element == 'non_elemental' else [element]
                # JSON data keeps exact authored values; matching-element
                # absorption takes precedence when combat later consumes it.
                catalog = json.loads(json.dumps(catalog))
                resolved = build_enemy('cave_bat', 2, data=catalog)
                self.assertEqual(resolved['metadata']['elemental_profile'], profile)
                self.assertEqual(resolved['metadata']['elemental_profile']['damage_percentages'], expected)
                self.assertEqual(resolved['combat'], expected_combat)

    def test_boss_records_derive_ten_times_xp_with_only_explicit_stat_adjustments(self):
        catalog = deepcopy(self.catalog)
        boss = catalog['enemies']['cave_bat']
        boss['tier'] = 'boss'
        boss['tier_multipliers'] = {'hp': 2}
        generated = build_enemy('cave_bat', 2, data=catalog)
        self.assertEqual(generated['xp_reward'], 320)
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
        generated['metadata']['elemental_profile']['damage_percentages']['fire'] = 50
        generated['metadata']['elemental_profile']['absorption']['elements'].append('fire')
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

    def test_pending_presentation_accepts_only_explicit_null_sprite_without_aliases(self):
        data = deepcopy(self.catalog)
        data['enemies']['cave_bat']['presentation'] = {'sprite_id': None, 'action_aliases': {}}
        before = deepcopy(data)
        enemy = build_enemy('cave_bat', 2, data=data)
        self.assertTrue(enemy['metadata']['presentation_pending'])
        self.assertEqual(data, before)
        invalid = (
            None, {}, {'sprite_id': None},
            {'sprite_id': None, 'action_aliases': []},
            {'sprite_id': None, 'action_aliases': {'cave_bat_bite': 'bite'}},
            {'sprite_id': None, 'action_aliases': {}, 'status': 'pending'},
            {'sprite_id': '', 'action_aliases': {}},
            {'sprite_id': False, 'action_aliases': {}},
            {'sprite_id': 'not_created_yet', 'action_aliases': {}},
        )
        for presentation in invalid:
            with self.subTest(presentation=presentation):
                malformed = deepcopy(data)
                malformed['enemies']['cave_bat']['presentation'] = presentation
                with self.assertRaises(ValueError):load_bestiary(malformed)

    def test_ready_presentation_rejects_an_action_without_a_real_animation(self):
        data = deepcopy(self.catalog)
        # The action exists, so checking only the global action dictionary
        # would silently admit a pose that the real Bat art cannot render.
        data['enemies']['cave_bat']['presentation']['action_aliases']['cave_bat_bite'] = 'rig_activation'
        with self.assertRaises(ValueError):
            load_bestiary(data)

    def test_bad_stagger_values_cannot_enable_unimplemented_mechanics(self):
        for field, value in (('status', 'active'), ('resistance', 99)):
            data = deepcopy(self.catalog)
            data['enemies']['cave_bat']['planned_mechanics']['stagger'][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):load_bestiary(data)

    def test_invalid_elemental_profiles_fail_without_mutation(self):
        valid = self.catalog['enemies']['cave_bat']['elemental_profile']
        cases = [None, [], {}, {**valid, 'extra': 1}]
        for key in valid:
            profile = deepcopy(valid)
            del profile[key]
            cases.append(profile)
        for element in ('poison', 'lightning', 'Non-Elemental', '', None, [], True):
            cases.append({**valid, 'element': element})
        for value in (-1, 201, True, False, float('inf'), float('-inf'), float('nan'),
                      10**1000, '100', None, [], {}):
            profile = deepcopy(valid)
            profile['damage_percentages']['fire'] = value
            cases.append(profile)
        for percentages in (None, [], {}, {'fire': 200},
                            {**valid['damage_percentages'], 'poison': 100}):
            cases.append({**valid, 'damage_percentages': percentages})
        for element in ELEMENT_IDS:
            profile = deepcopy(valid)
            del profile['damage_percentages'][element]
            cases.append(profile)
        for rationale in ('', '   ', None, {}, 'x'*2001):
            cases.append({**valid, 'design_rationale': rationale})
        for absorption in (None, [], {}, {'elements': [], 'healing_percent': True},
                           {'elements': [], 'healing_percent': 50},
                           {'elements': [], 'healing_percent': 100.0},
                           {'elements': [], 'healing_percent': 100, 'extra': 1},
                           {'elements': 'fire', 'healing_percent': 100},
                           {'elements': ['non_elemental'], 'healing_percent': 100},
                           {'elements': ['fire'], 'healing_percent': 100}):
            cases.append({**valid, 'absorption': absorption})
        for index, profile in enumerate(cases):
            data = deepcopy(self.catalog)
            data['enemies']['cave_bat']['elemental_profile'] = deepcopy(profile)
            before = deepcopy(data)
            with self.subTest(index=index):
                with self.assertRaises(ValueError):load_bestiary(data)
                self.assertEqual(data, before)

    def test_typed_enemies_must_absorb_only_their_own_element_at_full_strength(self):
        for element in ELEMENT_IDS[1:]:
            for absorbed in ([], ['non_elemental'], ['poison'], [element, element],
                             [element, 'non_elemental']):
                data = deepcopy(self.catalog)
                profile = data['enemies']['cave_bat']['elemental_profile']
                profile['element'] = element
                profile['absorption']['elements'] = absorbed
                with self.subTest(element=element, absorbed=absorbed):
                    with self.assertRaises(ValueError):load_bestiary(data)

    def test_obsolete_partial_affinity_map_is_rejected(self):
        data = deepcopy(self.catalog)
        data['enemies']['cave_bat']['planned_mechanics']['elemental_affinities'] = {
            'status': 'planned', 'multipliers': {'fire': 2}}
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
