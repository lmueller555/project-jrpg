"""Approved miniboss authoring remains inspectable without art or new combat rules."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from battle_model import BattleModel, load_actions
from bestiary import ELEMENT_IDS, build_enemy, load_bestiary
from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from combat_damage import calculate_damage
from leveling import character_stats


ROOT = Path(__file__).resolve().parents[1]
SEQUENCE = ['vespermaw_'+name for name in (
    'raking_claw', 'confluence_roar', 'gather_resonance', 'ruinous_pounce', 'exhausted')]


class VespermawBestiaryTests(unittest.TestCase):
    def test_exact_level_seven_profile_rewards_and_elemental_relationships(self):
        record = build_enemy('vespermaw', 7)
        self.assertEqual(record['combat']['attributes'], dict(zip(ATTRIBUTE_IDS,
                         (1877, 29, 24, 18, 17, 26, 18, 11, 23, 19, 21))))
        self.assertEqual(record['xp_reward'], 1110)
        self.assertEqual(record['combat']['rewards']['drops'],
                         {'aether_amethyst': 1, 'aether_sapphire': 1})
        metadata = record['metadata']
        self.assertEqual((metadata['tier'], metadata['archetype'], metadata['stat_profile']),
                         ('boss', 'windup_attacker', 'brute'))
        self.assertEqual(metadata['level_range'], {'min': 7, 'max': 7})
        self.assertEqual(metadata['planned_mechanics']['stagger'],
                         {'status': 'planned', 'resistance': 'normal'})
        profile = metadata['elemental_profile']
        self.assertEqual(profile['element'], 'ground')
        self.assertEqual(profile['damage_percentages'],
                         {key: {'electric': 50, 'water': 150}.get(key, 100)
                          for key in ELEMENT_IDS})
        self.assertEqual(profile['absorption'], {'elements': ['ground'], 'healing_percent': 100})
        for level in (None, 6, 8, True, 7.0):
            with self.subTest(level=level), self.assertRaises(ValueError):
                build_enemy('vespermaw', level)

    def test_full_combat_design_is_retained_without_approximating_unsupported_actions(self):
        record = build_enemy('vespermaw', 7)
        design = record['metadata']['combat_design']
        self.assertFalse(record['metadata']['combat_pending'])
        self.assertFalse(record['metadata']['presentation_pending'])
        self.assertFalse(record['metadata']['drops_pending'])
        self.assertEqual(record['presentation'], {'sprite_id': 'vespermaw',
            'action_aliases': {key: key.removeprefix('vespermaw_') for key in SEQUENCE}})
        self.assertEqual(design['status'], 'ready')
        self.assertEqual(record['behavior']['sequence'], SEQUENCE)
        self.assertEqual(record['combat']['abilities'], SEQUENCE)
        self.assertEqual(record['behavior']['fallback'], SEQUENCE[0])
        claw, roar, prepare, pounce, recover = (design['actions'][key] for key in SEQUENCE)
        self.assertEqual((claw['kind'], claw['potency'], claw['mp_cost']), ('physical', .65, 0))
        self.assertEqual((roar['kind'], roar['target'], roar['potency'], roar['mp_cost']),
                         ('magical', 'all_opponents', .5, 6))
        self.assertEqual(prepare['kind'], 'prepare')
        self.assertEqual((pounce['kind'], pounce['target'], pounce['potency']),
                         ('physical', 'opponent', 1.4))
        self.assertEqual((recover['kind'], recover['target']), ('recover', 'self'))
        self.assertEqual(design['windup']['minimum_target_actions'], 1)
        self.assertEqual(design['windup']['retargeting'], 'repeat_warning')
        self.assertEqual(design['recovery']['damage_taken_multiplier'], 1.25)
        self.assertEqual(design['encounter'],
                         {'trigger': 'story', 'repeatable': False, 'formation_size': 1})
        # Live definitions match the complete approved design.
        actions = load_actions()
        for key in SEQUENCE:
            self.assertTrue(design['actions'][key].items() <= actions[key].items())

    def test_records_are_detached_and_local_actions_cannot_override_live_actions(self):
        catalog = load_bestiary()
        before = deepcopy(catalog)
        record = build_enemy('vespermaw', 7, data=catalog)
        record['metadata']['combat_design']['actions'][SEQUENCE[1]]['target'] = 'opponent'
        record['combat']['rewards']['drops'].clear()
        self.assertEqual(catalog, before)
        boss = catalog['enemies']['vespermaw']
        # Consistently rename one local action to a real live action ID.
        boss['combat_design']['actions']['bite'] = boss['combat_design']['actions'].pop(SEQUENCE[0])
        boss['behavior']['sequence'][0] = boss['behavior']['fallback'] = 'bite'
        boss['combat_design']['recovery']['ends_before_action'] = 'bite'
        with self.assertRaisesRegex(ValueError, 'match its live actions'):
            load_bestiary(catalog)

    def test_pending_combat_cannot_construct_single_or_group_battles_even_with_art(self):
        catalog = load_bestiary()
        catalog['enemies']['vespermaw']['combat_design']['status'] = 'pending_runtime'
        source = CharacterAttributes()
        before = source.to_dict()
        for art_ready in (False, True):
            with self.subTest(art_ready=art_ready):
                catalog['enemies']['vespermaw']['presentation'] = (
                    {'sprite_id': 'vespermaw', 'action_aliases':
                     {key: key.removeprefix('vespermaw_') for key in SEQUENCE}}
                    if art_ready else {'sprite_id': None, 'action_aliases': {}})
                self.assertEqual(build_enemy('vespermaw', 7, data=catalog)
                                 ['metadata']['presentation_pending'], not art_ready)
                with patch.object(BattleModel, '__init__', side_effect=AssertionError('Battle began')):
                    with self.assertRaisesRegex(ValueError, 'combat implementation is pending'):
                        BattleModel.from_bestiary(source, 'vespermaw', 7, bestiary_data=catalog)
                    with self.assertRaisesRegex(ValueError, 'combat implementation is pending'):
                        BattleModel.from_bestiary_group(source, [
                            {'enemy_id': 'cave_bat', 'level': 2},
                            {'enemy_id': 'vespermaw', 'level': 7}], bestiary_data=catalog)
        self.assertEqual(source.to_dict(), before)

    def test_pending_design_pose_aliases_require_real_states_and_stay_local(self):
        catalog = load_bestiary()
        catalog['enemies']['vespermaw']['presentation']['action_aliases'][SEQUENCE[0]] = 'missing_claw'
        with self.assertRaisesRegex(ValueError, 'authored animation states'):
            load_bestiary(catalog)
        # Existing live-action aliases still refer to action definitions.
        catalog = load_bestiary()
        catalog['enemies']['cave_bat']['presentation']['action_aliases']['cave_bat_bite'] = 'idle'
        with self.assertRaisesRegex(ValueError, 'Invalid Bestiary presentation'):
            load_bestiary(catalog)

    def test_proposed_damage_envelope_uses_current_party_growth_and_guard(self):
        boss = build_enemy('vespermaw', 7)['combat']['attributes']
        for level in (5, 6, 7):
            for identifier in ('caelan', 'mira', 'lucan'):
                with self.subTest(level=level, character=identifier):
                    character = character_stats(identifier, level)
                    claw = calculate_damage(boss['str'], character['def'], .65)
                    roar = calculate_damage(boss['mag'], character['m_def'], .5)
                    pounce = calculate_damage(boss['str'], character['def'], 1.4)
                    guarded = calculate_damage(boss['str'], character['def'], 1.4, protected=True)
                    self.assertTrue(60 <= claw <= 65)
                    self.assertTrue(27 <= roar <= 28)
                    self.assertTrue(131 <= pounce <= 140)
                    self.assertTrue(65 <= guarded <= 70)

    def test_preview_formats_expose_pending_design_without_creating_files(self):
        with tempfile.TemporaryDirectory(prefix='vespermaw-preview-') as directory:
            for format_name in ('json', 'csv', 'markdown'):
                with self.subTest(format=format_name):
                    result = subprocess.run([sys.executable, str(ROOT/'tools/preview_bestiary.py'),
                        '--enemy', 'vespermaw', '--levels', '7', '--format', format_name],
                        cwd=directory, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if format_name == 'json':
                        records = json.loads(result.stdout)
                        self.assertEqual(len(records), 1)
                        self.assertFalse(records[0]['metadata']['combat_pending'])
                        self.assertEqual(records[0]['metadata']['combat_design']['actions']
                                         [SEQUENCE[1]]['target'], 'all_opponents')
                    elif format_name == 'csv':
                        row, = csv.DictReader(io.StringIO(result.stdout))
                        self.assertEqual((row['hp'], row['xp_reward']), ('1877', '1110'))
                        self.assertEqual((row['presentation_pending'], row['combat_pending']), ('False', 'False'))
                    else:
                        self.assertIn('Combat: ready', result.stdout)
                        self.assertIn('all_opponents', result.stdout)
                        self.assertIn('damage taken ×1.25', result.stdout)
                        self.assertIn('100% healing (absorb)', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])
