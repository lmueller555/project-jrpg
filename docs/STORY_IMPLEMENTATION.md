# Sanctuary opening

New Game now stages the approved bedroom, breakfast and request scenes from
`narrative/game_01/CH01_MQ01.md`. This milestone ends with accepting Serene's
three-household quest; the practical household tasks are the next stage.

## Playable sequence

1. The title fades into Caelan's bedroom. His closed-eye head is visible on the
   existing pillow, with his body beneath the quilt. Tomas speaks from outside
   the bedroom doorway. Click, Space or E advances the approved exchange.
2. Control returns beside the bed. E inspects nearby books, notes, the family
   drawing, wardrobe or bed using the approved optional lines. The tracker points
   to breakfast; players can explore without a timer or required inspection list.
3. Walking through the hall's northeast door starts breakfast. The production
   player mover walks Caelan from the doorway to the table with full collision.
   Seated poses and a four-pose short reach register Tomas's plate nudge on the
   tabletop. Serene continues sorting provisions in the background.
4. The breakfast conversation and brief shared meal finish, then the player can
   approach Serene. Her gold availability marker and journal entry become visible
   at this point. Tomas waits nearby while she works.
5. Refusing the request leaves it available after walking away and returning.
   Clicking **I'll help** accepts exactly once, updates the quest UI, and plays
   the remaining approved request dialogue. Both actors face Caelan for this
   exchange, then return to their ambient schedules. The household objectives
   remain incomplete until their real task controllers are implemented.

Morning sounds are quiet diegetic bell, knock, bird and stream cues, independent
of the title score and muted by its music setting. Missing audio hardware is safe.

## Runtime and art

`opening.py` controls scene checkpoints, borrowing the original Serene and Tomas
instances. `social.py` supports actorless scripted dialogue as well as ordinary
proximity conversations. Main's story pose overrides are visual only: logical
feet stay on valid floor, and normal rendering returns when the scene releases
control. The temporary seated chair positions are restored after breakfast.

The script and staging coordinates live in `assets/story/opening.json`. The
seated poses, sleep head, plate and reach frames live beneath
`assets/story/sanctuary_opening/poses`, with source hashes and registration notes.
`tools/build_sanctuary_opening_poses.py` rebuilds these native pixel exports from
the existing approved character art. The original character PNGs are unchanged.

## Saved progress

The existing version-one journey envelope accepts an optional `opening` record
with its own version and stage. Stages are `disabled`, `wake`, `explore`,
`breakfast`, `assignment`, `acceptance` and `done`. New saves checkpoint scene
boundaries and acceptance. Continuing unfinished wake/breakfast/acceptance scenes
restarts that short scene from a safe point; finished scenes do not replay.
Quests and dialogue flags retain their existing validation and persistence.

Older saves without this field restore in `disabled` mode and keep their prior
story progress and location. They do not insert the new morning retroactively.
Direct `Game(start_on_title=False)` instances also default to this mode so
focused room, asset and routine tests can run independently of the opening.

## Remaining first-quest work

Halden, Elira and the Venn family still need their character packs, portraits
and placement. Tomas's temporary following segment, grain-sack carrying,
lantern retrieval, gate repair, the final report and the staged mill-failure
arrival still need their gameplay controllers. The quest feedback layer is
ready for those events; room visits never stand in for completing their tasks.
