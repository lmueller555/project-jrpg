# Elden Vale regional HD foundation — offline review

This staged pack follows the [terrain standard](../../TERRAIN_ART_STANDARD.md#staged-elden-vale-regional-hd-foundation)
and [regional design](../../world/regions/ELDEN_VALE.md). It is not selected by
runtime maps, and these compositions are not gameplay screenshots or user approval.

- [Asset board](asset_board.png): regional exports and all 51 vegetation designs.
- [Farm/material scale](scale_scene.png): regional building/prop proportions against
  approved Caelan artwork and shared emerald ground; a bank donor demonstrates contact.
- [Woodland](woodland_scene.png), [riverbank](riverbank_scene.png), and
  [bridge](bridge_scene.png): native-size donor/asset arrangements for readability.
- [Antler blockout](antler_blockout.png): current roads, walls, rivers and known places,
  with an illustrative northeast ridge study area and overhead envelope. No solid
  supports are approved or registered here. Detailed reserve station clearance,
  viewpoints and foreground visibility remain required before PR2 finished art.

Sources are retained original drawings and existing HD packs, not enlarged legacy
runtime PNGs. Recipes record dependencies/hashes; existing material colors are
retained with explicit emerald green-role mapping. Exported masks/footprints do
not alter collision. The wide bridge retains its empty collapsed span and 72-unit
road depth. Variants should be composed into coherent areas with blended contacts;
actual streaming integration, material seams, movement, NPC contact poses,
occlusion, pause/focus and reduced-motion lifecycle still need gameplay review.

Reproduce using `python tools/build_elden_vale_hd_foundation.py`; use `--check`
for byte-for-byte comparison without writes. No external generation service is
required to reconstruct these exports. No source drawing or legacy bank is retired.
