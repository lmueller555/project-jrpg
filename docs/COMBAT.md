# Wait-ATB combat

MQ02 introduces combat on the riverbank north of Eldenmere. Caelan and Mira
fight a Ridgeback Tusker together before inspecting the blocked mill intake.
Mira is a player-controlled Engineer with a wearable arm rig, her own
attributes, commands, HP/MP and ATB. Her rig uses six allocated power units. Mira gives Caelan his gear-and-gem sword before departure. The warning, encounter and linear aftermath lead into his smaller sword-focused water spell and the mechanical repair.

The [arm-rig combat guide](MIRA_RIG_COMBAT.md) documents her current techniques,
power requirements, barriers and save behavior.

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
[initial combat implementation preview](reviews/mira_rig_continuity/README.md).

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
reloads at the safe arrival and restarts without granting progress. A Flee return waits for an explicit retry or a new area entry. Party defeat
opens Game Over without changing recovery saves. Completed and
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
See the [actual scene and transition review](reviews/mira_rig_continuity/README.md).

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
her live six-unit Weapons/Protection/Support allocation console. Apply commits
a complete configuration; only applied power enables her techniques. Panel height follows measured text
and the wheel’s usable area; larger text keeps its configured size. Long
command labels wrap and command selection scrolls to remain visible. Contextual
skill details appear immediately above the panel.

At standard text size in 960×640 or 1440×960, the three-character panel is
102 logical pixels tall, down from 128, while Caelan's gear stays 48×48 logical
pixels. Accessible text keeps its configured size; at the smallest window with
150% text, the panel grows to fit and the party stagger compresses to keep every
sprite visible. See the [compact UI comparison](reviews/mira_rig_continuity/README.md).

Mira uses her [wearable arm rig](MIRA_RIG_COMBAT.md), her own ATB and MP, and the live power-routing console. Her equipment does not add a separate combatant.

| Input | Action |
| --- | --- |
| Click a command | Open Skills or commit an action for the selected ready character |
| Click a ready character’s status / Tab | Select another ready party member |
| Arrows + Enter/Space | Select and commit a command |
| Drag Caelan’s gear while editable | Rotate a gem toward the fixed north catch; release to seat it |
| Hover the editable gear | All units’ ATB charges at 25% of its normal rate |
| G, then Left/Right and Enter/Space while editable | Focus the gear, rotate and seat a gem with the keyboard |
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

Mira’s gift installs only the Blue Water gem in the wheel; its other sockets
are visibly empty and cannot be selected. Owned gems and the settled focus are
separate saved facts. The fixed catch at twelve o’clock determines the focus. A short snap confirms seating; gear
rotation consumes no turn, ATB or MP. Caelan can adjust it only during his
charging window, as defined below. His last settled gem remains fixed while
ready, selecting a command/target and performing his action.

Hover slows charging for all party members and enemies only while the gear is
editable. A locked gear cannot activate slowdown. Ready decisions pause all
gauges. Action animation, impact and audio clocks retain their normal speed.

### Charging windows for character interactables

The combat model owns one timing rule for Caelan's gear and Mira's power
routing: a living active character can edit configuration only while their own
ATB is below full and battle time is actually charging. This also defines the
timing contract for future character interactables.

| Battle state | Interactable treatment |
| --- | --- |
| Gauges advancing; character's ATB below full | Editable, subject to equipment and guided-lesson restrictions. |
| Character's ATB reaches full, including waiting for selection | Lock the last committed configuration. |
| Any character's ready command or target menu | Both controls remain locked because gauges are paused. |
| Any action animation, including Vespermaw's free channeling | Both controls remain locked. Resetting ATB at action start does not reopen them. |
| Character finishes their action and charging resumes | Reopen their control if alive and their ATB remains below full. |
| KO, pause, focus loss, or result | Disable input; retain the committed configuration. |

The locked controls remain visible with subdued interaction highlights and a
small lock indicator. Mouse, keyboard and delayed configuration callbacks obey
the same model rule. Cancelling a command or changing the selected ready party
member does not reopen a charging window.

At a window boundary, discard an unfinished gear drag, keyboard preview,
uncompleted seating animation or unconfirmed routing draft and restore the
last committed gem/allocation. No edit is deferred to the next turn. A completed
edit before the boundary stays committed; if seating completion and ATB-full
occur at the same instant, the lock wins. Pending interaction animation never
delays readiness or a combat command. Coarse and fine frame updates use the
same charging and transfer boundaries.

