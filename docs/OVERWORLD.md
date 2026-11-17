# Elden Vale overworld

**Scope:** Current regional travel, streaming, controller ownership and reproduction.
[Elden Vale — Regional Design Guidance](world/regions/ELDEN_VALE.md) is the single
creative authority for the region. The HD terrain/scenery foundation is now
integrated, with six area records and nonblocking reservations for later work.
The Pale Antlers and Sanctuary presentation are integrated. Causeway structures,
Rising Rain and final atlas artwork remain deferred.

Construction follows the [visual](VISUAL_ART_STANDARD.md) and
[terrain](TERRAIN_ART_STANDARD.md) standards. The regional overworld is a separate
presentation scale from the detailed village, reserve and interiors. Historical
[initial region](reviews/elden_vale_overworld/README.md),
[environment quality](reviews/elden_vale_polish/README.md) and
[place-composition](reviews/elden_vale_composition/README.md) captures record earlier
implementation milestones. They remain evidence, not future art direction.

## Integrated HD foundation

`region.json` selects `assets/maps/overworld/elden_vale/hd_integration/manifest.json`
through `hd_art_manifest`, after the base, detail, composition and Sanctuary art
records. `tools/build_elden_vale_hd_integration.py` builds this live adapted
registry from the immutable staged foundation and shared HD packs. The original
`assets/terrain/overworld/elden_vale/hd/art.json` retains its staged
`not_integrated` metadata; it is not the runtime selector.

Selected grass, dirt, paving, field materials, water and ordinary scenery use
native 2× artwork at their existing regional logical sizes. Nineteen vegetation
aliases use one union crop, scale and registration across each donor's idle,
frames and fixed layers; original canvases and foot anchors remain unchanged.
Scenery breeze and water follow the exploration clock, with stable reduced-motion
frames. Characters, wildlife and work props retain their existing controllers.
The Sanctuary miniature remains separately owned pending landmark integration;
its detailed reserve continues to use its existing native bank.

The six `design_layout.areas` records describe home meadows, southern farms,
western bridge road, central causeway, northern woodland and Sanctuary ridge.
The causeway reservation follows the existing stone road through `[10,-1]`,
`[7,4]`, `[-3,8]`, `[-15,11]` and `[-28,14]`. Additional clearing/clearance metadata
protects this route without placing ruins or changing its travel connections.
The antlers' overhead envelope is nonblocking; candidate bases reference existing
solid outcrops. Viewpoint reservations do not clear a town-to-ridge forest corridor
or turn walkable hillside into new solid ground. Detailed Sanctuary support
coordinates remain separate from regional tiles.

See the [actual-game foundation review](reviews/elden_vale_hd_integration/README.md)
for current captures and verification scope. Signature landscape, Rising Rain
activation and final atlas updates remain subsequent integration work.

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

**Elden Vale Sanctuary** stands northeast of Eldenmere, on a wooded rocky
shoulder inside the northern wall and west of the eastern river. A maintained
footpath branches from the eastern foothill loop, passes between rock shelves
and reaches its forecourt on an open dirt approach. There are no stair props on
the overworld approach. The miniature combines a pale stone hall, slate roof,
small bellcote and side cloister, with a grove and boundary markers around it.
The landmark appears on the regional atlas and minimap from the start: Caelan
already knows this local place. It is separate from **Serene's home**, the
household within Eldenmere where Caelan and Tomas live.

Walking onto the miniature now enters the [detailed sanctuary reserve](SANCTUARY_RESERVE.md)
at its southern woodland approach. The reserve contains the court and cloister,
memorial grove, cave approach and surveyed stone face, with an enterable hall.
The southern exit returns to the overworld outside the miniature's contact
area. The [continuous cave and rescue](SANCTUARY_CAVE.md) are implemented.
Eldenmere's existing automatic entry and return remain independent. The
[current in-game review](reviews/sanctuary_reserve_hd/README.md) shows this visit;
the [original miniature review](reviews/overworld_sanctuary/README.md) records
the earlier stage before entry was enabled.

