# Caelan — back-facing walk cycle

Status: approved by the user, including the coordinated head-and-shoulder bob. The approved directional idles and front walk are unchanged.

- `frame_01.png`–`frame_04.png`: four distinct transparent 24×36 frames.
- `spritesheet.png`: transparent 96×36 strip in playback order.
- `animation.json`: rectangles, 140 ms frame timing, phase names, and `[12, 34]` foot anchor.
- `walk_back_preview.gif`: looping 480×720 preview enlarged 20× on a light background.
- `frames_review.png`: static 12× enlargement of the four frames.

Playback is contact A → passing A → contact B → passing B, then repeat (560 ms per cycle). On passing frames 2 and 4, the head, neck, shoulders, and upper chest rise together by exactly one native pixel. A lower-chest row bridges to the stationary waist. Offsets in metadata describe motion already baked into the PNGs; do not apply them a second time.

The approved back idle supplies the exact head and neck pixels. Every native frame uses the approved front palette and binary transparency. Source poses are reduced with nearest-neighbor sampling, palette mapped, and registered to a common 24×36 frame.

Sources are retained in `../../../source/characters/caelan/walk_back/`. Use this approved cycle and its coordinated upper-body bob as references for later animation work. There is currently no game runtime.
