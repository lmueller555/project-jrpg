# Iselin — first artwork sources

Authoring rules live in the [global sprite and animation standard](../../../../docs/SPRITE_ANIMATION_STANDARD.md).
This file retains asset-specific implementation details and review history;
older construction methods and review-stage wording are historical, not current
general instructions.

The user approved **Design A / Royal Envoy**: white hair, blue eyes, royal-blue
travelling clothing with silver details, an anatomical-left braid (viewer right
in front views), and a navy mantle over her anatomical-right shoulder.

The portrait, 42×72 directional idles and all four 16-frame walks are approved
and merged (walk completion: PR #201). The initial 24×36 idle described below
was superseded by the detailed export. Runtime Aldric-to-Iselin character
replacement remains separate. See the global standard and the
[detailed idle implementation](../../../../docs/reviews/iselin_first_assets/IMPLEMENTED.md)
for current rendering dimensions; this file preserves the initial source study.

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
the initial idle study used a 24×36 RGBA canvas. That study is historical;
the approved detailed sprite uses 42×72 artwork at 2 artwork pixels per world
pixel, representing a 21×36 logical frame.
