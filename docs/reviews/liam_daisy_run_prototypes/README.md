# Liam and Daisy — four-frame running prototypes

**Both left-facing running animations are approved by the user.**
The previews retain their original prototype labels. All four running
directions are now approved and merged into `main`.
Each uses exactly **four frames**, matching the walk packs' frame count.
The run cadence is **100 ms per frame / 400 ms per cycle**, compared with the
approved walk's 140 ms per frame / 560 ms cycle.

- [Both running, same native scale](both_running.gif)
- [Both running, slow motion](both_running_slow.gif)
- [Independent walk/run comparison](walk_run_comparison.gif)
- [Liam — normal](liam_run.gif) · [slow](liam_run_slow.gif) · [four poses](liam_frames.png)
- [Daisy — normal](daisy_run.gif) · [slow](daisy_run_slow.gif) · [four poses](daisy_frames.png)

Slow motion holds the same four source poses for 300 ms each. No interpolated
or additional animation frames are added. The walk/run comparison preserves
each animation's actual cadence; their clocks realign after 2.8 seconds.

## Liam

The cycle is **near-leg contact → flight → far-leg contact → flight**.
Supporting boots touch the existing row-34 baseline. Both flight frames clear
the ground by three pixels. His head, neck, collar and shoulders move together
by two vertical pixels; a one-pixel forward lean keeps his face unchanged.
Bent elbows swing opposite the legs on contact poses. The recovered heel folds
up toward his seat, and its boot points down rather than remaining horizontal.

Liam retains a 24×36 frame, `[12,34]` foot anchor, approved head/face/collar and
central tunic pixels, with the idle's stationary hand removed from the hem.
New run joint poses supply bent limbs in his approved palette. Short breeches,
small boots and child proportions remain intact. His resting height is still
26 pixels; tucked airborne limbs change the occupied bounds naturally.

## Daisy

The four summary poses are **forepaw landing → gathered hind-leg loading →
hind push-off → extended flight**. Front and rear legs cooperate in a gallop;
the walk's three-support/one-swing rule does not apply. Near paws use row 34
and far paws row 32 when supporting. All paws clear the ground in the last pose.
Four frames imply the staggered footfalls rather than showing every contact
as a separate drawing.

Her head and face use unchanged native pixels, translated with her body. The
large left-flank patch remains on this side. Her torso compresses/extends by
one or two native columns. New bent leg silhouettes use existing fur shades,
with native shaggy paw tips. Her visible ear is hinged at the head: its tip
hangs lower after landing and folds up during flight, with two pixels of
follow-through in each direction. The white neck ruff stays out of the moving
gray ear mask. Her fluffy tail swishes around a fixed overlapping root; its
tip changes position without the tail detaching.

Daisy's run canvas is **40×36**, padded four pixels either side of the existing
32×36 frame. Her native pixel scale is unchanged. The foot anchor becomes
`[20,34]`, keeping the same world baseline. The wider canvas accommodates the
extended paws and swishing tail without clipping. Individual previews use the
same 16× scale for both characters; the shared running previews use 14×.

## Source and verification

```sh
python tools/build_liam_daisy_run_prototypes.py
python -m unittest discover -s tests -p test_liam_daisy_run_prototypes.py -v
```

Each character's `run_left/` directory contains four native PNGs, a transparent
strip, animation metadata and a recipe. New pose templates are in
`assets/templates/child_24x36/run_left/` and
`assets/templates/quadruped_40x36/run_left/`. Full per-frame layers are retained
under the corresponding character source folders.

Nine checks cover protected idle/walk inputs, four unique frames and native
palettes/alpha/bounds, real ground contact and flight, Liam's unchanged
face/neck/collar and bent limbs, Daisy's face/markings and attached ear/tail
roots, source-layer and sheet reconstruction, exact decoded GIF colors/timing,
and independent comparison clocks. Preview GIFs have opaque light backgrounds,
nearest-neighbor enlargement and infinite looping. Recipes preserve approval
status on later rebuilds.

This is an asset prototype. Running controls, movement speed, world placement,
and the remaining run directions are not added by this change.
