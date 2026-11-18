# Iselin native left stop and settle source

`stop_source.png` retains the original `image_gen.imagegen` output unchanged:
eight complete left-facing stopping drawings on a 1536×1024, four-column,
two-row grid. Each cell is 384×512. The approved native left walk's final frame
and left idle supplied the character and transition references. The near side
is anatomical left, with its forward braid; the mantle remains on anatomical
right. Both arm swings damp as the trailing leg closes behind the planted lead
leg. Later poses relax the coat, braid and shoulders into standing.

The existing [sprite and animation standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md)
owns construction guidance. This file records the local export recipe.

## Registration and preservation

`recipe.json` records every whole-drawing crop, a shared nominal sampling density
of 0.08, a 31×41 nearest-neighbor sample and common `[-4,-2]` origin on the native
24×36 canvas. The source registration point `[192,462]` maps to `[11,35]` in this
sampling grid; it is distinct from the unchanged logical ground reference
`[12,34]`. The shared body-grid translation aligns torso and stance with the
approved native design. Individual foot bounds never set pose scale or origin.

After complete-drawing registration, rows 0–12 retain exact approved head/neck
pixels from walk frame 16 for the first six drawings and the left idle for the
last two. This keeps head proportions stable and supplies the single-pixel rise
from walking settle into standing. The neck seams were visually inspected.
Arms, braid tail, torso, coat and legs below that region remain the complete
authored drawings. No isolated moving limb is constructed, rotated or stretched.

A single nearest-RGB palette mapping brings body colors into the combined
approved handoff/idle palette; protected head pixels remain exact. Hard alpha
uses threshold 220. `registered/` contains the eight resulting 24×36 PNGs for
inspection. Original generated pixels are retained separately in the source.

`tools/build_regent_iselin.py` uniformly presents those drawings on the existing
80×96 ground-camera canvas at scale `80/34`, anchor `[40,92]`. The stop adds no
ordinary-world collision, size or walking changes. `registration.json` records
the recipe/source/dependency hashes, native body registrations and all exports.

## Clip timing

The `stop_left` action begins with the exact existing `walk_left_15.png` camera
frame for 40 ms, continues through all eight new drawings at 60 ms each, holds
the final drawing for 60 ms, then recovers to exact `stand_left` for 120 ms.
Its persistent rest also selects `stand_left`. Total action duration is 700 ms.

The arrival gate binds it to the last half-second of deceleration and a further
200 ms of settling, preserving the existing route endpoint. The complete
walking cycle remains unchanged. Rebuild or verify from the repository root:

```sh
python tools/build_regent_iselin.py
python tools/build_regent_iselin.py --check
```
