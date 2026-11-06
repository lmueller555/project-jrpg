The retained full-scene imagegen edit converts the first three flower-pot
windows into open floor-level cloister bays. The fourth bay keeps its original
worktable, pots, baskets, pail and leaning tools. All existing sanctuary assets
remain untouched.

Run `python tools/build_sanctuary_cloister_openings.py` from the repository root
to export the localized opaque ground patch and eight replacement depth
silhouettes. `--check` verifies source hashes and exact exported bytes without
writing files. The recipe records the retained sources, crop, native pixel
registration, interior rectangles and depth masks.

The opaque patch occupies native bounds (630, 240, 803, 324), but generated
pixels enter only three interior rectangles. Original source pixels preserve
every column, arch, roof tile and occupied eastern bay. The manifest replaces
only `cloister_depth`; the new floor patch sorts before actors, rear wall at
285, original front architecture at 312, and eastern stock at 325. Foreground
depth remains transparent across the full first-three bay foot rectangles at
(666, 302), (717, 302) and (771, 302).

The rear wall's dark face ends around native y281; shaded flagstones continue
from there into the courtyard. Collision can follow the visible wall using
native bounds (631, 276, 222, 9), with floor beginning at y285. Runtime geometry,
actor placement and interaction remain the scene builder's responsibility.
