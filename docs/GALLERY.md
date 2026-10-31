# Cutscene Gallery

Choose **Gallery** on the title screen to replay any of the 24 registered scenes.
The catalogue is available immediately, including without a saved journey.
Thumbnails are cropped from actual production-rendered frames, not illustrations
or prerecorded playback. Scenes run with their current dialogue, animation,
camera, music and effects.

## Controls

| Where | Input | Action |
| --- | --- | --- |
| Catalogue | Mouse wheel | Scroll |
| Catalogue | Up/Down or W/S | Select and reveal the adjacent scene |
| Catalogue | Home/End, Page Up/Page Down | Jump through the list |
| Catalogue | Click a card, Play scene, Enter or Space | Start the selected scene |
| Catalogue | Back, Esc or Backspace | Return to the title |
| Replay | Space, E, Enter or click | Advance dialogue when present |
| Replay | Gallery, Esc or Backspace | Return to the retained catalogue position |
| Replay | Restart or R | Recreate this scene from its initial fixture |
| Standalone cinematic | P | Use the production pause/resume control |
| Standalone cinematic | Skip button | Finish the preview without starting a journey |
| Either | F11 | Toggle fullscreen using the normal display setting |

Dialogue scenes identify their input in the replay toolbar. Automatic scenes
identify themselves there as well. Necessary same-station interactions (for
example lifting the assembled lantern) proceed automatically after the preceding
dialogue/action finishes. Player travel, menus and incidental encounters are
disabled inside the bounded preview. The millrace threat ends before combat.

## Coverage and boundaries

Every fixture is in `cutscene_gallery.py`, beside its stable ID and metadata.
It supplies prerequisite facts and an initial station to existing controllers;
it does not duplicate dialogue, animation or camera scripts.

| Stable ID | Name | Production sequence and end boundary |
| --- | --- | --- |
| `later_journey` | A Light in the Distance | `OpeningCinematic.start`; complete/Skip ends preview before New Game |
| `morning_wake` | Morning Bells | `OpeningSequence.start_new_game`; wake animation/dialogue through exploration |
| `morning_breakfast` | Breakfast at the Sanctuary | Opening breakfast arrival, seating, meal, cup and standing through assignment |
| `halden_medicine` | Medicine for Halden | Halden visit conversation and physical medicine handoff |
| `tomas_sack` | Tomas Lends a Hand | Halden visit: Tomas approaches, lifts, carries and stores one sack |
| `elira_lantern_retrieval` | The Memorial Lantern | Elira stool/retrieval action until lantern carried |
| `elira_lantern_placement` | A Lantern Remembered | Elira placement action until lantern rests on table |
| `venn_failed_spell` | A Spell That Will Not Take | Venn magicks attempt and subsequent practical repair |
| `venn_gate_repair` | Borrowed Tools | Venn tools repair through restored channel |
| `halden_arrival` | Trouble at the Mill | OpeningConclusion: Halden enters the sanctuary and reports the mill problem |
| `millrace_threat` | A Boar by the Millrace | Mill encounter camera reveal, conversation and return warning; native callback stops before battle |
| `mill_bypass` | Make Room for the Water | Mill preparation dialogue and bypass action |
| `mill_small_spell` | A Smaller Magical Success | Mill spell introduction/action and Mira's encouragement |
| `mill_repair` | Freeing the Intake | Mill repair dialogue, lever and haul-rope action until restored |
| `regent_arrival` | Aldric's Relief Caravan | RegentArrival requested after completed mill facts; natural finish or Skip |
| `regent_cart_release` | The Road Crew's Cart | Regent dispute dialogue, release and Venn's cart departure |
| `lantern_frame` | A Frame of His Own | Workshop design, assembly and frame lift until frame ready |
| `lantern_collect` | Gathering the Materials | Collection dialogue and material pickup |
| `lantern_homecoming` | A Place at the Table | Home arrival and material placement |
| `lantern_paper_practice` | The First Paper Window | Home paper practice action |
| `lantern_finishing` | Finishing Liam's Lantern | Design, preparation, covering, fastening and finished lantern lift |
| `lantern_putaway` | Safe Until Tomorrow | Final home placement and farewell through quest completion |
| `grain_extra_sack` | One Sack Too Many | GrainFarm's finite exchange, shared lowering and lashing check |
| `bridge_tea` | Tea by the Broken Bridge | BridgeCrew's finite request, offer, reception, drink and seated break |

