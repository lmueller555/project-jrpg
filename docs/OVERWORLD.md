# Elden Vale overworld

Eldenmere's southern road now opens into the first playable region of Auratia.
This is a separate regional scale: the detailed village retains its existing
layout, while the overworld represents it with a small, recognizable town.
The [review captures](reviews/elden_vale_overworld/README.md) show the actual
renderer and the [atlas survey](reviews/elden_vale_overworld/atlas_reference.png)
shows how the region follows the approved world map.

The [environment quality pass](reviews/elden_vale_polish/README.md) adds three
composed farmsteads, smaller crop parcels, village orchards, clustered woodland,
rocky slopes, riverbank planting and inhabited checkpoints. The main stone road,
farm cart tracks and woodland footpaths have distinct widths and materials;
their junctions and bends follow the places they serve. The original regional
captures remain available as a historical comparison.

The [place-composition pass](reviews/elden_vale_composition/README.md) connects
farm doors, loading spaces, crop gates and property boundaries into compact
working places. Orchard aisles arrive at a harvest/resting nook, relief stores
sit beside their approach, and guards occupy duty stations close to the gates.
Grouped canopies, connected rock shelves and selected shoreline conditions
give woodland, foothills and riverbanks more coherent local forms.

## Geography and travel

Elden Vale is an inland, temperate corridor on the western side of Merovar's
Greyfold foothills. Woodland occupies the north, cultivated ground opens south,
and rocky, wooded hills rise east. Two winding, unnamed rivers form the western
and eastern boundaries. They remain distinct from the village brook and the
controlled millrace. No sea, desert or new river name is introduced.

Stone walls join the riverbanks to the north and south. Each wall has a guarded
opening. Both checkpoints are closed during the opening quests. The western
road bridge lies **inside** the walls, so Caelan can inspect its lightning-damaged
approach without passing a checkpoint. Broken masonry, scorched ground and
damaged road on both banks convey the recent surge. The far-bank road continues
toward the unnamed town south of Eldenmere; its actual destination scene is
future work. There is no bridge over the eastern river.

The ruined stone bridge has a three-tile roadway: 72 pixels north–south between
its parapets. The artwork retains its east–west span and an empty collapsed
center. Its approaches and the independently repaired future deck use the
same width; increasing the bridge's visible roadway does not grant repair or
open the crossing. The review includes a measured native-width audit.

The main road takes approximately 47 seconds to walk from the town miniature's
exit to the near-bank bridge approach. Local paths lead toward woodland, a
supply staging area, the two checkpoints and an eastern overlook. Ordinary
movement remains 72 pixels/second, or 108 while running. This regional scale
does not establish kilometres, a global travel speed or the final world's size.

Walk down Eldenmere's existing southern road to leave automatically. The player
appears just south of the miniature. Approach the miniature from any side to
return to the village's southern entrance, facing north. A short cooldown and
contact rearming prevent immediate return loops. The existing direct village ↔
Upper Millrace route and MQ02 cutscene remain available. The regional millrace
landmark is a locator, not another quest entrance.

Press **M** to inspect the regional map. Scroll or use +/- to zoom, drag to pan,
click a landmark for details, or use arrows/WASD to select landmarks. **Fit** or
**F** restores the overview; **M**, **Esc** or the close button returns to play.
The town map and classroom world-map viewer retain their existing behavior.
Major geography is charted immediately; optional local landmarks are added
after Caelan approaches them. Discovery persists with the saved journey.
The regional map and journal pause movement and regional time. The existing
Eldenmere Theme continues across the scale change.

The countryside uses grain, vegetable, fallow, pasture and orchard ground,
with parcel-specific row directions. Farmhouses, barns, sheds, fences and gates
form compact regional scenery. Flowers, laundry, resting places, relief carts
and packed lantern supplies give routes local character. Small wildlife and
smoke animations are placed in selected scenes. These additions do not create
new interiors or quests. The regional map reflects crop and road differences;
farmstead glyphs are scenery rather than new selectable destinations.

## Boundaries and story facts

Checkpoint collision belongs to the gate geometry, independently of the guard
sprites. Passing a gate requires both `CH01_OPENING_REGION_RELEASED` and an
authored, ready onward destination. Neither destination is ready in this PR.
There is deliberately no producer for the release flag yet: completing MQ04,
the last currently implemented quest, does not finish the opening chapter.
The future festival/departure sequence must grant release explicitly.

Bridge repair is a separate durable fact,
`ELDEN_VALE_WEST_BRIDGE_REPAIRED`. Restoring the mill, helping Aldric, or opening
a checkpoint does not repair the bridge. No current quest grants this flag.
The engine can reconstruct the repaired crossing from the fact for later work;
this PR implements the destroyed state experienced during the opening.

