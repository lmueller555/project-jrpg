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

The lattice uses the full content width beneath the character header. Fit shows
the complete section. The camera supports 5–200% zoom, with smaller
node markers at overview scales and attribute icons at closer scales. The gold
exploration cursor, nearest-node selection and pulsing selection remain the
navigation controls; inspection does not move the character or spend resources.

## Growth budget

These totals assume every attribute node in this section is activated. Completed
values include Caelan's approved starting attributes and exclude equipment,
temporary effects and progression outside this section.

| Attribute | Nodes | Section gain | Completed value |
| --- | ---: | ---: | ---: |
| HP | 30 | +3,000 | 3,140 |
| MP | 12 | +180 | 210 |
| Str | 14 | +45 | 55 |
| Mag | 14 | +45 | 55 |
| Spr | 12 | +40 | 50 |
| Def | 14 | +45 | 55 |
| M. Def | 12 | +40 | 50 |
| Speed | 8 | +30 | 40 |
| Acc | 6 | +30 | 40 |
| Eva | 4 | +20 | 30 |
| Lck | 4 | +10 | 20 |
| **Attribute total** | **130** | | |

The section develops Caelan as an adaptable all-rounder, with comparable physical
and magical investment, useful healing and reliable defenses. Accuracy, Evasion
and Luck are ratings rather than percentages. Combat formulas and encounter
balance remain future work; these are section targets rather than game-wide caps.

Early nodes retain their original bonuses and crystal costs. Later nodes provide
larger authored increases. Increasing maximum HP or MP does not refill the current
resource, and Attunement Rank grants movement rather than additional hidden stats.

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
defines the version-two section. Formation records identify their member nodes,
center, entry and exit. Internal edge records include a `curve` control point;
straight edge records omit it.

The original 30-node version is archived in
[`assets/progression/aether_lattice_v1.json`](../assets/progression/aether_lattice_v1.json).
Existing node identities, effects, costs and connections are preserved. Continue
validates a version-one record against that archived board before upgrading it.
RP, spent Steps, visited and activated nodes, current position, reward receipts,
crystals and current HP/MP are retained. Layout changes do not grant rewards.

The deterministic authoring tool reproduces the current section:

```sh
python tools/build_caelan_lattice.py
```

To inspect the production menu using disposable journey and settings files:

```sh
python tools/preview_aether_lattice.py --rp 0 --crystals 0
```
