"""Authored reward tiers follow Caelan's actual gated progression paths."""
from collections import Counter, deque
import heapq
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COUNTS = {'hp': 20, 'mp': 17, 'str': 14, 'mag': 19, 'spr': 12,
          'def': 14, 'm_def': 12, 'speed': 8, 'acc': 6, 'eva': 4, 'lck': 4}
TIERS = {'hp': (100, 200, 300, 400), 'mp': (5, 10, 20, 30)}
CRYSTALS = {'hp': 'aether_emerald', 'mp': 'aether_sapphire',
            'str': 'aether_ruby', 'def': 'aether_ruby',
            'mag': 'aether_amethyst', 'm_def': 'aether_amethyst',
            'spr': 'aether_opal', 'speed': 'aether_topaz',
            'acc': 'aether_topaz', 'eva': 'aether_topaz', 'lck': 'aether_topaz'}
LABELS = {'hp': 'HP', 'mp': 'MP', 'str': 'Str', 'mag': 'Mag', 'spr': 'Spr',
          'def': 'Def', 'm_def': 'M. Def', 'speed': 'Speed',
          'acc': 'Acc', 'eva': 'Eva', 'lck': 'Lck'}


def adjacency(data):
    result = {identifier: [] for identifier in data['nodes']}
    for edge in data['edges']:
        result[edge['from']].append((edge['to'], edge['min_rank']))
        result[edge['to']].append((edge['from'], edge['min_rank']))
    return result


def unlock_ranks(data, graph):
    start = data['starts']['caelan']
    result = {start: 1};queue = [(1, start)]
    while queue:
        rank, node = heapq.heappop(queue)
        if rank != result[node]:continue
        for other, gate in graph[node]:
            candidate = max(rank, gate)
            if candidate < result.get(other, float('inf')):
                result[other] = candidate
                heapq.heappush(queue, (candidate, other))
    return result


def distances(data, graph, rank):
    start = data['starts']['caelan']
    result = {start: 0};queue = deque([start])
    while queue:
        node = queue.popleft()
        for other, gate in graph[node]:
            if gate <= rank and other not in result:
                result[other] = result[node]+1
                queue.append(other)
    return result


def earliest_rank(data, graph, identifier):
    """Minimum rank with both an open route and enough banked travel Steps."""
    low, high = 1, max(edge['min_rank'] for edge in data['edges'])+len(graph)
    while low < high:
        rank = (low+high)//2
        cost = distances(data, graph, rank).get(identifier, float('inf'))
        if cost <= rank-1:high = rank
        else:low = rank+1
    return low


class LatticeTierDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT/'assets/progression/aether_lattice.json').read_text())
        cls.legacy = json.loads((ROOT/'assets/progression/aether_lattice_v2.json').read_text())
        cls.nodes = cls.data['nodes']
        cls.stats = {key: node for key, node in cls.nodes.items() if node['kind'] == 'stat'}
        cls.graph = adjacency(cls.data)
        cls.unlocks = unlock_ranks(cls.data, cls.graph)
        cls.ranks = {key: earliest_rank(cls.data, cls.graph, key) for key in cls.stats}

    def test_node_population_changes_only_ten_hp_nodes_into_mp_and_mag(self):
        self.assertEqual(self.data['version'], 3)
        self.assertEqual(Counter(node['kind'] for node in self.nodes.values()),
                         {'stat': 130, 'ability': 20, 'blank': 50})
        self.assertEqual(Counter(node['stat'] for node in self.stats.values()), COUNTS)
        changed = [(identifier, before, self.nodes[identifier])
                   for identifier, before in self.legacy['nodes'].items()
                   if before.get('stat') != self.nodes[identifier].get('stat')]
        self.assertEqual(len(changed), 10)
        self.assertTrue(all(before.get('stat') == 'hp' and after['kind'] == 'stat'
                            for _, before, after in changed))
        self.assertEqual(Counter(after['stat'] for _, _, after in changed),
                         {'mp': 5, 'mag': 5})

    def test_every_reward_uses_an_allowed_tier_and_matching_crystal(self):
        for identifier, node in self.stats.items():
            with self.subTest(node=identifier):
                self.assertIn(node['amount'], TIERS.get(node['stat'], (1, 2, 3, 4)))
                self.assertEqual(node['cost'], {CRYSTALS[node['stat']]: 1})
                self.assertEqual(node['name'], LABELS[node['stat']]+' +'+str(node['amount']))
                self.assertIn('by '+str(node['amount'])+'.', node['description'])
                if node['stat'] in ('hp', 'mp'):
                    self.assertIn('Current '+LABELS[node['stat']]+' is unchanged.',
                                  node['description'])
        for stat in ('hp', 'mp'):
            self.assertEqual({node['amount'] for node in self.stats.values()
                              if node['stat'] == stat}, set(TIERS[stat]))
        self.assertEqual({node['amount'] for node in self.stats.values()
                          if node['stat'] not in TIERS}, {1, 2, 3, 4})

    def test_rebalancing_preserves_every_position_route_and_non_stat_reward(self):
        self.assertEqual(set(self.nodes), set(self.legacy['nodes']))
        self.assertEqual({key: node['position'] for key, node in self.nodes.items()},
                         {key: node['position'] for key, node in self.legacy['nodes'].items()})
        for key in ('id', 'starts', 'starting_abilities', 'rank_curve', 'edges', 'formations'):
            self.assertEqual(self.data[key], self.legacy[key], key)
        for identifier, original in self.legacy['nodes'].items():
            if original['kind'] != 'stat':self.assertEqual(self.nodes[identifier], original)

    def test_opening_path_starts_with_small_rewards_before_landmark_growth(self):
        self.assertEqual((self.nodes['hp_01']['stat'], self.nodes['hp_01']['amount']), ('hp', 100))
        self.assertEqual((self.nodes['mp_01']['stat'], self.nodes['mp_01']['amount']), ('mp', 5))
        self.assertEqual((self.nodes['str_01']['stat'], self.nodes['str_01']['amount']), ('str', 1))
        self.assertEqual(self.ranks['hp_01'], 2)
        self.assertGreaterEqual(self.ranks['hp_03'], 9)
        self.assertEqual(self.data['formations']['quiet_reserve']['center_node'], 'hp_03')
        self.assertIn(self.nodes['hp_03']['amount'], (300, 400))

    def test_maximum_rewards_are_rare_and_usually_centers_or_late_progression(self):
        centers = {formation['center_node'] for formation in self.data['formations'].values()}
        maximum = [key for key, node in self.stats.items()
                   if node['amount'] == TIERS.get(node['stat'], (1, 2, 3, 4))[-1]]
        self.assertGreater(len(maximum), 0)
        self.assertLessEqual(len(maximum), len(self.stats)//10)
        preferred = [key for key in maximum if key in centers or self.ranks[key] >= 65]
        self.assertGreaterEqual(len(preferred)*5, len(maximum)*4)
        self.assertLessEqual(len(maximum)-len(preferred), 2)
        self.assertTrue(all(self.ranks[key] > 2 for key in maximum))

    def test_typical_reward_tiers_rise_with_real_access_and_step_requirements(self):
        bands = {'early': [], 'middle': [], 'late': []}
        for identifier, node in self.stats.items():
            tier = TIERS.get(node['stat'], (1, 2, 3, 4)).index(node['amount'])+1
            rank = self.ranks[identifier]
            bands['early' if rank <= 12 else 'middle' if rank < 65 else 'late'].append(tier)
        averages = {band: sum(values)/len(values) for band, values in bands.items()}
        self.assertLess(averages['early'], averages['middle'])
        self.assertLess(averages['middle'], averages['late'])
        # The late reserve shortcut must not make rank-110 rewards count as early.
        late_members = self.data['formations']['steadfast_heart']['nodes']
        self.assertTrue(all(self.ranks[key] >= 110 for key in late_members if key in self.stats))

    def test_large_formations_keep_hp_mp_and_magical_growth_choices(self):
        for identifier, formation in self.data['formations'].items():
            if formation['size'] != 'large':continue
            types = {self.nodes[key]['stat'] for key in formation['nodes']
                     if self.nodes[key]['kind'] == 'stat'}
            with self.subTest(formation=identifier):
                self.assertLessEqual({'hp', 'mp', 'mag'}, types)

    def test_authoring_output_is_reproducible_without_rewriting_files(self):
        spec = importlib.util.spec_from_file_location(
            'caelan_tier_authoring_test', ROOT/'tools/build_caelan_lattice.py')
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        data, catalog = module.build()
        self.assertEqual(data, self.data)
        self.assertEqual(catalog, json.loads((ROOT/'assets/abilities/catalog.json').read_text()))


if __name__ == '__main__':unittest.main()
