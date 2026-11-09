# Nivareth authored combat sources

These six PNGs are unchanged original `image_gen` outputs. The registration
records their generated filenames and SHA-256 hashes. The first atlas establishes
the white crystal core, hollow curved ice mantle, and disconnected shard limbs;
the following atlases use that design as a reference. Layout corrections were
made with `image_gen` before export so complete poses have transparent gutters.

The pack contains **176 distinct authored drawings**: emerge 8, idle 16,
Rime Needle 16, Glassfall 24, Gather Frost 24, charged hold 16, Frostspire Thrust
24, settling 16, hurt 8, and defeat 24. Every drawing is used exactly once.
Movement and disintegration are drawn in the atlases. Runtime export does not
create extra poses through transforms, mirrored frames, or recolored copies.

`registration.json` identifies every source cell, fixed per-atlas native scale,
virtual floor, and body/core/contact/cast anchors. A floating elemental has no
anatomical feet; the fixed virtual floor keeps it registered to the battle scene.
The different atlas scales account for their different layout sizes. Extraction
keeps all shards, including disconnected fragments, thresholds alpha at 128,
uses nearest-neighbor registration and one shared 64-color opaque palette.
Source RGB and generated PNGs remain unchanged.

Build and verify from the repository root:

```sh
python tools/build_nivareth_combat.py
python tools/build_nivareth_combat.py --check
python tools/build_nivareth_combat.py --review
```

The builder rejects clipped source cells, clipped native silhouettes, duplicate
native drawings, unused drawings, non-binary alpha, and source hash changes.
Art review media is in `docs/reviews/nivareth_combat/`; it is separate from a
gameplay capture.
