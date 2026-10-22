# Female NPC 01 — front walk

Status: draft for user review. All four idle designs and palettes remain approved.

Four 24×36 frames follow the shared front-walk stride and arm masks, at 140 ms per frame with a looping 560 ms cycle and `[12, 34]` foot anchor. The approved dark-haired face, blue irises and low bun are retained. Passing frames 02/04 raise the head, neck, shoulders and upper bodice together by one pixel, preserving neck height. Offsets are baked into the frames.

The blue dress uses dedicated skirt poses. The lower skirt sways one pixel opposite the leading leg on contacts. On passing frames, its hem lifts from row 28 to 27; the waist remains fixed. The dress texture comes from the approved idle, with covered hand areas filled using dress colors. Bare calves and brown ankle boots use the exact shared stride silhouette, with per-leg boot heights so the shortened rear foot remains visible below the hem.

- `frame_01.png`–`frame_04.png`: native transparent frames.
- `spritesheet.png`: native 96×36 strip.
- `animation.json`: timing, phases, anchors, bob offsets and retained layer paths.
- `walk_front_preview.gif`: 20× looping preview on a light background.
- `frames_review.png`: all four frames at 12× scale.
- `shared_motion_comparison.gif`: 12× synchronized Caelan/female comparison.
- `recipe.json`: approved appearance references, shared template and authored skirt/boot poses.

Rebuild from the repository root:

```sh
python tools/build_dress_walk.py
```

Editable head/bodice appearances and six posed layers per frame are retained under `../../../../source/characters/npcs/female_01/walk_front/parts/`. The other two walking palettes and the remaining walking directions are future work after approval of this base cycle.