The main road takes approximately 47 seconds to walk from the town miniature's
exit to the near-bank bridge approach. Local paths lead toward woodland, a
supply staging area, the two checkpoints and an eastern overlook. Ordinary
movement remains 72 pixels/second, or 108 while running. This regional scale
does not establish kilometres, a global travel speed or the final world's size.

Follow Eldenmere's southern road through the inn/item-shop lane to the town's
southern edge to leave automatically. The road continues to the expanded map
boundary; its `overworld_exit` contact and return position are authored in the
town recipe and exported with the map, alongside `destinations.southern_exit`.
The pre-expansion exit inside the business district no longer transfers scenes.
The player appears just south of the miniature. Approach the miniature from any
side to return on the southern road below the businesses, facing north. A short
cooldown and contact rearming prevent immediate return loops. The existing direct village ↔
Upper Millrace route and MQ02 cutscene remain available. The regional millrace
landmark is a locator, not another quest entrance.

Press **M**, or click the overworld minimap, to inspect the
[illustrated regional atlas](REGIONAL_MAP.md). Its default view frames the
inhabited vale, both rivers, the ruined crossing and the checkpoints. Scroll or
use +/- to zoom, drag to pan, click a known place or its name for details, or use
arrows/WASD to select landmarks. **Fit** or **F** restores the local overview;
zooming farther out shows the wider authored chart. **M**, **Esc** or the close
button returns to play.
The town map and classroom world-map viewer retain their existing behavior.
Major geography is charted immediately; optional local landmarks are added
after Caelan approaches them. Discovery persists with the saved journey.
The regional map and journal pause movement and regional time. The existing
Eldenmere Theme continues across the scale change.

A north-up minimap follows Caelan at the bottom right during ordinary regional
exploration. It shares the atlas's geography and live passage states, while a
directional player marker provides local orientation. It yields to dialogue
and interface screens. The exploration Menu button is removed in every area;
Escape continues to open pause.

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
authored, ready onward destination. Neither destination is currently authored.
There is deliberately no producer for the release flag yet: completing MQ04,
the last currently implemented quest, does not finish the opening chapter.
The future festival/departure sequence must grant release explicitly.

Bridge repair is a separate durable fact,
`ELDEN_VALE_WEST_BRIDGE_REPAIRED`. Restoring the mill, helping Iselin, or opening
a checkpoint does not repair the bridge. No current quest grants this flag.
The engine can reconstruct the repaired crossing from the fact for later work;
the current layout shows the destroyed state experienced during the opening.

The intact land checkpoints reserve a route for Iselin's relief caravan, which
must not arrive across the ruined bridge. The [arrival cinematic](REGENT_ARRIVAL.md)
uses the southern land checkpoint and preserves the broken crossing and the
player's travel restrictions. The Sanctuary's ridge site does not open those
checkpoints, repair the bridge, add an encounter or place the original temple.
The southern town remains unnamed and its onward destination is future work.
The cave, Sanctuary arrival, rescue and MQ03 return resolution are implemented;
they do not grant regional release or bridge repair.

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

`regional_terrain_hd.py` composes native material detail through the existing
logical road/river masks. Texture phases use signed global tile coordinates,
including negative coordinates, and crop-row angles retain their authored
directions. Material contact shading does not expand route widths. Natural bank
detail is clipped outside the exact water footprint, and the repaired bridge deck
stays dry. The helper has separate byte-bounded asset and mask caches; it does not
retain enlarged region-wide textures or an unbounded frame stack.

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
- Live adapted HD bindings and vegetation exports:
  `assets/maps/overworld/elden_vale/hd_integration/manifest.json`.
- HD registration recipe, source hashes and layout reservation reference:
  `assets/source/maps/overworld/elden_vale/hd_integration/`.

The `detail_art_manifest` extends the base art at runtime. Existing art and
the original review images remain unchanged. The layout recipe adds typed crop
parcels, road hierarchy, authored setpieces and decorative placements. Existing
world, landmark, town-contact and progression identifiers stay stable.
The optional `composition_art_manifest` supplies the wider bridge and related
composition modules while preserving the base and first-pass art files.
`hd_art_manifest` overlays the selected native bindings last; `terrain_hd.enabled`
opts the region into native phase-aware material composition. Neither field
changes collision, quest ownership or the regional coordinate space.

