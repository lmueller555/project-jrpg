# Mira — front walk

Status: draft awaiting visual review. The corrected front idle is the appearance source; no new image-generated walking frames are used.

## Files

- `frame_01.png`–`frame_04.png`: four transparent native 24×36 frames.
- `spritesheet.png`: transparent 96×36 strip in playback order.
- `animation.json`: rectangles, 140 ms timing, phase names, foot anchor, and baked upper-body offsets.
- `walk_front_preview.gif`: enlarged looping 480×720 preview (20×, light background).
- `shared_motion_comparison.gif`: synchronized 12× loop, Caelan on the left and Mira on the right.
- `frames_review.png`: static 12× enlargement of all four frames.
- `recipe.json`: palette, source-part regions and shared-template selection.

## Assembly

`tools/build_character_walk.py` assembles this cycle from the shared front-walk pose masks. Mira's exact head pixels—including both corrected eyes, the ponytail and the flower—move as one layer. The head, neck, shoulders and upper chest rise by one pixel on passing frames 2 and 4. Shirt material bridges to the stationary waist rather than extending the neck.

Arm silhouettes follow Caelan's approved poses, with Mira's pink sleeve colors, darker rolled sleeve edges, and bare forearms. Her own shirt pixels seed the torso; the recipe fills regions previously hidden by arms. The belt/pelvis and tool pouch are separate parts, and arms can overlap the pouch. The matching lower-leg/boot artwork is reused exactly from Caelan's four phases.

Appearance parts and the four pairs of materialized arm layers are retained at `../../../source/characters/mira/walk_front/parts/`. Their combined walking pose differs from the idle naturally; the idle itself is unchanged. All images are ordinary PNGs; no runtime integration is included.

## Rebuild

From the repository root, with Pillow installed from `tools/requirements-assets.txt`:

```sh
python tools/build_character_walk.py mira
```

Use `--refresh-template` to also rebuild the shared material masks from the approved Caelan references. Frame offsets in metadata describe motion already baked into the pixels; do not apply them again.