The Blue-gem lessons explain preparation during charging, before command
selection. Their ready menus do not bypass this rule. The gift's already seated
Blue gem remains available for the guided Aqua attempts.

Aether Edge works with every owned focus and remains non-elemental. Aqua Edge
requires the Blue gem, an equipped blade and its learned unlock. Selecting or
owning a gem never teaches its skill. MQ02 exposes only the experimental Aqua
attempt: it fails, then inadvertently releases Aether Edge automatically. The
later water utility spell does not grant Aqua Edge. The first Sanctuary cave
encounter teaches Aqua Edge separately. Optional level-five Embravyr and
Nivareth encounters then award the Red/Flame Edge and White/Ice Edge unlocks
in either order. These still use one gear with one selected focus. Aether
materials in inventory do not install gems.

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

The [gear combat review](reviews/mira_rig_continuity/README.md) retains historical MQ02
and four-focus previews from before Blue-only ownership. See
[Caelan’s opening progression](CAELAN_AQUA_PROGRESSION.md) for current rules.

## Choreographed actions

Caelan’s Attack runs through preparation, approach, planting, strike,
follow-through, a retreating hop and landing. Aether Edge adds a sword-focused
channeling gesture before its dash. Aether Dart gathers at the current hand or
blade anchor, releases at 0.75 seconds, lands at 1.10 and recovers by 1.60.
Armed and unarmed actions use separate authored whole-body drawings, preserving
body proportions and a shared floor anchor. Contact positions derive from the
actual sword-tip or fist reach against the Bat or Tusker silhouette.

Mira uses her [wearable arm rig](MIRA_RIG_COMBAT.md), her own ATB and MP, and the live power-routing console. Her equipment does not add a separate combatant.

The painted battlefield, sprites and effects receive one restrained camera
transform (up to 4% zoom); status columns and commands stay fixed. Ground
shadows follow floor positions beneath airborne sprites. Reduced Motion keeps
camera and staging steady while retaining action drawings and contact timing.

Impact events drive Bat wing recoil, Tusker head/shoulder recoil, Caelan’s hurt
recovery and guarded bracing, independently of damage-number lifetimes. Exact
impact age is carried through coarse frames. Small departure/landing dust and
short cues from existing licensed recordings accompany movement. No new dodge
probability or skill unlock is introduced by this presentation pass.

Review the [action and MQ02 previews](reviews/mira_rig_continuity/README.md).

Mira's [wearable arm-rig art](MIRA_ARM_RIG_ART.md) supplies 82 whole-body drawings,
including eight-frame animations for each of her five live rig techniques.
Her revised base bank preserves stable floor registration, aim/recoil,
cuff activation and separate guarded-impact recovery. Bolt Shot releases from its authored muzzle
at 0.28 seconds and keeps its 0.40-second damage impact and 0.80-second duration.
Rig techniques resolve on their own registered contact frames. See
[the arm-rig review](reviews/mira_arm_rig/README.md) for the new artwork. The
live techniques and allocation rules are documented in [Mira rig combat](MIRA_RIG_COMBAT.md).

## Caelan's combat actions

| Action | Effect | MP | Duration / impact |
| --- | --- | ---: | --- |
| Attack | Physical damage, potency 1 | 0 | 1.40 / 0.72 seconds |
| Guard | Halve the next incoming action | 0 | 0.60 / 0.20 seconds |
| Flee | Leave this test encounter safely | 0 | 0.70 / 0.35 seconds |
| Aether Dart | Magical damage, potency 2; requires its learned unlock | 4 | 1.60 / 1.10 seconds |
| Aether Edge | Immediate physical sword strike plus non-elemental Mag component; requires learned skill and equipped weapon | 4 | 2.00 / 1.00 seconds |
| Aqua Edge | Physical sword strike plus Water Mag component; requires learned skill, equipped weapon and Blue gem | Normally 4; introductory battle 0 | 2.00 / 1.00 seconds |
| Flame Edge | Physical sword strike plus Fire Mag component; requires Red gem and its learned unlock | Normally 4 | 2.00 / 1.00 seconds |
| Ice Edge | Physical sword strike plus Ice Mag component; requires White gem and its learned unlock | Normally 4 | 2.00 / 1.00 seconds |

All already-learned elemental Edges cost 0 MP throughout the two optional
elemental teaching encounters and their retries. Aether Edge and Mira’s rig techniques retain their ordinary MP costs

