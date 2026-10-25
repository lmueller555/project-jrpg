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
and both parents 34, inside 24×36 frames with baseline row 34. New directions
are awaiting review separately from the approved front designs.
