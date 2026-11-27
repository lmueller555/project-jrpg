# Lucan frontal-run continuity repair

This is an asset-specific source and review record. The global sprite and
animation standard remains the authoring authority. The replacement drawings
are implemented for in-game review; this does not claim user approval of the
new performance.

The bank remains 48 poses over 800 ms, on a 768x1024 artwork canvas with anchor
384,960. Ground travel remains 4 m/s. Ordinary gameplay sprites are unchanged.
Complete ImageGen drawings replace poses 8–17, 35 and 38–40. Frame 41 selects
an existing complete drawing at its reviewed chronological position. Every
runtime pose is unique, with two attached arms/legs, right-hand sword and
left-arm shield. No final sprite uses a limb rig, regional paste, source warp,
cross-fade, duplicate endpoint or silhouette-based scaling.

`selected_generation_records.json` identifies every active replacement, its
original generation ID, exact prompt and retained input hashes. It records the
actual source chronology: the balanced exchange originally requested as 40 is
selected at 39, and the existing later extension originally labelled 40 is
selected at 41. The old runtime pose 40 is replaced, so this is not a duplicate.
`chronology.json` explains those two choices. The original v2 bank is retained.
Unused attempts in `history/` are historical sources, not active references.

The missing leg movement was established in actual whole-frame keys, then
subdivided against close drawn neighbors. When a generator repeated a held
extension or jumped to a fully tucked leg, actual same-character partial leg
shapes supplied clearer motion references. Some initial drawings changed the
head and torso inconsistently. They were redrawn against full-canvas accepted
model references rather than stretched to match boot bounds. Uniform whole-
master source density remains 0.63. Eyes, neck and belt register the complete
drawing, with the existing single authored weight chart.

Upper-body and lower-body reference crops, padded model references and pose
diagrams are authoring inputs only. ImageGen produced each final complete
character. Python only prepares references, measures actual artwork and performs
uniform whole-image export. It never pastes an accepted upper region into a
final sprite or moves an isolated leg.

The two leg exchanges, their neighboring joins, body size, sword grip, shield
carry and both limb chains were inspected in the actual selected drawings.
The 35 sword-arm drop was distributed through an actual intermediate pose.
Scoped palette edits remove isolated warm/bright flashes in 15, 35, 38 and 40.
Image-derived regression checks retain the fixed 65 artwork-pixel step guard,
early-progress checks, model/registration bounds and cycle coverage. The
three-tick concentration ratio remains a review diagnostic; a small overage
does not justify deforming a toe. Passing counts or tests alone does not
establish natural motion.

`reviewed_landmarks.json` retains actual selected PNG hashes, visible kneecap
observations and opaque boot-edge points for the contacts, corrected exchanges
and relevant boundaries. Its ROIs were checked against the painted anatomy;
they are separate from authoring target guides. Occluded heels and anatomical
ankles are explicitly unmeasured. Frame 27 documents the rear boot separately
from the front boot that can enter a broad midline ROI.

The contact cues remain 0 and 24. The intended support/compression intervals
are 0–6 and 24–30, toe-off 7–10 and 31–34, flight/exchange 11–16 and 35–40,
and approach 17–23 and 41–47. These labels are authoring intent, not proof of
3D contacts: the detailed actor is an upright billboard, the frontal shot crops
most soles, and source boot-Y mixes depth, articulation and height. This review
does not establish world-ground foot locking at 4 m/s. Do not distort anatomy
to make a 2D contour satisfy a supposed world-distance equation.

Reproduce the fixed source registration and export with the existing authoring
environment (`opencv-python-headless`, NumPy and Pillow for measurements):

```sh
python assets/source/cinematics/fire_veinhold/face_reveal/lucan/run_v3/register_candidates.py
python assets/source/cinematics/fire_veinhold/face_reveal/lucan/run_v3/build_profile.py
python tools/export_prologue_faces.py --actor lucan
python tools/export_prologue_faces.py --actor lucan --check
python assets/source/cinematics/fire_veinhold/face_reveal/lucan/run_v3/measure_reviewed_landmarks.py
python tools/audit_prologue_motion.py --actor lucan
```

The ordinary production exporter needs no OpenCV. The landmark helper writes
diagnostic PNGs under the temporary `lucan_run_v3_landmarks` directory. The PR
also reviews production-shot/Gallery rendering; full-body source loops are
diagnostics, not a substitute for the actual cinematic view.
