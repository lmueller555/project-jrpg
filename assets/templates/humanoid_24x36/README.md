# Shared humanoid pose components — 24×36

This is the start of the reusable character-template workflow, derived from Caelan's approved artwork.

- `idle_front_legs.png`: transparent 24×36 component containing the exact approved front-idle lower legs and boots at rows 26–35.
- `idle_front.json`: canvas, foot anchor, component placement, assembly regions, and motion convention.

Mira reuses this component unchanged. Her appearance-specific head and shirt/arms/accessories are separate assembly layers at the same canvas size. The [front-walk template](walk_front/README.md) now provides four shared arm masks and leg poses from Caelan's approved cycle, used by the repeatable character-walk builder.

Matching [left](walk_left/README.md), [right](walk_right/README.md) and [back](walk_back/README.md) templates now provide the other approved Caelan pose sequences for Mira's new directional drafts. The builder defaults to front; use `--direction all` to assemble every facing and the combined review board.

The existing walking convention is four frames at 140 ms each, with a one-pixel coordinated rise of head, neck, shoulders, and upper chest on passing frames 2 and 4. Translate those parts together to preserve neck height; keep the planted foot baseline fixed.
