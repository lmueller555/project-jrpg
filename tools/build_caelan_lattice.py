"""Build Caelan's authored circular Aether Lattice from its preserved v1 seed.

The output is committed game data, not a runtime random layout. Node identities,
positions and connections remain stable. Version-three bonuses are authored
explicitly below; saved grants migrate through their archived rule versions.
"""
from __future__ import annotations

from collections import Counter, deque
from copy import deepcopy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT/'assets/progression/aether_lattice_v1.json'
OUTPUT = ROOT/'assets/progression/aether_lattice.json'
ABILITIES = ROOT/'assets/abilities/catalog.json'

# These original pool sizes reproduce version two's node identities and layout.
# Conversions happen after geometry is built, without reallocating any positions.
LAYOUT_COUNTS = {
    'hp': 30, 'mp': 12, 'str': 14, 'mag': 14, 'spr': 12, 'def': 14,
    'm_def': 12, 'speed': 8, 'acc': 6, 'eva': 4, 'lck': 4,
}
CONVERSIONS = {
    'mp': ('hp_05', 'hp_10', 'hp_16', 'hp_24', 'hp_28'),
    'mag': ('hp_07', 'hp_12', 'hp_13', 'hp_20', 'hp_26'),
}
# Stable IDs describe ownership, not necessarily the node's current stat. Each
# list is an intentional placement, not a random distribution or suffix rule.
# The route audit considers both gate rank and Steps from the origin. In
# particular, the rank-110 return shortcut must never make late nodes look early.
# Rank 1–24 is mostly tier one, 25–64 mostly tier two, and 65+ mostly tier three.
# Nine of 130 stat nodes use tier four: the early Quiet Reserve center and eight
# rewards behind rank-85/110 gates. Utility ratings deliberately stop at +3 here.
BONUS_PLAN = {
    'hp': {
        100: 'hp_01 hp_02 hp_04 hp_06'.split(),
        200: 'hp_08 hp_09 hp_11 hp_14 hp_15 hp_17 hp_19'.split(),
        300: 'hp_18 hp_21 hp_22 hp_23 hp_25 hp_27 hp_29'.split(),
        400: 'hp_03 hp_30'.split(),
    },
    'mp': {
        5: 'mp_01 mp_03'.split(),
        10: 'mp_02 mp_04 hp_05 mp_05 mp_06 mp_07 mp_09'.split(),
        20: 'hp_10 hp_16 mp_08 hp_24 mp_11 hp_28'.split(),
        30: 'mp_10 mp_12'.split(),
    },
    'str': {
        1: 'str_01 str_02 str_03'.split(),
        2: 'str_04 str_05 str_06 str_07'.split(),
        3: 'str_08 str_09 str_10 str_11 str_12 str_14'.split(),
        4: ['str_13'],
    },
    'mag': {
        1: 'mag_01 mag_02 mag_03'.split(),
        2: 'mag_04 hp_07 mag_05 mag_06 hp_12 mag_07'.split(),
        3: 'hp_13 mag_08 mag_09 mag_10 hp_20 mag_11 mag_12 hp_26 mag_14'.split(),
        4: ['mag_13'],
    },
    'spr': {
        1: 'spr_01 spr_02 spr_03'.split(),
        2: 'spr_04 spr_05 spr_06'.split(),
        3: 'spr_07 spr_08 spr_09 spr_10 spr_11'.split(),
        4: ['spr_12'],
    },
    'def': {
        1: 'def_01 def_02 def_03'.split(),
        2: 'def_04 def_05 def_06 def_07'.split(),
        3: 'def_08 def_09 def_10 def_11 def_12 def_13'.split(),
        4: ['def_14'],
    },
    'm_def': {
        1: 'm_def_01 m_def_02 m_def_03'.split(),
        2: 'm_def_04 m_def_05 m_def_06'.split(),
        3: 'm_def_07 m_def_08 m_def_09 m_def_10 m_def_11'.split(),
        4: ['m_def_12'],
    },
    'speed': {1: 'speed_01 speed_02'.split(),
              2: 'speed_03 speed_04 speed_05'.split(),
              3: 'speed_06 speed_07 speed_08'.split()},
    'acc': {1: 'acc_01 acc_02'.split(), 2: 'acc_03 acc_04'.split(),
            3: 'acc_05 acc_06'.split()},
    'eva': {1: ['eva_01'], 2: 'eva_02 eva_03'.split(), 3: ['eva_04']},
    'lck': {1: 'lck_01 lck_02'.split(), 2: ['lck_03'], 3: ['lck_04']},
}
BONUS_TIERS = {stat: (100, 200, 300, 400) if stat == 'hp' else
              (5, 10, 20, 30) if stat == 'mp' else (1, 2, 3, 4)
              for stat in LAYOUT_COUNTS}
