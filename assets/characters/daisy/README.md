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
Daisy is placed in the family cottage; see her house routines below.

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
All four walking directions are approved and used by her indoor wandering.

## Left-facing run — approved

`run_left/` adds a four-frame run prototype at 100 ms per frame. See the
[normal-speed, slow-motion and walk/run comparisons](../../../docs/reviews/liam_daisy_run_prototypes/README.md).
The left run is approved; approved idles and walks are unchanged.

## Front, right and back runs — approved

`run_front/`, `run_right/` and `run_back/` each contain four running poses at
100 ms per frame. They continue the approved left run and use each approved
directional idle's appearance. See the [all-direction normal/slow loops](../../../docs/reviews/liam_daisy_directional_runs/README.md).
All four running directions are approved and merged into `main`; the left run is unchanged.

## Lying pose and rug — approved

`lying_left/pose.png` is a single 40×36 still pose, composed from the approved
left-facing head, coat, floppy ear, paw pixels and fluffy tail. Her legs fold
under her lowered chest and the plume rests alongside her body. She is placed
on the woven rug in Liam's house between her wandering and bowl visits.
See the [in-game household and rug close-up](../../../docs/reviews/liam_household/README.md).

## House routines — approved

`house_routines/` adds four-pose stand/settle, head-lowering/raising, eating and
drinking actions. Approved idles, walks, runs and lying art are unchanged.
Daisy walks indoors at 36 px/s, rests on her rug, and consumes one fill level
per bowl visit. See the [routine pack](house_routines/README.md) and
[in-game previews](../../../docs/reviews/daisy_house_routines/README.md).

## Playtime with Liam — approved

A shared controller temporarily pauses Daisy's normal routine for Liam's
invitation, two excited hops and a tail wag, three running laps in front of
their cottage, and a return-home nap. She chooses once, with equal probability,
between drinking first and going directly to her rug. All travel reuses her
approved walks and runs. See the
[shared action pack](../liam_family/play_routine/README.md) and
[runtime review](../../../docs/reviews/liam_daisy_play/README.md).

## Curious visit to Liam's blocks — approved

A nearby Daisy has one 10% chance per eligible building session of approaching
Liam's finished creation. A four-pose sniff makes nose contact before the blocks
fall. Liam tells her to lie down; she walks to her rug and uses her existing
settling pose, then rests 45–90 seconds. The block controller waits for any bowl
visit to finish, and restores her normal routine afterward. See
[the accident preview](../../../docs/reviews/liam_blocks/daisy_accident.gif).
