# Liam's wooden-block action sprites — awaiting review

Each action contains four distinct transparent poses. Liam uses a 96×96 canvas,
anchor [64,66], and approved native offset [52,36]. `kneel_left/right` and
`rise_left/right` use 180 ms per pose; `take_left`, `return_left`, `place_right`
and `collect_right` use 300 ms; `react` uses 700 ms.

Kneeling folds the legs beneath the tunic, lowers the head three pixels, and
keeps knees/boots on the ground. Short arm gestures reach at most ten pixels
sideways from the foot anchor. Each Liam frame records `hand_local`; third
poses (zero-based `contact_frame` 2) are the physical block handoffs. Contact
hands are [54,57] left and [74,57] right, meaning feet-relative [-10,-9] or
[10,-9]. Held blocks are separate runtime props, centered at these landmarks.

`curious_nudge_left` belongs to Daisy and uses a 64×48 canvas and [32,42]
anchor. Four 250 ms poses keep her body, paws and tail fixed while her nose
lowers two pixels with slight ear follow-through. Its `nose_local` positions
are [17,30], [17,31], [17,32], [17,31]. Contact is the third pose; a foot position
of [130,204] puts her actual black nose at [115,194].

`animations.json` records per-action character/canvas/timing, contacts and
retained source-layer paths, plus SHA-256 hashes protecting all pre-existing
Liam and Daisy PNGs. Build with `python tools/build_liam_blocks.py`.
