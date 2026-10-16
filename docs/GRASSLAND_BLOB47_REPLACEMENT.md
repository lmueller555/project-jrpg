# Blob47 replacement atlas (visual review required)

The 47 source illustrations could not be assigned to canonical masks by row order. This candidate reconstructs the 47 masks from the approved source's grass and dirt texture samples. It uses explicit symmetric shared-edge rules and masks from engine.grassland_autotile.

**Technical gates:** 47 canonical masks and 16 base textures; 63 atlas cells; deterministic generation; strict byte-identical neighbor-edge tests over randomized composed maps; source dimension check; existing map/collision data untouched.

**Artistic gate not passed:** the replacement is more repetitive and has simpler transition contours than the illustrated concepts. Do not enable it by default in Eldenmere or merge until native-size and in-game screenshot review accepts the look.

Generate: `python -m tools.terrain.build_blob47`. Test: `python -m pytest tests/test_grassland_blob47.py`.
