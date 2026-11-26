# Sanctuary opening

**Migration status — 2026-11-26:** Current-runtime reference. The approved
opening is now the [Fire Veinhold sequence in Chapter 1](narrative/game_01/CHAPTER_01.md).
The old opening flashforward and Festival of Light storyline are retired target
story. The existing cinematic still runs in the game; this documentation-only
migration changes no controller, dialogue, asset, quest flag or save contract.
The playable sequence and former approval labels below describe that unchanged
implementation, pending the separately scoped opening rewrite.

This guide owns the opening controller, audio, rendering, and save contracts.
The [MQ01 script](narrative/game_01/CH01_MQ01.md) owns the authored opening and
household dialogue. The separate [flashforward](narrative/scenes/OPENING_CINEMATIC.md) and
[regent arrival](narrative/scenes/REGENT_ARRIVAL.md) each own their cinematic specification.
Use the [narrative index](narrative/README.md) to find current story authorities.

## Playable sequence

1. After the cinematic finishes or is skipped, the title's New Game path enters
   Caelan's bedroom. His closed-eye head is visible on the
   existing pillow, with his body beneath the quilt. Tomas speaks from outside
   the bedroom doorway. Click, Space or E advances the approved exchange. Four
   registered wake poses show him waking, sitting at the edge and standing;
   quilt occlusion stays below his face. He leaves through the clear bedside.
2. Control returns beside the bed. E inspects nearby books, notes, the family
   drawing or wardrobe using the approved optional lines. At the bed's side or
   foot, **E: rest** offers **Rest / Not now**. Confirming a short rest fully
   recovers every registered party member's HP and MP to their effective maxima,
   including earned attribute growth, then saves. A brief fade and Caelan's refreshed
   response acknowledge the rest. This repeatable interaction preserves story
   stages and is also available to existing journeys without the opening scene.
   The tracker points to breakfast; players can explore without a timer or
   required inspection list.
3. Walking through the hall's northeast door starts the greeting and invitation.
   This exchange allows movement; leaving it unfinished postpones the meal.
   Returning through the doorway or using **E: join breakfast** near the table
   starts the invitation again.
   The production player mover then walks Caelan to his chair with full collision.
   Four-pose sitting, eating, cup placement and standing actions provide the
   visible meal. Tomas nudges his plate and eats more enthusiastically; Caelan
   takes a small bite and sets out a cup for Serene. She sorts provisions nearby.
4. The breakfast conversation and shared meal finish, then the player can
   approach Serene. Her gold availability marker and journal entry become visible
   at this point. Tomas waits nearby while she works.
5. Refusing the request leaves it available after walking away and returning.
   Clicking **I'll help** accepts exactly once, updates the quest UI, and plays
   the remaining approved request dialogue. Both actors face Caelan for this
   exchange. Serene resumes her schedule; Tomas joins Caelan. Caelan can move throughout
   the offer and follow-up. Leaving the follow-up releases the actors while
   preserving the explicitly accepted quest. The household objectives
   remain incomplete until their actual deliveries and practical tasks finish.
6. Tomas follows through town and building doors using the real collision mask.
   He trails Caelan, catches up during longer walks, and yields in tight spaces.
   His feet never prevent Caelan passing through a doorway. He accompanies only
   the Halden segment; other NPCs retain their normal schedules.
The household visits continue in the order and with the dialogue specified
by [MQ01](narrative/game_01/CH01_MQ01.md). Their technical owners are
[Halden's visit](HALDEN_VISIT.md), [Elira's visit](ELIRA_VISIT.md), and
[the Venn visit](VENN_VISIT.md). Those guides specify interactions, prop
ownership, interruption, and safe reconstruction rather than a second script.

Morning sounds are quiet diegetic bell, knock, bird and stream cues, with cloth,
footstep, chair, plate, bite and cup effects emitted at actual action beats.
Music and effects levels are independent and persist separately from the journey.
PCM is prepared before the launcher's first visible title frame. Missing audio
hardware is safe. Pause freezes only owned audio channels and restores them
without interrupting unrelated sound effects.

## Runtime and art