LABELS = {'hp': 'HP', 'mp': 'MP', 'str': 'Str', 'mag': 'Mag', 'spr': 'Spr',
          'def': 'Def', 'm_def': 'M. Def', 'speed': 'Speed', 'acc': 'Acc',
          'eva': 'Eva', 'lck': 'Lck'}
NAMES = {'hp': 'maximum HP', 'mp': 'maximum MP', 'str': 'Strength',
         'mag': 'Magick', 'spr': 'Spirit', 'def': 'Defense',
         'm_def': 'Magick Defense', 'speed': 'Speed', 'acc': 'Accuracy',
         'eva': 'Evasion', 'lck': 'Luck'}
CRYSTALS = {'hp': 'aether_emerald', 'mp': 'aether_sapphire',
            'str': 'aether_ruby', 'def': 'aether_ruby',
            'mag': 'aether_amethyst', 'm_def': 'aether_amethyst',
            'spr': 'aether_opal', 'speed': 'aether_topaz',
            'acc': 'aether_topaz', 'eva': 'aether_topaz', 'lck': 'aether_topaz'}

# These are learned techniques/spells.  Combat execution is a separate system.
NEW_ABILITIES = {
    'focused_strike': ('Focused Strike', 'technique', 'A deliberate physical technique focused on one opponent.'),
    'sweeping_strike': ('Sweeping Strike', 'technique', 'A broad physical technique intended to reach nearby opponents.'),
    'guarded_strike': ('Guarded Strike', 'technique', 'A measured physical attack made from a guarded stance.'),
    'piercing_strike': ('Piercing Strike', 'technique', 'A precise physical technique for finding an opening in a sturdy defense.'),
    'rally': ('Rally', 'technique', 'A supportive technique for helping an ally regain their composure.'),
    'intercept': ('Intercept', 'technique', 'A protective technique for stepping into the path of an attack aimed at an ally.'),
    'riposte': ('Riposte', 'technique', 'A physical response made after meeting an attack with a guard.'),
    'aether_dart': ('Aether Dart', 'spell', 'A small, focused damaging spell whose power is governed by Magick.'),
    'aether_arc': ('Aether Arc', 'spell', 'An arcing damaging spell intended to reach several opponents; power is governed by Magick.'),
    'aether_lance': ('Aether Lance', 'spell', 'A concentrated damaging spell directed at one opponent; power is governed by Magick.'),
    'aether_burst': ('Aether Burst', 'spell', 'A broader release of damaging magicks whose power is governed by Magick.'),
    'greater_mend': ('Greater Mend', 'spell', 'A stronger restorative spell whose healing power is governed by Spirit.'),
    'renew': ('Renew', 'spell', 'A sustained restorative working whose healing power is governed by Spirit.'),
    'cleanse': ('Cleanse', 'spell', 'A restorative working intended to remove a harmful affliction.'),
    'ward': ('Ward', 'spell', 'A protective working intended to soften incoming magicks.'),
    'dispel': ('Dispel', 'spell', 'A controlled working for unraveling an existing magical effect.'),
    'channel': ('Channel', 'technique', 'A concentration technique for managing the effort of sustained casting.'),
    'steadfast': ('Steadfast', 'technique', 'A defensive technique for maintaining a steady position under pressure.'),
}