The layout builder pins the approved classroom atlas by SHA-256, retains
normalized reference anchors, and exports its survey annotation separately.
It neither redraws nor modifies that atlas. Boundary placement and travel
distances are authored gameplay interpretations of its geography.

```sh
python tools/build_overworld_art.py --check
python tools/build_overworld_polish_art.py --check
python tools/build_overworld_composition_art.py --check
python tools/build_elden_vale_hd_integration.py --check
python tools/build_elden_vale_overworld.py --check
python tools/build_cartography_art.py --check
python tools/build_elden_vale_cartography.py --check
python -m unittest discover -s tests -p 'test_overworld_*.py' -v
python tools/capture_elden_vale_atlas.py
python tools/capture_elden_vale_hd_integration.py /tmp/elden-vale-hd-review
```

The layout check validates wall–river joins, default enclosure reachability,
bridge independence and the walking-time target. Runtime tests additionally
exercise actor footprints, seams, cache eviction, map coordinate transforms,
travel locks, legacy/region Continue and quest companion ownership.

## Western grain farm

The western farmstead now has two region-owned workers: a loader in rust and a
careful coworker in slate. `grain_farm.py` owns their small courtyard routes,
work poses, three individually accounted sacks and optional conversation.
Before `CH01_MQ02_MILL_RESTORED`, the loader inspects and covers waiting grain;
the coworker walks around the parked cart to check its lashings. The actual
intake-repair flag starts two finite loading trips. Quest completion alone does
not start loading, and the workers do not claim Caelan repaired the mill.

After loading, the loader considers the third sack. Press E near a worker once
the coworker has returned to the resting spot to hear their axle disagreement.
Passing through does not start dialogue. Afterwards they lower the spare sack
together, and the loader checks the lashings. Quiet checking and resting replace
further loading. Each worker also has a short greeting and state-aware prose.
Walking away cancels an unfinished conversation. Workers wait for blocked
routes; they never relocate the player or teleport to bypass an obstruction.

The optional `overworld.grain_farm` save record stores the number of completed
placements, whether the exchange was read, whether the physical payoff finished,
and completed greetings. The outer save version stays 1. Continue reconstructs
unfinished work at a safe storage boundary: an unplaced sack returns to storage,
while placed sacks stay on the cart. A read exchange is not repeated if Continue
occurs during the assisted placement. The final scene beat commits after the
loader checks the lashings. Leaving and returning retains the live controller;
chunk eviction does not own or duplicate workers. The controller sleeps beyond
260 pixels from the farm and uses the same map/journal pause as the region.

The [NPC animation pass](REGION_NPCS.md) gives the workers authored full-body
work and directional carrying sequences. Sacks remain at their source through
grabs and in hand through placement or shared lowering, then snap when the
animation completes. Directional holding attachments support normal carrying
and rear-facing body occlusion. Blocked
carrying uses a steady hold. Four-direction guard poses and a matching armored
portrait also make checkpoint conversations consistent with the visible actors.

The cart remains parked. Original decorative grain sacks remain reserve scenery;
the three small handled sacks are the finite delivery batch. This adds no town
NPC ownership, companion representation, quest reward, bridge repair, gate
release, or delivery destination. Work-pose provenance and the repeatable builder
live in `assets/source/characters/grain_workers/README.md`.

[Current NPC videos and review notes](reviews/region_npcs/README.md) show both
mill states, the whole exchange and payoff, blocked-path recovery, Continue and
the guard conversations. The [original farm review](reviews/grain_farm/README.md)
remains as the earlier implementation record.

```sh
python tools/build_grain_workers.py
python tools/build_grain_workers.py --check
python -m unittest discover -s tests -p 'test_grain_farm.py' -v
python tools/capture_grain_farm.py
python tools/capture_region_npcs.py
```

## Near-bank bridge crew

