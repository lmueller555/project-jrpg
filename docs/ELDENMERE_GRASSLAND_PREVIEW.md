# Eldenmere default grassland terrain

Eldenmere now renders grass and dirt paths using the approved native 32x32 canonical blob47 atlas on the 640x448 presentation canvas. No environment variable or preview toggle is required.

The obsolete 16x16 **grass and path** manifest entries have been removed. The existing environment atlas **must remain** for water, trees, farmland, floor, and the animated water/smoke effects, which do not yet have new production replacements. The older illustrated source-slot grassland atlas stays untouched as historical/source staging while the approved canonical atlas is active.

The existing 16-unit map, collision and movement systems, camera positions, NPCs, interactions, Sanctuary, and other scene materials are unchanged.

Test: `python -m pytest tests/test_eldenmere_default_ground.py tests/test_eldenmere_ground.py tests/test_grassland_blob47.py -q`.
Capture: `python -m tools.terrain.capture_eldenmere_preview`.
