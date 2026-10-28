"""Cross-model lattice commands never charge or award only half a transaction."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from aether_lattice import AetherLattice, MAX_RP
from character_attributes import CharacterAttributes, MAX_ATTRIBUTE_VALUE
from inventory import Inventory, MAX_QUANTITY
from lattice_progression import LatticeProgression


class LatticeTransactionTests(unittest.TestCase):
    def setUp(self):
        self.lattice = AetherLattice()
        self.inventory = Inventory()
        self.attributes = CharacterAttributes()
        self.progression = LatticeProgression(self.lattice, self.inventory, {'caelan': self.attributes})

    def snapshot(self):
        return (self.lattice.to_dict(), self.inventory.to_dict(), self.attributes.to_dict(),
                [self.attributes.value(key) for key in self.attributes.definitions])

    def test_rp_only_loot_only_and_duplicate_completions(self):
        self.assertTrue(self.progression.award_battle_rewards('battle:1', {'caelan': 20}, {}))
        self.assertEqual((self.lattice.rank(), self.lattice.steps()), (2, 1))
        self.assertTrue(self.progression.award_battle_rewards('battle:2', {}, {'aether_emerald': 1}))
        before = self.snapshot()
        self.assertFalse(self.progression.award_battle_rewards('battle:2', {'caelan': 500}, {'aether_emerald': 9}))
        self.assertEqual(self.snapshot(), before)

    def test_invalid_drop_or_overflow_does_not_award_rp_or_consume_receipt(self):
        cases = ({'aether_emerald': 0}, {'aether_emerald': True},
                 {'aether_emerald': MAX_QUANTITY+1}, {'halden_medicine': 1}, {'unknown': 1})
        for drops in cases:
            with self.subTest(drops=drops):
                before = self.snapshot()
                self.assertFalse(self.progression.award_battle_rewards('invalid', {'caelan': 20}, drops))
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(self.lattice.has_receipt('invalid'))
        self.assertTrue(self.inventory.add('aether_emerald', MAX_QUANTITY))
        before = self.snapshot()
        self.assertFalse(self.progression.award_battle_rewards('overflow', {'caelan': 20}, {'aether_emerald': 1}))
        self.assertEqual(self.snapshot(), before)

    def test_invalid_rp_never_grants_drops(self):
        for awards in ({'caelan': -1}, {'caelan': True}, {'caelan': 0},
                       {'caelan': MAX_RP+1}, {'unknown': 20}, [], None):
            with self.subTest(awards=awards):
                before = self.snapshot()
                self.assertFalse(self.progression.award_battle_rewards('bad_rp', awards, {'aether_emerald': 1}))
                self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.progression.award_battle_rewards('empty', {}, {}))

    def test_travel_does_not_activate_passed_nodes_and_wrong_gem_never_charges(self):
        self.assertTrue(self.progression.award_battle_rewards('start', {'caelan': 75}, {'aether_emerald': 1}))
        self.assertTrue(self.progression.move('str_01'))
        self.assertEqual(self.lattice.state()['activated'], [])
        self.assertEqual(self.attributes.value('hp'), 140)
        self.assertEqual(self.lattice.rank(), 4)
        self.assertEqual(self.lattice.steps(), 0)
        before = self.snapshot()
        self.assertIn('Aether Ruby', self.progression.activation_reason('str_01'))
        self.assertFalse(self.progression.activate('str_01'))
        self.assertEqual(self.snapshot(), before)

    def test_stat_activation_is_once_and_preserves_base_and_current_resources(self):
        self.assertTrue(self.progression.award_battle_rewards('first', {'caelan': 20}, {'aether_emerald': 2}))
        self.assertTrue(self.progression.move('hp_01'))
        self.assertTrue(self.progression.activate('hp_01'))
        self.assertEqual(self.attributes.base_value('hp'), 140)
        self.assertEqual((self.attributes.current_hp, self.attributes.value('hp')), (140, 160))
        self.assertEqual(self.inventory.quantity('aether_emerald'), 1)
        before = self.snapshot()
        self.assertFalse(self.progression.activate('hp_01'))
        self.assertEqual(self.snapshot(), before)

    def test_ability_activation_uses_diamond_and_preserves_starting_magicks(self):
        self.assertTrue(self.progression.award_battle_rewards('training', {'caelan': 1000}, {'aether_diamond': 1}))
        self.assertTrue(self.progression.move('mend_01'))
        self.assertTrue(self.progression.activate('mend_01'))
        self.assertEqual(self.lattice.learned_abilities(), ['basic_magicks', 'mend'])
        self.assertEqual(self.inventory.quantity('aether_diamond'), 0)
        self.assertEqual(self.attributes.value('spr'), 10)

    def test_attribute_limit_failure_keeps_crystal_and_node_unactivated(self):
        record = self.attributes.to_dict()
        record['attributes']['hp'] = MAX_ATTRIBUTE_VALUE
        self.assertTrue(self.attributes.restore(record))
        self.assertTrue(self.progression.award_battle_rewards('limit', {'caelan': 20}, {'aether_emerald': 1}))
        self.assertTrue(self.progression.move('hp_01'))
        before = self.snapshot()
        self.assertFalse(self.progression.activate('hp_01'))
        self.assertEqual(self.snapshot(), before)

    def test_independent_characters_compete_for_shared_crystals(self):
        catalog = deepcopy(self.attributes.catalog)
        catalog['characters']['guest'] = deepcopy(catalog['characters']['caelan'])
        catalog['characters']['guest']['name'] = 'Guest'
        guest = CharacterAttributes('guest', catalog)
        lattice = AetherLattice(starts={'caelan': 'origin', 'guest': 'origin'})
        progression = LatticeProgression(lattice, self.inventory, {'caelan': self.attributes, 'guest': guest})
        self.assertTrue(progression.award_battle_rewards('party', {'caelan': 20, 'guest': 20}, {'aether_emerald': 1}))
        self.assertTrue(progression.move('hp_01', 'caelan'))
        self.assertTrue(progression.move('hp_01', 'guest'))
        self.assertTrue(progression.activate('hp_01', 'caelan'))
        self.assertFalse(progression.activate('hp_01', 'guest'))
        self.assertEqual((self.attributes.value('hp'), guest.value('hp')), (160, 140))
        self.assertEqual(lattice.state('guest')['activated'], [])

    def test_inventory_commit_rejection_rolls_back_reward_ledger(self):
        before = self.snapshot()
        with patch.object(self.inventory, 'restore', return_value=False):
            self.assertFalse(self.progression.award_battle_rewards('commit_fail', {'caelan': 20}, {'aether_emerald': 1}))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.lattice.has_receipt('commit_fail'))

    def test_combined_validation_uses_canonical_bonuses_and_rejects_missing_owners(self):
        self.assertTrue(self.progression.award_battle_rewards('grow', {'caelan': 20}, {'aether_emerald': 1}))
        self.assertTrue(self.progression.move('hp_01'))
        self.assertTrue(self.progression.activate('hp_01'))
        self.assertTrue(self.attributes.set_current(hp=160))
        record = {'aether_lattice': self.lattice.to_dict(), 'character_attributes': self.attributes.to_dict()}
        self.assertTrue(LatticeProgression.valid_journey(record))
        self.assertFalse(LatticeProgression.valid_journey({'character_attributes': record['character_attributes']}))
        self.assertFalse(LatticeProgression.valid_journey({'aether_lattice': record['aether_lattice']}))
        bad = deepcopy(record);bad['character_attributes']['current_hp'] = 161
        self.assertFalse(LatticeProgression.valid_journey(bad))


if __name__ == '__main__':unittest.main()
