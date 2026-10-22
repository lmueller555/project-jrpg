# Mira — back-facing walk

Status: approved by the user in chat. The approved front walk is unchanged.

- `frame_01.png`–`frame_04.png`: four transparent native 24×36 frames.
- `spritesheet.png`: transparent 96×36 strip in playback order.
- `animation.json`: rectangles, 140 ms timing, `[12, 34]` foot anchor, and baked motion offsets.
- `walk_back_preview.gif`: enlarged 20× looping preview on a light background.
- `shared_motion_comparison.gif`: synchronized 12× loop with Caelan on the left and Mira on the right.
- `frames_review.png`: static 12× frame strip.
- `recipe.json`: source appearance, palette, template and part regions.

This cycle uses Caelan's approved back walk as the pose template. Its paired lower-leg/boot artwork is reused exactly; arm material masks preserve the source pose while applying Mira's pink shirt, rolled sleeve edges and bare forearms. Her shirt, waist and pouch are separate appearance parts. Her head, face where visible, ponytail and flower move together with the shoulders on passing frames 2 and 4, preserving neck height.

The new facing appearance is prepared under `../../../source/characters/mira/directions/`. These appearance inputs are approved; the walking poses themselves are assembled procedurally from retained masks, not independently generated. Her flower and tool pouch stay on anatomical left, visible in left profile and on viewer-left from behind, and hidden on the far side in right profile.

## Rebuild

From the repository root with `tools/requirements-assets.txt` installed:

```sh
python tools/build_character_walk.py mira --direction back
```

Add `--refresh-template` to regenerate the retained pose masks from the approved references. All motion offsets are already baked into the PNGs. The facing appearance, stride, clothing and accessory continuity are approved.
