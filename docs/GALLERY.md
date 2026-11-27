# Cutscene Gallery

Choose **Gallery** on the title screen to replay the registered scenes.

The **Scene Studies** section also includes **Mira: Aether Arm Rig**, an isolated
phase-one combat art preview. It shows her wearable augmentation, all combat
poses, illustrative future technique effects and a local six-unit routing
console. Its buttons select artwork rather than execute skills, and its
configuration never changes a journey. See the [arm-rig review](reviews/mira_arm_rig/README.md)
for captures, controls and the precise phase boundary.
The catalogue is available immediately, including without a saved journey.
Thumbnails are cropped from actual production-rendered frames, not illustrations
or prerecorded playback. Scenes run with their current dialogue, animation,
camera, music and effects.

**Scene Studies** includes **Ice Reaper: Frozen Clearing (32s)**, an isolated
pre-boss cinematic study. It uses the detailed
cinematic party sprites, its retained Wintermute2 soundtrack and the production
cinematic camera/dialogue controls. It ends at the authored cinematic handoff before playable combat and
does not replace New Game's opening or create a main-story encounter.
See the [scene document](narrative/scenes/ICE_REAPER_PRE_BOSS.md) and
[review clip](reviews/ice_reaper_opening/preview.mp4).

**Fire Veinhold Prologue** contains six individual shots and **Fire Veinhold —
Complete Cutscene (42s)**. The production list combines the 25-second eagle
approach/vista, five-second 180° island orbit, four-second alarm lead-in,
one-second bridge rush, four-second frozen-guard reveal and three-second
side-on running-party shot. The orbit has 301
inclusive perspective samples at 60 FPS. Individual clips initialize their
correct full-reel state, including an already sounding alarm for the bridge rush.
All use native 960×640 cinematic detail, continuous wind and owned scene effects.
New Game keeps the bedroom opening until the full prologue and playable handoff
are ready. See the [scene guide](narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md) and
[60 FPS review evidence and small downloadable preview](reviews/veinhold_bridge_run/README.md).

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
example placing Elira’s retrieved lantern) proceed automatically after the preceding
dialogue/action finishes. Player travel, menus and incidental encounters are
disabled inside the bounded preview. The millrace threat ends before combat.

## Coverage and boundaries

Every fixture is in `cutscene_gallery.py`, beside its stable ID and metadata.
It supplies prerequisite facts and an initial station to existing controllers;
it does not duplicate dialogue, animation or camera scripts.

| Stable ID | Name | Production sequence and end boundary |
| --- | --- | --- |
| `morning_wake` | Morning Bells | `OpeningSequence.start_new_game`; wake animation/dialogue through exploration |
| `morning_breakfast` | Breakfast at Home | Opening breakfast arrival, seating, meal, cup and standing through assignment |
| `halden_medicine` | Medicine for Halden | Halden visit conversation and physical medicine handoff |
| `tomas_sack` | Tomas Lends a Hand | Halden visit: Tomas approaches, lifts, carries and stores one sack |
| `elira_lantern_retrieval` | The Memorial Lantern | Elira stool/retrieval action until lantern carried |
| `elira_lantern_placement` | A Lantern Remembered | Elira placement action until lantern rests on table |
| `venn_failed_spell` | A Spell That Will Not Take | Venn magicks attempt and subsequent practical repair |
| `venn_gate_repair` | Borrowed Tools | Venn tools repair through restored channel |
| `halden_arrival` | Trouble at the Mill | OpeningConclusion: Halden enters Serene's home and reports the mill problem |
| `millrace_threat` | A Boar by the Millrace | Mill encounter camera reveal, conversation and return warning; native callback stops before battle |
| `mill_bypass` | Make Room for the Water | Mill preparation dialogue and bypass action |
| `mill_small_spell` | A Smaller Magical Success | Mill spell introduction/action and Mira's encouragement |
| `mill_repair` | Freeing the Intake | Mill repair dialogue, lever and haul-rope action until restored |
| `grain_extra_sack` | One Sack Too Many | GrainFarm's finite exchange, shared lowering and lashing check |
| `bridge_tea` | Tea by the Broken Bridge | BridgeCrew's finite request, offer, reception, drink and seated break |
| `garden_quiet_care` | A Little Shade | GardenOrchard's quiet-care dialogue, plant lift/carry/placement and settling into rest |
| `sheep_basket_visit` | A Familiar Visitor | PurposefulWildlife's finite gardener visit, sheep gathering, basket nuzzle and pat, basket retrieval and home return through release of the borrowed gardener |
| `checkpoint_borrowed_seat` | Keeping Your Seat | CheckpointCharm's bench ownership, supplies check, borrowed seat and familiar exchange through both original guards returning to duty posts |
| `ice_reaper_opening` | Ice Reaper: Frozen Clearing (32s) | Independent late-game cinematic study; ends before playable combat |
| `mira_arm_rig` | Mira: Aether Arm Rig | Independent art/technique preview; no journey changes |
| `fire_veinhold_opening` | Fire Veinhold — Complete Cutscene | Six ordered production clips totaling 42 seconds |
| `fire_veinhold_shot_01` | Shot 1 — Eagle Ascent and Cinder Isles (25s) | 15-second ascent followed by ten seconds overlooking the Cinder Isles |
| `fire_veinhold_shot_02` | Shot 2 — Fire Veinhold — Island Orbit (5s) | 301 rendered camera samples turn 180° around the main isle toward Merovar |
| `fire_veinhold_shot_03` | Shot 3 — Fire Veinhold — Emergency Alarms (4s) | Red beacons and siren activate; four seconds precede the rush |
| `fire_veinhold_shot_04` | Shot 4 — Fire Veinhold — Bridge Rush (1s) | Fast movement from the fortress toward the Merovar bridge landing |
| `fire_veinhold_shot_05` | Shot 5 — Fire Veinhold — Frozen Guards (4s) | Settle 20 feet onto the bridge, facing frozen guards and mainland |
| `fire_veinhold_shot_06` | Shot 6 — Fire Veinhold — Running the Bridge (3s) | Track the trio's legs across the steel bridge toward the Veinhold; faces stay outside the frame |

