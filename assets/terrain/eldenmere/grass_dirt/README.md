# Eldenmere — grass and dirt terrain

Status: approved by the user in chat. Native tiles are 24×24; characters in the review remain 24×36.

The first terrain pack establishes an approved quiet, fresh-green upland-village palette with cooler grass shadows and warm compacted stony earth. It follows the approved opening's watermill, bridge, irrigation and eastern terrace context, and the discussed regional mountain direction. Precise geography, season and town layout remain separate story decisions. This is a grass/dirt foundation; water, terrace stone, buildings and other props are future work.

## Contents and review

- `grass_00.png`–`grass_03.png`: four opaque grass variations; `grass.png` is their 96×24 strip.
- `dirt_blob_47.png`: 192×144 transparent overlay atlas, eight columns by six rows. The last slot is unused and transparent.
- `dirt/mask_<number>.png`: all 47 unique 24×24 overlay states, ordered by canonical mask value in the atlas.
- `dirt_fill_00.png`–`dirt_fill_02.png`: three opaque dirt interiors, including the atlas's base full-fill tile. The other two are optional variants for fully surrounded dirt cells, mask 255. `dirt_fill.png` is their 72×24 strip.
- `tileset.json`: status, tile rectangles, mask definitions, lookup for all 256 raw neighborhoods, source quarter references and composition order.
- `palette.json`: named grass and dirt colors; transparent pixels use hard alpha, with no antialiasing.
- `materials_review.png`: enlarged grass and dirt samples.
- `blob_47_review.png`: every overlay over grass at 6× scale, labeled with atlas index and mask.
- `review_scene.png`: a 3× enlarged scale/terrain review with Caelan, Mira and all six NPCs.
- `review_scene_native.png`: that same scene at its native 480×384 resolution.
- `review_scene_ground_native.png`: native ground without characters.
- `review_scene.json`: grass choices, dirt masks, fill variants and native character placements for exact reconstruction.

The scene demonstrates narrow and wider paths, bends, a junction, a clearing with an inner grass island, isolated patches, and all character palettes on grass/dirt. It is an art test, not the canonical Eldenmere map or a playable game. Characters are composited from approved sprites without altering their pixels.

## Blob convention

Grass is the opaque base layer. Dirt is painted over it with transparency outside the path. Read the eight surrounding dirt cells clockwise: **N=1, NE=2, E=4, SE=8, S=16, SW=32, W=64, NW=128**. A diagonal counts only when both adjoining cardinal neighbors connect. `lookup_256[raw_mask]` returns the atlas tile index for every possible raw mask; the selected entry provides its source rectangle. There are 47 canonical shapes.

Each shape assembles from four 12×12 quarters. Each corner has five states: outer rounded corner, horizontal edge, vertical edge, inner corner and full fill. Twenty oriented quarter images are retained with the source. Rounded contours, sparse grass tips and a restrained earthy lip form the boundary. There is no black terrain outline. Sparse source-texture windows keep most ground quiet; one-pixel uniform material borders and matching quarter geometry prevent texture/border seams.

Rebuild and verify from the repository root with the asset dependencies installed:

```sh
python tools/build_eldenmere_terrain.py
python tools/test_eldenmere_terrain.py
```

The retained source concept, material crops, palette, texture windows and contour parameters live in `../../../source/terrain/eldenmere/grass_dirt/`. Approval status comes from its `recipe.json` and is preserved on rebuild. Both grass and dirt are ordinary ground appearances; this pack adds no game engine, collision system or canonical map.
