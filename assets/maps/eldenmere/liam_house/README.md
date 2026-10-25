# Liam's family cottage — approved

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
The house is playable by running `main.py`. Liam, his mother, his father and
Daisy live inside. Both parents are stationary and silent. Daisy rests
on her woven rug, wanders, eats and drinks; she has no dialogue.
`house.json` now also records the four resident sprites, positions, foot probes
and rug registration; rebuilding preserves this placement.
See the [household review](../../../../docs/reviews/liam_household/README.md).

## Daisy's food and water bowls

Two matching wooden bowls sit side by side to the right of the rug. Both start
full. `bowls` records in `house.json` select each initial state, position and
caregiver approach. Full, half-full and empty sprites share fixed rims, drawing
registration and footprints. The room's entity `state_images` maps are retained
for state changes. Daisy consumes one fill level per visit; refill routines
remain future work. See
the [bowl pack](../../../terrain/eldenmere/liam_home/bowls/README.md) and
[in-game captures](../../../../docs/reviews/daisy_bowls/README.md).

## Daisy's indoor routine — approved

`../routines/daisy.json` defines her calm walking speed, wander points, rug rest,
food/water cooldowns and separate bowl approach/clear points. The town's
`ambient_scenes` preloads this room so Daisy progresses while it is offscreen.
The cached room preserves her position, cooldowns and bowl states on re-entry.
Bowl reservations prevent future caregivers changing a bowl during a visit.
See the [complete routine previews](../../../../docs/reviews/daisy_house_routines/README.md).

## Shared play routine — approved

`play_routine` references `../routines/liam_daisy_play.json`. Liam is a
`play_actor` while his parents remain stationary. The game coordinates Liam and
Daisy through an invitation, excited hops/wag, individual door transfers, three
front-yard running laps, and a return-home nap. Daisy has a 50% chance of
visiting her water bowl first. Existing meals finish before the invitation.
The controller temporarily owns Daisy and restores her normal behavior after
the nap; both actors retain their identity across scenes. See the
[complete review](../../../../docs/reviews/liam_daisy_play/README.md).

## Wooden-block play — approved

`block_routine` references `../routines/liam_blocks.json`. An open wooden toy box
fits against the west wall in the gap between the two beds. Its six fill states
represent zero through five blocks. The box has a small fixed foot blocker;
player access is [90,212], distinct from Liam's closer [80,200] handoff position.

Liam removes five identified blocks and builds a two-support bridge, admires it,
then returns the pieces individually. A single 50% cleanup roll leaves one piece
on the floor; the next session collects that same piece before starting again.
Floor pieces are decorative and cannot block paths. No extra toys are spawned.

When Daisy first comes within two tiles after at least three pieces are placed,
one 10% roll can select a curious visit. She remains free to move until Liam has
finished all five pieces, and finishes a bowl visit before being borrowed. Her
nose touches the beam before the four-stage collapse. Liam reacts with ambient
speech, sends her to her rug, then tidies up. She rests 45–90 seconds afterward.

This activity and the outdoor chase share Liam's ownership. Both continue in the
cached room offscreen; neither can start while the other owns Liam. The initial
block-play delay is 90–150 seconds and repeat cooldown 3–5 minutes. See the
[review clips](../../../../docs/reviews/liam_blocks/README.md).
