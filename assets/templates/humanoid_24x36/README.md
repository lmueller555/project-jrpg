# Shared humanoid pose components — 24×36

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

These retained components reproduce the older character-template implementation,
derived from Caelan's then-approved artwork. They are not the current authoring
workflow.

- `idle_front_legs.png`: transparent 24×36 component containing the exact approved front-idle lower legs and boots at rows 26–35.
- `idle_front.json`: canvas, foot anchor, component placement, assembly regions, and motion convention.

Mira reuses this component unchanged. Her appearance-specific head and shirt/arms/accessories are separate assembly layers at the same canvas size. The [front-walk template](walk_front/README.md) now provides four shared arm masks and leg poses from Caelan's approved cycle, used by the repeatable character-walk builder.

Matching [left](walk_left/README.md), [right](walk_right/README.md) and [back](walk_back/README.md) templates retain the other historical Caelan pose sequences used for Mira's
existing directional packs. The builder defaults to front; use `--direction all` to assemble every facing and the combined review board.

These legacy packs use four frames at 140 ms each. Their head, neck, shoulders
and upper chest rise together by one pixel on passing frames 2 and 4, while the
planted foot baseline remains fixed. These are facts about the retained packs,
not universal frame-count, cadence or body-part translation rules. New motion
uses complete drawings and body-landmark registration under the global standard.
