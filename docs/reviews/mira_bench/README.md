# Mira's outdoor bench routine — review

Status: awaiting user review.

- [6× looping close-up](bench_closeup.gif)
- [3× workshop scene](workshop_scene.gif)
- [Still close-up](bench_closeup.png)
- [Still workshop scene](workshop_scene.png)

These are captures of the real runtime renderer: Mira inspects, makes three wrench strokes, lowers the tool, wiggles the fitting and rests. She remains at the bench. The footage uses exact native pixels and the actual eight-second routine timing; captions are review annotations. Existing smoke, sign and scenery continue animating, so their longer cycles may restart at this excerpt's loop boundary.

Run `python main.py` and walk east from the sanctuary toward the workshop to see her in-game. `python tools/capture_mira_bench.py` reproduces the previews. Tests cover pose timing, planted feet, tool contact, fitting synchronization, depth order, collision, route clearance and persistence across shop entry/exit, alongside the existing town and door checks.
