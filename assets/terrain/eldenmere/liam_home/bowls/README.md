# Daisy's wooden food and water bowls

Two matching shallow wooden bowls are placed side by side to the right of
Daisy's rug in Liam's family cottage. Both start **full**. Each bowl has three
interchangeable still sprites: **full, half-full and empty**.

`bowls.json` maps `food` and `water` to `full`, `half_full` and `empty` image paths,
with fill fractions 1, 0.5 and 0. All six exports are transparent **24×24** frames.
Their wooden body, rim, shadow, frame registration, content target `[12,12]` and
12×4 foot blocker remain fixed. Only pixels in `content_mask.png` change;
`half_content_mask.png` keeps the smaller fill lower in the recessed well.
The empty sprites intentionally match, since both containers have the same wood.

Food uses warm brown morsels and pale crumbs. Water uses the approved kitchen
water palette with a small static reflection. Wood uses the approved cottage
furniture palette. Native source layers reconstruct every variant. The strip
is 72×48: food then water rows, full/half-full/empty columns.

Placement and the selected state are recorded in
`assets/maps/eldenmere/liam_house/house.json`. Runtime entities contain one full
sprite in `frames`, all three alternatives in `state_images`, a `bowl_kind`,
`bowl_pack`, fixed collision rectangle and world-space `content_target`.
Caregiver approaches are registered in the room's `destinations`.
The state map is ready for later feeding/drinking/refill code; sprites do not
cycle, drain, refill or trigger interactions on their own. Family NPCs remain
stationary, without dialogue or action routines.

```sh
python tools/build_daisy_bowls.py
python tools/build_liam_family_home.py
python tools/capture_daisy_bowls.py
python -m unittest discover -s tests -p test_daisy_bowls.py -v
```

The household builder also regenerates the bowl pack. Its source recipe is
`assets/source/terrain/eldenmere/liam_home/bowls_recipe.json`.
See the [in-game placement and six variants](../../../../../docs/reviews/daisy_bowls/README.md).
