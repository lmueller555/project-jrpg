# Crown soldier: frontal run continuity correction

`../source_art_48.json` selects 48 unique complete painted figures over 800 ms,
with anatomical right contact at frame 0 and left contact at frame 24. The
canvas remains 768×1024 and the ground anchor remains `[384,960]`. The sword is
in the anatomical right hand (viewer left); the plain boss shield is on the
left forearm. Steel, navy cloth and brown leather retain the Crown identity.

Four approved complete contact/recovery sources (0, 12, 24, 36) remain byte
identical. ImageGen drew the other 44 complete figures, using close actual
painted poses and the corresponding approved upper-body action as references.
There is no detached limb assembly, image warp, regional pixel restoration,
endpoint blend or duplicate-pose filling. A final complete frame 30 correction
bridges the sword-arm carry after independent review found a visible dip.

`selected_sources.json` owns the selection and exact generation prompts,
reference paths/hashes, generation IDs and source hashes. Individual generation
records and root/helper aggregates preserve successful and rejected attempts.
Unselected sources and `history/` are authoring evidence, not runtime frames.
Raw ImageGen output bytes remain unchanged; `selected_source_integrity.json`
records that comparison for every selected master.

`register_sources.py` measures painted eyes, neck and belt. New complete masters
use one calibrated 0.70 uniform density; retained keys keep their approved 0.60
density and registration. The whole figure translates together to its approved
eye phase. Independent neck/belt observations check the projected body model.
The tool never fits occupied height, ground clearance or individual limbs.
Premultiplied-alpha whole-image sampling and the exporter's alpha floor 16
remove only near-transparent fringe. No procedural anatomy enters the artwork.

`authoring_bounds/` contains immutable whole-figure reference exports. Colored
joint/arrow guides are explicitly source-only plans; their coordinates are not
observed animation measurements and their pixels never enter final drawings.
`reviewed_sole_observations.json` and `reviewed_hand_observations.json` instead
record actual painted landmarks/windows, bound to the selected raw hashes.
These separate crossing feet, gloves and equipment during pixel-based checks.
They do not relax the regression caps or certify visual quality by themselves.

Reproduce from the repository root:

```sh
python assets/source/cinematics/fire_veinhold/face_reveal/crown_soldier/run_v3/register_sources.py
python tools/export_prologue_faces.py --actor crown_soldier
python tools/export_prologue_faces.py --actor crown_soldier --check
```

The old actual 10–12 boot overshoot/reset remains a negative regression fixture.
Chronological source review checks both connected leg chains, support/flight,
the loop, body proportions and sword/shield carry. Independent review accepted
the repaired 9–12, 14–24 and 24–47 leg intervals; production-shot framing and
normal/slow playback remain part of integration review. The implementation is
for the player's in-game Gallery review, not a claim of prior player approval.
