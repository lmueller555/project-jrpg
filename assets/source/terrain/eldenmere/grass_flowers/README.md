# Eldenmere grass and wildflower source — review

`materials_concept.png` retains the generated six-plant atlas guided by the approved cottage-garden scene. The original remains at `/workspace/generated_images/exec-95e99595-943e-4798-a46e-3aa0b9ca4d78.png` in the creation workspace. The committed copy is sufficient to rebuild elsewhere.

`recipe.json` records exact source crops, nearest-neighbor sample sizes and positions, material ramps, fixed-root boundary, bend-band rows, nine wind poses and all review placements. Sparse, splayed and dense grass have visible source heights of 13, 11 and 18 pixels. White daisies, yellow wildflowers and violet wildflowers have 20-pixel source heights. All fit transparent 24×24 frames alongside the existing 24×36 characters.

The exporter removes magenta with the same explicit RGB rule as the foliage exporter. Grass uses the six approved leaf colors. Source flower pixels that are green-dominant, and every pixel below the recorded blossom/leaf boundary, use that same green ramp; the other flower pixels use the appropriate petal and shared golden-center ramps. Nearest RGB material assignment and binary alpha keep the native pixels crisp. No source sprites are redrawn or recolored between animation phases.

`parts/` retains each sampled native plant, its fixed base and three full-frame, disjoint horizontal bend bands. All flower heads lie in the upper band, keeping their shapes intact. A shallow bend propagates from the upper section through two lower stem/leaf sections, then relaxes. Every section moves only zero or one pixel east; roots at native row 20 and below never move. Sections meet with at most a one-pixel horizontal step and no vertical displacement. Nine 600 ms poses include a held gust and settling pause for a 5.4-second cycle. Rest reproduces the source-derived plant exactly; this is anchored bending rather than whole-sprite translation.

The scene reads all 54 approved foliage frames without altering them. New plants use the existing 5.4-second breeze and per-instance offsets, so the combined scene remains 54×200 ms = 10.8 seconds. All new opaque pixels cover grass only, including every existing foliage phase, with no overlap between new plants. Existing buildings, paths, entrances, characters, water routes and elevations remain clear. The illustrative review placements do not establish game geography.

Build: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_grass_flowers.py`.

Test: use the same interpreter with `tools/test_eldenmere_grass_flowers.py`.

This review includes three grass silhouettes and three flower clumps. Reeds and additional plant species are separate future milestones. Design approval is pending.