`opening.py` controls scene checkpoints, borrowing the original Serene and Tomas
instances. `social.py` supports actorless scripted dialogue as well as ordinary
proximity conversations. `speech_bubble.py` lays out portrait speech bubbles
above the actual speaker, including Caelan's replies, and clamps them to the
viewport. Rendering and clicked response hitboxes share that layout. A pending
NPC handoff has its own small anchored hint; only that participant pauses after
putting the item down. Normal conversations do not own movement or camera control.
Walking away cancels unfinished prose without applying flags or quest effects.
Main's story pose overrides are visual only: logical
feet stay on valid floor, and normal rendering returns when the scene releases
control. Both chairs use permanent positions in the source room, runtime map
and collision masks; no scene action moves furniture. Action queues and dialogue
completion barriers prevent quick reading from omitting a required gesture.

`camera_director.py` normally follows Caelan with the full 480×320 world viewport,
including through live dialogue, and eases tracking over approximately 0.35 seconds.
Its explicit scripted focus/return API also supports MQ02's millrace cutscene:
the party stops, a bounded shot holds the boar, and the camera returns before
music and battle start. That scoped sequence uses fixed bottom/top dialogue
panels; ordinary conversations keep their existing behavior. Opening an ordinary
bubble does not change the shot or reserve a separate text-panel area. Bedroom
inspections, the breakfast invitation and the accepted-quest exchange are live;
the authored bed, guided walk and chair/meal actions still control his body.
Steering during the meal latches a request to leave: the remaining gestures and
standing action finish safely, dismissing unread meal prose without extra clicks.
`pause_menu.py` stops gameplay during dialogue and actions as well as exploration;
Escape resumes without advancing dialogue or choosing a quest response. Its
Settings menu and the title use `audio_settings.py` and `saves/settings.json`.

The script and staging coordinates live in `assets/story/opening.json`. The
seated poses, sleep head, plate and reach frames live beneath
`assets/story/sanctuary_opening/poses`, with source hashes and registration notes.
`tools/build_sanctuary_opening_poses.py` rebuilds these native pixel exports from
the existing approved character art. Each short action has four native 24×36
key poses, registered display anchors and timing. The original character PNGs
are unchanged.

## Saved progress

The existing version-one journey envelope accepts an optional `opening` record
with its own version and stage. Stages are `disabled`, `wake`, `explore`,
`breakfast`, `assignment`, `acceptance` and `done`. New saves checkpoint scene
boundaries and acceptance. Continuing unfinished wake/breakfast/acceptance scenes
restarts that short scene from a safe point; finished scenes do not replay.
Quests and dialogue flags retain their existing validation and persistence.
Leaving an offer or report unread never accepts or completes it. An accepted
quest stays accepted if the player walks away from its follow-up conversation.

Older saves without this field restore in `disabled` mode and keep their prior
story progress and location. They do not insert the new morning retroactively.
Direct `Game(start_on_title=False)` instances also default to this mode so
focused room, asset and routine tests can run independently of the opening.

## Household controllers and MQ01 completion

The inventory foundation now grants and saves Serene's supplies on acceptance.
Its guarded handoff API consumes medicine and records a delivery without
completing the grain-sack task. All three household controllers now invoke that
API at their actual handoffs. See [inventory](INVENTORY.md).

`halden_visit.py` now owns the first household. Its optional version-one
`halden_visit` journey record saves each stored sack, Caelan's carried sack,
the closing exchange and Tomas's goodbye. Inventory owns the medicine receipt.
An interrupted Tomas lift/carry safely returns that sack to its entry position;
stored sacks stay stored. Continuing an escort restores the same Tomas beside
Caelan; completed visits never rejoin or replay supplies. Old accepted saves
can begin the Halden visit, and old completed objectives migrate as completed.
See [the first household](HALDEN_VISIT.md) for controls and validation.

