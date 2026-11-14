# Iselin — first artwork sources

The user approved **Design A / Royal Envoy**: white hair, blue eyes, royal-blue
travelling clothing with silver details, an anatomical-left braid (viewer right
in front views), and a navy mantle over her anatomical-right shoulder.

The design choice is approved. The new portrait and front idle are **awaiting
user review before merge**; approval of the design does not approve these new
exports. No runtime character replacement is included in this asset milestone.

- `design_concepts.png`: original three-way concept board; only column A is selected.
- `idle_front_master.png`: generated front-facing idle artwork, retained unchanged.
- `../../portraits/eldenmere/iselin_master.png`: generated dialogue portrait master.
- `provenance.json`: source hashes, generation references, instruction summaries,
  design approval, and review scope.

Rebuild the two exports and review images from the repository root:

```sh
python tools/export_iselin_first_assets.py
python tools/export_iselin_first_assets.py --check
```

The exporter performs technical cropping, alpha isolation, uniform nearest-neighbor
reduction, whole-body registration and review layout. It does not draw new faces,
limbs, clothing or outlines. The portrait follows the existing 72×72 RGB format;
the idle follows Caelan's 24×36 RGBA canvas and existing foot/draw anchors.
