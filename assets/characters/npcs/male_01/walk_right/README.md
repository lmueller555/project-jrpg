# Male NPC 01 — right-facing walk

Status: draft awaiting user review. The front walk and all directional idle designs remain approved.

Four 24×36 frames use Caelan's approved right-facing poses and the NPC's approved `../idle_right.png` appearance. Head and face pixels remain intact. The head, neck, shoulders and upper shirt rise together by one pixel on passing frames 2 and 4. All frames use 140 ms timing and the shared `[12, 34]` foot anchor.

The shirt is moss green, trousers tan and boots brown. Arm material masks retain the shared poses; an explicit leg-color mapping preserves every source leg and foot silhouette while applying the NPC costume. There is no pouch. A plain dark-brown profile belt and tan upper trousers complete the torso. The profile retains its single visible eye and the approved hairstyle rather than mirroring another facing.

- `frame_01.png`–`frame_04.png`: transparent native frames.
- `spritesheet.png`: native 96×36 playback strip.
- `animation.json`: timing, phases, frame rectangles, anchor and baked offsets.
- `walk_right_preview.gif`: 20× enlarged looping preview.
- `frames_review.png`: 12× static strip of all four poses.
- `shared_motion_comparison.gif`: synchronized 12× loop with Caelan on the left.
- `recipe.json`: source appearance, material colors, part regions and shared template.

Rebuild from the repository root with the asset dependencies installed:

```sh
python tools/build_character_walk.py npcs/male_01 --direction right
```

Prepared parts are retained under `../../../../source/characters/npcs/male_01/walk_right/parts/`. Compare all four directions in `../walk_directions_review.gif`. The other two palettes will be applied after approval of these base directional cycles.
