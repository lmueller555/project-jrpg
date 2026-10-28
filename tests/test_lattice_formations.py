"""Caelan's authored section: growth budget, readable paths and onward routes."""
from collections import Counter, deque
from copy import deepcopy
import json
from pathlib import Path
import unittest

from aether_lattice import AetherLattice, LatticeBoard, MAX_RP
from character_attributes import CharacterAttributes


COUNTS = {'hp': 30, 'mp': 12, 'str': 14, 'mag': 14, 'spr': 12, 'def': 14,
          'm_def': 12, 'speed': 8, 'acc': 6, 'eva': 4, 'lck': 4}
GAINS = {'hp': 3000, 'mp': 180, 'str': 45, 'mag': 45, 'spr': 40, 'def': 45,
         'm_def': 40, 'speed': 30, 'acc': 30, 'eva': 20, 'lck': 10}
FINAL = {'hp': 3140, 'mp': 210, 'str': 55, 'mag': 55, 'spr': 50, 'def': 55,
         'm_def': 50, 'speed': 40, 'acc': 40, 'eva': 30, 'lck': 20}


def _points(board, edge):
    start, end = (board.nodes[edge[key]]['position'] for key in ('from', 'to'))
    if 'curve' not in edge:return [tuple(start), tuple(end)]
    control = edge['curve']
    return [tuple((1-t)**2*start[axis]+2*(1-t)*t*control[axis]+t*t*end[axis]
                  for axis in (0, 1)) for t in (index/32 for index in range(33))]


def _bounds(points):
    return (min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points))


def _intersect(a, b, c, d):
    def cross(x, y):return x[0]*y[1]-x[1]*y[0]
    r, s = (b[0]-a[0], b[1]-a[1]), (d[0]-c[0], d[1]-c[1])
    delta = (c[0]-a[0], c[1]-a[1])
    denominator = cross(r, s)
    if abs(denominator) < 1e-8:
        if abs(cross(delta, r)) > 1e-8:return False
        axis = 0 if abs(r[0]) >= abs(r[1]) else 1
        return (min(max(a[axis], b[axis]), max(c[axis], d[axis]))-
                max(min(a[axis], b[axis]), min(c[axis], d[axis]))) > 1e-6
    t, u = cross(delta, s)/denominator, cross(delta, r)/denominator
    return -1e-8 <= t <= 1+1e-8 and -1e-8 <= u <= 1+1e-8


def _distance_squared(point, start, end):
    x, y = end[0]-start[0], end[1]-start[1]
    length = x*x+y*y
    t = max(0, min(1, ((point[0]-start[0])*x+(point[1]-start[1])*y)/length)) if length else 0
    return (point[0]-start[0]-t*x)**2+(point[1]-start[1]-t*y)**2


