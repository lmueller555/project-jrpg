# Caelan's Aether Lattice section

Caelan's section contains **200 nodes**: 130 attribute nodes, 20 ability nodes
and 50 empty nodes. Empty nodes include the origin and the small connections
between formations. Every graph connection costs one Lattice Step, whether it
is drawn as a curve or a straight segment.

## Circular formations and connections

Large formations combine outer arcs, inner arcs and junctions. Smaller circular
formations sit along the route and on branches. A center may contain an ability,
a substantial attribute bonus or an ordinary node. Each center connects onward
through its formation, so reaching it does not require retracing the approach
to continue to the exit.

Connections within a formation use authored quadratic curves. Connections
between formations, and every connection involving a node outside them, use
straight lines. A curve changes the appearance of an edge, not its Step cost.
The gold route highlight and locked-path dashes follow the same geometry.

The lattice uses the full content width beneath the character header. The mouse
wheel controls 5–200% zoom, with smaller node markers at overview scales and
attribute icons at closer scales. Click a node to select it, drag to pan the
camera, or steer the gold cursor with the arrow keys. Releasing a drag or the
arrow keys selects the node nearest the cursor and smoothly centers it with a
pulsing halo. Inspection does not move the character or spend resources.

An affordable, reachable destination offers a contextual Step-cost preview and
Move button beside the selection. An eligible current node offers its effect,
crystal cost and Activate button when the required crystals are available.
These commands execute when clicked and disappear while navigating or reading
help. There is no permanent action panel or zoom toolbar. See the
[controls guide](AETHER_LATTICE.md#menu-controls) for all inputs.

## Growth budget

These totals assume every attribute node in this section is activated. Completed
values include Caelan's approved starting attributes and exclude equipment,
temporary effects and progression outside this section.

| Attribute | Nodes | Section gain | Completed value |
| --- | ---: | ---: | ---: |
| HP | 20 | +4,700 | 4,840 |
| MP | 17 | +260 | 290 |
| Str | 14 | +33 | 43 |
| Mag | 19 | +46 | 56 |
| Spr | 12 | +28 | 38 |
| Def | 14 | +33 | 43 |
| M. Def | 12 | +28 | 38 |
| Speed | 8 | +17 | 27 |
| Acc | 6 | +12 | 22 |
| Eva | 4 | +8 | 18 |
| Lck | 4 | +7 | 17 |
| **Attribute total** | **130** | | |

The section develops Caelan as an adaptable all-rounder, with more opportunities
to develop damaging magicks, useful healing and reliable defenses. Accuracy, Evasion
and Luck are ratings rather than percentages. Combat formulas and encounter
balance remain future work; these are section targets rather than game-wide caps.

These totals follow the authored rewards. Increasing maximum HP or MP does not refill
the current resource, and Attunement Rank grants movement rather than additional
hidden stats.

## Reward tiers and pacing

| Attribute | Allowed bonuses | Nodes at each tier, in that order |
| --- | --- | --- |
| HP | +100 / +200 / +300 / +400 | 4 / 7 / 7 / 2 |
| MP | +5 / +10 / +20 / +30 | 2 / 7 / 6 / 2 |
| Other attributes | +1 / +2 / +3 / +4 | Authored individually along the route |

Most early choices grant the first tier, with selected second-tier rewards on
branches. Middle formations emphasize the second tier and introduce the third;
late formations mostly grant the third tier. Placement considers both the
route's rank gates and the number of Steps needed to reach a node from the
origin. A late connection back to an early region does not turn its rewards into
early progression.

Only **nine of 130 attribute nodes (6.9%)** grant the maximum tier. Quiet Reserve's
central HP +400 node is the sole early exception, reachable at Attunement 9 with
eight saved Steps. The other eight maximum rewards require Attunement 85 or 110.
Not every attribute needs a +4 in this section; Speed, Acc, Eva and Lck top out at
+3 here, leaving room for later sections.

The ten former HP nodes retain their stable identities and positions. Five now
grant MP (`hp_05`, `hp_10`, `hp_16`, `hp_24`, `hp_28`) and five grant Mag
(`hp_07`, `hp_12`, `hp_13`, `hp_20`, `hp_26`). Their crystal families change to
Sapphire or Amethyst accordingly, at one crystal per activation. MP and Mag are
distributed beside spell opportunities: Gathered Light gains a Mag reward near
Aether Burst, and Far Reach offers both MP and Mag near Aether Lance. Every large
formation retains HP, MP and Mag choices. Shared Strength, Shelter and Steadfast
Heart retain three HP nodes each.

Exact placements are explicit in `BONUS_PLAN` in the authoring tool; rerunning
the builder does not randomize rewards or move their geometry.

## Abilities

Twenty nodes unlock techniques and spells, including Brace and Mend. Basic
Magicks remains a starting capability and does not consume one of those twenty
unlocks. The section includes physical techniques, damaging magicks, recovery
and protective utility.

The lattice records and displays learned abilities. Executing them, paying their
combat costs and resolving their effects belong to the future battle system.
Opening quest magicks retain their authored outcomes.

## Authored data and journey compatibility

[`assets/progression/aether_lattice.json`](../assets/progression/aether_lattice.json)
defines the version-three section. Formation records identify their member nodes,
center, entry and exit. Internal edge records include a `curve` control point;
straight edge records omit it.

The original 30-node version is archived in
[`assets/progression/aether_lattice_v1.json`](../assets/progression/aether_lattice_v1.json).
The complete pre-tier section is archived in
[`assets/progression/aether_lattice_v2.json`](../assets/progression/aether_lattice_v2.json).
This reward pass preserves version-two node identities, positions, connections,
gates and ability rewards.
Continue validates older records against their archived rules before upgrading.
Previously activated nodes retain their original paid rewards, even when their
unactivated counterparts now grant another attribute or a larger tier. Their
icons, crystal colors and earned-bonus metadata display that retained reward.
They cannot be activated again to collect the replacement reward.

New activations use the version-three tiers. Ledger schema version two
records which activations predate the rebalance; their bonuses come from the
canonical archive rather than duplicated numeric totals. RP, spent Steps,
visited nodes, current position, receipts, crystals, base attributes and current
HP/MP remain intact. Repeated Continue does not stack either generation's gains.
The growth table above describes a fresh journey; a migrated journey retains
the rewards it had already earned.

The deterministic authoring tool reproduces the current section:

```sh
python tools/build_caelan_lattice.py
```

To inspect the production menu using disposable journey and settings files:

```sh
python tools/preview_aether_lattice.py --rp 0 --crystals 0
```

## Proposed expansion — awaiting design review

The following is a proposal. The implemented board remains the 200-node section
documented above; no additional formations, rewards or abilities are enabled.

### Size and composition

| Content | Current | Add | Proposed |
| --- | ---: | ---: | ---: |
| Attribute nodes | 130 | 100 | 230 |
| Ability nodes | 20 | 15 | 35 |
| Empty nodes | 50 | 35 | 85 |
| **Total** | **200** | **150** | **350** |

Five new large formations of 22 nodes, four new small formations of six nodes,
and sixteen exterior waypoints supply the added 150. The complete layout would
have twelve large circles, nine small circles and 32 exterior nodes. Nineteen
of the added empty nodes sit inside circles; the other sixteen provide straight
connections. Most connecting stretches should contain only one or two empty
nodes, with rewards and branch decisions between longer journeys.

### Main route

Use three rows of four large formations, following a serpentine route. Working
names for new regions are marked with an asterisk; these names imply no new
story canon.

```text
First Light → Steady Hand → Rooted Steps* → Clear Intent
                                               ↓
Shelter ← Measured Force* ← Shared Strength ← Gathering Current*
   ↓
Open Horizon* → Far Reach → Steadfast Heart → Lasting Resolve*
```

First Light and Steady Hand keep Caelan's opening tools close together.
Rooted Steps adds physical reliability, defenses and capacity. Gathering Current
offers MP, Mag and Spr choices near spell development. Measured Force combines
physical offense, magicks and protection. Open Horizon emphasizes Speed,
Accuracy and broader options. Lasting Resolve becomes the final region with
several rare maximum rewards and a capstone candidate.

| Parent region | Small formations |
| --- | --- |
| First Light | Gentle Current; Quiet Reserve |
| Steady Hand | Clear Water |
| Rooted Steps | Sure Footing* |
| Clear Intent | Gathered Light |
| Gathering Current | Quiet Focus* |
| Shared Strength | Crossing Paths |
| Measured Force | Helping Hand* |
| Open Horizon | Inner Reserve* |

Each small branch leaves and rejoins its parent through different connections.
Routes through circular centers continue to separate exits without retracing.
Internal connections remain curved and exterior connections remain straight.
The final return route runs around the map perimeter. Its unlock condition must
prevent the existing Quiet Reserve shortcut from bypassing new late regions.

### Attribute choices and reward pacing

| Attribute | Current | Proposed |
| --- | ---: | ---: |
| HP | 20 | 34 |
| MP | 17 | 31 |
| Str | 14 | 25 |
| Mag | 19 | 33 |
| Spr | 12 | 22 |
| Def | 14 | 25 |
| M. Def | 12 | 22 |
| Speed | 8 | 14 |
| Acc | 6 | 10 |
| Eva | 4 | 7 |
| Lck | 4 | 7 |
| **Total** | **130** | **230** |

This preserves broad competence, slightly greater opportunity for damaging
magicks, and separate support growth through Spirit. The proposed fifteen
ability slots reserve four physical, four damaging-magick, four healing or
protective, and three utility roles. Their exact abilities need separate review.

Redistribute tiers across the entire enlarged board, including existing late
formations that become middle regions. Keep the approved HP, MP and rating
tiers, with maximum-tier rewards on approximately seven percent of stat nodes.
A provisional distribution is:

| Phase | Stat nodes | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Foundation | 40 | 30 | 9 | 0 | 1 |
| Developing options | 50 | 20 | 25 | 5 | 0 |
| Greater control | 50 | 5 | 30 | 14 | 1 |
| Advanced application | 50 | 0 | 15 | 30 | 5 |
| Section mastery | 40 | 0 | 6 | 25 | 9 |
| **Total** | **230** | **55** | **85** | **74** | **16** |

Quiet Reserve retains the early HP +400 landmark. A second exceptional maximum
could reward a middle-region center, while fourteen maximum rewards sit in the
final two phases. Previously purchased rewards would retain their grants under
the migration principle already used by the current board.

Exact node assignments and total gains remain review decisions. They must leave
useful progression space below the implemented caps of 9,999 HP, 999 MP and 255
for each rating. Rank gates also remain provisional until actual routes are
audited: visiting 350 distinct nodes requires at least 349 paid Steps before
backtracking. Access to the final region and completion of every optional node
are different milestones. RP and battle-reward pacing require a later pass.
