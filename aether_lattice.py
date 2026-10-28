"""Authored Aether Lattice rules, independent of UI, inventory and combat.

Rank derives from lifetime Resonance Points. Movement spends banked Steps,
never rank. Activated-node IDs are the source of earned bonuses and abilities;
the gameplay coordinator owns crystal consumption and durable checkpoints.
"""
from collections import deque
from copy import deepcopy
import heapq
import json
from math import isqrt
from pathlib import Path
import re

from character_attributes import ATTRIBUTE_IDS, MAX_ATTRIBUTE_VALUE


ROOT = Path(__file__).resolve().parent
BOARD_PATH = ROOT/'assets/progression/aether_lattice.json'
LEGACY_BOARD_PATH = ROOT/'assets/progression/aether_lattice_v1.json'
ABILITY_PATH = ROOT/'assets/abilities/catalog.json'
MAX_RP = 999999999
MAX_RECEIPTS = 4096
MAX_NODES = 1024
_IDENTIFIER = re.compile(r'^[a-zA-Z0-9_.:/-]{1,128}$')


def _identifier(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _integer(value, minimum=0, maximum=MAX_RP):
    return type(value) is int and minimum <= value <= maximum


def _point(value):
    return (isinstance(value, list) and len(value) == 2
            and all(type(n) is int and abs(n) <= 100000 for n in value))


def _has_center_route(adjacency, center, entry, exit_node):
    """Two vertex-disjoint center paths join entry to exit without retracing."""
    residual = {}

    def connect(a, b, capacity):
        residual.setdefault(a, {})[b] = capacity
        residual.setdefault(b, {}).setdefault(a, 0)

    sink = ('sink',)
    for node, neighbors in adjacency.items():
        connect((node, 'in'), (node, 'out'), 2 if node == center else 1)
        for other in neighbors:connect((node, 'out'), (other, 'in'), 2)
    for node in (entry, exit_node):connect((node, 'out'), sink, 1)
    source = (center, 'out')
    for _ in range(2):
        queue = deque([source]);parents = {source: None}
        while queue and sink not in parents:
            node = queue.popleft()
            for other, capacity in residual[node].items():
                if capacity and other not in parents:
                    parents[other] = node;queue.append(other)
        if sink not in parents:return False
        node = sink
        while parents[node] is not None:
            previous = parents[node]
            residual[previous][node] -= 1;residual[node][previous] += 1
            node = previous
    return True


class LatticeBoard:
    """A validated, connected graph and its referenced crystal/ability metadata."""

    def __init__(self, data=None, abilities=None):
        if data is None:data = json.loads(BOARD_PATH.read_text(encoding='utf-8'))
        if abilities is None:abilities = json.loads(ABILITY_PATH.read_text(encoding='utf-8'))
        self.data = deepcopy(data)
        self.ability_catalog = deepcopy(abilities)
        self._validate()
        self.id = self.data['id']
        self.version = self.data['version']
        self.name = self.data['name']
        self.description = self.data['description']
        self.nodes = self.data['nodes']
        self.edges = self.data['edges']
        self.formations = self.data.get('formations', {})
        self.node_formations = {node: identifier for identifier, formation in self.formations.items()
                                for node in formation['nodes']}
        self.starts = self.data['starts']
        self.starting_abilities = self.data['starting_abilities']
        self.crystals = self.data['crystals']
        self.rank_curve = self.data['rank_curve']
        self.abilities = self.ability_catalog['abilities']
        self.adjacency = {identifier: [] for identifier in self.nodes}
        for edge in self.edges:
            self.adjacency[edge['from']].append((edge['to'], edge['min_rank']))
            self.adjacency[edge['to']].append((edge['from'], edge['min_rank']))

    def _validate(self):
        data = self.data
        required = {'version', 'id', 'name', 'description', 'rank_curve', 'starts',
                    'starting_abilities', 'crystals', 'nodes', 'edges'}
        if (not isinstance(data, dict) or not required <= set(data) or set(data)-required-{'formations'}
                or not _integer(data['version'], 1, 999999) or not _identifier(data['id'])
                or any(not isinstance(data[key], str) or not data[key].strip()
                       for key in ('name', 'description'))):
            raise ValueError('Invalid Aether Lattice board')
        curve = data['rank_curve']
        if (not isinstance(curve, dict) or set(curve) != {'first', 'increment'}
                or not _integer(curve['first'], 1, 1000000)
                or not _integer(curve['increment'], 0, 1000000)):
            raise ValueError('Invalid Attunement curve')
        abilities = self.ability_catalog
        if (not isinstance(abilities, dict) or set(abilities) != {'version', 'abilities'}
                or type(abilities['version']) is not int or abilities['version'] != 1
                or not isinstance(abilities['abilities'], dict) or not abilities['abilities']):
            raise ValueError('Invalid ability catalog')
        for identifier, record in abilities['abilities'].items():
            if (not _identifier(identifier) or not isinstance(record, dict)
                    or set(record) != {'name', 'description', 'kind'}
                    or record['kind'] not in ('capability', 'technique', 'spell')
                    or any(not isinstance(record[key], str) or not record[key].strip()
                           for key in ('name', 'description'))):
                raise ValueError('Invalid ability definition')
        crystals = data['crystals']
        if not isinstance(crystals, dict) or not crystals:
            raise ValueError('Missing Aether Crystals')
        for identifier, record in crystals.items():
            if (not _identifier(identifier) or not isinstance(record, dict)
                    or set(record) != {'name', 'color'}
                    or not isinstance(record['name'], str) or not record['name'].strip()
                    or not isinstance(record['color'], str)
                    or re.fullmatch(r'#[0-9a-fA-F]{6}', record['color']) is None):
                raise ValueError('Invalid Aether Crystal definition')
        nodes = data['nodes']
        if not isinstance(nodes, dict) or not 1 <= len(nodes) <= MAX_NODES:
            raise ValueError('Invalid lattice nodes')
        for identifier, node in nodes.items():
            if not _identifier(identifier) or not isinstance(node, dict):
                raise ValueError('Invalid lattice node')
            base_keys = {'kind', 'name', 'description', 'position', 'cost'}
            kind = node.get('kind')
            expected = base_keys | ({'stat', 'amount'} if kind == 'stat' else
                                    {'ability_id'} if kind == 'ability' else set())
            if (kind not in ('blank', 'stat', 'ability') or set(node) != expected
                    or any(not isinstance(node[key], str) or not node[key].strip()
                           for key in ('name', 'description'))
                    or not _point(node['position'])
                    or not isinstance(node['cost'], dict)):
                raise ValueError('Invalid lattice node fields')
            if kind == 'blank':
                if node['cost']:raise ValueError('Blank nodes cannot consume crystals')
            elif (not node['cost'] or any(key not in crystals or not _integer(value, 1, 999999)
                                         for key, value in node['cost'].items())):
                raise ValueError('Invalid crystal cost')
            if kind == 'stat' and (node['stat'] not in ATTRIBUTE_IDS
                                   or not _integer(node['amount'], 1, MAX_ATTRIBUTE_VALUE)):
                raise ValueError('Invalid lattice stat bonus')
            if kind == 'ability' and (not isinstance(node['ability_id'], str)
                                      or node['ability_id'] not in abilities['abilities']):
                raise ValueError('Unknown lattice ability')
        if len({tuple(node['position']) for node in nodes.values()}) != len(nodes):
            raise ValueError('Overlapping lattice nodes')
        starts = data['starts']
        initial = data['starting_abilities']
        if (not isinstance(starts, dict) or not starts
                or any(not _identifier(key) or not isinstance(value, str) or value not in nodes
                       for key, value in starts.items())
                or not isinstance(initial, dict) or set(initial) != set(starts)):
            raise ValueError('Invalid character lattice starts')
        for known in initial.values():
            if (not isinstance(known, list)
                    or any(not isinstance(key, str) or key not in abilities['abilities'] for key in known)
                    or len(known) != len(set(known))):
                raise ValueError('Invalid starting abilities')
        edges = data['edges']
        if not isinstance(edges, list) or len(edges) > MAX_NODES*4:
            raise ValueError('Invalid lattice connections')
        pairs = set();adjacency = {key: set() for key in nodes}
        for edge in edges:
            if (not isinstance(edge, dict) or set(edge) not in
                    ({'from', 'to', 'min_rank'}, {'from', 'to', 'min_rank', 'curve'})
                    or not isinstance(edge['from'], str) or edge['from'] not in nodes
                    or not isinstance(edge['to'], str) or edge['to'] not in nodes
                    or edge['from'] == edge['to'] or not _integer(edge['min_rank'], 1, 999999)
                    or ('curve' in edge and not _point(edge['curve']))):
                raise ValueError('Invalid lattice connection')
            pair = frozenset((edge['from'], edge['to']))
            if pair in pairs:raise ValueError('Duplicate lattice connection')
            pairs.add(pair)
            adjacency[edge['from']].add(edge['to']);adjacency[edge['to']].add(edge['from'])
        reached = {next(iter(nodes))};queue = deque(reached)
        while queue:
            for other in adjacency[queue.popleft()]-reached:
                reached.add(other);queue.append(other)
        if reached != set(nodes):raise ValueError('Unreachable lattice content')
        self._validate_formations(adjacency)

    def _validate_formations(self, adjacency):
        if 'formations' not in self.data:
            if any('curve' in edge for edge in self.data['edges']):
                raise ValueError('Curved paths require formation metadata')
            return
        formations = self.data['formations']
        if not isinstance(formations, dict) or not formations or len(formations) > MAX_NODES:
            raise ValueError('Invalid lattice formations')
        membership = {}
        fields = {'name', 'center', 'radius', 'size', 'nodes', 'center_node', 'entry', 'exit'}
        for identifier, formation in formations.items():
            if (not _identifier(identifier) or not isinstance(formation, dict) or set(formation) != fields
                    or not isinstance(formation['name'], str) or not formation['name'].strip()
                    or not _point(formation['center']) or not _integer(formation['radius'], 1, 100000)
                    or formation['size'] not in ('large', 'small')
                    or not isinstance(formation['nodes'], list) or not 3 <= len(formation['nodes']) <= MAX_NODES
                    or any(not isinstance(node, str) or node not in self.data['nodes'] for node in formation['nodes'])
                    or len(formation['nodes']) != len(set(formation['nodes']))):
                raise ValueError('Invalid lattice formation fields')
            members = set(formation['nodes'])
            endpoints = (formation['center_node'], formation['entry'], formation['exit'])
            if (any(not isinstance(node, str) or node not in members for node in endpoints)
                    or len(set(endpoints)) != 3 or members & set(membership)
                    or self.data['nodes'][formation['center_node']]['position'] != formation['center']):
                raise ValueError('Invalid lattice formation membership')
            cx, cy = formation['center'];radius = formation['radius']+1
            if any((self.data['nodes'][node]['position'][0]-cx)**2
                   +(self.data['nodes'][node]['position'][1]-cy)**2 > radius*radius for node in members):
                raise ValueError('Formation node lies outside its bounds')
            inner = {node: adjacency[node] & members for node in members}
            reached = {formation['entry']};queue = deque(reached)
            while queue:
                for other in inner[queue.popleft()]-reached:
                    reached.add(other);queue.append(other)
            if (reached != members or not _has_center_route(inner, formation['center_node'],
                                                          formation['entry'], formation['exit'])):
                raise ValueError('Formation center needs a continuing entry-to-exit route')
            membership.update(dict.fromkeys(members, identifier))
        for edge in self.data['edges']:
            group = membership.get(edge['from'])
            internal = group is not None and group == membership.get(edge['to'])
            if internal != ('curve' in edge):
                raise ValueError('Formation paths curve; external paths must be straight')

    def rank_for_rp(self, rp):
        if not _integer(rp):raise ValueError('Invalid Resonance Points')
        first, increment = self.rank_curve['first'], self.rank_curve['increment']
        if not increment:return 1+rp//first
        linear = 2*first-increment
        levels = (isqrt(linear*linear+8*increment*rp)-linear)//(2*increment)
        return 1+levels

    def rp_for_rank(self, rank):
        if not _integer(rank, 1, MAX_RP+2):raise ValueError('Invalid Attunement Rank')
        levels = rank-1
        return levels*self.rank_curve['first']+self.rank_curve['increment']*levels*(levels-1)//2

    def edge_rank(self, start, end):
        return next((rank for other, rank in self.adjacency.get(start, ()) if other == end), None)


class AetherLattice:
    """Independent character ledgers on one shared authored lattice."""

    def __init__(self, board=None, starts=None):
        self.board = board if board is not None else LatticeBoard()
        if not isinstance(self.board, LatticeBoard):raise ValueError('Invalid lattice board')
        self.starts = deepcopy(self.board.starts if starts is None else starts)
        if (not isinstance(self.starts, dict) or not self.starts
                or any(not _identifier(key) or not isinstance(value, str) or value not in self.board.nodes
                       for key, value in self.starts.items())):
            raise ValueError('Invalid lattice character starts')
        self.character_ids = tuple(self.starts)
        self.reset()

    def reset(self):
        self._characters = {identifier: {'rp': 0, 'spent_steps': 0, 'position': node,
                                        'visited': {node}, 'activated': set()}
                            for identifier, node in self.starts.items()}
        self._receipts = set()

    def state(self, character_id='caelan'):
        state = self._characters[character_id]
        return {**state, 'visited': sorted(state['visited']), 'activated': sorted(state['activated'])}

    def rank(self, character_id='caelan'):
        return self.board.rank_for_rp(self._characters[character_id]['rp'])

    def steps(self, character_id='caelan'):
        return self.rank(character_id)-1-self._characters[character_id]['spent_steps']

    def rp_progress(self, character_id='caelan'):
        rank = self.rank(character_id)
        threshold = self.board.rp_for_rank(rank)
        return (self._characters[character_id]['rp']-threshold,
                self.board.rp_for_rank(rank+1)-threshold)

    def _route(self, start, target, rank):
        if (not isinstance(start, str) or not isinstance(target, str)
                or start not in self.board.nodes or target not in self.board.nodes):return None
        queue = deque([start]);parents = {start: None}
        while queue:
            node = queue.popleft()
            if node == target:
                route = []
                while node is not None:route.append(node);node = parents[node]
                return list(reversed(route))
            for other, required in self.board.adjacency[node]:
                if other not in parents and (rank is None or required <= rank):
                    parents[other] = node;queue.append(other)
        return None

    def route(self, target, character_id='caelan'):
        if not isinstance(character_id, str) or character_id not in self._characters:return None
        return self._route(self._characters[character_id]['position'], target, self.rank(character_id))

    def required_rank(self, target, character_id='caelan'):
        if (not isinstance(character_id, str) or character_id not in self._characters or not isinstance(target, str)
                or target not in self.board.nodes):return None
        start = self._characters[character_id]['position']
        best = {start: 1};queue = [(1, start)]
        while queue:
            requirement, node = heapq.heappop(queue)
            if node == target:return requirement
            if requirement != best[node]:continue
            for other, gate in self.board.adjacency[node]:
                candidate = max(requirement, gate)
                if candidate < best.get(other, MAX_RP+1):
                    best[other] = candidate;heapq.heappush(queue, (candidate, other))
        return None

    def move_reason(self, target, character_id='caelan'):
        if not isinstance(character_id, str) or character_id not in self._characters:return 'Unknown character.'
        if not isinstance(target, str) or target not in self.board.nodes:return 'Unknown node.'
        if target == self._characters[character_id]['position']:return 'Already standing on this node.'
        route = self.route(target, character_id)
        if route is None:
            return 'Requires Attunement '+str(self.required_rank(target, character_id))+'.'
        cost = len(route)-1
        if cost > self.steps(character_id):return f'Requires {cost} Lattice Steps; {self.steps(character_id)} available.'
        return ''

    def move(self, target, character_id='caelan'):
        if self.move_reason(target, character_id):return False
        route = self.route(target, character_id)
        state = self._characters[character_id]
        state['spent_steps'] += len(route)-1
        state['position'] = target
        state['visited'].update(route)
        return True

    def activation_reason(self, target, character_id='caelan'):
        if not isinstance(character_id, str) or character_id not in self._characters:return 'Unknown character.'
        if not isinstance(target, str) or target not in self.board.nodes:return 'Unknown node.'
        node = self.board.nodes[target];state = self._characters[character_id]
        if node['kind'] == 'blank':return 'Blank nodes have no bonus.'
        if target in state['activated']:return 'Already activated.'
        if target != state['position']:return 'Move to this node to activate it.'
        return ''

    def activate(self, target, character_id='caelan'):
        if self.activation_reason(target, character_id):return False
        self._characters[character_id]['activated'].add(target)
        return True

    def bonuses(self, character_id='caelan'):
        result = dict.fromkeys(ATTRIBUTE_IDS, 0)
        for identifier in self._characters[character_id]['activated']:
            node = self.board.nodes[identifier]
            if node['kind'] == 'stat':result[node['stat']] += node['amount']
        return result

    def learned_abilities(self, character_id='caelan'):
        known = set(self.board.starting_abilities.get(character_id, ()))
        for identifier in self._characters[character_id]['activated']:
            node = self.board.nodes[identifier]
            if node['kind'] == 'ability':known.add(node['ability_id'])
        return sorted(known)

    def has_receipt(self, receipt_id):
        return isinstance(receipt_id, str) and receipt_id in self._receipts

    def award_rewards(self, receipt_id, awards):
        if (not _identifier(receipt_id) or receipt_id in self._receipts
                or len(self._receipts) >= MAX_RECEIPTS or not isinstance(awards, dict)
                or any(not isinstance(key, str) or key not in self._characters
                       or not _integer(value) or self._characters[key]['rp']+value > MAX_RP
                       for key, value in awards.items())):
            return False
        for key, value in awards.items():self._characters[key]['rp'] += value
        self._receipts.add(receipt_id)
        return True

    def to_dict(self):
        return {'version': 1, 'board_id': self.board.id, 'board_version': self.board.version,
                'characters': {key: self.state(key) for key in sorted(self._characters)},
                'receipts': sorted(self._receipts)}

    def _normalized_snapshot(self, data):
        """Validate the archived rules before upgrading a known old ledger."""
        if (not isinstance(data, dict) or self.board.id != 'caelan_starter' or self.board.version != 2
                or data.get('board_id') != self.board.id or type(data.get('board_version')) is not int
                or data['board_version'] != 1):
            return data
        try:
            legacy = LatticeBoard(json.loads(LEGACY_BOARD_PATH.read_text(encoding='utf-8')),
                                  self.board.ability_catalog)
            if (legacy.id != self.board.id or legacy.version != 1
                    or legacy.rank_curve != self.board.rank_curve
                    or legacy.starts != self.board.starts or self.starts != legacy.starts
                    or legacy.starting_abilities != self.board.starting_abilities):
                return None
            # Cosmetic layout changes and new routes may not rewrite an earned
            # bonus, crystal payment or old gated connection during migration.
            for identifier, node in legacy.nodes.items():
                current = self.board.nodes.get(identifier)
                if current is None or any(current.get(key) != value for key, value in node.items()
                                          if key not in ('position', 'name', 'description')):
                    return None
            if any(self.board.edge_rank(edge['from'], edge['to']) != edge['min_rank']
                   for edge in legacy.edges):
                return None
            if not AetherLattice(legacy, self.starts)._valid_current_snapshot(data):return None
        except (OSError, ValueError, TypeError):
            return None
        normalized = deepcopy(data)
        normalized['board_version'] = self.board.version
        return normalized

    def _valid_snapshot(self, data):
        return self._valid_current_snapshot(self._normalized_snapshot(data))

    def _valid_current_snapshot(self, data):
        if (not isinstance(data, dict)
                or set(data) != {'version', 'board_id', 'board_version', 'characters', 'receipts'}
                or type(data['version']) is not int or data['version'] != 1
                or data['board_id'] != self.board.id
                or type(data['board_version']) is not int or data['board_version'] != self.board.version
                or not isinstance(data['characters'], dict) or set(data['characters']) != set(self.starts)
                or not isinstance(data['receipts'], list) or len(data['receipts']) > MAX_RECEIPTS
                or any(not _identifier(key) for key in data['receipts'])
                or len(data['receipts']) != len(set(data['receipts']))):
            return False
        for identifier, state in data['characters'].items():
            if (not isinstance(state, dict)
                    or set(state) != {'rp', 'spent_steps', 'position', 'visited', 'activated'}
                    or not _integer(state['rp']) or not _integer(state['spent_steps'])
                    or not isinstance(state['position'], str) or state['position'] not in self.board.nodes
                    or any(not isinstance(state[key], list) or len(state[key]) > len(self.board.nodes)
                           or any(not isinstance(node, str) or node not in self.board.nodes for node in state[key])
                           or len(state[key]) != len(set(state[key])) for key in ('visited', 'activated'))):
                return False
            rank = self.board.rank_for_rp(state['rp'])
            visited, activated = set(state['visited']), set(state['activated'])
            if (state['spent_steps'] > rank-1 or len(visited) > state['spent_steps']+1
                    or self.starts[identifier] not in visited or state['position'] not in visited
                    or not activated <= visited
                    or any(self.board.nodes[node]['kind'] == 'blank' for node in activated)):
                return False
            start = self.starts[identifier]
            reached = {start};distances = {start: 0};queue = deque(reached);bipartite = True
            while queue:
                node = queue.popleft()
                for other, required in self.board.adjacency[node]:
                    if other not in visited or required > rank:continue
                    if other not in reached:
                        reached.add(other);distances[other] = distances[node]+1;queue.append(other)
                    elif (distances[node]-distances[other]) % 2 == 0:bipartite = False
            if reached != visited:return False
            distance = distances[state['position']]
            if (state['spent_steps'] < distance
                    or (state['position'] == start and len(visited) > 1
                        and state['spent_steps'] < len(visited))
                    or (bipartite and (state['spent_steps']-distance) % 2)):
                return False
            edges = sum(1 for node in visited for other, required in self.board.adjacency[node]
                        if other in visited and required <= rank)//2
            if edges == len(visited)-1:
                # In a tree every visited branch must be retraced except the
                # path where the character currently stands. Repeated moves
                # add pairs of traversals; spending cannot invent a return.
                minimum = 2*edges-distance
                if state['spent_steps'] < minimum or (not edges and state['spent_steps']):
                    return False
        return True

    @classmethod
    def valid_snapshot(cls, data, board=None, starts=None):
        return cls(board, starts)._valid_snapshot(data)

    def restore(self, data):
        data = self._normalized_snapshot(data)
        if not self._valid_current_snapshot(data):return False
        self._characters = {key: {**deepcopy(value), 'visited': set(value['visited']),
                                  'activated': set(value['activated'])}
                            for key, value in data['characters'].items()}
        self._receipts = set(data['receipts'])
        return True