`elira_visit.py` owns the order-flexible lantern visit. Inventory owns the food/oil
receipt; its optional version-one `elira_visit` record saves the lantern's single
location. Interrupted gestures resume on valid floor with the lantern either
still on its shelf or in Caelan's hands. A placed lantern and unread closing
conversation survive leaving and reloading. Older saves reconstruct outstanding
or completed visits without duplicating supplies. See [Elira's visit](ELIRA_VISIT.md).

`venn_visit.py` saves the two completed inspections, chosen method and repaired
gate. Inventory owns the recovery-supply receipt. Interrupted repair gestures
restart safely from the bank with the gate jammed; finished repairs persist
without completing unread family dialogue. Old completed visits migrate to a
working gate without inventing a repair choice. The family uses role titles;
given names and exact ages remain open. See [Venn's visit](VENN_VISIT.md).

The three household tasks and the MQ01 conclusion are playable. After the last
household, approach Serene for the approved report. Finishing its final line
records the report without completing MQ01. If she is in the dining room, she
walks through the existing doorway into the sanctuary hall. Halden's trip from
home occurs offscreen; the same miller actor then walks from the courtyard through
the real sanctuary door and approaches Serene. The player remains free to move.

Approach Serene in the hall to hear the approved stopped-wheel exchange. Only
its final line completes MQ01 and makes **A Little Trouble at the Mill** available,
with the tracker pointing toward Mira's workshop. Speaking with Mira at her
outdoor workbench now accepts the complete MQ02 adventure: mill diagnosis,
upstream intake preparation, Caelan's smaller successful spell, encouragement,
cooperative repair and return to Halden. The mill holds a still frame after the
MQ01 report and resumes only when the intake is physically restored. Stream
animation continues throughout. See [Mira's mill quest](MILL_QUEST.md) and its
[in-game review](reviews/mill_quest/README.md).

`opening_conclusion.py` owns optional version-one stages `idle`, `arrival`,
`waiting` and `done`. Leaving unread report prose records nothing. Leaving the
arrival dialogue keeps the actors waiting and MQ02 locked; returning permits the
exchange again. A saved `arrival` resumes safely from the courtyard; `waiting`
restores the hall actors without replaying their entrance; `done` replays neither
scene nor notifications. Pause/inventory freeze the staging and map/journal defer
it. Older completed turn-ins retain their completed quest and receive only the
missing mill hook. New Game resets the hook, actors and wheel. New locked quest
records may be absent in older quest snapshots and migrate without announcements.
See the [runtime capture and testing notes](reviews/opening_conclusion/README.md).



## Later quest owners

| Quest / scene | Narrative owner | Runtime owner |
| --- | --- | --- |
| MQ02 | [MQ02 script](narrative/game_01/CH01_MQ02.md) | [Mill implementation](MILL_QUEST.md) |
| Iselin's arrival | [Arrival scene](narrative/scenes/REGENT_ARRIVAL.md) | Its controller/clip sections |
| MQ03 | [MQ03 script](narrative/game_01/CH01_MQ03.md) | [Regent runtime](REGENT_QUEST.md), [reserve staging](SANCTUARY_ARRIVAL.md), and [cave](SANCTUARY_CAVE.md) |
| MQ04 | [Complete MQ04 script](narrative/game_01/CH01_MQ04.md) | [Lantern implementation](LANTERN_QUEST.md) |

Each owner records its own acknowledgments, actor/prop handoffs, compatibility,
and completion boundaries. This guide does not maintain another walkthrough
or implementation-status summary of those quests.

## Opening dialogue through MQ02

Authored opening and mill exchanges live in their linked quest scripts.
The following conditional filtering and controller behavior remain runtime
contracts of this guide.

The existing `serene_quest_report` includes a six-line optional recollection guarded by per-line `requires: ["CH01_MQ01_VENN_MAGICKS_FAILED"]`. `SocialSystem.start` filters those lines against restored story flags before pagination; its selected source remains stable during reading and text reflow. Only players who attempted the spell hear it. Canceling unread report prose still commits nothing; reporting and the subsequent acknowledged mill handoff retain their separate checkpoints.

Serene’s available-MQ02 reminder points to Mira’s workbench; MQ02 reminders follow the current investigation, intake control, repair or return stage. The longer Serene offer has an actor-presence alternative for older journeys where Tomas is elsewhere, retaining all essential directions without an offscreen speaker. Its conversation ID, explicit acceptance, supplies and quest prerequisites remain the same.

`prepare_done` and `repair_done` play after the actual mill actions commit. Canceling or loading during those follow-up exchanges preserves the completed work; the current stage reminder provides any onward direction again. All existing version-one quest snapshots and the conditional Venn failure/limited mill success remain intact. See the [opening script](narrative/game_01/CH01_MQ01.md), [mill script](narrative/game_01/CH01_MQ02.md) and `tools/verify_opening_dialogue_pass.py` for fresh-game verification through both quests.
