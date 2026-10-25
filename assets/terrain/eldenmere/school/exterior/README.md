# Eldenmere schoolhouse exterior — awaiting review

Native 192×192 transparent pixel-art frames, matching 24×24 terrain and the
approved character scale. Ground registration is [24,96,144,96], a six-by-four
terrain-tile footprint. The schoolhouse uses the cottage stone, plaster, timber,
glass and smoke palettes with a muted blue-green roof and small bronze bell.

Tall paired classroom windows, worn timber braces, a sheltered central doorway,
an open-book sign and warm entrance lantern distinguish it from a home. The
roof bell remains still; the lantern, thin chimney smoke and one-pixel book-sign
movement repeat over eighteen 300 ms phases (5.4 seconds).

`school.json` records full repository-relative frame paths and source layers.
The five door patches are 20×34 at local [86,150]. Their first image matches the
closed crop in every exterior phase; the runtime overlays opening/closing poses
without replacing the rest of the building. The step ends at local row 191.

Build with `python tools/build_eldenmere_school_exterior.py`. No existing asset
exports are modified. Source recipes and separated layers are retained in
`assets/source/terrain/eldenmere/school/exterior/`.
