# Liam's shared hearth animation audit

The live Liam fireplace used the shared Sanctuary dining HD fire bank. Its
masonry was fixed, but copying a rectangle from four independently fitted whole
fireplace drawings also animated the log bed and shifted the flame's support.
The tall tips and shifting logs made the fire appear to climb out of the hearth.

The corrected bank keeps the first drawing's complete structure and lower log
lip stationary. Connected source flames are uniformly fitted, bottom-center
registered to artwork `[48,114]`, and occluded by an inset firebox mask. Only
pixels inside that mask animate. Flame height is at most 20 artwork pixels,
leaving space below the lintel. The original 48×72 logical canvas, 2× density,
300 ms frames, 1.2 s loop, room positions, collision, sorting and source art
hashes are unchanged. Source and component registration are recorded in the
existing dining recipe and manifest. The inn's separate static hearth was
inspected and is not part of this animated family.

## Visual evidence

- [Before / after, all four live phases at 3× inspection scale](before_after.png).
- [All eleven live consumers, four phases at native asset scale](live_families.png).
- [Three consecutive 1.2 s loops through the World compositor](three_loops.gif).

The four source-derived flame poses stay on one visible coal/log support. The
mantel, chimney, side masonry, front lip and logs remain fixed. Review covers
Liam, Halden, Elira, Venn, homes A/B/C, Mira, mill, school and Sanctuary dining.
The dining light layers remain below the hearth at their existing depth.
Actual Caelan overlap captures confirmed fire is hidden with the hearth behind
an actor in front, rather than rendered as an always-on-top effect.

## Reproduce

```sh
python tools/build_sanctuary_dining_hd.py --hearth-only
python tools/capture_hearth_animation.py /tmp/hearth-review
python -m unittest tests.test_sanctuary_dining_hd tests.test_hearth_animation_runtime -v
python -m unittest tests.test_rendering -v
python -m unittest tests.test_eldenmere_interior_architecture -v
python -m unittest tests.test_eldenmere_hd_integration.TownHDContracts -v
python -m unittest tools.test_eldenmere_cottage_hearth -v
```

The capture uses a temporary journey/settings directory. It renders every live
phase in all eleven rooms, three loops in Liam's room, normal and reduced-motion
native 960×640 frames, and real Caelan front/behind diagnostic overlaps. The
reduced-motion checks apply the setting through a zero-time production update
and verify six widely separated elapsed times render the same complete hearth.
The focused runtime test covers phase boundaries, three loop seams, a large
elapsed time, reduced-motion toggling and actor depth. Asset tests verify exact
reproduction, hard alpha, mask containment, a common root and fixed log pixels.

Validation: 11 focused artwork/runtime tests and 16 renderer tests passed.
Legacy cottage-hearth tests passed (5), and town HD contract tests passed (9). The broader combined town/gameplay run
was killed by the environment after its asset contracts and early gameplay tests
passed; this is not claimed as a full-suite pass. The independent full interior module also exceeded the environment memory limit
during its sixth gameplay test after five passed. These interrupted aggregate
runs are not full passes; no check failed before either kill. The pre-existing dining
assertion expecting 36 repeated copies of a static ground path was corrected to
the compact single static frame already used by the live map; light timing
assertions remain intact, and the dining exporter now preserves that compact form.
