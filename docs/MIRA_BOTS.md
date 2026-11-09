# Mira's Engineer combat and Rivet

**Design-role revision, 2026-11-07:** Engineer supersedes Machinist. The runtime
catalog still uses the earlier label; these documentation notes do not change
the implemented bot rules below. Her [future combat progression concept](narrative/game_01/characters/MIRA.md#combat-progression-concept)
covers additional bots, engineered self-augments and a five-turn piloted mech.

Mira begins with a compact spring-driven bolt launcher, her workshop bot
**Rivet**, and **Overclock**. Rivet is her only starting bot and Piston Jab its
only autonomous ability. The MQ02 outing introduces this equipment at her
workbench and replaces the former spear preparation, carried prop and battle
poses. The intake repair still requires Mira's work and Caelan's small spell.

## Battle entry and autonomy

Rivet automatically unfolds beside Mira when she participates in a battle.
Deployment costs no turn or MP and starts with an empty ATB gauge. Its basic
Piston Jab is one physical, non-elemental hit using Mira's effective Str.
The current one-enemy battle sends it against the same foe as Mira; broader
target selection belongs to future multiple-enemy encounters.

Rivet is a support unit outside the character party tuple. It has no HP or MP,
cannot be selected by enemy attacks, is excluded from hostile area effects and
does not count toward party survival, rewards or player command selection.
Its ATB and remaining Haste turns are internal state; no separate bot HUD,
party-table row or health bar is displayed.

Bot gauges share the ordinary battle clock. Player decisions, tutorials, action
animations, explicit pause and focus loss stop them. At simultaneous readiness,
party choices take priority, then bot actions, then the enemy. A bot never
interrupts another animation or attacks while the player chooses a command.

If Mira is incapacitated, Rivet suspends its gauge and actions, preserving
progress and remaining Haste turns for revival. Defeat still occurs when all
characters are incapacitated. Results clear deployment, ATB and Haste; loading
pending victory spoils applies the same cleanup. Between encounters Rivet is
folded away with Mira's kit.

## Overclock

| Property | Rule |
| --- | --- |
| Command | Mira → Skills → Overclock |
| Cost | 5 MP and one ordinary Mira ATB action |
| Target | Her active bot; no weapon requirement |
| Animation / application | 0.90 / 0.50 seconds |
| Effect | Haste: multiply the final ATB fill rate by 1.5 |
| Duration | Eight completed bot actions |
| Recasting | Refresh to eight turns without stacking |
| Gauge progress | Preserved on application and expiration |

Mira's turns, enemy turns and menu time do not consume Haste. Each completed
Piston Jab spends one turn; starting or reaching its impact does not expire the
effect early. With Speed 8, Rivet normally fills in about 6.58 charging seconds;
Haste reduces this to about 4.39. Animation and decision time are excluded from
both measurements. The remaining turn count is not displayed on the battlefield;
Overclock's command description and activation feedback still explain the effect.

## Initial balance

Mira now starts with 150 HP, 30 MP and 10 in every rating. Her bots inherit
these reduced stats through the existing rules. The historical benchmark below
uses the former 300 HP / Str 20 profile to compare bot and spear mechanics.
Bolt Shot has potency 0.75, Piston Jab potency 1.0, and Rivet's base Speed is 8.
Against the Tusker at fixed 100% variance, Caelan's punch deals 16, Mira's bolt
50 and Rivet's jab 67. Every hit uses the existing physical damage formula and
its normal per-hit cap.

These two damage sources are balanced together. A deterministic 90-second
comparison with equivalent action timing produces 1,103 damage for Mira and
Rivet against 1,111 for the former spear profile. Using Overclock produces 1,154,
including its turn cost. Active Tusker simulations retain the preparation and
Guard opportunity and win with either strategy. These are tuning checks, not
guarantees for every encounter or future attribute build.

## Combat presentation

Mira's combat bank contains 42 authored whole-body drawings with her established
ponytail, cream flower, rolled pink sleeves and workshop equipment. Her ranged
formation position stays fixed while her shoulders, elbows and knees carry the
aim, recoil and recovery. Separate guard entry, held guard and guarded-impact
drawings distinguish bracing from an unguarded hurt reaction.

Bolt Shot raises and settles the launcher before releasing at 0.28 seconds.
The bolt travels from the release drawing's registered muzzle to the target's
silhouette, reaching the unchanged damage impact at 0.40 seconds; recovery ends
at 0.80 seconds. Overclock's controller gesture applies Haste at 0.50 seconds
and ends at 0.90 seconds. Small release/controller glints are suppressed with
Reduced Motion, which retains the drawings and readable bolt travel.

The source atlas and explicit anatomical floor/attachment registration are
retained under `assets/source/combat/mira_redraw/`. Rebuild using
`python tools/build_mira_combat.py`; the Machinist and mill asset builders also
dispatch to this exporter. The existing overworld launcher and Rivet assets
are preserved. The Ice Reaper opening's copied ready frames use the same idle.

See the [sprite and production-motion review](reviews/mira_redraw/README.md).

## Definitions and saved loadouts

- [`assets/abilities/characters.json`](../assets/abilities/characters.json)
  registers Mira's starting Overclock skill and Rivet capability.
- [`assets/combat/bots.json`](../assets/combat/bots.json) defines possible bots,
  owners, default abilities and allowed ability choices.
- [`assets/combat/actions.json`](../assets/combat/actions.json) defines Bolt Shot,
  Piston Jab and Overclock's timing, costs and effects.
- [`bot_loadouts.py`](../bot_loadouts.py) derives starting ownership and validates
  one bot/ability loadout per owner. Merely adding a catalog entry grants nothing.
- [`battle_model.py`](../battle_model.py) owns deployment, scheduling, actor-specific
  skills, Haste and combat cleanup.

Journeys persist a version-one `bot_loadouts` record with Mira's selected bot and
autonomous ability. New games and older saves without this record start with
Rivet/Piston Jab. Unknown bots, foreign owners, unsupported abilities and malformed
records are rejected before Continue can change the journey. Live deployment,
gauges and status counters are never saved. Caelan-only encounters have no bot.

The first release supplies one choice. Future earned bot ownership, upgrades and
configuration UI will extend this foundation; they are not granted by the current
catalog or implemented as a separate experience grind.

## Art and reproduction

Generated sources and provenance are retained under
[`assets/source/combat/machinist`](../assets/source/combat/machinist).
Mira has 19 registered poses on a 64×64 canvas; Rivet has 16 on a 32×32 canvas.
The small world launcher has registered grip and muzzle points and mirrors with
Mira's facing. Exported sprites use fixed native scales, opaque/binary alpha,
unclipped silhouettes and stable ground anchors.

`python tools/build_machinist_assets.py` exports the current assets.
`tools/build_mill_combat_assets.py` delegates to it for Mira and Rivet, preserving
the replacement when rebuilding the mill encounter.

The [production review](reviews/mira_rivet/README.md) includes a silent battle
preview, native/enlarged-text screenshots, source fingerprints and test results.
