"""Approved progression anchors, complete growth, and isolated XP ownership."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from character_attributes import ATTRIBUTE_IDS
from leveling import (MAX_LEVEL, MAX_TOTAL_XP, MIN_LEVEL, CharacterLevel,
                      character_ids, character_stats, level_for_total_xp,
                      load_growth_catalog, monster_xp, raw_character_stats,
                      total_xp_for_level, xp_to_next_level)


TARGETS = {
    'caelan': [5600, 400, 280, 280, 200, 220, 220, 115, 230, 190, 200],
    'mira': [5800, 400, 230, 230, 230, 230, 230, 100, 220, 190, 200],
    'lucan': [7400, 240, 300, 140, 170, 300, 230, 89, 240, 150, 180],
    'rhea': [3600, 600, 90, 300, 190, 120, 180, 108, 200, 180, 200],
    'edran': [6500, 500, 120, 120, 300, 280, 300, 94, 190, 140, 180],
}
STARTS = {
    'caelan': [140, 30, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    'mira': [150, 30, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    'lucan': [170, 20, 12, 7, 8, 12, 9, 8, 11, 8, 9],
    'rhea': [100, 45, 6, 13, 10, 7, 10, 10, 10, 10, 10],
    'edran': [160, 40, 7, 7, 13, 12, 12, 8, 9, 7, 10],
}


class CharacterGrowthTests(unittest.TestCase):
    def test_approved_roster_starting_profiles_and_final_targets(self):
        self.assertEqual((MIN_LEVEL, MAX_LEVEL), (1, 100))
        self.assertEqual(character_ids(), ('caelan', 'mira', 'lucan', 'rhea', 'edran'))
        for identifier in character_ids():
            with self.subTest(character=identifier):
                self.assertEqual(list(character_stats(identifier, 1).values()), STARTS[identifier])
                self.assertEqual(list(character_stats(identifier, 100).values()), TARGETS[identifier])

    def test_every_level_is_monotonic_with_resource_and_rating_headroom(self):
        for identifier in character_ids():
            previous = character_stats(identifier, 1)
            for level in range(1, 101):
                with self.subTest(character=identifier, level=level):
                    stats = character_stats(identifier, level)
                    self.assertEqual(tuple(stats), ATTRIBUTE_IDS)
                    self.assertTrue(all(type(value) is int for value in stats.values()))
                    self.assertTrue(all(stats[key] >= previous[key] for key in ATTRIBUTE_IDS))
                    self.assertLessEqual(stats['hp'], 9999)
                    self.assertLessEqual(stats['mp'], 999)
                    self.assertLessEqual(stats['speed'], 255)
                    for key in set(ATTRIBUTE_IDS)-{'hp', 'mp', 'speed'}:
                        self.assertLessEqual(stats[key], 300)
                    previous = stats

    def test_midgame_speed_uses_approved_doubled_then_fifty_percent_gains(self):
        self.assertEqual(character_stats('caelan', 34)['speed'], 45)
        self.assertEqual(character_stats('mira', 34)['speed'], 40)
        self.assertEqual(character_stats('lucan', 34)['speed'], 35)
        self.assertEqual(character_stats('rhea', 34)['speed'], 43)
        self.assertEqual(character_stats('edran', 34)['speed'], 37)

    def test_raw_reference_and_returned_stats_have_no_mutable_aliases(self):
        first = raw_character_stats('caelan', 25)
        self.assertTrue(any(not value.is_integer() for value in first.values()))
        first['str'] = -99
        self.assertGreater(raw_character_stats('caelan', 25)['str'], 10)
        values = character_stats('mira', 100)
        values['hp'] = 1
        self.assertEqual(character_stats('mira', 100)['hp'], 5800)
        catalog = load_growth_catalog()
        catalog['characters']['mira']['target']['str'] = 1
        self.assertEqual(character_stats('mira', 100)['str'], 230)

    def test_invalid_levels_and_character_ids_fail_explicitly(self):
        for bad in (True, False, 1.0, '1', None, [], {}):
            with self.subTest(level=bad):
                for function in (character_stats, raw_character_stats):
                    with self.assertRaises(TypeError):function('caelan', bad)
        for bad in (-1, 0, 101, 999999):
            with self.subTest(level=bad):
                with self.assertRaises(ValueError):character_stats('caelan', bad)
        for bad in ('', 'unknown', 'Caelan'):
            with self.assertRaises(ValueError):character_stats(bad, 1)
        for bad in (None, True, 3, [], {}):
            with self.assertRaises(TypeError):character_stats(bad, 1)

    def test_invalid_catalog_profiles_and_rules_are_rejected(self):
        good = load_growth_catalog()
        records = [[], {}, {**good, 'version': True}, {**good, 'level_cap': 99}]
        for identifier, field, value in (
                ('rhea', 'mag', 301), ('caelan', 'speed', 256),
                ('mira', 'hp', 10000), ('edran', 'mp', 1000),
                ('lucan', 'str', True), ('caelan', 'def', 9)):
            record = deepcopy(good)
            record['characters'][identifier]['target'][field] = value
            records.append(record)
        missing = deepcopy(good);del missing['characters']['mira']['start']['eva']
        records.append(missing)
        roster = deepcopy(good);roster['characters']['future'] = roster['characters'].pop('edran')
        records.append(roster)
        for field in ('exponents', 'xp'):
            for bad in (None, [], True):
                records.append({**good, field: bad})
        for bad in (True, 1.3, float('inf'), float('nan'), 10**1000):
            record = deepcopy(good);record['exponents']['ratings'] = bad
            records.append(record)
        for field in ('required_scale', 'monster_scale', 'multiplier', 'boss_multiplier'):
            record = deepcopy(good);record['xp'][field] = float(record['xp'][field])
            records.append(record)
        with tempfile.TemporaryDirectory(prefix='level-catalog-') as directory:
            path = Path(directory)/'growth.json'
            for record in records:
                with self.subTest(record=record):
                    path.write_text(json.dumps(record))
                    with self.assertRaises(ValueError):load_growth_catalog(path)


class ExperienceCurveTests(unittest.TestCase):
    def test_approved_doubled_curves_and_boss_rewards(self):
        anchors = {1: (200, 42), 10: (1262, 133), 25: (2626, 210),
                   50: (4574, 297), 75: (6326, 364), 99: (7898, 417)}
        for level, (required, reward) in anchors.items():
            with self.subTest(level=level):
                self.assertEqual(xp_to_next_level(level), required)
                self.assertEqual(monster_xp(level), reward)
                self.assertEqual(monster_xp(level, boss=True), reward*10)
        self.assertEqual(xp_to_next_level(100), 0)
        self.assertEqual(monster_xp(100), 420)
        self.assertEqual(monster_xp(100, boss=True), 4200)

    def test_required_curve_stays_even_and_rewards_are_reduced(self):
        self.assertEqual(xp_to_next_level(5), 724)
        self.assertEqual(monster_xp(2), 59)
        for level in range(1, 101):
            with self.subTest(level=level):
                self.assertEqual(xp_to_next_level(level) % 2, 0)
                old_reward = 2*int(30*level**0.5+0.5)
                self.assertLessEqual(abs(monster_xp(level)-0.7*old_reward), 0.500001)

    def test_every_cumulative_boundary_and_one_xp_below_it(self):
        self.assertEqual(total_xp_for_level(1), 0)
        self.assertEqual(level_for_total_xp(0), 1)
        previous_cost = previous_reward = 0
        for level in range(2, 101):
            with self.subTest(level=level):
                threshold = total_xp_for_level(level)
                self.assertEqual(level_for_total_xp(threshold-1), level-1)
                self.assertEqual(level_for_total_xp(threshold), level)
                self.assertEqual(threshold-total_xp_for_level(level-1), xp_to_next_level(level-1))
                self.assertGreaterEqual(xp_to_next_level(level-1), previous_cost)
                self.assertGreaterEqual(monster_xp(level-1), previous_reward)
                previous_cost, previous_reward = xp_to_next_level(level-1), monster_xp(level-1)
        self.assertEqual(total_xp_for_level(100), MAX_TOTAL_XP)
        self.assertEqual(level_for_total_xp(MAX_TOTAL_XP+10**30), 100)

    def test_xp_api_rejects_bools_bad_types_negative_and_out_of_range_levels(self):
        for function in (xp_to_next_level, monster_xp, total_xp_for_level):
            for bad in (True, False, 1.0, None, '2', []):
                with self.subTest(function=function, value=bad):
                    with self.assertRaises(TypeError):function(bad)
            for bad in (-1, 0, 101):
                with self.assertRaises(ValueError):function(bad)
        for bad in (True, 0.0, None, '20'):
            with self.assertRaises(TypeError):level_for_total_xp(bad)
        with self.assertRaises(ValueError):level_for_total_xp(-1)
        for bad in (1, 0, 'boss', None):
            with self.assertRaises(TypeError):monster_xp(1, boss=bad)


class CharacterLevelRecordTests(unittest.TestCase):
    def test_awards_carry_excess_through_multiple_levels_and_report_growth(self):
        state = CharacterLevel('caelan')
        old_stats = state.stats
        requested = total_xp_for_level(12)+17
        result = state.award_xp(requested)
        self.assertEqual((result.old_level, result.new_level, result.levels_gained), (1, 12, 11))
        self.assertEqual((result.accepted_xp, result.discarded_xp), (requested, 0))
        self.assertEqual((state.level, state.total_xp, state.xp_into_level), (12, requested, 17))
        self.assertEqual(state.xp_remaining, xp_to_next_level(12)-17)
        self.assertEqual(dict(result.stat_gains),
                         {key: state.stats[key]-old_stats[key] for key in ATTRIBUTE_IDS})

    def test_award_partitioning_produces_identical_levels_and_stats(self):
        whole, parts = CharacterLevel('rhea'), CharacterLevel('rhea')
        amount = total_xp_for_level(60)+123
        whole.award_xp(amount)
        for chunk in (200, 300, 1000, amount-1500):parts.award_xp(chunk)
        self.assertEqual(parts.to_dict(), whole.to_dict())
        self.assertEqual(parts.stats, whole.stats)

    def test_level_cap_reports_discarded_xp_without_further_growth(self):
        state = CharacterLevel('edran', MAX_TOTAL_XP-1)
        result = state.award_xp(100)
        self.assertEqual((state.level, state.total_xp), (100, MAX_TOTAL_XP))
        self.assertEqual((result.accepted_xp, result.discarded_xp), (1, 99))
        self.assertEqual((state.xp_into_level, state.xp_remaining), (0, 0))
        before = state.to_dict()
        capped = state.award_xp(6000)
        self.assertEqual((capped.accepted_xp, capped.discarded_xp), (0, 6000))
        self.assertEqual(state.to_dict(), before)
        self.assertTrue(all(value == 0 for value in capped.stat_gains.values()))
        self.assertEqual(capped.levels_gained, 0)

    def test_bad_awards_are_atomic_and_exports_are_independent(self):
        state = CharacterLevel('mira', 42)
        before = state.to_dict()
        for bad in (True, False, 1.0, '200', None, [], -1):
            with self.subTest(value=bad):
                with self.assertRaises((TypeError, ValueError)):state.award_xp(bad)
                self.assertEqual(state.to_dict(), before)
        exported = state.to_dict();exported['total_xp'] = 999
        self.assertEqual(state.to_dict(), before)
        stats = state.stats;stats['hp'] = 0
        self.assertEqual(state.stats['hp'], 150)
        receipt = state.award_xp(200)
        with self.assertRaises(FrozenInstanceError):receipt.new_level = 100
        with self.assertRaises(TypeError):receipt.stat_gains['hp'] = -1
        exported_receipt = receipt.to_dict();exported_receipt['stat_gains']['hp'] = -1
        self.assertGreaterEqual(receipt.stat_gains['hp'], 0)

    def test_strict_snapshot_round_trip_and_malformed_records(self):
        for identifier in character_ids():
            state = CharacterLevel(identifier, total_xp_for_level(50)+7)
            snapshot = json.loads(json.dumps(state.to_dict()))
            restored = CharacterLevel.from_dict(snapshot)
            self.assertEqual(restored.to_dict(), snapshot)
            self.assertEqual(restored.stats, state.stats)
        good = CharacterLevel().to_dict()
        records = [None, [], True, {}, {**good, 'extra': 1},
                   {**good, 'version': True}, {**good, 'version': 2},
                   {**good, 'character_id': 'future'}, {**good, 'character_id': None},
                   {**good, 'total_xp': True}, {**good, 'total_xp': -1},
                   {**good, 'total_xp': MAX_TOTAL_XP+1}]
        for key in good:
            missing = dict(good);del missing[key];records.append(missing)
        for record in records:
            with self.subTest(record=record):
                with self.assertRaises((TypeError, ValueError)):CharacterLevel.from_dict(record)


if __name__ == '__main__':unittest.main()
