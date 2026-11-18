# Caelan — archived directional idle sprites

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Caelan is **18 years old** at the beginning of Game I and is Tomas's older
biological brother; see [approved character facts](../../../../../../docs/narrative/game_01/CHARACTERS.md).

The archived directional idle designs and the four-frame walking cycles for [front](walk_front/README.md), [left](walk_left/README.md), [right](walk_right/README.md), and [back](walk_back/README.md), including their coordinated head-and-shoulder bob, were explicitly approved for that earlier artwork. Those approvals do not
approve or describe Caelan's current authored overworld refresh.

## Files

- `idle_front.png`: approved transparent 24×36 front idle.
- `idle_left.png`, `idle_right.png`, `idle_back.png`: approved transparent 24×36 directional idles. Left/right describe the direction the character faces on screen.
- `idle_directions.png`: transparent 96×36 sheet, ordered front, left, right, back.
- `idle_directions.json`: frame rectangles, foot anchors, and approval status; a standalone asset description, not an engine integration.
- `idle_directions_review.png`: labeled 12× enlargement on a light background for review, not a runtime texture.
- `idle_front_preview.png` and `idle_front_review.png`: earlier enlarged front views.
- `walk_directions.png`: approved native 96×144 walking sheet, with front, left, right, and back rows; each row contains four 24×36 frames.
- `walk_directions.json`: row/frame rectangles, approval status, and links to each direction's animation metadata.
- `walk_directions_review.gif`: labeled 12× comparison loop, ordered front, left, right, back; `walk_directions_review.png` is its first frame for static inspection.

Every frame uses hard transparency, colors from the approved front palette, and a shared foot anchor at `[12, 34]` in frame coordinates. Frame bounds are 24×36; the visible character occupies a smaller area within that transparent frame. The reference terrain scale discussed in chat is 24×24 pixels.

## Appearance

Chestnut hair, ivory tunic and sleeves, teal outer tabard, ochre trim, brown belt/pouch and boots, and dark trousers. The retained design places the hip pouch on anatomical left. Current
appearance and animation references are linked in
[Caelan's current artwork guide](../../../../../characters/caelan/README.md).

Generated source concepts are retained in [the retained source directory](../../). They are high-resolution references; the native game-sized sprites are the 24×36 files here. Native exports use nearest-neighbor sampling, hard alpha, and palette mapping. Review images use whole-number enlargement without smoothing.

This artwork approval does not alter the preserved story documents or their character-name spelling. The no-runtime description belonged to the original study milestone. The
game now uses the authored overworld refresh; these archived sprites remain
historical evidence.
