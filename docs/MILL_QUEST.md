# Mira and the mill quest

MQ02 now ends with Caelan returning to help Serene and Tomas inside the
sanctuary dining room. Halden's acknowledged mill report records the repair
and releases Mira to her workshop, while the quest remains active. After the
homecoming conversation and actual cup-setting action finish, the existing
quest rewards settle once and [Aldric's arrival cinematic](REGENT_ARRIVAL.md)
plays. It introduces the relief caravan before the party appears at the lower
brook bridge in town, then returns control to Caelan in the same dining room.
The [regional story handoff](narrative/game_01/REGIONAL_SURGES.md) continues into
MQ03's relief, quarry and [covenant](world/SANCTUARY_COVENANT.md) discussion.
Serene's separate request to meet the visitors accepts MQ03.

`CH01_MQ02` begins after MQ01’s stopped-wheel exchange. Its available marker points to Mira at the existing outdoor workbench before the upper bridge. The revised request leads into her early birthday present for Caelan. Completing the presentation owns/equips the sword once, accepts the quest and records the meeting before the same Mira accompanies him.

The main route is now workshop request and gift, mill diagnosis, armed departure, the riverbank tutorial, linear aftermath, intake inspection, pressure relief, sword-focused water spell, encouragement, cooperative repair and gift thanks, working wheel, Halden’s resolution and the sanctuary homecoming. Dialogue supplies household/work context and the actual north-road directions; selective emotive cues use literal asterisks.

## The birthday presentation

Mira prepared the gift before the outing. A detailed workshop insert shows her presenting the blade, Caelan taking its weight, the gear guard and gems, his hand turning the ring and their reactions. Its grip stays fixed while a firm ring click selects a focus. Green is Nature, blue Water, red Fire and white Ice. The selected gem responds, but no elemental spell succeeds during this demonstration.

`mill_gift.py` owns this presentation, using the ordinary portrait-panel format and player-paced source text from `assets/story/mill/scene.json:gift`. The visual phases are `reveal`, `whole`, `handoff`, `gear` and `faces`; minimum authored movement totals approximately eighteen seconds in addition to reading time. Phase completion barriers prevent fast acknowledgements from skipping the handoff or selector demonstration. Pause/focus loss and Reduced Motion retain their normal presentation behavior.

The real item is `caelan_gearblade`, **Mira’s Blade**. Its inventory/first-weapon receipt is separate from learning Aether Edge: the gift leaves starter training pending. Reequipping cannot bypass that state. An interrupted unfinished scene can restart safely, while an owned gift is never granted twice. New Game clears ownership/training normally. Older already-active/completed journeys keep their route without a forced retroactive presentation.

## Playing through

Inspect the wheel and its channel with Mira nearby, then acknowledge the diagnosis and departure warning. Mira brings her spring-driven bolt launcher and folded four-legged bot Rivet. Caelan now brings the sheathed gearblade. Take the actual north road past the sanctuary steps and use the boundary prompt to enter the upper millrace.

At the safe arrival, the party stops and notices the damaged tree and ridgeback tusker. The camera pans to the creature, holds while they speak, then returns on Mira’s “Caelan, back towards me. Slowly” warning. Kindled Courage and the battle transition begin only after that returned shot settles and its dialogue is acknowledged.

The guided battle opening teaches **Guard first** against a visible charge. Caelan’s first Skills turn offers Nature Edge, Aqua Edge and Flame Edge; every choice fails, spending the turn without an MP penalty. Mira tells him to use the blade as a focus. On his **next full ATB**, any elemental selection produces direct, non-elemental **Aether Edge**. That discovery becomes his sole learned starter skill and releases ordinary battle controls. The three elemental options are temporary attempts, not learned abilities later removed.

A pending-training route arriving from optional Bat combat with fewer than `min(80, max HP)` HP or 4 MP first plays the short `tutorial_preparation` exchange. Its acknowledged callback raises only those resources to the lesson minimums and checkpoints before entry. Normal fresh-game resources are untouched; this adds no rest choice, time advance or objective and prevents the required discovery from being unaffordable.

During that short lesson, the game guides the active character and commands; Mira covers with Guard and Rivet contributes a bounded number of autonomous jabs. All gauges pause for dialogue and player decisions. After discovery, Mira is player-controlled and Rivet resumes normal autonomous behavior, including her starting Overclock. The [combat guide](COMBAT.md) records tuning and action details. A recorded discovery survives withdrawal/retry without repeating the gift or teaching scene.

Victory plays Triumphal Fanfare once, the victory banner and Spoils of Battle. Spoils settles the cleared encounter and reward once. Silence follows the fanfare until Continue returns to the world and starts the linear aftermath. There is no continue/rest choice. Unread aftermath remains available, and quitting during victory resumes Spoils without a duplicate grant. Defeat and withdrawal return to a viable approach rather than restoring the intake.

Mira checks Caelan after the fight. The first-aid variant only appears if he was incapacitated. Rivet folds away, and she secures the launcher beside the intake while using the bypass and tools. The water spell and physical repair remain Caelan and Mira’s work rather than a bot ability.

Inspect the lodged limb and the pressure holding it against the screen. Mira operates the bypass while Caelan stands clear. Once the main supply is isolated, he proposes moving the small pocket around the catch into its adjacent drain. Selecting the blue focus and using a stable sword-casting stance moves existing water and reveals the catch. This deterministic world action has no time limit, cast roll or MP charge; it does not unlock Aqua Edge or move the main current.

The encouragement follows actual success. Its saved Venn-failure branch lets Caelan be pleased while still wishing he had managed that earlier, heavier task. The direct-tools branch invents no failed spell. After acknowledgment, he grips the haul rope while Mira releases the catch and operates the lever. Only that physical repair removes the limb and restores the intake.

The first post-repair line preserves his held-rope beat; advancing beyond it releases the pose. The same follow-up then lets him thank Mira for bringing the gift early and agree to bring his book to the workshop. That is future intent, not a new appointment or practice objective. Return to inspect the working wheel, then speak with Halden and Mira. Their goodbye gives Caelan a spoken reason to return to the sanctuary and help with the remaining preparations. The mill report is saved separately from MQ02 completion; no arrival cinematic or quest reward starts there.

## Return to the sanctuary

After Halden's report, Mira returns to her workshop and Caelan walks home under
player control. The final objective directs him to Mother Serene at the
sanctuary. The existing Serene and Tomas actors are staged inside the dining
room before arrival, without exposing Aldric's party or enabling MQ03 early.
Caelan's earlier morning offer to help is remembered without suggesting he
forgot the tables: Tomas and Serene already took over that work.

`sanctuary_return` closes the mill outing and ends with the exact exchange:

- Tomas: “The tables are finished, we're just setting them if you can grab the cups.”
- Serene: “You could bring those clean ones over, if you have a moment.”
- Caelan: “Yep, on it.”

Caelan visibly collects, carries and places the clean cups in a short staged
action, using the existing character and prop art. `sanctuary_setting` introduces
the expected regent and moves Tomas's bow question here from MQ03. Both the
physical placement and Serene's final acknowledged thanks are required before
MQ02 can complete. Interrupted prose or movement cannot bypass that boundary.

The dining-room view holds and fades into the arrival. The audience sees
Aldric's approach while Caelan stays at the sanctuary, and the return preserves
his room and position. Speaking with Serene afterward accepts MQ03 through the
short welcome-visitors request rather than repeating the preparations.

## Finding the interactions

The town trail prompt sits at the northern road boundary, beyond the terrace stairs. The return prompt sits at the southern end of the upper millrace road. Both arrivals leave Caelan and Mira on clear ground outside the reverse prompt.

Inspect the mechanism beside the visible wheel and the millrace beside its channel. At the intake, approach the visible screen, bypass handle, water recess and repair lever; the **E** hint appears beside each object. After repairs, inspect the same wheel, then speak with the actual Halden and Mira nearby. The new final conversation is beside Serene inside the sanctuary dining room; matching coordinates outside cannot trigger it. The request and birthday presentation remain beside Mira at her outdoor workbench; encouragement follows Mira rather than an abandoned spell position.

Object interactions measure the gap between Caelan’s ground footprint and the object’s visible bounds, within 20 native pixels. The wheel reads its approved artwork metadata; intake controls read their rendered alpha bounds. Work stations are separate from interaction areas: Caelan walks around solid props into the existing action positions, preserving Mira’s hand contacts and the rope alignment. The corrected layout and both trail endpoints are reproduced by `tools/build_mill_quest.py`.

## Ownership

`mill_quest.py` owns quest staging, accompaniment, physical actions and durable
milestones. `assets/story/mill/scene.json` holds the current spoken lines. The
[MQ02 narrative script](narrative/game_01/CH01_MQ02.md) also records the arrival
handoff. `regent_arrival.py` owns that separate presentation and its saved
pending/seen checkpoint; it never repeats the mill's rewards.

Mira's existing bench actor, directional walking art, portrait and workshop are
reused. Her bench-work fitting stays at the workbench while she accompanies
Caelan. Her blocker follows her actual position, and a following Mira yields
rather than becoming a wall at a door or narrow path. Halden is likewise the
existing actor from MQ01, moved to an explicit resolution station.

The upstream area uses the existing world loader and a reversible exterior link.
Its walking banks, channel and intake collision remain consistent while repair
props change state. The small spell keeps Caelan’s stable stance and normal body proportions while using the gearblade’s blue focus; it does not stretch his limbs or move his planted boots unnaturally. Mira's supporting
and repair actions remain physically connected to the mechanism.

A single durable mill-restored fact controls the repaired intake, adequate race
flow, turning wheel and map description. The MQ01 conclusion's stopped-wheel
rule yields to that restoration. The main stream continues moving throughout.
The encounter's defeat does not free the intake. Tree damage explains how the
limb reached it, and Halden acknowledges the monster and warns the carriers
when the encounter actually occurred.

## Objectives and durable milestones

| Objective | Completed by |
| --- | --- |
| `meet_mira` | Acknowledging the request/gift presentation, owning the blade and accepting MQ02 |
| `diagnose_mill` | Reading both inspections and the diagnosis |
| `prepare_journey` | Fully reading Mira's warning before departure |
| `secure_trail` | Winning the riverbank encounter, settled once with rewards |
| `reach_intake` | Reading the upstream intake inspection |
| `prepare_intake` | Completing the bypass action |
| `small_spell` | Completing the successful water movement |
| `repair_intake` | Completing the cooperative lever repair |
| `verify_mill` | Observing the working mill and finishing its exchange |
| `report` | Finishing the closing exchange with Halden and Mira; the quest then directs Caelan home |
| `return_sanctuary` | Finishing the visible cup placement after Serene’s final acknowledged thanks |

The optional version-two `mill_quest` journey record stores `inspected` (from
`mechanism`, `race`, `intake`) and the boolean facts `prepared`, `spell_done`,
`encouraged`, `restored`, `verified`, `resolved`, `warned`, `encounter_cleared`,
`aftermath_done` and `legacy_bypass`. Quest state and these facts
are validated together. Transient poses, dialogue pointers, movement paths and
action clocks are rebuilt safely rather than serialized. The final handoff extends the same version-two record with the optional boolean pair `reported_to_halden` and `cups_placed`; both are present together once the Halden report is recorded. Older records may omit both. The report objective commits the first fact without marking `resolved`, while the new `return_sanctuary` objective finishes only after Serene’s final acknowledged instruction and the physical cup placement. Reloading between these boundaries does not repeat the mill report or complete unread dialogue.

The pressure-easing and water-returning dialogue follows the actual bypass and repair actions. These follow-ups do not undo completed work if canceled or interrupted.

The successful spell is checkpointed before the encouragement. Leaving that
exchange unread preserves it without replaying the spell. Completed repairs
stay repaired while the player travels or reloads. Interrupted actions resume
from a safe unfinished stage. Pause and inventory freeze action clocks; ordinary
dialogue remains live and cancelable. New Game resets Mira and all mill facts. Carrying or holding the cups is transient: an interrupted unfinished sequence reloads safely before the introduction and carry. Already-completed older MQ02 journeys retain their result; quest migration adds the new final objective as completed without replaying the homecoming, arrival or rewards. The new state never reopens MQ02 for an existing completed journey.

Older saves at the available Mira handoff remain valid and can receive the presentation. Already-active/completed MQ02 journeys preserve their prior progress without a forced retroactive gift or replayed fight. When those journeys do not own `caelan_gearblade`, `_speak` chooses the matching `legacy_*` arrays for weapon-dependent aftermath, spell, encouragement, repair follow-up and later replies. Their words do not claim an elemental lesson or birthday gift that never occurred. The committed legacy arrays retain the prior route’s facts and body registration.

Earlier placeholder MQ02 objective records preserve only their meeting. Version-one journeys at or beyond the intake retain the explicit route bypass without invented combat, warnings, aftermath, monster reports or rewards. An old upstream checkpoint before the intake rejoins the safe approach. An upstream scene remains a valid exterior location. The repeatable town Bat is independent of MQ02 story progress.

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

## Millrace arrival cutscene, music and transition

After the warned departure, entering the millrace stops Caelan at the real trail
arrival while Mira joins him through the existing link. Both then stand and
notice the large boar. The camera pans to the creature and holds through the
pre-fight conversation, with portraits and prose in a fixed bottom panel.

Mira’s final “Caelan, back towards me. Slowly” line
starts a return pan. Its panel moves above the party so both remain visible.
The existing Eldenmere Theme continues until the camera has returned and the
warning has been acknowledged. Only then does Kindled Courage begin and the
existing world-to-battle transition start. Fast acknowledgements cannot skip
the return; slow reading keeps the party shot held.

Movement and unrelated menu inputs are held during staging; Escape, the pause
menu, display changes and prose advancement remain available. Focus loss pauses
the scene. Reduced Motion uses static shots. Canceling releases the shot and
actors. Flee and defeat do not force an immediate repeat; an explicit retry or
leaving and entering the area can stage it again.

Camera clocks, dialogue position and staging are not saved. An unfinished
cutscene reloads at the safe arrival; completed encounters, legacy bypasses and
saved Spoils do not replay it. No new quest fact or choice is added. Victory's
fanfare, Spoils, once-only rewards and linear aftermath remain the same.

See the [actual millrace cutscene review](reviews/millrace_cutscene/README.md).
