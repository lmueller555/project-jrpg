# Eldenmere — animated stream and banks

Status: stream-and-bank artwork approved by the user in chat. This is the first stream-and-bank milestone of the staged water/infrastructure pack.

Native terrain remains 24×24, with approved 24×36 characters. Muted blue-green water contains small drifting, fading reflection clusters. Banks, the earthy lip and the shallow-water rim remain stationary. There are six phases at 200 ms each: a 1.2-second seamless playback loop. Two compatible surface variations reduce obvious repetition while using one shared phase across connected water.

## Review

- `review_scene.gif`: the updated scene at 3× scale, with a pool, narrow branch, stream bends, approved grass/dirt and all eight characters.
- `review_scene.png`: first phase of that enlarged scene.
- `review_scene_frame_01.png`–`review_scene_frame_06.png`: six native 480×384 scene frames.
- `review_scene.json`: exact ground masks, water masks, surface choices, character positions and playback timing.
- `water_cycle_review.gif`: a 6× close-up of a small pool, showing the complete water cycle and fixed banks; `_review.png` is its first phase.
- `bank_47_review.png`: all 47 bank shapes with water over approved grass at 6× scale.

The scene is an art/scale/seam demonstration rather than a canonical Eldenmere map or playable game. Two characters are repositioned onto dry ground to make room for the water. Every character uses the existing approved native sprite unchanged. Irrigation modules, stone terraces, bridge, gate and mill remain later milestones following this approved stream milestone.

## Native exports

- `banks_47.png`: 47 stationary bank/shallow overlays in a 192×144 atlas (8 columns, 6 rows; last slot transparent).
- `water_masks_47.png`: corresponding hard-alpha masks for the water surface.
- `surface/variant_00_frame_01.png`–`variant_01_frame_06.png`: two sets of six opaque 24×24 water textures. Both have matching border pixels in every phase.
- `water_surface.png`: 144×48 surface sheet: six phases as columns, two variations as rows.
- `water_47/frame_01.png`–`frame_06.png`: six complete 192×144 atlases using surface variation 00. These contain 282 composed 24×24 tile frames.
- `water_blob_47.png`: those six atlases stacked into a 192×864 sheet.
- `tileset.json`: 47 shape rectangles, source-quarter references, the 256-neighbor lookup, phase timing, surface variation references and layer order.
- `palette.json`: approved ground colors plus the new proposed water ramp.

For a layered renderer, draw grass/dirt, then the selected surface clipped by its water mask, then the stationary bank/shallow overlay, then characters or props. Variation 01 uses the same bank atlas and masks as variation 00. The complete baked atlases provide a simple variation-00 export; the review scene uses both variations through the layered representation.

Neighbor bits match the approved dirt pack: **N=1, NE=2, E=4, SE=8, S=16, SW=32, W=64, NW=128**. Diagonals count only when both adjacent cardinal neighbors connect. `lookup_256[raw_mask]` selects one of 47 canonical shape rectangles in every phase. Keep the same global phase index for all connected water; choose surface variation independently without altering that clock. Ripple motion is already baked into the texture pixels.

Rebuild and check from the repository root:

```sh
python tools/build_eldenmere_stream.py
python tools/test_eldenmere_stream.py
python tools/test_eldenmere_terrain.py
```

The new source recipe controls artwork approval status. Source material, extracted ripple masks and forty oriented bank/water quarter pieces are retained under `../../../source/terrain/eldenmere/stream/`. Existing approved terrain, characters and story files are read only.
