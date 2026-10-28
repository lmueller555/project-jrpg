"""Formation geometry and archived-rule migration preserve earned progression."""
from copy import deepcopy
import json
import unittest

from aether_lattice import AetherLattice, LatticeBoard, LEGACY_BOARD_PATH


def legacy_data():
    return json.loads(LEGACY_BOARD_PATH.read_text(encoding='utf-8'))


def formation_data():
    data = legacy_data()
    data.update(id='formation_fixture', version=2)
    positions = {'origin': [-40, 0], 'hp_01': [0, 0],
                 'blank_01': [40, 0], 'str_01': [0, 40]}
    data['nodes'] = {key: {**data['nodes'][key], 'position': position}
                     for key, position in positions.items()}
    data['nodes']['bridge'] = {'kind': 'blank', 'name': 'Bridge',
                              'description': 'A straight path outside the formation.',
                              'position': [160, 0], 'cost': {}}
    data['edges'] = [
        {'from': 'origin', 'to': 'hp_01', 'min_rank': 1, 'curve': [-20, -8]},
        {'from': 'hp_01', 'to': 'blank_01', 'min_rank': 1, 'curve': [20, -8]},
        {'from': 'blank_01', 'to': 'str_01', 'min_rank': 1, 'curve': [40, 35]},
        {'from': 'str_01', 'to': 'origin', 'min_rank': 1, 'curve': [-40, 35]},
        {'from': 'blank_01', 'to': 'bridge', 'min_rank': 1},
    ]
    data['formations'] = {'small': {
        'name': 'Small circle', 'center': [0, 0], 'radius': 80, 'size': 'small',
        'nodes': list(positions), 'center_node': 'hp_01',
        'entry': 'origin', 'exit': 'blank_01',
    }}
    return data


