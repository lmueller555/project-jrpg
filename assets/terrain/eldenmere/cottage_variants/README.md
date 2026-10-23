# Cottage palettes — approved

Three new palettes accompany the approved slate-roof, cream-plaster cottage:

| Directory | Roof | Plaster | Timber |
| --- | --- | --- | --- |
| `terracotta/` | Muted clay red | Ivory | Dark oak |
| `moss/` | Moss green | Warm buff | Walnut |
| `heather/` | Dusky heather | Cool pale | Weathered ash |

Each directory contains the complete 120×144 cottage kit: fourteen registered components plus reusable inserts and lit-window alternatives, fixed structure, five door poses/sheet, eighteen lantern/smoke layers, static open/closed states, eighteen transparent demonstration composites, palette and `cottage.json`. Placement retains the approved 96×72 ground rectangle at `[12,72,96,72]` on the 24×24 terrain grid. Pixel silhouettes, registration and animation phases are identical to the base. Stone, glass, white flower details, foliage, golden lamplight and pale smoke retain their original colors. The retained source recipe and builder document semantic color aliases in the roof and protected detail pixels.

Opening/closing door tracks play once at 100 ms per pose; hold the endpoint for closed/open states. Smoke/lantern layers retain the approved 200 ms ambient timing and 3.6-second smoke cycle. Repeated door use in the review is demonstration only, not autonomous door behavior for the game.

Review exports:

- `variants_review.gif` / `.png`: all four palettes side by side at 4×, labeled and synchronized.
- `review_scene.gif` / `.png`: 30×36-tile scene at 2× with the original cottage in place and three new homes in a southern demonstration courtyard.
- `courtyard_closeup.gif` / `.png`: new variants in their scene context at 3×.
- `scene_frames/`: eighteen native 720×864 scene phases.

The earlier scene is preserved except for a dry connection to the existing lower path. Its NPC remains untouched. Additional ground extends the canvas southward. The three cottage thresholds and approach occupy the lower ground at elevation zero; no new waterways or elevation transitions are introduced. The original base cottage retains its original placement. This is an asset review arrangement, not final village geography or a game level.

Rebuild using `python tools/build_eldenmere_cottage_variants.py`; test with `python tools/test_eldenmere_cottage_variants.py` (Pillow environment documented in `tools/README.md`). Status comes from the retained source recipe. The three palettes and their animations are approved for main.
