# Mira and the mill quest

`CH01_MQ02` begins after MQ01's stopped-wheel exchange. Its available marker points
to Mira at her existing outdoor workbench. Finishing the reunion accepts the
quest and lets the same actor accompany Caelan.

The complete route is workbench, mill diagnosis, upstream intake, pressure
relief, a small successful spell, encouragement, cooperative repair, verification
of the working mill, and Halden's closing exchange. The quest is noncombat and
has no timer, casting roll or resource charge.

## Playing through

Speak with Mira after MQ01. Inspect the mill mechanism and its race, then finish
the diagnosis conversation. Take the north road to the end of the map and use **E** to continue to the upper millrace. Inspect the limb
jammed across its intake screen. Mira sets the bypass to unload the mechanism
while Caelan stands clear in his normal idle stance. Once the pressure is off, clear the still water trapped in the inspection recess with
Caelan's modest spell. Only the inspection pocket clears at this point; the
limb and jammed screen stay in place until the physical repair. Finish the
exchange with Mira, grip the visible haul rope while she operates the repair
lever, and return to see the mill working. Finish the final exchange with
Halden and Mira to complete the quest.

The inspection pocket is a smaller magical task than pushing back the Venns'
flowing channel. The brief blue effect accompanies actual movement of existing
water into a nearby drain. The main obstruction is removed using tools and
leverage. The whole stream is never held back, created or magically lifted.

The encouragement exchange branches on `venn_visit.magicks_failed`. A player
who witnessed that failure hears Caelan's pleasure mixed with disappointment
and Mira's grounded encouragement. A player who chose tools receives a short
exchange about the success without an invented previous attempt.

## Finding the interactions

The town trail prompt sits at the northern road boundary, beyond the terrace stairs. The return prompt sits at the southern end of the upper millrace road. Both arrivals leave Caelan and Mira on clear ground outside the reverse prompt.

Inspect the mechanism beside the visible wheel and the millrace beside its channel. At the intake, approach the visible screen, bypass handle, water recess and repair lever; the **E** hint appears beside each object. After repairs, inspect the same wheel, then speak with the actual Halden and Mira nearby. Recruitment remains beside Mira at her outdoor workbench; encouragement follows Mira rather than an abandoned spell position.

Object interactions measure the gap between Caelan’s ground footprint and the object’s visible bounds, within 20 native pixels. The wheel reads its approved artwork metadata; intake controls read their rendered alpha bounds. Work stations are separate from interaction areas: Caelan walks around solid props into the existing action positions, preserving Mira’s hand contacts and the rope alignment. The corrected layout and both trail endpoints are reproduced by `tools/build_mill_quest.py`.

## Ownership

`mill_quest.py` owns quest staging, accompaniment, physical actions and durable
milestones. `assets/story/mill/scene.json` holds the spoken lines. The narrative
script is [CH01_MQ02](narrative/game_01/CH01_MQ02.md).

Mira's existing bench actor, directional walking art, portrait and workshop are
reused. Her bench-work fitting stays at the workbench while she accompanies
Caelan. Her blocker follows her actual position, and a following Mira yields
rather than becoming a wall at a door or narrow path. Halden is likewise the
existing actor from MQ01, moved to an explicit resolution station.

The upstream area uses the existing world loader and a reversible exterior link.
Its walking banks, channel and intake collision remain consistent while repair
props change state. The small spell uses the reviewed standing Caelan silhouette;
his head, hips, legs and boots retain their idle registration. Mira's supporting
and repair actions remain physically connected to the mechanism.

A single durable mill-restored fact controls the repaired intake, adequate race
flow, turning wheel and map description. The MQ01 conclusion's stopped-wheel
rule yields to that restoration. The main stream continues moving throughout.

## Objectives and durable milestones

| Objective | Completed by |
| --- | --- |
| `meet_mira` | Reading the reunion and accepting MQ02 |
| `diagnose_mill` | Reading both inspections and the diagnosis |
| `reach_intake` | Reading the upstream intake inspection |
| `prepare_intake` | Completing the bypass action |
| `small_spell` | Completing the successful water movement |
| `repair_intake` | Completing the cooperative lever repair |
| `verify_mill` | Observing the working mill and finishing its exchange |
| `report` | Finishing the closing exchange with Halden and Mira |

The optional version-one `mill_quest` journey record stores `inspected` (from
`mechanism`, `race`, `intake`) and the boolean facts `prepared`, `spell_done`,
`encouraged`, `restored`, `verified` and `resolved`. Quest state and these facts
are validated together. Transient poses, dialogue pointers, movement paths and
action clocks are rebuilt safely rather than serialized.

The successful spell is checkpointed before the encouragement. Leaving that
exchange unread preserves it without replaying the spell. Completed repairs
stay repaired while the player travels or reloads. Interrupted actions resume
from a safe unfinished stage. Pause and inventory freeze action clocks; ordinary
dialogue remains live and cancelable. New Game resets Mira and all mill facts.

Older saves at the available Mira handoff remain valid. Earlier placeholder
MQ02 objective records require explicit migration when expanding the objective
list; they must not become invented completed repairs. A saved upstream scene
is accepted as a valid exterior location.

## Verification and review

Gameplay verification covers the complete route, both Venn histories,
Mira's single-actor identity and work fitting, scene transfers, canceled speech,
interrupted actions, saved checkpoints, older saves, and visible mill
restoration. Pose checks compare actual source pixels and idle registration;
visual review also checks tool contact and the moving water in the real scene.

The runtime review should show the small success and encouragement close up,
as well as the full repair route and the working mill afterward. Reaching a
location or displaying a blue spark alone is insufficient evidence of a
completed task.

See the [interaction placement audit and native scene previews](reviews/mill_triggers/README.md) for the corrected road ends, object approaches and real-input route verification.
