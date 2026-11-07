# Wait-ATB combat

MQ02 introduces combat on the riverbank north of Eldenmere. Caelan and Mira
fight a Ridgeback Tusker together before inspecting the blocked mill intake.
Mira is a temporary, player-controlled Engineer with a bolt launcher, her own
attributes, commands, HP/MP and ATB, and the autonomous bot Rivet. Mira gives Caelan his gear-and-gem sword before departure. The warning, encounter and linear aftermath lead into his smaller sword-focused water spell and the mechanical repair.

Engineer is her revised design role; the [bot guide](MIRA_BOTS.md) distinguishes
that terminology from the earlier runtime label and documents current mechanics.

The repeatable **test Bat** is available in Eldenmere independently of MQ02 or
other quest progress. It contains one Bat and Caelan and hovers on the grass
west of the well, at world position **336, 900**. Walk or run within 32 pixels to
start the encounter automatically; no interaction key is required. It cannot
interrupt a conversation, household action, opening cutscene, menu or room
transition, and it does not trigger indoors or at the millrace.

After returning, move outside its trigger radius before approaching again.
The normal four-second respawn cooldown also applies, so standing at the
return point cannot repeatedly drag the player into combat. Loading while
already inside its radius also waits for the player to leave and reapproach.
Pre-MQ02 victories
use the same fanfare, Spoils, once-only rewards and reload checkpoints without
advancing or inventing mill quest progress.

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
Every encounter uses the user-provided **Kindled Courage**. MQ02 stages its
first millrace arrival as a cutscene: Caelan stops while Mira follows through
the real trail link, both face the boar, and the camera pans over to hold it
through their conversation. A bottom portrait panel keeps the creature visible.
Mira’s final “Caelan, back towards me. Slowly” line
requests the return pan, with its panel above the party. Battle music starts
only after the camera has arrived and the player has acknowledged the warning.
Fast reading cannot skip the pan; slower reading holds the returned party shot.
The score then continues into battle without restarting.

Pause or focus loss freezes staging and the camera. Movement and unrelated
menu inputs cannot move the actors or advance a pan. Reduced Motion uses static
shot changes. Canceling releases the camera and actors; an unfinished scene
reloads at the safe arrival and restarts without granting progress. A Flee or
defeat return waits for an explicit retry or a new area entry. Completed and
legacy-bypassed encounters do not replay. Ordinary dialogue still follows the
player with the full viewport. See the [millrace cutscene review](reviews/millrace_cutscene/README.md).

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
exact boundary** while the player chooses. The active character column is highlighted;
click another ready character’s status area or press Tab to choose between ready characters.
Commands and MP costs belong to the selected character. Enemy gauges exist
in the model but are never displayed.
The Bat automatically chooses an affordable action when its gauge fills.
Party readiness wins a simultaneous boundary with the enemy.

All gauges also pause during action resolution, result screens and explicit
pause. Commands spend their ATB and MP once when committed; damage occurs once
at the authored impact time. Results appear after the animation finishes.
Large updates and smaller time steps follow the same readiness boundaries.

## Battle controls and interface

The bottom panel has one column per participating character and a narrower
shared Commands column on the right. Character columns contain name and yellow
ATB on the same row, followed by HP and MP bars with their labels and values to
the right. These three compact rows use the top third; the individual mechanic
area uses the bottom two-thirds. HP is green above 50%, yellow above 25% through 50%,
and red at 25% or below. MP is blue.

Caelan’s lower section contains his rotating gear. Mira’s lower section is
reserved for her future mechanic; Overclock and Rivet continue through their
existing command and autonomous behavior. Panel height follows measured text
and the wheel’s usable area; larger text keeps its configured size. Long
command labels wrap and command selection scrolls to remain visible. Contextual
skill details appear immediately above the panel.

At standard text size in 960×640 or 1440×960, the three-character panel is
102 logical pixels tall, down from 128, while Caelan's gear stays 48×48 logical
pixels. Accessible text keeps its configured size; at the smallest window with
150% text, the panel grows to fit and the party stagger compresses to keep every
sprite visible. See the [compact UI comparison](reviews/compact_combat_ui/README.md).

