# Sanctuary opening

This guide describes the checked-in runtime, including the regional-surges and
covenant dialogue and the [MQ02-to-MQ03 arrival cinematic](REGENT_ARRIVAL.md).

New Game first plays the approved late-journey [opening cinematic](OPENING_CINEMATIC.md),
then stages the bedroom, breakfast and request scenes from
`narrative/game_01/CH01_MQ01.md`. The playable opening now continues through
Tomas's temporary escort, the complete first household visit to Halden, and
Elira's memorial-lantern visit, and the Venn family's recovery-supply/gate visit.

The cinematic preserves the author's latest dialogue. Its visual sequence now
places the cup on the bench, holds both hands for Mira's reassurance, restores
the lamp in stages and follows Caelan's blue signal into the sky. A returned
camera gates Mira's final repair. The pair then leave behind a foreground sword
and bloody helmet; the camera stays with it for the final zoom and fade. This
future frame grants no gameplay facts or resources to the opening morning.

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
7. Approach Master Halden inside his mill-side cottage. Finish the approved
   exchange to pass him Serene's medicine. The handoff removes it from inventory
   once, without completing the remaining work. Leaving unread dialogue keeps
   the medicine in Caelan's satchel.
8. Three real sacks stand by the entry; a raised wooden pallet marks dry storage
   near the north wall. **E** lifts a sack and sets it on its matching pallet
   space. The context prompt identifies the location. Caelan carries the outer
   sacks. **E** by the middle sack asks Tomas to carry it: he walks to it, lifts,
   carries and sets it down with the approved stride and coordinated bob.
   There is no timer or failure penalty. Movement and the camera remain live
   except for the short handoff, lift and set-down gestures.
9. After all three sacks are stored, approach Halden for the closing exchange
   about his joints and the noisy mill. Then approach Tomas for his goodbye.
   He walks out through the cottage door before the Halden objective completes
   and Elira/Venn unlock in either order. Tomas then physically walks back to
   the sanctuary and resumes his preparation schedule, without following Caelan.
10. Elira's visit unlocks after Halden, independently of Venn. Approach her in the
    bridge cottage for the approved food/oil exchange. The short handoff consumes
    only her supply bundle. **E** near the stool aligns Caelan on clear floor,
    steps him onto the stool, raises his arms, lifts the unlit lantern from its
    registered shelf pixels, lowers it carefully and steps down. The shelf changes
    to the approved empty state exactly when his hands take ownership. Carry it
    to the north side of her table and press **E** to set it down. Approach Elira
    again for the approved conversation about her husband and the festival. Only
    reading its final line completes the objective. Ordinary dialogue stays live.
11. The Venn parents and recovering child occupy the wide eastern cottage. The
    child rests on the existing pillow and can be spoken to from the bedside.
    Approach either parent for the approved recovery-supply exchange; the handoff
    consumes their bundle once. **E** inspects both the pin and the channel at
    the existing irrigation gate east of their home. After reading both, **E**
    at the pin offers two clicked responses. Tools reseat the pin, move Caelan
    along the dry bank to pull debris clear, then lift the board. Trying magicks
    produces a weak blue spark that fails to move the water. Caelan acknowledges
    the failure and uses the borrowed tools. Only that physical repair restores
    animated downstream flow over the existing spillway. Return through the cottage door and finish
    the approved family conversation to complete the objective. Elira and Venn
    can be played in either order; the last household makes the quest ready for
    Serene's existing report dialogue.

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

## Remaining first-quest work

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



## MQ03 — The Regent’s Road

`regent_quest.py` and `assets/story/regent/scene.json` implement the
[approved regional story](narrative/game_01/REGIONAL_SURGES.md),
[covenant guide](world/SANCTUARY_COVENANT.md) and
[revised MQ03 script](narrative/game_01/CH01_MQ03.md). After MQ02's acknowledged
report and rewards, the [arrival cinematic](REGENT_ARRIVAL.md) introduces Aldric
at the southern land gate, shows him hearing local accounts of the destroyed
crossing, and gives Serene a private moment inside the sanctuary. The caravan
then waits at its registered town approach. Completing or skipping the scene
returns control to Caelan without accepting MQ03. Its saved arrival checkpoint
prevents both replay after completion and duplicate MQ02 rewards.

