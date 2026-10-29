"""Tier upgrades retain paid rewards and validate old journeys before migration."""
from copy import deepcopy
import json
import unittest

from aether_lattice import (AetherLattice, LatticeBoard, LEGACY_BOARD_PATH,
                            PRE_TIER_BOARD_PATH)
from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from inventory import Inventory
from lattice_progression import LatticeProgression


def read_board(path):
    return LatticeBoard(json.loads(path.read_text(encoding='utf-8')))


def tier_fixture():
    # This fixture works before or after the authored board lands and exercises
    # changed magnitude, changed stat family and a newly activated reward.
    data = json.loads(PRE_TIER_BOARD_PATH.read_text(encoding='utf-8'))
    data['version'] = 3
    for identifier, stat, amount, crystal in (
            ('hp_01', 'hp', 100, 'aether_emerald'),
            ('hp_02', 'mp', 10, 'aether_sapphire'),
            ('hp_03', 'mag', 4, 'aether_amethyst'),
            ('mp_01', 'mp', 5, 'aether_sapphire')):
        data['nodes'][identifier].update(stat=stat, amount=amount, cost={crystal: 1})
    return LatticeBoard(data)


class LatticeTierMigrationTests(unittest.TestCase):
    def setUp(self):
        self.old = read_board(PRE_TIER_BOARD_PATH)
        self.current = tier_fixture()

    def earn_old(self, version=2, targets=('hp_01', 'hp_02', 'hp_03', 'mend_01')):
        board = self.old if version == 2 else read_board(LEGACY_BOARD_PATH)
        lattice = AetherLattice(board)
        self.assertTrue(lattice.award_rewards('old:battle', {'caelan': 10000}))
        for target in targets:
            self.assertTrue(lattice.move(target))
            self.assertTrue(lattice.activate(target))
        self.assertTrue(lattice.award_rewards('old:loot', {}))
        return lattice

    def journey(self, lattice):
        attributes = CharacterAttributes()
        self.assertTrue(attributes.set_modifiers('lattice', lattice.bonuses()))
        self.assertTrue(attributes.set_current(hp=attributes.value('hp'), mp=attributes.value('mp')))
        inventory = Inventory()
        self.assertTrue(inventory.add('aether_emerald', 3))
        self.assertTrue(inventory.add('aether_sapphire', 2))
        return {'aether_lattice': lattice.to_dict(),
                'character_attributes': attributes.to_dict(),
                'inventory': inventory.to_dict()}, attributes

    def test_v2_archive_is_the_exact_pre_tier_board_and_keeps_all_paid_rules(self):
        self.assertEqual(self.old.version, 2)
        self.assertEqual(len(self.old.nodes), 200)
        self.assertEqual(self.old.nodes['hp_01']['amount'], 20)
        self.assertEqual(self.old.nodes['hp_02']['stat'], 'hp')
        self.assertEqual(self.old.nodes['mp_01']['amount'], 2)

    def test_fresh_tiered_ledger_has_no_legacy_rewards_or_unearned_bonuses(self):
        lattice = AetherLattice(self.current)
        self.assertEqual(lattice.to_dict()['version'], 2)
        self.assertEqual(lattice.to_dict()['board_version'], 3)
        self.assertEqual(lattice.state()['legacy_activated'], [])
        self.assertFalse(any(lattice.bonuses().values()))
        self.assertTrue(lattice.award_rewards('new:battle', {'caelan': 20}))
        self.assertTrue(lattice.move('hp_01'))
        self.assertTrue(lattice.activate('hp_01'))
        self.assertEqual(lattice.bonuses()['hp'], 100)
        self.assertEqual(lattice.state()['legacy_activated'], [])

    def test_v1_and_v2_keep_every_paid_bonus_including_retyped_hp_nodes(self):
        for version in (1, 2):
            with self.subTest(version=version):
                old = self.earn_old(version)
                saved = old.to_dict();original = deepcopy(saved)
                current = AetherLattice(self.current)
                self.assertTrue(current.restore(saved))
                self.assertTrue(AetherLattice.valid_snapshot(saved, self.current))
                self.assertEqual(current.bonuses(), old.bonuses())
                self.assertEqual(current.learned_abilities(), old.learned_abilities())
                self.assertEqual(current.rank(), old.rank())
                self.assertEqual(current.steps(), old.steps())
                state = current.state();legacy = state.pop('legacy_activated')
                self.assertEqual(state, old.state())
                self.assertEqual(legacy, old.state()['activated'])
                self.assertEqual(current.to_dict()['receipts'], old.to_dict()['receipts'])
                self.assertEqual(current.reward_node('hp_02')['stat'], 'hp')
                self.assertEqual(current.reward_node('hp_03')['stat'], 'hp')
                self.assertFalse(current.activate('hp_03'))
                self.assertEqual(saved, original)

    def test_current_resources_and_base_values_restore_without_refill_or_reductions(self):
        old = self.earn_old()
        saved, original_attributes = self.journey(old)
        original = deepcopy(saved)
        lattice = AetherLattice(self.current)
        self.assertTrue(lattice.restore(saved['aether_lattice']))
        attributes = CharacterAttributes()
        self.assertTrue(attributes.restore(saved['character_attributes'], lattice_bonuses=lattice.bonuses()))
        self.assertEqual(attributes.to_dict(), original_attributes.to_dict())
        self.assertEqual(tuple(attributes.value(stat) for stat in ATTRIBUTE_IDS),
                         tuple(original_attributes.value(stat) for stat in ATTRIBUTE_IDS))
        self.assertEqual(attributes.current_hp, original_attributes.current_hp)
        self.assertEqual(attributes.current_mp, original_attributes.current_mp)
        self.assertEqual(attributes.base_value('hp'), 140)
        self.assertEqual(saved, original)

    def test_mixed_old_and_new_rewards_round_trip_without_double_apply(self):
        old = self.earn_old(targets=('hp_01', 'hp_02'))
        record, original_attributes = self.journey(old)
        lattice = AetherLattice(self.current)
        self.assertTrue(lattice.restore(record['aether_lattice']))
        attributes = CharacterAttributes()
        self.assertTrue(attributes.restore(record['character_attributes'], lattice_bonuses=lattice.bonuses()))
        inventory = Inventory();self.assertTrue(inventory.restore(record['inventory']))
        coordinator = LatticeProgression(lattice, inventory, {'caelan': attributes})
        self.assertTrue(coordinator.move('mp_01'))
        self.assertTrue(coordinator.activate('mp_01'))
        self.assertEqual(attributes.value('mp'), original_attributes.value('mp')+5)
        self.assertEqual(attributes.current_mp, original_attributes.current_mp)
        self.assertEqual(inventory.quantity('aether_sapphire'), 1)
        self.assertNotIn('mp_01', lattice.state()['legacy_activated'])
        expected = lattice.to_dict(), attributes.to_dict(), inventory.to_dict()
        expected_values = {stat: attributes.value(stat) for stat in ATTRIBUTE_IDS}
        for _ in range(3):
            clone = AetherLattice(self.current);self.assertTrue(clone.restore(expected[0]))
            attrs = CharacterAttributes();self.assertTrue(attrs.restore(expected[1], lattice_bonuses=clone.bonuses()))
            inv = Inventory();self.assertTrue(inv.restore(expected[2]))
            self.assertEqual((clone.to_dict(), attrs.to_dict(), inv.to_dict()), expected)
            self.assertEqual({stat: attrs.value(stat) for stat in ATTRIBUTE_IDS}, expected_values)
            self.assertFalse(clone.activate('hp_02'))
            self.assertFalse(clone.activate('mp_01'))
            self.assertFalse(clone.award_rewards('old:battle', {'caelan': 100}))

    def test_newly_retyped_reward_uses_new_stat_and_crystal_without_free_bonus(self):
        old = self.earn_old(targets=('hp_01',))
        lattice = AetherLattice(self.current);self.assertTrue(lattice.restore(old.to_dict()))
        attributes = CharacterAttributes();self.assertTrue(attributes.set_modifiers('lattice', lattice.bonuses()))
        inventory = Inventory();self.assertTrue(inventory.add('aether_emerald', 2))
        coordinator = LatticeProgression(lattice, inventory, {'caelan': attributes})
        self.assertTrue(coordinator.move('hp_02'))
        before = lattice.to_dict(), inventory.to_dict(), attributes.to_dict()
        self.assertFalse(coordinator.activate('hp_02'))
        self.assertEqual((lattice.to_dict(), inventory.to_dict(), attributes.to_dict()), before)
        self.assertTrue(inventory.add('aether_sapphire', 1))
        self.assertTrue(coordinator.activate('hp_02'))
        self.assertEqual(lattice.bonuses()['hp'], 20)
        self.assertEqual(lattice.bonuses()['mp'], 10)
        self.assertEqual(inventory.quantity('aether_emerald'), 2)
        self.assertEqual(inventory.quantity('aether_sapphire'), 0)
        self.assertEqual(attributes.current_hp, 140)
        self.assertEqual(attributes.current_mp, 30)

    def test_forged_old_travel_is_rejected_before_more_permissive_new_graph(self):
        # The original v1 tree cannot claim a paid closed return in three Steps.
        old = AetherLattice(read_board(LEGACY_BOARD_PATH)).to_dict()
        old['characters']['caelan'].update(rp=75, spent_steps=3, position='origin',
                visited=['origin', 'hp_01', 'blank_01'], activated=['hp_01'])
        current = AetherLattice(self.current);before = current.to_dict()
        self.assertFalse(current.restore(old))
        self.assertEqual(current.to_dict(), before)

    def test_invalid_provenance_versions_and_missing_resources_reject_atomically(self):
        migrated = AetherLattice(self.current)
        self.assertTrue(migrated.restore(self.earn_old().to_dict()))
        saved = migrated.to_dict()
        cases = []
        for value in (None, {}, True, ['missing'], ['origin'], ['mp_01'],
                      ['hp_01', 'hp_01'], [False], [[]]):
            bad = deepcopy(saved);bad['characters']['caelan']['legacy_activated'] = value;cases.append(bad)
        bad = deepcopy(saved);bad['characters']['caelan'].pop('legacy_activated');cases.append(bad)
        for key, value in (('version', 1), ('version', True), ('board_version', 4),
                           ('board_version', True), ('board_id', 'other')):
            bad = deepcopy(saved);bad[key] = value;cases.append(bad)
        bad = deepcopy(saved);bad['board_version'] = 2;cases.append(bad)
        for data in cases:
            with self.subTest(data=data):
                fresh = AetherLattice(self.current);before = fresh.to_dict()
                self.assertFalse(fresh.restore(data))
                self.assertFalse(AetherLattice.valid_snapshot(data, self.current))
                self.assertEqual(fresh.to_dict(), before)

    def test_migration_rejects_changed_travel_rules_abilities_or_unknown_board_lineage(self):
        saved = self.earn_old().to_dict()
        bad_boards = []
        data = deepcopy(self.current.data);data['rank_curve']['first'] += 1;bad_boards.append(data)
        data = deepcopy(self.current.data);data['starting_abilities']['caelan'] = [];bad_boards.append(data)
        data = deepcopy(self.current.data);data['edges'][0]['min_rank'] += 1;bad_boards.append(data)
        data = deepcopy(self.current.data);data['nodes']['mend_01']['ability_id'] = 'brace';bad_boards.append(data)
        for data in bad_boards:
            with self.subTest(data=data):
                current = AetherLattice(LatticeBoard(data));before = current.to_dict()
                self.assertFalse(current.restore(saved))
                self.assertEqual(current.to_dict(), before)

    def test_reset_removes_migration_provenance_and_rewards(self):
        lattice = AetherLattice(self.current)
        self.assertTrue(lattice.restore(self.earn_old().to_dict()))
        self.assertTrue(lattice.state()['legacy_activated'])
        lattice.reset()
        self.assertEqual(lattice.state()['legacy_activated'], [])
        self.assertFalse(any(lattice.bonuses().values()))
        self.assertEqual(lattice.state()['position'], 'origin')
        self.assertEqual(lattice.steps(), 0)


if __name__ == '__main__':unittest.main()
