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

The gold exploration cursor can browse the entire board, including branches
that the character cannot yet reach. Releasing the navigation controls selects
the nearest node and smoothly centers the camera on it. A pulsing circular halo
marks that selection. Moving the character requires the explicit Move action;
browsing never spends Steps, crystals or RP. The route preview shows the path
and its total Step cost. Connections with a rank requirement use permanent
Attunement, so spending movement cannot close a previously opened path.

## Nodes and crystals

The starter board contains 30 nodes: one blank origin, 20 stat nodes, seven
additional blank nodes and two ability nodes. The 20-node main route has
four-node and six-node side branches, with dead-end rewards and connections
requiring Attunement 5 and 8. All eleven attributes are represented.

Stat nodes grant HP +20, MP +2 or another attribute +1. The board data defines
the effect and crystal cost for each node.

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

Activation requires standing on the selected node, owning its required
crystals and using the Activate action. It consumes the cost and grants the
benefit once per character. Blank nodes cannot be activated. Insufficient
Steps, rank, crystals or an already activated node leave progression and
inventory unchanged.

An HP or MP node raises maximum capacity without refilling the current
resource. For example, activating HP +20 at 140/140 produces 140/160. A new
rank has no additional hidden stat growth.

Brace and Mend are the two new learnable abilities in the starter board.
Caelan retains his established basic magick capability separately. The lattice
records and displays learned techniques; casting and resolving their effects
will be connected to the future battle system. Opening quest spell outcomes
remain authored scenes.

## Menu controls

| Input | Action |
| --- | --- |
| Hold arrow keys | Steer the gold cursor freely; release to select the nearest node. |
| Tab / Shift+Tab | Inspect the next / previous node and smoothly center it. |
| Click the map | Select the node nearest the pointer and smoothly center it. |
| M or Move button | Prepare travel and inspect its cost. |
| A or Activate button | Prepare activation and inspect its cost. |
| Enter or the prepared action button | Confirm the prepared action. |
| Escape | Cancel a prepared action; otherwise return to Pause. |
| + / − or the zoom buttons | Smoothly zoom toward the selected node. |
| Mouse wheel over the map | Smoothly zoom around the point beneath the pointer. |
| Drag the map | Explore with the gold cursor; release to select the nearest node. |
| F or Fit button | Smoothly fit the whole board to the viewport. |
| 0 or 100% button | Return to 100% zoom and center the selected node. |
| Page Up / Page Down, Home / End | Read longer node details. |
| F1 or the ? button | Open the controls help. |

Node details show the effect or ability, owned and required crystal quantities,
travel and return costs, gate requirements, crystal stocks and learned abilities.
Cancellation leaves Steps, crystals and node ownership unchanged. The menu holds
the world and any conversation beneath it until the player resumes. Camera
centering takes about 180 milliseconds and redirects smoothly if another node
is selected during the transition. Zoom transitions use the same short easing,
with a range of 18% to 200% and a visible percentage in the map toolbar. Repeated
zoom inputs adjust the destination without jumping the current view. Zooming
does not select a different node or spend progression resources. Outside the
map, the wheel scrolls node details. Help and confirmation dialogs use the
wheel to scroll their own text.
Reduced Motion uses a steady selection halo and immediate camera and zoom
changes.

## Runtime and authored data

[`assets/progression/aether_lattice.json`](../assets/progression/aether_lattice.json)
defines stable node IDs, positions, effects, costs, connected edges, starting
positions and rank gates. Ability descriptions are defined in
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
