# Echo Chamber rupture modules

`authored_modules.png` is the retained image-generation output, using the live
limestone cave as its palette and camera reference. It contains eight distinct
cells: north/south/west/east rims, a deep layered face, fresh rubble, a branching
fissure and climbing scratches. Individual microcrystals remain tiny.

`python tools/build_cave_chasm_assets.py` exports reusable native modules and
`assets/terrain/limestone_cave/chasm/assets.json`, retaining source hash, cell
bounds, crop bounds and nearest-neighbor registration. The composed 288×174
rupture uses those modules around a dark depth mask. There is no painted room
background, body deformation, generated character or new travel scene.

The continuous map recipe owns placement, blocked opening, safe landing and
inspection. Rising aether is runtime VFX in `cave_chasm_fx.py`, shared with the
12-second Echo Chamber battlefield export. Other cave battlefields keep their
existing six-second cycles and image pixels.
