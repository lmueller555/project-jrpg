# Eldenmere starter foliage — draft for review

One rounded broadleaf tree and one compact shrub begin the foliage kit. Deep green undersides, warmer sunlit leaf tips and the approved brown wood ramp match the village. Their leaves move locally in a restrained eastward breeze, agreeing with cottage chimney smoke; their bark, branches, roots and ground-shadow pixels remain fixed.

| Asset | Transparent frame | Ground rectangle | Loop |
| --- | --- | --- | --- |
| Tree | 96×120 pixels | `[36,96,24,24]` | Nine poses × 600 ms = 5.4 seconds |
| Shrub | 24×24 pixels | `[0,0,24,24]` | Nine poses × 600 ms = 5.4 seconds |

Terrain remains 24×24 and characters remain 24×36. The tree's visible art is about 90×92 pixels; padding accommodates registration and leaf motion. Ground rectangles are placement anchors, not a new engine collision implementation.

Each asset directory contains `idle.png`, `frames/`, `sheet.png`, fixed `trunk.png`/`shadow.png`, `canopy.png`, source-derived `clusters/` and `foliage.json`. Composite in metadata draw order: shadow, canopy backing, translated leaf clusters, then fixed wood. Maximum displacement is one pixel east/up; individual poses relax toward rest. The whole plant and ground shadow never translate. The source rest pose is preserved exactly. All exports use named colors and binary alpha, without blur or fractional transparency.

Review files:

- `foliage_review.gif` / `.png`: tree at 6×, shrub detail at 12×, plus unchanged Caelan/shrub at matching 6× scale. The character appears only on this review board for scale.
- `garden_closeup.gif` / `.png`: 4× cottage-garden view with the new foliage.
- `review_scene.gif` / `.png`: full existing 32×54-tile scene at 2× with two tree and four shrub instances.
- `scene_frames/`: fifty-four native 768×1296 frames.

The full-scene/garden loops run 10.8 seconds to preserve both the new 5.4-second foliage cycle and the approved 3.6-second cottage cycle. Water, doors, smoke and existing characters keep their original frames/timing. Foliage phases are staggered by instance. Plants only cover existing grass; all waterways, paths, buildings, entrances and characters remain clear. Ground placements share the existing lower-ground elevation zero. No older scene or asset file is modified, and the review does not establish final village geography.

Rebuild with `python tools/build_eldenmere_foliage.py`; verify with `python tools/test_eldenmere_foliage.py` in the Pillow environment documented in `tools/README.md`. Status comes from `assets/source/terrain/eldenmere/foliage/recipe.json`. Published for review, not merged into main. This first milestone adds no other foliage designs yet.