Caelan is a Spellblade. Aether Edge is his only learned starter skill and appears under Skills after its MQ02 discovery. Before he has a weapon, Skills is greyed out with **Requires a weapon**. The direct strike combines physical potency 1 and Mag potency 0.5, sharing one variance roll and one per-hit cap. It does not enchant future attacks or grant charges. See [character dictionaries and weapon unlocks](CHARACTER_ABILITIES.md).

Guard consumes a turn and remains until the next incoming action resolves.
Flee is guaranteed in this first encounter. Entering combat grants no spells or
learned unlocks. Other catalog abilities will receive battle implementations in
later passes; their ownership and descriptions are preserved.

This slice uses the [approved per-hit damage backend](DAMAGE_FORMULA.md), with
independent 95–105% variance from the battle's own RNG. Attack accuracy is
currently guaranteed and critical hits are disabled while those probability
rules await design. No damage-limit break is granted by the encounter.

## Lucan's cave guest combat

Lucan joins the Sanctuary rescue as a **level-five guest**. He is manually
controlled through Attack, Skills, Items, Guard and Flee; encounter-specific
Flee restrictions still apply. He has no combat interactable during this guest
appearance. His full Armsmaster arsenal and interactable remain later work for
his permanent recruitment.

| Skill | MP | Effect |
| --- | ---: | --- |
| Inspire | 5 | Raises every living active party member's Attack (`str`) by 50% for five of that recipient's turns. |
| Bolster | 5 | Raises every living active party member's Defense (`def`) by 50% for five of that recipient's turns. |
| Provoke | 8 | Directs each susceptible normal enemy's single-target hostile actions toward Lucan for five of that enemy's turns. |

Inspire and Bolster coexist, refresh without stacking, and apply battle-only
modifiers rather than changing saved base stats. The casting action does not
immediately consume the caster's freshly applied buff turn. Effective Attack
and Defense use integer rounding down and respect the existing stat cap.
KO clears the affected character's buffs; battle results clear all temporary
buff and Provoke state.

Provoke does not affect minibosses or bosses and does not redirect party-wide
attacks or self-buffs. Enemies can still prepare attacks; a prepared
single-target attack follows the normal target warning and response guarantee
when its target changes. Each affected enemy tracks its own duration; Lucan
becoming incapacitated ends forced targeting. Recasting refreshes the effect
rather than stacking it. If every enemy is immune, the command is rejected
without MP or ATB cost. In a mixed formation, it affects susceptible normal
enemies and reports the others' immunity.

Lucan receives **no combat EXP while he is this guest**, even when alive at
victory. Caelan and Mira retain their normal full-survivor awards. Buffs and
Provoke are encounter state and do not persist into the next fight.

## Millrace tutorial

The Ridgeback Tusker uses the level-one **Brute boss** template: **270 HP, Str 13, Def 14 and Speed 9**, with no extra species or tier stat multipliers. It grants **240 EXP** to each surviving active character. The revised lesson opens with a separate visible charge preparation, then gives Caelan a real Guard opportunity. After the guided opening it resumes normal tusk strikes, preparation and charge actions. Guard halves the next incoming hit and survives a harmless preparation turn.

Mira starts with HP 150, MP 30 and 10 in every other rating, matching her level-one growth profile. Bolt Shot uses potency 1.0. Her five rig techniques spend her own ATB and MP; no autonomous companion supplies extra turns. The enemy’s increased health and reduced strength give the new teaching turns room while retaining the damage backend’s 95–105% variance. No hidden minimum-HP invulnerability holds the creature alive.

### Guided opening

The battle model’s `spellblade_tutorial=True` enables the Guard, failed-Aqua and automatic-Aether sequence. The armed, still-learning Caelan is the guided actor:

1. The visible charge tell leads to Guard and actual guarded charge resolution.
2. His first Skills turn offers only **Aqua Edge**. That attempt sputters without an MP penalty.
3. Mira’s hurried instruction follows the failed resolution. The same attempted technique inadvertently follows through as direct **Aether Edge**, without another menu selection.
4. At its impact, `aether_edge_discovered` becomes true. The 4-MP strike is learned and normal party commands resume. Aqua Edge remains unlearned until the cave.

Back, submenu changes or unacknowledged prose do not advance a lesson. Actor switching and Flee are disabled only during this introductory sequence. Mira automatically covers with Guard. Her rig is unavailable during the guided steps and becomes usable when ordinary party commands resume. Existing non-Spellblade/legacy encounters keep their ordinary tutorial behavior.

