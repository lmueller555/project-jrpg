# Grain workers: source and export

`pose_reference.png` is the unmodified image-generation work-pose reference made
for this change, using the approved male_02 and male_03 front review images as
appearance references. Requested poses were lifting, carrying, placing,
stretching, checking rope, inspecting grain, assisting, and resting; the prompt
specified the existing rust/charcoal and slate/brown costumes, planted feet,
clear hand grips, hard pixels, and no scenery or lettering.

This reference guides the grips and weight shifts. Runtime exports deliberately
retain the approved villagers' layered heads, shirts, waists and legs rather
than replacing the approved designs with the generated plate. The existing
walk frames remain read-only. `tools/build_grain_workers.py` assembles the work
poses from those appearance parts and explicitly registered arm joints, on a
40×44 transparent canvas with the common [20,38] foot anchor. Carrying reuses all
four approved leg phases; waiting in a blocked lane holds the first phase.
The small sack and cover are controller-owned props, separate from the bodies.

The new action exports have **review** status; this does not relabel any source
or existing villager artwork as newly approved. Normal-zoom gameplay evidence
is in `docs/reviews/grain_farm/`.

Rebuild with `python tools/build_grain_workers.py` (Pillow required). Runtime
needs only Pygame and reads the checked-in PNGs.
