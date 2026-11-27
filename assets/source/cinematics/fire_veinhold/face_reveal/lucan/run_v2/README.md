# Lucan frontal run revision

> Historical revision. The active selection is `../source_art_48.json`;
> [revision 3](../run_v3/README.md) records the current continuity corrections.
> The implementation status and source descriptions below refer to revision 2.

Status: implemented for in-game review, internally inspected; no claim of user
approval of these replacement drawings. The previous 24-pose source remains
unchanged as historical material.

`frames/frame_00.png` through `frame_47.png` are the active complete source
drawings. Each was separately authored with ImageGen; every figure has two arms,
two legs, anatomical-right sword and anatomical-left shield. The sword elbow
pumps between hip, waist and chest; the shield counterbalances with less range.
Contact keys are right0 and left24. The full two-step cycle is800ms at60Hz.
The ordinary world actor and costume are outside this revision.

`keys.png` and `key_*.png` are low-resolution motion references only. The final
`guided_key_*.png` are full-detail individual redraws. `guides/` and
`guide_recipe.py` are authoring diagrams, never runtime artwork or limb rigs.
All active runtime figures are single complete drawn images, not warped idle
pixels, detached limb transforms, blended frames or copied static heads.

The first strip attempts compressed too much motion into each strip. The first
individual keys also anticipated some end poses. `rejected_keys/` preserves
those unused attempts; they are not sources for the active export. Final
generation records and exact prompts identify the accepted drawings. ImageGen
originals are retained at their recorded generated-images paths; copied masters
remain unchanged. Helper repairs override helper initial records for13–17;
final4_result overrides earlier phase4 attempts. Phase36 was redrawn with a
lifted recovery boot and safe downward sword.

Registration is a constant0.63 whole-source density for all master dimensions,
with measured eyes, collar and belt points for complete-figure translation.
Occupied height, individual boots and garment bounds never determine scale.
The one authored support/flight weight chart is recorded in the source profile;
runtime must not add another bob. Source points are source-cell pixels; exported
points are768x1024 artwork pixels with anchor384,960. Near-transparent alpha
fringe is removed by the shared exporter at the recorded floor16, leaving the
original masters unchanged.

Reproduce landmark measurements with the authoring-only dependencies
`opencv-python-headless` and`numpy`, then register and export:

```sh
python assets/source/cinematics/fire_veinhold/face_reveal/lucan/run_v2/measure_landmarks.py
python assets/source/cinematics/fire_veinhold/face_reveal/lucan/run_v2/build_profile.py
python tools/export_prologue_faces.py --actor lucan
python tools/export_prologue_faces.py --actor lucan --check
```

Production loading/export does not require OpenCV. The fixed coordinates and
source hashes are preserved in`../source_art_48.json`.

The chronological registered drawings were inspected in twelve-frame groups,
including batch joins and47→0. Repairs address the phase7 and9 hand dips, early
phase4 hand rise, phase26 leg swap and premature39–41 recovery extension. The
12→18 toe-off arc received additional full-frame redraws. Isolated source boot
motion remains a perspective approximation; this frontal reveal crops the feet,
and the camera/bridge/side-shot travel review is recorded in the PR review.
Source count and unique files alone do not establish motion quality.
