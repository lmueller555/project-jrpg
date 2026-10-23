# Mother Serene — front walk

**Awaiting review.** Four 24×36 frames, 140 ms each, looping in 560 ms. Foot anchor `[12,34]`; offsets are already baked into the pixels.

- `walk_front_preview.gif`: opaque 20× nearest-neighbor loop.
- `frames_review.png`: opaque 12× strip of all four phases.
- `shared_motion_comparison.gif`: synchronized 16× Caelan/Serene loop, Caelan on the left.
- `spritesheet.png`: native 96×36 sheet, phases in playback order.
- `animation.json`: timing, frame rectangles, bob/eye landmarks and layer provenance.
- `recipe.json`: review status, read-only inputs and costume-specific row poses.

The shared front template supplies stride silhouettes, arm poses, timing and the one-pixel passing bob. Head and the whole shoulder mantle move together, preserving the neck. Sage sleeves end in linen cuffs. Skirt rows retain the approved apron, pocket and repaired patch; lower rows sway one pixel on contact phases. Passing poses shorten the green hem without dropping a patch row. The shared dress leg adapter supplies bare calves and short brown boots.

Run `python tools/build_serene_walk.py`, then `python tools/test_serene_walk.py`. Approval lives in `recipe.json`. The approved idles, palette and shared templates are read only. Other walking directions are not included.
