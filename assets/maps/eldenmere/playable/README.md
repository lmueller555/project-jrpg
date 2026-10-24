# Eldenmere — playable outdoor map

Run `python main.py` from the repository root. This package turns the approved 64×56 layout (24px tiles, 1536×1344 native pixels) into runtime data, with the finished sanctuary/charm and workshop exteriors in their approved positions. Caelan and Mira are drawn dynamically by the game, never baked into these images. Quests remain unimplemented.

- `map.json`: spawn, dimensions, ground clocks, depth-sorted entities, collision path, bridge foreground layers, landmarks and approved navigation destinations.
- `ground/`: six actor-free, building-free ground phases at 200 ms, retaining paths, masonry, brook/channels, spillways, jammed gate and bridge decks/wakes.
- `entities/`: native building and prop frames, deduplicated within each entity. Cottages/smoke/lanterns, the mill, sanctuary and workshop retain their existing animation phases; foliage uses 600 ms frames.
- `foreground/`: southern bridge rails, drawn over crossing actors.
- `collision.png`: the approved final exterior's solid geometry, used by the live 24×12 player probe. Roads are not the only walkable surfaces: unblocked grass is explorable too.
- `overview.png`: actor-free in-game town map.

The player starts at `[384,312]` in the sanctuary courtyard. These coordinates are the **centre of the ground collision probe**. Drawing uses the existing town registration `[12,30]` within Caelan's 24×36 frame; the artwork's bottom-foot anchor remains `[12,34]`. This distinction preserves the approved stair/bridge/doorway clearance measurements and sprite placement.

Ground baselines sort roofs, tree canopies and props against the player; bridge foreground rails draw afterward. Player movement is normalized diagonally, subdivided into at most one-pixel steps and resolved per axis to stop tunnelling and allow sliding along walls. The camera clamps to the map boundary. North/south routes remain town boundaries until adjoining maps are implemented.

`map.json` now includes nine proximity doors and an interior scene registry. Door panels are drawn with their host buildings, so ambient animations and depth sorting continue while doors open. A 30px proximity starts opening; a 38px release radius prevents boundary flicker. Five 100ms poses play forward/reverse without looping or restarting when direction changes. Walking north into the fully open threshold transfers to the corresponding furnished interior; returning through its cutaway south exit places Caelan safely outside the same door. Detailed room/door data are in [building_interiors](../building_interiors/README.md).

The `npcs` registry contains two actors. Mira's [outdoor bench routine](../../../characters/mira/work_bench/README.md) is approved by the user. Its variable-duration poses and bench fitting share the global game clock, so returning from a room does not create another Mira or restart her work. Her 8×4 foot blocker leaves both approved yard approach points and the doorway usable.

The [sanctuary gardener](../../../characters/npcs/female_02/gardener/README.md) uses a persistent moving routine and a 12×8 foot probe. Task waypoints and flower-root targets live in `../routines/gardener.json`. She follows the terrace stairs and the lower part of the workshop lane, fills at dry-bank position `[786,408]`, and waters the four approved courtyard patches. Safe movement is checked against the existing mask, other NPCs and Caelan. Occupied stations cause waiting; sustained obstructions can trigger a local detour. Task state and bucket contents continue across room visits. This routine is awaiting design review. The approved static collision mask and all source scenery remain unchanged.

To rebuild in the asset environment:

```sh
python -m pip install -r tools/requirements-assets.txt
python tools/build_playable_eldenmere.py
```

The compiler reads approved layout/art and their assembly helpers without invoking asset exports or changing the source packs. It also calls `tools/build_building_interiors.py` to compile room/door data. There are no placeholder sanctuary/workshop buildings and no scale-review characters in the runtime map. Gameplay, door round trips and planned route connectivity are checked with `python -m unittest discover -s tests -v`.
