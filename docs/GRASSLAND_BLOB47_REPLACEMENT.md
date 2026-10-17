# Polished blob47 atlas — asset-only Phase 1

This generator uses the approved 1254×1254 original source sheet, combining source grass and dirt variants inside tiles and applying deterministic, mask-driven frayed organic transitions. Shared boundary texels are fixed and the 47 masks remain canonical. Semantic IDs stay exactly the same (8 grass, 8 dirt, 47 transition IDs).

Run `python -m tools.terrain.build_blob47` and `python -m pytest tests/test_grassland_blob47.py tests/test_grassland_autotile.py tests/test_grassland_seams.py -q`.

No Eldenmere renderer, collision, input, map, or gameplay changes belong in this PR. Renderer work remains in stacked PR #32.

The previous in-chat polished comparison was a visual prototype; the generated GitHub atlas must undergo byte-level verification and CI seam checks before merging.
