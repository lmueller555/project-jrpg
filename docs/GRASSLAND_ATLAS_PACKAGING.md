# Grassland v1 source-slot atlas

Run `python -m tools.terrain.build_grassland_atlas` (requires Pillow) to regenerate the native 256×256 RGBA PNG from the illustrated 1254×1254 source sheet. All 63 occupied 8×8 cells are packaged as 32×32 runtime sprites. The 64th source cell is unused.

**Important:** This is an image packaging layer, **not** a verified 47-mask blob implementation. The generated illustration has grid dividers and non-native pixels; extracting/downscaling it does not guarantee seam alignment, exact pixel fidelity, or correct neighborhood transitions. The transition sprites deliberately have source-slot IDs. A future visual review and manually verified 47-mask mapping must precede autotiling or Eldenmere integration.

Run `python -m pytest tests/test_grassland_atlas.py` to check atlas dimensions and metadata.
