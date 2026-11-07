# Grass demonstration field

`recipe.json` authors an isolated 32 × 22 tile field for reviewing the proposed
24-pixel grass pack at normal character scale. Existing Eldenmere and Sanctuary
maps are unchanged.

Maintained lawn fills the west, meadow spreads across the center and south, and
woodland grass occupies an irregular northeastern patch. Quiet base variants
dominate; fuller growth appears in larger authored coverage patches. The
material boundaries blend through hard native pixel clusters. The two small
northwestern comparison plots retain the existing grass and proposed richer
lawn side by side.

The 78 tall-grass clumps use irregular outer fringes, staggered roots and denser
interleaved growth toward their centers. Their root positions, variants and
wind phases are placement data. Tall grass is never baked into runtime ground
and has no blocking collision. The overview shows its idle appearance; the
playable world owns bending, held occupancy and recovery.

The existing tree and bench modules provide palette and character-scale
context. Only their physical footprints and the visible low boundary block
feet. All review checkpoints and grass roots accept the full 24 × 12 player
probe. `review_route` records ordinary walk/run visits and standing pauses;
`checkpoints` also provides direct points for focused tests and captures.

Build with `python tools/build_grass_demo_scene.py`; `--check` verifies all four
exports byte for byte. The map records source paths and hashes for the assets
actually read during composition. The grass asset builder must run first when
its pack changes.
