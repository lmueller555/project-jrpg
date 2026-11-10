# Optional elemental encounters in the Sanctuary cave

Two optional branches extend the continuous Sanctuary cave. **Embravyr** waits
in the **Embervein Chamber** and **Nivareth** in the **Stillfrost Chamber**.
Both are fixed level-four, one-time solo encounters. Either can be approached
first; neither is required to reach or defeat Vespermaw. Completing the earlier
Aqua Edge bat lesson enables these encounters without resolving MQ03's pending
Sanctuary arrival.

These guardians are formations of ambient elemental Aether. Embravyr's red
core, emberglass fragments and flame form its body; Nivareth's white core,
suspended pale shards and frost form its lattice. They are not living cave
reptiles, insects or animals with elemental coatings. On defeat their Aether
settles into a usable focus gem.

## Exploration and approach

The Embervein branch leaves the lower Vein Gallery route. The Stillfrost branch
leaves the upper/deeper junction. Each has a continuous walkable approach,
room label and its own terrain palette, wall microcrystals and pulse lighting.
The rooms and connecting branches share `sanctuary_cave`; entering them does
not load a separate exploration scene. Their protected encounter spaces do not
roll random battles over the authored guardian trigger.

At an undefeated guardian the player receives **Approach / Party / Leave**.
Party preparation uses existing story restrictions and restores no resources.
A short live-world introduction leads to a displayed loading screen and the
matching animated battlefield, `cave_embervein` or `cave_stillfrost`.

Embervein's walls carry red microcrystal seams with a warm floor wash; Stillfrost
uses white and blue facets over colder stone. Sparse native-pixel embers or
frost motes stay clipped to each room's actual walkable floor. Reduced Motion
holds their positions and removes rising wisps. A quiet original crystal hum
uses Effects volume, yields on menus, dialogue, focus loss and combat, and
releases its mixer channel without changing the music stream.

## Bestiary profiles

Both use the shared enemy growth pipeline, selected stat profile, species
multipliers and boss HP multiplier, with a single final rounding step.

| Attribute at level 4 | Embravyr | Nivareth |
| --- | ---: | ---: |
| HP | 612 | 658 |
| MP | 37 | 61 |
| Strength | 15 | 12 |
| Magick | 15 | 18 |
| Spirit | 16 | 19 |
| Defense | 28 | 11 |
| Magick Defense | 11 | 28 |
| Speed | 11 | 12 |
| Accuracy | 17 | 17 |
| Evasion | 15 | 15 |
| Luck | 16 | 16 |
| EXP per living active party member | 420 | 420 |

Embravyr uses the **Armored** stat profile, with Strength ×1.10, Magick ×1.25,
Speed ×0.90 and boss HP ×1.80. Nivareth uses **Warded**, with Strength ×0.85,
Magick ×1.20, Speed ×0.90 and boss HP ×2.20. Both use the Windup Attacker
archetype and Telegraphed Windup fighting style.

| Incoming element | Embravyr | Nivareth |
| --- | ---: | ---: |
| Non-Elemental | 100% damage | 100% damage |
| Fire | 100% healing | 200% damage |
| Electric | 100% damage | 100% damage |
| Water | 200% damage | 50% damage |
| Ice | 150% damage | 100% healing |
| Nature | 50% damage | 100% damage |
| Wind | 100% damage | 100% damage |
| Holy | 100% damage | 100% damage |
| Ground | 100% damage | 100% damage |

Absorption overrides a stored damage percentage. Matching elemental damage
restores its neutral-affinity amount up to missing HP. For a mixed Spellblade
hit, only the magical component follows that elemental response; the physical
component still deals ordinary physical damage. The tables remain internal
Bestiary data. Appearance, environment and observed hits provide clues; this
change does not add Study or automatic weakness labels.

## Combat cycles

| Embravyr action | Category / target | Potency | MP |
| --- | --- | ---: | ---: |
| Cinder Lash | Non-Elemental physical / one character | 0.65 | 0 |
| Emberwash | Fire magical / living party | 0.45 each | 4 |
| Gather Embers | Preparation / self | 0 | 0 |
| Furnace Lunge | Fire physical / marked character | 1.35 | 0 |
| Cooling | Recovery / self | 0 | 0 |

| Nivareth action | Category / target | Potency | MP |
| --- | --- | ---: | ---: |
| Rime Needle | Ice magical / one character | 0.40 | 0 |
| Glassfall | Ice magical / living party | 0.35 each | 4 |
| Gather Frost | Preparation / self | 0 | 0 |
| Frostspire Thrust | Ice physical / marked character | 2.00 | 0 |
| Settling | Recovery / self | 0 | 0 |

