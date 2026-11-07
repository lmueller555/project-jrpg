# Grass demonstration source

This is a review prototype, separate from the approved Eldenmere and Sanctuary
maps. `recipe.json` defines a modestly richer green palette, twelve native
24-pixel ground designs and four rooted tall-grass silhouettes.

Maintained grass uses small low-growing clusters. Meadow variants use different
cluster sizes, blade heights and coverage. Woodland variants add broken shade,
leaf litter and short exposed-root marks. All ground tile borders use the same
base green, so mixing tiles does not introduce hard seams. These are deliberate
motif arrangements rather than a uniform per-pixel noise texture.

The existing grass, dense clump and Caelan sprite are retained references with
their hashes. New ground motifs and individual blade root/tip/depth graphs are
authored in the recipe and builder at native resolution. Original packs remain
unchanged. The review board uses the original grass and Caelan pixels for direct
color and character-scale comparison.

Tall grass uses a shared 24 × 32 transparent canvas with root anchor `(12,28)`.
The contact rectangle is relative to that anchor. Each silhouette has six
800-millisecond breeze poses and three strengths for each cardinal parting
direction. Every pose includes full-canvas `rear` and `front` layers; their root
rows 26–31 remain identical. The runtime owns contact timing, displacement,
holding and recovery. The pack supplies no collision or movement penalty.

Build with `python tools/build_grass_demo_assets.py`; add `--check` to verify
source references and deterministic exports without writing. The runtime
manifest is `assets/terrain/grass_demo/assets.json`; the review board is
`assets/terrain/grass_demo/materials_review.png`.
