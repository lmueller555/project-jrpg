# Auratia classroom world map

The school displays the approved map of Auratia, including the Nivren Crown
and Istrava. Its geographic reference is the [World Atlas](world/WORLD_ATLAS.md)
and the [polar regions guide](world/POLAR_REGIONS.md).

Enter the village school and approach the small framed map on the north wall,
left of the writing board. The prompt **E — Examine Auratia’s world map** appears
beside its reachable floor approach. Press **E** to inspect it.

The viewer opens with the whole map fitted to the screen. Scroll to zoom around
the pointer and drag with the left mouse button to explore. **Fit** restores
the overview; **Esc**, **E**, or **Close** returns to the classroom. It renders
the original image directly at display resolution, preserving detail when
zoomed. The player, NPCs, doors, and quest clocks pause during inspection;
the location's music continues.

The furnishing retains its existing `village_map` ID, position `[96, 28]`,
and 42×40 native sprite footprint. Its interaction position is `[108, 94]`,
matching the room's existing walkable map destination. The wall map adds no
floor collision or quest requirement. Existing saves need no migration.

Assets live in [`assets/world/auratia`](../assets/world/auratia/README.md).
`world_map.png` is the approved 1448×1086 artwork; `wall_map.png` is the native
classroom prop. The school builders preserve both the prop and its authored
interaction record through later rebuilds.

```sh
python tools/build_auratia_world_map.py
python tools/build_eldenmere_school.py
python tools/capture_school_world_map.py
python -m unittest discover -s tests -p 'test_*world_map*.py' -v
```

The [review captures](reviews/school_world_map/README.md) show the actual
classroom, fitted viewer, and zoomed detail.
