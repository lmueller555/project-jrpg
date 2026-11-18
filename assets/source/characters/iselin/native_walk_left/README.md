# Native Iselin left-walk source

Status: left walk approved by the user. This milestone stages the left direction without
changing the live campaign bank or the approved native idles/front walk.

`keys.png` contains four complete left-facing contact/passing drawings created
with `image_gen.imagegen`. `authored.png` contains the sixteen complete drawings
in chronological row-major order. The approved native left idle owns appearance;
the established cast and previous approved left walk supplied motion references.
The current drawing is left-specific, retaining the near anatomical-left braid
and far anatomical-right mantle rather than mirroring a finished costume.

The near left leg advances with the far right arm; the near left arm counters
the near leg. At opposite contacts, the bright near sleeve moves from behind
the torso to across its front while the muted far arm exchanges roles behind
it. Similar hand positions at those contacts do not mean the same anatomical
hand stayed there. Both leg chains progress through contact, support, recovery
and passing, with ordinary partial occlusion by the coat and other limb.

`tools/export_iselin_native_left_walk.py` applies hard alpha220 and extracts the
connected complete figure. The one 1086×1448 source has a 4×4 grid; rounded
column boundaries produce 271/272-pixel cells. Transparent right-edge padding
registers every cell at 272×362 before a common 27×36 nearest-neighbor sample.
The fixed source crown is at 27–28 and waist near 202–207. A single nominal
0.1 source density and fixed `[-2,-1]` origin serve every pose. Neither boot
extents nor individual silhouette heights determine scale or alignment.

Following the approved front walk's documented regional-preservation workflow,
the exporter restores the approved left idle's rows 0–11 at destination y1.
That fixed head/face is one pixel lower than idle during walking, giving a
small weight settle with contact feet on the declared ground line. No extra
runtime bob is applied. The neck, braid tail, torso, arms, coat and legs below
y13 remain from the complete authored frames. No moving limb is assembled,
rotated, translated or stretched. Original sources remain unchanged.

Frames are 24×36 RGBA at one artwork pixel per world pixel; draw anchor `[12,30]`,
foot anchor `[12,34]`, collision probe 8×4. Sixteen explicit 35 ms frames retain
the full 560 ms two-step cadence. The ordinary sheet-based review actor contains
the approved idles and this left loop, with no HD override or runtime change.
Source/export hashes and complete registration records are in `registration.json`.

See `docs/reviews/iselin_native_left_walk/README.md` for renderer/movement evidence
and reproduction. General authoring rules remain centralized in
`docs/SPRITE_ANIMATION_STANDARD.md`.
