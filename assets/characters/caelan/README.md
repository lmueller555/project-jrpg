# Caelan — directional idle sprites

The front idle design was explicitly approved by the user in chat. Its original pixels remain unchanged. The back, left, and right idle views are new proposals awaiting review; walking animations have not started.

## Files

- `idle_front.png`: approved transparent 24×36 front idle.
- `idle_left.png`, `idle_right.png`, `idle_back.png`: draft transparent 24×36 directional idles. Left/right describe the direction the character faces on screen.
- `idle_directions.png`: transparent 96×36 sheet, ordered front, left, right, back.
- `idle_directions.json`: frame rectangles, foot anchors, and approval status; a standalone asset description, not an engine integration.
- `idle_directions_review.png`: labeled 12× enlargement on a light background for review, not a runtime texture.
- `idle_front_preview.png` and `idle_front_review.png`: earlier enlarged front views.

Every frame uses hard transparency, colors from the approved front palette, and a shared foot anchor at `[12, 34]` in frame coordinates. Frame bounds are 24×36; the visible character occupies a smaller area within that transparent frame. The reference terrain scale discussed in chat is 24×24 pixels.

## Appearance

Chestnut hair, ivory tunic and sleeves, teal outer tabard, ochre trim, brown belt/pouch and boots, and dark trousers. The hip pouch should remain on the character's anatomical left as views and animations are refined. New views must be reviewed for outfit continuity and silhouette before animation.

Generated source concepts are retained in `../../source/characters/caelan/`. They are high-resolution references; the native game-sized sprites are the 24×36 files here. Native exports use nearest-neighbor sampling, hard alpha, and palette mapping. Review images use whole-number enlargement without smoothing.

This artwork approval does not alter the preserved story documents or their character-name spelling. There is currently no game runtime.
