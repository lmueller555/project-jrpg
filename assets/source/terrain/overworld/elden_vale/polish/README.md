# Elden Vale countryside art source

This kit adds 12 ground textures and 45 native props/animation frames to the
regional overworld. The original Elden Vale PNGs and the classroom atlas are
unchanged. Runtime assets and their bottom-center anchors are listed in
`assets/terrain/overworld/elden_vale/polish/art.json`.

The six generated sheets are preserved unaltered, with their hashes in
`recipe.json` and exact prompts in `prompts.json`:

- `nature_sheet.png`: tree silhouettes, understory, flowers, river plants and
  low rocky formations.
- `farm_sheet.png`: miniature buildings, orchard, hedges, fences, farmyard
  objects, festival supplies and a roadside shelter.
- `detail_sheet.png`: rubble, broken fencing, grass, and paired bird, butterfly,
  sheep and chimney-smoke frames.
- `wall_sheet.png`: intact mossy and weathered masonry variations.
- `texture_sheet.png`: retained first material study.
- `quiet_texture_sheet.png`: final material revision, using quieter grass,
  leaf litter, fine grain, sparse gravel and nondirectional packed earth.

The final materials were reviewed in actual gameplay views. Low-contrast
ground lets the 24×36 character and environmental silhouettes remain clear.
Wheel ruts belong to the road geometry rather than the repeating earth tile.

`recipe.json` records every source crop, native size and anchor. The exporter
only crops, thresholds alpha, uniformly scales with nearest-neighbour sampling,
reduces palettes and adds transparent padding. It does not paint illustrations.
Alpha is thresholded before bounding/cropping so almost-transparent RGB fringes
cannot become visible outlines. All runtime alpha is binary, all ground is
opaque 24×24, and no source generation is overwritten.

```sh
python tools/build_overworld_polish_art.py
python tools/build_overworld_polish_art.py --check
```

`native_review.png` is a labeled review diagram assembled from the exported
sprites. Its labels and enlarged samples are outside the runtime art.
