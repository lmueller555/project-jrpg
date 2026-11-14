# Iselin — portrait and front idle review

The user selected **Design A / Royal Envoy** and requested these first two assets
for visual review before merging. The design is approved; this new artwork is
**awaiting user review**. The work remains on `art/iselin-portrait-front-idle`.

![Game-sized portrait and idle exports, enlarged with cast comparison](preview.png)

## Assets

- `assets/portraits/eldenmere/iselin_neutral.png`: 72×72 RGB neutral dialogue
  portrait with an opaque green-gray backdrop, matching the current portrait format.
- `assets/characters/iselin/idle_front.png`: 24×36 transparent front idle,
  foot anchor `[12, 34]`, map draw anchor `[12, 30]`.

The white anatomical-left braid (viewer right), blue eyes, royal-blue coat,
silver closures and anatomical-right navy mantle match the selected concept.
The native silhouette is slenderer than Caelan and Mira; the comparison uses
their actual current artwork at a common foot line and identical scaling.

`portrait_4x.png` and `idle_front_16x.png` show the actual native exports enlarged
with nearest-neighbor sampling. They are not substituted high-resolution masters.
`native_comparison.png` and `comparison_4x.png` retain the actual cast scale.

## Scope and verification

The new actor is not registered in gameplay yet. Existing dialogue, actors,
quest progress, save data, and other cast art are unchanged. Side/rear artwork,
walking and cinematic poses are outside this two-asset milestone.

Reproduce and verify with:

```sh
python tools/export_iselin_first_assets.py
python tools/export_iselin_first_assets.py --check
```

The scoped exporter only crops, isolates hard transparency, reduces with one
nearest-neighbor scale, registers the complete drawing and arranges previews.
Image generation supplies the artwork. Generated masters and the selected
concept are preserved unchanged; source hashes, extraction geometry and output
hashes are recorded in
`assets/source/characters/iselin/first_assets_export.json` and generation
references are in `provenance.json` beside it.

Visual review covered the portrait, native reduction, braid/mantle orientation,
full-body anatomy, outline visibility, planted feet and same-scale cast comparison.
No full gameplay or cinematic compliance is claimed for these unintegrated assets.

Verification passed: all nine generated outputs match a fresh deterministic
export; both native PNGs load in Pygame; dimensions and RGB/RGBA formats match
the existing conventions; sprite alpha is exclusively 0/255; its silhouette
is contained at `[6, 1, 19, 35]`; metadata retains the intended anchors and
separate design/artwork approval states. Both blue eye pixels survive reduction.
