# Liam native activity artwork

Native, literal pixel contours in `drawings.json` plus the canonical named Liam
head/face. No legacy actor bitmap is enlarged, no cut-out limb is rotated, and no
inverse-kinematics renderer is involved. The JSON contains the final coordinates,
not a procedural skeleton. The canonical idles are read from
`assets/characters/named_hd/liam` so hair, face and palette remain one identity.

Run from repository root:

```
python assets/source/characters/liam/activity_hd/export.py --repo-root .
python assets/source/characters/liam/activity_hd/validate.py --repo-root .
```

Dependencies: Python, Pillow. Outputs are deterministic; `sha256.json` inventories
55 PNGs (52 activity frames and three lantern sheets containing91 cells).

## Coordinate contract

All manifest coordinates remain logical/world pixels. Density is declared by
`artwork_pixels_per_world_pixel: 2`. Activity rasters are192×192 for logical96×96,
anchor[64,66], standing native offset[104,72]. Lantern cells are80×96 for logical
40×48 with original anchor[20,38] and original logical sheet rectangles. Loaders
must double the rect for slicing but retain logical contact and draw offsets.

Blocks preserve durations, contact frame2 (zero-based), hands and handoffs.
Rise is the reverse of kneel; support soles remain planted at native y140.
Invitation and sleeping retain original phase durations and head placement.
Bed frames are ACTOR-ONLY. The scene owns its actual existing HD bed/quilt overlay;
no obsolete bed furniture is baked into this bank.

Lantern timing, hands, prop rectangles, action facing, world contacts and ownership
remain inherited. Only actor source provenance, old arm-rig joints and preservation
claims were removed. Existing lantern `frame` and `extras` layers remain the prop
source and are nearest2× compatibility art, explicitly not a native actor redraw.
Rear carry draws the prop behind the actor; the other directions draw it in front.

Scope excludes Daisy, blocks/box/furniture, bowls, all other characters' lantern
sheets, scripts/cues/ownership, and Sanctuary gardener. Runtime integration is a
separate change. `status: candidate` is intentional until integration review.
