# Terrain art and pack creation standard

This is the single maintained reference for terrain creation and pack maintenance:
ground materials, transitions, vegetation, rocks, water, banks, elevation, stairs,
environmental accents, exports, integration and review. It replaces the former
grass guides and the grass/dirt, stream, irrigation, terrace, foliage, flower and reed pack
READMEs. Existing recipes and manifests retain machine-readable implementation
facts; historical review reports record earlier work rather than prescribe new
construction methods.

The [global visual standard](VISUAL_ART_STANDARD.md) owns project-wide appearance,
units and rendering. This document applies those rules to the complete terrain
workflow. Building art follows the global standard; terrain and buildings share
scale, perspective, lighting and compatible contact edges. For manipulable objects,
also follow the [interaction standard](OBJECT_INTERACTION_STANDARD.md) and
[personal-prop visibility](PERSONAL_PROPS.md).

**Status:** The new Eldenmere grass/dirt and stone-paving packs are **rebuilt but
not integrated**. Their 48×48 artwork tiles retain a 24×24 logical footprint.
The shipped town and shared terrain retain previous assets until a separate
integration change. See the [grass/dirt reference](#staged-eldenmere-hd-grassdirt-blob)
and [stone-paving reference](#staged-eldenmere-hd-stone-paving).

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

Grass/dirt and stone paving are available as staged asset packs below. Terraces,
water/banks and larger vegetation follow as coordinated families. Runtime migration
and in-game acceptance remain a separate step.

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
State is `rebuilt` / `not_integrated`; user visual approval is recorded separately.
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
State is `rebuilt` / `not_integrated`, with user visual approval recorded separately.
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