`bridge_crew.py` owns two regional workers north of the ruined western approach:
a moss-shirted mason and a slate-shirted surveyor. Three loose stones are
inspected and moved into a two-piece reusable stack and a separate rejected
piece. Afterwards the mason brushes down, checks the barrier and looks toward
the damage; the surveyor measures along the work area. The batch never grows.
All stations are on existing connected dry ground, outside the main road.
The broken bridge, water, checkpoints and main quest facts are unchanged.

Once sorting finishes, E near the resting mason starts an optional tea visit.
The surveyor returns to the visible kettle, picks up the cup and walks around
the steady tray. E continues the two short exchanges, allowing the player to
leave rather than imposing modal dialogue. The unstable stone makes the
surveyor move the cup to the tray, then guide it into the mason's reaching
hand. The mason sits with the drink while the surveyor briefly takes over the
tool. The cup is handed back and carried to the kettle. Subsequent interactions
use quiet work greetings. This creates no quest or reward.

The optional `overworld.bridge_crew` record stores `sorted` (0–3), `tea_beat`
(0–5), `request_read`, greeted roles and optional `cup_phase` ownership. The first dialogue commits its read
fact immediately; Continue during the wobble resumes the physical action
without replaying that dialogue. Older crew records remain valid. Completed sorting, cup placement, cup handoff, read
exchange and completed break are checkpointed. Continue restores an interrupted
carry to its last safe station, preserving completed cup transfers; read final dialogue never repeats. A break
interrupted after the exchange resumes its physical payoff. Existing saves
without the block remain valid. Leaving retains the live controller, while
map, journal, title, pause and town transitions suspend it. Chunk eviction
never owns actors or props. The controller sleeps beyond 260 pixels.

The cup has one rendered location at every stage. Grabs, set-downs and handoffs
snap only after the complete action animation; stones use the same rule.
Rear-facing held objects sort behind the body. Actor probes and a reserved
handoff area prevent overlap; the sequence begins only when that reservation
is clear. Workers wait for blocked routes rather than teleporting or moving
the player. The [NPC animation pass](REGION_NPCS.md) gives both workers authored
directional work and carrying frames, registered hand contacts and supported
seated drinking/recovery. Source art and reproducible export provenance are
recorded in `assets/source/characters/bridge_workers/README.md`.

[Actual-game videos and fixture details](reviews/bridge_crew/README.md).

```sh
python tools/build_bridge_workers.py
python tools/build_bridge_workers.py --check
python -m unittest discover -s tests -p 'test_bridge_crew.py' -v
python tools/capture_bridge_crew.py
```

## Garden and orchard workers

The [garden/orchard work guide](GARDEN_ORCHARD.md) documents the southern kitchen
gardener's finite watering and harvest, the village orchard picker's fruit
sorting and rest, and an optional act of care for a struggling plant. Both
workers belong to the region. Their objects, interrupted actions and first-read
conversation persist independently of streamed scenery. Physical contacts use
the shared distance-limited regional audio controller.

## Checkpoint familiarity and optional participation

`checkpoint_charm.py` owns the finite northern guards' seat-sharing vignette;
`regional_participation.py` owns optional overlook sitting, greeting the resting
farm cat and inspecting the bridge crew's unfinished work. These live controllers
replace the completed regional charm planning document. They remain implementation
references beneath the single regional creative design authority.

The guards retain their duty stations and gate clearance. The complete exchange
plays once, with durable read/contact checkpoints and quieter repeats. The other
contacts add no named cast, tasks or rewards. Existing orchard, sheep-care,
workers, props and regional companions keep their own owners.

Hint and E target selection agree. Busy/repeated input cannot restart work or
consume another target. Sitting offers stand/cancel with a collision-safe return.
Interruption and Continue preserve ownership and contact state without duplicating
actors, props or sounds. Cosmetic clocks stay outside progress dirtiness;
meaningful contacts use the shared positional audio/lifecycle rules.

The guards' production scene is replayed as **Keeping Your Seat** in Gallery;
routine participation stays outside it. See [the gameplay review](reviews/checkpoint_charm/README.md)
and [Gallery coverage](GALLERY.md) for current evidence. Gate release, bridge
repair and quest progression remain independent.