After the completed mill quest, MQ03 becomes available from Serene in the
home dining room. Caelan meets Aldric, Lucan, the page and the driver by the
brook and guides them directly to the meal. The former Venn cart dispute is
removed. Serene explains the Sanctuary's duty to guide the region's dead and
the growling heard since the bridge incident.

An injured Crown worker enters through the actual house doors and reports an
attack. The crew's presence exposes Aldric's secret deployment before the
negotiation. Lucan explicitly did not know. Serene, Tomas and the driver remain
to help the survivor; Caelan collects Mira at her workshop, then travels with
her, Aldric, Lucan and the page through the existing overworld contacts.

Version-three quest checkpoints separate acknowledged discussion, the physical
interruption, attack report, departure, Mira's rejoining and Sanctuary travel.
Partial dialogue and entrance routes are transient. The existing four objective
IDs remain compatible with earlier journeys; the final objective stays active
at `sanctuary_arrival_pending`. A separate arrival owner now plays the
eight-beat scene in the live reserve, checkpoints acknowledged beats and
returns control at the cave apron. It does not grant rewards, turn in MQ03 or
unlock MQ04.

Mira's existing resources and character state persist through the required
`mq03_sanctuary` party event. Aldric, Lucan and the page are story escorts on
the road. Once the arrival rescue plan is acknowledged, Lucan becomes the
temporary third combat member while Aldric and the page stay with the workers.
New Game releases borrowed actors.
Completed version-one/two MQ03 journeys remain complete and retain later
lantern progress; an unfinished old discussion resumes before the new facts
are acknowledged. The later formal authorization remains separate story work.

See the [runtime guide](REGENT_QUEST.md),
[narrative script](narrative/game_01/CH01_MQ03.md) and
[current gameplay review](reviews/mq03_emergency/README.md).

## MQ04 — A Light of His Own, opening segment

Completed legacy MQ03 journeys unlock the first of four segments of MQ04. The new Sanctuary route awaits its later resolution before that handoff. Tomas’s dining-room invitation leads into a school preparation session with the existing teacher and six children, a parent-approved outing, and collaborative frame construction at Mira’s workshop. One quest record stores committed scenes; the full eight-objective chain is stable from this first segment. The endpoint `frame_ready` completes only the first two objectives and keeps MQ04 active, with a truthful checkpoint in the journal and tracker.

Quest-scoped attendance borrows the actual home residents. Liam’s existing play and block routines yield safely, Tomas’s MQ03 staging hands off explicitly, and Mira’s post-mill return no longer competes with her workshop scene. New Game releases borrowed actors; old completed-MQ03 saves gain the newly gated quest without replaying earlier visits. See [the implementation guide](LANTERN_QUEST.md), [script](narrative/game_01/CH01_MQ04.md), and [review artifacts](reviews/lantern_quest/README.md).

## MQ04 — village preparations and Elira, second segment

Continue the saved `frame_ready` checkpoint by speaking with Mira. Liam and Tomas accompany Caelan to Halden’s working mill, the recovering Venn household and Elira. Eleven player-paced scenes introduce shared festival food, homebound portions, a small household decoration and a specific memory of Elira’s husband. After the goodbye, both companions leave through the real cottage door before the outside reflection completes `visit_elira`. MQ04 remains active at `elira_visited`, with the first four existing objectives complete.

`lantern_village.py` extends the existing controller with version-one committed checkpoints. Mira actually returns to her original workbench; the frame and drawing stay together on the craft table. Prior controllers keep authority over the wheel, repaired irrigation, Venn child’s resting appearance and Elira’s single memorial lantern. The later domestic break, theology discussion and personal lantern purpose remain subsequent segments. See [the PR2 script](narrative/game_01/CH01_MQ04_PR2.md) and [actual-game review](reviews/lantern_village/README.md).

## MQ04 — home break and sanctuary, third segment

Continue `elira_visited` outside the cottage. Return to Mira, collect the frame and papers, and take a break at Liam’s home. The existing father hosts the snack; Liam tries a loose paper panel while Caelan and Tomas reflect on Elira. Take his questions to Serene in the sanctuary hall. The quest remains active at `serene_heard`, with the first six existing objectives complete. The final purpose, covering and showing mother belong to the concluding segment.

