# Venn held water magick repair

[In-game close-up](repair.gif) · [Slow motion](repair-slow.gif).

Caelan raises an open hand and pulls existing water upstream. The crescent stays
held as his other hand straightens the pin and lifts the gate. Lowering the
casting hand releases the flow, which visibly carries the twigs downstream.
The effect uses the existing channel and water palette, without creating water.

The old generic casting frames and ripple renderer have been replaced. The
new poses have separate casting-arm, working-arm, head and body source layers.
The moving hand and gate pin are registered together through the lift. Water
is composited through a mask that preserves the gate's wood, stone and iron.

Rebuild art: `python tools/build_venn_magicks.py` (Pillow).
Capture: `python tools/capture_venn_magicks.py` (Pygame and Pillow).
The capture seeds the quest delivery and inspections, then runs the real game
repair. It shows an enlarged nearest-neighbor crop of the runtime world renderer;
phase labels are review annotations. Decoded GIF frames are checked on export.

Tests: `python -m unittest discover -s tests -p 'test_venn*.py' -v`.
