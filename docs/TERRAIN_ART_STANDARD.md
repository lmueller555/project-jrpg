# Terrain art and pack creation standard

This is the single maintained reference for terrain creation and pack maintenance:
ground materials, transitions, vegetation, rocks, water, banks, elevation, stairs,
environmental accents, exports, integration and review. It replaces the former
grass guides and the grass/dirt, stream, irrigation, terrace, foliage, flower and reed pack
READMEs. Existing recipes and manifests retain machine-readable implementation
facts; historical review reports record earlier work rather than prescribe new
construction methods.

The [World and Environment Design Standard](WORLD_DESIGN_STANDARD.md) owns
creative place-design principles and the region/zone brief, including identity,
weather/phenomena, inhabited history, folklore and exploration. Use it to plan
the place; this document owns terrain authoring, pack maintenance and integration.

The [global visual standard](VISUAL_ART_STANDARD.md) owns project-wide appearance,
units and rendering. This document applies those rules to the complete terrain
workflow. Building art follows the global standard; terrain and buildings share
scale, perspective, lighting and compatible contact edges. For manipulable objects,
also follow the [interaction standard](OBJECT_INTERACTION_STANDARD.md) and
[personal-prop visibility](PERSONAL_PROPS.md).

**Status:** Eldenmere's outdoor town, southern business lane and upstream scene
now use the rebuilt grass/dirt, paving, maintained masonry/stairs, temperate
water/shores, channels/spillways and vegetation at 2× artwork density. Original
world coordinates and the entire original collision/navigation rectangle are
preserved. The town expands south from 1536×1344 to 1536×1632 logical units.

The live consumer registry is `assets/maps/eldenmere/town_hd/manifest.json`.
Standalone pack manifests below retain their original staged-delivery metadata;
that metadata does not replace the live map's explicit integration registry.
Unused variants and other regions remain separate migrations. Existing shared
legacy banks are still required by regional scenes and historical source tools.