Rivet remains visible and autonomous on the battlefield. Its internal ATB gauge
and remaining Haste turns are not displayed as a separate HUD. Overclock's
description and one-off action feedback remain available.

| Input | Action |
| --- | --- |
| Click a command | Open Skills or commit an action for the selected ready character |
| Click a ready character’s status / Tab | Select another ready party member |
| Arrows + Enter/Space | Select and commit a command |
| Drag Caelan’s gear | Rotate a gem toward the fixed north catch; release to seat it |
| Hover the gear | All units’ ATB charges at 25% of its normal rate |
| G, then Left/Right and Enter/Space | Focus the gear, rotate and seat a gem with the keyboard |
| Tab while the gear is focused | Return to command navigation |
| Back / Escape in Skills | Return to root commands without spending a turn |
| Escape outside Skills | Pause/resume the battle |
| Continue on Spoils / a non-victory result | Return to exploration; failed mill attempts return to the safe approach |
| F11 | Toggle fullscreen |

Losing window focus pauses battle time and input. Regaining focus leaves it
paused until Resume or Escape. Repeated held input cannot spend several turns
or click through a result into exploration. The UI supports the minimum
480×320 window, 150% text, letterboxing and Reduced Motion.

## Caelan’s gear focus

The wheel holds Nature, Water, Fire and Ice gems. The fixed catch at twelve
o’clock determines the settled focus. A short snap confirms seating; gear
rotation consumes no turn, ATB or MP. Caelan can adjust it while charging and
while deciding an action. His confirmed action captures its focus and locks
rotation until that action finishes.

Hover slows charging for party members, enemies and Rivet. Haste multiplies
normally: an Overclocked Rivet charges at base × 1.5 × 0.25 while hovering.
Ready decisions still pause every gauge completely. Attack animations, damage
impact timing and audio retain their normal speed.

Aether Edge works with every gem and remains non-elemental. Future learned
Nature Edge, Aqua Edge and Flame Edge require their respective gems as well as
normal weapon and MP requirements. Selecting a gem never teaches its skill.
The Ice gem currently supplies a focus position without an initial combat skill.
MQ02 temporarily exposes its three experimental Edges: the first matching
attempt fails, the next matching attempt discovers Aether Edge, and only that
technique remains learned afterward. The later water utility spell does not
grant Aqua Edge.

Seating triggers a mechanical catch, engraved energy chase and an elemental
burst. Blade effects attach to authored per-frame guard and sword coordinates:
branching Nature filaments, Water ribbons, Fire embers or Ice glints. Unmastered
focuses stay tentative, failed casts sputter, and Aether Edge uses neutral
violet-white energy. Its eight-drawing strike bank is sampled within a two-second sequence, with
contact aligned to damage at one second. A brief four-drawing adjustment gesture handles
focus changes without altering body proportions.

The last settled focus survives encounters and save/load. Water is the default
for new and legacy saves, matching Mira’s gift presentation. Pause, focus loss,
resize, dialogue and results cancel unfinished gestures safely. Reduced Motion
retains gem identification and immediate visual seating while suppressing
optional motion and bursts.

See the [gear combat review](reviews/caelan_gear/README.md) for production MQ02
and four-focus animation previews.

## Choreographed actions

Caelan’s Attack runs through preparation, approach, planting, strike,
follow-through, a retreating hop and landing. Aether Edge adds a sword-focused
channeling gesture before its dash. Aether Dart gathers at the current hand or
blade anchor, releases at 0.75 seconds, lands at 1.10 and recovers by 1.60.
Armed and unarmed actions use separate authored whole-body drawings, preserving
body proportions and a shared floor anchor. Contact positions derive from the
actual sword-tip or fist reach against the Bat or Tusker silhouette.

`assets/combat/caelan_choreography.json` owns phase, pose, movement, elevation,
camera and impact timing. Only Caelan’s canonical actions receive these timing
profiles; other actors and custom action fixtures keep their defined timings.
All ATB remains paused through the complete action, including the return and
landing. A lethal hit finishes recovery before victory. Discovery checkpoints
remain at the successful Edge’s authoritative impact. Rivet’s Haste still
expires after eight completed bot actions, independent of animation duration.