There are 27 current entries. The old flashforward, relief-caravan arrival
and MQ04 lantern-assembly fixtures are removed. Elira's private household
lantern retrieval/placement remains ordinary remembrance, without a festival.
Mill intake scenes use the retained encounter-complete facts. Regional scenes
begin at their finite vignette stations with preceding routine work seeded.

The garden preview starts at the completed-work checkpoint and ends only after
the struggling plant has been moved to its production destination by the hedge.
Its isolated fixture marks the separately registered pasture follow-up complete
so the gardener remains at that scene's home/rest boundary. The pasture preview
starts with plant care completed and the original gardener at home; production
code performs the entire visit. A fixed clear observer station keeps both sheep
and the full worker route active. The normal camera holds a full-height view of
home and pen, with no player travel or animation-clock shortcuts. Completion
requires the same empty basket and gardener home, with the actor loan released.
The checkpoint preview starts at its normal bench observation target and uses
the two existing guards throughout. It ends after both have returned to their
original posts and all seven lines have been acknowledged. Sitting, greeting
the cat and inspecting masonry remain ordinary optional interactions.

Ordinary standing conversations, player-controlled errands/travel, the mill
battle and repeating ambient routines are excluded. Removed quests do not
remain as hidden replay fixtures. Unimplemented Fire Veinhold shots are not
listed. Current retirement captures are under
`docs/reviews/opening_retirement/gallery/`; older Gallery captures are
historical evidence.

## Isolation and cleanup

`GallerySession` constructs a fresh `Game` with separate worlds, actors, quest
state, inventory, camera, controllers and image caches. The title's loaded
journey never enters it. Its SaveStore has no path, and `save_progress` has an
independent preview guard even if a caller later assigns a path. Settings are
copied before audio starts into a separate, non-persistent settings object.

No preview checkpoint, reward or completion receipt can reach the normal save.
Continue resumes the title's original loaded journey. Closing a preview stops
its owned cinematic, morning and regional effects and soundtrack, then restores
title music. Regional voice leases are released by sound identity; unrelated
channels are not globally stopped. Restart constructs another fresh runtime.
Completion holds only the final world pose briefly and does not advance the
next scene. Standalone Fire Veinhold films return immediately, without exposing
an underlying world after their final clip. Window focus loss freezes preview
progression and dialogue input.

The prologue's bounded background PNG decoder is drained on scene close,
restart and application exit before SDL shuts down. Starting a newly loaded
presentation establishes a fresh frame clock so preload time does not skip its
first displayed frame.

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
   To capture one addition without replacing existing thumbnails, use
   `--mode thumbnails --scene sheep_basket_visit`. Focused captures retain the
   original catalogue provenance and supply source hashes on the updated entry.
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

For the Fire Veinhold movie and individual clips at native 60 FPS, use
`python tools/capture_fire_veinhold_opening.py`, optionally with
`--shot-id island_orbit` or `--reduced-motion`. Its audio is reconstructed from
the production exports and clock, separately from the silent general-Gallery
review workflow.

See [review evidence](reviews/gallery/README.md) for the recorded regression result,
captured replay paths and remaining limitations.
