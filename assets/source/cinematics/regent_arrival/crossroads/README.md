# Regent crossroads — offline retained-source composition

This is **not newly image-generated art**. No image generation tool was available
or used. The panorama is an offline composition of the retained high-resolution
nature/farm/detail sheets, their original raw material cells, and the original
wide bridge generation. Only the new bridge is **assembled art with additional
retained outer masonry columns**, not a simple crop export of an approved runtime
image. A calm **water-only** crop from the retained cinematic riverbank supplies
water detail, not its river shape, bridge, horizon or banks. Its recorded 0.6
mean-centered contrast and RGB multiply subdue highlights before quilting; no
source image is repainted and no exported 24px water texture is enlarged.
No regional chart, tiny map crop, exported 24px texture, actor sprite, building at
the junction, or gate is an illustration input. Original files are read-only.

## Native contract

- 4928×1728 opaque RGB panorama; 34,062,336 bytes if decoded to RGBA (<50 MB).
- Single invertible ground-plane projection: origin tile `[-136,-28]`, scale
  `[28,24]` pixels/tile, offset `[0,0]`. East is right; south is down.
- The 28px horizontal scale is chosen to retain both broken abutment faces and
  inner bank-damage edges in a native 480×320 shot without a local zoom. It is not
  an enlargement of the regional map. Native humans remain 77–80px tall; large
  oaks are individually reduced to roughly 142–193px, with bounded source crops.
- Actual three-way junction `(7,4)`: stone N/slightly E toward Eldenmere, the
  same stone road WSW toward the western bridge, and rutted dirt SSE. There is
  no fourth branch or watercourse at the junction.
- Geometry comes directly from the **already densified** points in the pinned
  regional manifest. No exporter is imported or rerun; original widths, farm
  access, fields, relief spur, river and scorched parcels stay unchanged.
- The exact junction-to-deck-center road arc is about 122.068 tiles. Camera
  points sample at most one tile of actual arc length, with exact endpoints.
  The source road's tiny eastward bridge-approach nudge remains in the explicit
  source point list; the chosen exact arc samples are monotonically westward.
- Absolute actor foot anchors and native framing are in the runtime manifest.
  `carrier` maps to the parent's existing `local` actor. The optional caravan
  anchor is mostly beyond the viewport's right edge on the clear eastern verge;
  neither its image nor any other actor image is baked or read by the builder.
- The 960×480 runtime reference scene is an exact, unscaled panorama crop.
  Its native 480×320 camera offset is `[240,80]`.

## Bridge scale, damage, and honest framing limits

The canonical world/prop anchor is `(-111,30)`; its **deck center is `(-111,29)`**.
The canonical repaired deck footprint remains `[-120,27.5,18,3]`, i.e. 504×72px
under the common projection. The original 1774×887 bridge is uniformly reduced
**once** to 232×116 with nearest sampling. Its two 116px source components retain
their jagged inner faces and are placed at x=84 and x=304 on a 504×116 canvas.
Each new abutment is explicitly assembled to **200px** by adding **84px of
retained outer masonry/parapet/arch-front columns at its OUTER end**. These are
1:1 copies from that same reduced image, not resized or repainted stone. Two
outer panel strips keep the support/front joins structural; three split,
staggered cobble courses interrupt a full-height copy/paste seam. Neither inner
fracture is repeated or changed. Every source rectangle and output position is
recorded in the recipe, manifest, geometry and provenance.

This changes **only the newly authored crossroads illustration**: it is not a
simple crop export, nor an unchanged export of the approved 288px bridge. All
original approved runtime bridge images and original source images are untouched.
The former padding-only arrangement left a 290px alpha-empty gap; the new output
has a measured **122px transparent collapse**, x=[191,313) in the sprite, close to
the approved source's 74/288 gap proportion rather than exaggerating it. Both
broken faces now read near the bridge center (native x=206 and x=329, around the
fixed x=268 bridge center), while the canonical 504px physical span, 72px clear
deck depth and 10-tile north–south river remain unchanged. No nonuniform stretch,
local camera zoom, bank shift or actor-anchor adjustment is used.

The native endpoint shows the collapse, both broken abutment faces and **inner
parts** of the two canonical scorched bank polygons. It cannot show all of an
18-tile span and both complete damage parcels in 480px. The eastern terminal
approach is partly cropped. The unscaled 960×480 bridge reference shows the full
physical crossing, both banks and their complete damage; **no camera zoom** or
shortened world-distance claim is made. The river follows the western canonical
north–south watercourse, including its actual bend.

## Rebuild and verification

Run the new builder with the configured asset interpreter:

    /usr/local/bin/python3 tools/build_regent_crossroads.py
    /usr/local/bin/python3 tools/build_regent_crossroads.py --check
    /usr/local/bin/python3 -m unittest discover -s tests -p test_regent_crossroads_art.py

Dependencies are the existing asset requirements (Pillow 13, NumPy 2+). There is
no network call, game import, display/audio initialization, or runtime patch.
`--check` is read-only. Source SHA256s are pinned in the authored recipe. PNG
checks compare decoded pixels if compression differs; exact JSON still has to
match. Rebuilds on the same local stack reproduce PNG bytes and do not rewrite
already identical products. All writes are confined to the two new crossroads
trees and geography/crossroads/bridge-prefixed review PNGs; existing clerk review
images and all other assets are outside the writer's allowlist.

The 40 read-only art tests retain the original geography/staging coverage and
add an independent exported-pixel regression for the actual collapse width,
substantial visible abutments, native face positions and source-registered 72px
deck samples in both the component image and graded panorama. A separate pixel
oracle checks one uniform source reduction followed by explicit 1:1 outer-column
assembly, staggered joins and untouched inner fracture pixels. Calm-water crop,
contrast and deterministic, nonperiodic quilting are checked as well.

`geometry.json` preserves actual regional points/widths, sample anchors, the
projection and native binary masks. `material_samples.json` records every
minimum-error-quilt crop location and flip in the reduced **raw source** sample.
`provenance.json` records original source hashes, crop registrations, actual prop
placements, component registration, tool hash, grade, and decoded product hashes.
Raw materials are reduced, not enlarged; nonperiodic minimum-error seams follow
texture detail rather than exposing rectangular swatch edges. Grass/verge
overlaps and source-crop props are layered over geographic masks under shared
upper-left lighting. Review labels/rulers/actor rectangles exist only in the
separate review PNGs, never in the runtime panorama or exact reference crops.

This deliberately bounded oblique ground-plane scene has no invented horizon.
Retained farm motifs are stylized; their placement, not their decorative outline,
is canonical. Static props are baked into an opaque background; no genuine
foreground/depth parallax layer is supplied or claimed. This offline refinement
does not edit parent integration, scene data, renderers, capture tools, music,
actors or existing exporters.