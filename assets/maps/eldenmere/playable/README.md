# Eldenmere — playable outdoor map

Run `python main.py` from the repository root. This package turns the approved 64×56 layout (24px tiles, 1536×1344 native pixels) into runtime data, with the finished sanctuary/charm and workshop exteriors in their approved positions. There are no NPCs or quests in this export. Caelan is drawn dynamically by the game, never baked into these images.

- `map.json`: spawn, dimensions, ground clocks, depth-sorted entities, collision path, bridge foreground layers, landmarks and approved navigation destinations.
- `ground/`: six actor-free, building-free ground phases at 200 ms, retaining paths, masonry, brook/channels, spillways, jammed gate and bridge decks/wakes.
- `entities/`: native building and prop frames, deduplicated within each entity. Cottages/smoke/lanterns, the mill, sanctuary and workshop retain their existing animation phases; foliage uses 600 ms frames.
- `foreground/`: southern bridge rails, drawn over crossing actors.
- `collision.png`: the approved final exterior's solid geometry, used by the live 24×12 player probe. Roads are not the only walkable surfaces: unblocked grass is explorable too.
- `overview.png`: actor-free in-game town map.

The player starts at `[384,312]` in the sanctuary courtyard. These coordinates are the **centre of the ground collision probe**. Drawing uses the existing town registration `[12,30]` within Caelan's 24×36 frame; the artwork's bottom-foot anchor remains `[12,34]`. This distinction preserves the approved stair/bridge/doorway clearance measurements and sprite placement.

Ground baselines sort roofs, tree canopies and props against the player; bridge foreground rails draw afterward. Player movement is normalized diagonally, subdivided into at most one-pixel steps and resolved per axis to stop tunnelling and allow sliding along walls. The camera clamps to the map boundary. North/south routes remain town boundaries until adjoining maps are implemented. Doors remain closed in this outdoor milestone.

To rebuild in the asset environment:

```sh
python -m pip install -r tools/requirements-assets.txt
python tools/build_playable_eldenmere.py
```

The compiler reads approved layout/art and their assembly helpers without invoking asset exports or changing the source packs. There are no placeholder sanctuary/workshop buildings and no scale-review characters in the runtime map. Gameplay and planned route connectivity are checked with `python -m unittest discover -s tests -v`.
