"""Headless exports expose authored profiles without changing the default view."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'tools/preview_leveling.py'


class LevelingPreviewTests(unittest.TestCase):
    def run_preview(self, *args):
        with tempfile.TemporaryDirectory(prefix='leveling-preview-') as directory:
            return subprocess.run([sys.executable, str(SCRIPT), *args],
                                  cwd=directory, capture_output=True, text=True)

    def test_default_json_keeps_character_and_baseline_rows(self):
        result = self.run_preview('--levels', '100', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual([row['profile'] for row in rows],
                         ['caelan', 'mira', 'lucan', 'rhea', 'edran', 'enemy_baseline'])
        self.assertEqual(rows[-1]['hp'], 50000)
        self.assertEqual(rows[-1]['def'], 288)

    def test_named_json_uses_raw_reference_and_authored_exceptions(self):
        result = self.run_preview('--enemy-profiles', '--levels', '100', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {row['profile']: row for row in json.loads(result.stdout)}
        self.assertEqual(len(rows), 16)
        self.assertEqual(rows['enemy_armored']['def'], 460)
        self.assertEqual(rows['enemy_armored']['m_def'], 174)
        self.assertEqual(rows['enemy_caster']['mag'], 321)
        self.assertEqual(rows['enemy_swift']['acc'], 324)
        self.assertEqual(rows['enemy_evasive']['eva'], 319)
        self.assertEqual(rows['enemy_lightweight']['hp'], 20000)

    def test_all_levels_csv_covers_every_profile_and_preserves_columns(self):
        result = self.run_preview('--enemy-profiles', '--all-levels', '--format', 'csv')
        self.assertEqual(result.returncode, 0, result.stderr)
        reader = csv.DictReader(io.StringIO(result.stdout))
        rows = list(reader)
        self.assertEqual(reader.fieldnames,
                         ['profile', 'level', 'total_xp_to_level', 'xp_to_next_level',
                          'normal_monster_xp', 'boss_xp', 'hp', 'mp', 'str', 'mag',
                          'spr', 'def', 'm_def', 'speed', 'acc', 'eva', 'lck'])
        self.assertEqual(len(rows), 1600)
        self.assertEqual(len({(row['profile'], row['level']) for row in rows}), 1600)
        for profile in {row['profile'] for row in rows}:
            with self.subTest(profile=profile):
                self.assertEqual({int(row['level']) for row in rows if row['profile'] == profile},
                                 set(range(1, 101)))

    def test_markdown_and_invalid_levels_keep_the_cli_contract(self):
        result = self.run_preview('--enemy-profiles', '--levels', '1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('| enemy_brute | 1 |', result.stdout)
        self.assertIn('species/tier modifiers are absent', result.stdout)
        invalid = self.run_preview('--enemy-profiles', '--levels', '101')
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn('levels must be between 1 and 100', invalid.stderr)


if __name__ == '__main__':
    unittest.main()
