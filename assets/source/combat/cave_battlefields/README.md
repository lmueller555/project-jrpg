# Sanctuary cave battlefields

These four 480 × 320 combat views are assembled from the approved limestone
terrain modules used in the continuous Sanctuary cave. They are not generated
panoramas or screenshots of the exploration map.

| Battlefield | Source landmarks | Distinctive scenery |
| --- | --- | --- |
| `cave_outer` | Cave Entrance, Vein Gallery | Rooted earth, side daylight, a limestone passage |
| `cave_grotto` | Reflecting Grotto, Upper Passage | Rear reflecting pool, fixed banks, animated seepage and ripples |
| `cave_hollow` | Splitstone Hollow, Keeper's Recess | Split columns, a natural arch and the distant raised overlook |
| `cave_depths` | Deep Passage, Deep Gallery | Dark recess, hanging formations, dense mineral seams |

The native floor tiles use a nearest-neighbor vertical projection for the
lower battle camera. Rear walls, formations, roots, debris, water and embedded
microcrystals reference retained asset manifests. Tiny crystal components keep
their native 1–4 × 1–5 pixel sizes. The action floor remains open for enemy and
party formations; actors, UI and combatant shadows are never baked in.

Each battlefield contains 24 frames at 250 ms per frame. The six-second crystal
breathing cycle changes local illumination as well as the native mineral
facets. The grotto's six water poses repeat over 1.5 seconds. Frame 8 is the
static reduced-motion view and also supplies `background.png`. Animated frames
are named `background_00.png` through `background_23.png`; `battlefield.json`
provides the runtime contract, source room references and exact provenance.

Rebuild with `python tools/build_cave_battlefields.py`; verify checked-in
exports with `python tools/build_cave_battlefields.py --check`. The builder
records hashes of its recipe, code, continuous-cave metadata, manifests and
every source image it consumes. It changes only the four battlefield folders.
