# Tomas — back walk

**Approved.** Four native 24×36 frames, 140 ms each (560 ms loop), foot anchor `[12,34]`, motion baked into pixels.

`walk_back_preview.gif` is an opaque 20× loop; `frames_review.png` is a 12× strip; `spritesheet.png` is a native 96×36 sheet in playback order. `animation.json` retains timing, frame rectangles, height, eye/patch landmarks and ordered layer provenance. `shared_motion_comparison.gif` shows approved Caelan on the left and Tomas on the right at 16×, synchronized with a shared baseline.

The approved back idle supplies appearance. The shared directional template supplies stride and timing, while the approved front walk's arm registration fits Tomas's proportions. Head, collar and shoulders share the passing bob; profile masks omit the source character's neck. Tomas stays two pixels shorter than Caelan in matching phases (32 visible rows on contact, 33 while raised). Boots follow directional leg lengths. The patch is on the front of the left knee and faces away from the back view; no eyes are visible.

Run `python tools/build_tomas_walk.py --direction back` for this pack, or `--direction remaining` for all three new walks and the combined board. Run `python tools/test_tomas_walk.py` after building all directions. Approval lives in `recipe.json`. Approved idles, palette, front-walk output and shared templates remain unchanged.