def apply_bonus_plan(data):
    """Apply the reviewed tier placements after stable geometry is constructed.

    The optional Gathered Light detour gains Mag alongside Aether Burst. Far
    Reach adds both MP and Mag beside Aether Lance. Shared Strength, Shelter
    and Steadfast Heart retain three HP nodes each, while the other broad
    formations retain two. Quiet Reserve's HP center is the single early
    maximum; every other maximum is gated at Attunement 85 or 110.
    """
    nodes = data['nodes']
    for stat, identifiers in CONVERSIONS.items():
        for identifier in identifiers:
            assert nodes[identifier]['stat'] == 'hp'
            nodes[identifier]['stat'] = stat
    assigned = set()
    for stat, tiers in BONUS_PLAN.items():
        for amount, identifiers in tiers.items():
            assert amount in BONUS_TIERS[stat]
            for identifier in identifiers:
                assert identifier not in assigned
                node = nodes[identifier]
                assert node['kind'] == 'stat' and node['stat'] == stat
                assigned.add(identifier)
                description = 'Increase '+NAMES[stat]+' by '+str(amount)+'.'
                if stat in ('hp', 'mp'):description += ' Current '+LABELS[stat]+' is unchanged.'
                node.update(name=LABELS[stat]+' +'+str(amount),
                            description=description, amount=amount,
                            cost={CRYSTALS[stat]: 1})
    assert assigned == {key for key, node in nodes.items() if node['kind'] == 'stat'}
    expected = dict(LAYOUT_COUNTS, hp=20, mp=17, mag=19)
    assert Counter(nodes[key]['stat'] for key in assigned) == expected


