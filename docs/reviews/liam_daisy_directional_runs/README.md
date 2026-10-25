# Liam and Daisy — remaining running directions

**Front, right and back runs are ready for review.** The left runs are approved
and included as references. These running assets have not yet been merged into
`main`.

## Enlarged looping previews

Each preview shows **front, left, right and back**, at the same 10× native pixel
scale. Every run uses exactly **four frames, 100 ms each, 400 ms per cycle**.

- [Liam — all four directions](liam_all_directions.gif) · [slow motion](liam_all_directions_slow.gif)
- [Daisy — all four directions](daisy_all_directions.gif) · [slow motion](daisy_all_directions_slow.gif)

Slow motion holds the same four native frames for 300 ms each. No intermediate
poses are generated. Synchronized character comparisons are also available:
[front](both_front.gif), [right](both_right.gif) and [back](both_back.gif).
Individual new runs have 16× normal/slow GIFs (`CHARACTER_DIRECTION.gif` and
`CHARACTER_DIRECTION_slow.gif`) and four-pose sheets (`CHARACTER_DIRECTION_frames.png`).

## Liam

The new runs retain the approved **contact → flight → opposite contact →
flight** cadence, bent elbows, short breeches, small boots and 24×36 frame.
His head, neck, collar and shoulders rise together by two pixels during flight.
Both airborne poses clear the ground; alternating support boots meet row 34.
Foot anchor remains `[12,34]`.

The right view reuses the approved left limb geometry, reflected for the new
facing, while its head, face, eyes, hair, collar and torso come from the approved
right idle. Front and back have authored foreshortened limb poses registered
to those idles. The back view has no eyes; both green eyes remain visible in
front. Moving arms replace the idle's stationary hands around the tunic hem.

## Daisy

All directions use the approved four-pose gallop: **forepaw landing → gathered
hind-leg loading → hind push-off → extended flight**. The new runs retain the
40×36 padded canvas, `[20,34]` anchor and original pixel scale. Four added
transparent columns on each side accommodate running limbs and tail motion.

The right view retains its own two smaller dark flank spots and white hip;
it does not mirror the left view's large dark flank patch. Only the joint
geometry is reflected. Its visible gray ear folds and drops around its fixed
head attachment, and its light-tipped fluffy tail swishes around the rump.

Front and back use foreshortened legs, one-pixel torso compression/extension,
two hinged ear tips and a sideways tail sweep with vertical follow-through.
The face and central head pixels are inherited without rescaling. Both eyes
remain in front, one in profile, and none behind. Native shaggy paw tips and
the coat palette stay consistent.

Depth planes matter in these views. In front, forepaws support at row 34 and
hind paws at row 32. In back, hind paws support at row 34 and forepaws at row 32.
A hind-only front support pose therefore ends above the foreground baseline;
that is the farther ground plane, not a flight pose. Every paw clears its own
contact plane in the final airborne pose. Profile near paws use row 34 and far
paws row 32, matching the approved left run.

## Source and checks

```sh
python tools/build_liam_daisy_directional_runs.py
python -m unittest discover -s tests -p 'test_liam*py' -v
```

Each character's `run_front/`, `run_right/` and `run_back/` folder contains four
native PNGs, a transparent strip, animation metadata and a pose recipe. New
joint templates live under `assets/templates/child_24x36/` and
`assets/templates/quadruped_40x36/`; complete per-frame source layers reconstruct
the final sprites. The builder preserves each pack's recorded approval status.

Eight directional checks verify protected approved inputs, exact palettes and
bounds, four-frame timing, support/flight, unchanged faces and collars, bent
elbows, asymmetric coat markings, attached ear/tail roots, source/strip
reconstruction and decoded normal/slow preview pixels. Combined with the
existing walk and left-run checks, **32 tests pass**. `animations.json` links
all six new packs and records hashes of approved idles, walks, left-run frames,
recipes, templates, source layers and original previews.

The previews use opaque light backgrounds, nearest-neighbor enlargement, exact
GIF colors, full-frame disposal and infinite looping. The thin horizontal guide
lies on row 35, below the native sprite pixels.

This change completes the running art for review. It does not add running
controls, movement speed, character placement or NPC behavior to the game.
