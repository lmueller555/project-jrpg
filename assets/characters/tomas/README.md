# Tomas — front idle

Visual design approved in conversation; this native front idle **awaits review**.

The sprite has tousled honey-blond hair with a cowlick, two green eyes, a short rust-red tunic over an ivory shirt with rolled cuffs, dark brown trousers, a repaired patch on his anatomical left knee (viewer right), and worn brown ankle boots. His hands are empty. No cloth ties, tools, weapons or religious symbols are included. His exact age remains unspecified.

- `idle_front.png`: RGBA 24×36 frame, hard alpha; occupied bounds `[6,3,12,32]` (x, y, width, height).
- `idle_front.json`: frame, height comparison, eye/patch landmarks, palette/source paths and independent sprite approval status.
- `palette.json`: named materials and pupil/iris colors.
- `idle_front_review.png`: opaque RGB review at 24× nearest-neighbor scale.
- `scale_comparison.png`: Caelan, Tomas and Serene together at 16× with the same foot baseline.

Tomas is visibly 32 pixels tall, two pixels shorter than Caelan's 34, and narrower (12 versus 14 pixels across the full occupied bounds). All use 24×36 frames and `[12,34]` foot anchors. Transparent rows above Tomas accommodate the height difference. The patch is a small native accent; fine source details simplify at this resolution.

Rebuild with `python tools/build_tomas_idle.py` from the repository root. Retained concept, recipe and four reconstructable full-frame layers are under `assets/source/characters/tomas/`. This milestone includes one still front pose; directional views and walking animations will follow review.
