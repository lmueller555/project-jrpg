# Eldenmere — watermill source and assembly

Status: draft artwork for visual review.

`materials_concept.png` retains the generated companion reference: an isolated building without a wheel, an isolated eight-paddle wheel, a working undershot mill and a stopped-supply study. The approved bridge close-up supplied pixel/material guidance. `recipe.json` retains the native sizes, source crops, backdrop extraction rule, roof/glass ramps, wheel angle increment, placement, elevations and review framing.

## Design and physical layout

The mill is a compact timber-framed building over a stone foundation, with cream wall panels, a muted slate roof, a front-left door and front-right wheel axle. A level 48×24 timber landing carries doorway access over the narrow race. The first complete overlay is 144×168, the building material sample 120×144 and the wheel 48×48; all are used alongside unchanged 24×36 characters and 24×24 terrain.

The race leaves the brook at `(17,4)`, travels east to column 28, descends on the map to row 11, turns west below the wheel and rejoins the brook at `(17,11)`. The grade falls continuously 18 → 17 → 16 while all banks/floor/landing remain at 24. Water reaches the bottom paddles from the east. Clockwise rotation moves those paddles west; the left side rises, carrying the authored droplets. A wheel axle at 40 and radius 24 put its lowest tips at 16, one below the supplied race surface. Water never climbs a terrace or passes over the wheel's top.

The blocked-supply alternative interrupts the race at `(24,4)`. It retains the supplied upstream segment and renders the downstream channel dry, holding the intact wheel at phase zero and omitting effects. This is a review asset option rather than a revision to the story's unresolved obstruction details. The older terrace example remains unchanged as requested.

## Retained source and native processing

`parts/building_native.png` samples the building reference with nearest-neighbor scaling. Border-connected backdrop pixels are removed by comparing their distance to the sampled corner colors and exact material ramps; enclosed plaster and window regions remain. Retained pixels use only named colors and hard alpha. `parts/wheel_material.png` and `paddle.png` retain source wood/grain samples for the separately assembled wheel.

Wheel geometry has eight repeated spokes/paddles, a timber rim, iron fasteners and a round hub. Each phase uses explicit native-pixel geometry at a 7.5° increment without interpolated rotation or partial alpha. The fixed building composites behind it; separate splash/drop/ripple layers occupy only the lower wheel and receiving-water area. Eight-fold symmetry supports a six-phase 45° repeat at 200 ms, implying a 9.6-second full revolution.

Race pieces reuse approved irrigation frames. A reversed-current return mouth uses the same east-facing bank opening with westward motion; all other ports retain the approved cardinal convention. The exported scene records a complete reachable path and a non-increasing surface elevation at every cell. Existing native brook bank pixels are overlaid only at the two new mouths; original source assets are never rewritten.

The running and stopped scene builders read the six approved bridge native frames, extend grass eastward, restore the generic gray-haired NPC's former ground cells, add the race and a dirt service approach, then draw the mill and unchanged NPC at the landing. All earlier pixels outside the race mouths/corridor and restored NPC cells remain identical. Direct enlarged running, stopped and comparison GIFs provide review delivery.

Build with `python tools/build_eldenmere_watermill.py`; test with `python tools/test_eldenmere_watermill.py`. Checks cover native palettes/alpha, exact structure/wheel/effect composition, stationary roof/walls, observed paddle positions and westward currents, water contact/clearance, directed race reachability and grade, blocked-state behavior, dry building footprint and landing, native scene reconstruction, localized changes and exact enlarged GIF pixels/timing. Recipe approval state survives rebuilds.
