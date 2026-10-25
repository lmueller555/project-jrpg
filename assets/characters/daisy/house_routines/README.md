# Daisy's indoor action poses — awaiting review

Eight actions each contain four unique, transparent 64×48 pixel frames:
stand_up, settle_down, lower_food, raise_food, eat, lower_water, raise_water,
and drink. Stand/settle take 720 ms; lower/raise take 640 ms. Eating loops at
180 ms per pose and drinking at 100 ms per pose. All movement uses the approved
four-direction walks at 140 ms per frame; there is no indoor running.

The draw anchor is [32,42]. Approved 32×36 sprites are padded at [16,12], and
the 40×36 lying pose at [12,12]. Feet align at row 46. Direction-specific head
layers rotate around the neck; hips, paws and tail roots remain anchored.
A single muted pink tongue pixel appears on the drinking lap pose. Each frame
records its mouth landmark and whether it contacts the bowl contents.

`animations.json` records timing, palette, layers and SHA-256 checksums of all
existing approved Daisy PNGs. Retained source layers reconstruct every export.
Build with `python tools/build_daisy_routines.py` or the family-home builder.
See [runtime previews](../../../../docs/reviews/daisy_house_routines/README.md).