Fixtures use completed prerequisite quest facts for the selected chapter only.
The lantern fixtures use the current controller's stage/objective prefix; mill
intake scenes use current v2 encounter-complete facts. Regional scenes begin at
their authored finite vignette stations with the preceding routine work seeded.

Intentional exclusions are ordinary standing conversations, player-controlled
errands/travel and repeating ambient routines. Specifically: opening quest
acceptance and household reminders/turn-ins; manually carrying Caelan's sacks;
mill inspection/report/aftermath exchanges and the playable battle; Regent
preparations/greeting/welcome/excavation/private dialogue and free escort travel;
lantern classroom/permission/neighbor/memorial/sanctuary/school conversation
stations; and recurring resident work, play and patrol loops. Their staged
actions listed above are included. Future unimplemented scenes are not listed.

## Isolation and cleanup

`GallerySession` constructs a fresh `Game` with separate worlds, actors, quest
state, inventory, camera, controllers and image caches. The title's loaded
journey never enters it. Its SaveStore has no path, and `save_progress` has an
independent preview guard even if a caller later assigns a path. Settings are
copied before audio starts into a separate, non-persistent settings object.

No preview checkpoint, reward or completion receipt can reach the normal save.
Continue resumes the title's original loaded journey. Closing a preview stops
its owned morning, regional and arrival effects and soundtrack, then restores
title music. Regional voice leases are released by sound identity; unrelated
channels are not globally stopped. Restart constructs another fresh runtime.
Completion holds only the final world pose briefly and does not advance the
next scene. Window focus loss freezes preview progression and dialogue input.

The toolbar has its own display area, and scene input coordinates account for
that viewport. This keeps the complete production dialogue and Skip controls
visible. Missing/corrupt assets encountered during launch or lazy rendering
return to an actionable Gallery error panel; missing thumbnails have a deliberate
lantern fallback. Browsing does not construct scene runtimes or load every image.

## Registering another scene

1. Add a small fixture accepting `(game, playback)` in `cutscene_gallery.py`.
   Seed only initial prerequisites; invoke the production controller's entry
   point and use `playback.watch(predicate, drive)` or its completion callback.
   A drive may invoke an existing same-station interaction, never copy story
   text or advance the animation clock. Keep encounters and travel bounded.
2. Add metadata to `GALLERY_ENTRIES` with a unique stable ID and a readable name,
   chapter, description and input hint. Keep the thumbnail path repository-local.
3. Add a representative action predicate/crop to `tools/capture_gallery.py` and
   run `python tools/capture_gallery.py --mode thumbnails`. Check the image and
   `assets/ui/gallery/capture.json` provenance. Thumbnails are 320×180 PNGs.
4. Run the catalogue and session tests. The catalogue dynamically discovers a
   completion test for every registered entry. Add boundary-specific assertions
   where the new scene needs them, then refresh the review capture.

## Verification and captures

Run the normal `python -m unittest discover -s tests -v` suite. On memory-limited
machines, discover all modules and execute each in a fresh process sequentially;
this avoids retaining Pygame asset graphs from many unrelated test modules.

`python tools/capture_gallery.py --mode all` regenerates thumbnails, responsive
screenshots and the review MP4. It uses real title/Gallery input, actual scene
controllers at 30 Hz, an isolated temporary saved journey, and byte comparisons
before each return. Dialogue acknowledgement is brisk for review; authored
animation and camera timing are unchanged. The video is deliberately silent
because SDL dummy has no audio loopback. Mixer ownership/lifecycle is tested;
no perceptual listening is claimed.

See [review evidence](reviews/gallery/README.md) for the final regression result,
captured replay paths and remaining limitations.
