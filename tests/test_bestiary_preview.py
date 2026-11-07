"""The headless authoring tool reports real dictionary data from any cwd."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bestiary import ELEMENT_IDS, load_bestiary, build_enemy
from tools.preview_bestiary import elemental_rows, stat_rows


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'tools/preview_bestiary.py'


class BestiaryPreviewTests(unittest.TestCase):
    def run_preview(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd or ROOT,
                              capture_output=True, text=True)

    def test_overview_lists_fixed_and_computed_entries_without_assigning_levels(self):
        result = self.run_preview('--list', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {row['id']: row for row in json.loads(result.stdout)}
        self.assertEqual(set(rows), {'bat', 'ridgeback_tusker', 'cave_bat'})
        self.assertEqual(rows['bat']['kind'], 'fixed')
        self.assertEqual(rows['ridgeback_tusker']['levels'], 'fixed')
        self.assertEqual(rows['cave_bat']['kind'], 'species')
        self.assertEqual(rows['cave_bat']['levels'], '2–3')
        self.assertEqual(rows['cave_bat']['stat_profile'], 'hybrid')
        self.assertEqual(rows['cave_bat']['element'], 'non_elemental')
        self.assertEqual(rows['bat']['element'], 'unassigned')
        self.assertEqual(rows['ridgeback_tusker']['element'], 'unassigned')

    def test_json_uses_real_species_stats_rewards_and_behavior_outside_repository(self):
        with tempfile.TemporaryDirectory(prefix='bestiary-preview-') as directory:
            result = self.run_preview('--enemy', 'cave_bat', '--format', 'json', cwd=directory)
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = json.loads(result.stdout)
        self.assertEqual([record['level'] for record in records], [2, 3])
        self.assertEqual([record['combat']['attributes']['hp'] for record in records], [73, 85])
        self.assertEqual([record['xp_reward'] for record in records], [84, 104])
        self.assertEqual(records[0]['behavior']['sequence'],
                         ['cave_bat_bite', 'cave_bat_wing_gust'])
        self.assertTrue(records[0]['metadata']['drops_pending'])
        self.assertEqual(records[0]['combat']['rewards'], {'drops': {}})
        profile = records[0]['metadata']['elemental_profile']
        self.assertEqual(profile['element'], 'non_elemental')
        self.assertEqual(profile['damage_percentages'],
                         {key: 200 if key == 'fire' else 100 for key in ELEMENT_IDS})
        self.assertEqual(profile['absorption'], {'elements': [], 'healing_percent': 100})
        self.assertTrue(profile['design_rationale'])
        self.assertEqual(records[1]['metadata']['elemental_profile'], profile)

    def test_csv_and_markdown_have_consistent_levels_and_no_fabricated_fixed_xp(self):
        result = self.run_preview('--enemy', 'cave_bat', '--levels', '3', '2', '--format', 'csv')
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual([row['level'] for row in rows], ['3', '2'])
        self.assertEqual([row['xp_reward'] for row in rows], ['104', '84'])
        self.assertEqual([row['mp'] for row in rows], ['5', '5'])
        self.assertEqual([row['element'] for row in rows], ['non_elemental']*2)
        for row in rows:
            self.assertEqual({key: row['damage_percent_'+key] for key in ELEMENT_IDS},
                             {key: '200' if key == 'fire' else '100' for key in ELEMENT_IDS})
            self.assertEqual(row['absorption_elements'], 'none')
            self.assertEqual(row['absorption_healing_percent'], '100')
        fixed = self.run_preview('--enemy', 'bat', '--format', 'json')
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        record = json.loads(fixed.stdout)[0]
        self.assertIsNone(record['level'])
        self.assertIsNone(record['xp_reward'])
        self.assertEqual(record['combat']['attributes']['hp'], 72)
        self.assertNotIn('elemental_profile', record['metadata'])
        readable = self.run_preview('--enemy', 'cave_bat', '--levels', '2', '3')
        self.assertEqual(readable.returncode, 0, readable.stderr)
        self.assertIn('cave_bat_bite → cave_bat_wing_gust', readable.stdout)
        self.assertIn('Cave Bat', readable.stdout)
        self.assertIn('Element: Non-Elemental', readable.stdout)
        self.assertIn('| Fire | 200% damage |', readable.stdout)
        self.assertIn('| Non-Elemental | 100% damage |', readable.stdout)
        self.assertIn('Design rationale:', readable.stdout)
        self.assertIn('battle effects are not active', readable.stdout)

    def test_absorption_overrides_damage_in_relationship_display_and_csv_is_explicit(self):
        catalog = load_bestiary()
        profile = catalog['enemies']['cave_bat']['elemental_profile']
        profile['element'] = 'fire'
        profile['absorption']['elements'] = ['fire']
        profile['damage_percentages']['fire'] = 125
        profile['damage_percentages']['water'] = 75
        profile['damage_percentages']['electric'] = 125.123456789
        record = build_enemy('cave_bat', 2, data=catalog)
        relationships = {row['Element']: row['Response']
                         for row in elemental_rows(record['metadata']['elemental_profile'])}
        self.assertEqual(len(relationships), 9)
        self.assertEqual(relationships['Fire'], '100% healing (absorb)')
        self.assertEqual(relationships['Water'], '75% damage')
        self.assertEqual(relationships['Electric'], '125.123456789% damage')
        self.assertEqual(relationships['Non-Elemental'], '100% damage')
        row = list(stat_rows([record], include_elements=True))[0]
        self.assertEqual(row['element'], 'fire')
        self.assertEqual(row['damage_percent_fire'], 125)
        self.assertEqual(row['damage_percent_water'], 75)
        self.assertEqual(row['absorption_elements'], 'fire')
        self.assertEqual(row['absorption_healing_percent'], 100)

    def test_fixed_preview_does_not_guess_affinities(self):
        readable = self.run_preview('--enemy', 'bat')
        self.assertEqual(readable.returncode, 0, readable.stderr)
        self.assertIn('Elemental profile: unassigned (fixed encounter).', readable.stdout)
        self.assertNotIn('100% damage', readable.stdout)
        output = self.run_preview('--enemy', 'ridgeback_tusker', '--format', 'csv')
        self.assertEqual(output.returncode, 0, output.stderr)
        row = list(csv.DictReader(io.StringIO(output.stdout)))[0]
        self.assertEqual(row['element'], 'unassigned')
        self.assertTrue(all(row['damage_percent_'+key] == '' for key in ELEMENT_IDS))
        self.assertEqual(row['absorption_elements'], 'unassigned')
        self.assertEqual(row['absorption_healing_percent'], '')

    def test_invalid_id_level_or_mode_exits_cleanly(self):
        for args in (('--enemy', 'missing'), ('--levels', '2'),
                     ('--enemy', 'cave_bat', '--levels', '1'),
                     ('--enemy', 'cave_bat', '--levels', '4'),
                     ('--enemy', 'cave_bat', '--levels', '2.5'),
                     ('--enemy', 'bat', '--levels', '2'),
                     ('--list', '--enemy', 'cave_bat')):
            with self.subTest(args=args):
                result = self.run_preview(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