The scene uses speaker-labelled, player-paced instruction with brief interface hints. All gauges and action clocks stop for those lines and player decisions. Acknowledgement input cannot also commit a command. Model stages advance on resolved actions, not page counts or menu visits. The first-weapon gift and Aether Edge discovery have distinct persistence: a gifted weapon does not learn the technique early, and a recorded discovery is not repeated on withdrawal/retry.

If optional encounters leave the pending-training Caelan below `min(80, max HP)` HP or 4 MP, the pre-battle `tutorial_preparation` exchange completes before entry and restores only those minimums. A normal first playthrough is unaffected. This ensures the required Guard and 4-MP discovery remain viable without inventing a rest choice or additional quest milestone.

After the introduction, Mira is player-controlled with Attack, Skills, Items, Guard and Flee. Her [rig techniques](MIRA_RIG_COMBAT.md) provide physical and Electric offense, a personal barrier, and ally healing. Reconfiguration is free; every technique spends her normal turn and its listed MP.

The battlefield looks south/southwest toward distant Eldenmere, with the river along the near left bank, reeds, roots and freshly broken timber. A visible tusker and damaged tree mark the actual upstream approach. Mira powers her worn arm rig for the outing, safes its emitter during intake work and reactivates the brace for the return. Caelan’s blade is sheathed on the walking route and used as the blue Water focus for the later isolated-pocket spell. The spell does not unlock Aqua Edge.

Victory grants one Aether Emerald once on Spoils, and commits
the cleared trail with remaining resources before its Continue opens the linear aftermath. The intake remains
blocked until the existing repair. If Mira wins while Caelan is incapacitated,
first aid restores him to 25% maximum HP before the recovery exchange. Flee
returns to the safe approach without rewards or encounter completion. Party defeat
opens Game Over and offers manual-save or autosave loading without healing
or overwriting recovery files.
Interrupted battles save the unfinished encounter at the safe approach. Party
resources resume from the entry checkpoint; partial ATB, action damage and the
dialogue cursor are not serialized. Older completed
intake/repair saves preserve their progress through an explicit legacy bypass
and receive no invented battle or reward.

## Sanctuary cave Aqua lesson

The first cave entrance with Mira’s Blade presents a short resonance scene:
concentrated ambient aether lights its Blue gem and suggests that Caelan may be
able to focus Aqua Edge here. The scene is acknowledged and saved separately
from learning the technique.

The first distance-triggered cave encounter is always **two level-two Cave
Bats**, retaining its exact formation, battlefield and seed in a saved ticket.
A guided opening gives conscious Caelan Skills → Aqua Edge, while allies,
Mira and enemy actions wait for the cast. Aqua Edge costs **0 MP throughout
this introductory battle and its retries**, so no MP preparation or healing
detour is required. At impact Aqua Edge is learned and checkpointed with
current party resources; normal ATB then
resumes. After clearing the encounter, ordinary casts cost 4 MP in every area,
with the two optional elemental teaching encounters as a later 0-MP exception.

Aqua Edge uses the same physical potency 1 and magical potency 0.5 as Aether
Edge, but only its magical component is **Water-aligned**. That component uses
the target’s full 0–200% Water response, or heals the matching elemental target
for its neutral-affinity value when absorbed. Its physical component remains
physical. Guard and the existing recovery vulnerability continue to apply
through the shared hit resolution. Elemental values are not revealed in the HUD.

The introductory battle is cleared only by victory and its ordinary once-only
award. Withdrawal preserves its exact ticket for retry, without
unlearning a successful discovery. Defeat opens Game Over; loading restores
the chosen snapshot, including its discovery state. A deferred retry allows preparation and
travel instead of immediately restarting combat. Caelan must be conscious,
active and carrying the blade; no MP minimum is imposed. The first lesson takes
priority over the miniboss, and normal weighted encounters begin after it clears.
Older journeys with prior cave encounters migrate without replaying the lesson.
See [save and migration details](CAELAN_AQUA_PROGRESSION.md).

## Optional elemental chambers

Embravyr and Nivareth are fixed level-five formations of Fire and Ice Aether,
encountered independently in the continuous Embervein and Stillfrost branches.
Each has its own Approach / Party / Leave offer, live introduction and animated
combat field. Both permit Flee, preserving spent resources. Defeat restores
entry resources and offers Retry / Leave; unfinished entries preserve their
seed and party on Continue. Neither encounter is mandatory for Vespermaw.

A marked Furnace Lunge or Frostspire Thrust guarantees the target an action
opportunity before impact. The following recovery exposes **+50% incoming
damage**; Vespermaw's post-Pounce exhaustion now uses that same multiplier.
The bonus begins at the heavy hit and ends before the next basic action, with
ordinary Guard and per-hit caps preserved. This does not implement Stagger.

