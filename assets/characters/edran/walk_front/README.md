# Edran Hale — front walking cycle

**Status:** Four-frame front-walk animation approved by the user. The standing
character design is approved.

Four front-facing poses use the game's existing 140 ms cadence, for a 560 ms
loop. Frames are transparent 24×36 PNGs; spritesheet.png contains the four
frames in order. animation.json records source provenance, shared palette,
registration, timings and phases.

[Watch the animated preview](../../../../docs/reviews/companion_front_walks/edran_front_walk.gif).
[Compare all three walks](../../../../docs/reviews/companion_front_walks/README.md).

Both halves of the stride retain the character's anatomical equipment sides.
The same uniform scale is used throughout the cycle and colors are mapped to
the approved idle palette. New poses are authored in the retained generated
source artwork; export does not stretch limbs or mirror the character.

The source and extraction recipe live in
[assets/source/companions/edran/walk_front](../../../source/companions/edran/walk_front/source.json).

Rebuild with:

    python tools/build_companion_front_walks.py --actor edran
