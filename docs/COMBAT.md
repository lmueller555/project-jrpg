# Eldenmere wait-ATB combat

The first combat slice is a repeatable encounter with one Bat and Caelan.
The Bat hovers on the grass west of the well, at world position **336, 900**.
Approach within 32 pixels and press **E** when **Engage Bat** appears. The Bat
does not attack automatically and cannot interrupt a conversation, household
action, opening cutscene, menu or room transition.

The encounter opens a separate clearing with combat sprites and a bottom
interface. The exploration world, player position, villagers and quest clocks
remain paused until the encounter ends. See the
[actual-game preview](reviews/atb_combat/README.md).

## Timing and decisions

Each combatant has an ATB gauge from 0 to 1. During charging:

```text
Gauge gain per second = 0.12 + 0.004 × Speed
```

At starting Speed 10, Caelan fills an empty gauge in 6.25 charging seconds.
The Bat has Speed 8 and needs approximately 6.58 charging seconds. These are
the initial tuning values; animation time is separate.

When Caelan becomes ready, **every gauge stops at that exact boundary** while
the player chooses. Enemy gauges exist in the model but are never displayed.
The Bat automatically chooses an affordable action when its gauge fills.
If both become ready simultaneously, Caelan receives the choice first.

All gauges also pause during action resolution, result screens and explicit
pause. Commands spend their ATB and MP once when committed; damage occurs once
at the authored impact time. Results appear after the animation finishes.
Large updates and smaller time steps follow the same readiness boundaries.

## Battle controls and interface

The bottom panel shows Caelan's name, current/max HP and MP, and ATB. Commands
appear when he is ready. Mouse clicks select a command directly; arrow keys
and Enter/Space provide keyboard access. Only supported learned abilities appear.

| Input | Action |
| --- | --- |
| Click a command | Commit that action when Caelan is ready |
| Arrows + Enter/Space | Select and commit a command |
| Escape | Pause/resume the battle |
| Continue on a result | Return to the same Eldenmere position |
| F11 | Toggle fullscreen |

Losing window focus pauses battle time and input. Regaining focus leaves it
paused until Resume or Escape. Repeated held input cannot spend several turns
or click through a result into exploration. The UI supports the minimum
480×320 window, 150% text, letterboxing and Reduced Motion.

## Caelan's initial actions

| Action | Effect | MP | Duration / impact |
| --- | --- | ---: | --- |
| Attack | Physical damage, potency 1 | 0 | 0.72 / 0.36 seconds |
| Guard | Halve the next incoming action | 0 | 0.50 / 0.20 seconds |
| Flee | Leave this test encounter safely | 0 | 0.70 / 0.35 seconds |
| Aether Dart | Magical damage, potency 2; requires its lattice unlock | 4 | 0.90 / 0.50 seconds |

Guard consumes a turn and remains until the next incoming action resolves.
Flee is guaranteed in this first encounter. Entering combat grants no spells or
lattice unlocks. Other catalog abilities will receive battle implementations in
later passes; their ownership and descriptions are preserved.

This slice uses the [approved per-hit damage backend](DAMAGE_FORMULA.md), with
independent 95–105% variance from the battle's own RNG. Attack accuracy is
currently guaranteed and critical hits are disabled while those probability
rules await design. No damage-limit break is granted by the encounter.

## Test Bat

| Attribute | Value |
| --- | ---: |
| HP | 72 |
| MP | 4 |
| Str | 7 |
| Mag | 6 |
| Spr | 3 |
| Def | 6 |
| M. Def | 5 |
| Speed | 8 |
| Acc | 10 |
| Eva | 12 |
| Lck | 4 |

| Ability | Type | Potency | MP |
| --- | --- | ---: | ---: |
| Bite | Physical | 1 | 0 |
| Wing Gust | Magical | 1.5 | 2 |

The Bat alternates Bite and Wing Gust. Once its MP is insufficient, it uses
Bite as the free fallback. At starting attributes, Caelan's Attack deals about
17–19 damage and a Bat attack deals about 8–10, making this a forgiving test.
Enemy HP and MP have independent structural bounds; future bosses can exceed
party resource caps without changing the damage calculation.

## Outcomes and checkpoints

Victory grants **20 Resonance Points and one Aether Emerald** on Continue.
This uses the existing atomic lattice reward operation with a unique receipt
for the encounter attempt. Resource changes and the reward checkpoint are saved
together; repeated confirmation cannot award twice. Rewards displayed before
return reflect available room at technical RP/inventory storage limits.

Victory and Flee retain the battle's remaining HP/MP, without refilling them.
Flee grants no rewards. Defeat returns with the pre-battle resources in this
prototype, allowing combat review without losing story progress. The Bat
reappears after four seconds in the exploration world for another test.

Battle HP/MP are copies until return. Quitting an unfinished encounter saves
the pre-battle journey rather than a partial fight. No interrupted battle is
resumed on Continue. A reward validation failure keeps the result open for a
retry with live resources, inventory and progression unchanged. A disk-write
failure after a successful settlement uses the game's existing live-state save
retry and error notice; it does not apply rewards again.

## Code and art

- [`battle_model.py`](../battle_model.py): deterministic charging, turns, actions,
  copied resources, AI and outcomes.
- [`battle_scene.py`](../battle_scene.py): separate field, sprites, UI, input,
  focus handling, damage popups and action animation.
- [`world_encounters.py`](../world_encounters.py): visible Bat, entry guards,
  resource/reward settlement, return and cooldown.
- [`assets/combat/actions.json`](../assets/combat/actions.json) and
  [`enemies.json`](../assets/combat/enemies.json): validated action/enemy data.
- [`assets/combat/encounter.json`](../assets/combat/encounter.json): world placement.

Caelan has idle, unarmed attack, casting, guard, hurt, victory and kneeling defeat
animations. The Bat has flight, bite, gust, hurt and descending defeat states.
Each actor has sixteen distinct transparent native frames. Contact and casting
poses cover the corresponding action's impact time. The original generated
sheets and extraction-only exporter are retained in
[`assets/source/combat`](../assets/source/combat) and
[`tools/build_combat_assets.py`](../tools/build_combat_assets.py).

Run `python tools/capture_combat.py` for the reproducible temporary-journey
preview. No ordinary journey or settings file is used by the capture.
