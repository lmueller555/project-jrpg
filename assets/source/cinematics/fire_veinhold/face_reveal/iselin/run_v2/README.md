# Iselin — frontal cinematic run revision 2

> Historical revision. The active selection is `../source_art_48.json`;
> [revision 3](../run_v3/README.md) records the current continuity corrections.
> The implementation status and source descriptions below refer to revision 2.

Status: implemented for the owner's in-game Gallery review. Internal pose and
continuity checks do not represent user approval of the new drawings.

The current source profile is `../source_art_48.json`: 48 complete authored
frontal drawings, 800 ms for one full two-step loop, right-foot contact at 0 and
left-foot contact at 24. The 60 Hz display clock is independent of cadence.
The 1024×1024 transparent canvas and [512,960] anchor provide extra space for
flowing hair and mantle at the existing body size.

`generation_records.json` selects every current complete master and its exact
ImageGen generation and prompt. Most selected drawings are under `repairs/`.
`generation_records_initial.json` and `frame_00.png` … `frame_47.png` retain the
initial individual guided pass. Superseded repairs are archived unchanged in
`repairs/history/`; the current selection must be read from the profile rather
than inferred from a directory listing. `appearance_reference.png` preserves
the original painted identity independently of mutable runtime exports.

The current bank uses checked female-model keys at 0/12/24/36 and complete
ImageGen-authored midpoint drawings between actual neighboring poses. Secondary
midpoints subdivide those intervals. Each picture contains the whole resolved
character; no detached limb rig, idle warp, face paste or pixel interpolation
supplies final movement. The shared global sprite standard owns construction
rules; this folder records only this asset's implementation.

Initial planning experiments are retained as history. The eight-cell key sheet
and `guide_*.png` files communicate phase but did not guarantee correct drawn
anatomy or continuous movement. Broad in-between strips repeated extremes and
were rejected. Some individually guided drawings held an arm, changed hair
volume or repeated the wrong leading leg despite correct labels. A Crown-body
passing reference also changed Iselin's body proportions; the final passing key
uses the accepted Iselin female model with anatomical sides restored. Actual
painted limbs and body landmarks, rather than guide coordinates, determine the
internal review result.

`build_authoring_guides.py`, `build_repair_guides.py`, the reflected pose guide
and related diagrams are **authoring plans only**. They never enter the animation
renderer, transform the painted source or supply final pixels.

The correction moves both arm chains through their running action, preserves
right/left leg identity through contact and recovery, and gives loose hair,
heavy braid, mantle and coat distinct follow-through. The mantle stays on
anatomical right (viewer left), the braid on anatomical left (viewer right).
Hands do not carry the braid. Boot bands and geometric mantle trim retain the
approved clothing language.

`register_sources.py` measures face, neck and belt features. It applies one
uniform whole-drawing density per master, calibrated from actual face/model
landmarks and checked against neck/belt proportions, then whole-drawing placement
with the planned small weight offset. It does not fit occupied height, move
individual joints, stretch regions, paste a face or blend poses. The resulting
model landmarks and source match scores are in `registration_measurements.json`.

The documented `alpha_floor: 16` removes only generator fringe with alpha ≤16
before premultiplied uniform sampling. Raw masters remain unchanged. Visible
hair strands, material shading and outlines remain authored pixels.

Reproduce from the repository root:

1. Run this folder's `select_current_sources.py` to combine the generation records.
2. Run this folder's `register_sources.py` to record the selected model registration.
3. Run `tools/export_prologue_faces.py --actor iselin` for the ordinary export.

The shared running-polish review owns final production-shot motion, audio,
performance and Gallery lifecycle checks. The count of distinct PNGs alone does
not establish motion quality.