Each repeats the listed cycle, skipping an unaffordable party-wide spell and
using its free basic action as fallback. Initial ATB values use the ordinary
0–50% range. Preparation identifies the next large hit and its living target;
that character gets at least one valid action before release. A changed target
receives a fresh warning and response opportunity. The red charge aura and
named announcement remain attached to the actual preparation state.

After Furnace Lunge or Frostspire Thrust, the guardian takes **50% more damage**
and spends its next turn recovering. Vulnerability starts at the large hit's
impact and ends immediately before the next basic action begins. Vespermaw's
post-Pounce exhaustion now uses the same **×1.50** multiplier. This is a visible
recovery window, independent of a future Stagger system. Guard retains its
existing component-level calculation. The exhaustion bonus applies once to the
composed hit before its ordinary damage cap.

Aqua Edge is useful against Embravyr. Nivareth's high Magick Defense and Water
resistance make ordinary physical attacks and Aether Edge viable choices when
it is found first; Flame Edge is useful if the Red gem was obtained already.
Ice Edge also offers a second weakness option against Embravyr when Nivareth
was defeated first. Neither route requires the other guardian's reward.

During these two teaching encounters, every already-learned elemental Edge
costs **0 MP**: Aqua, Flame and Ice. This applies throughout the fight and retries.
It does not grant unknown skills or missing gems, and selecting the required
owned focus still matters. Aether Edge retains its **4 MP** cost and Overclock
its **5 MP** cost. In ordinary encounters and Vespermaw, elemental Edges retain
**4 MP**. There is no hidden pre-fight healing or MP refill.

## Focus rewards and acknowledged installation

| Guardian | Guaranteed focus item | Installed gem | Learned technique |
| --- | --- | --- | --- |
| Embravyr | `red_focus_gem` | Fire / Red | Flame Edge (`flame_edge`) |
| Nivareth | `white_focus_gem` | Ice / White | Ice Edge (`ice_edge`) |

Each victory grants the full 420 EXP to every living active character, plus its
focus item once. Reserves, bots and KO characters receive no EXP. The focus,
installed gem and technique are guaranteed even if Caelan ends the fight KO.
Neither a raw Aether Ruby nor Aether Opal installs these focuses.

The reward transaction records the item, owned gem, learned technique, selected
focus, party resources, EXP, defeated state and receipt together. The newly
acquired gem becomes the selected focus. There is still only one blade gear;
this change does not add multi-element combinations or another simultaneous
focus selection. All three Edges use physical potency 1 plus magical potency
0.5; their magical types are Water, Fire and Ice respectively.

After Spoils, Caelan and Mira acknowledge the settled gem and its installation.
The first acquired focus receives the fuller discovery exchange; the second
acknowledges his growing familiarity. Either order works. Presentation does not
grant rewards a second time. If Caelan is KO, the already-earned reward remains
and the dialogue waits until he is conscious during free exploration, including
after recovery outside the cave.

## Defeat, withdrawal and durable saves

`elemental_bosses.py` owns separate records for the guardians: discovery,
introduction seen, defeated and pending acquisition presentation. `victory_order`
records which was obtained first. One pending ticket fixes the enemy, level,
receipt, battlefield, safe return position, party entry resources and combat
seed before loading. Receipts are `boss:embravyr` and `boss:nivareth`.

Continue from an unfinished encounter restarts that exact entry. A defeat
restores captured entry HP/MP, grants nothing and offers **Retry / Leave**.
Retry retains the ticket and seed; Leave returns to that chamber's reachable
approach. Flee is permitted, retains resources actually spent and returns to
the chamber approach without a reward. Both guardians remain available until
victory, and their state is separate from the random encounter countdown and
Vespermaw's owner.

A failed victory checkpoint rolls back the full transaction. Retry cannot keep
a gem while repeating EXP, or mark an undefeated guardian cleared. Pending or
awarded Spoils resume on Continue without duplicating grants. An interrupted
acquisition exchange replays its pending presentation until acknowledged; it
never reruns the battle or reward. Completed encounters disappear from their
world positions and cannot repeat rewards.

Older journeys without this optional state gain fresh, undefeated guardians.
Their existing inventory, party, EXP, treasure, Aqua discovery, Vespermaw entry
or completion and MQ03 stage remain intact. Boss completion does not recruit
Lucan, conclude the Sanctuary arrival or alter story music ownership.

## Validation and review

The focused model, map and actual-Game integration suites cover both orders,
partial completion, zero MP, Guard response windows, ×1.50 exhaustion, save
boundaries, rollback, KO acquisition and independent older journeys.

The [encounter review](reviews/elemental_cave_encounters/README.md)
contains historical room, combat and acquisition captures, a contact sheet and
source hashes. Its captured EXP values predate the current reward curve;
the values in this guide describe live rewards. Reproduce the review with:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python tools/capture_elemental_cave_encounters.py
```