The painted battlefield, sprites and effects receive one restrained camera
transform (up to 4% zoom); status columns and commands stay fixed. Ground
shadows follow floor positions beneath airborne sprites. Reduced Motion keeps
camera and staging steady while retaining action drawings and contact timing.

Impact events drive Bat wing recoil, Tusker head/shoulder recoil, Caelan’s hurt
recovery and guarded bracing, independently of damage-number lifetimes. Exact
impact age is carried through coarse frames. Small departure/landing dust and
short cues from existing licensed recordings accompany movement. No new dodge
probability or skill unlock is introduced by this presentation pass.

Review the [action and MQ02 previews](reviews/caelan_choreography/README.md).

Mira's [combat redraw](reviews/mira_redraw/README.md) adds 42 whole-body drawings
with stable floor registration, two-handed aim/recoil, controller handling and
separate guarded-impact recovery. Bolt Shot releases from its authored muzzle
at 0.28 seconds and keeps its 0.40-second damage impact and 0.80-second duration.
Overclock retains its 0.50-second application and 0.90-second duration. See
[Mira's combat presentation](MIRA_BOTS.md#combat-presentation).

## Caelan's initial actions

| Action | Effect | MP | Duration / impact |
| --- | --- | ---: | --- |
| Attack | Physical damage, potency 1 | 0 | 1.40 / 0.72 seconds |
| Guard | Halve the next incoming action | 0 | 0.60 / 0.20 seconds |
| Flee | Leave this test encounter safely | 0 | 0.70 / 0.35 seconds |
| Aether Dart | Magical damage, potency 2; requires its learned unlock | 4 | 1.60 / 1.10 seconds |
| Aether Edge | Immediate physical sword strike plus non-elemental Mag component; requires learned skill and equipped weapon | 4 | 2.00 / 1.00 seconds |

Caelan is a Spellblade. Aether Edge is his only learned starter skill and appears under Skills after its MQ02 discovery. Before he has a weapon, Skills is greyed out with **Requires a weapon**. The direct strike combines physical potency 1 and Mag potency 0.5, sharing one variance roll and one per-hit cap. It does not enchant future attacks or grant charges. See [character dictionaries and weapon unlocks](CHARACTER_ABILITIES.md).

Guard consumes a turn and remains until the next incoming action resolves.
Flee is guaranteed in this first encounter. Entering combat grants no spells or
learned unlocks. Other catalog abilities will receive battle implementations in
later passes; their ownership and descriptions are preserved.

This slice uses the [approved per-hit damage backend](DAMAGE_FORMULA.md), with
independent 95–105% variance from the battle's own RNG. Attack accuracy is
currently guaranteed and critical hits are disabled while those probability
rules await design. No damage-limit break is granted by the encounter.

## Millrace tutorial

The Ridgeback Tusker has **700 HP, Str 12, Def 18 and Speed 8**. The revised lesson opens with a separate visible charge preparation, then gives Caelan a real Guard opportunity. After the guided opening it resumes normal tusk strikes, preparation and charge actions. Guard halves the next incoming hit and survives a harmless preparation turn.

Mira has HP 300, MP 30, Str 20, Mag 12, Spr 12, Def 18, M. Def 14, Speed 12, Acc 16, Eva 12 and Lck 10. Bolt Shot uses potency 0.75. Rivet unfolds automatically with empty ATB and autonomously uses Piston Jab at potency 1, drawing strength from Mira. The enemy’s increased health and reduced strength give the new teaching turns room while retaining the damage backend’s 95–105% variance. No hidden minimum-HP invulnerability holds the creature alive.

### Guided opening

The battle model’s `spellblade_tutorial=True` enables stages `opening → guard → charge → first_edge → second_edge → complete`. The armed, still-learning Caelan is the guided actor:

1. The visible charge tell leads to Guard and actual guarded charge resolution.
2. His first Skills turn offers **Nature Edge**, **Aqua Edge** and **Flame Edge**. Any selection fails, spending ATB but no MP.
3. Mira’s hurried instruction follows the failed resolution. On Caelan’s **next full ATB**, any elemental choice resolves as direct **Aether Edge**.
4. At the second strike’s impact, `aether_edge_discovered` becomes true, the permanent technique is available in the battle and the temporary attempts disappear. Normal party commands resume.

Back, submenu changes or unacknowledged prose do not advance a lesson. Actor switching and Flee are disabled only during this introductory sequence. Mira automatically covers with Guard. Rivet remains autonomous but takes at most three Piston Jab actions during the bounded lesson; its gauge is preserved and ordinary behavior resumes afterward. This gives the allies useful contributions without allowing their damage to skip the required beats. Existing non-Spellblade/legacy encounters keep their ordinary tutorial behavior.

The scene uses speaker-labelled, player-paced instruction with brief interface hints. All gauges, action clocks and bot clocks stop for those lines and player decisions. Acknowledgement input cannot also commit a command. Model stages advance on resolved actions, not page counts or menu visits. The first-weapon gift and Aether Edge discovery have distinct persistence: a gifted weapon does not learn the technique early, and a recorded discovery is not repeated on withdrawal/retry.

If optional encounters leave the pending-training Caelan below `min(80, max HP)` HP or 4 MP, the pre-battle `tutorial_preparation` exchange completes before entry and restores only those minimums. A normal first playthrough is unaffected. This ensures the required Guard and 4-MP discovery remain viable without inventing a rest choice or additional quest milestone.

After the introduction, Mira is player-controlled with Attack, Skills, Guard and Flee. Overclock costs 5 MP and one normal turn, giving Rivet Haste for eight completed bot actions at 1.5× final ATB fill rate. Recasting refreshes without stacking. Rivet has no HP bar, cannot be targeted, suspends while Mira is incapacitated and does not count toward party survival. See [Mira’s bot rules](MIRA_BOTS.md).

The battlefield looks south/southwest toward distant Eldenmere, with the river along the near left bank, reeds, roots and freshly broken timber. A visible tusker and damaged tree mark the actual upstream approach. Mira carries her launcher from the workshop, secures it during intake work and retrieves it for the return. Caelan’s blade is sheathed on the walking route and used as the blue Water focus for the later isolated-pocket spell. The spell does not unlock Aqua Edge.

Victory grants one Aether Emerald once on Spoils, and commits
the cleared trail with remaining resources before its Continue opens the linear aftermath. The intake remains
blocked until the existing repair. If Mira wins while Caelan is incapacitated,
first aid restores him to 25% maximum HP before the recovery exchange. Flee
returns to the safe approach without rewards or encounter completion. Defeat
returns there with full Caelan HP and pre-battle MP for a viable retry.
Interrupted battles save the unfinished encounter at the safe approach. Party
resources resume from the entry checkpoint; partial ATB, action damage and the
dialogue cursor are not serialized. Older completed
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

Spoils awards the encounter's actual item drops on entry. The Bat and MQ02's
Tusker each grant one Aether Emerald, subject to inventory capacity. The screen
shows authoritative received amounts, and Continue becomes available after the
award checkpoint succeeds. A failed grant or save leaves a Retry action on
Spoils. Receipts prevent duplicate rewards even when a capped inventory receives
no additional items.

The standalone [traditional leveling foundation](LEVELING.md) and
[enemy archetype catalogue](ENEMY_ARCHETYPES.md) define the approved XP and growth
curves. Combat XP distribution remains pending its eligibility and recovery
policies; these encounters do not yet award traditional XP.

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

Caelan retains his unarmed baseline animation bank, while the MQ02 gearblade adds its armed/focus presentation and direct Aether Edge action. Idle, attack, casting, guard, hurt, victory and kneeling defeat states remain supported. The Bat has flight, bite, gust, hurt and descending defeat states.
Each actor has sixteen distinct transparent native frames. Contact and casting
poses cover the corresponding action's impact time. The original generated
sheets and extraction-only exporter are retained in
[`assets/source/combat`](../assets/source/combat) and
[`tools/build_combat_assets.py`](../tools/build_combat_assets.py).

Run `python tools/capture_combat.py` for the reproducible temporary-journey
preview. No ordinary journey or settings file is used by the capture.
