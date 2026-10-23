# Eldenmere cottage — draft for review

First front-facing cottage appearance on the 24×24 terrain grid, designed beside the approved mill. Cream plaster, brown structural timber, a low slate roof, fieldstone base, daisies in a flower box, shutters and an iron hanging light give a modest maintained village home. The 120×144 transparent prefab includes headroom for smoke; its ground rectangle is `[12,72,96,72]` (four by three tiles). Character scale remains 24×36. This is an art prefab, not a playable interior or engine collision setup.

`structure.png` holds the fixed building and dark doorway. Composite one `doors/` frame, one `lantern/` frame and optionally one `smoke/` frame above it. `closed.png` and `open.png` are ready-made static states without smoke. Five door poses compress the source leaf toward a fixed west hinge without moving its top/bottom. Opening and reversed closing play once at 100 ms per pose; hold their endpoint for a persistent state. The review repeats door use only to demonstrate it.

Smoke has eighteen 200 ms phases (3.6 seconds), with three staggered puffs. Puffs rise, drift east in a consistent breeze, expand and thin into separated opaque pixels before disappearing. Transparency is binary; no blurred alpha fades. The light moves at most one pixel while its mounting bracket remains fixed. The roof and walls stay still. The review's mill and water retain their approved six-phase timing.

`parts/` and `cottage.json` expose registered roof sections, five wall columns, the chimney, door, two windows and decorations. Source-derived clean 24-pixel roof-repeat and wall inserts support subsequent width assemblies; warm lit-window alternatives preserve the frames/shutters. The base assembly is the review milestone. Compact/wider homes and household-specific customization still need assembly and review; the separated base parts alone are not a finished all-shapes autotile system. `door_sheet.png` shows five complete poses. `components_review.png` displays the fourteen registered source parts (wide roof at 3×, others 4×).

The full scene reuses each approved running mill scene without moving existing characters or changing waterways. Only the new cottage and a short dry ground path are composited. Doorstep and approach share elevation 24. It preserves the earlier terrace example as requested; this illustrative layout establishes no final village geography or named resident.

Review files:

- `cottage_closeup.gif` / `.png`: 5× view with smoke, door use and the approach.
- `review_scene.gif` / `.png`: entire unchanged-size 30×26-tile scene at 3×.
- `scene_frames/`: eighteen native 720×624 frames.
- `preview_frames/`: transparent cottage demonstration frames, separate from game animation tracks.

Rebuild: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage.py`.
Verify: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/test_eldenmere_cottage.py`.

Approval status comes from `assets/source/terrain/eldenmere/cottage/recipe.json`. Published for review, not merged into main.
