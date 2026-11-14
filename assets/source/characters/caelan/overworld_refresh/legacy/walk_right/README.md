# Caelan — right-facing walk cycle

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Historical approval: approved by the user for the archived artwork, including the coordinated head-and-shoulder bob. The approved directional idles and front walk are unchanged.

- `frame_01.png`–`frame_04.png`: four distinct transparent 24×36 frames.
- `spritesheet.png`: transparent 96×36 strip in playback order.
- `animation.json`: rectangles, 140 ms frame timing, phase names, and `[12, 34]` foot anchor.
- `walk_right_preview.gif`: looping 480×720 preview enlarged 20× on a light background.
- `frames_review.png`: static 12× enlargement of the four frames.

Playback is contact A → passing A → contact B → passing B, then repeat (560 ms per cycle). On passing frames 2 and 4, the head, neck, shoulders, and upper chest rise together by exactly one native pixel. A lower-chest row bridges to the stationary waist. Offsets in metadata describe motion already baked into the PNGs; do not apply them a second time.

The approved right idle supplies the exact head and neck pixels. Every native frame uses the approved front palette and binary transparency. Source poses are reduced with nearest-neighbor sampling, palette mapped, and registered to a common 24×36 frame. The opposite side-view phases use the corrected two-frame concept to distinguish the near and far legs.

Sources are retained in [the retained source directory](../../../walk_right/). This cycle and its bob are retained historical evidence, not the current
animation-authoring reference. The no-runtime description belonged to the
original study milestone; see
[Caelan's current artwork guide](../../../../../../characters/caelan/README.md)
for current exports and runtime rendering.
