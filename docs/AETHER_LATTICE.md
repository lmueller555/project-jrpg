# Aether Lattice

Open **Pause → Aether Lattice** to inspect character progression. The connected
board separates travel from activation: **Lattice Steps** pay for movement,
and **Aether Crystals** activate stat or ability nodes after the character
reaches them.

## Progression and travel

| Term | Meaning |
| --- | --- |
| Resonance Points (RP) | Battle-earned experience accumulated by an individual character. |
| Attunement Rank | Permanent character level, derived from earned RP. |
| Lattice Steps | Banked movement allowance; each rank gained awards one Step. |
| Aether Crystals | Inventory resources consumed when activating nodes. |

Caelan starts at **Attunement 1**, with zero RP and zero Steps, standing on the
blank origin node. His starting attributes remain 140 HP, 30 MP and nine
ratings of 10. Normal New Game grants no crystals or sample battle rewards.

The first rank gain requires 20 RP, followed by 25, 30, 35 and so on. Overflow
RP carries forward, and a single reward can grant several ranks and their
corresponding Steps. Spending Steps never lowers Attunement.

Each connection crossed costs one Step, including backtracking. A blank node
still costs movement but grants no bonus, RP or resource. A character may pass
through an unactivated stat or ability node. Missing crystals prevent its
activation without blocking travel along otherwise open connections.

Clicking a node selects it and smoothly centers the camera on it. The gold
exploration cursor can also browse the entire board, including branches that
the character cannot yet reach. Releasing the arrow keys or a camera drag
selects the node nearest that cursor. A pulsing circular halo marks the
selection; browsing never spends Steps, crystals or RP.

A reachable selected destination shows its route, Step cost and a **Move**
button only when the character has enough Steps and meets the route's rank
requirements. Clicking Move executes the travel. The current node and
unavailable destinations have no travel preview or Move button. Connections
with a rank requirement use permanent Attunement, so spending movement cannot
close a previously opened path.

## Nodes and crystals

Caelan's section contains 200 nodes: 130 attribute nodes, 20 ability nodes and
50 empty nodes, including the origin. Large and small circular formations use
curved internal paths, with junctions and onward routes through their centers.
Connections between formations and the nodes outside them use straight lines.
See the [section guide](CAELAN_LATTICE.md) for the layout and complete growth
budget. All eleven attributes are represented.

