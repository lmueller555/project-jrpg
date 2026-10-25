# Liam's new family home — review pending

A new wide cottage now stands in **western Eldenmere, immediately south of the
sanctuary**, with a front path connecting it to the main village lane.

- [Updated town layout — house highlighted](town_layout.png)
- [Sanctuary and surrounding neighborhood](neighborhood.png)
- [In-game exterior — chimney smoke and lantern loop](exterior.gif)
- [Furnished 16×10 interior](interior.png)

The exterior and interior captures come from the actual `main.py` renderer,
using the real map and furniture. Caelan is shown for scale. The exterior loop
has 18 phases at 200 ms each, at 2× nearest-neighbor enlargement. The full town
layout is native scale with an added review marker; the neighborhood is 2×.

The house is assigned to Liam, his mother, his father and Daisy. It reuses the
approved wide cottage kit in terracotta, with a shared parents' bed, Liam's
separate bed, four dining seats, kitchen, washbasin, storage and animated hearth.
The existing wide-room partition and lighting remain intact. There is clear
floor space for Daisy and a separate entrance to this household's room.

Doors use the game's existing proximity animation and walk-in transfer, and
exiting returns to this same new house. Map labels, navigation routes and
collision include the new building and path. The eastern Venn family cottage
retains its identity and room. Existing residents and routines are preserved.

The family characters have not been spawned yet; this change establishes their
home before their NPC placement and action routines. It is on the review branch
and has not been merged into `main`.

```sh
python tools/build_liam_family_home.py
python tools/capture_liam_house.py
python -m unittest discover -s tests -v
```

Checks cover the new placement, path, household assignment, furniture access,
animated exterior and door registration. Existing door tests also walk into and
out of the new home, open/hold/close its door and verify access to every piece of
furniture. The full suite checks all prior town routes and NPC routines.

Validation: **22 town/door/home tests pass**. The full suite passed 156 of 157
checks; the existing Serene full-schedule check can fail when random Tomas
timing blocks the dining-room doorway. Runs with seeds 0–3 produced identical
results on unchanged `main` (`e86be03`) and this branch, including the seed-2
failure. No scheduling code was changed. See [recorded validation](validation.json).
The local rebuild also reproduced all 149 checked runtime/source files byte
for byte, and all 98 prior interior files remain unchanged.
