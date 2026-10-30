# Wait-ATB combat

MQ02 introduces combat on the riverbank north of Eldenmere. Caelan and Mira
fight a Ridgeback Tusker together before inspecting the blocked mill intake.
Mira is a temporary, player-controlled guest with a short spear, her own
attributes, commands, HP/MP and ATB. The warning, encounter and linear
aftermath lead into the quest's existing small spell and mechanical repair.

The repeatable Bat encounter unlocks after that fight, or for migrated older
journeys that already passed the intake investigation. It contains one Bat and Caelan.
The Bat hovers on the grass west of the well, at world position **336, 900**.
Approach within 32 pixels and press **E** when **Engage Bat** appears. The Bat
does not attack automatically and cannot interrupt a conversation, household
action, opening cutscene, menu or room transition.

The encounter opens a separate view of Eldenmere's well clearing, with combat
sprites and a bottom interface. The exploration world, player position,
villagers and quest clocks remain paused until the encounter ends. See the
[current battlefield preview](reviews/eldenmere_battlefield/README.md) and the
[initial combat implementation preview](reviews/atb_combat/README.md).

## Eldenmere battlefield

The battle camera looks across the grass west of the village well. The roofed
stone well sits behind and to the right of the fighting ground; timber and
plaster cottages, garden fences, firewood and trees establish the surrounding
village. The brook and mill are farther east and are outside this view.

The foreground has larger grass, clover, white flowers, partly buried stones
and exposed earth at the corners. Shorter, worn grass and footpaths leave the
middle open for attacks and spell effects. Warm daylight and contact shadows
keep both combatants connected to the ground while preserving the Bat's
hovering height. Scenery does not advance the exploration world or introduce
festival decorations independently of the story.

Two small foreground grass tufts sway at the outer corners. Reduced Motion
keeps them still, and pausing the battle freezes their animation. Background
art, grass poses and contact shadows are loaded or prepared once per encounter.

## Music and battle entry

The user-provided **Eldenmere Theme** plays on the title screen, throughout
Eldenmere and its interiors, and along the millrace. A shared streamed-music
controller preserves playback across New Game, Continue and those area changes.
Every encounter uses the user-provided **Kindled Courage**. In MQ02 it is cued
on the first displayed page of Mira's “Easy, Caelan. Back slowly. Keep your feet
under you” line, while the player is still in the world. Text reflow and repeated
updates do not restart it. Canceling that encounter conversation returns to the
Eldenmere theme; an unfinished encounter reloads with the world theme.

Battle entry freezes a freshly rendered world frame, closes a dark diagonal
curtain, briefly covers the screen and reveals the battlefield in 0.72 seconds.
Reduced Motion uses a 0.26-second plain fade. World and battle clocks remain
frozen throughout entry. Held keys, mouse clicks and transition acknowledgements
cannot submit a command when the battlefield appears. Escape and focus loss
pause the transition; resizing and fullscreen changes preserve its progress.

Music continues during ATB decisions and gently lowers beneath dialogue and
Mira's tutorial. Explicit battle pause and window focus loss pause the score
without rewinding it. Volume and mute changes apply immediately through the
existing Music preference. Exiting Spoils, or returning from Flee or defeat, restores the Eldenmere theme.
Victory uses its one-shot fanfare and then silence, including reward retries.
Environmental and UI effects retain their independent volume and channels.

The original uploads remain in `assets/music/`; supported Vorbis playback copies
and their catalog are under the same folder. The asset guide documents the
conversion and conservative removal of the battle track's near-silent tail.
See the [actual scene and transition review](reviews/battle_music_transition/README.md).

## Timing and decisions

Each combatant has an ATB gauge from 0 to 1. During charging:

```text
Gauge gain per second = 0.12 + 0.004 × Speed
```

At starting Speed 10, Caelan fills an empty gauge in 6.25 charging seconds.
The Bat has Speed 8 and needs approximately 6.58 charging seconds. These are
the initial tuning values; animation time is separate.

When any participating character becomes ready, **every gauge stops at that
exact boundary** while the player chooses. The active party row is highlighted;
click another ready row or press Tab to choose between ready characters.
Commands and MP costs belong to the selected character. Enemy gauges exist
in the model but are never displayed.
The Bat automatically chooses an affordable action when its gauge fills.
Party readiness wins a simultaneous boundary with the enemy.

All gauges also pause during action resolution, result screens and explicit
pause. Commands spend their ATB and MP once when committed; damage occurs once
at the authored impact time. Results appear after the animation finishes.
Large updates and smaller time steps follow the same readiness boundaries.

## Battle controls and interface

The compact bottom panel places a party table on the right, with shared
**ATB, NAME, HP, MP** column headings. Each participating character occupies
one horizontal row. A small yellow ATB gauge sits to the left of the name;
HP and MP show current/max numbers with thin bars beneath them in their own
columns. The millrace has Caelan and Mira's rows; the Bat has Caelan's row.
HP is green above 50%, yellow
above 25% through 50%, and red at 25% or below. MP is blue; the ATB fill stays
yellow while charging and when ready.

At standard text size the panel is 80 logical pixels tall, down from 108
(about 26% shorter). Larger text can expand it to preserve readable labels
and controls. The table shows participating characters rather than the sketch's
illustrative future-party placeholders.

Commands form a compact vertical list on the left when a party member is ready.
Mouse clicks select a command directly; arrow keys and Enter/Space provide
keyboard access. Only supported learned abilities appear. Result titles and
Continue remain on the left; action messages, rewards and retry details use
the space beneath the party row. See the
[compact table preview](reviews/compact_battle/README.md).