HP nodes grant +100, +200, +300 or +400; MP nodes grant +5, +10, +20 or +30.
Every other attribute node grants +1, +2, +3 or +4. Lower tiers dominate early
progression and higher tiers become common deeper into the route. Maximum-tier
rewards remain rare, usually behind late rank gates, with Quiet Reserve's
central HP +400 as an early landmark. See the
[pacing and growth guide](CAELAN_LATTICE.md#reward-tiers-and-pacing) for the
authored distribution. Board data defines each individual effect and cost.

| Crystal | Color | Activates |
| --- | --- | --- |
| Aether Emerald | Green | HP nodes |
| Aether Sapphire | Blue | MP nodes |
| Aether Ruby | Red | Str and Def nodes |
| Aether Amethyst | Violet | Mag and M. Def nodes |
| Aether Opal | White | Spr nodes |
| Aether Topaz | Gold | Speed, Acc, Eva and Lck nodes |
| Aether Diamond | Prismatic | Spell and ability nodes |

Names and attribute icons accompany colors. The seven crystals are ordinary
inventory items, and related attributes share a crystal family. Starter nodes
require one matching crystal; costs remain data so other quantities can be
authored later.

An eligible, unactivated node at the character's current position shows its
effect, full crystal cost and an **Activate** button when the required crystals
are available. Clicking Activate consumes the cost and grants the benefit once
per character. Blank nodes cannot be activated. Insufficient Steps, rank,
crystals or an already activated node leave progression and inventory unchanged.

An HP or MP node raises maximum capacity without refilling the current
resource. For example, activating HP +100 at 140/140 produces 140/240. A new
rank has no additional hidden stat growth.

Brace and Mend are among the twenty learnable abilities in Caelan's section.
Caelan retains his established basic magick capability separately. The lattice
records and displays learned techniques; casting and resolving their effects
will be connected to the future battle system. Opening quest spell outcomes
remain authored scenes.

## Menu controls

| Input | Action |
| --- | --- |
| Click a node | Select it, smoothly center the camera and pulse the selection. |
| Hold arrow keys | Steer the gold cursor freely; release to select the nearest node. |
| Mouse wheel over the map | Smoothly zoom around the point beneath the pointer. |
| Hold left mouse button and drag the map | Pan the camera directly; release to select and center the node nearest the gold cursor. |
| Click Move | Travel to the selected destination for the displayed Step cost. |
| Click Activate | Activate the current node for the displayed crystal cost. |
| Escape / × | Close help or return to Pause. |
| Mouse wheel / Page Up / Page Down / Up / Down in help | Scroll the controls help. |
| F1 or the ? button | Open the controls help. |

The lattice fills the full content width beneath the compact character header.
The small action preview sits beside the selected node when its requirements
are met and disappears while navigating or reading help. It is not a permanent
panel. Clicking a node only selects it; clicking its displayed command executes
the action without a separate confirmation dialog. Empty map clicks do not
select a nearby node. The menu holds the world and any conversation beneath it
until the player resumes.

Camera centering takes about 180 milliseconds and redirects smoothly if another
node is selected during the transition. The mouse wheel is the only zoom
control, with a range of 5% to 200%. Zoom transitions use the same short easing;
repeated wheel inputs adjust the destination without jumping the current view.
Zooming does not select a different node or spend progression resources. The
wheel scrolls help while it is open.

Dragging grabs the map beneath the pointer: its contents track the mouse
directly at every zoom and window scale. A three-pixel tolerance keeps small
hand movements from turning a click into a drag. The camera and zoom stop their
current transition when a grab begins. Wheel inputs are ignored while dragging.
The gold cursor stays at the camera center while dragging;
release selects its nearest node and eases to that node over 180 milliseconds.
Dragging and selection never move the character or spend resources.

Reduced Motion uses a steady selection halo and immediate camera and zoom
changes.

## Runtime and authored data

[`assets/progression/aether_lattice.json`](../assets/progression/aether_lattice.json)
defines stable node IDs, positions, effects, costs, connected edges, starting
positions and rank gates. Formation membership and quadratic curve controls
describe the visual layout; each connection still costs exactly one Step.
Ability descriptions are defined in
[`assets/abilities/catalog.json`](../assets/abilities/catalog.json).

[`aether_lattice.py`](../aether_lattice.py) owns the graph and per-character
progress: cumulative RP, spent movement, current node, visited nodes, activated
nodes and battle-reward receipts. Characters share the authored board while
keeping independent progression. Only Caelan is currently available in the
game; this system does not recruit additional party members.

Effective attributes are calculated from **preserved base attributes + bonuses
from activated nodes**. The activated-node record is the source of lattice
bonuses, which prevents them from being added again on Continue. Current HP
and MP are validated against their effective maxima.

Activation validates the complete cost and effect before changing inventory,
node ownership or derived attributes. The game checkpoints the complete result
together. Existing atomic-save replacement and error/retry behavior apply; a
failed disk write does not mean the activation has been durably saved.

[`lattice_progression.py`](../lattice_progression.py) coordinates those
transactions across the lattice, inventory and attributes. The public game
operations are `move_lattice`, `activate_lattice` and `award_battle_rewards`.

## Battle rewards

The current game has no battle controller. The integration boundary is:

```python
game.award_battle_rewards(
    'unique-battle-attempt-id',
    {'caelan': 20},
    {'aether_emerald': 1},
)
```

The awards map gives RP to named recipients; the drops map adds shared crystal
items. The reward operation validates the entire payload and commits its
receipt, RP and drops together. Repeating the same completion receipt awards
nothing again. A legitimately repeated encounter needs a new attempt ID.

There is no reward-claim button in the normal game, no retroactive RP for
opening quests and no sample crystals granted on New Game. Actual combat
rewards will call this interface when battles are implemented.

## Journey compatibility

Journey checkpoints contain an independently versioned `aether_lattice`
record alongside character attributes and inventory. Loading the title
validates these records without changing the fresh world or saved journey.
Continue restores them together and recomputes node bonuses once.

The authored section is board version three. Version-one and version-two
records are validated against their archived rules before upgrading. Existing
node IDs remain intact. This reward pass preserves version-two geometry and
retains RP, spent Steps, position, visited
and activated nodes, receipts and inventory. Previously activated nodes retain
their original paid bonuses; unactivated nodes use the current attribute,
bonus tier and crystal family. An old activation cannot collect its replacement
reward a second time.

Lattice ledger schema version two adds per-character `legacy_activated` provenance.
It identifies old grants whose amounts and attributes are derived from the
canonical version-two board archive. Fresh journeys have no legacy grants.
Loading rebuilds the combined old and new bonuses once, preserving base
attributes and current HP/MP without stacking gains or refilling resources.

Attribute version-three snapshots preserve base values under `attributes` and
store current HP/MP separately. Existing version-one and version-two attribute
values migrate into the preserved base; Caelan's earlier 300-to-140 HP migration
still applies to the original version-one baseline. Older journeys without
lattice progress receive the untouched origin state and no rewards.

New Game resets lattice progress, receipts, derived bonuses and crystal
ownership. Existing quest facts and their ordinary save migrations retain
their established behavior.

## Isolated preview

```sh
python tools/preview_aether_lattice.py
```

The interactive preview uses temporary journey and settings files. Its default
fixture awards 20 RP and one Emerald through the real reward interface, so the
first HP activation can be reviewed immediately. It does not open or replace
the player's ordinary journey.

For a richer fixture, use:

```sh
python tools/preview_aether_lattice.py --rp 500 --crystals 10
```

The RP and crystal values configure only the temporary preview. The capture
tool writes production-menu screenshots and verification data beneath
`work/aether-lattice`:

```sh
python tools/capture_aether_lattice.py
```
