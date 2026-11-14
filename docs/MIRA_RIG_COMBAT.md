# Mira: wearable arm-rig combat

Sprite construction, proportions, registration and visual review follow the
[global sprite and animation standard](SPRITE_ANIMATION_STANDARD.md). The
implementation details below describe this asset/system; older construction
methods are retained for reproducibility, not as new authoring instructions.

Mira is an **Engineer** wearing an external arm augmentation over her intact
limb. Her forearm emitter, projector and engineering tools use her own stats,
MP and ATB turn. She has no autonomous combat companion or second action queue.
The [phase-one artwork](MIRA_ARM_RIG_ART.md) supplies the complete pose bank;
this phase connects those drawings to authoritative battle actions.

## Power allocation

The rig has six units split among **Weapons**, **Protection** and **Support**.
A new journey begins at **2 / 2 / 2**. Allocation is configuration, not ammunition:
using a technique does not remove units. Channels do not grant passive stat
bonuses in this first gameplay version. Requirements are minimum values.

The combat panel maintains a draft. Minus releases a unit; plus assigns a free
unit. Apply commits only nonnegative integer allocations totaling exactly six.
Cancel discards the draft. Only the applied allocation enables techniques.
Reconfiguration costs no MP or turn, and does not grant/reset ATB. It is
available only while Mira is alive, her own ATB is below full and battle time
is charging. Once her gauge fills, her last applied allocation stays locked
through command/target selection and her completed action. ATB resets at action
start, but the rig does not reopen until the action finishes and charging
resumes. Any actor's ready menu or action animation pauses the editing window,
including Vespermaw's free elemental transformation. Guided lessons, KO, pause,
focus loss and results also disable it. See the shared
[charging-window rule](COMBAT.md#charging-windows-for-character-interactables).

If the window closes with an unconfirmed draft, discard it and display the last
applied allocation. A draft never applies automatically next turn. The panel
remains visible with dimmed controls and a small lock indicator; mouse,
keyboard and model callbacks enforce the same restriction. Valid configurations
committed before the cutoff retain their existing persistence behavior.

Use the panel's mouse controls, or **M** to focus it. Left/Right adjusts power,
Up/Down selects a channel and Enter applies a complete configuration. Tab
returns to ordinary command/party controls; Escape cancels a focused draft.
Unpowered skills remain visible with their exact current/required values.

## Starting actions

| Action | Minimum power | MP | Effect |
| --- | --- | ---: | --- |
| Bolt Shot | None | 0 | Basic physical attack; potency 1.0 |
| Charged Bolt | Weapons 3 | 3 | Single-target physical attack; potency 1.75 |
| Bulwark | Protection 3 | 3 | Self barrier: 25% of Mira's maximum HP, rounded down, minimum 1 |
| Repair Pulse | Support 3 | 4 | Heal one living active ally: floor(15% of recipient maximum HP) + twice Mira's Spirit |
| Impact Bolt | Weapons 2 / Protection 2 | 4 | Physical hit at potency 1.0 and self barrier: 10% maximum HP |
| Arc Discharge | Weapons 3 / Support 2 | 5 | Single-target Electric magical hit; potency 1.5 |

Each skill spends one normal Mira ATB turn and deducts MP at commitment. Known
skill, applied allocation, readiness, MP and target validity must all pass before
any resource changes. Cancelling or choosing an invalid recipient costs nothing.
Effects occur at the registered impact time, not when a menu entry is highlighted.

Physical actions use Mira's Strength against Defense; Arc Discharge uses Magick
against Magick Defense and the target's authored Electric relationship, including
absorption. No shared damage formula or character growth profile is changed.

Repair Pulse's nominal output caps at 9,999 and then clamps to missing HP.
It cannot target a KO/full-HP character, revive, restore MP or heal reserves
outside the combat lineup. Mira can heal herself. It uses the ally recipient
menu or a party-status click. It is initially combat-only; field healing remains
handled by consumables and rest locations.

## Barriers

Bulwark and Impact Bolt produce a battle-only pool on Mira. Existing damage
modifiers and Guard resolve first, then the barrier absorbs the resulting
physical or magical damage. Full absorption produces zero HP damage; the
landed-hit minimum is not reapplied afterward. Misses, immunity and healing
consume no barrier strength. Guard is consumed by a landed hit even when a
barrier absorbs all of its remaining damage.

A barrier lasts until Mira completes her **second subsequent action**. The
creating action does not immediately consume a duration turn. Her later attacks,
skills, items and Guard count; routing edits and other actors' actions do not.
Reapplication refreshes the duration and retains the stronger remaining pool,
never adding the pools. Impact Bolt grants its barrier even if its shot misses.
Changing away from Protection does not remove an existing barrier. KO and battle
end clear the pool and its duration.

The status UI shows the remaining barrier amount and turn count. Absorbed damage
and remaining HP damage have distinct feedback, while the visible projector
effect follows the same action clock as its actual application.

## Persistence and compatibility

The versioned `mira_rig` journey owner stores only the applied allocation. Drafts,
input focus, barriers and visual clocks are transient. Every battle receives a
copy of the entry allocation. Victory or withdrawal commits the final allocation
with party resources, consumed supplies and rewards. Failed transactions restore
the entry owner; retry does not repeat costs or grants. Defeat and an unfinished
battle Continue use the existing entry checkpoint and its allocation.

Version-four pending victories retain deterministic item offers, consumption,
EXP and receipts, and include rig before/after snapshots and bounded skill-use/
healing summaries. A bounded effective-entry HP/Spirit basis preserves the
healing strength used in battle, including temporary Spirit modifiers, without
substituting post-level-up stats. This allows a legitimate Repair Pulse victory to end with
HP above its entry value without accepting arbitrary resource increases. Continue
resumes the exact existing grant rather than replaying combat or rerolling loot.
Earlier version-one/two/three pending victories retain their original rules.
Future persistent equipment owners should derive and validate that modifier
basis alongside their own saves; this record does not add a general equipment
or temporary-modifier persistence system.

Recognized old starting bot-loadout data is normalized before journey validation.
New saves contain the rig owner and omit the retired loadout. Levels, EXP,
party/quest facts, gems, inventory and current resources are retained. New starting
techniques do not recruit Mira or make an unavailable/reserve character combat-ready.

## Tutorials and review

The Boar's Guard → failed Aqua Edge → Aether Edge lesson and the first cave Aqua
lesson retain their guided control. Mira's rig becomes available in charging
windows after their required steps; a ready menu is never an editing exception.
Combat guidance describes her direct engineering techniques.
Phase three completes the story dialogue, worn-rig exploration and cinematic art,
and retirement of the autonomous bot backend. See the
[continuity review](reviews/mira_rig_continuity/README.md).

The title Gallery's phase-one arm-rig study remains an isolated art sandbox.
Its local allocations and illustrative effects never change the durable rig.

See the [live combat review](reviews/mira_rig_combat/README.md) for actual selected
skills, resource changes, layout captures and a silent combat clip. The review
uses disposable, explicitly injured fixtures with shortened readiness, not a
claimed complete battle playthrough.
