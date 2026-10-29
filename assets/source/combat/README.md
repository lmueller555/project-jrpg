# Combat sprite sources

The two PNG sheets were authored with image generation for this game's first
ATB encounter. Caelan references the approved `idle_left.png`, `idle_front.png`
and enlarged front reference in `assets/characters/caelan/`; the Bat is an
original design. Both source sheets contain sixteen poses in a four-by-four
grid. The corrected Bat sheet leaves transparent gutters around every wing.

Run `python tools/build_combat_assets.py` from the repository root to reproduce
the native exports in `assets/combat/caelan/` and `assets/combat/bat/`. The
exporter only extracts cells, scales with nearest-neighbor sampling, registers
the ground/flight anchors and converts alpha to binary pixel coverage. It does
not paint, redraw or synthesize poses. Creative changes require editing or
regenerating the source artwork first.

Each actor's `animation.json` records the source SHA-256, native 48×48 canvas,
24×42 ground anchor, frame files, source cells, duration and loop behavior.
Caelan's two defeat poses naturally kneel and bow; the Bat's defeat sequence
descends from flight to a folded pose on the ground. The runtime loads native
frames and does not need Pillow or this authoring tool.
