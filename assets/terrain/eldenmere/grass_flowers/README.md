# Eldenmere grass and wildflowers — approved

Three grass shapes (sparse, splayed and dense) and three flower clumps (white, yellow and soft violet) extend the approved garden foliage. Greens reuse the tree/shrub ramp; subdued petal colors keep the cottages and characters readable.

Each plant uses a transparent 24×24 frame, a 24×24 placement rectangle and no blocking collision. Grass source heights range from 11–18 pixels; flowers are 20 pixels tall. These are decorative overlays, not new ground or autotile replacements.

Each directory contains `idle.png`, `frames/`, a 216×24 nine-pose `sheet.png`, `base.png`, three `bands/` and `plant.json`. Composite the translated bands, then the fixed base. Horizontal offsets are at most one pixel east, with no vertical movement. Flower heads remain intact while the stems bend; roots stay fixed. The 5.4-second cycle uses nine 600 ms poses with a held gust and settling pause. Encoded GIFs can merge identical held poses while retaining their complete durations.

Review files:

- `garden_closeup.gif` / `.png`: updated cottage garden at 4×.
- `review_scene.gif` / `.png`: full existing scene at 2×.
- `plants_review.gif` / `.png`: all six plants at 12×, plus unchanged Caelan and plants sharing 3× scale.
- `scene_frames/`: 54 native 768×1296 frames, 200 ms each, for a 10.8-second shared repeat.

The scene adds 22 small plant instances to grass around the cottage examples. Phase offsets avoid identical neighboring motion. All previous foliage, smoke, doors, lights and water retain their original pixels and timing. Plants leave paths, entrances, waterways, buildings and characters clear. This is an art-review scene, not a finished level. Lossless difference GIFs keep the enlarged previews small enough to load reliably.

Rebuild with `python tools/build_eldenmere_grass_flowers.py`; verify with `python tools/test_eldenmere_grass_flowers.py` in the Pillow environment documented in `tools/README.md`. Source, sampling and placement settings live under `assets/source/terrain/eldenmere/grass_flowers/`. The six designs and their animations are approved for main. Reeds are the next foliage milestone.