## Signature landmark framework and cross-scale placement plan

Step 2 PR 1 supplies explicit `distant`, `ground` and `overhead` landmark passes
in `landmark_layers.py`. Production landmark registries remain empty. The
[disposable initialized-Game review](reviews/elden_vale_landmark_framework/README.md)
records renderer evidence, not activated scenery or approval of a final landscape.
The regional creative authority and protected travel contracts above remain
unchanged. Rising Rain, local actions and final atlas artwork remain deferred.

Landmark positions are top-left **logical world units**, with explicit logical
size and artwork density. The staged `assets` schema must be adapted to explicit
runtime records, not merged into a `props` registry. The three passes sit behind
nearby entities, below actors, and above actors respectively. Overhead local
cutaways follow actual/story actor positions and authored interaction positions.
Source LRUs and viewport-sized temporary work remain separate from cached ground.
Full visible bounds, not ordinary scenery-root lookup, determine visibility.
Scenery metadata never supplies collision or save fields.

### Selected detailed presentation direction for PR 2

The original support study remains evidence, not a final placement. At its
full-scale master origin `[592,-230]`, the 784×528-logical master extends beyond
the reserve on the north/east. The old `[864,456]` viewpoint's ordinary camera
starts at y296 and crops almost all of the skull. Rendering the complete skull
in the ground pass also lets the northern-loop actor appear to stand on bone.
Do not activate that arrangement unchanged or move collision to accommodate it.

The selected direction is a **dedicated build-time 0.625 coherent rendition**:
project the complete 1568×1056 artwork master once to **980×660 artwork pixels**,
then register a **490×330 logical** assembly at `[726,-41]`. Segment at native
x `[0,330,650,980]` and y474, giving even-pixel part dimensions and exact master
reconstruction. The change from ideal fractional split y475 changes only layer
ownership of one native row, not anatomy. Preserve orientation and all registered
relationships; do not independently fit/mirror parts or stretch to the regional
envelope. No runtime downsampled image cache is necessary.

The registered contact becomes `[948.5,274,45,12.5]`, entirely within the original
solid `[948,274,72,20]` study. The ordinary protected northern-loop viewpoint
`[960,168]`, camera `[672,8]`, provides the near anatomical reveal without changing
camera coverage. The cave apron `[1008,406]` remains usable and intentionally
screens most of the base behind existing cave scenery. The old southern skull
view is not promoted to a reveal. All beams remain nonblocking.

PR 2 must finish the contact/depth registration, not merely copy this rectangle:

- Trim only peripheral rubble/root contact fringe against the existing solid
  ridge union, retaining bone anatomy. In the untrimmed projection, a lowest-
  contour audit finds 122 native columns over walkable mask, at x895–1139.5 and
  y273–284.5. This audit is diagnostic, not a replacement for visible support review.
- Split raised skull/root presentation from the actual grounded contact wherever
  the eastern circuit overlaps it. A body-center audit finds 27 sampled loop
  positions near `[1100,267]`–`[1100,295]` over the ground-pass skull image. Raised
  portions need local cutaway/depth treatment; no extra collision is allowed.
- Add the essential limestone, earth, root and moss dressing with the same
  contact/depth checks. Retain the memorial grove, crystals, hall/relief doors,
  cloister, survey station, care/arrival staging and keeper-rail/cave apron.
- Re-run the complete circuit in both directions, companions, story arrival/care,
  rail operation, Save/Continue and normal/reduced-motion visibility after the
  final rendition and grounding are built. No probe shrinkage, teleports,
  relocated stations, new story flags or new crossing is part of this plan.

### Regional and town bindings for PR 2

