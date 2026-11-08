# Sanctuary limestone cave material library

Approval status: **pending review**. This pack is demonstrated in an isolated
review chamber; the playable Sanctuary cave and existing game maps retain their
current assets until the user approves a rollout.

The material follows Elden Vale's existing natural limestone: neutral warm gray,
pale calcite, restrained mauve mineral deposits and damp teal. Fine rock texture
samples the regional ridge at native resolution and remaps its colors into the
new stone ramps. The recipe and manifest record the exact source inputs.

## Contents

- Native 24 × 24 floors: 12 dry limestone, 8 damp stone, 8 gravel and 4 silt.
- Larger 48, 72 and 96 pixel irregular patches for all four materials.
- Straight, outside-corner and inside-corner transitions for damp, gravel and silt.
- Natural 96 × 72 wall faces, returns, concave/convex corners and overhangs.
- Worn stalagmites, broken columns, flowstone fans, hanging formations and boulders.
- Wet shoreline edges/corners and mineral sockets, plus a natural tunnel mouth.
- A separate wall-gem supplement with red, blue, green, white, orange and purple
  gems embedded in chipped stone recesses. The gems pulse without changing
  their physical silhouette or growing into floor clusters.

`assets.json` records `materials.*.tiles` and named `modules`. Each module has
native `size`, `frames`, a placement `anchor` and canvas-relative `footprints`.
Only the footprints should affect collision; tall visible stone can overlap
characters through the ordinary depth renderer. Ceiling pendants have no floor
footprint. Wall-gem sprites live in `wall_gems/`; they share the production
crystal-light pulse and emission system. Their six colors describe this visual
palette and do not assign elemental affinities.

`materials_review.png` is a native-scale inventory. `regional_comparison.png`
compares source, current cave stone and proposed limestone at the same exact 3×
nearest-neighbor enlargement, with unchanged Caelan art for scale. These boards
show unlit material colors; the review chamber demonstrates actual lighting.

Rebuild with `python tools/build_limestone_cave_assets.py`. Use `--check` to verify
all deterministic exports without writing. The authoritative source recipe is
`assets/source/terrain/limestone_cave/recipe.json`.
Build the embedded gem supplement with `python tools/build_wall_gems.py`, or
use `--check` for a read-only deterministic verification. Its source recipe is
`assets/source/terrain/limestone_cave/wall_gems.json`.
