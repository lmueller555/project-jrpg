# Daisy — retained directional source

`idle_turnaround_concepts.png` is the generated appearance plate: front at top
left, left profile at top right, right profile at bottom left, back at bottom
right. The complete silhouettes and tails have transparent margins on every
side. The original generated source remains unchanged.

`tools/build_daisy_idles.py` exports each view using its registered crop, nearest
sampling, alpha threshold 128 and a limited shared palette. `export.json`
records the crops, occupied rectangles, eye/nose landmarks, layer ranges and
common foot anchor. Three full-frame retained layers reconstruct each native
idle exactly under `idle_DIRECTION_layers/`.

The dog canvas is 32×36. Front/back are 24 visible pixels tall and profiles 23,
slightly below Liam's 26. The wider transparent frame accommodates a natural
quadruped silhouette and whole fluffy tail. Both eyes are explicitly registered
in front, one in each profile, and none in back. The builder verifies frame
bounds, hard alpha, palette membership, eyes, baseline and layer reconstruction.

Requested facts are Daisy's name, family association, female pronouns, gray
coat with white/black spots, fluffy tail, floppy gray ears, and size slightly
smaller than Liam. Specific spot placement and all four idle designs are
approved by the user. Left/right spots are intentionally asymmetric and stay associated
with the correct anatomical side.

## Front walking source

`walk_front/parts/` retains four complete sets of tail, hind legs, torso, fore
legs, head and ear-tip layers. The approved front idle supplies face, markings,
fur and paw pixels. A four-beat quadruped template records paw joints and
support states; a short filled root keeps the tail connected through its sway.
Build using `python tools/build_liam_family_front_walks.py`. This front walk
is approved; no approved idle or palette is rewritten.

## Left, right and back walking source — approved

`tools/build_liam_family_directional_walks.py` reposes each approved directional
idle without rewriting it. New per-phase layers live under
`walk_DIRECTION/parts/`. Each view retains its own asymmetrical coat markings.
Three new 32×36 quadruped templates record the four-beat paw joints and support
states; paw shapes come from approved native pixels. Far legs are layered
behind the body, near legs in front, with a connected tail root and ear lag.

Native frames, recipes and layer paths are in the matching character animation
metadata. The [directional walk review](../../../../docs/reviews/liam_family_directional_walks/README.md)
contains synchronized looping comparisons. All four walking directions are approved.

## Four-frame left run — prototype source

`tools/build_liam_daisy_run_prototypes.py` composes approved native appearance
parts with new four-pose running joints. Per-frame layers are retained under
`run_left/parts/`. The animation recipes link source input hashes and pose templates.
See the [run prototype review](../../../../docs/reviews/liam_daisy_run_prototypes/README.md).
The left run is approved; no approved idle or walk is rewritten.

## Remaining running directions — approved

`tools/build_liam_daisy_directional_runs.py` builds four-frame front, right and
back runs from each approved directional idle and authored joint poses. New
per-phase layers are retained under
`run_DIRECTION/parts/`. Recipes record native input hashes
and template paths. The approved left-run assets and source layers are protected.
See the [directional run previews](../../../../docs/reviews/liam_daisy_directional_runs/README.md).
All four running directions are approved and merged into `main`.
