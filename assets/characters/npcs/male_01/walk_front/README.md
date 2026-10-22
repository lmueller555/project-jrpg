# Male NPC 01 — front walk

Status: approved by the user in chat. All four idle designs and their palettes remain approved.

Four 24×36 frames use Caelan's approved front-walk poses, at 140 ms per frame with a looping 560 ms cycle and the shared `[12, 34]` foot anchor. The approved brown-haired head and face are retained exactly. On passing frames 2 and 4, the head, neck, shoulders and upper shirt rise together by one pixel; the belt stays at the same height. Arm motion comes from the shared semantic pose masks.

The shirt is moss green, the trousers tan and the boots brown. An explicit leg-color mapping changes the shared pose's costume colors while retaining the exact foot and leg silhouettes. The original belt, buckle and upper-trouser pixels are retained as a separate waist layer. There is no pouch.

- `frame_01.png`–`frame_04.png`: native transparent frames.
- `spritesheet.png`: native 96×36 playback strip.
- `animation.json`: rectangles, timing, phases, anchor and baked bob offsets.
- `walk_front_preview.gif`: enlarged 20× looping preview on a light background.
- `shared_motion_comparison.gif`: synchronized 12× loop, with Caelan on the left and this NPC on the right.
- `frames_review.png`: static 12× strip of all four frames.
- `recipe.json`: appearance regions, shared template, material palette and leg-color mapping.

Rebuild from the repository root with the asset dependencies installed:

```sh
python tools/build_character_walk.py npcs/male_01
```

Prepared appearance layers, posed arms and recolored leg layers are retained under `../../../../source/characters/npcs/male_01/walk_front/parts/`. Motion offsets are already baked into the images. The other male palettes and walking directions are the next planned assets.
