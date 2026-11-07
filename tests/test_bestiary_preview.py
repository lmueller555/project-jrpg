"""The headless authoring tool reports real dictionary data from any cwd."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


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

    def test_csv_and_markdown_have_consistent_levels_and_no_fabricated_fixed_xp(self):
        result = self.run_preview('--enemy', 'cave_bat', '--levels', '3', '2', '--format', 'csv')
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual([row['level'] for row in rows], ['3', '2'])
        self.assertEqual([row['xp_reward'] for row in rows], ['104', '84'])
        self.assertEqual([row['mp'] for row in rows], ['5', '5'])
        fixed = self.run_preview('--enemy', 'bat', '--format', 'json')
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        record = json.loads(fixed.stdout)[0]
        self.assertIsNone(record['level'])
        self.assertIsNone(record['xp_reward'])
        self.assertEqual(record['combat']['attributes']['hp'], 72)
        readable = self.run_preview('--enemy', 'cave_bat', '--levels', '2', '3')
        self.assertEqual(readable.returncode, 0, readable.stderr)
        self.assertIn('cave_bat_bite → cave_bat_wing_gust', readable.stdout)
        self.assertIn('Cave Bat', readable.stdout)

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
