"""Aether Lattice progression, graph rules and canonical ownership records."""
from collections import Counter
from copy import deepcopy
import unittest

from aether_lattice import AetherLattice, LatticeBoard, MAX_RP, MAX_RECEIPTS
from character_attributes import ATTRIBUTE_IDS


class AetherLatticeTests(unittest.TestCase):
    def setUp(self):
        self.lattice = AetherLattice()
        self.board = self.lattice.board

    def earn(self, amount, receipt='battle:1'):
        self.assertTrue(self.lattice.award_rewards(receipt, {'caelan': amount}))

    def test_caelan_layout_has_complete_approved_node_mix_and_crystal_families(self):
        self.assertEqual(len(self.board.nodes), 200)
        self.assertEqual(Counter(node['kind'] for node in self.board.nodes.values()),
                         {'blank': 50, 'stat': 130, 'ability': 20})
        self.assertGreater(len(self.board.edges), len(self.board.nodes)-1)
        self.assertEqual({node['stat'] for node in self.board.nodes.values()
                          if node['kind'] == 'stat'}, set(ATTRIBUTE_IDS))
        self.assertEqual(self.board.nodes['hp_01']['cost'], {'aether_emerald': 1})
        self.assertEqual(self.board.nodes['spr_01']['cost'], {'aether_opal': 1})
        self.assertEqual(self.board.nodes['mend_01']['cost'], {'aether_diamond': 1})
        self.assertEqual(self.board.edge_rank('blank_01', 'blank_05'), 5)
        self.assertEqual(self.board.edge_rank('blank_02', 'blank_06'), 8)
        self.assertEqual(self.lattice.learned_abilities(), ['basic_magicks'])

    def test_new_character_starts_with_no_free_rewards_or_growth(self):
        self.assertEqual(self.lattice.rank(), 1)
        self.assertEqual(self.lattice.steps(), 0)
        self.assertEqual(self.lattice.rp_progress(), (0, 20))
        self.assertEqual(self.lattice.state(), {'rp': 0, 'spent_steps': 0,
                         'position': 'origin', 'visited': ['origin'], 'activated': [],
                         'legacy_activated': []})
        self.assertFalse(any(self.lattice.bonuses().values()))
        self.assertFalse(self.lattice.move('hp_01'))
        self.assertFalse(self.lattice.activate('origin'))

    def test_rank_thresholds_overflow_and_multiple_level_reward(self):
        for rp, rank, progress in ((0, 1, (0, 20)), (19, 1, (19, 20)),
                                   (20, 2, (0, 25)), (44, 2, (24, 25)),
                                   (45, 3, (0, 30)), (75, 4, (0, 35)),
                                   (100, 4, (25, 35)), (110, 5, (0, 40))):
            with self.subTest(rp=rp):
                self.lattice.reset()
                self.earn(rp)
                self.assertEqual(self.lattice.rank(), rank)
                self.assertEqual(self.lattice.steps(), rank-1)
                self.assertEqual(self.lattice.rp_progress(), progress)
        self.lattice.reset();self.earn(100)
        self.assertTrue(self.lattice.move('blank_01'))
        self.assertEqual(self.lattice.rank(), 4)
        self.assertEqual(self.lattice.steps(), 1)

    def test_blank_movement_backtracking_and_optional_activation_are_separate(self):
        self.earn(75)
        self.assertEqual(self.lattice.route('blank_01'), ['origin', 'hp_01', 'blank_01'])
        self.assertTrue(self.lattice.move('blank_01'))
        self.assertFalse(any(self.lattice.bonuses().values()))
        self.assertEqual(self.lattice.steps(), 1)
        self.assertFalse(self.lattice.activate('blank_01'))
        self.assertTrue(self.lattice.move('hp_01'))
        self.assertEqual(self.lattice.steps(), 0)
        self.assertTrue(self.lattice.activate('hp_01'))
        self.assertEqual(self.lattice.bonuses()['hp'], 100)
        self.assertEqual(self.lattice.rank(), 4)
        self.assertFalse(self.lattice.activate('hp_01'))
        self.assertFalse(self.lattice.move('origin'))

    def test_rank_gated_connections_open_by_permanent_rank_not_remaining_steps(self):
        self.earn(75)
        self.assertIsNone(self.lattice.route('blank_05'))
        self.assertEqual(self.lattice.required_rank('mend_01'), 5)
        self.assertIn('Attunement 5', self.lattice.move_reason('mend_01'))
        self.assertEqual(self.lattice.required_rank('hp_03'), 8)
        self.assertTrue(self.lattice.award_rewards('battle:2', {'caelan': 35}))
        self.assertEqual(self.lattice.rank(), 5)
        self.assertTrue(self.lattice.move('blank_05'))
        self.assertEqual(self.lattice.steps(), 1)
        self.assertIsNotNone(self.lattice.route('mend_01'))
        self.assertIn('Steps', self.lattice.move_reason('mend_01'))

    def test_activate_only_current_node_once_and_learn_referenced_abilities(self):
        self.earn(10000)
        self.assertFalse(self.lattice.activate('hp_01'))
        self.assertIn('Move', self.lattice.activation_reason('hp_01'))
        self.assertTrue(self.lattice.move('mend_01'))
        self.assertTrue(self.lattice.activate('mend_01'))
        self.assertEqual(self.lattice.learned_abilities(), ['basic_magicks', 'mend'])
        self.assertTrue(self.lattice.move('brace_01'))
        self.assertTrue(self.lattice.activate('brace_01'))
        self.assertEqual(self.lattice.learned_abilities(), ['basic_magicks', 'brace', 'mend'])
        self.assertFalse(self.lattice.activate('brace_01'))

    def test_characters_share_graph_but_not_progress_or_activation(self):
        lattice = AetherLattice(self.board, {'caelan': 'origin', 'fixture_ally': 'origin'})
        self.assertTrue(lattice.award_rewards('battle:1', {'caelan': 20, 'fixture_ally': 45}))
        self.assertTrue(lattice.move('hp_01', 'caelan'))
        self.assertTrue(lattice.activate('hp_01', 'caelan'))
        self.assertEqual(lattice.bonuses('fixture_ally')['hp'], 0)
        self.assertEqual(lattice.state('fixture_ally')['position'], 'origin')
        self.assertTrue(lattice.move('hp_01', 'fixture_ally'))
        self.assertTrue(lattice.activate('hp_01', 'fixture_ally'))
        self.assertEqual(lattice.steps('caelan'), 0)
        self.assertEqual(lattice.steps('fixture_ally'), 1)
        self.assertEqual(lattice.rank('caelan'), 2)
        self.assertEqual(lattice.rank('fixture_ally'), 3)

    def test_reward_receipts_are_idempotent_and_bad_rewards_are_atomic(self):
        self.earn(20)
        before = self.lattice.to_dict()
        self.assertTrue(self.lattice.has_receipt('battle:1'))
        self.assertFalse(self.lattice.award_rewards('battle:1', {'caelan': 100}))
        for receipt, awards in (('', {'caelan': 1}), ([], {'caelan': 1}),
                                ('battle:2', {'unknown': 1}), ('battle:2', {'caelan': -1}),
                                ('battle:2', {'caelan': True}), ('battle:2', {'caelan': 1.0}),
                                ('battle:2', {'caelan': MAX_RP}), ('battle:2', [])):
            with self.subTest(receipt=receipt, awards=awards):
                self.assertFalse(self.lattice.award_rewards(receipt, awards))
                self.assertEqual(self.lattice.to_dict(), before)
        self.assertTrue(self.lattice.award_rewards('loot_only:1', {}))
        self.assertTrue(self.lattice.has_receipt('loot_only:1'))
        self.assertEqual(self.lattice.rank(), 2)
        self.assertTrue(self.lattice.award_rewards('battle:2', {'caelan': 1}))
        self.assertEqual(self.lattice.state()['rp'], 21)

    def test_save_round_trip_preserves_bonuses_without_duplicate_application(self):
        self.earn(10000)
        for target in ('hp_01', 'mend_01', 'brace_01'):
            self.assertTrue(self.lattice.move(target))
            self.assertTrue(self.lattice.activate(target))
        saved = self.lattice.to_dict()
        before = (self.lattice.bonuses(), self.lattice.learned_abilities(), self.lattice.steps())
        self.assertTrue(AetherLattice.valid_snapshot(saved))
        other = AetherLattice()
        for _ in range(3):
            self.assertTrue(other.restore(saved))
            self.assertEqual(other.to_dict(), saved)
            self.assertEqual((other.bonuses(), other.learned_abilities(), other.steps()), before)
        saved['characters']['caelan']['activated'].clear()
        saved['characters']['caelan']['rp'] = 0
        self.assertNotEqual(other.to_dict(), saved)

    def test_invalid_snapshot_shapes_types_and_impossible_records_are_rejected_atomically(self):
        before = self.lattice.to_dict()
        records = [None, [], {}, True]
        for key in before:
            bad = deepcopy(before);bad.pop(key);records.append(bad)
        for key, value in (('version', True), ('version', 3), ('board_id', 'wrong'),
                           ('board_version', True), ('receipts', ['battle:1', 'battle:1']),
                           ('receipts', [[]]), ('characters', {})):
            bad = deepcopy(before);bad[key] = value;records.append(bad)
        for key, value in (('rp', True), ('rp', MAX_RP+1), ('spent_steps', 1),
                           ('position', 'missing'), ('visited', ['origin', []]),
                           ('visited', ['origin', 'origin']), ('activated', ['origin']),
                           ('activated', ['hp_01']), ('visited', ['hp_01'])):
            bad = deepcopy(before);bad['characters']['caelan'][key] = value;records.append(bad)
        gate = deepcopy(before)
        gate['characters']['caelan'].update(rp=75, spent_steps=3, position='blank_05',
                                           visited=['origin', 'hp_01', 'blank_01', 'blank_05'])
        records.append(gate)
        for record in records:
            with self.subTest(record=record):
                self.assertFalse(AetherLattice.valid_snapshot(record))
                self.assertFalse(self.lattice.restore(record))
                self.assertEqual(self.lattice.to_dict(), before)

    def test_receipt_storage_bound_and_maximum_rp_do_not_overflow(self):
        saved = self.lattice.to_dict()
        saved['receipts'] = ['battle:'+str(i) for i in range(MAX_RECEIPTS)]
        self.assertTrue(self.lattice.restore(saved))
        self.assertFalse(self.lattice.award_rewards('battle:more', {'caelan': 1}))
        self.lattice.reset();self.earn(MAX_RP)
        rank = self.lattice.rank()
        self.assertLessEqual(self.board.rp_for_rank(rank), MAX_RP)
        self.assertGreater(self.board.rp_for_rank(rank+1), MAX_RP)
        progress, cost = self.lattice.rp_progress()
        self.assertLess(progress, cost)

    def test_tree_snapshots_require_paid_return_travel_and_valid_step_parity(self):
        original = self.lattice.to_dict()
        cases = ((20, 1, 'origin'), (75, 3, 'origin'), (45, 2, 'hp_01'))
        for rp, spent, position in cases:
            with self.subTest(rp=rp, spent=spent, position=position):
                bad = deepcopy(original)
                bad['characters']['caelan'].update(rp=rp, spent_steps=spent, position=position,
                                                   visited=['origin', 'hp_01'], activated=['hp_01'])
                self.assertFalse(AetherLattice.valid_snapshot(bad))
                self.assertFalse(self.lattice.restore(bad))
                self.assertEqual(self.lattice.to_dict(), original)
        no_edges = deepcopy(original)
        no_edges['characters']['caelan'].update(rp=45, spent_steps=2)
        self.assertFalse(self.lattice.restore(no_edges))
        round_trip = deepcopy(original)
        round_trip['characters']['caelan'].update(rp=45, spent_steps=2, position='origin',
                                                  visited=['origin', 'hp_01'], activated=['hp_01'])
        self.assertTrue(AetherLattice.valid_snapshot(round_trip))
        self.assertTrue(self.lattice.restore(round_trip))
        self.assertEqual(self.lattice.steps(), 0)
        self.assertEqual(self.lattice.bonuses()['hp'], 100)
        self.assertEqual(self.lattice.state()['position'], 'origin')

    def test_malformed_board_data_fails_before_mutating_inputs(self):
        data = self.board.data;abilities = self.board.ability_catalog
        cases = []
        for key, value in (('version', True), ('rank_curve', {'first': 0, 'increment': 5}),
                           ('starts', {'caelan': []}), ('starting_abilities', {'caelan': [[]]})):
            bad = deepcopy(data);bad[key] = value;cases.append(bad)
        for node, key, value in (('hp_01', 'amount', True), ('hp_01', 'stat', 'unknown'),
                                 ('hp_01', 'cost', {'missing': 1}), ('hp_01', 'cost', {'aether_emerald': -1}),
                                 ('origin', 'cost', {'aether_emerald': 1}), ('mend_01', 'ability_id', []),
                                 ('hp_01', 'position', data['nodes']['origin']['position'])):
            bad = deepcopy(data);bad['nodes'][node][key] = value;cases.append(bad)
        bad = deepcopy(data);bad['edges'].append(deepcopy(bad['edges'][0]));cases.append(bad)
        bad = deepcopy(data);bad['edges'] = [];cases.append(bad)
        bad = deepcopy(data);bad['edges'][0]['min_rank'] = True;cases.append(bad)
        for record in cases:
            with self.subTest(record=record):
                unchanged = deepcopy(record)
                with self.assertRaises(ValueError):LatticeBoard(record, abilities)
                self.assertEqual(record, unchanged)

    def test_unknown_movement_activation_and_empty_paths_never_mutate(self):
        self.earn(20);before = self.lattice.to_dict()
        for target in (None, [], 'missing', 'origin'):
            self.assertFalse(self.lattice.move(target))
            self.assertFalse(self.lattice.activate(target))
            self.assertEqual(self.lattice.to_dict(), before)
        self.assertIsNone(self.lattice.route([]))
        self.assertIsNone(self.lattice.route('hp_01', []))
        self.assertFalse(self.lattice.move('hp_01', []))
        self.assertFalse(self.lattice.activate('hp_01', 'missing'))


if __name__ == '__main__':unittest.main()
