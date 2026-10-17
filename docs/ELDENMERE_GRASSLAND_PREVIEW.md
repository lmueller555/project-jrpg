# Eldenmere grassland preview

This changes **rendering only**. The original logical map grid is 16 units, and this draws the canonical mask-resolved ground at 2x on the 640x448 presentation canvas. Collision, positions, objects, movement, camera math, dialogue, NPCs, and other terrain materials remain on the original code paths.

Run `JRPG_GRASSLAND_BLOB47=1 python main.py` on macOS/Linux to enable the **optional** native-grassland preview. Unset the environment variable (or set it to 0) for existing visuals.

The new terrain has passed programmatic edge-matching checks, but its artistic style is **not approved** yet. This preview must be evaluated in Eldenmere before switching it on by default. The atlas `assets/atlases/terrain/grassland_blob47.png` and its 63 manifest IDs come from stacked PR #31. The polished atlas is already merged into main via PR #31. Keep preview opt-in pending final user acceptance.
