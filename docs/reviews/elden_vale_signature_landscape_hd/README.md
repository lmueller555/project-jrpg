# Elden Vale signature landscape — staged asset review

This is PR 2 of the regional asset work. The pack is **not integrated**, and these
images are offline compositions, not gameplay captures or user visual approval.
Follow the [regional design](../../world/regions/ELDEN_VALE.md) and
[central terrain standard](../../TERRAIN_ART_STANDARD.md#staged-elden-vale-signature-landscape).

## Artwork and assemblies

- [Asset board](asset_board.png): coherent Pale Antlers master, separately registered
  beams/skull, regional and distant views, sixteen ridge/dressing drawings, twelve
  causeway drawings, split arch and Sanctuary miniature.
- [Distant glimpse](distant.png), [approach](approach.png), [forecourt](forecourt.png),
  [skull reveal](skull.png) and [underpass](underpass.png): illustrative camera/scale
  studies. Distant artwork omits the skull/base and is screened by woodland.
- [Inhabited causeway](causeway.png), [causeway joints](causeway_run.png) and
  [ridge joints](ridge_run.png): references for cap/port registration and reuse.
- [Clearance plan](clearance_plan.png): existing reserve public approaches and loop
  in logical units. The proposed support sits in the existing solid ridge.

The four antler parts reconstruct the same master exactly. Do not independently
mirror, rotate or rearrange them; the skull faces lower-left. Empty space between
branches stays transparent. Alpha masks are supplied for future local cutaways;
this PR does not implement fading or new collision. The arch likewise reconstructs
from its overhead lintel and side supports, with a genuinely transparent underpass.

The miniature uses current hall, cave and layered memorial-tree donors. It remains
96×80 logical units; the antler landscape is independently bounded. No new entry
geometry, river crossing, bridge repair, gate release or story knowledge is granted.
Exact species, age, death and supernatural relationships remain unresolved.

## Reproduction and limits

Run `python tools/build_elden_vale_signature_landscape_hd.py`, or add `--check` for
non-writing byte comparisons. Retained source PNGs, generation brief, source hashes,
layout plan and recipe are under
`assets/source/terrain/overworld/elden_vale/signature_landscape_hd/`. No generation
service is needed to rebuild exports. New pixel art was authored with image_gen;
export processing is limited to sampling, palette reduction, alpha/contour cleanup,
segmentation and assembly. Existing scene donors remain unchanged.

Focused tests cover support rejection on walkable ground, unchanged input geometry,
exact anatomical/arch layer reconstruction, real arch opening, density/alpha/masks
and reference module ports. The scene/collision hashes intentionally fail if the
layout changes so proposed supports must be reviewed again.

Compositions use explicit presentation scales and crops for different viewpoints;
they are not final world placements. The support study validates the existing
solid location, not every future pose/camera. Integration must ground the visible
base against that ridge, preserve complete player/party clearance, check quest
staging, implement any needed foreground cutaway, and review actual camera,
movement, save/Continue and reduced-motion behavior. Reference ports are overlap
joints, not a seamless blob/terrain autotile system. Rising Rain, weather action
poses and final atlas regeneration remain subsequent work.