class FormationSchemaTests(unittest.TestCase):
    def test_legacy_board_stays_straight_without_formation_metadata(self):
        board = LatticeBoard(legacy_data())
        self.assertEqual(board.formations, {})
        self.assertEqual(board.node_formations, {})
        self.assertEqual((board.version, len(board.nodes), len(board.edges)), (1, 30, 29))

    def test_formations_expose_membership_and_keep_exterior_nodes_outside(self):
        original = formation_data()
        board = LatticeBoard(original)
        self.assertEqual(board.formations['small']['center_node'], 'hp_01')
        self.assertEqual(set(board.node_formations), {'origin', 'hp_01', 'blank_01', 'str_01'})
        self.assertNotIn('bridge', board.node_formations)
        self.assertEqual(board.edge_rank('blank_01', 'bridge'), 1)
        original['formations']['small']['nodes'].clear()
        self.assertEqual(len(board.formations['small']['nodes']), 4)

    def test_invalid_geometry_and_membership_are_rejected(self):
        cases = []
        for value in (None, [], {}, True):
            bad = formation_data();bad['formations'] = value;cases.append(bad)
        for key, value in (
                ('name', ''), ('center', [False, 0]), ('center', [0.0, 0]),
                ('center', [100001, 0]), ('center', [1, 0]), ('radius', 0),
                ('radius', True), ('radius', 100001), ('radius', 10), ('size', 'medium'),
                ('nodes', []), ('nodes', ['origin', 'hp_01', 'missing']),
                ('nodes', ['origin', 'hp_01', ['bad']]),
                ('nodes', ['origin', 'hp_01', 'blank_01', 'origin']),
                ('center_node', 'bridge'), ('entry', 'bridge'), ('entry', 'hp_01'),
                ('exit', 'origin')):
            bad = formation_data();bad['formations']['small'][key] = value;cases.append(bad)
        bad = formation_data();bad['formations']['small'].pop('exit');cases.append(bad)
        bad = formation_data();bad['formations']['small']['unknown'] = 1;cases.append(bad)
        bad = formation_data();bad['formations']['other'] = deepcopy(bad['formations']['small']);cases.append(bad)
        for record in cases:
            with self.subTest(record=record):
                original = deepcopy(record)
                with self.assertRaises(ValueError):LatticeBoard(record)
                self.assertEqual(record, original)

    def test_only_internal_connections_may_curve_and_unknown_fields_fail(self):
        cases = []
        for value in (None, [], [1], [False, 0], [0.5, 0], [100001, 0]):
            bad = formation_data();bad['edges'][0]['curve'] = value;cases.append(bad)
        bad = formation_data();bad['edges'][0].pop('curve');cases.append(bad)
        bad = formation_data();bad['edges'][-1]['curve'] = [80, 0];cases.append(bad)
        bad = formation_data();bad.pop('formations');cases.append(bad)
        bad = formation_data();bad['edges'][0]['unknown'] = True;cases.append(bad)
        for record in cases:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):LatticeBoard(record)

    def test_a_connected_center_cannot_end_in_a_dead_end(self):
        data = formation_data()
        data['edges'].pop(1)
        with self.assertRaisesRegex(ValueError, 'continuing'):LatticeBoard(data)

    def test_two_center_edges_must_offer_a_genuine_onward_route(self):
        data = formation_data()
        data['nodes']['origin']['position'] = [-60, 0]
        data['nodes']['blank_01']['position'] = [60, 0]
        data['nodes']['str_01']['position'] = [0, 60]
        data['nodes']['inner'] = {'kind': 'blank', 'name': 'Inner', 'description': 'Inner loop.',
                                  'position': [0, 30], 'cost': {}}
        data['formations']['small']['nodes'].append('inner')
        data['edges'] = [
            {'from': a, 'to': b, 'min_rank': 1, 'curve': control}
            for a, b, control in (
                ('origin', 'str_01', [-40, 60]), ('blank_01', 'str_01', [40, 60]),
                ('str_01', 'hp_01', [-8, 30]), ('hp_01', 'inner', [8, 15]),
                ('inner', 'str_01', [8, 45]))]
        data['edges'].append({'from': 'blank_01', 'to': 'bridge', 'min_rank': 1})
        # Both center neighbors return through str_01 before either endpoint.
        with self.assertRaisesRegex(ValueError, 'continuing'):LatticeBoard(data)

    def test_current_cycle_round_trip_keeps_paid_steps_and_activation(self):
        board = LatticeBoard(formation_data())
        lattice = AetherLattice(board)
        self.assertTrue(lattice.award_rewards('cycle_battle', {'caelan': 1000}))
        self.assertTrue(lattice.move('hp_01'));self.assertTrue(lattice.activate('hp_01'))
        for target in ('blank_01', 'str_01', 'origin'):self.assertTrue(lattice.move(target))
        snapshot = lattice.to_dict()
        self.assertEqual(snapshot['characters']['caelan']['spent_steps'], 4)
        self.assertTrue(AetherLattice.valid_snapshot(snapshot, board))
        restored = AetherLattice(board)
        self.assertTrue(restored.restore(snapshot))
        self.assertEqual(restored.to_dict(), snapshot)
        self.assertEqual(restored.bonuses()['hp'], 20)

    def test_even_cycles_require_paid_closed_returns_and_bipartite_parity(self):
        board = LatticeBoard(formation_data())
        initial = AetherLattice(board).to_dict()
        visited = ['origin', 'hp_01', 'blank_01', 'str_01']
        for spent, position, valid in ((3, 'origin', False), (4, 'hp_01', False),
                                       (4, 'origin', True), (5, 'hp_01', True)):
            snapshot = deepcopy(initial)
            snapshot['characters']['caelan'].update(rp=1000, spent_steps=spent,
                                                    position=position, visited=visited)
            with self.subTest(spent=spent, position=position):
                self.assertEqual(AetherLattice.valid_snapshot(snapshot, board), valid)
                fresh = AetherLattice(board)
                self.assertEqual(fresh.restore(snapshot), valid)
                if not valid:self.assertEqual(fresh.to_dict(), initial)

    def test_odd_cycles_allow_legitimate_odd_return_walks(self):
        data = formation_data()
        data['edges'].append({'from': 'origin', 'to': 'blank_01', 'min_rank': 1,
                              'curve': [0, -20]})
        board = LatticeBoard(data)
        lattice = AetherLattice(board)
        self.assertTrue(lattice.award_rewards('triangle_battle', {'caelan': 1000}))
        for node in ('hp_01', 'blank_01', 'origin'):self.assertTrue(lattice.move(node))
        snapshot = lattice.to_dict()
        self.assertEqual(snapshot['characters']['caelan']['spent_steps'], 3)
        self.assertTrue(AetherLattice.valid_snapshot(snapshot, board))
        restored = AetherLattice(board);self.assertTrue(restored.restore(snapshot))
        self.assertEqual(restored.to_dict(), snapshot)


