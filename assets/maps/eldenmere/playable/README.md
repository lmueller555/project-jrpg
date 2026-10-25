# Eldenmere — playable outdoor map

Run `python main.py` from the repository root. This package turns the approved 64×56 layout (24px tiles, 1536×1344 native pixels) into runtime data, with the finished sanctuary/charm and workshop exteriors in their approved positions. Caelan and Mira are drawn dynamically by the game, never baked into these images. Quests remain unimplemented.

- `map.json`: spawn, dimensions, ground clocks, depth-sorted entities, collision path, bridge foreground layers, landmarks and approved navigation destinations.
- `ground/`: six actor-free, building-free ground phases at 200 ms, retaining paths, masonry, brook/channels, spillways, jammed gate and bridge decks/wakes.
- `entities/`: native building and prop frames, deduplicated within each entity. Cottages/smoke/lanterns, the mill, sanctuary and workshop retain their existing animation phases; foliage uses 600 ms frames.
- `foreground/`: southern bridge rails, drawn over crossing actors.
- `collision.png`: the approved final exterior's solid geometry plus the well's 48×48 footprint, used by the live 24×12 player probe. Roads are not the only walkable surfaces: unblocked grass is explorable too.
- `overview.png`: actor-free in-game town map.

The player starts at `[384,312]` in the sanctuary courtyard. These coordinates are the **centre of the ground collision probe**. Drawing uses the existing town registration `[12,30]` within Caelan's 24×36 frame; the artwork's bottom-foot anchor remains `[12,34]`. This distinction preserves the approved stair/bridge/doorway clearance measurements and sprite placement.

Ground baselines sort roofs, tree canopies and props against the player; bridge foreground rails draw afterward. Player movement is normalized diagonally, subdivided into at most one-pixel steps and resolved per axis to stop tunnelling and allow sliding along walls. The camera clamps to the map boundary. North/south routes remain town boundaries until adjoining maps are implemented.

`map.json` now includes nine proximity doors and an interior scene registry. Door panels are drawn with their host buildings, so ambient animations and depth sorting continue while doors open. A 30px proximity starts opening; a 38px release radius prevents boundary flicker. Five 100ms poses play forward/reverse without looping or restarting when direction changes. Walking north into the fully open threshold transfers to the corresponding furnished interior; returning through its cutaway south exit places Caelan safely outside the same door. Detailed room/door data are in [building_interiors](../building_interiors/README.md).

The `npcs` registry contains two actors. Mira's [outdoor bench routine](../../../characters/mira/work_bench/README.md) is approved by the user. Its variable-duration poses and bench fitting share the global game clock, so returning from a room does not create another Mira or restart her work. Her 8×4 foot blocker leaves both approved yard approach points and the doorway usable.

The [sanctuary gardener](../../../characters/npcs/female_02/gardener/README.md) uses a persistent moving routine and a 12×8 foot probe. Task waypoints, flower-root targets and rest bounds live in `../routines/gardener.json`. She follows the terrace stairs and the lower part of the workshop lane, fills at dry-bank position `[786,408]`, and waters the four approved courtyard patches plus both raised window troughs. She reaches the troughs via the gap east of the bench and turns between them from `[316,294]`, leaving the doorway clear. Each trip is followed by a uniformly random 180–300-second rest, sampled once on entering rest; the initial rest uses the same bounds. Safe movement is checked against the existing mask, other NPCs and Caelan. Occupied stations cause waiting; sustained obstructions can trigger a local detour. Task state, bucket contents and the rest countdown continue across room visits. This routine is approved by the user.

The separate `persistent_npcs` registry contains Mother Serene. Her data-driven schedule in `../routines/serene.json` uses the approved four-direction sprite pack, four new planted work loops and the same collision-aware pathfinder. One actor instance moves between the sanctuary dining room and hall; room visits never duplicate her or reset the schedule. Her action stations and 12×8 foot probe keep the breakfast area, central aisles and all doorway approaches open. These routines await user review.

The [well square overlay](../well_square/README.md), approved by the user, adds a 10×8-tile commons clearing, reused stone paving and a southern path connection. The well is one additional animated depth-sorted entity. Only its 2×2-tile ground footprint becomes solid; its roof can overhang walkable ground. `navigation_allowed` points to the extended route mask; `destinations` includes its four approaches and southern connector. All original destinations and building positions remain intact. The original approved foundation stays recorded in `original_layout_source`.

To rebuild in the asset environment:

```sh
python -m pip install -r tools/requirements-assets.txt
python tools/build_eldenmere_well.py
python tools/build_playable_eldenmere.py
```

The compiler reads approved layout/art and their assembly helpers without invoking asset exports or changing the source packs. It also calls `tools/build_building_interiors.py` to compile room/door data. There are no placeholder sanctuary/workshop buildings and no scale-review characters in the runtime map. Gameplay, door round trips and planned route connectivity are checked with `python -m unittest discover -s tests -v`.

## Liam's family cottage — approved

A new wide cottage south of the sanctuary is assigned to Liam, his parents and
Daisy. It has a connecting path, animated proximity door, map label and separate
16×10 furnished room. See the [house source and build instructions](../liam_house/README.md)
and [review captures](../../../../docs/reviews/liam_family_home/README.md).
Liam's parents remain stationary and silent. Daisy rests on her woven
rug, wanders around the room, and visits her food and water bowls. The room is
preloaded as an ambient scene; her routine also advances while offscreen.

Liam and Daisy's shared play routine (approved) transfers both actors
through their cottage door for three running laps on clear lower ground in
front of the house, then returns them to their bed/rug resting spots. No town
terrain or building positions are changed. See the
[routine review](../../../../docs/reviews/liam_daisy_play/README.md).

## Village school — awaiting review

An enterable schoolhouse now stands northeast of the well square on the lower
western bank, with a shaded forecourt and a path into the square. Its separate
16×12 classroom seats six children. Liam's mother is recorded as its teacher;
attendance and teaching routines will follow the building review. See the
[school placement and build instructions](../school/README.md) and
[exterior, classroom and door previews](../../../../docs/reviews/eldenmere_school/README.md).

## Generic villager households — awaiting review

Three parent pairs now belong to home_a, home_b and home_c. Five adults are
placed inside those cottages; the existing gardener remains outdoors and is
assigned to home_a with the olive-shirted father. See the
[registry and build instructions](../households/README.md). Names, children and
additional schedules remain for a later stage.