Elden Vale's regional foundation now has its own
[integrated HD bindings](#integrated-elden-vale-regional-foundation), using the
shared materials and adapted scenery at the existing miniature logical scale.
Pale Antlers and Sanctuary views now use explicit landmark integration. Causeway
structures and inhabited ruins now have separate live bindings; Rising Rain
remains inactive.

Eldenmere's building/interior integration and the new inn/shop follow the
[global visual standard](VISUAL_ART_STANDARD.md#integrated-eldenmere-town-and-businesses).

## Contents

- [Visual direction](#1-visual-direction)
- [Density and world scale](#2-artwork-density-and-world-scale)
- [Palette ownership](#3-palette-ownership)
- [Pack specification](#4-define-the-pack-before-drawing)
- [Construction methods](#5-choose-the-appropriate-construction)
- [Materials](#6-establish-the-materials-first)
- [47-tile blobs](#7-constructing-a-47-tile-blob-set)
- [Variation](#8-adding-variation-safely)
- [Decoration and vegetation](#9-decorative-terrain-and-vegetation)
- [Elevation and stairs](#10-elevation-stonework-and-stairs)
- [Water and banks](#11-water-and-bank-construction)
- [Environmental animation](#12-grass-and-environmental-animation)
- [Sources and exports](#13-source-organization-and-reproducible-exports)
- [Eldenmere integration](#14-integrating-terrain-into-eldenmere)
- [Review and acceptance](#15-review-and-acceptance)
- [Initial rebuild sequence](#16-eldenmeres-initial-rebuild-sequence)
- [Existing pack maintenance](#17-existing-pack-maintenance-reference)
- [Playable grass demonstration](#18-playable-grass-demonstration)

## 1. Visual direction

Terrain should look deliberately drawn and belong to its region. Additional pixels
improve material definition, shapes and small environmental details. For Eldenmere,
preserve emerald grass, warm compacted dirt, muted gray-beige stone, cool blue-green
water and restrained flower accents.

Eldenmere is a tended village surrounded by richer natural growth. Paths show use;
lawns stay quiet; sheltered margins collect grass, moss and flowers. Charm comes
from relationships: growth beside walls, worn path centers, moss in sheltered
joints, reeds in suitable shallow banks and flowers in undisturbed ground. Avoid
uniformly distributing every detail across the map.

| Detail level | Purpose | Examples |
| --- | --- | --- |
| Large shapes | Establish readable areas and routes. | Lawns, paths, clearings, banks, terraces. |
| Material structure | Explain the surface. | Grass clusters, compacted soil, stone faces, shallow channels. |
| Small accents | Add local character. | Pebbles, cracks, moss, petals. |

Large shapes remain readable when small details are difficult to see. Keep ground
beneath characters quiet and concentrate richer detail around appropriate margins.

## 2. Artwork density and world scale

New terrain uses **two artwork pixels per logical world unit**.

| Element | Logical dimensions | Artwork dimensions |
| --- | --- | --- |
| Standard ground tile | 24×24 | 48×48 |
| Quarter tile | 12×12 | 24×24 |
| Two-tile-wide module | 48×24 | 96×48 |

Larger assets follow the same relationship. Doubling artwork dimensions preserves
the in-game footprint. Path widths, collision, interaction positions, camera
coverage and map dimensions remain logical.

Draw additional detail at target density, preserve the grid and physical scale,
declare density and coordinate spaces in metadata, and retain native artwork
through composition. Enlarging old pixels is a compatibility treatment, not an
artwork rebuild. Do not infer physical size from occupied pixels: blades, banks
and rocks can overhang their supporting footprints.

## 3. Palette ownership

Establish named material ramps before drawing. For an existing region, use its
**currently shipped appearance** as the reference. Earlier approved studies can
contain superseded colors.

Eldenmere's current emerald grass palette is in
[`assets/terrain/grass/assets.json`](../assets/terrain/grass/assets.json), centered
on `#2c7c50`. Older Eldenmere grass/dirt palette files contain the earlier olive
colors; they describe those historical assets and must not silently select the
rebuilt grass palette. Use existing dirt, stone and water ramps as the starting
regional colors, checking their current in-game appearance as well as manifests.
Record proposed additions explicitly for visual review.

Name deep shadow, shadow, base, light, restrained highlight and any edge/joint
roles. Improve intentional clusters and shapes before adding colors. Neighboring
variants and transitions use compatible ramps; animations retain stable material
colors. Transparent pixels must not produce matte fringes. Lighting and weather
must affect related terrain coherently.

## 4. Define the pack before drawing

Record the following specification before creating the pack.

| Field | Required information |
| --- | --- |
| Scope and region | Materials, features and intended consumers. |
| Density and grid | Artwork density and logical tile dimensions. |
| Palette | Authoritative references and named material roles. |
| Perspective and lighting | Ground projection, vertical faces, heights, light direction and shadows. |
| Connections | Adjoining materials, modules, ports and junctions. |
| Variants | Fill, edge and decorative variation. |
| Animation | Moving features, fixed supports, clocks and reduced motion. |
| Gameplay geometry | Walkability, collision, approaches and clearances to preserve. |
| Review location | A representative existing scene. |
| Replacement inventory | Existing outputs, consumers and eventual retirements. |

Keep artwork reconstruction separate from unrequested map redesign.

## 5. Choose the appropriate construction

| Terrain feature | Construction |
| --- | --- |
| Grass–dirt boundaries | 47-tile blob transitions. |
| Large material interiors | Seamless fill variants. |
| Flowers, tufts and scattered rocks | Decorative sprites or overlays. |
| Terrace walls | Directional faces, caps, corners and ends. |
| Stairs | Explicit direction and elevation modules. |
| Streams | Connected banks/channels and coordinated water animation. |
| Distinctive formations | Authored modules with declared connections and footprints. |

A binary blob set cannot describe every elevation or multi-material junction.
Define layering and junction treatment where three materials meet; independently
correct transition sets can still produce an incorrect combined corner.

## 6. Establish the materials first

Draw representative interiors before completing transitions. Review individual
tiles, large repeated fields, adjoining materials, approved characters and an
existing Eldenmere scene. Establish maintained lawn, richer meadow, shaded or
sheltered ground and compacted dirt. Related colors can support different cluster
shapes, coverage and accent density.

Grass uses quiet broad color with restrained blades and shaded growth; taller
silhouettes belong in separate vegetation. Dirt uses compacted earth with sparse
stones and irregular wear while remaining readable as a route. Check for repeated
landmarks at identical positions, unintended rows, diagonals and checkerboards.
Approve the material language before multiplying it into a complete pack.

## 7. Constructing a 47-tile blob set

For Eldenmere grass/dirt, grass is the opaque base and dirt the transition overlay.
Pixels outside the dirt silhouette are transparent. Interior variants replace
suitable fully connected dirt cells.

### Neighborhood convention

The center contains dirt. Read its eight dirt neighbors clockwise:

| Neighbor | Bit value |
| --- | --- |
| North | 1 |
| Northeast | 2 |
| East | 4 |
| Southeast | 8 |
| South | 16 |
| Southwest | 32 |
| West | 64 |
| Northwest | 128 |

A diagonal counts only when both adjoining cardinal neighbors connect: northeast
requires north and east. Normalizing all 256 raw neighborhoods gives **47 canonical
shapes**. Supply a complete raw-neighborhood lookup. A grass-only center uses the
base layer, outside these occupied dirt-center cases; mask zero is isolated dirt.

### Quarter construction

Each 48×48 artwork tile comprises four 24×24 artwork quarters. Each orientation
has five states: outer corner, edge along either axis, inner corner and full
interior. Four orientations × five states give **20 oriented quarter pieces**.

1. Establish shared boundary positions.
2. Draw a representative straight boundary.
3. Draw outer and inner corners.
4. Verify quarter continuity.
5. Assemble the canonical shapes.
6. Refine assembled shapes as necessary.
7. Validate every permitted connection.

Technical tools can assemble approved pieces and lookup tables. Assembly still
requires artistic review. Compatible neighbors agree on boundary crossings,
material colors, contour thickness, shading, texture and any crossing accents.
Check joins within tiles and between complete tiles. Rotated or mirrored artwork
must retain correct lighting and material structure.

An eight-column, six-row atlas contains 47 shapes plus one unused transparent slot:
**384×288 artwork pixels** at 2×. Record identities and artwork rectangles in the
manifest rather than relying on an undocumented visual ordering.

## 8. Adding variation safely

Build variation around a verified transition set.

- **Fill variants:** restrained internal variation with compatible borders; place
  coherent groups rather than independent random noisy tiles.
- **Edge variants:** varied tufts, roots, pebbles or erosion that retain the same
  connection contract. Matching mask numbers alone do not prove compatibility.
- **Larger patches:** occasional coordinated modules that preserve compatible
  boundaries and physical scale. Avoid conspicuous repeated stamps.

Choose authored or deterministic placement so revisiting/loading does not reroll
the ground. Do not randomize terrain appearance every frame or ordinary scene entry.

## 9. Decorative terrain and vegetation

Use separate assets when details cross tile boundaries or need independent depth:
tall grass, flowers, reeds, rocks, leaves, moss and roots. Record logical canvas,
root/ground anchor, occupied silhouette, depth baseline, allowed surfaces,
collision behavior and any animation/contact response.

Keep doors, stairs, work stations and sightlines legible. Group growth believably;
ground assets with appropriate roots, soil contact or restrained shadows. Avoid
identical plants in regular rows. Decorations must not imply an impassable area
where players can walk freely.

Distinct foreground plants and rocks use thin dark contours beginning at one
artwork pixel. Continuous ground uses material boundaries and shading, not a black
box around each tile. Decoration receives glints/highlights only when tied to an
actual available interaction under the global object-cue rules.

## 10. Elevation, stonework and stairs

Define walkable tops, vertical faces, caps, inner/outer corners, side faces, ends,
stairs and any outlets/spillways. Keep height, cap thickness and stair proportions
consistent. Joints continue logically; corners show thickness; caps sit on walls;
stairs connect the intended levels. Worn edges should match material and use.

Do not suggest a different walkable height from the actual map. Use chips, cracks
and moss selectively while preserving broad stone faces and readable step edges.

## 11. Water and bank construction

Coordinate deep/shallow surfaces, damp banks, channel edges, bends, sources/outlets
and connections to bridges or spillways. Identify which features belong to terrain
and which require separate structure work.

Banks, rocks and supports stay fixed. Only intended ripples, current, reflections
and foam animate. Keep flow direction coherent through connections, registration
stable and the last-to-first transition continuous. Avoid obvious whole-texture
sliding or brightness pulsing. Highlights explain the water without making every
surface the brightest moving feature.

### Orthogonal crossing interfaces

Eldenmere crossings follow the global orthogonal exploration projection. The
source-owned architecture schedule beside `town_hd/recipe.json` declares both
bank endpoints, full deck coverage, generous walking corridors, separate rail
placement and the mill doorstep connection. Construct explicit repeat sections,
joints and ends for the actual span; measure occupied deck/rail artwork, not only
transparent PNG dimensions. Keep board and post proportions consistent rather
than stretching a centered donor across different canvases. Bank transitions
must explain a continuous dry surface while water remains visible beside/below.
Compose decks after every water phase, including reduced motion. Near rails
belong to foreground lower-body occlusion, not a screen-wide actor-covering wall.
The mill service landing owns the complete road-to-door surface; its old baked
fence is not a substitute and must not return in a later exterior export.

## 12. Grass and environmental animation

Preserve useful existing grass behavior when rebuilding: gentle breeze,
directional walking response, stronger running response, occupied holds, recovery
and consistent contact for visible party members/NPCs. Grass remains scenery unless
gameplay changes are explicitly intended.

Keep roots registered, preserve plant mass and propagate motion coherently through
stems/blades. Use appropriate amplitudes and avoid frame noise, sparkling pixels
or sudden height changes. Instance phases can differ while sharing a coherent
breeze. Fixed trunks, branches, banks and supports do not drift with foliage.

Support stable reduced motion; freeze relevant clocks during pause/focus loss.
Clear transient contacts on scene exit and rebuild them coherently on re-entry.
Do not award progress or change ownership through scenery animation.

## 13. Source organization and reproducible exports

Keep authored sources separate from runtime exports. Retain source drawings,
named palettes, technical recipes, manifests, exporters and review evidence.
Recipes record selections, registration, construction settings and variation;
manifests declare files, density, logical dimensions, artwork atlas rectangles,
masks, anchors and animation clocks. Supporting world/depth/collision data remains
logical. Source provenance must permit reconstruction without external workspace
paths. Runtime play does not require the asset-building toolchain.

Exporters may crop, uniformly sample, register, map palettes, prepare hard alpha,
assemble approved pieces, pack atlases, generate lookups and verify hashes.
Technical processing must preserve the authored design; inspect for lost detail,
damaged corners and repetition. Enlarging old pixels does not supply newly drawn
material detail. Provide a non-writing check mode to detect stale exports.

The terrain authoring and maintenance instructions belong here. Do not regenerate
parallel instructional READMEs in asset/source folders. Machine-readable local
recipes/manifests and historical review evidence remain beside their assets.

## 14. Integrating terrain into Eldenmere

Eldenmere uses assembled map layers; some grass is shared with the Sanctuary
reserve and upstream mill. Inventory consumers and active versus historical assets,
record geometry/masks, choose affected regions and verify native rendering first.
An Eldenmere-only change must not silently replace every consumer of shared grass;
choose a shared migration or an explicit regional replacement.

Preserve collision, navigation, entrances, spawns, stairs/routes, quest approaches,
water boundaries and later town additions. Use the currently assembled map, since
an older full-map compiler can omit additions introduced later.

Verify the whole chain:

**Source → atlas extraction → map/chunk assembly → scene composition → display.**

A 48×48 tile loses its new detail if an intermediate stage reduces it to 24×24.
Keep raw source loading and density-normalized drawing explicit. Installing a new
PNG alone does not certify density migration.

### Integrated Eldenmere town and upstream

The maintained owner is `tools/build_eldenmere_hd.py`, with source recipe and new
retained drawings under `assets/source/maps/eldenmere/town_hd/`. Run it to build;
use `--check` to verify reproducible exports and the linked held-prop compositions.
It reads current assembled map records and preserves unrelated quest/NPC data.
Retained pre-migration maps, logical cell geometry and alpha bounds register the
new artwork; legacy color pixels are not enlarged into the new environment.
Changed collision/navigation inside the original town rectangle stops a rebuild
for explicit source-registration review rather than silently overwriting it.

The town adds twelve 24-unit rows to the south. Inn and shop physical footprints
sit in this extension, connected to the existing southbound well-square route.
Their entrances, furnishings, local blockers and return landings are separately
authored. Original entrances, destinations, routes, spawns and collision remain at
their original coordinates. Upstream keeps its existing dimensions and collision.

`ground_overlays` are nonoverlapping chunks no larger than 192×192 logical units
(384×384 artwork). Dry chunks are static; wet chunks reference six 200 ms states.
One world origin controls tile texture phases. Preserve cardinal channel ports,
westward outlet bindings and full/trickle states; thin flow follows bends as well
as straight runs. Shared full-height spillways keep their authored 24×48 footprints.
Bridge decks/far rails draw below actors; near rails remain the foreground pass.

Ground frames load only when drawn/sampled, through a 48 MiB scene-local LRU.
They bypass the persistent raw character/prop image cache. The separate global
transform cache retains its existing bound. `World.draw_ground` is the shared
composition pass; `World.ground_region` samples a logical rectangle from it for
quest-controlled flow overlays. Never sample a whole-map `ground[phase]` bitmap:
the ground is now composed from visible chunks. These helpers preserve native
pixels through the scene buffer and avoid full-map frame duplication.

The composed grass manifest activates three native variants for every existing
town/upstream clump, preserving IDs, roots, contact areas, phases and directional
walk/run/recovery behavior. It removes unused legacy variant references locally;
other scenes retain their own banks. Plants keep fixed roots and their logical
canvases. Scene-local prop replacements use `room_art_image` even outdoors;
raw character/atlas loading remains explicit and separate.

The well retains its rope/crank/handoff data and one-pail ownership. New pails
register to the old occupied bounds, rotate as rigid props about the handle and
show distinct fill levels. Rope and pail disappear behind the near rim during
lowering. Irrigation/intake gates retain their functional opening states. Bowls,
toy boxes and lantern work retain consumed/empty states and transfer timing.

Pause/focus freezes exploration clocks. Reduced motion holds ambient ground,
foliage, smoke and light while preserving functional doors, recovery and authored
work. Native gameplay captures, route evidence and renderer timings are in
[the town review](reviews/eldenmere_town_hd/README.md). Generate them with
`python tools/capture_eldenmere_hd.py docs/reviews/eldenmere_town_hd`; the tool
uses temporary saves/settings only.

### Eldenmere settlement framework

The settlement framework owns street, parcel and public-space composition contracts.
Its source is `assets/source/maps/eldenmere/settlement/recipe.json`; the maintained
town recipe selects it through `settlement_recipe`.
`tools/eldenmere_settlement.py` resolves its build-time contracts and
`tools/eldenmere_settlement_inventory.py` inventories semantic native asset
candidates. The reproducible report is
`assets/maps/eldenmere/settlement/manifest.json`.

PR 1 delivered metadata only. **PR 2 integrates ground-only streets with zero
active prop placements.** The recipe explicitly selects `ground_only`; the helper
still rejects placements and rejects ground activation under `framework_only`.
There is no new blocking mask, navigation behavior, interaction, scene or save
state. `tools/build_eldenmere_hd.py` remains the sole town map writer and produces
the report from its working town data. The standalone framework CLI writes only
the report. Generated town map/manifest hashes are not producer inputs, avoiding
a recursive dependency on the town's own outputs.

`tools/eldenmere_settlement_streets.py` resolves and paints the recipe's native
ground treatments. Primary compact-earth roads keep the western/southern spine
legible; secondary lanes retain the two-bridge loop and business connection.
Small stone surfaces mark selected junctions, bridge approaches, stair feet and
all 13 doorsteps. Two narrow desire paths acknowledge existing grass travel.
They do not narrow existing usable roads or declare new walkable ground. Courtyard
dressing, workyards, civic furniture, household plots, Venn's growing area and
southern planting remain later composition work.

Treatment coordinates are logical; native masks and terrain composition use
twice those dimensions. Routes have explicit widths; rectangles have explicit
bounds. Doorsteps resolve their center from the **loaded door anchor**, retaining
fractional logical registration. Unknown treatment keys, invalid geometry,
unsupported materials and gameplay/collision overrides fail validation. Ground
is allowed within movement reservations: those reservations protect access from
new obstacles, not from flat surfaces. Existing physical blockers clip paint.

Paint before masonry, stairs, water and independently owned bridge assemblies.
Keep the authored stone blob boundary and spatial phase
`x % 2 + 2 * (y % 2)` at a shared world origin. Stone contact sits over its declared
compact-earth substrate; it does not introduce a new curb or solid support.
Keep hard alpha and native detail. A published native coverage mask bounds the
allowed changes; all six final ground phases must match the pre-pass ground
outside it. Collision, navigation, foregrounds, buildings and door interfaces
are separately preserved, including bridge ground drawn after water.

The complete `cartography.street_network` is compiled from the maintained old
route sources, later household/school/well paths and the same active ground
treatments. Its records use logical world points, widths, material and role.
`MapUI` uses that complete network instead of drawing the old road diagram again;
maps without the key retain their legacy fallback. Runtime map display never
reads the source recipe. Preserve the cartography's source references when an
unchanged route is maintained rather than copying its geometry into another owner.

Protection records come from current map interfaces and explicit selectors into
their authoritative route, household, well, work and story sources. They preserve
source evidence and roles for movement or sightlines. Selectors may read geometry
in tiles, but their padding is always a **logical half-extent**; it is never
multiplied by tile size. Routes protect the swept segments and actor clearance,
not every point inside their enclosing rectangle. These are reservations against
new dressing, not assertions that all existing protected pixels are walkable.
An existing well or work surface can already occupy its own reserved area.

Code-owned geometry uses named `reviewed_regions` and a source-file hash. When
that owner changes, inspect its named scene geometry and update the reviewed
region deliberately before refreshing provenance. Do not silently repin a hash
or omit an unresolved selector. Interior, upstream and cinematic coordinates
are excluded unless the selected geometry explicitly belongs to the town; a
key named `courtyard` does not establish its scene. The report records these
excluded contexts for review.

The five district envelopes describe overlapping composition roles, not new
collision or guaranteed empty placement space. In particular, the historical
mill-yard rectangle is not an approved free apron: it overlaps later building
art. Future placements must be checked against current occupied bounds as well
as protected actors, entrances and routes.

The catalogue separates pack delivery/visual-approval metadata, exact existing
town bindings and available reuse candidates. Every listed native canvas is
checked against declared logical size and 2× density. Candidate availability
does not approve a new placement, define collision or grant interaction cues.
The well and existing workshop fixtures retain their functional owners; do not
replace them with decorative clones. Crop-bed and mill-storage gaps remain
explicit review items, not silently created art or new gameplay.

`validate_placements` can review future namespaced `settlement.*` proposals
without applying them. Positions are logical **artwork top-lefts**; a solid
proposal requires a separate local logical footprint. Supporting rectangles and
alpha do not automatically become collision. Tall artwork is also checked against
protected standing-character and interaction sightlines. A nonblocking tree can
still be an invalid placement when it hides a required scene. Ground and low
dressing roles require deliberate classification rather than bypassing visibility
review by default.

```sh
python tools/build_eldenmere_hd.py
python tools/build_eldenmere_hd.py --check
python tools/build_eldenmere_settlement_framework.py
python tools/build_eldenmere_settlement_framework.py --check
python tools/capture_eldenmere_settlement_framework.py /tmp/eldenmere-framework-review
```

The framework capture tool supports `--baseline /path/to/earlier/observations.json` to compare
active map/art inputs and native views with an earlier run. See the
[framework review](reviews/eldenmere_settlement_framework/README.md) for the
historical framework evidence and its scope. The [street review](reviews/eldenmere_streets/README.md)
records PR 2's authorized surface differences and unchanged physical interfaces.
Preservation captures do not certify the visual
quality of unresolved building, bridge or landmark issues; those asset fixes
remain separately scoped. The regional guide remains the creative authority.

### Integrated Sanctuary courtyard and approach

The earlier courtyard source remains under
`assets/source/maps/eldenmere/courtyard_hd/`. Its approved facade, planter/prop
registration and native contact-grass drawings are retained. The complete town
composer now owns the facade animation, ground, composed grass manifest and overview.
It rebuilds the approved facade through the courtyard helper, keeping window
lighting steady while preserving the bell and smoke. The courtyard
build command forwards to that composer; it cannot restore a historical overview
or replace another region's bindings. Earlier review images remain historical
acceptance evidence, not a separate construction guide.

The legacy full-town compiler is guarded against overwriting the HD map. Its
terrain-only command forwards to the maintained composer. Reproduce historical
full-map exports in an isolated historical checkout. Do not recompile the live
map from older blockouts, which omit later buildings and story additions.

## 15. Review and acceptance

### Individual assets

Check palette, intentional clusters, material identity, contour weight,
transparency, complete corners/edges and animation registration. Enlarged views
help diagnose defects.

### Assembled terrain

Include large fills, straight boundaries, tight bends, inner/outer corners, narrow
connections, intersections, isolated patches, enclosed islands, irregular borders,
neighboring variants and relevant multi-material junctions. Inspect at gameplay and
enlarged scales for grids, stamps, inconsistent edges, holes, quarter seams,
texture breaks, incorrect lighting and noise.

### Actual gameplay

Review beneath approved characters and beside existing buildings during walking,
running and camera movement. Check readability, scale, route clarity, vegetation
occlusion, interaction stations, elevation, water, native detail and reduced motion.
Technical seamlessness alone does not establish attractive or readable scenery.

Automate appropriate checks for dimensions/density, palette, alpha, atlas bounds,
all 256 lookups, exactly 47 canonical states, quarter reconstruction, compatible
boundaries/variants, animation registration, deterministic placement, unchanged
geometry and reproducible exports. Visual review remains necessary.

## 16. Eldenmere's initial rebuild sequence

1. **Material study:** lawn, meadow, shaded ground and dirt, repeated broadly with
   approved characters for scale.
2. **Transition study:** straight edges, outer/inner corners, narrow path and
   clearing. Resolve boundary design before completing the set.
3. **Complete pack:** 47 transitions, compatible fills, restrained edge variants,
   initial decorations, metadata and checks.
4. **Scene review:** one existing location containing open ground and a building
   approach, seen during ordinary movement.
5. **Town integration:** after appearance approval, migrate intended consumers,
   preserve geometry, verify native composition and remove superseded assets/code
   once all references have migrated. Update this document's implementation status.

Grass/dirt, stone paving, terraces and water/natural shores are staged below.
Channels/spillways, vegetation and natural accents retain their original delivery
references below. The complete Eldenmere integration above activates selected
town/upstream exports; other regional migrations remain separate work.

## 17. Existing pack maintenance reference

Except for the explicitly staged HD banks, dimensions, timings and construction
formats below describe **existing 1× exports**, not requirements for newly drawn
2× packs. Preserve these implementation
facts when reproducing the existing bank. Recipes/manifests hold exact crops,
thresholds, masks, palette roles, placements and hashes. Earlier review images
include older character art and illustrative layouts; they do not establish current
character dimensions or canonical geography.

Run commands from the repository root using a Python environment with the asset
tools' Pillow dependency. The game uses Pygame and checked-in exports; it requires
no build step. Use `python main.py` for ordinary play. Commands in this section are
maintenance entry points, not instructions to rebuild unrelated assets during a
scoped migration. Only use `--check` on tools that implement it.

### Pack locations and commands

For the seven Eldenmere packs below, source/recipe paths are
`assets/source/terrain/eldenmere/<pack>/recipe.json`; runtime paths are
`assets/terrain/eldenmere/<pack>/`. Retained `materials_concept.png` references and
source parts live beside the recipes.

| Pack | Runtime metadata | Build | Verify |
| --- | --- | --- | --- |
| `grass_dirt` | `tileset.json`, `palette.json` | `python tools/build_eldenmere_terrain.py` | `python tools/test_eldenmere_terrain.py` |
| `stream` | `tileset.json`, `palette.json` | `python tools/build_eldenmere_stream.py` | `python tools/test_eldenmere_stream.py` |
| `irrigation` | `tileset.json`, `palette.json` | `python tools/build_eldenmere_irrigation.py` | `python tools/test_eldenmere_irrigation.py` |
| `terraces` | `tileset.json`, `palette.json` | `python tools/build_eldenmere_terraces.py` | `python tools/test_eldenmere_terraces.py` |
| `foliage` | Per-design `foliage.json`, `palette.json` | `python tools/build_eldenmere_foliage.py` | `python tools/test_eldenmere_foliage.py` |
| `grass_flowers` | Per-design `plant.json`, `palette.json` | `python tools/build_eldenmere_grass_flowers.py` | `python tools/test_eldenmere_grass_flowers.py` |
| `reeds` | Per-design `reeds.json`, `palette.json` | `python tools/build_eldenmere_reeds.py` | `python tools/test_eldenmere_reeds.py` |

Tests verify existing exports and illustrative scenes. Rebuilds can update source
parts and review assets as well as runtime output; use a disposable checkout when
only checking the historical pipeline. Existing band/cluster methods below are
bank-specific reproduction facts, not mandatory methods for new plant drawings.

### Staged Eldenmere HD grass/dirt blob

Source recipe: `assets/source/terrain/eldenmere/grass_dirt_hd/recipe.json`.
Staged pack: `assets/terrain/eldenmere/grass_dirt_hd/tileset.json`.
Original delivery status was `rebuilt` / `not_integrated`; current Eldenmere bindings are listed above; user visual approval is recorded separately.
This bank is not selected by any playable map or runtime terrain registry.

The pack contains 47 distinct 48×48 hard-alpha dirt overlays, a 384×288 atlas
with its final slot empty, a matching coverage atlas, 20 oriented 24×24 quarter
pieces, four grass materials and four dirt fills. Logical tile/quarter sizes are
24×24 and 12×12. Atlas rectangles are artwork coordinates; world anchors remain
logical. The complete 256-entry lookup uses this document's eight-neighbor rule.
Grass uses the shipped emerald ramp; dirt uses the existing earth/stone colors.
Fresh retained material and edge drawings supply the artwork. Source RGB medians
are registered to the existing base colors before exact-ramp assignment, keeping
broad ground quiet. Recipe metadata records scales, crops and connection ports.

```sh
python tools/build_eldenmere_grass_dirt_hd.py
python tools/build_eldenmere_grass_dirt_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_hd_blob
```

[Offline review evidence](reviews/eldenmere_hd_blob/README.md) includes all shapes,
repeated fills, winding paths, corners, islands and scale references. The retained
cottage is a legacy building shown at its existing physical size; Caelan and
Iselin retain native approved HD pixels. These are illustrative compositions,
not gameplay captures or runtime implementation. Integration must later verify
the actual map, native rendering and interactions under section 14.

### Staged Eldenmere HD stone paving

Source recipe: `assets/source/terrain/eldenmere/stone_paving_hd/recipe.json`.
Staged manifest: `assets/terrain/eldenmere/stone_paving_hd/tileset.json`.
Original delivery status was `rebuilt` / `not_integrated`; current Eldenmere bindings are listed above, with user visual approval recorded separately.
No playable map, selector, collision or renderer is changed by creating this bank.

There are **47 canonical boundary shapes**, four phase-correct stone surface
atlases and separate 47-shape grass/dirt contact-trim atlases. Tile artwork is
48×48 per 24×24 logical footprint; quarter masks are 24×24 artwork. The fieldstone
palette is the existing warm gray-beige terrace ramp. New retained surface drawings
supply irregular fitted stones, quiet worn faces, restrained cracks and highlights.
Optional sparse moss accents use existing greens and clip to stone mortar/shadow.

**Texture phases are spatial, not random variants or animation frames.** A 96×96
artwork pattern spans a 2×2 tile block. Select phase
`(world_tile_x % 2) + 2 * (world_tile_y % 2)` using a common world origin across
connected paving. The four interior tiles contain different arrangements but must
retain that adjacency. Their stone/joint ports are paired; random phase selection
would break joint continuity. Keep the same phase when changing a boundary mask.

The manifest records four body files per shape, contact files, the complete
256-neighborhood lookup, coverage/quarter masks, coordinate spaces and path bases.
Stone bodies are common to both surrounds. For grass–dirt–stone junctions, select
contact trim from the **actual substrate mask per pixel**, then draw the stone
body above it. Do not choose one surround for an entire mixed paving tile.
Layer order is substrate, material-clipped contact, phase-correct body, optional
mortar-clipped moss and independently sorted world objects.

```sh
python tools/build_eldenmere_stone_paving_hd.py
python tools/build_eldenmere_stone_paving_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_stone_paving_hd
```

[Stone-paving review evidence](reviews/eldenmere_hd_stone/README.md) shows both
surrounds, repeated phase-correct material, a paved square, narrow walkway, enclosed
patches, three-material junctions and approved character scale beside a retained
cottage. These are offline compositions, not integration captures. Runtime/native
composition, interactions and real map geometry still need integration acceptance.

### Shared emerald grass in production

Source: [`assets/source/terrain/grass/recipe.json`](../assets/source/terrain/grass/recipe.json).
Runtime: [`assets/terrain/grass/assets.json`](../assets/terrain/grass/assets.json).
The source records the approved study fingerprint, referenced assets and derivative
inputs. Twelve 24×24 materials span lawn, meadow and woodland; their borders share
emerald base green. Four rooted silhouettes use a 24×32 canvas, root `(12,28)`, six
800 ms breeze poses and three parting strengths per cardinal direction. Fixed root
rows are 26–31. Combined opaque height is capped at 17 pixels; upright plants are
16–17 pixels, with foreground tips no more than five pixels above the root. Rear
and front layers keep upper bodies readable.

The shared bank includes 47 dirt transitions, three dirt interiors and white,
yellow and violet flowers derived from earlier Eldenmere inputs. Exact legacy
greens are remapped while earth/petals, transparency, bases, geometry and timing
are retained. Flower-local image paths are relative to each plant manifest;
`assets.json` paths are relative to the repository root.

Map `grass` records specify the shared manifest and clump IDs, roots, variants and
breeze phases. World supplies visible actor contacts after movement. Occupancy and
recovery are transient, require no save migration, do not block movement and add
no speed penalty. Reduced motion holds a static occupied presentation. Production
consumers include Eldenmere, the Sanctuary reserve and upstream mill area; regional
overworld and battle terrain have separate vocabularies.

Reproduce dependencies in order:

```sh
python tools/build_grass_assets.py
python tools/build_playable_eldenmere.py --terrain-only
python tools/build_elden_vale_sanctuary.py
python tools/build_mill_quest.py
```

Non-writing checks available for the shared pack and selected map compilers:

```sh
python tools/build_grass_assets.py --check
python tools/build_playable_eldenmere.py --terrain-only --check
python tools/build_elden_vale_sanctuary.py --check
```

Eldenmere coverage recipes live in
[`assets/source/maps/eldenmere/grass/recipe.json`](../assets/source/maps/eldenmere/grass/recipe.json).
Per-water-phase coverage masks protect paths, banks and later buildings; hashes
and the collision fingerprint reject stale assumptions. Review those sources if
layout changes. Terrain-only compilation preserves the assembled town; a full
historical town rebuild requires its later follow-up builders.

### Earlier grass/dirt foundation

Four 24×24 grass variants form `grass.png` (96×24). Three dirt interiors form
`dirt_fill.png` (72×24); alternatives apply to fully surrounded dirt, mask 255.
`dirt_blob_47.png` is 192×144, eight columns by six rows with the last empty.
`dirt/mask_<number>.png` contains canonical overlay tiles. `tileset.json` declares
rectangles, bit masks, lookup and source-quarter order.

The recipe uses 12×12 quarters, sparse texture windows and a one-pixel common
material border. Nearest sampling and named-ramp quantization keep hard alpha;
the dirt-edge color is reserved for contours. Twenty source quarters, a one-pixel
neighborhood halo and matching boundary geometry support continuity. Verification
covers all raw masks and 2,048 compatible adjacency cases, quarter reconstruction,
palette/alpha and exact review-scene reconstruction.

`materials_review.png`, `blob_47_review.png`, `review_scene_native.png`,
`review_scene_ground_native.png` and `review_scene.json` record the earlier study.
Its olive grass palette is historical, not the current emerald target.

### Existing stream and banks

Two compatible 24×24 surfaces have six 200 ms phases (1.2 s). All connected water
shares a phase; surface variants may differ independently. `banks_47.png` and
`water_masks_47.png` are 192×144 atlases. `water_surface.png` is 144×48.
`water_47/frame_01.png`–`frame_06.png` bake variation zero; `water_blob_47.png`
stacks those into 192×864. Variation one uses the layered representation.

Layer order: underlying ground, selected surface clipped by its water mask,
stationary bank/shallow overlay, then appropriately sorted actors/props.
Source `parts/` contains a surface and three binary ripple masks; `quarters/`
contains 20 bank pieces plus 20 water-alpha pieces. Existing geometry uses a
2-pixel earth lip and 1-pixel shallow rim. Local drifting/fading reflection
clusters move at most two pixels; banks, silhouettes and broad base color stay
fixed. Recipes define sparse depth windows, thresholds and arrangement choices.

Reviews include `bank_47_review.png`, `water_cycle_review.gif`, per-phase scene
PNGs and the reconstructible `review_scene.json`. Cross-check dirt compatibility
with `python tools/test_eldenmere_terrain.py` when maintaining stream connections.

### Existing irrigation channels

This connected terrain bank uses 24×24 tiles, 8-pixel water channels, a 1-pixel
shallow rim and 2-pixel earth banks. It has **40 directed modules**: 32 routes
over 15 cardinal connection shapes, four stream intakes and four outlets.
Six 200 ms phases share the stream clock. Current marks repeat every 12 pixels
and advance two pixels per phase; banks stay fixed. These baked frames are art,
not a water simulation.

Cardinal connection bits are **N=1, E=2, S=4, W=8**, distinct from the eight-neighbor
blob convention. Each route has one input and other connected ports as outputs;
single-port modules are settling caps, while special outlets supply trickles.
Intake input is `stream`; its directional output joins a channel. An outlet's
input feeds discharge toward `receiver`, with declared local effect bounds.
Place stream intakes across aligned straight banks and keep connected phases
synchronized. Tests cover all compatible directed joins, movement in four straight
directions and source-to-outlet reachability.

Phase atlases are 192×120 (eight columns/five rows); `irrigation.png` stacks them
into 192×720. `channel_banks.png` and `channel_masks.png` are 96×96, with transparent
slot zero and connected shapes 1–15. Source `parts/` retains sampled earth and a
binary droplet; `shapes/` retains bank/mask pairs and directional inlet/outlet
layers. Source preparation uses nearest sampling, named ramps and hard alpha;
exact orientation changes use native-pixel transposes. Shared-border textures
remain compatible. `review_scene.json` and module/channel previews retain the
schematic routing review, not a canonical map or implemented irrigation system.

### Existing terraces, stairs and spillway

Stone midtone is `#969284`; ramps, modules and ports are in the palette/tileset.
A wall face is 24 pixels including coping. The pack has three matching front
textures, corners, ends, side faces and back coping. There are 18 static tiles
(14 masonry modules and four stair quarters), and 20 slots per animated phase.
Five-column/four-row phase atlases are 120×96; `terraces.png` is 120×576.

`stairs_south.png` is 48×48 with four broad treads, a central 34-pixel visual
walking area, north upper landing and south lower landing, representing a
24-pixel elevation change. The 24×48 south spillway has 8-pixel north/south ports
and six 200 ms phases synchronized with channels. Masonry, stairs, shorelines and
water masks stay fixed; falls, impact flecks and ripples move. Prefabs or their
recorded tile quarters must be placed together at their declared connections.

Retained parts include 48×24 wall material, 48×48 stair material, fall/ripple masks,
fixed spillway structure and water mask. Tests check boundaries, ports, downward
flow reachability, clearances and exact GIF/scene reconstruction. Review metadata
records the illustrative upper/lower terrain; it is not itself playable collision.

### Existing foliage, flowers and reeds

| Design | Existing artwork canvas | Supporting rectangle / root | Existing loop |
| --- | --- | --- | --- |
| Broadleaf tree | 96×120 | `[36,96,24,24]` | 9×600 ms = 5.4 s |
| Shrub | 24×24 | Declared in `foliage.json` | 9×600 ms |
| Sparse/splayed/dense grass; three flower colors | 24×24 | 24×24 placement; fixed roots from row 20 | 9×600 ms |
| Tall reed | 24×48 | `[0,24,24,24]`; fixed rows 44–47 | 9×600 ms |
| Short reed | 24×24 | `[0,0,24,24]`; fixed rows 20–23 | 9×600 ms |

Ground rectangles describe support/placement, not automatic collision. Tree art
occupies about 90×92; shrub art 22×19. Grass heights are 13/11/18 pixels and flowers
20. Tall/short reed art samples to 20×36 and 18×21 respectively; tall canvas
padding supports north overhang. Recipes retain exact thresholds, ramps and roots.

Foliage source preparation removes magenta and classifies bark/leaf/shadow into
named ramps. Fixed trunk/branches/shadow and five tree/three shrub leaf clusters
compose in metadata order: shadow, canopy backing, moving leaf patches, fixed wood.
Patches move at most one pixel east/up; rest reconstructs the sampled source.

Flowers and grass retain three disjoint horizontal bands plus a fixed base.
Whole flower heads stay in the top band; offsets are zero/one pixel east with no
vertical displacement. Reeds use the same anchored format. Their older exporter
uses premultiplied BOX sampling to retain thin stalks, discards coverage below
48/255 and hardens all retained pixels; seedheads use the cottage wood ramp.
These are technical facts about those retained sources, not permission for blurred
runtime sprites. Exported alpha is zero or 255.

Per-design manifests declare idle/frames/sheet paths and layer order. Foliage
uses trunk/shadow/canopy/clusters; grass/flowers and reeds use bands/base. Rooted
plants are nonblocking scenery. Review placements retain existing paths,
entrances, water routes, structures and earlier actors; they are illustrative.
The combined cottage/vegetation review has 54×200 ms frames (10.8 s), retaining
both the 5.4 s foliage and 3.6 s cottage clocks. Held GIF frames may merge only
when decoded pixels and total timing remain exact. Pack review boards, closeups,
`scene_frames/` and placement metadata remain alongside each bank.

## 18. Playable grass demonstration

The isolated preview uses the shared renderer and player movement rules. It
opens no journey/settings file and includes maintained lawn, meadow, woodland,
rooted clumps and adjacent material comparisons. Its retained comparison art can
show older character pixels; use current approved characters when reviewing new
terrain. It does not replace production maps.

```sh
python tools/preview_grass.py
```

| Control | Action |
| --- | --- |
| WASD / arrow keys | Walk |
| Shift while moving | Run |
| Release movement | Stand among the grass |
| R | Reset |
| M | Toggle reduced motion |
| H | Toggle guide |
| Escape | Close |

Source: `assets/source/terrain/grass_demo/recipe.json` and
`assets/source/maps/grass_demo/`. Runtime: `assets/terrain/grass_demo/assets.json`
and `assets/maps/grass_demo/`. `grass_demo.py` supplies the preview world;
`interactive_grass.py` owns occupancy/recovery. The source recipe retains material
motifs, blade root/tip/depth graphs, palette and reference hashes. Canvas, roots,
height cap, breeze and parting formats match the shared-grass reference above.
The approved study supplies production art through its recipe/functions.

```sh
python tools/build_grass_demo_assets.py
python tools/build_grass_demo_scene.py
python tools/build_grass_demo_assets.py --check
python tools/build_grass_demo_scene.py --check
python tools/preview_grass.py --headless --frames 120 --screenshot /tmp/grass-demo.png
```

**Existing rebuild limitation:** `build_grass_demo_assets.py --check` currently
fails while reading the earlier Caelan reference
`assets/source/characters/caelan/overworld_refresh/legacy/idle_front.png`, retired
before this documentation consolidation. Its recipe and builder remain unchanged
here. Reproducing that older source pipeline needs a separately scoped reference
migration; this guide does not claim its check passes. Checked-in pack files remain
available. The shared production exporter `build_grass_assets.py --check` passes.

[Grass demonstration evidence](reviews/grass_demo/README.md) and
[production rollout evidence](reviews/grass_rollout/README.md) retain captures and
historical source/artifact fingerprints. Capture entry points are
`python tools/capture_grass_demo.py` and `python tools/capture_grass_rollout.py`;
each offers `--check` for its recorded capture. Source documentation deletion
intentionally makes older fingerprints historical: a stale check calls for a
new scoped capture, not editing old verification JSON to pretend it is current.
Production rollout captures use disposable saves; the upstream still is an
initialized production fixture, not proof of quest-gated travel.


### Staged Eldenmere HD terraces, walls and stairs

Source recipe: `assets/source/terrain/eldenmere/terraces_hd/recipe.json`.
Staged manifest: `assets/terrain/eldenmere/terraces_hd/tileset.json`.
These assets were delivered at 2× density as a staged bank; current Eldenmere bindings are listed above. Merge does not
constitute user visual approval; that status remains explicit in the manifest.

The bank contains three masonry families (maintained, weathered and mossy),
14 wall modules per family, four stair designs (including broad-lipped stone),
48 matching upper/lower landings, and nine illustrative terrace prefabs combining
the three wall treatments with grass, dirt or paving. Wall modules include three
front-face variations, outer/inner corners, ends, sides, back coping and back
corners. Shared named connection ports permit wear treatments to meet.

Wall modules occupy 24×24 logical units, exported at 48×48 artwork pixels.
Wall rise stays 24 logical units. South-descending stairs occupy 48×48 logical
units (96×96 artwork), rise 24, and have four treads with upper landing north and
lower landing south. The walkable interval remains x=[7,41) logical, width 34.
Do not rotate or mirror this stair set into unsupported orientations. Wall
coverage envelopes retain existing geometry only; every visible material pixel
comes from the retained new source drawings, registered to the existing stone
ramp and current emerald greens. Do not enlarge legacy color art as new artwork.

Atlas rectangles and source rectangles are in artwork pixels; anchors, sizes,
heights, landings and clearance are explicitly named logical fields. Wall `ports`
name compatible edges, tested across all three treatments. Source coping bands
are registered to shared ten-artwork-pixel caps; side returns retain the existing
coverage envelope. Stair quarters reconstruct the full source export. Landing
contact bands register to the adjacent stair edge. Grass/dirt landings have one
floor phase; paving has all four world phases, selected using x%2+2*(y%2) from a
common tile origin. Do not randomly substitute paving phases.

Prefabs are 144×144 logical units with a six-by-three-tile upper floor and a
south stair opening. Metadata records each module placement, upper/lower landing,
stair clearance and elevation. They are illustrative compositions, not collision
masks or automatic navigation. Future integration must preserve live geometry,
apply explicit renderer adapters, and review actual movement and occlusion.
Spillway/water assets and active maps are outside this staged bank.

```sh
python tools/build_eldenmere_terraces_hd.py
python tools/build_eldenmere_terraces_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_terraces_hd
```

[Terrace review evidence](reviews/eldenmere_hd_terraces/README.md) records native
character scale, enlarged modules, stair variants, reproducibility and the
one-time preservation comparison. These are offline compositions; gameplay
acceptance remains a later integration step.

### Staged world HD water and natural shores

Source recipe: `assets/source/terrain/water_hd/recipe.json`.
Staged manifest: `assets/terrain/water_hd/tileset.json`.
Original delivery status was `rebuilt` / `not_integrated`; current Eldenmere bindings are listed above; user visual approval is separate and remains
not reviewed. Eldenmere is the primary scale/palette reference; the bank is reusable
across regions. No runtime selector, map, collision or navigation is changed.

Four water families are temperate freshwater (existing muted teal ramp), clear
cold water, peat-stained water and deep lake blue. The latter three have explicitly
recorded new ramps. Each family has shallow/deep treatments, two arrangements,
four spatial texture phases and six 200 ms temporal frames: 64 surface records,
384 animated surface PNGs and 64 explicit reduced-motion stills. A 96×96 artwork
field spans 2×2 logical tiles. Select spatial phase `(x%2)+2*(y%2)` from one world
tile origin; select arrangement deterministically in coherent groups. Never
confuse spatial phase, material arrangement and animation frame. Two-artwork-pixel
quiet ports are shared across arrangements. All connected water/effects share the
six-phase, 1.2-second clock. Base texture stays still; source-derived ripple
clusters move locally with restrained color changes. Reduced motion uses the
explicit stills and omits animated current/foam effects.

Five shoreline families—grass, exposed earth, sand/gravel, rock and marsh—each
provide all 47 canonical shapes and two compatible arrangements (235 geometric
material configurations, 470 bank images). Twenty oriented quarter records supply
water coverage and each bank/arrangement. Tile size remains 24×24 logical / 48×48
artwork. Rectangles are artwork pixels; draw anchors remain logical. Legacy
coverage masks are retained as geometry only, never as enlarged visible artwork.
New material drawings, crops, named ramps and source hashes are retained.

Water, land-bank and shallow-margin masks are separate. Land bank and water do
not overlap; the shallow margin is a subset of water. L-mode depth controls contain
0/85/170/255 discrete depth levels and intersect the water mask. `compose_water`
registers intermediate depth colors back to the receiving surface palette; depth
never defines collision, swimming or damage. Submerged pebbles/bed details are
optional overlays; emergent rocks and plants remain separately depth-sorted.

Supported bank-material meetings are grass–earth, earth–sand, sand–rock,
earth–rock, earth–marsh and grass–marsh. Twelve junction atlases show both axes
across all 47 shapes. `mix_banks` uses the actual substrate selector per pixel,
then a narrow fixed soil contact lip, preserving coverage. Do not choose one bank
material for a whole tile when two materials meet; do not claim arbitrary bank
pairs are supported without a reviewed meeting treatment.

Twenty-four directional current overlays cover four straights, eight directed
bends and four directions each of mouth, widening and narrowing cues. Geometry
widening/narrowing comes from adjacent shoreline shapes; the overlay does not
change water coverage. Clip effects to receiving water and recolor to its family.
Four separate ripple, eddy, foam and impact effect loops supplement nine source
accents (including submerged pebbles, wet rock, deposits and rooted short plants).
Banks/supports stay fixed; root anchors, logical sizes and nonblocking decoration
status are explicit. Tall vegetation, open-ocean surf, frozen surfaces and magical
water remain separate future work.

```sh
python tools/build_world_water_hd.py
python tools/build_world_water_hd.py --check
PYTHONPATH=.:tests python -m unittest test_world_water_hd
```

[Water and shore review evidence](reviews/world_water_hd/README.md) includes four
regional compositions, every shoreline family, a broad repeated water field,
animated loops, native PNG frames, material studies and placement metadata.
GIFs use one exact shared palette per sequence; fixed artwork must not flicker
from frame-specific palette changes. These are offline asset fixtures, not actual
map integration or gameplay captures. Integration must independently verify live
terrain boundaries, bridge occlusion, movement and collision under section 14.

### Staged Eldenmere HD channels and spillways

Source recipe: `assets/source/terrain/eldenmere/waterworks_hd/recipe.json`.
Staged manifest: `assets/terrain/eldenmere/waterworks_hd/tileset.json`.
Original delivery status was `rebuilt` / `not_integrated`; current Eldenmere bindings are listed above, visual approval not yet reviewed. This bank
completes the water asset stage, without modifying any active scene or geometry.

Three channel treatments are earth-cut, maintained stone and weathered/lightly
mossy stone. Each retains all 40 directed modules: 32 routes across 15 cardinal
connection shapes, four stream intakes and four outlets. The weathered channel
uses the new mossy masonry material. Ports remain N=1,E=2,S=4,W=8, **not** the
eight-neighbor shoreline convention. Water is eight logical units wide, with
existing bank/receiver geometry retained from coverage-only source envelopes.
Logical modules are 24×24; artwork modules are 48×48. New visible pixels come from
the world-water source drawings and staged HD masonry, not legacy RGB enlargement.

Banks, water masks, shared per-route flow layers, six composed temporal frames,
static alternatives and phase atlases are exported separately. A route has one
input and other connected ports as outputs; do not connect two outputs and expect
coherent current. Match outgoing ports to incoming opposite ports. Every physical
port is tested through all six phases within its structural treatment. The
quiet outer connection pixels retain the receiving material's base color.
Currents move four artwork pixels per 200 ms phase over a 24-artwork-pixel period,
matching the existing two-logical-unit step and twelve-logical-unit period.

Intakes overlap an aligned straight natural-stream bank; their water coverage
opens the central bank while preserving the side supports. Outlets include a
source-derived airborne droplet crossing the gap to the fixed receiving pool.
Only outlet effects may extend beyond the water mask, and only within their
explicit logical `effect_bounds`. Droplets progress toward the receiver and enter
the pool in the final phases. These are authored visual modules, not simulation.

Three south-only spillways match maintained, weathered and mossy terrace masonry.
They retain a 24×48 logical / 48×96 artwork footprint, 24-unit fall and north/south
eight-unit water ports x=[8,16). Structure and coverage are fixed. Downward streaks,
impact flecks and small basin ripples animate on the common six-phase clock.
Do not rotate them to unsupported elevations/facings. Integration must separately
preserve collision, walking routes, elevation and sort/occlusion behavior.

Composed exports use temperate freshwater. Other regional water is supported by
combining the bank/structure and coverage layers with that family's water surface
and recolored flow/effect layers. Use its reflection/flow roles rather than merely
placing temperate-colored marks on another family's water. Reduced motion uses
explicit still files, with no airborne/current animation.

```sh
python tools/build_eldenmere_waterworks_hd.py
python tools/build_eldenmere_waterworks_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_waterworks_hd
```

[Waterworks review evidence](reviews/eldenmere_waterworks_hd/README.md) records the
three route inventories and a reconstructible stream-intake/bends/spillway/outlet
composition. It is an offline fixture; gameplay activation remains separate.
Recipes pin the geometry and current source dependencies. Existing water, channel,
terrace and map banks remain available until a separately reviewed migration.

### Staged world HD vegetation and natural accents

Source recipe: `assets/source/terrain/vegetation_hd/recipe.json`.
Staged manifest: `assets/terrain/vegetation_hd/plants.json`.
Original delivery status was `rebuilt` / `not_integrated`; current Eldenmere bindings are listed above; visual approval remains not reviewed.
The reusable pack contains **51 designs across 17 families**, three deliberately
different silhouettes per family, not random scales or mirrored copies.

| Family group | Families and variants |
| --- | --- |
| Trees (12) | Broadleaf full/spreading/weathered; woodland paired/leaning/sparse; orchard red-fruit/gold-fruit/old; conifer spruce/fir/old-pine. |
| Shrubs and ground plants (15) | Rounded/irregular/twiggy shrubs; curled/splayed/upright ferns; sparse/splayed/dense decorative grass; white/yellow/violet flowers; clover/ivy/moss groundcover. |
| Waterside (9) | Cattail/splayed/dense tall reeds; upright/splayed/sparse rushes; white/yellow/iris flowering bank plants. |
| Natural accents (15) | Rounded/angular/mossy boulders and rock clusters; cut/weathered/hollow logs; cut/split/mossy stumps; branching/twisted/knotted exposed roots. |

New retained drawings supply every visible pixel. Technical processing removes
the magenta background, uniformly samples the cutout into its occupied envelope,
registers the root, assigns named palette roles and records a one-artwork-pixel
silhouette contour. Fine stems/blades retain their source color, with the contour
using canvas padding; broad tree/stone/wood edges register inward. It does not enlarge legacy artwork or invent new geometry
from the PNG alpha. Leaves use the current shared emerald ramp; bark and stone
reuse existing ramps. Birch cream, flower ivory/yellow/violet and orchard fruit
accents are explicit named palette additions. Keep light from the upper left.
No regional palette switch or seasonal gameplay behavior is implied.

Trees preserve the existing 96×120 logical / 192×240 artwork canvas and supporting
rectangle [36,96,24,24]. Their root anchor is [48,116] logical / [96,232] artwork;
most species occupy at most 92 logical units of height, with lower orchard crowns.
Shrubs and ordinary small plants use 24×24 logical / 48×48 artwork canvases. Tall
reeds retain 24×48 logical / 48×96 artwork, a [12,46] logical root, and fixed rows
from artwork y=88. New bank flowers use the same canvas with their own declared
root/support. Larger boulders, logs and roots have explicitly recorded canvases;
do not infer their physical size from the visible source drawing.

Each design records artwork/logical sizes, occupied rectangle, root/draw anchor,
supporting ground rectangle, depth baseline and suitable surfaces. The supporting
rectangle does **not** automatically define collision. Canopy size does not expand
the tree's gameplay footprint. Foreground plants and natural accents have thin dark
contours; ordinary scenery does not acquire discovery glints or interaction cues.

Thirty-six living designs have a nine-frame, 600 ms-per-frame breeze (5.4 seconds).
Fifteen rocks/deadwood/root accents are static. Trees export fixed trunks/roots,
source-derived canopy backing and disjoint leaf patches. Patches rustle by at most
one artwork pixel horizontally with delayed local phases; woody pixels, fruits,
roots and crown coverage stay fixed. Backing uses existing leaf-shadow colors.
The rest pose reconstructs the registered drawing exactly. Small plants use
rooted horizontal bending by at most one artwork pixel, leaving the declared
base rows unchanged. No whole-tree translation, vertical bob, recoloring pulse,
randomized frame noise or support drift is permitted. Reduced motion uses idle
files; pause/focus behavior must be preserved by the eventual runtime consumer.

Every design has an idle file, an animation sheet, explicit frame rectangles and
per-frame files; trees also retain fixed/backing/cluster layers. The common idle
atlas is 768×1200 artwork pixels with explicit nonoverlapping rectangles. Asset
paths are pack-relative; source recipe paths are repository-relative. Never derive
an anchor or density from atlas position or opaque bounds.

These decorative grass drawings are **not** installed as replacements for the
existing shared contact-responsive grass. That active bank and its walk/run
parting, occupied holds, recovery and party/NPC contact behavior remain unchanged.
Any later migration must explicitly preserve those behaviors; this pack does not
pretend to implement them through visual-only breeze frames.

```sh
python tools/build_world_vegetation_hd.py
python tools/build_world_vegetation_hd.py --check
PYTHONPATH=.:tests python -m unittest test_world_vegetation_hd
```

[Vegetation review evidence](reviews/world_vegetation_hd/README.md) includes all
families, animation boards, native Eldenmere/northern-woodland/wetland compositions
and a common-baseline comparison with approved Caelan/Iselin. Composition metadata
records roots, phase offsets, terrain and depth ordering. Static water isolates
vegetation movement in these offline fixtures. They are not gameplay captures or
map redesigns. Actual traversal, tree/actor occlusion, environmental lighting,
contact, collision and reduced-motion acceptance remain integration work.

### Integrated Elden Vale Sanctuary reserve

The [regional design guidance](world/regions/ELDEN_VALE.md) owns creative direction
for Elden Vale and the Sanctuary approach, including the integrated Pale Antlers
and future Rising Rain. The construction reference below owns the core native
scenes; explicit landmark bindings are documented in the later integration
sections, without promoting the staged weather assets.

`tools/build_sanctuary_reserve_hd.py` owns the reserve exterior and cave approach,
Sanctuary Hall and visitor relief room. Its retained master drawing, extraction
recipe and pre-migration maps live in `assets/source/maps/sanctuary_reserve_hd/`;
its current native registry is `assets/maps/sanctuary_reserve_hd/manifest.json`.
Rebuild with that command and use `--check` for deterministic verification.
The older reserve exterior/art, hall and relief CLI builders forward to it after
integration; they cannot restore the earlier assembled maps. Historical exports
and recipes remain evidence, not live art inputs or alternative construction rules.
In particular, the retired Caelan reference in the historical reserve pipeline
is not a dependency of the current build.

Existing logical dimensions, collision files, full player probe, footprints,
spawn/return landings, public approaches, doors, grove roots and NPC/story stations
are preserved. Every environment entity declares native 2× artwork and its old
logical canvas. The memorial tree retains independently sorted roots/trunk/canopy;
cloister arches retain their original opening coverage as geometry-only control.
No legacy RGB supplies the rebuilt landmark drawings. The retained cave opening
clearance clips decorative crystal layers; the keeper rail retains its gameplay
identity and removal lifecycle.

Ground uses the shared visible-chunk compositor, world-aligned native grass/dirt
and paving, native low flowers and bounded scene ground caches. Contact grass
keeps instance identities, roots, phases, contact/recovery rules and current HD
variants in a scene-local manifest. Interior walls, windows, medallions, furnishings
and the functional relief doorway share the same density contract. Wall lighting
stays steady. Basin highlights move locally; stone supports remain fixed.

Caretaker body drawings remain in their existing bank. Pails use scene-local
native replacements with unchanged grips/angles; water streams use the shared
render adapters. Grove petals declare their own 2× density and logical size.
Motes/petals participate in scenery depth; pause/focus freezes the exploration
clock and reduced motion holds the ambient effects and caretaker at rest.

Small repeatable inspections and the relief bed opt into the existing glint and
nearby-outline system. Their boundaries identify actual authored approach areas;
controller availability and ordinary scene/menu gates remain authoritative.
Buildings, characters, the grove and decorative cave crystals are not blanket
highlighted. See the visual standard for cue construction and lifecycle rules.

`python tools/capture_sanctuary_reserve_hd.py /tmp/reserve-review` captures an
initialized disposable exploration fixture, subsequent real walking/running and
door transfers, inspections, watering, relief rest offers and the actual arrival
story director. Review evidence and measured warm renderer timings are in
[the reserve review](reviews/sanctuary_reserve_hd/README.md).

Earlier crystal/grove source recipes are retained under
`assets/source/terrain/sanctuary_fantasy/`, with historical pack exports under
`assets/terrain/sanctuary_fantasy/`. Their former builders
`tools/build_sanctuary_crystals.py` and `tools/build_sanctuary_grove.py` describe
those earlier banks, not the current reserve composer. The
[earlier fantasy review](reviews/sanctuary_fantasy/README.md) retains travel,
landmark depth, map and reduced-motion evidence. Its annotated placement sheet
is an explanatory diagram. Earlier fingerprint checks belong to that historical
snapshot; use the maintained native owner above for current scene verification.

### Integrated Elden Vale regional foundation

`assets/maps/overworld/elden_vale/region.json` selects
`assets/maps/overworld/elden_vale/hd_integration/manifest.json` through the explicit
`hd_art_manifest` overlay, with `terrain_hd.enabled` selecting native material
composition. This registry is integrated; the original staged foundation bank
below retains its own metadata and remains a source, not the live selector.
Do not overwrite base/detail/composition banks to activate newer art.

`tools/build_elden_vale_hd_integration.py` preserves the regional canvases and
foot anchors while adapting selected HD vegetation and reusing foundation props.
All states of a vegetation donor share one union crop, scale and origin; roots
and fixed layers remain registered while authored leaves move. The registry
records source hashes, material aliases and animation frames. Source metadata and
layout recommendations live under
`assets/source/maps/overworld/elden_vale/hd_integration/`.

`regional_terrain_hd.py` applies shared emerald grass, dirt, paving, temperate
water and natural shore detail through existing logical masks. Paving and water
phases use signed global tile coordinates; agricultural row angles retain their
authored direction. Material boundaries do not widen paths or redefine water.
Animated water remains outside a restored bridge deck. Asset/mask helpers and
streamed render chunks use bounded caches, not enlarged whole-region images.
Reduced motion holds scenery and water to stable frames.

The live six-area layout records preserve current inhabited places and routes.
Causeway clearance follows existing stone road; an overhead antler envelope and
existing-solid candidate support IDs reserve later work without new blocking
ground. Neither these records nor the artwork activate signature ruins, the
Pale Antlers, Rising Rain or final atlas artwork.

Rebuild adapted bindings with `python tools/build_elden_vale_hd_integration.py`;
add `--check` for non-writing verification. The vector layout remains owned by
`tools/build_elden_vale_overworld.py`. Reproduce the gameplay review with
`python tools/capture_elden_vale_hd_integration.py /tmp/elden-vale-hd-review`.
[Current captures and scope](reviews/elden_vale_hd_integration/README.md) remain
separate from the offline source-pack studies below. Characters, wildlife, work
props and the separately owned Sanctuary miniature retain their existing owners.

### Staged Elden Vale regional HD foundation

`tools/build_elden_vale_hd_foundation.py` stages the regional foundation under
`assets/terrain/overworld/elden_vale/hd/art.json`. Its source recipe and replacement
inventory live under `assets/source/terrain/overworld/elden_vale/hd/`. The original
bank retains **not integrated** metadata and has no user visual approval yet.
Selected consumers are now integrated through the separate adapted registry
above. Existing controllers, collision and travel remain authoritative; the
original staged bank and legacy regional manifests are retained as sources.

The exporter samples retained original regional drawings directly at 2× artwork
density, preserving logical canvases and anchors. It resolves base/polish/composition
overrides, excludes obsolete wildlife/guards and the superseded narrow bridge,
and adds a one-artwork-pixel black exterior contour. Green-dominant pixels move
halfway toward the emerald hue; earth, stone and timber retain source colors.
The town miniature incorporates current HD inn/shop donors along its southern edge.

The bank references the existing grass/dirt, paving, water, masonry and waterworks
manifests without flattening their phase/connection metadata. Regional vegetation
exports cover all 51 existing HD designs: tree canvases are halved in logical size
for the miniature view; other plants retain their declared sizes. Complete frames,
idle artwork and available fixed/backing layers retain registration. This stages
breeze art, not contact-responsive grass behavior or new animal routines.

Crop rows have two orientations; seven material groups have three retained-master
crop treatments. These are fill/dressing candidates for coherent areas, not new
47-shape transitions. The active regional terrain painter supplies material
contacts; unused variants remain separate selections. Water retains the donor
pack's temporal frames, spatial phases and bank masks through explicit references.

Build with `python tools/build_elden_vale_hd_foundation.py`; verify without writing
with the same command plus `--check`. Focused contracts are covered by
`python -m unittest discover -s tests -p test_elden_vale_hd_foundation.py -v`.
[Review compositions](reviews/elden_vale_hd_foundation/README.md) are offline asset
studies, not gameplay captures. Their preliminary antler blockout remains source
history; the active design-layout records reserve future circulation and views.
Staged signature and weather packs below do not activate their Sanctuary icon,
remains, ruins, weather, action poses or atlas artwork in gameplay.

### Staged Elden Vale signature landscape

`tools/build_elden_vale_signature_landscape_hd.py` owns the staged Pale Antlers,
limestone ridge/dressing kit, causeway ruins and Sanctuary miniature. Sources,
generation brief, geometric layout plan and dependency hashes are retained in
`assets/source/terrain/overworld/elden_vale/signature_landscape_hd/`; exports are
registered by `assets/terrain/overworld/elden_vale/signature_landscape_hd/manifest.json`.
This original pack retains **not integrated** metadata and has not received user
visual approval. Selected remains, ridge dressing and miniature are now active
through explicit live bindings and the reserve/town builders; the staged manifest
is not the runtime registry.

One retained anatomy master supplies the registered skull/overhead layers and
cross-scale views. Distant views exclude the skull. Parts reconstruct the master
without gaps or duplicate pixels. Overhead pieces have no ground collision and
provide alpha masks for future visibility treatment. The layout plan checks the
proposed base against current solid ridge pixels and protected approaches/loop;
changed protected geometry/collision inputs require renewed review. The historical
full-map hash is evidence, not an active visual-build dependency. An explicit
`protected_geometry.json` snapshot preserves doors, approaches, loop, supports and
entry facts; `--record-visual-provenance` records generated map hashes separately
as review output, never as input to the staged pack or active map builders. World grounding and final
foreground behavior remain integration work, not an alpha-derived collision mask.

Sixteen ridge/dressing drawings and twelve causeway drawings provide handed ends,
corners, natural faces, contact dressing, fragments, decks, parapets, arch and
buried foundations. They are authored overlap modules rather than 47-shape blobs.
Reference runs declare matching connection ports, including a lower broken end.
The wide arch has independent lintel/support layers and an open 94-unit passage.
The 96×80 logical Sanctuary icon uses current hall/cave/memorial-tree donors; keep
the monumental antlers on separate layers and preserve existing entry contracts.

Build with `python tools/build_elden_vale_signature_landscape_hd.py`; add `--check`
to verify bytes without writing. Focused contracts live in
`tests/test_elden_vale_signature_landscape_hd.py`.
[Offline review evidence](reviews/elden_vale_signature_landscape_hd/README.md)
records source-based assets, scale studies, module connections and the clearance
plan. It does not certify gameplay integration, map release or new lore.

### Staged Elden Vale Rising Rain

`tools/build_elden_vale_rising_rain_hd.py` owns the third staged regional asset
pack. Sources, identity references, generation brief and recipe/hashes are under
`assets/source/terrain/overworld/elden_vale/rising_rain_hd/`; environment exports
are registered by `assets/terrain/overworld/elden_vale/rising_rain_hd/manifest.json`.
This bank is **not integrated** and has not received user visual approval.

Sixteen drawn water/atmosphere cells provide surface gathering/detachment, ascending
clusters, meadow curtains, canopy strands, high veils, wet accents and dedicated
reduced-motion stills. Exports retain hard masks; controlled whole-layer opacity
provides intentional atmosphere. Separate fixed posts and cloth panels/bundles,
ties, leaf states and basket support local-life staging. Ordinary props never
automatically receive discovery glints or yellow outlines.

The deterministic twelve-second review timeline illustrates the four phenomenon
phases. It does not establish live frequency, triggers, weather simulation,
resource collection or combat bonuses. Preview particle placement protects a
central travel/interaction band. Integration must implement authoritative event
eligibility, reliable first witnessing, clocks, scene cleanup, bounded rendering
and actual foreground visibility under normal and reduced motion.

The same builder stages right-facing action clips beside existing actor banks,
a bird bank beside regional wildlife, and 64×64 atlas icon candidates beside
cartography. Active selectors and maps stay unchanged. Those clips and icons do
not establish new NPC schedules, Liam's story location, animal routes or a map
forecast. Final atlas regeneration follows layout integration.

Build with `python tools/build_elden_vale_rising_rain_hd.py`; use `--check` to
verify bytes without writing. Focused contracts are in
`tests/test_elden_vale_rising_rain_hd.py`. See
[offline previews and limits](reviews/elden_vale_rising_rain_hd/README.md) and the
[actor export reference](VISUAL_ART_STANDARD.md#staged-rising-rain-actions-and-wildlife).


### Integrated Pale Antlers bindings

`tools/elden_vale_landmark_bindings.py` is the signature-schema adapter consumed
by `tools/build_elden_vale_hd_integration.py`. Its native regional segments, masks,
existing-foot ridge adaptations and miniature register in the live manifest.
Placements and contact safety remain owned by the regional source recipe. The
region builder, foundation metadata refresh, live bindings and reserve
builders reproduce in that order; Eldenmere has no antler binding; there is no generated reserve-map visual hash
in the staged signature dependency graph. Preserve the protected geometry and
collision checks and record visual provenance separately.

The reserve recipe's `pale_antlers` block owns its coherent dedicated rendition,
registration, named solid supports and essential limestone/strata/earth/root/ivy/
moss dressing. Detailed and regional lower contact fringe is embedded with an
explicit uneven contour while protecting bone anatomy, never used to generate
collision. Original staged exports and historical captures remain unchanged.
Production evidence is in [the gameplay review](reviews/elden_vale_pale_antlers/README.md).

The town owner also checks its dependent Caelan scene export. Source-inventory
paths are sorted canonically there so filesystem enumeration order cannot
invalidate provenance JSON on a fresh checkout. This integration changes only
that inventory ordering, not actor pixels, poses, dimensions or gameplay.


### Integrated old causeway and reused masonry

The regional recipe's explicit causeway props and placements extend the live
signature adapter, without modifying original setpiece geometry. The complete
arch is projected once and segmented into a native overhead lintel and ordinary
depth-sorted piers. Each physical support has a named source-owned footprint;
flat paving has none. Original deck ports join surviving short remnants off the
main travel surface, while a parapet/resting edge and sparse buried works show
inhabited reuse. These are authored assemblies, not a blob autotile system.

Rebuild the vector layout, refresh foundation provenance, then build/check live
HD bindings. Support validation covers both the reserved and smoothed centerline
and rejects corridor encroachment. Source artwork, original staged metadata and
historical reviews remain retained. No new scenery automatically glints.
