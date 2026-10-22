# Eldenmere — first terrain source

Status: draft for user review.

`materials_concept.png` is the generated material reference: quiet/denser grass in the top half, compacted stony earth at bottom left, and a grass/dirt fringe reference at bottom right. The approved Caelan and blue female NPC previews supplied character style and scale references only. Those character assets remain unchanged.

`recipe.json` records native 24×24 material crops, a 12×12 quarter size, the named palette, sparse native texture windows, the one-pixel common texture border, corner geometry and review scales. The source is sampled with nearest-neighbor and quantized into flat material ramps. Only the specified native texture windows retain detail; all other material pixels use the base color, keeping the final ground quieter than the appearance source. The dirt edge color is reserved for contour shading, not scattered texture. No interpolated pixels or partial alpha are introduced.

`python tools/build_eldenmere_terrain.py` exports materials, then constructs twenty oriented quarter pieces under `quarters/`. Each orientation has outer, edge-x, edge-y, inner and full states. A one-pixel neighborhood halo supplies consistent edge shading across shared tile borders. Sparse grass-colored tips interrupt the earthy lip. The builder composes these into all 47 canonical masks and writes a complete 256-entry neighborhood lookup table.

The review map uses a fixed seed for grass/interior choices. Its JSON records every terrain cell and each native 24×36 character placement; the scene can be reconstructed exactly from exported tiles and existing sprites. The test scene is deliberately schematic and does not establish Eldenmere's geography or season. The wider mountain setting remains a working narrative direction, while the watermill/bridge/irrigation/eastern terrace are established opening-quest context.

Verify with `python tools/test_eldenmere_terrain.py`. Tests cover all raw mask lookups, all unique shapes, quarter reconstruction, palette/hard alpha, rotated contours, 2,048 compatible adjacent-neighborhood cases and native scene reconstruction. The source recipe is the approval record. Native art and enlarged views are rebuilt deterministically.
