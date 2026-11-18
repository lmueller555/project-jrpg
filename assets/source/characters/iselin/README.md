# Iselin — native character sources

Iselin's approved native design uses white hair, blue eyes, royal blue and
silver travelling clothes, an anatomical-left braid and anatomical-right mantle.
The four idles and four 16-frame walks are integrated at 24×36 native world
pixels, preserving the existing 8×4 collision probe and 560 ms walk cadence.

Each `native_*` directory retains its complete authored source images,
registration recipe and source/output hashes. These approved native source and
export PNGs remain unchanged. The superseded detailed masters, trial exports,
old partial repairs and obsolete dedicated animation exporters were deleted.
Their lessons remain in the central animation standard rather than parallel
legacy guides.

The dialogue portrait is independent: its approved master remains at
`assets/source/portraits/eldenmere/iselin_master.png`, and
`tools/export_iselin_portrait.py` reproduces the unchanged 72×72 RGB export.

Build the live ordinary actor with `tools/build_iselin_native_actor.py` and the
scene-specific views with `tools/build_regent_iselin.py`. Use `--check` to verify
exports without writing. Individual native idle/walk recipes remain available
for maintenance; their source directories document the actual extraction and
registration, including preserved approved head regions.

Authoring rules live in the
[global sprite and animation standard](../../../../docs/SPRITE_ANIMATION_STANDARD.md).
See the [native integration review](../../../../docs/reviews/iselin_native_integration/README.md)
for current production evidence, scope and reproduction. Original native
approval captures remain historical snapshots at their recorded commits.
