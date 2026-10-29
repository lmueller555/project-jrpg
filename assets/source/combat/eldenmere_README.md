# Eldenmere battle scenery sources

These original PNGs were generated with the image generation tool for the Bat
encounter on the green west of Eldenmere's well. They are the authored artwork;
the exporter does not draw or procedurally replace any scenery.

- `eldenmere_background_generated.png`: complete opaque 1536×1024 panorama.
  References were the actual playable Eldenmere overview, the existing roofed
  well structure, and the terracotta cottage structure. The composition places
  cottage fronts and trees behind a clear, trampled grass fighting lane, with
  the well to the right and detailed grass, flowers, clover and stones at the
  outer foreground edges. The brook, mill and festival props are omitted.
- `eldenmere_grass_generated.png`: isolated transparent grass-and-clover sprig,
  generated using the panorama as its palette reference. This is a separate
  foreground accent for restrained breeze animation.

Run `python tools/build_eldenmere_battlefield.py` from the repository root to
rebuild `assets/combat/eldenmere/`. It exports the full panorama at 480×320 with
nearest-neighbour sampling, and trims the grass using an alpha threshold of 128
before nearest-neighbour export at 24×12. Source hashes and dimensions are stored
in `assets/combat/eldenmere/scene.json`.

The bottom battle panel covers the lower scene at runtime; the visible clearing
and corner vegetation have been composed above its normal y=204 top edge. No
actors, combat interface or text are baked into the environment artwork.
