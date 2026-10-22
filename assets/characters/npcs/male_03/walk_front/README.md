# Male NPC 03 — front walk

Status: approved by the user in chat. This NPC's directional idle designs and palette remain approved.

Gray hair, slate shirt, brown trousers and brown boots. These four 24×36 frames apply the approved palette to the approved base male front-walk recipe. The shared stride, frame timing, silhouette and coordinated head-and-shoulder bob are identical. The approved palette idle supplies the head and waist; the belt, skin and boots retain their original colors.

- `frame_01.png`–`frame_04.png`: transparent native frames.
- `spritesheet.png`: native 96×36 strip.
- `animation.json`: four 140 ms phases, shared `[12, 34]` foot anchor and baked bob offsets.
- `walk_front_preview.gif`: 20× looping preview.
- `frames_review.png`: 12× static frame strip.
- `shared_motion_comparison.gif`: synchronized 12× comparison with Caelan on the left.
- `recipe.json`: derived pose recipe, palette provenance and persistent animation approval status.

Review all three male NPCs together in `../../male_walk_front_variants_review.gif`. Rebuild the palette walks and combined comparison with `python tools/build_npc_walk_variants.py`. The original approved base animation is unchanged.
