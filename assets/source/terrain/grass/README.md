# Approved emerald terrain source

`recipe.json` is the production source for the shared grass pack used by the
outdoor maps. Its emerald base is `#2c7c50`. Twelve native 24 × 24 materials span
maintained lawn, meadow and woodland; quiet variants are intended to be more
common than the larger accent motifs. All tile borders share the base color.

The material motifs and four grass silhouettes preserve the exact pixels from
the approved grass study. The builder reuses that study's native art functions
instead of resampling its exports. The source recipe records the reviewed
recipe's fingerprint, the original asset references and every derivative input.
The isolated comparison remains available as a record of the approved direction.

Tall grass has a 24 × 32 transparent canvas, root anchor `(12,28)`, six breeze
poses and three parting strengths in each cardinal direction. Combined opaque
height is at most 17 pixels, against Caelan's 34-pixel visible sprite. Upright
grass is 16–17 pixels; foreground tips reach at most five pixels above roots so
the grass overlaps legs while preserving the coat, torso and head. Root rows
remain fixed, with hard alpha in every pose. Runtime contact, occupancy, running
displacement and recovery are owned by the shared World layer.

The pack also supplies 47 dirt transition shapes, three dirt interior tiles and
white, yellow and violet wildflowers. These derive from the existing Eldenmere
pack. Only exact legacy green colors are replaced; transition geometry, earth
colors, flower petals, transparency, fixed bases and animation timings remain
intact. Original images remain archived inputs, so their prior review is still
reproducible. The flower `plant.json` records retain relative image paths; the
shared `assets.json` uses paths relative to the repository root.

Build with `python tools/build_grass_assets.py`; use `--check` to verify source
hashes and deterministic exports without writing. The production manifest is
`assets/terrain/grass/assets.json`, and `materials_review.png` provides a native
art comparison enlarged with nearest-neighbor scaling.
