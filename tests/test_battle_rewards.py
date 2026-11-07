"""Item grants and battle receipts commit together without progression owners."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from battle_rewards import BattleRewards, MAX_RECEIPTS
from inventory import Inventory, MAX_QUANTITY


class BattleRewardTests(unittest.TestCase):
    def setUp(self):
        self.inventory = Inventory()
        self.owner = BattleRewards(self.inventory)

    def state(self):
        return self.inventory.to_dict(), self.owner.to_dict()

    def test_once_only_grant_survives_independent_owner_restore(self):
        self.assertTrue(self.owner.award_battle_rewards('battle:first', {'aether_emerald': 2}))
        self.assertEqual(self.inventory.quantity('aether_emerald'), 2)
        before = self.state()
        clone = BattleRewards(self.inventory)
        self.assertTrue(clone.restore(self.owner.to_dict()))
        self.assertFalse(clone.award_battle_rewards('battle:first', {'aether_emerald': 2}))
        self.assertEqual(self.state(), before)
        self.assertTrue(clone.award_battle_rewards('battle:second', {'aether_emerald': 1}))
        self.assertEqual(self.inventory.quantity('aether_emerald'), 3)

    def test_empty_capped_spoils_still_record_receipt_once(self):
        self.assertTrue(self.inventory.add('aether_emerald', MAX_QUANTITY))
        before = self.inventory.to_dict()
        self.assertTrue(self.owner.award_battle_rewards('battle:empty', {}))
        self.assertTrue(self.owner.has_receipt('battle:empty'))
        self.assertFalse(self.owner.award_battle_rewards('battle:empty', {}))
        self.assertEqual(self.inventory.to_dict(), before)

    def test_invalid_bundle_or_capacity_failure_never_consumes_receipt(self):
        self.assertTrue(self.inventory.add('aether_emerald', MAX_QUANTITY))
        before = self.state()
        invalid = [None, [], {'missing': 1}, {'aether_ruby': 0},
                   {'aether_ruby': True}, {'aether_ruby': 1.0},
                   {'aether_ruby': 1, 'aether_emerald': 1},
                   {'aether_ruby': MAX_QUANTITY+1}]
        key_item = next(key for key, value in self.inventory.definitions.items()
                        if value['category'] == 'key_items')
        invalid.append({key_item: 1})
        for bundle in invalid:
            with self.subTest(bundle=bundle):
                self.assertFalse(self.owner.award_battle_rewards('battle:retry', bundle))
                self.assertEqual(self.state(), before)
        self.assertTrue(self.owner.award_battle_rewards('battle:retry', {'aether_ruby': 1}))

    def test_inventory_commit_failure_keeps_both_owners_unchanged(self):
        before = self.state()
        with patch.object(self.inventory, 'restore', return_value=False):
            self.assertFalse(self.owner.award_battle_rewards('battle:retry', {'aether_ruby': 1}))
        self.assertEqual(self.state(), before)

    def test_snapshot_shapes_identifiers_and_capacity_are_strict(self):
        self.assertTrue(self.owner.award_battle_rewards('battle:first', {}))
        before = self.state()
        invalid = [None, [], {}, {'version': True, 'receipts': []},
                   {'version': 2, 'receipts': []}, {'version': 1, 'receipts': ['same', 'same']},
                   {'version': 1, 'receipts': [True]}, {'version': 1, 'receipts': ['']},
                   {'version': 1, 'receipts': ['has space']},
                   {'version': 1, 'receipts': [], 'extra': 1}]
        for record in invalid:
            with self.subTest(record=record):
                self.assertFalse(self.owner.restore(record))
                self.assertEqual(self.state(), before)
        full = {'version': 1, 'receipts': ['battle:'+str(index) for index in range(MAX_RECEIPTS)]}
        self.assertTrue(self.owner.restore(full))
        before = self.state()
        self.assertFalse(self.owner.award_battle_rewards('battle:overflow', {}))
        self.assertEqual(self.state(), before)
        full['receipts'].append('battle:overflow')
        self.assertFalse(self.owner.restore(full))
        self.assertEqual(self.state(), before)

    def test_invalid_receipt_never_changes_inventory(self):
        before = self.state()
        for receipt in (None, True, 3, [], '', 'bad receipt', 'x'*129):
            with self.subTest(receipt=receipt):
                self.assertFalse(self.owner.award_battle_rewards(receipt, {'aether_ruby': 1}))
                self.assertEqual(self.state(), before)

    def test_exports_do_not_alias_receipts_or_inventory(self):
        self.assertTrue(self.owner.award_battle_rewards('battle:first', {'aether_ruby': 1}))
        exported = self.owner.to_dict()
        exported['receipts'].clear()
        self.assertTrue(self.owner.has_receipt('battle:first'))
        self.assertTrue(BattleRewards.valid_journey({'battle_rewards': self.owner.to_dict()}))
        self.assertFalse(BattleRewards.valid_journey({'battle_rewards': None}))
        self.assertTrue(BattleRewards.valid_journey({}))


if __name__ == '__main__':
    unittest.main()
