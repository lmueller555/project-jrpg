# MQ02 riverbank scenery sources

These PNGs are original artwork generated with the image generation tool for
Mira and Caelan's first story battle north of Eldenmere.

- `millrace_background_generated.png` is the complete opaque riverbank
  panorama. References were the current Eldenmere battle clearing, the actual
  playable town overview and the upstream map overview. The camera looks back
  south/southwest toward distant cottages and the sanctuary. The river curves
  along the near left edge, beside a broad dry fighting bank. The broken tree,
  exposed roots, reeds and fresh wood connect the scene to the intake problem.
- `millrace_fallen_tree_generated.png` is an isolated transparent top-down tree
  prop, using the existing village tree and upstream overview as references.
  Jagged breaks, gouged bark, exposed roots and the missing limb establish the
  evidence encountered on the exploration path. The original tree prop, rather
  than a newly painted collision rectangle, is the visible object.

Run `python tools/build_mill_battlefield.py` to reproduce the native scenery.
The exporter only uses nearest-neighbour scaling, alpha thresholding/trimming,
and canvas registration. It does not paint scenery or alter the exploration
map's collision. Generated sources are retained intact; their hashes and
dimensions are recorded in the exported metadata.

Runtime outputs:

- `assets/combat/millrace/background.png`: opaque 480×320 battle canvas.
- `assets/combat/millrace/scene.json`: location and source metadata.
- `assets/story/mill/encounter/tree_evidence.png`: transparent 128×96 prop.
- `assets/story/mill/encounter/scene.json`: placement and source metadata.
