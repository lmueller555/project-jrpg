# Mira: worn arm-rig continuity sources

`exploration_authored.png` contains 36 authored drawings in a 6×6 atlas: four
standing directions, four walking frames per direction, and sixteen workshop
studies. `cinematic_authored.png` contains 32 authored drawings in an 8×4 atlas:
eight raised directions, eight lowered directions, eight cuff-adjustment poses
and eight brace-lift/test poses. Both original image-generation outputs are
retained here without repainting.

The robotics are external equipment over Mira's intact anatomical left arm.
Her hand remains visible and usable. The engineering kit retains her brown
ponytail, flower, work clothes, gloves and boots.

Run `python tools/build_mira_rig_continuity.py` to isolate connected alpha,
register feet, and export using nearest-neighbor sampling at a fixed scale for
each atlas. `registration.json` records source hashes, source cells and anchors.
The wider 32×36 exploration canvas prevents the cuff and tools being clipped;
world positions, collision probes, walk cadence and the eight-second workshop
cycle are unchanged. Cinematic canvas, timing, headings and endpoint filenames
are retained, with the shot emitter registered to the cuff instead of a held gun.
