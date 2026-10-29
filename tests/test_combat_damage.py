"""Approved per-hit damage values, resolution order and attribute integration."""
from fractions import Fraction
import random
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

from character_attributes import CharacterAttributes
from combat_damage import (BREAK_DAMAGE_CAP, MAX_VARIANCE_PERCENT,
                           MIN_VARIANCE_PERCENT, NORMAL_DAMAGE_CAP,
                           calculate_damage, magical_damage, physical_damage,
                           roll_variance)


class CombatDamageTests(unittest.TestCase):
    def test_approved_basic_and_powerful_attack_examples(self):
        examples = ((10, 10, 18, 54), (25, 20, 104, 312),
                    (50, 40, 357, 1071), (100, 80, 1111, 3333),
                    (150, 120, 2045, 6136), (200, 150, 3200, 9600),
                    (255, 200, 4335, 9999), (255, 255, 3663, 9999))
        for offense, defense, basic, powerful in examples:
            with self.subTest(offense=offense, defense=defense):
                self.assertEqual(calculate_damage(offense, defense), basic)
                self.assertEqual(calculate_damage(offense, defense, 3), powerful)

    def test_approved_defense_comparison_holds_offense_constant(self):
        for defense, expected in ((0, 2000), (50, 1333), (100, 1000),
                                  (200, 666), (255, 563)):
            with self.subTest(defense=defense):
                self.assertEqual(calculate_damage(100, defense), expected)

    def test_approved_worked_spell_and_variance_endpoints(self):
        self.assertEqual(calculate_damage(50, 40, 2), 714)
        self.assertEqual(calculate_damage(50, 40, 2, variance_percent=95), 678)
        # Exact arithmetic must not turn a mathematical 750 into 749.
        self.assertEqual(calculate_damage(50, 40, 2, variance_percent=105), 750)
        self.assertEqual(calculate_damage(56, 38, 2), 908)

    def test_rounding_occurs_after_potency_and_all_modifiers(self):
        self.assertEqual(calculate_damage(43, 43), 258)
        self.assertEqual(calculate_damage(43, 43, 3), 775)
        self.assertNotEqual(calculate_damage(43, 43, 3), 258*3)
        self.assertEqual(calculate_damage(100, 80, critical=True), 1666)
        self.assertEqual(calculate_damage(100, 80, affinity=2), 2222)
        self.assertEqual(calculate_damage(100, 80, affinity=Fraction(1, 2)), 555)

    def test_critical_affinity_protection_and_variance_compose(self):
        self.assertEqual(calculate_damage(100, 100, critical=True), 1500)
        self.assertEqual(calculate_damage(100, 100, affinity=2), 2000)
        self.assertEqual(calculate_damage(100, 100, affinity=.5), 500)
        self.assertEqual(calculate_damage(100, 100, protected=True), 500)
        self.assertEqual(calculate_damage(100, 100, critical=True, affinity=2,
                                          protected=True, variance_percent=95), 1425)

    def test_damage_caps_apply_after_reducing_modifiers(self):
        # Unmodified damage is 13,005; protection reduces it before the cap.
        self.assertEqual(calculate_damage(255, 200, 3, protected=True), 6502)
        self.assertEqual(calculate_damage(255, 200, 3, affinity=.5), 6502)
        self.assertEqual(calculate_damage(255, 200, 3, affinity=.5,
                                          break_damage_limit=True), 6502)

    def test_approved_cap_break_examples_raise_only_the_ceiling(self):
        self.assertEqual(NORMAL_DAMAGE_CAP, 9999)
        self.assertEqual(BREAK_DAMAGE_CAP, 99999)
        for potency, affinity, uncapped, broken in ((3, 1, 13005, 13005),
                                                   (12, 1, 52020, 52020),
                                                   (12, 2, 104040, 99999)):
            with self.subTest(potency=potency, affinity=affinity):
                self.assertGreater(uncapped, NORMAL_DAMAGE_CAP)
                self.assertEqual(calculate_damage(255, 200, potency, affinity=affinity), 9999)
                self.assertEqual(calculate_damage(255, 200, potency, affinity=affinity,
                                                  break_damage_limit=True), broken)
        self.assertEqual(calculate_damage(50, 40, 2, break_damage_limit=True), 714)

    def test_damage_caps_are_per_hit_and_not_per_action_total(self):
        hits = [calculate_damage(150, 50) for _ in range(4)]
        self.assertEqual(hits, [3000]*4)
        self.assertEqual(sum(hits), 12000)
        capped_hits = [calculate_damage(255, 200, 3) for _ in range(4)]
        self.assertEqual(capped_hits, [9999]*4)
        self.assertEqual(sum(capped_hits), 39996)

    def test_successful_nonimmune_hits_have_minimum_one_damage(self):
        for offense in (0, 1):
            with self.subTest(offense=offense):
                self.assertEqual(calculate_damage(offense, 255, Fraction(1, 1000),
                                                  affinity=.5, protected=True,
                                                  variance_percent=95), 1)
        self.assertEqual(calculate_damage(255, 0, 1e308), 9999)
        self.assertEqual(calculate_damage(255, 0, 1e308, break_damage_limit=True), 99999)

    def test_misses_and_immunities_deal_zero_even_with_critical_and_cap_break(self):
        for zero in ({'hit': False}, {'immune': True}, {'affinity': 0}):
            with self.subTest(zero=zero):
                self.assertEqual(calculate_damage(255, 0, 12, critical=True,
                                                  break_damage_limit=True, **zero), 0)
        self.assertEqual(calculate_damage(0, 255, hit=False), 0)

    def test_integer_float_and_fraction_potencies_agree_without_early_rounding(self):
        for potency in (3, 3.0, Fraction(3)):
            self.assertEqual(calculate_damage(43, 43, potency), 775)
        for potency in (1.5, Fraction(3, 2)):
            self.assertEqual(calculate_damage(50, 40, potency), 535)
        self.assertEqual(calculate_damage(50, 0, .1), 50)
        self.assertEqual(calculate_damage(50, 0, Fraction(1, 10)), 50)

    def test_physical_and_magical_wrappers_select_only_their_stat_pair(self):
        class Attributes:
            def __init__(self, values):
                self.values, self.reads = values, []

            def value(self, key):
                self.reads.append(key)
                return self.values[key]

        attacker = Attributes({'str': 43, 'mag': 56})
        defender = Attributes({'def': 43, 'm_def': 38})
        self.assertEqual(physical_damage(attacker, defender), 258)
        self.assertEqual(magical_damage(attacker, defender, 2), 908)
        self.assertEqual(attacker.reads, ['str', 'mag'])
        self.assertEqual(defender.reads, ['def', 'm_def'])

    def test_wrappers_read_capped_effective_attributes_without_mutating_state(self):
        attacker, defender = CharacterAttributes(), CharacterAttributes()
        self.assertTrue(attacker.set_modifiers('lattice', {'str': 1000, 'mag': 1000,
                                                         'spr': 245, 'lck': 245}))
        self.assertTrue(defender.set_modifiers('equipment', {'def': 1000, 'm_def': 1000}))
        before = attacker.to_dict(), defender.to_dict()
        self.assertEqual(physical_damage(attacker, defender), 3663)
        self.assertEqual(magical_damage(attacker, defender), 3663)
        self.assertEqual((attacker.to_dict(), defender.to_dict()), before)
        self.assertEqual(attacker.value('str'), 255)
        self.assertEqual(defender.value('m_def'), 255)

    def test_wrappers_forward_per_hit_modifiers_and_cap_permission(self):
        attacker = SimpleNamespace(value=lambda key: 255)
        defender = SimpleNamespace(value=lambda key: 200)
        for wrapper in (physical_damage, magical_damage):
            with self.subTest(wrapper=wrapper.__name__):
                self.assertEqual(wrapper(attacker, defender, 12, affinity=2,
                                          break_damage_limit=True), 99999)
                self.assertEqual(wrapper(attacker, defender, 3, protected=True), 6502)
                self.assertEqual(wrapper(attacker, defender, hit=False), 0)

    def test_wrappers_reject_invalid_attribute_providers_and_returned_ratings(self):
        valid = SimpleNamespace(value=lambda key: 10)
        for wrapper in (physical_damage, magical_damage):
            for invalid in (None, object(), SimpleNamespace(value=10)):
                with self.subTest(wrapper=wrapper.__name__, provider=invalid):
                    with self.assertRaises(TypeError):wrapper(invalid, valid)
                    with self.assertRaises(TypeError):wrapper(valid, invalid)
            for value, error in ((True, TypeError), (10.0, TypeError),
                                 (-1, ValueError), (256, ValueError)):
                invalid = SimpleNamespace(value=lambda key: value)
                with self.subTest(wrapper=wrapper.__name__, value=value):
                    with self.assertRaises(error):wrapper(invalid, valid)
                    with self.assertRaises(error):wrapper(valid, invalid)

    def test_offense_and_defense_require_bounded_nonboolean_integer_ratings(self):
        for field in ('offense', 'defense'):
            for bad in (True, False, 1.0, '10', None, [], Fraction(10)):
                with self.subTest(field=field, bad=bad):
                    args = {'offense': 10, 'defense': 10, field: bad}
                    with self.assertRaises(TypeError):calculate_damage(**args)
            for bad in (-1, 256):
                with self.subTest(field=field, bad=bad):
                    args = {'offense': 10, 'defense': 10, field: bad}
                    with self.assertRaises(ValueError):calculate_damage(**args)

    def test_potency_requires_a_positive_finite_numeric_value(self):
        for bad in (True, False, '1', None, [], {}, complex(1)):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):calculate_damage(10, 10, bad)
        for bad in (0, -1, -0.1, float('nan'), float('inf'), float('-inf')):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):calculate_damage(10, 10, bad)

    def test_affinity_allows_only_immunity_resistance_neutral_or_weakness(self):
        for affinity, expected in ((0, 0), (.5, 500), (1, 1000), (2, 2000)):
            self.assertEqual(calculate_damage(100, 100, affinity=affinity), expected)
        for bad in (True, False, '.5', None, [], complex(1)):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):calculate_damage(10, 10, affinity=bad)
        for bad in (-1, .25, 1.5, 3, float('nan'), float('inf')):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):calculate_damage(10, 10, affinity=bad)

    def test_variance_requires_an_integer_percent_in_the_approved_range(self):
        self.assertEqual((MIN_VARIANCE_PERCENT, MAX_VARIANCE_PERCENT), (95, 105))
        for bad in (True, False, 100.0, '100', None, Fraction(100)):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):calculate_damage(10, 10, variance_percent=bad)
        for bad in (-1, 0, 94, 106):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):calculate_damage(10, 10, variance_percent=bad)

    def test_boolean_options_are_explicit_booleans(self):
        for field in ('critical', 'protected', 'hit', 'immune', 'break_damage_limit'):
            for bad in (0, 1, None, 'yes', []):
                with self.subTest(field=field, bad=bad):
                    with self.assertRaises(TypeError):calculate_damage(10, 10, **{field: bad})

    def test_miss_and_immunity_do_not_hide_invalid_requests(self):
        for zero in ({'hit': False}, {'immune': True}, {'affinity': 0}):
            with self.subTest(zero=zero):
                with self.assertRaises(ValueError):calculate_damage(256, 10, **zero)
                with self.assertRaises(ValueError):calculate_damage(10, 10, 0, **zero)
                with self.assertRaises(ValueError):calculate_damage(10, 10, variance_percent=94, **zero)
                with self.assertRaises(TypeError):calculate_damage(10, 10, critical=1, **zero)

    def test_damage_increases_with_offense_and_decreases_with_defense(self):
        for defense in (0, 40, 128, 255):
            values = [calculate_damage(offense, defense) for offense in range(256)]
            self.assertEqual(values, sorted(values))
        for offense in (1, 10, 100, 255):
            values = [calculate_damage(offense, defense) for defense in range(256)]
            self.assertEqual(values, sorted(values, reverse=True))

    def test_variance_roll_uses_only_the_injected_random_source(self):
        class FixedRoll:
            def __init__(self, result):self.result, self.calls = result, []

            def randint(self, low, high):
                self.calls.append((low, high))
                return self.result

        before = random.getstate()
        for value in (95, 100, 105):
            source = FixedRoll(value)
            self.assertEqual(roll_variance(source), value)
            self.assertEqual(source.calls, [(95, 105)])
        self.assertEqual(random.getstate(), before)
        first, second = random.Random(749), random.Random(749)
        rolls = [roll_variance(first) for _ in range(32)]
        self.assertEqual(rolls, [roll_variance(second) for _ in range(32)])
        self.assertTrue(all(95 <= roll <= 105 for roll in rolls))

    def test_invalid_random_sources_and_rolls_are_rejected(self):
        for source in (None, object(), SimpleNamespace(randint=1)):
            with self.subTest(source=source):
                with self.assertRaises(TypeError):roll_variance(source)
        for value in (True, 100.0, '100', None):
            source = SimpleNamespace(randint=lambda low, high: value)
            with self.subTest(value=value):
                with self.assertRaises(TypeError):roll_variance(source)
        for value in (94, 106):
            source = SimpleNamespace(randint=lambda low, high: value)
            with self.subTest(value=value):
                with self.assertRaises(ValueError):roll_variance(source)

    def test_calculation_is_deterministic_and_does_not_advance_global_random_state(self):
        before = random.getstate()
        self.assertEqual([calculate_damage(50, 40, 2) for _ in range(8)], [714]*8)
        self.assertEqual(random.getstate(), before)

    def test_module_import_needs_no_game_files_pygame_or_random_rolls(self):
        code = (
            'import random, sys\n'
            'from unittest.mock import patch\n'
            'before = random.getstate()\n'
            'with patch("pathlib.Path.read_text", side_effect=AssertionError("data read")), '
            'patch("builtins.open", side_effect=AssertionError("file read")):\n'
            ' import combat_damage\n'
            'assert "pygame" not in sys.modules\n'
            'assert before == random.getstate()\n'
        )
        result = subprocess.run([sys.executable, '-c', code],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':unittest.main()