Each victory guarantees its focus item, owned gem and learned Edge even if
Caelan is KO, while EXP still goes only to living active members. Installation
prose follows Spoils and waits for Caelan to recover. Its acknowledgment never
repeats rewards. See [complete combat, rewards and save rules](ELEMENTAL_CAVE_ENCOUNTERS.md).

## Vespermaw elemental channeling

The Echo Chamber boss starts in Fire and cycles **Fire → Ice → Water** after
every two completed boss actions, including preparation and recovery turns.
Before turns 3, 5, 7 and so on, a free 2.5-second channeling performance precedes
the scheduled action without spending another ATB gauge, MP payment or AI slot.
The new form commits at 1.65 seconds. Other actions and ATB progression wait for
the performance; a marked Pounce target and its response guarantee remain intact.

Fire is weak to Water, Ice to Fire, and Water to Ice, each at 200% damage.
Matching-element damage heals for 100%; other elements remain neutral. These
relationships are not disclosed by ordinary combat UI. Fur colors, distinct
ambient effects and the corresponding large red/white/blue wall crystal show
the current form without suggesting its counter. Confluence Roar uses that
form's element; the claw and pounce remain physical and Non-Elemental.

Optional gems are not an entry requirement. Physical/non-elemental damage can
finish the fight in every form. Continue and Retry rebuild the captured entry
in Fire with zero completed boss turns. See the [Bestiary](BESTIARY.md#vespermaw)
and [art guide](VESPERMAW_COMBAT_ART.md) for profiles and presentation.

## Cave Bat and the Bestiary

The [Bestiary](BESTIARY.md) stores fixed authored encounters and computed
species definitions in one dictionary. `BattleModel.from_bestiary()` resolves a
Cave Bat at level 2 or 3 with its approved Hybrid/species growth, XP metadata,
namespaced Bite/Gust actions, living-party target cycle and existing Bat art.
Its 5 MP pays for two Gusts before free Bite fallback. The factory supports
isolated combat without placing encounters or awarding live XP.

The Cave Bat is distinct from the fixed test Bat below and appears in the
continuous Sanctuary cave. Its complete elemental profile specifies
Non-Elemental identity, Fire damage received at 200% and all other types at
100%, with no absorption. Aqua Edge now reads its Water response during actual
combat. Stagger remains future work; [supply drop tables](CONSUMABLES.md) now feed victory loot.

The Bestiary's [elemental design](BESTIARY.md#elemental-identity-and-relationships)
uses Non-Elemental, Fire, Electric, Water, Ice, Nature, Wind, Holy and Ground.
Species store all nine damage percentages and matching-element absorption;
unaligned creatures do not absorb Non-Elemental attacks. These internal data
are hidden in ordinary combat. A creature's appearance, name, habitat and
behavior should offer consistent clues. Edran's planned Study ability will be
one of the limited ways to reveal the data directly. Elemental Edges apply the
stored matching magical response, while Study and automatic HUD affinity labels remain
unimplemented.

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

The [traditional leveling foundation](LEVELING.md) and
[enemy archetype catalogue](ENEMY_ARCHETYPES.md) define the XP and growth
curves. Each living EXP-eligible active combatant receives the full encounter
EXP; level-ups do not restore HP or MP. Lucan's fixed-level cave guest receives
no combat EXP, while Caelan and Mira retain their normal awards.

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
safe return. Defeat opens Game Over and preserves all existing saves. See
[save slots and autosaves](SAVE_SYSTEM.md). Neither Flee nor
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
  [`bestiary.json`](../assets/combat/bestiary.json): validated action/enemy data.
- [`assets/combat/encounter.json`](../assets/combat/encounter.json): world placement.

Caelan retains his unarmed baseline animation bank, while the MQ02 gearblade adds its armed/focus presentation and direct Aether Edge action. Idle, attack, casting, guard, hurt, victory and kneeling defeat states remain supported. The Bat has flight, bite, gust, hurt and descending defeat states.
Each actor has sixteen distinct transparent native frames. Contact and casting
poses cover the corresponding action's impact time. The original generated
sheets and extraction-only exporter are retained in
[`assets/source/combat`](../assets/source/combat) and
[`tools/build_combat_assets.py`](../tools/build_combat_assets.py).

Run `python tools/capture_combat.py` for the reproducible temporary-journey
preview. No ordinary journey or settings file is used by the capture.