class LegacyFormationMigrationTests(unittest.TestCase):
    def setUp(self):
        self.legacy = LatticeBoard(legacy_data())
        data = legacy_data();data['version'] = 2
        data['nodes']['future'] = {'kind': 'blank', 'name': 'Future', 'description': 'New path.',
                                  'position': [2000, 0], 'cost': {}}
        data['edges'].append({'from': 'mag_02', 'to': 'future', 'min_rank': 50})
        self.current = LatticeBoard(data)

    def earned_snapshot(self):
        lattice = AetherLattice(self.legacy)
        self.assertTrue(lattice.award_rewards('battle:legacy', {'caelan': 10000}))
        for target in ('hp_01', 'mend_01', 'brace_01'):
            self.assertTrue(lattice.move(target));self.assertTrue(lattice.activate(target))
        self.assertTrue(lattice.award_rewards('loot:legacy', {}))
        return lattice.to_dict(), lattice

    def test_existing_progress_upgrades_only_board_version_without_mutating_input(self):
        saved, old = self.earned_snapshot();original = deepcopy(saved)
        self.assertTrue(AetherLattice.valid_snapshot(saved, self.current))
        fresh = AetherLattice(self.current)
        for _ in range(3):
            self.assertTrue(fresh.restore(saved))
            expected = deepcopy(original);expected['board_version'] = 2
            self.assertEqual(fresh.to_dict(), expected)
            self.assertEqual(fresh.state(), old.state())
            self.assertEqual(fresh.steps(), old.steps())
            self.assertEqual(fresh.bonuses(), old.bonuses())
            self.assertEqual(fresh.learned_abilities(), old.learned_abilities())
        self.assertEqual(saved, original)

    def test_fresh_legacy_state_and_receipts_are_preserved(self):
        original = AetherLattice(self.legacy)
        self.assertTrue(original.award_rewards('old_loot_receipt', {}))
        fresh = AetherLattice(self.current)
        self.assertTrue(fresh.restore(original.to_dict()))
        self.assertEqual(fresh.state(), original.state())
        self.assertEqual(fresh.steps(), 0)
        self.assertTrue(fresh.has_receipt('old_loot_receipt'))
        self.assertFalse(any(fresh.bonuses().values()))

    def test_old_forged_travel_is_rejected_using_archived_tree_rules(self):
        data = deepcopy(self.current.data)
        data['edges'].append({'from': 'origin', 'to': 'blank_01', 'min_rank': 1})
        current = LatticeBoard(data)
        snapshot = AetherLattice(self.legacy).to_dict()
        snapshot['characters']['caelan'].update(rp=45, spent_steps=2, position='origin',
                                                visited=['origin', 'hp_01', 'blank_01'])
        fresh = AetherLattice(current);before = fresh.to_dict()
        self.assertFalse(AetherLattice.valid_snapshot(snapshot, current))
        self.assertFalse(fresh.restore(snapshot))
        self.assertEqual(fresh.to_dict(), before)

    def test_legacy_version_cannot_claim_new_nodes_or_change_earned_rules(self):
        snapshot, _ = self.earned_snapshot()
        bad = deepcopy(snapshot)
        bad['characters']['caelan']['visited'].append('future')
        self.assertFalse(AetherLattice.valid_snapshot(bad, self.current))
        records = []
        data = deepcopy(self.current.data);data['nodes']['hp_01']['amount'] = 40;records.append(data)
        data = deepcopy(self.current.data);data['rank_curve']['first'] += 1;records.append(data)
        data = deepcopy(self.current.data);data['starts']['caelan'] = 'hp_01';records.append(data)
        data = deepcopy(self.current.data);data['edges'][19]['min_rank'] = 4;records.append(data)
        for data in records:
            with self.subTest(data=data):
                self.assertFalse(AetherLattice.valid_snapshot(snapshot, LatticeBoard(data)))

    def test_unknown_board_versions_and_ids_do_not_migrate(self):
        saved, _ = self.earned_snapshot()
        for key, value in (('board_version', 0), ('board_version', True), ('board_version', 3),
                           ('board_id', 'different_board')):
            bad = deepcopy(saved);bad[key] = value
            with self.subTest(key=key, value=value):
                self.assertFalse(AetherLattice.valid_snapshot(bad, self.current))


if __name__ == '__main__':unittest.main()
