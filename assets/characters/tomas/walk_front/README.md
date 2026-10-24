# Tomas — front walk

**Awaiting review.** Four native 24×36 frames, 140 ms each (560 ms loop), foot anchor `[12,34]`. Motion offsets are baked into the pixels.

- `walk_front_preview.gif`: opaque 20× nearest-neighbor looping review.
- `shared_motion_comparison.gif`: synchronized 16× Caelan/Tomas comparison with a shared foot baseline.
- `frames_review.png`: opaque 12× strip of the four phases.
- `spritesheet.png`: native 96×36 sheet in playback order.
- `animation.json`: status, timing, frame rectangles, height, eye/patch landmarks and ordered source layers.
- `recipe.json`: approved appearance inputs, shared pose template, arm registration, boot boundaries and per-pose patch placement.

Tomas retains his approved head, collar, tunic, belt and green eyes. The shared walk supplies phase timing, leg silhouettes and arm poses. Arm regions are nearest-neighbor registered from 24×12 to 20×11 and placed at `[2,15]`, fitting his narrower shoulders and shorter reach. His head, chest and shoulders rise together by one pixel on passing poses, preserving the neck.

His visible height is 32 pixels on contacts and 33 on raised passing poses, consistently two pixels shorter than Caelan in the matching phase. The patch stays on the front of his anatomical left knee (screen right), changes position and apparent area with the foreshortened leg, and remains inside visible trouser cloth. Boots keep per-leg ankle boundaries. The source calf/boot adapter receives dark trouser colors in its upper-leg material slots.

Run `python tools/build_tomas_walk.py`, then `python tools/test_tomas_walk.py`. Approval lives in `recipe.json`. Approved idles, palette, other characters and shared templates are read only. This milestone adds only the front walk.
