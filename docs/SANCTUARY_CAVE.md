# Sanctuary crystal cave

For nearby recovery, return to the Sanctuary hall and take the bed-marked
north-wing door to the visitor relief room. Attendant Nessa and the bed both
offer a free, confirmed short rest that restores travelling party HP/MP and
revives KO companions. There is no need to return to Eldenmere. See
[visitor care](SANCTUARY_RESERVE.md#visitor-relief-room).

The Sanctuary's first dungeon is one continuous scrolling cave, assembled from
the approved limestone dungeon asset pack. The player walks from the rooted,
daylit entrance through crystal-bearing galleries and reflecting water to the
broad Echo Chamber. Rooms, branches and return paths share the same world;
there are no internal scene transfers or passage interactions.

## Layout and travel

The direct route is **Cave Entrance → Vein Gallery → Splitstone Hollow →
Deep Gallery → Quiet Shelf → Echo Chamber**.

| Branch | Connection | Exploration reward |
| --- | --- | --- |
| Reflecting Grotto | Leaves Vein Gallery and rejoins the Upper Passage before Splitstone Hollow | A dropped pack and a chest across the reflecting pool |
| Keeper's Recess | Takes the lower damp route from Splitstone Hollow and rejoins Deep Passage | A keeper's chest and traces of maintained stonework |
| High shelf | A ramp-accessed spur overlooking Splitstone Hollow | A cache and a view over the junction |
| Quiet Shelf alcove | A short spur before the final chamber | The last cache and room to prepare |

The first Vein Gallery cache introduces the containers on the direct route.
Both longer detours reconnect, so exploration does not require retracing a
long dead end. A split pillar, natural arch, contrasting dry and wet routes,
wall contours and local lighting distinguish the junctions. The Echo Chamber
has a broad, clear floor framed by stone and embedded microcrystals.

Main passages allow at least three 24-pixel tiles of clearance. Shelves, ramps
and optional routes are authored for the full 24 × 12 pixel player footprint
and the following story party. Physical scenery sorts at its base.

Press **E** at the Sanctuary cave approach to lift the rail and enter. Inside,
walking crosses every room boundary. **E** opens containers, reads inspections
or returns through the entrance to the Sanctuary apron. **M** shows the whole
cave, its room landmarks, the exterior exit and the player's actual position.
Selection and mouse hover label rooms; select a room with the keyboard or mouse
to read its description.
Treasure and encounter staging data are not map markers.

## Persistent discoveries and journeys

The six existing discovery IDs and their inventory rewards are retained:

| Receipt | Placement |
| --- | --- |
| `cave_vein_cache` | Vein Gallery, on the direct route |
| `cave_grotto_pack` | Reflecting Grotto loop |
| `cave_grotto_chest` | Across the grotto pool, reached around its shore |
| `cave_keeper_chest` | Keeper's Recess |
| `cave_overlook_cache` | High shelf above Splitstone Hollow |
| `cave_quiet_cache` | Quiet Shelf alcove |

Opening a discovery grants its existing Aether material bundle through the
inventory foundation and changes the visible container state. Its independent
receipt prevents duplicate rewards after reopening, revisiting or continuing
a journey. Material uses and equipment customization remain future systems.

Journeys saved inside the continuous cave restore the same location and opened
containers. Older journeys from the three-section cave migrate to safe
landings in the corresponding part of the new map, preserving receipts,
inventory, party and quest progress.

## Assets and lighting

The live map is `assets/maps/sanctuary_cave/map.json`, authored by
`assets/source/maps/sanctuary_cave/recipe.json`. The builder composes the reusable
modules documented in [the dungeon asset pack](DUNGEON_ASSET_PACK.md): dry and
damp limestone, gravel, silt, rooted earth transitions, walls and overhangs,
ledges and ramps, fixed water banks, animated water, seepage, debris and
restrained keeper paving. Containers reuse the original cave's open and closed
sprites. Authored room polygons and navigation routes describe the full level.

Red, blue, green, white, orange and purple microcrystals follow the cave walls
in varied seams, corners and narrow fissures. Individual facets are mostly
2 × 3 native pixels and never exceed 4 × 5. They remain embedded scenery when
the player collects a container.

`SanctuaryCaveWorld` draws ordinary ground, scenery, party and foreground before
applying the colored light field. Sources follow a six-second breathing cycle;
the crystal frames and local illumination share that pulse. Ambient light
keeps the paths readable at the trough. Cached falloff is clipped at walls and
culled to the viewport. The HUD, dialogue and menus remain outside the lighting
pass. Reduced motion holds crystals and illumination at a readable static
state while preserving the same terrain and collision.

## Story and encounters

The cave is explorable while the MQ03 Sanctuary arrival remains pending.
Existing party ownership and Kindled Courage continue at that checkpoint.
Cave entry, treasure and the Echo Chamber inspection preserve that story state.

The cave now uses [distance-based random encounters](CAVE_RANDOM_ENCOUNTERS.md)
with Cave Bats, Lithrusks and Veylumes. A hidden 16–36-tile countdown, weighted
toward 26, selects one of 14 authored formations from the outer, middle or deep
pool. Battles contain at most four enemies; groups of three or four are rarer.
The six original encounter spaces remain layout references. Random selection
uses the player's actual location throughout the continuous cave.

The entrance apron, High Overlook, Quiet Shelf and Echo Chamber are protected.
The Echo Chamber reserves the future level-seven miniboss,
[Vespermaw](BESTIARY.md#vespermaw). Its Bestiary entry records the solo story
encounter design, stats, elements, rewards and complete action cycle. Art,
party-wide Roar damage, Pounce response rules, recovery vulnerability and the
actual encounter trigger remain pending. It is excluded from random pools.
The Quiet Shelf provides
a preparation pause without restoring HP or MP. Battle entry focuses the party,
presents a loading screen and reveals one of four animated cave battlefields.
Victory/flee return to the same cave position and reset the distance budget.

The arrival cutscene, miniboss implementation, further combat tuning and
post-boss resolution remain later work. The cave does not establish the
confluence's detailed workings, identify the original sacrificial temple or
merge this location with the historically sealed workers' passage.

## Reproduction and retained reviews

```sh
python tools/build_continuous_sanctuary_cave.py
python tools/build_continuous_sanctuary_cave.py --check
```

The retained [original cave review](reviews/sanctuary_cave/README.md) documents
the earlier three-section implementation. Its images and walkthrough are
historical evidence, not a preview of the current layout. The
[limestone chamber](LIMESTONE_CAVE_REVIEW.md) and
[expanded pack review](reviews/dungeon_pack/README.md) show the approved reusable
materials. No new walkthrough was generated for the continuous level; review
the merged dungeon in-game.
