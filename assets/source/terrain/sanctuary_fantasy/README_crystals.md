# Sanctuary crystal and stone modules

`crystals.json` authors six mineral silhouettes in amethyst, cyan, opal and
amber ramps. They are native pixel graphs with separate tip, shoulder, facet
and base geometry. Broader central prisms, smaller embedded tips, uneven roots,
mineral bands and inclusions give clusters a different feel from grass or a
uniform starburst. Colorways do not assign an elemental affinity or a resource.

The tallest formations are approximately three times Caelan's 34-pixel visible
height. Each crystal has six 700-millisecond internal shimmer frames. Alpha,
canvas, root anchor and the basal five rows remain fixed. There is no translated
sprite, external sparkle or baked rectangular glow. Surface veins animate only
within their fixed native lines.

Limestone sockets and seven ancient masonry fragments retain the native pixel
structure of the established ridge crop. Its yellow-green mineral/moss colors
are remapped into an explicit quiet limestone ramp. Broken circular carvings
and branching marks are visual motifs, not readable claims about the site's
history. Memorial markers, lamps and flower offerings extend the same palette.

The manifest records native canvas size, root anchor, repository-relative frame
paths, animation timing and suggested local ground footprints. Flat veins,
buried paving/arcs and offerings have no collision. Scene placements fit solid
bases into existing blocked stone/tree areas; the scene owns final collision.

Build with `python tools/build_sanctuary_crystals.py`; add `--check` to compare
deterministic outputs without writing files. Source hashes and the recipe hash
are retained in `assets/terrain/sanctuary_fantasy/crystals/assets.json`.
`materials_review.png` places Caelan and all forms at one native scale and a
shared root baseline. Source Eldenmere and regional art is unchanged.
