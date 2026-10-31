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

## Opening story route context

**Status:** Approved regional lore. The [Elden Vale overworld](OVERWORLD.md)
now implements the local landscape and ruined western crossing. The classroom
map remains unchanged. Aldric's [arrival cinematic](REGENT_ARRIVAL.md) and MQ03
dialogue now present the revised relief-visit story in the game.

Before Game I opens, an extraordinarily powerful lightning surge destroyed
the road from Eldenmere to the next town south, along the map's corresponding
southward connection. That town has no approved name: **River Leth** and
**Lower Leth** are geographic labels, not its name. The
[Regional Surges guide](narrative/game_01/REGIONAL_SURGES.md) records the
handful of other recent incidents, Aldric's relief visits and the resulting
repair shortages. The [Sanctuary Covenant](world/SANCTUARY_COVENANT.md)
explains how those needs bear on the proposed quarry near the old ridge
sanctuary.

This route context does not redraw the classroom map, add damage markers or
establish a new playable town. The existing viewer and artwork remain the
geographic reference described above; the regional story does not set new
distances or settle the unnamed town's precise location.
