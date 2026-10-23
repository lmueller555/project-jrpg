# Compact and wider cottage kit — approved

Two front-facing, single-floor layouts extend the approved cottage in all four palettes: slate/cream, terracotta/ivory, moss/buff and heather/pale.

| Layout | Ground footprint | Transparent prefab | Front windows |
| --- | --- | --- | --- |
| Compact | 3×3 tiles / 72×72 pixels | 96×144 pixels | One, right of the door |
| Approved base, read only | 4×3 tiles / 96×72 pixels | 120×144 pixels | Two |
| Wider | 5×3 tiles / 120×72 pixels | 144×144 pixels | Three, including the added bay |

All ground rectangles begin at `[12,72]`. Tile size remains 24×24 and character scale remains 24×36. Prefabs include transparent headroom for smoke. Modules are added/removed at native scale; window, door, roof-tile, stone and timber detail sizes are preserved. The compact keeps a flower box below its remaining window. The wider layout keeps the original flower box and adds one unscaled shuttered window.

Each `<shape>/<palette>/` folder contains:

- `structure.png` and registered `parts/` with assembly/provenance in `cottage.json`.
- Five `doors/` poses, `door_sheet.png`, static `closed.png` and `open.png`.
- Eighteen `smoke/`, `lantern/` and transparent `preview_frames/` phases.
- Native palette and prefab metadata, window rectangles and ground registration.

Opening/closing metadata plays once at 100 ms per pose. Hold its endpoint when open/closed. Ambient layers retain the approved 200 ms timing, 3.6-second smoke cycle, consistent eastward smoke drift and anchored one-pixel lantern sway. Their pixels are translated intact, with no clipping or deformation. The demonstration loops door use only for review; it introduces no engine entry behavior, interiors or collision system.

Review exports:

- `sizes_review.gif` / `.png`: compact, approved base and wider in slate at the same 4× pixel scale.
- `palettes_review.gif` / `.png`: all eight new cottages, compact row above wider row, labeled at 3×.
- `review_scene.gif` / `.png`: full 32×54-tile scene at 2×.
- `courtyard_closeup.gif` / `.png`: the new two-row demonstration courtyard at 2×.
- `scene_frames/`: eighteen native 768×1296 scene frames.

The existing scene is preserved except for a small dry connection beneath the old courtyard path. New homes occupy the southern extension, with an additional two grass columns at the east edge. Doorsteps and their connected paths all share lower-ground elevation zero. Existing waterways, terrace, mill, bridge, characters and cottages remain in place. This is an illustrative asset review arrangement, not a canonical level or resident assignment.

Rebuild with `python tools/build_eldenmere_cottage_shapes.py`; verify with `python tools/test_eldenmere_cottage_shapes.py` using the Pillow environment in `tools/README.md`. Status comes from the retained source recipe. The compact and wider layouts, all four palette assemblies and their inherited animations are approved for main.
