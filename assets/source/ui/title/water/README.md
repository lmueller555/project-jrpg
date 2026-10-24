# Title-water animation source

`recipe.json` defines the water regions and stationary rock exclusions in the
approved 640×360 title illustration's coordinates. Flow vectors point in the
illustration's downhill direction. Color selection narrows these outlines to
water/reflection/foam pixels while leaving banks and objects intact.

`tools/build_title_water.py` uses the original title illustration to export
registered masks and 24 hard-alpha overlay frames. Modulation and constrained
texture advection run over the complete selected surfaces. Three fall cycles
fit inside one 2.4-second main-surface loop; the distant water is restrained.

The background image is unchanged. Every frame's alpha reproduces the same
mask. A source hash in the manifest detects a mismatched background. Regenerate
the animation if the title illustration changes, then inspect the diagnostic
mask overlay written to `/tmp/title-water-mask-review.png`.