| Input | Action |
| --- | --- |
| Click a command | Commit that action for the selected ready character |
| Click a ready row / Tab | Select another ready party member |
| Arrows + Enter/Space | Select and commit a command |
| Escape | Pause/resume the battle |
| Continue on Spoils / a non-victory result | Return to exploration; failed mill attempts return to the safe approach |
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

## Millrace tutorial

The Ridgeback Tusker has 450 HP, Str 16, Def 18 and Speed 8. It alternates a
normal tusk strike, a separate preparation turn and a heavy charge. Preparation
deals no damage and identifies the charge target. The next enemy turn delivers
the charge, leaving the target a genuine opportunity to choose Guard. Guard
halves the next incoming hit against that character and survives the harmless
preparation turn.

Mira has HP 300, MP 30, Str 20, Mag 12, Spr 12, Def 18, M. Def 14, Speed 12, Acc 16,
Eva 12 and Lck 10. Her Attack resolves to Spear Thrust at potency 1.5. Against
the Tusker, Caelan's punch deals 16–17 and her spear deals 96–106. A Tusker
charge deals 66–73 against Caelan, or 33–36 when guarded. These values use the
approved formula and 95–105% per-hit variance.

The encounter's natural Mira guidance follows readiness, her first turn,
the targeted charge tell and the resulting hit. Short interface hints explain
the exact controls. Guidance is player-paced, freezes combat clocks, and
consumes acknowledgement input so it cannot also commit a command. The player
can choose other actions; the creature is never held at artificial minimum HP.

The new battlefield looks south/southwest toward distant Eldenmere, with the
river along the near left bank, reeds, exposed roots and freshly broken timber.
A visible Tusker and damaged tree mark the actual upstream approach. Mira
carries her spear from the workbench, sets it aside during intake work and
takes it up for the return. See the [actual MQ02 review](reviews/mill_combat/README.md).

Victory grants Caelan 30 RP and one Aether Emerald once on Spoils, and commits
the cleared trail with remaining resources before its Continue opens the linear aftermath. The intake remains
blocked until the existing repair. If Mira wins while Caelan is incapacitated,
first aid restores him to 25% maximum HP before the recovery exchange. Flee
returns to the safe approach without rewards or encounter completion. Defeat
returns there with full Caelan HP and pre-battle MP for a viable retry.
Interrupted battles save the unfinished encounter at the safe approach; no
partial ATB, guest resources or dialogue cursor is serialized. Older completed
intake/repair saves preserve their progress through an explicit legacy bypass
and receive no invented battle or reward.

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

## Victory and Spoils of Battle

When the final enemy is defeated, combat shows a centered **VICTORY** banner
and immediately replaces Kindled Courage with the user-supplied **Triumphal
Fanfare**. The fanfare plays once. The banner leads through a brief fade into a
separate **Spoils of Battle** screen; reward amounts and a victory Continue
button no longer appear in the battlefield.

Spoils awards the encounter's actual Resonance Points and items on entry.
Resonance Points are the game's existing battle-experience progression; this
change does not introduce a second EXP system. The Bat grants 20 RP and one
Aether Emerald; MQ02's Tusker grants 30 RP and one Aether Emerald. Displayed
amounts reflect available RP/inventory capacity. The screen shows authoritative
received amounts, and Continue becomes available after the award checkpoint
succeeds. A failed grant or save leaves a Retry action on Spoils.

The fanfare may finish while Spoils is open. No music follows it, and volume,
focus or repeated updates cannot replay it. Eldenmere Theme resumes only when
the player exits Spoils. World clocks remain frozen during the banner, fade and
Spoils; keyboard, mouse, focus, pause, scrolling and enlarged text remain usable.

## Outcomes and checkpoints

Victory saves a durable pending reward before presenting Spoils. Resources,
once-only reward receipt, and MQ02's cleared-encounter milestone are committed
together when Spoils awards the result. Continue leaves the review screen and
returns to exploration; Mira's linear aftermath begins only then.

Quitting during the victory banner, the fade or Spoils resumes directly at
Spoils in silence. A pending grant is completed once; an already received grant
is displayed without being awarded again. Presentation clocks and partial
battles are never serialized. Failed writes can be retried without duplicating
items or progression. Older journeys without a post-battle checkpoint still load.

Victory retains remaining HP/MP, with the existing MQ02 first aid if Mira wins
while Caelan is incapacitated. Flee grants no rewards and keeps its existing
safe return. Defeat also keeps its existing retry checkpoint. Neither Flee nor
defeat opens Spoils or plays the victory fanfare. The Bat returns after its
normal four-second exploration cooldown.

## Code and art

- [`battle_model.py`](../battle_model.py): deterministic charging, turns, actions,
  copied resources, AI and outcomes.
- [`battle_scene.py`](../battle_scene.py): separate field, sprites, UI, input,
  focus handling, damage popups and action animation.
- [`assets/combat/eldenmere`](../assets/combat/eldenmere): native battlefield
  panorama, transparent grass accent and source metadata. The retained
  [generated artwork](../assets/source/combat/eldenmere_README.md) is exported
  by [`tools/build_eldenmere_battlefield.py`](../tools/build_eldenmere_battlefield.py).
- [`world_encounters.py`](../world_encounters.py): encounter entry, victory flow,
  atomic reward checkpoints, return and cooldown.
- [`spoils_scene.py`](../spoils_scene.py): dedicated reward review and retry UI.
- [`post_battle.py`](../post_battle.py): durable victory checkpoint validation.
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
