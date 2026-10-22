# Caelan — left-facing walk cycle

Status: draft, awaiting user review. The approved directional idles and front walk are unchanged.

- `frame_01.png`–`frame_04.png`: four distinct transparent 24×36 frames.
- `spritesheet.png`: transparent 96×36 strip in playback order.
- `animation.json`: rectangles, 140 ms frame timing, phase names, and `[12, 34]` foot anchor.
- `walk_left_preview.gif`: looping 480×720 preview enlarged 20× on a light background.
- `frames_review.png`: static 12× enlargement of the four frames.

Playback is contact A → passing A → contact B → passing B, then repeat (560 ms per cycle). On passing frames 2 and 4, the head, neck, shoulders, and upper chest rise together by exactly one native pixel. A lower-chest row bridges to the stationary waist. Offsets in metadata describe motion already baked into the PNGs; do not apply them a second time.

The approved left idle supplies the exact head and neck pixels. Every native frame uses the approved front palette and binary transparency. Source poses are reduced with nearest-neighbor sampling, palette mapped, and registered to a common 24×36 frame. The opposite side-view phases use the corrected two-frame concept to distinguish the near and far legs.

Sources are retained in `../../../source/characters/caelan/walk_left/`. Review stride, arm movement, clothing continuity, and the transition from the approved idle before approving the cycle. There is currently no game runtime.