def build():
    seed = json.loads(SEED.read_text())
    data = deepcopy(seed)
    data['version'] = 3
    data['description'] = ('Caelan\'s connected circles combine broad formations, smaller loops and '
                           'straight connecting paths. Reach a center reward and continue onward.')
    nodes = data['nodes']
    edges = data['edges']
    original_pairs = {frozenset((edge['from'], edge['to'])): edge for edge in edges}
    edge_pairs = dict(original_pairs)
    formations, membership, circles = {}, {}, {}

    # Blank 08..33 live inside formations; 34..49 are straight-path waypoints.
    blank_ids = []
    for number in range(8, 50):
        identifier = 'blank_'+str(number).zfill(2)
        nodes[identifier] = {'kind': 'blank', 'name': 'Blank Node',
            'description': 'A connecting node with no bonus. Crossing one connection costs one Lattice Step.',
            'position': [0, 0], 'cost': {}}
        blank_ids.append(identifier)
    internal_blanks, outside_blanks = deque(blank_ids[:26]), deque(blank_ids[26:])

    # Reproduce the original pool ordering so the tier pass cannot move nodes
    # or alter circular membership, route lengths, gates or connections.
    stat_pool = []
    for order, (stat, count) in enumerate(LAYOUT_COUNTS.items()):
        existing = [node for node in seed['nodes'].values() if node['kind'] == 'stat' and node['stat'] == stat]
        rest = count-len(existing)
        for index in range(rest):
            amount = BONUS_TIERS[stat][0]
            identifier = stat+'_'+str(len(existing)+index+1).zfill(2)
            description = 'Increase '+NAMES[stat]+' by '+str(amount)+'.'
            if stat in ('hp', 'mp'):description += ' Current '+LABELS[stat]+' is unchanged.'
            nodes[identifier] = {'kind': 'stat', 'name': LABELS[stat]+' +'+str(amount),
                'description': description, 'position': [0, 0], 'cost': {CRYSTALS[stat]: 1},
                'stat': stat, 'amount': amount}
            stat_pool.append(((index+.5)/rest, order, identifier))
    stat_ids = deque(item[-1] for item in sorted(stat_pool))

    catalog = json.loads(ABILITIES.read_text())
    # Only canonical seed definitions and this authored set belong in output;
    # rerunning the builder must not accumulate retired experimental records.
    catalog['abilities'] = {key: catalog['abilities'][key] for key in ('basic_magicks', 'brace', 'mend')}
    for identifier, (name, kind, description) in NEW_ABILITIES.items():
        catalog['abilities'][identifier] = {'name': name, 'description': description, 'kind': kind}
        nodes[identifier+'_01'] = {'kind': 'ability', 'name': name,
            'description': 'Learn '+name+'.', 'position': [0, 0],
            'cost': {'aether_diamond': 1}, 'ability_id': identifier}

    def point(center, radius, angle):
        radians = math.radians(angle)
        return [round(center[0]+radius*math.cos(radians)),
                round(center[1]+radius*math.sin(radians))]

    def position(identifier, center, radius=0, angle=0):
        nodes[identifier]['position'] = point(center, radius, angle)
        if radius:circles[identifier] = (tuple(center), radius, angle)

    def edge(a, b, rank=1):
        pair = frozenset((a, b))
        if pair in edge_pairs:return
        record = {'from': a, 'to': b, 'min_rank': rank}
        edges.append(record);edge_pairs[pair] = record

    def ring(identifiers):
        for a, b in zip(identifiers, identifiers[1:]+identifiers[:1]):edge(a, b)

    def describe(identifier, name, center, radius, size, members, core, entry, exit):
        assert not any(node in membership for node in members)
        for node in members:membership[node] = identifier
        formations[identifier] = {'name': name, 'center': list(center), 'radius': radius,
            'size': size, 'nodes': members, 'center_node': core, 'entry': entry, 'exit': exit}

    # Main seed: outer twelve, inner nine, and Brace on a two-sided center chord.
    first_center = (36, 176)
    main = list(seed['nodes'])[:20]
    outer = main[:12]
    angle0 = -math.degrees(math.acos(-.2))
    angle1 = -math.degrees(math.acos(.2))
    outer_angles = [angle0]+[angle1+i*(360-(angle1-angle0))/11 for i in range(11)]
    for identifier, angle in zip(outer, outer_angles):position(identifier, first_center, 180, angle)
    extra_a, extra_b = internal_blanks.popleft(), internal_blanks.popleft()
    inner_at = [(main[12], 215), (main[13], 180), (main[15], 0), (main[16], 40),
                (main[17], 80), (main[18], 120), (main[19], 160), (extra_a, 250), (extra_b, 300)]
    for identifier, angle in inner_at:position(identifier, first_center, 95, angle)
    position('brace_01', first_center)
    ring(outer)
    ring([identifier for identifier, angle in sorted(inner_at, key=lambda item: item[1])])
    edge('mp_01', 'hp_02');edge('def_01', 'blank_04')
    describe('first_light', 'First Light', first_center, 180, 'large',
             main+[extra_a, extra_b], 'brace_01', 'origin', 'mp_01')

    # The old Mend branch becomes a complete small loop with a distinct exit.
    mend_center = (300, -135)
    mend_a, mend_b = internal_blanks.popleft(), internal_blanks.popleft()
    mend_ring = ['blank_05', 'def_02', 'spr_02', mend_a, mend_b]
    for identifier, angle in zip(mend_ring, (135, 205, 275, 345, 55)):
        position(identifier, mend_center, 100, angle)
    position('mend_01', mend_center)
    for a, b in zip(mend_ring, mend_ring[1:]):edge(a, b)
    edge('mend_01', mend_b)
    describe('gentle_current', 'Gentle Current', mend_center, 100, 'small',
             mend_ring+['mend_01'], 'mend_01', 'blank_05', mend_b)
    edge(mend_b, 'str_01', 5)

    # Its old north-branch counterpart preserves the rank-eight boundary too.
    reserve_center = (36, 696)
    reserve_ring = ['blank_06', 'mp_02', 'm_def_02', 'blank_07', 'lck_02']
    for identifier, angle in zip(reserve_ring, (270, 330, 30, 90, 210)):
        position(identifier, reserve_center, 100, angle)
    position('hp_03', reserve_center)
    for a, b in zip(reserve_ring, reserve_ring[1:]):edge(a, b)
    describe('quiet_reserve', 'Quiet Reserve', reserve_center, 100, 'small',
             reserve_ring+['hp_03'], 'hp_03', 'blank_06', 'lck_02')

    core_abilities = ['aether_dart', 'focused_strike', 'greater_mend', 'ward',
                      'aether_lance', 'steadfast', 'cleanse', 'aether_burst']
    reserved = {identifier+'_01' for identifier in core_abilities}
    ability_ids = deque(identifier+'_01' for identifier in NEW_ABILITIES if identifier+'_01' not in reserved)
    ordinary_core = internal_blanks.popleft()
    pools = {'stat': stat_ids, 'ability': ability_ids, 'blank': internal_blanks}
    used, lengths = Counter(), {key: len(value) for key, value in pools.items()}

    def next_node():
        kind = min((key for key, pool in pools.items() if pool),
                   key=lambda key: ((used[key]+.5)/lengths[key], key))
        used[kind] += 1
        return pools[kind].popleft()

    large_nodes = {'first_light': outer}

    def large(identifier, name, center, core, entry_index=0, exit_index=6):
        outer_ids = [next_node() for _ in range(12)]
        inner_ids = [next_node() for _ in range(9)]
        inner_angles = [0, 40, 80, 120, 160, 180, 220, 260, 300]
        for node, angle in zip(outer_ids, range(180, 540, 30)):position(node, center, 180, angle)
        for node, angle in zip(inner_ids, inner_angles):position(node, center, 95, angle)
        position(core, center);ring(outer_ids);ring(inner_ids)
        top_inner = 8 if identifier == 'shelter' else 7
        for outer_index, inner_index in ((0, 5), (3, top_inner), (6, 0), (9, 2)):
            edge(outer_ids[outer_index], inner_ids[inner_index])
        edge(inner_ids[5], core);edge(core, inner_ids[0])
        describe(identifier, name, center, 180, 'large', outer_ids+inner_ids+[core],
                 core, outer_ids[entry_index], outer_ids[exit_index])
        large_nodes[identifier] = outer_ids

    # Assignment order follows the main journey and interleaves the small loops.
    large('steady_hand', 'Steady Hand', (556, 176), 'aether_dart_01')

    def small(identifier, name, center, core,
              angles=(30, 100, 150, 220, 290), entry_index=2, exit_index=0):
        outer_ids = [next_node() for _ in range(5)]
        for node, angle in zip(outer_ids, angles):position(node, center, 90, angle)
        position(core, center);ring(outer_ids)
        edge(outer_ids[3], core);edge(core, outer_ids[0])
        describe(identifier, name, center, 90, 'small', outer_ids+[core], core,
                 outer_ids[entry_index], outer_ids[exit_index])
        return outer_ids

    small('clear_water', 'Clear Water', (556, -224), 'cleanse_01')
    large('clear_intent', 'Clear Intent', (1076, 176), 'focused_strike_01')
    small('gathered_light', 'Gathered Light', (1076, -224), 'aether_burst_01')
    large('shared_strength', 'Shared Strength', (1596, 176), 'greater_mend_01', 0, 9)
    small('crossing_paths', 'Crossing Paths', (1996, 176), ordinary_core,
          (30, 100, 150, 210, 290), 3, 1)
    large('shelter', 'Shelter', (1596, 696), 'ward_01', 3, 0)
    large('far_reach', 'Far Reach', (1076, 696), 'aether_lance_01', 6, 0)
    large('steadfast_heart', 'Steadfast Heart', (556, 696), 'steadfast_01', 6, 0)
    assert not any(pools.values()), {key: len(value) for key, value in pools.items()}

    def bridge(a, b, rank, waypoint_count):
        start, end = nodes[a]['position'], nodes[b]['position']
        chain = [a]
        for index in range(waypoint_count):
            node = outside_blanks.popleft();fraction = (index+1)/(waypoint_count+1)
            nodes[node]['position'] = [round(start[axis]+(end[axis]-start[axis])*fraction) for axis in (0, 1)]
            chain.append(node)
        chain.append(b)
        for first, second in zip(chain, chain[1:]):edge(first, second, rank)

    route = ['first_light', 'steady_hand', 'clear_intent', 'shared_strength',
             'shelter', 'far_reach', 'steadfast_heart']
    for first, second, rank in zip(route, route[1:], (12, 25, 45, 65, 85, 110)):
        bridge(formations[first]['exit'], formations[second]['entry'], rank, 2)
    # Small local loops enter and rejoin through different straight approaches.
    for parent, child, rank, indices in (('steady_hand', 'clear_water', 20, (2, 4)),
                                       ('clear_intent', 'gathered_light', 35, (2, 4)),
                                       ('shared_strength', 'crossing_paths', 55, (5, 7))):
        bridge(large_nodes[parent][indices[0]], formations[child]['entry'], rank, 1)
        edge(formations[child]['exit'], large_nodes[parent][indices[1]], rank)
    # A waypoint keeps the reserve's outward approach distinct from the
    # shortest inward journey, rather than offering an equal-cost detour back
    # through the previous formation while selecting its center.
    bridge('lck_02', 'mag_01', 8, 1)
    # The far end reconnects to the earlier reserve only after its late gate.
    edge(formations['steadfast_heart']['exit'], 'm_def_02', 110)
    assert not outside_blanks

    # Every internal connection is an authored quadratic curve.  Circular arcs
    # use a circle midpoint; radial/chord links get a restrained bow.  Bridges
    # and all exterior-waypoint segments remain exactly straight.
    for record in edges:
        a, b = record['from'], record['to']
        if membership.get(a) != membership.get(b) or a not in membership:continue
        pa, pb = nodes[a]['position'], nodes[b]['position']
        first, second = circles.get(a), circles.get(b)
        if first is not None and second is not None and first[:2] == second[:2]:
            center, radius, angle = first
            delta = (second[2]-angle+180) % 360-180
            midpoint = point(center, radius, angle+delta/2)
            control = [round(2*midpoint[axis]-(pa[axis]+pb[axis])/2) for axis in (0, 1)]
        else:
            dx, dy = pb[0]-pa[0], pb[1]-pa[1]
            length = math.hypot(dx, dy)
            bow = min(10, length*.08)
            control = [round((pa[0]+pb[0])/2-dy/length*bow),
                       round((pa[1]+pb[1])/2+dx/length*bow)]
        record['curve'] = control
    data['formations'] = formations

    assert len(nodes) == 200
    assert Counter(node['kind'] for node in nodes.values()) == {'stat': 130, 'ability': 20, 'blank': 50}
    assert len({tuple(node['position']) for node in nodes.values()}) == len(nodes)
    apply_bonus_plan(data)
    for identifier, original in seed['nodes'].items():
        current = nodes[identifier]
        assert current['kind'] == original['kind']
        assert current['cost'] == original['cost']
        if original['kind'] == 'ability':
            assert current['ability_id'] == original['ability_id']
    for original in seed['edges']:
        current = edge_pairs[frozenset((original['from'], original['to']))]
        assert all(current[key] == value for key, value in original.items())
    return data, catalog


def main():
    data, catalog = build()
    OUTPUT.write_text(json.dumps(data, indent=2)+'\n')
    ABILITIES.write_text(json.dumps(catalog, indent=2)+'\n')
    print('Built', len(data['nodes']), 'nodes,', len(data['formations']), 'formations and', len(data['edges']), 'connections.')
    return 0


if __name__ == '__main__':raise SystemExit(main())
