# Auratia classroom world map

The school displays the approved 2026-11-25 map of Auratia: elongated western
Merovar, far-southern Elden Vale, far-northern Adamanthra and the central
east–west river. Serevin, Othara and polar Istrava remain separate continents.
Its geographic reference is the [World Atlas](narrative/world/WORLD_ATLAS.md#approved-world-map)
and the [polar regions guide](narrative/world/POLAR_REGIONS.md).

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
The source [approval record](../assets/source/world/auratia/approval.json)
pins the detailed map and the derived prop's geography. The exporter verifies
both before writing and supports read-only `--check` verification.

```sh
python tools/build_auratia_world_map.py
python tools/build_auratia_world_map.py --check
python tools/build_eldenmere_school.py --map-only
python tools/capture_school_world_map.py --output-dir docs/reviews/merovar_world_map/school
python -m unittest discover -s tests -p 'test_*world_map*.py' -v
```

The [current review](reviews/merovar_world_map/README.md) shows the actual
classroom, fitted viewer and zoomed southern Elden Vale. The
[original review](reviews/school_world_map/README.md) remains historical evidence
of the prior artwork. Use explicit output directories for fresh captures so
the historical files are preserved.

## Opening story route context

**Status:** Approved geography, with the intact bridge implemented and the
replacement opening's story scenes still future work. The
[Chapter 1 chronology](narrative/game_01/CHAPTER_01.md) owns the approved
2026-11-26 Fire Veinhold opening. The flashforward, Festival of Light and
quarry/excavation Act I are retired. Their prologue, arrival and invasion
replacements remain unimplemented.

The western bridge is intact during Caelan and Mira's introduction, before
Iselin and Lucan arrive. It is destroyed in the later Fire Veinhold attack;
the former pre-opening lightning cause is obsolete. The
[current overworld](OVERWORLD.md) now begins with a playable intact bridge and
a bounded west-bank road ending in a layby. This adds no onward destination
or new town location. Historical arrival/MQ03 captures record the older story;
their scene runtime is removed. Earlier local coordinates and surveys remain
historical references rather than current bridge-state specifications.

The southern road's neighbouring town still has no approved name.
**River Leth** and
**Lower Leth** belong to central Merovar, north of the Vale's separate southern
watershed; they do not identify that nearby town or its road. The
[Sanctuary Covenant](narrative/world/SANCTUARY_COVENANT.md) retains background
custodial terms, with no required quarry storyline. The natural confluence
remains established; the Sanctuary and cave's new plot roles remain open.

The world-map revision adds no playable onward town or central-river crossing.
Distances, exact tributary junctions, political boundaries and the unnamed
town's precise location remain open. The Fire Veinhold's exact map location,
the identity of its weapon relative to the later cannon, any cave bypass,
bridge repair and the onward route also remain open. The local brook,
millrace, two bounding
rivers, Sanctuary approach and story gates retain their existing gameplay
contracts; see the [regional guide](OVERWORLD.md). Those land gates must be
accounted for before the bridge's loss can be said to isolate the village.
