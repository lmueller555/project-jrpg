# Eldenmere — well and commons square

Status: **approved by the user**.

A roofed fieldstone well sits just north of the commons' through path. Slate-colored shingles, brown timber posts, a hand crank, winding spindle, rope and a suspended wooden bucket match the village materials. Six 200ms phases add small water glints inside the shaft; the roof, stone, windlass, rope and bucket stay fixed. Character scale remains 24×36 on 24px terrain.

- `structure.png`: transparent 84×96 registered sprite.
- `frames/`: six native ambient phases.
- `well.json`: position `[486,792]`, 48×48 ground blocker `[504,840,48,48]`, draw baseline 888, water clock and east drawing approach `[564,864]`.
- `well_review.png`: enlarged opaque native-art reference.
- [Town layout and runtime previews](../../../../docs/reviews/eldenmere_well/README.md).

The rounded 10×8-tile square uses the existing 47-tile dirt transitions, with an apron assembled from the approved sanctuary flagstones. A two-tile-wide connector joins the southern road/bridge approach. North, south, east and west approaches remain open; the western gathering area is reserved for future conversations and festival activity. Existing buildings and watercourses keep their positions.

The well is installed in the actual `main.py` world with collision, depth sorting, animation and an updated in-game map. It is an ambient world asset at this milestone; drawing water and retargeting the gardener are separate interactions. The gardener's approved brook routine continues unchanged.

Source concept, native structure, water mask and recipe are retained in `assets/source/terrain/eldenmere/well/`. Run `python tools/build_eldenmere_well.py` to export art, `python tools/build_playable_eldenmere.py` to compile the square, and `python tools/capture_eldenmere_well.py` for review captures, using the asset environment. The game requires only Pygame and the checked-in exports.
