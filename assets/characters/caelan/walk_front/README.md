# Caelan — front-facing walk cycle

Status: walking design approved; revised upper-body bob awaiting user review. The four approved directional idle designs remain unchanged.

## Deliverables

- `frame_01.png`–`frame_04.png`: four transparent native 24×36 frames.
- `spritesheet.png`: transparent 96×36 strip in playback order.
- `animation.json`: rectangles, timing, phase descriptions, and shared foot anchor.
- `walk_front_preview.gif`: looping 480×720 preview, enlarged 20× with nearest-neighbor scaling on a solid light background.
- `frames_review.png`: static 1152×432 review strip, enlarged 12×.

Playback is 1 → 2 → 3 → 4 → repeat, at 140 ms per frame (560 ms per cycle). Frame 1 has the screen-left boot forward; frame 2 is the screen-left support passing pose; frame 3 has the screen-right boot forward; frame 4 is the opposite passing pose. There are four distinct frames, not a mirrored two-frame loop.

Every native frame uses the approved front idle palette, binary transparency, and the same `[12, 34]` foot anchor. Generated body and leg poses are reduced with nearest-neighbor sampling and mapped to that palette.

The head, neck, shoulders, and upper chest stay at their original height on contact frames 1 and 3, and move upward together exactly one native pixel on passing frames 2 and 4. The original pixels are translated without redrawing, preserving the head-to-shoulder spacing instead of extending the neck. A lower-chest row connects the raised upper body to the stationary waist. The belt, hips, legs, feet, and timing are unchanged from the first walking preview. No topmost head pixels are clipped.

Source concepts are retained in `../../../source/characters/caelan/walk_front/`. The initial concept repeated the passing pose; `passing_opposite_concept.png` supplies the corrected fourth pose.

The user approved the walking design subject to adding this bob. Review the updated motion before merging or creating other directions. No runtime integration or other walking directions are included.