class LatticeFormationTests(unittest.TestCase):
    def setUp(self):
        self.board = LatticeBoard()
        self.lattice = AetherLattice(self.board)

    def test_full_section_has_the_proposed_stat_ability_and_empty_node_budget(self):
        self.assertEqual(len(self.board.nodes), 200)
        self.assertEqual(Counter(node['kind'] for node in self.board.nodes.values()),
                         {'stat': 130, 'ability': 20, 'blank': 50})
        self.assertEqual(Counter(node['stat'] for node in self.board.nodes.values()
                                 if node['kind'] == 'stat'), COUNTS)
        self.assertEqual({stat: sum(node['amount'] for node in self.board.nodes.values()
                                   if node['kind'] == 'stat' and node['stat'] == stat)
                          for stat in GAINS}, GAINS)
        abilities = [node['ability_id'] for node in self.board.nodes.values() if node['kind'] == 'ability']
        self.assertEqual(len(set(abilities)), 20)
        self.assertNotIn('basic_magicks', abilities)

    def test_existing_node_effects_crystal_costs_and_starter_travel_remain_intact(self):
        path = Path(__file__).resolve().parents[1]/'assets/progression/aether_lattice_v1.json'
        legacy = LatticeBoard(json.loads(path.read_text()))
        for identifier, original in legacy.nodes.items():
            with self.subTest(node=identifier):
                expected, actual = deepcopy(original), deepcopy(self.board.nodes[identifier])
                expected.pop('position');actual.pop('position')
                self.assertEqual(actual, expected)
        for edge in legacy.edges:
            self.assertEqual(self.board.edge_rank(edge['from'], edge['to']), edge['min_rank'])
        self.assertEqual(self.lattice.route('hp_01'), ['origin', 'hp_01'])
        self.assertEqual(self.lattice.route('blank_01'), ['origin', 'hp_01', 'blank_01'])
        self.assertEqual(len(self.lattice.route('str_01'))-1, 3)
        self.assertEqual(self.lattice.required_rank('mend_01'), 5)
        self.assertEqual(self.lattice.required_rank('hp_03'), 8)

    def test_small_and_large_formations_use_curves_and_all_other_links_are_straight(self):
        formations = self.board.formations
        sizes = Counter(record['size'] for record in formations.values())
        self.assertGreaterEqual(sizes['large'], 2)
        self.assertGreaterEqual(sizes['small'], 2)
        self.assertLess(max(record['radius'] for record in formations.values() if record['size'] == 'small'),
                        min(record['radius'] for record in formations.values() if record['size'] == 'large'))
        outside = set(self.board.nodes)-set(self.board.node_formations)
        self.assertTrue(outside)
        self.assertTrue(all(self.board.nodes[identifier]['kind'] == 'blank' for identifier in outside))
        curved = straight = 0
        for edge in self.board.edges:
            source = self.board.node_formations.get(edge['from'])
            target = self.board.node_formations.get(edge['to'])
            internal = source is not None and source == target
            with self.subTest(edge=(edge['from'], edge['to'])):
                self.assertEqual('curve' in edge, internal)
                if internal:
                    start, end = (self.board.nodes[edge[key]]['position'] for key in ('from', 'to'))
                    control = edge['curve']
                    self.assertNotEqual((control[0]-start[0])*(end[1]-start[1])-
                                        (control[1]-start[1])*(end[0]-start[0]), 0,
                                        'An internal quadratic must visibly bend off its chord.')
            curved += internal;straight += not internal
        self.assertGreater(curved, straight)
        self.assertGreater(straight, 0)

    def test_centers_have_an_entry_and_a_distinct_onward_route_without_retracing(self):
        for identifier, formation in self.board.formations.items():
            with self.subTest(formation=identifier):
                members = set(formation['nodes'])
                adjacency = {node: [other for other, _ in self.board.adjacency[node] if other in members]
                             for node in members}
                center, entry, exit_node = (formation[key] for key in ('center_node', 'entry', 'exit'))
                self.assertGreaterEqual(len(adjacency[center]), 2)

                def onward(visited):
                    queue = deque([[center]])
                    seen = {center}
                    while queue:
                        route = queue.popleft()
                        if route[-1] == exit_node:return route
                        for other in adjacency[route[-1]]:
                            if other not in visited and other not in seen:
                                seen.add(other);queue.append(route+[other])
                    return None

                def approach(route):
                    node = route[-1]
                    if node == center:
                        tail = onward(set(route[:-1]))
                        return route+tail[1:] if tail else None
                    for other in adjacency[node]:
                        if other not in route and other != exit_node:
                            result = approach(route+[other])
                            if result:return result
                    return None

                route = approach([entry])
                self.assertIsNotNone(route, 'The central reward must not require returning along its approach.')
                self.assertEqual(route[0], entry);self.assertEqual(route[-1], exit_node)
                self.assertEqual(len(route), len(set(route)))
                self.assertIn(center, route)

    def test_every_benefit_can_be_earned_and_the_completed_values_match_the_design(self):
        self.assertTrue(self.lattice.award_rewards('full_section', {'caelan': MAX_RP}))
        for identifier, node in self.board.nodes.items():
            self.assertTrue(self.lattice.move(identifier) or self.lattice.state()['position'] == identifier,
                            identifier)
            if node['kind'] != 'blank':self.assertTrue(self.lattice.activate(identifier), identifier)
        self.assertEqual(len(self.lattice.state()['visited']), 200)
        self.assertEqual(len(self.lattice.state()['activated']), 150)
        self.assertEqual(self.lattice.bonuses(), GAINS)
        attributes = CharacterAttributes()
        self.assertTrue(attributes.set_modifiers('lattice', self.lattice.bonuses()))
        self.assertEqual({key: attributes.value(key) for key in FINAL}, FINAL)
        self.assertEqual((attributes.current_hp, attributes.current_mp), (140, 30))
        self.assertEqual(len(self.lattice.learned_abilities()), 21)
        restored = AetherLattice()
        self.assertTrue(restored.restore(self.lattice.to_dict()))
        self.assertEqual(restored.to_dict(), self.lattice.to_dict())

    def test_shortest_routes_through_centers_continue_without_retracing(self):
        self.assertTrue(self.lattice.award_rewards('center_routes', {'caelan': MAX_RP}))
        for identifier, formation in self.board.formations.items():
            with self.subTest(formation=identifier):
                entry, center, exit_node = (formation[key] for key in ('entry', 'center_node', 'exit'))
                self.assertTrue(self.lattice.move(entry) or self.lattice.state()['position'] == entry)
                approach = self.lattice.route(center)
                self.assertIsNotNone(approach)
                self.assertTrue(self.lattice.move(center))
                onward = self.lattice.route(exit_node)
                self.assertIsNotNone(onward)
                route = approach+onward[1:]
                self.assertLessEqual(set(route), set(formation['nodes']))
                edges = [frozenset((left, right)) for left, right in zip(route, route[1:])]
                self.assertEqual(len(edges), len(set(edges)),
                                 f'The selected center route must not retrace its approach: {route}')
                self.assertEqual(len(route), len(set(route)),
                                 f'The selected center route must continue through distinct nodes: {route}')

    def test_curved_and_straight_connections_each_cost_one_lattice_step(self):
        self.assertTrue(self.lattice.award_rewards('travel', {'caelan': MAX_RP}))
        for curved in (True, False):
            edge = next(edge for edge in self.board.edges if ('curve' in edge) == curved)
            self.assertTrue(self.lattice.move(edge['from']) or self.lattice.state()['position'] == edge['from'])
            before = self.lattice.steps()
            self.assertTrue(self.lattice.move(edge['to']))
            self.assertEqual(self.lattice.steps(), before-1)

    def test_paths_do_not_cross_unrelated_paths_or_run_through_unconnected_nodes(self):
        paths = [(_points(self.board, edge), edge) for edge in self.board.edges]
        boxes = [_bounds(points) for points, _ in paths]
        for index, (points, edge) in enumerate(paths):
            left, top, right, bottom = boxes[index]
            ends = {edge['from'], edge['to']}
            for other_points, other in paths[index+1:]:
                if ends & {other['from'], other['to']}:continue
                a, b, c, d = _bounds(other_points)
                if right < a or c < left or bottom < b or d < top:continue
                crossing = any(_intersect(start, end, other_start, other_end)
                               for start, end in zip(points, points[1:])
                               for other_start, other_end in zip(other_points, other_points[1:]))
                self.assertFalse(crossing, f"Unmarked crossing: {edge['from']}–{edge['to']} and "
                                          f"{other['from']}–{other['to']}")
            for identifier, node in self.board.nodes.items():
                if identifier in ends:continue
                x, y = node['position']
                if not left-12 <= x <= right+12 or not top-12 <= y <= bottom+12:continue
                distance = min(_distance_squared((x, y), start, end)
                               for start, end in zip(points, points[1:]))
                self.assertGreater(distance, 12**2,
                                   f"{edge['from']}–{edge['to']} passes through unrelated node {identifier}")


if __name__ == '__main__':unittest.main()
