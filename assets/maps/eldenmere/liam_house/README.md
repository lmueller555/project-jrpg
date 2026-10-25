# Liam's family cottage — review pending

The new **wide terracotta-roofed cottage** is on lower ground immediately south
of the sanctuary, west of the village's main lane. Its ground footprint is
5×3 terrain tiles, matching the eastern wide cottage. The house is assigned
to **Liam, his mother, his father and Daisy**, separately from the Venn family.
Parent names, surname and quest association remain unassigned.

`house.json` is the placement and household source: native sprite origin
`[204,384]`, ground blocker `[216,456,120,72]`, two-tile-deep front path, and the
wide interior source. Existing terrace walls, stairs and water routes remain
unchanged. The new path joins the existing lane on the same elevation.

The 18 exterior phases reuse the approved wide terracotta kit's chimney smoke,
lantern and closed door. Five matching door patches support the existing
proximity open/hold/close behavior and walk-in scene transfer. The exterior is
registered as `liam_house`, with its own map landmark and approach destination.

The separate **16×10 floor** uses the approved wide shell, partition, windows,
lighting, kitchen and hearth. It adds Liam's bed below the shared parents' bed
and a fourth chair north of the dining table. Furniture access and the entry
remain walkable; a clear floor point is reserved for Daisy. The runtime scene
is `../building_interiors/rooms/liam_house/map.json`. Household membership is
also linked from `assets/characters/liam_family/family.json`.

```sh
python tools/build_liam_family_home.py
python tools/capture_liam_house.py
python -m unittest discover -s tests -v
```

The local builder updates only this town addition and its own room. Rebuilding
base doors/interiors through `tools/build_building_interiors.py` reapplies this
extension automatically, including when called by the full town compiler.
`interior_layout.json` records added furniture registration. New ground, allowed
routes, collision and map overview are checked into the runtime assets.

See the [marked town layout, in-game exterior loop and interior](../../../../docs/reviews/liam_family_home/README.md).
The house is playable by running `main.py` from this branch. Family NPC placement,
dialogue and routines are the next stage; no new residents are spawned here yet.
