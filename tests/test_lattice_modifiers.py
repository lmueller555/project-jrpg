"""Lattice growth derives from its ledger instead of compounding saved totals."""
from copy import deepcopy
import unittest

from character_attributes import ATTRIBUTE_IDS, MAX_ATTRIBUTE_VALUE, CharacterAttributes


class LatticeModifierTests(unittest.TestCase):
    def setUp(self):
        self.attributes = CharacterAttributes('caelan')

    def effective_state(self):
        return (tuple(self.attributes.value(identifier) for identifier in ATTRIBUTE_IDS),
                self.attributes.current_hp, self.attributes.current_mp,
                self.attributes.to_dict())

    def test_sources_replace_without_stacking_or_changing_preserved_base(self):
        before = self.attributes.to_dict()
        growth = {'hp': 20, 'mp': 2, 'str': 1}
        self.assertTrue(self.attributes.set_modifiers('lattice', growth))
        self.assertEqual(self.attributes.value('hp'), 160)
        self.assertEqual(self.attributes.value('mp'), 32)
        self.assertEqual(self.attributes.value('str'), 11)
        self.assertEqual(self.attributes.base_value('hp'), 140)
        self.assertEqual(self.attributes.to_dict(), before)
        self.assertEqual((self.attributes.current_hp, self.attributes.current_mp), (140, 30))
        self.assertTrue(self.attributes.set_modifiers('equipment', {'def': 4}))
        self.assertTrue(self.attributes.set_modifiers('lattice', growth))
        self.assertEqual(self.attributes.value('hp'), 160)
        self.assertEqual(self.attributes.value('def'), 14)
        self.assertTrue(self.attributes.set_modifiers('lattice', {'hp': 40}))
        self.assertEqual(self.attributes.value('hp'), 180)
        self.assertEqual(self.attributes.value('str'), 10)
        self.assertEqual(self.attributes.value('def'), 14)
        growth['hp'] = 900
        self.assertEqual(self.attributes.value('hp'), 180)

    def test_invalid_replacements_leave_all_sources_and_resources_unchanged(self):
        self.assertTrue(self.attributes.set_modifiers('lattice', {'hp': 20, 'str': 1}))
        self.assertTrue(self.attributes.set_current(hp=150))
        before = self.effective_state()
        for bonuses in (None, [], {'unknown': 1}, {'hp': -1}, {'hp': True},
                        {'hp': 1.0}, {'hp': '20'}, {'hp': MAX_ATTRIBUTE_VALUE}):
            with self.subTest(bonuses=bonuses):
                self.assertFalse(self.attributes.set_modifiers('lattice', bonuses))
                self.assertEqual(self.effective_state(), before)
        for source in (None, '', ' ', 1, 'x'*65):
            with self.subTest(source=source):
                self.assertFalse(self.attributes.set_modifiers(source, {'hp': 1}))
                self.assertEqual(self.effective_state(), before)
        self.assertFalse(self.attributes.set_modifiers('lattice', {}))
        self.assertEqual(self.effective_state(), before)
        self.assertTrue(self.attributes.set_current(hp=120))
        self.assertTrue(self.attributes.set_modifiers('lattice', {}))
        self.assertEqual(self.attributes.value('hp'), 140)
        self.assertEqual(self.attributes.current_hp, 120)

    def test_save_restore_rebuilds_effective_caps_before_validating_resources(self):
        bonuses = {'hp': 20, 'mp': 2, 'str': 1}
        self.assertTrue(self.attributes.set_modifiers('lattice', bonuses))
        self.assertTrue(self.attributes.set_current(hp=155, mp=31))
        saved = self.attributes.to_dict()
        self.assertEqual(saved['version'], 3)
        self.assertEqual(saved['attributes']['hp'], 140)
        self.assertEqual(saved['attributes']['str'], 10)
        self.assertFalse(CharacterAttributes.valid_snapshot(saved))
        self.assertTrue(CharacterAttributes.valid_snapshot(saved, lattice_bonuses=bonuses))
        clone = CharacterAttributes()
        fresh = clone.to_dict()
        self.assertFalse(clone.restore(saved))
        self.assertEqual(clone.to_dict(), fresh)
        for _ in range(3):
            self.assertTrue(clone.restore(saved, lattice_bonuses=bonuses))
            self.assertEqual(clone.value('hp'), 160)
            self.assertEqual(clone.value('str'), 11)
            self.assertEqual((clone.current_hp, clone.current_mp), (155, 31))
            self.assertEqual(clone.to_dict(), saved)
        bonuses['hp'] = 100
        self.assertEqual(clone.value('hp'), 160)

    def test_legacy_growth_becomes_base_before_any_lattice_growth(self):
        for version, maximum, current, expected_maximum, expected_current in (
                (1, 300, 150, 140, 70), (2, 300, 213, 300, 213),
                (2, 400, 250, 400, 250)):
            with self.subTest(version=version, maximum=maximum):
                saved = CharacterAttributes().to_dict()
                saved.update(version=version, current_hp=current, current_mp=11)
                saved['attributes'].update(hp=maximum, str=18, spr=17)
                original = deepcopy(saved)
                clone = CharacterAttributes()
                self.assertFalse(clone.restore(saved, lattice_bonuses={'hp': 20}))
                self.assertTrue(clone.restore(saved, lattice_bonuses={'hp': 0}))
                self.assertEqual(clone.base_value('hp'), expected_maximum)
                self.assertEqual(clone.base_value('str'), 18)
                self.assertEqual(clone.value('spr'), 17)
                self.assertEqual((clone.current_hp, clone.current_mp), (expected_current, 11))
                self.assertEqual(saved, original)
                converted = clone.to_dict()
                self.assertEqual(converted['version'], 3)
                self.assertTrue(clone.restore(converted, lattice_bonuses={'hp': 20}))
                self.assertEqual(clone.value('hp'), expected_maximum+20)
                self.assertEqual(clone.base_value('hp'), expected_maximum)

    def test_bad_external_bonus_context_rejects_restore_atomically(self):
        self.assertTrue(self.attributes.set_modifiers('lattice', {'str': 2}))
        self.assertTrue(self.attributes.set_current(hp=95, mp=10))
        before = self.effective_state()
        record = self.attributes.to_dict()
        for bonuses in ([], {'no_stat': 1}, {'hp': -1}, {'hp': True},
                        {'hp': 1.0}, {'hp': MAX_ATTRIBUTE_VALUE}):
            with self.subTest(bonuses=bonuses):
                self.assertFalse(CharacterAttributes.valid_snapshot(record, lattice_bonuses=bonuses))
                self.assertFalse(self.attributes.restore(record, lattice_bonuses=bonuses))
                self.assertEqual(self.effective_state(), before)

    def test_growth_does_not_refill_or_revive_and_new_game_clears_sources(self):
        other = CharacterAttributes()
        self.assertTrue(self.attributes.set_current(hp=0, mp=0))
        self.assertTrue(self.attributes.set_modifiers('lattice', {'hp': 20, 'mp': 2, 'mag': 1}))
        self.assertEqual((self.attributes.current_hp, self.attributes.current_mp), (0, 0))
        self.assertEqual(other.value('hp'), 140)
        self.attributes.reset()
        self.assertEqual(self.attributes.to_dict(), other.to_dict())
        self.assertEqual(self.attributes.value('mag'), 10)
        self.assertEqual((self.attributes.current_hp, self.attributes.current_mp), (140, 30))


if __name__ == '__main__':
    unittest.main()
