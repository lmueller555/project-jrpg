# Native Iselin idle candidate

Four newly authored complete idle drawings, created with `image_gen.imagegen`
for review after the restoration to PR #206. `turnaround.png` retains the
original generated sheet; do not overwrite the previous approved HD masters.

The source uses Caelan and Mira's native idles as the pixel-style references,
and Iselin's existing front/left/back drawings for character identity. The
brief specifies a white-haired, blue-eyed regent wearing a blue/silver royal
coat, thin black exterior contours, a mantle on anatomical right and a forward
braid on anatomical left. The four source columns are front, left, right and
back. The profiles are separately drawn, preserving the asymmetric clothing.

`tools/export_iselin_native_idles.py` performs hard-alpha extraction and
uniform nearest-neighbor registration of whole drawings. A single source
crown/sole interval sets the same body scale across all four facings. It does
not paint anatomy, mirror a profile or assemble detached limbs. Registration,
reference paths and source/export hashes are recorded in `registration.json`.

Exports are staged in `assets/characters/iselin/native_idles/`: four 24×36 RGBA
frames, one artwork pixel per world pixel, draw anchor `[12,30]`, foot anchor
`[12,34]` and the existing 8×4 world collision probe. Their local manifest has
no walks or high-resolution override. The current campaign bank is unchanged.

In-game comparison evidence and reproduction instructions are in
`docs/reviews/iselin_native_idles/README.md`. The user approved all four idles.
Walking, cinematic conversion and live activation remain separate work.
