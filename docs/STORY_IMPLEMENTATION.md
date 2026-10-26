# Sanctuary opening

New Game now stages the approved bedroom, breakfast and request scenes from
`narrative/game_01/CH01_MQ01.md`. This milestone ends with accepting Serene's
three-household quest; the practical household tasks are the next stage.

## Playable sequence

1. The title fades into Caelan's bedroom. His closed-eye head is visible on the
   existing pillow, with his body beneath the quilt. Tomas speaks from outside
   the bedroom doorway. Click, Space or E advances the approved exchange. Four
   registered wake poses show him waking, sitting at the edge and standing;
   quilt occlusion stays below his face. He leaves through the clear bedside.
2. Control returns beside the bed. E inspects nearby books, notes, the family
   drawing, wardrobe or bed using the approved optional lines. The tracker points
   to breakfast; players can explore without a timer or required inspection list.
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
   exchange, then return to their ambient schedules. Caelan can move throughout
   the offer and follow-up. Leaving the follow-up releases the actors while
   preserving the explicitly accepted quest. The household objectives
   remain incomplete until their real task controllers are implemented.

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

`camera_director.py` follows Caelan with the full 480×320 world viewport, including
through dialogue, and eases tracking over approximately 0.35 seconds. Opening a
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
completing the grain-sack task. See [inventory](INVENTORY.md). Household controllers
still need to invoke that API after their actual NPC handoffs.

Halden, Elira and the Venn family still need their character packs, portraits
and placement. Tomas's temporary following segment, grain-sack carrying,
lantern retrieval, gate repair, the final report and the staged mill-failure
arrival still need their gameplay controllers. The quest feedback layer is
ready for those events; room visits never stand in for completing their tasks.
