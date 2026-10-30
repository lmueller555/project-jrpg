# Opening beacon sequence — prop and upper-sky sources

The original imagegen masters in this folder are retained unchanged:

- `upper_sky_generated.png`: a square cloud-and-star extension matching the
  original cinematic's night palette, without terrain or a painted magic effect.
- `lamp_stages_generated.png`: four isolated versions of the same brass travel
  lamp plus a separate wooden cup. Damage, frame straightening, glass fitting
  and the secured cap distinguish the repair stages. No flame or glow is baked
  into the lamp bodies.
- `sword_helmet_generated.png`: an upright sword embedded in a stone slab,
  supporting a battered, blood-stained steel helmet. It has no heraldry or
  identity marks and establishes no specific character's fate.

Run `python tools/build_beacon_props.py` to reproduce the runtime exports. The
exporter needs Pillow and NumPy. It separates alpha-connected atlas components,
removes only the faint generation matte, crops, nearest-resizes and registers
the authored images. It does not paint new props or modify their anatomy.
Source/export dimensions, hashes and extraction bounds are recorded in
`assets/story/opening_cinematic/beacon_props/provenance.json`.

All four lamps share an 18×30 canvas, centered floor registration and top-left
world position (615,345). Their runtime flame center is (624,363). The cup is
6×7 with anchor (3,7), placed at (648,357) on the bench. The foreground sword and
helmet share a 100×160 canvas, floor anchor (50,160), world position (395,430)
and helmet focus (395,295). The 960×960 upper sky starts at world (0,-640).

The ordinary sanctuary exporter now uses the original lamp-free architecture
master and composites only the bench. The lamp is supplied separately by the
cinematic's repair-stage renderer, so no intact duplicate remains behind it.
