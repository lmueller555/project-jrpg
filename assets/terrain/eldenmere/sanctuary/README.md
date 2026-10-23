# Eldenmere sanctuary exterior — approved

Static first appearance review of the agreed sanctuary design, placed at its approved northwest town location. Terrain remains 24×24; Caelan remains 24×36.

- `sanctuary_review.png`: entrance and courtyard at 4×, with Caelan beside the closed doors; 1632×1744 including captions.
- `exterior_review.png`: isolated exterior at 4× on an opaque neutral background, with Caelan for scale.
- `town_review.png`: updated full-town still at 2×, 3072×2784 including captions.
- `closed.png`: transparent 216×216 native drawing frame, with 192×120 ground rectangle (8×5 tiles).
- `town_native.png`: native 1536×1344 town view, with the original Caelan at the commons.
- `entrance_native.png`, `scene_frames/frame_01.png`: native close-up and full scene with Caelan at the entrance.
- `sanctuary.json`, `palette.json`: native geometry, source parts, material ramps and review status.

The building has cream plaster, timber framing, fieldstone foundations, blue-gray slate, three narrow arched windows, a shallow door canopy, paired closed doors, a left timber belfry with a bronze bell and a right stone chimney. Bell, lantern and doors are stationary for this review; sanctuary smoke and animated layers are deferred until appearance approval.

The footprint and courtyard are preserved. The exported doorway aligns with the existing approach and fits the original full-width actor probe. The town outside the sanctuary drawing bounds is pixel-identical to the approved first frame. Its native art and exported files remain unchanged.

Rebuild with `tools/build_eldenmere_sanctuary.py`; verify with `tools/test_eldenmere_sanctuary.py`. Retained source and export settings live under `assets/source/terrain/eldenmere/sanctuary/`. The exterior is approved; original review images remain as the appearance record. The approved `../sanctuary_charm/` pack adds ambient animation and garden dressing. Sanctuary interaction, interiors, engine collision and transitions remain future work.
