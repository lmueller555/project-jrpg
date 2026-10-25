# Liam and his parents — retained front-idle source

`front_idle_concepts.png` retains the generated family appearance plate, ordered
mother, Liam, father. It supplies the new character designs, separate from the
existing approved cast. The native game exports are in the individual `liam`,
`liam_mother` and `liam_father` character folders.

The requested story facts are Liam's age of **8** and both parents being in
their **mid-30s**. Parent names, surname, home and quest association are unassigned.
The front-facing idle designs, including clothing, palettes, hair and visible
heights, are approved by the user.

Run `python tools/build_liam_family_idles.py` to reproduce the native sprites.
The builder uses the existing Tomas band-sampling/material-mapping helper,
records its crop/material/eye registration in `export.json`, and retains four
full-frame layers per character under the named subfolders. Alpha is thresholded
at 128; each body band maps to its declared palette. Face windows keep chins
skin-colored, and two explicit pupil/iris landmarks keep both eyes readable.

Each native frame is 24×36 with foot anchor `[12,34]`. Liam occupies 12×26 pixels
from row 9, mother 14×34 from row 1, and father 16×34 from row 1. The child's
shorter body and legs and larger relative head preserve his younger proportions.
The builder verifies silhouette bounds, opaque/transparent alpha, palette
membership, eye colors and exact reconstruction from the four source layers.

## Directional idle source

`turnaround_concepts.png` retains the generated nine-view continuation of the
approved front designs. Rows are mother, Liam, father; columns are left, right,
back. `turnaround_export.json` records crops, material bands, face/collar/braid
windows, eye landmarks and layer ranges for the new views.

Run `python tools/build_liam_family_turnarounds.py`. It reads the approved
palettes and front files without rewriting them. Each new view has four layers
under `CHARACTER/idle_DIRECTION_layers/`. Liam stays 26 visible pixels tall,
and both parents 34, inside 24×36 frames with baseline row 34. All left, right
and back designs are approved, alongside the existing approved fronts.

## Front walking source

`tools/build_liam_family_front_walks.py` registers the shared humanoid template
to the approved front idles. Per-frame body, arms, legs and clothing layers
are retained under `CHARACTER/walk_front/parts/`. Runtime recipes record the
source idle hash, template, arm registration, body regions, boot projections
and combined head/shoulder bob. The mother's apron is posed with the dress.
The front walks are approved; approved idles and palettes are read-only.

## Left, right and back walking source — approved

`tools/build_liam_family_directional_walks.py` reposes each approved directional
idle without rewriting it. New per-phase layers live under
`CHARACTER/walk_DIRECTION/parts/`. Human arm/leg silhouettes use the shared
24×36 humanoid directional templates; clothing and head/shoulder bob follow
the approved character proportions.

Native frames, recipes and layer paths are in the matching character animation
metadata. The [directional walk review](../../../../docs/reviews/liam_family_directional_walks/README.md)
contains synchronized looping comparisons. All four walking directions are approved.

## Four-frame left run — prototype source

`tools/build_liam_daisy_run_prototypes.py` composes approved native appearance
parts with new four-pose running joints. Per-frame layers are retained under
`liam/run_left/parts/`. The animation recipes link source input hashes and pose templates.
See the [run prototype review](../../../../docs/reviews/liam_daisy_run_prototypes/README.md).
The left run is approved; no approved idle or walk is rewritten.

## Remaining running directions — review pending

`tools/build_liam_daisy_directional_runs.py` builds four-frame front, right and
back runs from each approved directional idle and authored joint poses. New
per-phase layers are retained under
`liam/run_DIRECTION/parts/`. Recipes record native input hashes
and template paths. The approved left-run assets and source layers are protected.
See the [directional run previews](../../../../docs/reviews/liam_daisy_directional_runs/README.md).
These new directions await user approval.
