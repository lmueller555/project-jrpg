# Caelen V2 down — finalized native production artwork

The exact 160×48 RGBA PNG `assets/atlases/characters/caelen_v2_down.png` contains five independently hand-refined native 32×48 frames: idle, walk 1, passing 2, walk 3, passing 4.

Design: brown tousled hair, blue tunic with cream/gold trim, cuffs, belt buckle, dark trousers, complete brown boots. Transparent background and nearest-neighbor presentation. Walking playback target is 140 ms per frame.

The native production file is checked for geometry, transparency, foot baseline and distinct poses. The older `assets/source/characters/caelen/v2/caelen_v2_down_prototype.png` is a historical work-in-progress and **not** the final version.

**Not wired into the game:** Keep existing `caelen.png` and active animation manifest until all 20 Caelen V2 frames are complete and tested. Do not use the partially completed V2 strip as an incomplete 4-direction runtime atlas.

Check: `python -m pytest tests/test_caelen_v2_down_final.py -q` (Pillow).
