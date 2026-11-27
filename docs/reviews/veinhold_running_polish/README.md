# Veinhold running correction

Historical review of PR #663. The subsequent
[motion continuity correction](../veinhold_motion_continuity/README.md) records
the leg-transition and secondary-motion defects found after this revision,
their replacements and the additional regression evidence. The results below
describe this original revision, not a visual approval of later artwork.

This revision replaces the frontal performance reviewed in
[the original face reveal](../veinhold_face_reveal/README.md). That review's
passing timing/cache checks did not establish convincing motion. The player
identified Lucan's held arms, excessive cadence and weak hair/clothing action.

## Production contract

- Shot 6 remains three seconds (39–42s), using its complete side drawings at
  24 poses / 800 ms. Each source pose has two 60 Hz exposures.
- Shot 7 remains five seconds (42–47s), using 48 complete frontal drawings per
  character over 800 ms. The camera retains the 1.5-second downward reveal.
- Both use 4 m/s travel and one continuous contact clock. The side phases are
  `0`, `1/6`, `.3` seconds; frontal phases are `(3 + side_phase) % .8`.
- Side travel starts at 22.26 m and reaches the frontal marker at 34.26 m.
  World starting markers remain independent of velocity and camera drift.
- Side deck density is 942.15 pixels/m, retaining the existing drawing bank's
  ground excursion per cycle at half its old cadence. The camera's final
  drift preserves the trailing soldier's visibility and ten-foot formation.
- The 0–39s picture sources and all twelve alert/running WAVs are retained.
  Contact scheduling after 39s changes from 120 to 60 total cues over both runs.

## Construction and runtime

The current source profiles are
`assets/source/cinematics/fire_veinhold/face_reveal/<actor>/source_art_48.json`.
New complete painted masters, authoring references and instructions live in
each actor's `run_v2/` folder. Anatomical guides constrain image authoring;
they do not render limbs or replace final painted pixels. Whole drawings own
their anatomy, overlapping equipment, hair and clothing. The exporter performs
documented crop, low-alpha fringe removal, uniform sampling and registration.
Original masters remain unchanged. Earlier 24-pose sources and reviews are
history rather than the active construction recipe.

Lucan and the soldier retain 768×1024 RGBA canvases with `[384,960]` anchors.
Iselin uses 1024×1024 with `[512,960]`: the extra transparent width accommodates
her flowing silhouette without shrinking her body. Outline/face detail and
body landmarks are reviewed at native cinematic size. Runtime collision and
ordinary overworld sprites are outside this change.

The final shot is baked offline into 301 inclusive 960×640 full-performance
samples. The builder starts with fresh painted scenery and projects complete
figures through the same camera/whole-drawing path as the source reviewer.
Repeating the builder never composites onto a previously baked character.
Normal and Reduced Motion share the essential reveal and its exact timing.

The Gallery streams those final frames through eight slots, reserving at most
18.75 MiB for decoded pictures and pending loads. It reserves zero separate
actor images. The larger source bank is an offline authoring resource.
A deterministic performance signature binds the bank to its camera, formation,
phase/timing metadata and declared exported PNG hashes. Missing baked markers
or stale timing/pixel contracts fail validation instead of silently displaying
scenery-only or out-of-sync movement.

## Review boundary

The user requested implementation and merging for subsequent in-game review,
without a new preview delivery. Internal source/motion and Gallery checks are
still required by the global animation standard. This is not a claim of user
approval of the replacement drawings.

The retained side drawings have historical local stance-foot irregularities;
their cadence and average deck travel are calibrated here. They are not claimed
to achieve perfect per-pixel foot locking at every pose.

## Reproduction

Run with the game's Python environment from the repository root:

```sh
python tools/export_prologue_runners.py --check
python tools/export_prologue_faces.py --check
python tools/build_prologue_face_environment.py --check
python tools/build_prologue_alert_audio.py --check
```

For changed sources, omit `--check`, exporting drawings before the final bank.
The active full-frame recipe is
`assets/source/cinematics/fire_veinhold/face_reveal/environment/performance_recipe.json`.
The earlier environment-only recipe retains its original revision's facts.

Optional internal Gallery capture commands (no capture is needed to play):

```sh
python tools/capture_fire_veinhold_opening.py --shot-id face_reveal --out /tmp/run-review
python tools/capture_fire_veinhold_opening.py --shot-id face_reveal --reduced-motion --out /tmp/run-review-rm
python tools/capture_fire_veinhold_opening.py --out /tmp/run-complete
```

Review in the title-screen Gallery under **Fire Veinhold — The Infiltrators**, or
**Fire Veinhold — Complete Cutscene** for the continuous sequence. The preceding
shot is **Fire Veinhold — Running the Bridge**.

## Completed validation

All **215 targeted tests passed**: [144 cinematic/asset/audio checks](core_tests.log)
and [71 Gallery checks](gallery_tests.log). The source exports, all 301 final
native frames and the audio exports reproduce exactly. See the export/build
logs in this directory. Raw generation prompts retain their exact bytes;
the scoped `.gitattributes` rule treats these text captures as source data.

The source review traced actual wrists, knees and boots through both halves,
checked body proportions, equipment handedness, braid/mantle attachments and
the loop seam, and corrected the large held-pose exchanges and silhouette pops.
Final chronology is selected from the actual complete drawings, rather than
assuming their original generation labels describe correct gait order.
Native production checkpoints at 1.5, 3 and 5 seconds were inspected in the
camera composition alongside those chronological source comparisons.

[Capture validation](capture_validation.json) records actual save-disabled
Gallery playback: normal and Reduced Motion each produce **300 frames over
five seconds**; the complete film produces **2,820 frames over 47 seconds**.
All use 960×640 at 60 FPS, complete naturally, return to the Gallery and write
no journey/settings files. Completion drains the face image cache to zero.
Only the complete-film, running-bridge and infiltrators thumbnails are refreshed.
The [audio probe](audio_validation.json) records all 60 unique contact cues with
eight mixer channels and the unchanged audio prefix before 39 seconds. Audio
capture is an offline reconstruction, not physical-device listening evidence.

The [paced native profile](realtime_profile.json) ran 300 frames at real 60 Hz
deadlines using SDL dummy, after the test/encoding jobs completed. Controller
updates plus native rendering averaged **2.32 ms**, with **3.91 ms p95** and
zero foreground decoder waits. One transient frame reached **16.84 ms**.
The face cache peaked at **19,660,800 bytes (18.75 MiB)** and returned to zero.
Startup was 318 ms. These measurements exclude Game UI/scaling, video encoding
and startup from per-frame work; they describe this machine and do not establish
a hardware-independent frame-rate guarantee. Unpaced capture timings in the
capture JSON files are separate measurements.

Movies used for internal integration checks remain temporary; this revision
delivers in-game Gallery playback rather than another preview package.