`lantern_rest.py` extends version-one committed checkpoints. Liam’s frame has one stage-derived location: workshop, carried, then home. Its carry animation follows his actual direction/gait. Paper work remains visibly story-owned during the brothers’ dialogue; ambient block/chase routines stay suppressed and Daisy keeps her independent behavior. Serene’s explicit MQ03 handoff prevents earlier staging from reclaiming her. Old village preparations and repairs remain visible. See [the PR3 script](narrative/game_01/CH01_MQ04_PR3.md) and [review](reviews/lantern_rest/README.md).


## MQ04 — final purpose, covering and homecoming

Continue the shipped `serene_heard` save, choose Liam’s authored personal intention, draw the final stairs/window panel, dry-fit and fasten it with his father, then let Liam lift the finished unlit lantern. Walk together to the actual school teacher, let Liam explain his own work and purpose, then return home and put it away before the farewell completes MQ04.

`lantern_finish.py` extends the same version-one committed-stage save. One stage-derived object changes from bare frame to papered lantern, is carried in all four directions, and returns to its persistent home display. Drawing and practice paper stay home; Mira’s old craft surface stays empty. Interrupted dialogue/actions restore the last committed object and objective prefix. `QuestLog.complete_and_turn_in` commits the last objective and completed status with one notice and one save; there is no ready-to-report checkpoint or fictional report to Tomas.

Completion releases Liam to household play at his actual home. Tomas walks back to the sanctuary, Serene keeps her afternoon station, and Mother continues the school workshop. Completed saves reconstruct those stations without borrowing Liam again or replaying completion. Prior repairs and village preparations persist. New Game releases the final cast and removes the finished prop. MQ05 is not registered and the day does not advance automatically.

See [the attributed PR4 script](narrative/game_01/CH01_MQ04_PR4.md), [production-game captures](reviews/lantern_finish/README.md), and `tools/verify_lantern_full_quest.py` for the uninterrupted full four-part route.


## Opening dialogue through MQ02

The playable breakfast, Serene briefing and report, household scenes, mill handoff and complete MQ02 dialogue now establish the people and Festival of Light preparations on the main route. Serene names each household and its need, distinguishes the upper and southern bridges, and identifies the eastern terrace. Halden’s flour supports tomorrow’s baking; Mira’s repair work and workshop are established before her first encounter. Literal asterisk-wrapped emotes add selective expressions without changing the approved sprites or animation contacts.

The approved character pass now continues from the rewritten wake-up and breakfast through all of MQ01’s household dialogue, repeats and mill handoff. Tomas takes responsibility for his return to the courtyard; Halden’s dialogue establishes his mill-working relationship with Mira; Elira directs her own remembrance; and the Venns discuss practical work and recovery. Serene follows up on specific needs and remembers Caelan’s requested practice time. The attributed script escapes its asterisks so the emotive markers remain visible in Markdown as they do in the plain-text game UI.

The existing `serene_quest_report` includes a six-line optional recollection guarded by per-line `requires: ["CH01_MQ01_VENN_MAGICKS_FAILED"]`. `SocialSystem.start` filters those lines against restored story flags before pagination; its selected source remains stable during reading and text reflow. Only players who attempted the spell hear it. Canceling unread report prose still commits nothing; reporting and the subsequent acknowledged mill handoff retain their separate checkpoints.

Serene’s available-MQ02 reminder points to Mira’s workbench; MQ02 reminders follow the current investigation, intake control, repair or return stage. The longer Serene offer has an actor-presence alternative for older journeys where Tomas is elsewhere, retaining all essential directions without an offscreen speaker. Its conversation ID, explicit acceptance, supplies and quest prerequisites remain the same.

`prepare_done` and `repair_done` play after the actual mill actions commit. Canceling or loading during those follow-up exchanges preserves the completed work; the current stage reminder provides any onward direction again. All existing version-one quest snapshots and the conditional Venn failure/limited mill success remain intact. See the [opening script](narrative/game_01/CH01_MQ01.md), [mill script](narrative/game_01/CH01_MQ02.md) and `tools/verify_opening_dialogue_pass.py` for fresh-game verification through both quests.
