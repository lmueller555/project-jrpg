# Limestone cave material review

**Status: proposed artwork, awaiting user review. This chamber is isolated from
the live cave and is not merged into main.**

The review develops the Sanctuary's existing natural stone into a cave pack:
neutral grey and taupe limestone, pale calcite edges, damp teal staining and
irregular mineral strata. Red, blue, green, white, orange and purple gems sit
inside chipped recesses in the cave walls. Their facets pulse with the colored
light cast across the surrounding stone and floor. The gems are embedded
minerals rather than standing crystal clusters on the ground.

The pack contains dry limestone, damp stone, gravel and silt, larger material
patches, natural wall faces and returns, erosion pockets, overhangs, wet shores,
gem recesses and varied formations. Its 24-pixel grid and character scale
match the Sanctuary and Eldenmere. Keeper paving is a restrained trace of care
within the natural chamber.

The curved review chamber brings these materials together around a reflecting
pool. Caelan can walk and run between the dry floor, wet shoreline, gravel,
tunnel, keeper ledge and foreground formations. The normal game feet, movement,
animation, depth sorting and crystal-light renderer are used directly.

## Play the chamber

```sh
python tools/preview_limestone_cave.py
```

| Control | Action |
| --- | --- |
| WASD / arrow keys | Walk |
| Shift | Run |
| Space | Cycle live pulse, held low and held high |
| L | Toggle crystal lighting and unlit material colors |
| R | Toggle reduced motion |
| H | Show or hide the controls |
| Home | Return to the chamber's starting position |
| Escape | Close the viewer |

The viewer never opens a journey, quest, inventory or settings controller and
never writes a player save. The current Sanctuary, cave layout, cave assets and
story remain unchanged while this material direction is reviewed.

## Assets and reproduction

The authoritative pack recipe is
`assets/source/terrain/limestone_cave/recipe.json`; the chamber recipe is
`assets/source/maps/limestone_cave_review/recipe.json`.
The embedded gem supplement has its own authoritative recipe at
`assets/source/terrain/limestone_cave/wall_gems.json`.
The exported pack manifest records native module sizes, anchors, footprints
and source provenance. Both builders support deterministic read-only checks.

```sh
python tools/build_limestone_cave_assets.py
python tools/build_wall_gems.py
python tools/build_limestone_cave_chamber.py
python tools/build_limestone_cave_assets.py --check
python tools/build_wall_gems.py --check
python tools/build_limestone_cave_chamber.py --check
python tools/capture_limestone_cave.py
python tools/capture_limestone_cave.py --check
```

Pygame and NumPy are runtime dependencies. Rebuilding and capturing require
Pillow; recording the walkthrough also requires ffmpeg.

See the [production-renderer review](reviews/limestone_cave/README.md) for the
chamber, material comparison, pulse and walkthrough. The
[unlit material board](../assets/terrain/limestone_cave/materials_review.png)
compares the proposed modules with the regional stone sources and Caelan.
The [regional comparison](../assets/terrain/limestone_cave/regional_comparison.png)
places the new limestone alongside the approved Sanctuary and Eldenmere stone.
The [embedded gem board](../assets/terrain/limestone_cave/wall_gems/colors_review.png)
shows the six requested colors and their native sprite variants.
