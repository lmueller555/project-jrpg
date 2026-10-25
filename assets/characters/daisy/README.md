# Daisy — approved directional dog idles

Daisy is Liam's family's female dog: predominantly gray, with white and black
patches, floppy gray ears and a fluffy light-tipped tail. Her age is unspecified.
The front, left, right and back idle designs are approved by the user.

- `idle_front.png`, `idle_left.png`, `idle_right.png`, `idle_back.png`: transparent
  **32×36** frames, hard alpha and one shared limited palette.
- Matching JSON files record bounds, eyes, source layers and frame anchors.
- `idle_directions.png`: native transparent 128×36 strip, ordered front, left,
  right, back; `idle_directions.json` records frame rectangles and marking notes.
- `palette.json`: gray fur, warm white patches, near-black spots and brown eyes.

The frame is wider than a human's 24×36 frame to hold Daisy's quadruped body
and plumed tail at the same native pixel density. Her visible height is **24
pixels** front/back and **23 pixels** in profile, compared with Liam's **26**.
Foot anchor is `[16,34]`; the paw baseline matches the humans' row 34.

The left flank has a larger black patch. The right has two smaller black spots
and a white hip patch. Side views are separately exported, preserving these
asymmetric markings; no mirrored duplicate is used. The back has no visible eyes.

Build with `python tools/build_daisy_idles.py`. See
[enlarged views and the Liam comparison](../../../docs/reviews/daisy/README.md).
World placement and pet routines remain future work.

## Front walk — approved

`walk_front/` now adds four 140 ms quadruped walking phases. One paw swings at
a time, with three supporting paws, small ear-tip follow-through and connected
fluffy-tail sway. Approved face, fur palette and spots are retained. The native
32×36 frame and two-pixel height difference from Liam remain intact. See the
[family front-walk review](../../../docs/reviews/liam_family_front_walks/README.md).

## Left, right and back walks — approved

`walk_left/`, `walk_right/` and `walk_back/` each contain four 140 ms walking
frames, a native strip, animation metadata and a reproducible pose recipe.
Approved directional appearances, palettes and front walks remain unchanged.
See the [enlarged synchronized previews](../../../docs/reviews/liam_family_directional_walks/README.md).
All four walking directions are approved; no world placement is added.
