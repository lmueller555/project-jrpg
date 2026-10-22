# Male NPC 03 — back-facing walk

Status: approved by the user in chat. This palette's idles and front walk remain approved.

Gray hair, slate shirt, brown trousers and brown boots. These four 24×36 frames apply the existing approved palette to the approved base male back cycle. The approved palette idle supplies its directional head and appearance. The shared template keeps the stride, arm motion and coordinated head-and-shoulder bob identical across palettes. Timing is 140 ms per frame, with the shared `[12, 34]` foot anchor and baked upper-body offsets `[0, 0]`, `[0, -1]`, `[0, 0]`, `[0, -1]`. Skin, eyes, belt and boots retain their original colors.

- `frame_01.png`–`frame_04.png`: native transparent frames.
- `spritesheet.png`: native 96×36 playback strip.
- `animation.json`: frame rectangles, timing, phases and approval status.
- `walk_back_preview.gif`: 20× enlarged looping preview.
- `frames_review.png`: 12× static phase strip.
- `shared_motion_comparison.gif`: synchronized 12× comparison with Caelan on the left.
- `recipe.json`: derived recipe, palette provenance and persistent approval status.

Review this direction across all three palettes in `../../male_walk_back_variants_review.gif`, or every direction in `../../male_walk_all_variants_review.gif`. Rebuild with `python tools/build_npc_walk_variants.py --direction back`; add `--direction all` instead to also rebuild the complete review grid and per-character directional sheets. The approved base cycle is unchanged.