The intact land checkpoints reserve a route for Aldric's relief caravan, which
must not arrive across the ruined bridge. Its arrival cutscene and MQ03 dialogue
rewrite remain separate story work. No new quest, random encounter, original
temple location, named southern town or old ridge sanctuary marker is added.

## Streaming and coordinates

`overworld_world.py` supplies one persistent `auratia.overworld` world identity.
Global coordinates are signed pixels; the authored manifest uses signed tiles.
Tiles are 24×24 pixels and chunks contain 16×16 tiles (384×384 pixels).
The first authored envelope is `[-256, -192, 512, 384]` tiles, or 12,288×9,216
pixels. Additional regions can extend that coordinate space without changing
the meaning of existing positions.

The runtime never builds a region-sized ground image, animation stack,
collision mask or overview. Small vector features generate terrain only for
requested chunks. Shared native art is loaded once; a weighted LRU limits
rendered chunks to 64 MiB. Collision and decoration metadata each retain at
most 64 chunks. A one-chunk-per-frame lookahead prepares nearby terrain.
Deterministic decoration and global depth sorting prevent load-order changes
and keep canopies continuous across seams. Missing sparse chunks and positions
outside authored bounds block movement. Full player-foot probes query every
chunk they touch, including negative-coordinate seams.

`overworld_environment.py` supplies the detailed environment layer. Authored
setpieces group globally positioned props with optional solid foot rectangles.
Prop ownership, collision indexing and deterministic tree clusters work across
chunk boundaries. Roads and reserved scene approaches keep their clearances;
tree silhouettes, undergrowth and ground-edge variation break up regular grids.
Material patterns use global coordinates, including rotated crop textures, so
eviction or a change in load order does not shift the scenery. Regional ground
and props continue to share small source assets and the existing cache budgets.

The region stays outside `Game.scenes`: streaming a terrain section does not
create an additional town scene, tick a remote household or duplicate an NPC.
Camera clamping uses the region's actual origin. Sight queries use a world
collision interface instead of requiring a monolithic mask.

## Saves and companions

`overworld_travel.py` owns scale changes. Transfers first resolve a safe landing,
then move the leader, reset the camera/map, and checkpoint the journey. Existing
village/interior saves load without a migration. New saves add a versioned
`overworld` block containing the region identity and discovered landmark IDs;
the outer journey format remains version 1. Continue restores global position,
facing and discovery. Gate and bridge state come from durable dialogue flags,
never from cached surfaces.

Quest companions travel virtually at regional scale. Their detailed-scene
instances, placement owners and quest progress are retained while physical
town following and household ticks are suspended. On returning, the same
accompanying instances are placed safely near Caelan. Continue stages quest
restoration at town scale before restoring the regional leader, preventing a
town actor from being placed at regional coordinates. Exploring does not accept
or complete a quest, replay a reward, or add a regional edge to NPC path graphs.

## Sources and reproducibility

- Layout source: `assets/source/maps/overworld/elden_vale/recipe.json`.
- Runtime geometry: `assets/maps/overworld/elden_vale/region.json`.
- Original generated art, prompts and crop recipes:
  `assets/source/terrain/overworld/elden_vale/`.
- Native tiles/props and anchors:
  `assets/terrain/overworld/elden_vale/art.json`.
- Detailed environment art and its export manifest:
  `assets/terrain/overworld/elden_vale/polish/art.json`.
- Original detail generations, prompts and export recipes:
  `assets/source/terrain/overworld/elden_vale/polish/`.
- Wider-bridge composition art and export manifest:
  `assets/terrain/overworld/elden_vale/composition/art.json`.
- Original composition generations and measured export recipe:
  `assets/source/terrain/overworld/elden_vale/composition/`.

The `detail_art_manifest` extends the base art at runtime. Existing art and
the original review images remain unchanged. The layout recipe adds typed crop
parcels, road hierarchy, authored setpieces and decorative placements. Existing
world, landmark, town-contact and progression identifiers stay stable.
The optional `composition_art_manifest` supplies the wider bridge and related
composition modules while preserving the base and first-pass art files.

The layout builder pins the approved classroom atlas by SHA-256, retains
normalized reference anchors, and exports its survey annotation separately.
It neither redraws nor modifies that atlas. Boundary placement and travel
distances are authored gameplay interpretations of its geography.

```sh
python tools/build_overworld_art.py --check
python tools/build_overworld_polish_art.py --check
python tools/build_overworld_composition_art.py --check
python tools/build_elden_vale_overworld.py --check
python -m unittest discover -s tests -p 'test_overworld_*.py' -v
python tools/capture_elden_vale_composition.py
```

The layout check validates wall–river joins, default enclosure reachability,
bridge independence and the walking-time target. Runtime tests additionally
exercise actor footprints, seams, cache eviction, map coordinate transforms,
travel locks, legacy/region Continue and quest companion ownership.
