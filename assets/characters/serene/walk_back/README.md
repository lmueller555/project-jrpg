# Mother Serene — back walk

**Awaiting review.** Four native 24×36 frames at 140 ms each (560 ms loop), foot anchor `[12,34]`, offsets baked into pixels.

`walk_back_preview.gif` is an opaque 20× nearest-neighbor loop; `frames_review.png` is a 12× strip. `spritesheet.png` is a native 96×36 sheet in playback order. `animation.json` records status, phase rectangles, eye/hem/boot landmarks, timing and layer provenance. `shared_motion_comparison.gif` shows Caelan at left and Serene at right, synchronized at 16×.

The approved directional idle supplies head, bun, mantle, costume colors and apron details where visible. The shared directional template supplies stride silhouettes and timing; head and the whole mantle rise together on passing phases. Costume row poses add one-pixel hem sway and shorten the green hem in passing poses, preserving patch-bearing rows. Profile arm masks omit the source character's neck; still-hand regions are filled with sage cloth under the moving arms. The back keeps its sage skirt and has no eye landmarks or front apron panel.

Rebuild with `python tools/build_serene_walk.py --direction back`; rebuild all three new walks and the combined board with `--direction remaining`. Run `python tools/test_serene_walk.py` after building all directions. Approval lives in `recipe.json`. Existing idles, palette and shared templates remain read only.