The regional `[44,-86,64,43]` reservation is in **24-unit regional tiles**, not
reserve coordinates or a target canvas size. Keep the existing
`sanctuary_ledge_5` at `[96.5,-72]` and `sanctuary_upper_outcrop` at `[93.8,-74]`
as the original support candidates, not mandatory final anchors. Actual-game
ordinary-camera review rejected their northern registration because the drawing
was wholly above the approach view. The integrated coherent regional master is
registered at `[2143,-1771]` logical against existing `sanctuary_ledge_3` instead: its
contact `[2317.37,-1519,35.27,10]` fits the unchanged `[2303,-1519,64,10]` solid
footprint. No collision or road changed. Use a coherent rendition at a declared scale, never fill the
1536×1032-logical reservation by stretching the 384×264 regional drawing. Inspect
views at regional tiles `[42,-45]`, `[69,-55]` and `[90,-62]` with full-bounds
culling. Ridge/cave contact and the 96×80 Sanctuary miniature keep their existing
entry/forecourt contracts, independent of artwork alpha.

Town uses a fixed world-space `distant` anchor, with no new parallax or cleared
corridor. The disposable hall/spawn fixture anchors the 192×132 distant drawing
at `[264,132]` behind the existing roof and trees, demonstrating tip-only roof
screening; it is not a universal anchor for every town view. The integrated town anchor is `[350,50]`; ordinary reachable northern roof gaps
reveal its branches while the household roof screens the base.
Distant views omit the skull/base; changing cameras must not drag the silhouette
with the player or place it in front of roofs. Rooted landscape registration is
owned by the recipe/builders, not ad-hoc capture code.

### Internal causeway and arch plan for PR 3

Use the existing `south_town_road` alignment, in regional tiles:
`[[10,-1],[7,4],[-3,8],[-15,11],[-28,14]]`. The road is 2.5 tiles / 60 logical
units wide, within a 4-tile / 96-unit future clearance reservation. Register
module ports/overlapping joints deliberately along that curved route; paving and
decks stay below actors, near parapets use deliberate depth, and lintels remain
overhead. Do not imply pits, climbing or unsupported elevation mechanics.

The N/S-dominant `[10,-1]` to `[7,4]` leg is the first arch candidate, away from
the `[7,4]` junction to the southern land checkpoint. The E/W remainder is not a
natural crossing direction for the unrotated horizontal arch opening. Inspect
final supports against the reserved corridor rather than assuming an authored
94-unit aperture automatically preserves a 96-unit clearance reservation. Reject
or move the arch if supports crowd that corridor or the junction. Keep the
existing 24×12 probe and 22-unit passive-party spacing. Sweep both directions,
running and diagonal corners with `Game.update`; a centered walk alone is not
clearance proof. Flat reused paving stays traversable; physical fragments and
supports require visible, matching footprints outside protected travel/work
areas. This road remains inside the walls and creates no river, gate, broken-
bridge or cave bypass. Gate release and bridge repair remain independent facts.


## Integrated Pale Antlers and Sanctuary presentation

`signature_landscape` in the regional recipe owns the registered master origin,
existing support IDs, anatomical protection polygon, embedding edge, per-instance
ridge bindings and explicit placements. The vector builder copies placements;
the HD integration builder adapts staged `assets` into separate runtime `landmarks`
and `props` records. Regional split images reconstruct the same orientation; only
terrestrial contact fringe embeds into existing solid ridge. Raised skull and
branches use local cutaways. The new Sanctuary miniature remains96×80 logical
with foot anchor48,78 at the existing landmark position; its canvas creates no
collision or transfer trigger. Existing entry, forecourt, arrival and return
contracts remain authoritative.

Eldenmere's town recipe owns one fixed skull-free distant anchor, screened by
existing northern roofs and trees. Its ordinary camera reveals selected branch
tips, not an independent second anatomy or a general parallax system. The reserve
builder owns the dedicated0.625 native rendition, grounded dressing and protected
circuit; see [reserve runtime](SANCTUARY_RESERVE.md).

[Production gameplay review](reviews/elden_vale_pale_antlers/README.md) records
actual coverage, timings and limits. The source pack retains staged metadata and
historical offline studies. Rising Rain, causeway activation and final regional
atlas/minimap artwork are not part of this step.

The town skyline's authored viewing area starts south of logical y158, with a
22-unit viewpoint fade margin. Northern-lawn approaches suppress it, preventing
a distant branch from reading as a small walk-through prop. The intended roof
vista at `[600,180]` is fully visible; its fixed `[350,50]` anchor never moves.
