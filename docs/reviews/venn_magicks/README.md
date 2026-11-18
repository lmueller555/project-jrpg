# Venn failed magick attempt and tools fallback

[In-game scene preview](repair.gif) · [Slow motion](repair-slow.gif).

Caelan attempts to push the water back with magicks. A tiny blue-white palm spark
gathers, flickers and dies. The three-second cast leaves the water level, gate,
pin and debris unchanged. His head and lower body retain their normal idle
registration; the bent forearm moves without stretching his arms or legs.

After lowering his hand, Caelan says, "I can't move it. I'll need the tools."
Acknowledging the line starts the practical repair. He uses a mallet to set the
pin and a hook to clear the debris and lift the gate, standing on the dry bank.
Only that repair restores the flow. The sequence establishes a trace of magical
ability without enough strength to move the water yet.

The capture seeds the quest delivery and inspections, then runs the actual game
through the failed attempt, failure dialogue and complete tools fallback. It
shows an enlarged nearest-neighbor crop of the runtime renderer. Phase labels
are review annotations. The normal and slow GIFs contain the same rendered
frames; decoded frames and duration are checked on export.

The cast atlas has body, casting-arm and energy source layers, plus the unchanged
native idle reference. The builder checks head and lower-body preservation and
exact idle poses at the start and finish. The held-water and magick gate-opening
assets from the superseded successful-spell sequence are removed.

Rebuild cast art: `python tools/build_venn_magicks.py` (Pillow).
Rebuild tool poses and gate art: `python tools/build_venn_visit.py` (Pillow).
Capture: `python tools/capture_venn_magicks.py` (Pygame and Pillow).
Tests: `python -m unittest discover -s tests -p 'test_venn*.py' -v`.

The saved failure milestone prevents replaying the spell after leaving or
reloading. Existing repaired saves remain repaired. The Venn objective still
requires the family's closing conversation after the tools repair.
