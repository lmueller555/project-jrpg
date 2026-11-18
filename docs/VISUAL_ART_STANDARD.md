# Visual art standard

This is the authoritative guide for the game's visual style, asset sizing,
rendering contract, character construction, animation, export and review. It
covers characters, wildlife, terrain, architecture, props, combat art, effects,
backgrounds, portraits and interface artwork. Read the relevant sections before
creating or revising artwork, asset builders, renderers or their tests. The
character workflow below preserves the lessons from Iselin's four approved walks;
running extends them with coupled support, recovery and flight poses.

The [World and Environment Design Standard](WORLD_DESIGN_STANDARD.md) owns the
shared creative process for place identity, environmental storytelling,
exploration and the region/zone design brief. Use it when designing a place;
this guide retains appearance, sizing, rendering and asset/animation construction.
Approved regional lore and revelation limits remain authoritative.

**Approved direction:** Rebuild game artwork at two artwork pixels per logical
world pixel, preserving its existing on-screen proportions and world footprint.
Iselin's detailed artwork is the reference for this increase in fidelity.

**Implementation status:** Full-scene 2× composition is implemented in
`rendering.py`. The 480×320 logical view has an authoritative 960×640 native
buffer across exploration, battle and cinematic presentation. Existing asset
banks retain their legacy density until rebuilt; Iselin's detailed artwork, Caelan's approved overworld idles/walks/runs,
Caelan’s rebuilt household, carrying, quest-work, casting and cave-assistance poses,
all three Sanctuary home interiors (hall, bedroom and dining room), and
the complete Eldenmere town, remaining town interiors, southern inn/shop and
upstream scene, Elden Vale Sanctuary reserve/cave approach, Sanctuary Hall,
visitor relief room and the selected Elden Vale regional terrain/scenery foundation
now use the shared path. Dining was the first integrated environment bank; remaining
asset reconstruction and individual bank migrations continue as separately scoped work.

This standard replaces conflicting general advice in older character recipes,
tool descriptions and review notes. Those files retain asset-specific facts,
commands and historical evidence; they do not prescribe new construction methods.
Existing approvals remain evidence of the original assets. Migration proceeds
in explicitly scoped work; new artwork and runtime activation have separate
statuses. Apply these rules to the work being requested. Explicit user direction
takes precedence.

For actions involving objects, also follow the
[character–object interaction standard](OBJECT_INTERACTION_STANDARD.md) for
staging, ownership, transfer cues and lifecycle, and
[personal-prop visibility](PERSONAL_PROPS.md) for equipment visibility. This guide
owns appearance, sizing, rendering and motion quality; those companions own
interaction behavior, ownership and prop visibility. A walk's limb amplitudes
and timing are not rules for every combat pose.
The limb examples below describe a biped. For creatures with different anatomy,
plan their actual limb chains, support pattern and silhouette rather than forcing
a human two-arm/two-leg gait onto them.

Terrain creation and pack maintenance are documented together in the
[terrain art and pack creation standard](TERRAIN_ART_STANDARD.md). Use it for
materials, 47-tile blobs, vegetation, water, elevation, terrain exports and
integration. This document retains the shared project-wide visual/rendering
contract; terrain-specific authoring instructions belong in that companion.

## Navigation

- [Terrain creation and pack maintenance](TERRAIN_ART_STANDARD.md)
- [Visual direction](#visual-direction)
- [Object creation and interaction readability](#object-creation-and-interaction-readability)
- [Staged Eldenmere building exteriors](#staged-eldenmere-hd-building-exteriors)
- [Staged inns and item shops](#staged-eldenmere-inns-and-item-shops)
- [Units and sizing](#units-and-sizing)
- [Rendering contract](#rendering-contract)
- [Migration and acceptance](#migration-and-acceptance)
- [Character and animation working order](#working-order)
- [Character design and Iselin's registration example](#1-establish-the-character-before-animating)
- [Gait planning](#2-plan-the-gait-before-drawing-in-betweens),
  [complete drawings](#3-draw-complete-coherent-frames),
  [feet](#4-make-feet-progress-continuously) and
  [body registration](#5-register-the-body-author-the-bob)
- [Running animations](#running-animations): limb coupling, support/flight, phase plan,
  posture, registration and run-specific acceptance
- [Corrections](#6-correct-one-defect-while-protecting-accepted-work),
  [exports](#7-export-reproducibly), [review](#8-review-at-three-levels-before-declaring-completion)
  and [diagnosis](#9-diagnose-before-regenerating)

## Visual direction

Use Iselin's clear silhouettes, readable dark contours, coherent material shading
and fine costume detail as the fidelity reference. Preserve each character's
approved appearance, anatomical costume sides and relative height. Her 42×72
canvas is a character-specific example, not a frame size for the whole cast.

Author additional detail at the target density. Enlarging old pixels alone is
a compatibility treatment, not a completed visual rebuild. Retained larger
masters may supply suitable detail after proportion, palette and motion review.
Keep pixel clusters deliberate and use consistent outline weight within each
asset family. Ground materials need coherent edges and quiet transitions;
characters and foreground objects need readable separation. Avoid giving every
floor tile a character-style black border or filling every surface with noise.

| Asset family | Visual requirements |
| --- | --- |
| Characters and wildlife | Preserve identity, physical proportions, near/far anatomy and costume asymmetry across travel, actions and scene poses. Use the complete-drawing workflow below. |
| Terrain and vegetation | Preserve logical tile coverage, seamless material transitions and grounded roots/banks. Keep paths and interactables legible; foliage density and motion must support the scene's composition. |
| Buildings and interiors | Preserve established scale, perspective, door clearance, floor envelopes and furnishing relationships. Coordinate exteriors, interiors, cutaways and foreground occlusion. |
| Props and equipment | Match their users' scale and materials. Keep grip, hinge, support and attachment points explicit, including directional carrying and placed states. |
| Combat art and effects | Preserve established displayed size, silhouettes, action readability and impact cues. Coordinate projectiles, shadows and effects with the actors and scene camera. |
| Cinematics and backgrounds | Preserve character identity and environment scale through every used camera view. Declare scene-specific projection and density rather than inferring scale from the PNG canvas. |
| Portraits and interface artwork | Preserve character identity and existing layout slots. Record their display/layout sizing separately from world coordinates; text retains display-resolution rasterization. |

Maintain coherent palettes and material shading across related assets and their
animation frames. Regional colors and individual costume palettes retain their
identity. Keep lighting direction and shadow treatment consistent within a scene;
test characters and props against both light and dark backgrounds. Coordinate
painted highlights with dynamic lighting so characters, scenery and effects
belong to the same environment.

## Orthogonal exploration architecture

Ordinary Eldenmere exploration uses a consistent orthogonal, top-down JRPG
projection. Ground surfaces follow the map's horizontal and vertical axes.
Vertical height rises above an explicitly declared ground footprint; a visible
front wall must agree with its declared occupied ground and visual supports.
For Eldenmere, a roof's screen-space rise is an authored silhouette measurement,
not a projection of its collision-ground depth: do not require roof-image height
to equal or exceed footprint depth. The restored low historic roof proportions
below supersede that former constraint, including tests that enforced it.
Roofs, decks, porches and steps expose compatible upper surfaces. Flat bridge
decks read as walkable ground planes, not frontal illustrations of platforms.
Do not add strong perspective convergence or an implied distant horizon.
Off-scene objects do not become skyline scenery merely because they are nearby
in regional geography. Eldenmere contains no Pale Antlers, antler shadow or
replacement silhouette; regional and detailed Sanctuary bindings remain separate.

The technical per-building and crossing schedule lives with the existing town
recipe at `assets/source/maps/eldenmere/town_hd/architecture_schedule.json`.
It owns all 13 building canvases, physical ground, depth baselines, thresholds,
approaches, floors/circulation, hearth/flue registration, protected fixtures and
crossing interfaces. Keep those facts in that schedule rather than duplicating
an art guide. Author revised geometry to its intended proportions; do not stretch
facade strips independently to repair a mismatched source portal. Explicit reviewed
pane masks own window light. Roof, masonry, structural timber and merchandise
remain outside those masks, and solid structure is identical with reduced motion.
The [labelled construction reference](reviews/eldenmere_architecture_contracts/projection_reference.png)
shows the ground grid and Caelan at 2× scale; it is not gameplay evidence.

## Object creation and interaction readability

Create ordinary and special objects in the same visual style. All distinct
objects use thin black exterior contours, starting at **one artwork/render
pixel at 2× density**. Preserve those black pixels when highlighting an object.
Use restrained internal lines and material shading; quiet floor/plaster textures
do not need a black box around every repeated tile. A highlight never substitutes
for a recognizable silhouette, sensible support, accessible placement or clear
quest directions.

Before drawing a prop, record its logical canvas, occupied silhouette, supporting
surface/ground anchor, depth baseline, interaction boundary and any grip/hinge
points. Preserve physical scale when fitting retained high-resolution sources.
Export hard-alpha artwork with room for its contour; avoid opaque background
rectangles, soft generation halos and silhouette clipping. Register all animated
states to the same support: fireplace masonry, furniture legs and containers
stay still while only the intended flame, vapor, hinge or contents change.
Keep source artwork, extraction/registration recipe and density metadata together.

### Distinguishing special objects

Use this shared language for collectibles, examinable objects and objects tied
to a currently available objective/action:

- **Distant discovery:** one small, brief glint every **3–5 seconds**. Stagger
  timing deterministically by cue ID so a room does not flash together. The
  current glint lasts 0.28 seconds and spans seven render pixels; author its
  anchor on a readable part of the object's actual surface.
- **Nearby confirmation:** a steady, thin yellow silhouette outline **outside
  the black contour**, starting at **one render pixel** (`#f4d35c`). Activate
  within **10 logical world units** of the player's feet to the nearest point
  on the authored interaction boundary. Use Euclidean distance at corners.
  Fade over 0.12 seconds and retain proximity until the player moves beyond
  **12 units**, preventing threshold flicker. Do not pulse the whole object.
- **Action:** the existing interaction prompt confirms what can be done and
  retains the handler's positioning/facing requirements. A yellow outline
  advertises an eligible nearby object, not guaranteed permission to activate it.
- **Lifecycle:** remove both cues when the action is exhausted, unavailable or
  no longer relevant. Reconstruct eligibility from authoritative gameplay state
  after loading; presentation must never award progress. Clear proximity on
  scene exit and suppress cues during dialogue, cutscenes and menus. Pause/focus
  loss freezes cue time without catchup. Reduced motion uses a small static
  discovery marker and the same steady proximity outline.

Use actual object/support boundaries, not sprite centers or transparent canvas
padding. A tabletop object's boundary can describe its supporting table's
reachable edge; record that choice explicitly. Check collision and line of
approach so highlights do not advertise an object through a wall. Render both
cues at the object's normal depth, allowing characters, furniture and foregrounds
to obscure them. Never draw them as a final always-visible screen overlay.

Ordinary doors, chairs and decoration do not automatically glint or turn yellow.
Opt in only while a real special interaction is available. Supplies handed over
through dialogue must not look like independently collectible items. Use staging,
dialogue and objective text for people and large destinations instead of sparkling
entire characters/buildings. Essential progression must remain understandable
without noticing a tiny glint or distinguishing yellow alone.

The runtime reference is `object_cues.ObjectCues`. A world map opts in with:

```json
"interaction_cues": [{
  "id": "breakfast",
  "entity": "breakfast",
  "available_when": "opening_breakfast",
  "interaction_boundary": [144, 192, 48, 18],
  "glint_anchor": [14, 5]
}]
```

Boundary coordinates are logical world `[x,y,width,height]`; the glint anchor is
logical and local to the entity's image origin. `available_when` names an explicit
gameplay resolver, not an expression to evaluate or an automatic quest reward.
Sanctuary dining first integrates `opening_breakfast` while joining breakfast
is an available opening interaction. Its boundary is the table's support edge.
New special-object integrations must add their real availability resolver and
verify completion, interruption and save restoration rather than marking every
quest-adjacent decoration eligible.

Repeatable inspections remain eligible after their dialogue closes; they are
not exhausted actions. The bedroom inspection resolvers retain the existing
opening-stage gates and repeatable dialogue behavior. Do not invent quest
receipts or change save progress solely to silence a discovery cue.

Review an unhighlighted object, a distant glint, a nearby outline, an occluded
object and a completed/inactive state at normal game size. Check light/dark
surroundings, reduced motion and the final display scaling. The
[object-interaction standard](OBJECT_INTERACTION_STANDARD.md#discovery-cues-and-action-availability)
governs action availability and cleanup; this section owns object construction
and the visible cue treatment.

## Units and sizing

Every measurement must declare its coordinate space:

- **Logical world units:** map positions, tile footprints, camera coverage,
  collision probes, navigation, interaction distances and depth-sort baselines.
  Existing documentation's world pixels refer to these units.
- **Artwork pixels:** texels in an exported drawing, atlas cell or texture.
  The standard density is **2 artwork pixels per logical world unit** on each axis.
- **Render pixels:** pixels in the scene's composition target. The
  standard world target is **960×640** for the existing **480×320 logical view**.
- **Display pixels:** pixels in the actual window or embedded viewport after
  presentation. Interface text is rasterized in this space.

| Asset | Logical frame/footprint | Exported artwork at 2× |
| --- | --- | --- |
| Terrain tile | 24×24 | 48×48 |
| Existing Caelan-sized character canvas | 24×36 | 48×72 |
| Mira's wider canvas | 32×36 | 64×72 |
| Iselin's approved canvas | 21×36 | 42×72 |

Character canvas dimensions include transparent padding; they are not the
visible body height or collision footprint. Larger props and action canvases
follow the same density rule while retaining their own logical dimensions.
Regional overworld miniatures, combat staging and cinematic cameras retain
their established scales. Derive a bank's logical footprint from its actual
runtime presentation before rebuilding it; raw PNG dimensions alone cannot
establish how large it appears in those views.

For a world asset at density `d`, artwork dimensions and artwork-space anchors
are `d ×` their logical equivalents. Keep draw, foot/ground and interaction
anchors distinct. Iselin's draw anchor is `[21,60]` in artwork pixels and
`[10.5,30]` in world units; her foot anchor is `[21,68]` / `[10.5,34]`.
Her collision probe remains 8×4 world units. Fractional logical anchors are valid;
round at the rendering boundary consistently rather than truncating metadata.

The artwork migration preserves gameplay positions, collision, movement speeds,
interaction reach, scene transitions, camera coverage and physical proportions.
Collision and navigation masks remain logical data, independently registered
from image alpha. A revised silhouette does not automatically redefine them.
Body-spacing and hand-contact ranges in the interaction standard remain logical
world measurements; a 4-unit gap spans 8 artwork pixels at 2× density.

## Rendering contract

This section defines the shared rendering contract. Current runtime APIs and
asset metadata conventions are described below.

Preserve the 480×320 logical camera view while composing its world art at
960×640. Project logical positions and the camera into render space once.
For a simple unrotated 2× asset, placement is
`render_position = 2 × (world_position - camera_position) - artwork_draw_anchor`.
An explicit scene zoom/projection may extend that transform. Keep simulation,
depth ordering and interaction calculations in their established logical space.

Keep new artwork at its authored density throughout world composition. Drawing
it into a 480×320 fallback and enlarging the result discards its additional
detail. Compatibility drawing of legacy art may upscale it at its existing
logical size, with its migration status still recorded as legacy.

All participating paths must honor the same coordinate contract: the player,
companions, ambient routines, objects, doors, ground layers, grass, water,
foregrounds, shadows, cave lighting and effects. Preserve depth and alpha through
their ordered passes. Any deliberately lower-resolution light/effect field needs
an explicit transform and an in-scene quality check. Combat, cutscenes, Gallery,
playtests, transitions and frame snapshots must preserve the appropriate detail
before display-resolution UI is drawn. A single upgraded actor path does not
establish whole-game support.

Present pixel artwork with nearest-neighbor sampling. Use integer display
scaling when it fits; retain fitting/letterboxing behavior for embedded or
non-integer windows and inspect fractional-scale artifacts. At a 960×640 scene
viewport, the standard render target can display at 1:1. At a 480×320 viewport,
detail must be reduced: record that presentation limit rather than claiming
all source pixels remain visible. Existing small-window support remains in place
unless a separate implementation explicitly changes it. UI layout, text sizing
and input mapping must keep working across these presentation sizes.

Asset records and exporters must explicitly record the following contract.
The current runtime follows the loader conventions below.

| Record | Units / purpose |
| --- | --- |
| Artwork dimensions and density | Exported pixel dimensions and artwork pixels per logical unit. |
| Logical canvas/footprint | Expected world-space size, including intentional padding. |
| Draw and foot/ground anchors | Named coordinate space and conversion; preserve existing registration. |
| Attachment points and depth baseline | Grip, hinge, support and sorting coordinates with declared units. |
| Animation | Frame order, per-frame timing, loop behavior and action/impact cues. |
| Provenance and state | Sources, extraction/registration recipe, hashes, design approval and runtime migration status. |

Record source density and target density when they differ. Export uniformly,
preserving physical proportions. Builders must distinguish art dimensions from
logical masks and gameplay coordinates, and keep checking existing preservation
contracts intentionally rather than silently repinning historical hashes.

Doubling both artwork dimensions multiplies uncompressed surface storage by
four. Use bounded caches, visible chunks and reusable assets; avoid retaining
entire enlarged world images or rebuilding scaled frames on every draw. Profile
representative populated scenes, animated terrain, cave lighting and battles.
Set concrete memory/frame-time budgets during renderer implementation and record
the measured results; this documentation does not assert an unmeasured budget.

### Runtime APIs and metadata

`rendering.WorldCanvas` is a logical-coordinate Surface with two buffers:
its ordinary Surface storage is a compatibility mirror for geometry, sampling
and existing logical checks; `native` is the authoritative full-scene 2× buffer.
`get_size()`, rectangles and clips remain logical. `native.get_size()` returns
render dimensions. The mirror is never enlarged to reconstruct the displayed
scene. `dense_art.draw_actor` adapts the existing detailed-actor provider to
this shared compositor; there are no patch lists or pixel-repair scans.

Use the explicit `rendering.draw` primitive adapters, `scale`, `flip` and
`rotate` for world drawing and intermediate transforms. Bare Pygame drawing or
array writes on the logical Surface do not update its native buffer. Pixel
shaders must explicitly synchronize the compatibility mirror and native result.
Scene blur and rune projection preserve native detail. Legacy cinematic scenery
keeps its existing sampling grid until rebuilt, then enters the native scene as
a legacy background; later actors and effects retain their own density. Aerial
landscape manifest/plane records declare `artwork_pixels_per_world_pixel: 2` to
select native projection. Ice Reaper continuity scenery declares that field in
`assets/story/ice_reaper_continuity/environment/art.json` to select native
sky/ground sampling. These are explicit migration switches, not filename or
image-size heuristics. Native shader results supply their logical mirror;
the displayed scene is not reconstructed from that mirror.
The cave illumination field intentionally retains its logical sampling grid and
is applied to the native scene as a multiplicative light pass; crystal emission
masks preserve their declared source density.

- `present(scene, display_surface)` presents the native scene once before UI.
  Plain display/UI surfaces retain ordinary Pygame behavior.
- `scale(scene, logical_size)` returns a logical intermediate with its native
  buffer preserved. Pass an explicit ordinary destination for final display
  scaling; drawing an intermediate through an ordinary Surface's bare `blit`
  would consume its logical mirror.
- `snapshot(scene)` returns an independent, ordinary render-pixel Surface.
  `WorldCanvas.copy()` and `subsurface()` preserve both initialized buffers;
  transitions can retain that logical/native registration safely.
- `record_art(image, record)` normalizes declared artwork density.
  `World.art_image()` and `load_art()` apply that contract at bank boundaries.
  `World.image()` retains original image pixels for masks and source processing.
- `project_art(source, logical_size)` samples retained authored sources directly
  into both grids for cached projected poses. It preserves the logical sampling
  while retaining the source detail available to the native view.

The shared density field is `artwork_pixels_per_world_pixel`; omission means
legacy density 1, while rebuilt assets explicitly declare 2. `logical_size` is
an optional validation of the normalized dimensions. Exported 2× frame dimensions
must be divisible by two; pad small assets transparently as needed. Invalid
density, divisibility or declared logical size fails explicitly.

| Loader | Metadata units and inheritance |
| --- | --- |
| World ground/entities/foregrounds/doors | Map, entity and frame records may declare density; entity/frame overrides take precedence. Map/world positions, draw anchors, logical size and collision data remain logical. |
| Player and routine NPCs | Bank or gait/action records declare density. Existing world draw anchors, action canvases, body offsets, approach and prop positions remain logical; source atlas rectangles remain artwork pixels. |
| Story actor sheets | Sheet rectangles remain artwork pixels. Density normalizes the extracted frames; the actor record's world draw anchor remains logical. Existing detailed-provider manifests retain their explicit artwork anchors. |
| Combat and cinematic actor banks | Bank `canvas` and `anchor`, plus frame-local body anchors, describe artwork pixels. Loaders validate raw frames then normalize into logical frames/anchors. Timing and scene positions remain unchanged. |
| Cinematic backgrounds and cave battlefields | Layer/bank records declare density. Scene layout `canvas`/`size`, camera paths and geographic bounds remain logical. |
| Portraits and display-space UI | Existing layout slots determine displayed size. World-density conversion is not applied to display-coordinate layout or text. |

Immutable legacy assets use a shared 32 MiB transformed-image budget. Large
backgrounds are cropped to the visible region before compatibility enlargement.
Legacy-only overworld terrain chunks retain their original cached density.
Installing declared 2× tile art selects native chunk composition. The existing
64 MiB render budget counts both buffers for those chunks, so its LRU holds
fewer enlarged chunks rather than exceeding the byte limit. Projected
cinematic/body caches use 64 MiB byte limits per bank; oversized images are
transient. Ordinary collision caches retain logical resolution. Use
`python tools/profile_renderer.py --frames 30` for a temporary-save production
draw benchmark; optional `--capture` is intended for requested or private review.
Warm draw timings exclude simulation updates and are hardware-specific.

## Migration and acceptance

Maintain each asset family's implementation facts in its existing local guide
and source metadata. Track **legacy**, **rebuilt but not integrated**, and
**integrated** independently of design approval or merge status. The standard's
adoption leaves those facts intact; historical 24×24 and 24×36 exports remain
accurate descriptions of those original files.

For each scoped migration:

1. Inventory the canonical asset bank and its consumers, including action,
   carrying, seated, combat and cinematic variants. Separate masters, runtime
   frames, generated variations and historical review files.
2. Record the existing logical footprint, anchors, collision/navigation data,
   timing, displayed size and reference scene before rebuilding.
3. Reuse adequate retained masters or author detailed replacements under this
   standard. Preserve original sources and identify the current revision.
4. Export density-aware art and metadata; integrate every affected consumer
   while preserving its gameplay registration, action cues and object ownership.
5. Check actual scene scale, alpha, outline/material consistency, tile seams,
   foreground overlap, lighting and interaction readability. Verify normal and
   reduced-motion presentation at relevant window sizes and camera views.
6. Verify reproducible exports, unchanged intended gameplay geometry and
   applicable lifecycle behavior. Record performance and known limits, update
   the local migration status, and follow the user's requested review boundary.

Use the existing character/animation review levels below for moving bodies.
Frame counts and animation timing remain separate from artwork density: a 2×
rebuild does not automatically impose sixteen-frame walks or retime all NPCs.
Preserve historical captures and local recipes as evidence, with links to this
guide for current construction rules. The interaction and personal-prop guides
continue to own their behavioral requirements.

## Working order

1. Inspect the approved art and runtime format; record design, sides, density,
   anchors, body landmarks, frame budget and cycle duration.
2. Establish directional idles and inspect them at cast scale.
3. Draw contact/passing keys for one direction and inspect all limb paths before
   spending effort on transitions. A readable profile is useful for diagnosing
   near/far movement; the requested direction still determines the work scope.
4. Draw small batches of in-betweens against those keys and the same proportion
   reference. Export and inspect each batch at native resolution.
5. Assemble chronological poses, register by body landmarks, and inspect both
   half-cycles, batch joins and the loop seam. Correct the diagnosed defect.
6. Produce normal/slow previews and a numbered sheet; run the appropriate checks.
7. Carry the successful gait to other directions with their own approved
   appearance and occlusion. Check the complete directional set together.
8. Record the current revision, review outcome and requested merge boundary.
   Validate actual travel when runtime integration is part of the task.

Do not generate a larger batch to compensate for failing key poses. These are
internal quality checks, not extra user approval steps; ask for review at the
boundary the user requested.

## 1. Establish the character before animating

Use approved appearance references, not a fresh interpretation in every frame.
Create a character sheet or source recipe containing:

- The approved design, palette, silhouette and front/left/right/rear idles.
- Head width and height, neck length, shoulder width, torso length, waist,
  coat/garment length and limb proportions. Record stable landmarks in artwork
  coordinates, with a side-by-side comparison against the existing cast.
- Hair construction, face features and each asymmetric costume element, named
  by **anatomical left/right**, not just the side of the image.
- Frame dimensions, artwork density, logical world size, draw and ground
  anchors, collision footprint, frame budget and intended playback cadence.
- Source paths, generation/edit instructions, approval scope and export recipe.

Match the cast's pixel-art style: a readable dark/black exterior outline,
consistent outline weight, coherent material shading and clear gaps between
limbs. Keep small faces and costume details readable against bright and dark
scenery. Do not outline every internal feature with equally heavy black lines.
Check outline continuity through motion; a good idle does not guarantee a good
walking silhouette. Keep a consistent palette rather than changing hair, skin,
clothing or outline colors between frames.

Build all required directional idles before their walks. Each direction needs a
specific appearance reference. Profiles must retain the face, coat, mantle and
hair detail instead of becoming reduced-detail silhouettes.

### Artwork pixels, world pixels and display pixels

These are separate units. Record which unit every measurement uses. More source
pixels do not require a taller character, a larger collision box or a larger
world-space stride.

Iselin is a worked example, not a universal size requirement:

| Property | Approved Iselin value |
| --- | --- |
| Exported artwork frame | 42×72 RGBA |
| Artwork density | 2 artwork pixels per world pixel |
| Logical frame | 21×36 world pixels |
| Draw anchor | [21,60] artwork / [10.5,30] world |
| Ground/foot anchor | [21,68] artwork / [10.5,34] world |
| Collision probe | 8×4 world pixels |
| Walk | 16 frames × 35 ms = 560 ms per full two-step cycle |

The established detailed renderer preserves higher-resolution idle and walk
artwork at ordinary party scale. Resizing it to the logical fallback discards detail;
enlarging that fallback later cannot recover it. Validate the intended rendering
path and target window scale. Iselin's walk manifests are registered on her
reusable actor and the regent's opening/MQ03 scenes. Cinematic and seated
poses have separate complete drawings and preserve the same character design.

## 2. Plan the gait before drawing in-betweens

A full walking cycle contains two steps and returns to the same limb phase.
Choose frame count and total duration together. Extra frames subdivide movement;
they do not automatically make the walk slower or smoother. Iselin's 16×35 ms
cycle and older 4×140 ms cycles both last 560 ms. Existing approved cadences
remain character-specific; do not silently retime the cast.

Draw and inspect contact and passing keys first. Add down/recoil and up/recovery
poses, then intermediate drawings. This is a useful 16-frame planning template;
the actual approved motion, rather than the file number, determines each phase:

| Frame | Phase | Main action |
| --- | --- | --- |
| 1 | Right-foot contact | Right leg leads, left arm leads; opposite limbs trail. |
| 3 | Down/recoil | Weight settles onto the right support leg; left foot releases. |
| 5 | Passing | Left swing leg passes the support leg; both arms pass through their middle range. |
| 7 | Up/recovery | Left foot approaches its next contact; right foot finishes support. |
| 9 | Left-foot contact | Left leg leads, right arm leads; identities exchange. |
| 11 | Down/recoil | Weight settles onto the left support leg; right foot releases. |
| 13 | Passing | Right swing leg passes the support leg. |
| 15 | Up/recovery | Right foot approaches contact; left foot finishes support. |
| 16 → 1 | Loop seam | Continue into contact without a pose reset or repeated endpoint. |

Even-numbered frames bridge these keys. Do not fill them with almost identical
extended-leg poses and then jump to the next phase. Do not assume an image
generator's column order is a valid chronological cycle: inspect and label it.

### Arm and leg coupling

Each arm counters the **same-side leg**: left arm forward with left leg back,
and right arm back with right leg forward; reverse together on the next step.
Thus left arm and right leg move forward together. Track all four limbs by
anatomical identity throughout the cycle, including when hidden.

The desired expressive swing can approach roughly 45° forward and backward
in the sagittal plane, relative to a relaxed vertical limb. Treat that as an
art-direction target, not a requirement to draw straight limbs or force every
projected angle to 45°. Bend knees and elbows naturally. Front/rear views
foreshorten this motion in depth; they must not kick sideways to imitate a
profile's screen-space reach. Shorter foot reach is preferable to an exaggerated
kick followed by a landing snap. Natural anatomy takes priority over a numeric
angle, exact contact coordinate or old test.

## 3. Draw complete, coherent frames

For new or revised walks and runs, author each pose as a complete character drawing with
its near/far overlaps resolved. Export flattened RGBA frames. Do not manufacture
the cycle by rotating, sliding or stretching detached arms and legs around an
unchanging body, or by warping a flattened idle. Adding more frames to a limb
rig does not fix parked far limbs, duplicate hands or incorrect anatomy.

Use one approved proportion reference and the same landmark grid for every
strip. Small batches of complete drawings can help control motion, but every
batch must use the same body scale and phase plan. Review batch boundaries as
carefully as transitions within a strip. Pixel interpolation, cross-fading and
duplicate poses are not substitutes for drawn in-betweens.

### Reusable drawing/edit brief

Supply the actual reference images and a short phase table with the request.
Replace the bracketed fields; vague requests for a "smooth walk" leave too much
unspecified. For a repair, include adjacent good frames, not just the bad extreme.

> Draw [count] complete [direction]-facing character poses in [layout], in the
> phase order [listed contacts, passing poses and transitions]. Use [approved
> directional idle] for appearance and [approved keys] for gait. Preserve
> [head/neck/torso proportions and landmark grid], [anatomical costume sides],
> [palette and outline style]. Track each near/far arm and leg through the
> listed phases with natural occlusion. Keep [frame size/density] and
> [crown/neck/belt reference positions]. Draw [specified foot progression],
> without a held extreme followed by a reset. Use complete unified drawings,
> transparent background and clear cell separation. No extra limbs, sideways
> depth kicks, changing body scale or detached old pose pixels. For this repair,
> change [specific defect and frames] and preserve [accepted region/motion].

Keep image generation responsible for authored redraws; technical export handles
crop, alpha, uniform sampling, registration and documented pixel preservation.
Do not hide a new procedural anatomy/limb generator inside the exporter.

### Near/far limbs and occlusion

Inspect the near arm, far arm, near leg and far leg separately. Both pairs must
advance through the gait; animating only the camera-facing side is insufficient.
Trace shoulder → elbow → hand and hip → knee → ankle for each pose. There must
be exactly one anatomical chain for each limb, with coherent attachment points.

A far hand or leg can legitimately disappear behind the torso, coat or near
limb. Record the hidden phase and make its next appearance consistent with the
continuing swing. Do not draw it through the body to prove it is moving. Remove
the original idle hand/arm when redrawing its pose: leaving both is how a third
arm appears. Likewise, remove obsolete boots, coat fragments and outlines.

### Direction changes and asymmetry

| View | Anatomical left appears on | Anatomical right appears on |
| --- | --- | --- |
| Front | Viewer right | Viewer left |
| Rear | Viewer left | Viewer right |
| Left-facing profile | Near side | Far side |
| Right-facing profile | Far side | Near side |

An approved opposite-side gait may supply reflected **motion guides**. Redraw
the new direction's face, clothing and hair from its approved idle; do not flip
the finished asymmetric costume and call it complete. Document any deliberate
reuse of already approved pose pixels. Iselin's left walk preserves reflected
approved lower-leg movement while using new left-specific upper artwork.

For Iselin, the mantle is on anatomical right and the braid runs forward over
anatomical left. Her rear view shows the braid root/bend, not a newly invented
central ponytail. Keep hairstyle identity intact while adding sway.

Hair, braid tails, mantle and coat may lag the body motion slightly. Draw modest
secondary motion that follows the gait and loops smoothly. Avoid abrupt hair
length, volume or silhouette changes that read as character redesigns.

## 4. Make feet progress continuously

Separate **stance** from **swing**. During stance, the support foot progresses
backward relative to the travelling body. During swing, the other foot lifts,
passes, reaches and settles into contact. Use a consistent toe/heel landmark;
a bounding-box center can jump when the boot rotates without the foot actually
moving that far.

Inspect each leg over an entire half-cycle and through the handoff. Watch for:

- An extended foot wiggling in place for several frames, then teleporting behind.
- Excessive lift or reach immediately followed by a drop into contact.
- Abrupt reversals, horizontal track changes, flashing soles or foot identity swaps.
- Both legs becoming static while the arms continue, or changing direction at
  unrelated times. Allow natural double support during walking.

Record foot contact/release phases and per-frame landmarks. Compare neighboring
displacements and loop-seam displacement; inspect sudden outliers visually.
Ease the approach to contact and draw the missing passing/recovery poses instead
of reordering unrelated extremes or shortening a frame to hide a snap.

Iselin's rear boot once dropped about nine artwork pixels from frame 4 to 5.
The correction reduced lift and divided the return into smaller drawn changes;
the accepted revision has no adjacent vertical change above three artwork pixels.
That is a regression bound for this asset, not a universal speed limit. Front/rear
screen-space boot height also represents depth, so measure the intended motion.

An in-place preview does not prove world-ground foot locking. When integrating
travel, compare stance-foot motion against actor displacement at the intended
world speed: support-foot movement relative to the actor should approximately
cancel actor travel. Check actual scenery playback for sliding and skating.
Record observed sliding and review cadence, stride and pose construction within
the authorized scope. Perfect real-world speed matching is not required for an
otherwise approved stylized gait; do not distort anatomy or change collision
geometry to force it. A run needs its own support, recovery and flight phases;
see [running animations](#running-animations). Simply accelerating a walk does
not establish a convincing run.

## 5. Register the body; author the bob

Keep scale and pose displacement separate. Use a common pixel density and stable
body landmarks such as crown, head center, neck, shoulder line and belt/pelvis.
Preserve head size, neck length and torso proportions across the complete cycle.
Use multiple landmarks: a fixed crown alone can conceal a stretching torso.

**Do not normalize each pose or strip to its occupied height, or align the body
by the lowest opaque boot pixel.** A lifted foot, bent knee, hair tip or longer
stride changes those bounds. Separate strips normalized that way can have
different body scales even though every output canvas has identical dimensions.

If source canvas density differs, use audited body landmarks to derive a uniform
whole-drawing scale and registration. Record the landmarks, crop, scale and
origin. Never independently stretch horizontal and vertical axes or resize
individual limbs to make landmarks meet. If several body proportions still
disagree, redraw the source rather than repeatedly compensating during export.

Author a small, periodic vertical bob tied to weight transfer. At Iselin's
42×72 density, a total excursion around 1–2 artwork pixels is a useful initial
range, not a requirement for every character or gait. Keep the head, neck,
shoulders and torso coherent; the legs accommodate weight transfer naturally.
Keep support-foot contact grounded rather than translating the whole character
and its planted boots up and down. Do not add another runtime bob to artwork
that already includes one.

Iselin's accepted rear crown positions are
`3,3,2,2,3,4,4,3,3,3,2,2,3,4,4,3`: two gentle excursions per full cycle,
no neighboring jump above one artwork pixel, including frame 16 → 1.
The earlier four-pixel down/up impulses were export/proportion defects.
Check exported head and belt pixels, not just the bob array in the recipe.

Keep the character's declared draw/ground anchors and world position consistent
across directions, idle transitions and poses. The ground anchor is a logical
registration reference; it is not recalculated from whichever foot is lowest.
Do not change collision size as an incidental result of a larger art canvas.

## Running animations

This section extends the shared character construction, correction, export and
review rules with running mechanics. Its two-arm/two-leg phase plan describes
a biped; quadrupeds and other creatures need their own anatomical support and
flight pattern. Existing four-frame asset packs remain historical examples,
not a required frame count or a template for new runs.

### 1. Establish the run before drawing transitions

A running cycle must communicate **landing, weight absorption, push-off,
recovery and flight**. These actions distinguish it from walking. Author a
complete two-step cycle: one right-foot landing and one left-foot landing,
returning to the original anatomical phase.

Before drawing, establish:

- Approved directional appearance and costume asymmetry.
- Near/far identities for both arms and legs.
- Contact, compression, toe-off, flight and opposite-contact keys.
- Frame count and total cycle duration.
- Body proportions, forward lean, ground reference and intended vertical excursion.
- Which foot supports the body in each frame, or whether both are airborne.

More frames subdivide movement; they do not automatically improve anatomy or
timing. These are internal construction checks before drawing transitions,
not additional user approval gates.

**Caelan's initial construction specification for an HD profile run:**

| Property | Target |
| --- | --- |
| Direction | Right-facing |
| Frames | 16 complete drawings |
| Frame duration | 25 ms |
| Full two-step cycle | 400 ms, matching the current legacy run |
| Artwork density | 2 artwork pixels per world unit |
| Starting canvas | 48×72 artwork pixels |
| Logical canvas | 24×36 world units |
| Draw anchor | [24,60] artwork / [12,30] logical |
| Foot anchor | [24,68] artwork / [12,34] logical |
| Gameplay running speed | Existing 108 world units/second |

These are initial authoring targets. Caelan's approved four-direction HD runs
are now integrated: front/rear use 48×76 artwork with [24,64] draw anchors,
profiles use 56×76 with [28,64]; each remains density 2 and 16×25 ms. The
extra transparent padding preserves body scale. Current bank manifests and
`assets/characters/caelan/animation.json` own runtime sizes and registration.
Preserve physical character size. If a legitimate pose needs more transparent
padding, adjust canvas and anchors together rather than shrinking the character
or clipping a limb. Record the changed artwork/logical canvas and keep gameplay
collision and visible body proportions independent of that padding.

### 2. Track anatomical identity continuously

For Caelan's right-facing profile:

| Limb | Camera relationship |
| --- | --- |
| Right arm | Near |
| Right leg | Near |
| Left arm | Far |
| Left leg | Far |

These identities remain fixed. A limb does not become the near limb because
it moves forward. Maintain four separate anatomical chains during review:

- Right shoulder → elbow → hand.
- Left shoulder → elbow → hand.
- Right hip → knee → ankle → boot.
- Left hip → knee → ankle → boot.

Both arms and both legs must progress through their complete motions. Natural
occlusion may hide a limb temporarily; its subsequent appearance must continue
the same movement. Track the hidden phase in the plan without drawing a ghost
limb through the torso.

### 3. Couple arms and legs correctly

Each arm generally counters the **same-side leg**:

- Right leg forward pairs with right arm back.
- Left leg forward pairs with left arm back.
- Right arm and left leg advance together.
- Left arm and right leg advance together.

At right-foot contact, the right arm trails and left arm leads. At left-foot
contact, those roles exchange. This describes the overall swing relationship;
elbows, knees, wrists and ankles have their own flexion and small timing
offsets. They should not behave as rigid, perfectly mirrored pendulums.

Inspect the shoulder and upper arm when judging swing direction. A bent forearm
can place a hand near the torso even while its upper arm swings backward.

### 4. Draw running arms with natural flexion

Running arms should look active and relaxed enough to move, rather than locked
into a punching pose:

- Swing primarily from the shoulder.
- Keep a comfortable elbow bend, roughly around a right angle as a starting reference.
- Allow that angle to open and close naturally.
- Use loosely closed hands and neutral wrists.
- Keep the shoulder attachment stable.
- Let the forearm fold across projected body depth without crossing arbitrarily
  between anatomical sides.

A shoulder swing around **30–45° forward and backward** is an initial expressive
reference, not a mandatory angle in every drawing. The far arm needs its own
complete swing; it must not remain parked behind the torso while the near arm
performs the animation.

Do not force a hidden far hand into view. Remove obsolete hand pixels when
redrawing its pose so the character never gains a third arm. Use coherent
near/far overlaps and the approved material palette rather than hiding an
unplanned far limb in a flat dark silhouette.

### 5. Give each leg a complete running sequence

Each leg follows:

**Reach → contact → compression → support → push-off → toe-off → recovery →
forward swing → reach.**

During contact and support:

- Land slightly ahead of the pelvis without an exaggerated straight-legged reach.
- Keep the landing knee soft.
- Bend the support knee as the body absorbs weight.
- Progress the supporting foot backward relative to the body.
- Extend through the hip and ankle during push-off.
- Release through a recognizable toe-off.

During recovery and swing:

- Fold the knee so the heel rises behind the body.
- Bring the recovering leg forward through a bent-knee passing position.
- Let the lower leg unfold progressively.
- Lower the approaching foot into contact over several drawings.

The boot must not remain extended ahead for several frames and then snap behind
the character. Likewise, a high recovering heel must not suddenly become a
planted boot in the next drawing. Judge hip, knee and ankle together; moving
only the boot cannot produce convincing recovery. Track actual heel/toe or
ankle landmarks with the appropriate contact phase, rather than treating the
lowest silhouette pixel or a changing sole-span midpoint as a fixed joint.

### 6. Include clear flight phases

A run normally includes moments when **neither foot supports the ground**.
For Caelan's target cycle:

- Use one flight interval after each push-off.
- Keep the feet visibly released from support.
- Continue both leg recoveries and both arm swings during flight.
- Let the body rise and fall smoothly.
- Prepare the approaching leg for landing before contact occurs.

Flight must not freeze the character in one stretched pose. Do not manufacture
it by moving an entire standing sprite upward. Knee flexion, ankle position,
body posture and support release make the airborne state readable together.

### 7. Use this initial sixteen-frame phase plan

This is the construction plan for Caelan's right-facing run. Draw and inspect
the keys before filling transitions. A row's phase is verified from the actual
drawing, not inferred solely from its file number.

| Frame | Phase | Near right leg | Far left leg | Arms |
| --- | --- | --- | --- | --- |
| 1 | Right contact | Lands slightly ahead, knee soft | Recovering behind | Right trails; left leads |
| 2 | Compression | Knee bends under load | Heel recovers upward | Both continue toward midpoint |
| 3 | Mid-support | Supports beneath pelvis | Bent knee passes forward | Near midpoint |
| 4 | Late support | Extends behind body | Thigh advances | Right advances; left retreats |
| 5 | Push-off/toe-off | Finishes ground support | Prepares forward reach | Right leads; left trails |
| 6 | Early flight | Knee folds into recovery | Lower leg starts unfolding | Continue through their arcs |
| 7 | Flight | Heel recovers behind | Approaches landing position | Near opposing swing extremes |
| 8 | Landing preparation | Continues recovery | Lowers gently toward contact | Prepare opposite contact |
| 9 | Left contact | Recovering behind | Lands slightly ahead | Right leads; left trails |
| 10 | Compression | Heel recovers upward | Knee bends under load | Both approach midpoint |
| 11 | Mid-support | Bent knee passes forward | Supports beneath pelvis | Near midpoint |
| 12 | Late support | Thigh advances | Extends behind body | Right retreats; left advances |
| 13 | Push-off/toe-off | Prepares forward reach | Finishes ground support | Right trails; left leads |
| 14 | Early flight | Lower leg starts unfolding | Knee folds into recovery | Continue through their arcs |
| 15 | Flight | Approaches landing position | Heel recovers behind | Near opposing swing extremes |
| 16 | Landing preparation | Lowers toward right contact | Continues recovery | Continue smoothly into frame 1 |

In this starting plan, frames 1–5 support on right, frames 6–8 are airborne,
frames 9–13 support on left, and frames 14–16 are airborne. Toe-off ends support;
landing preparation precedes contact. Final metadata must match the reviewed
poses if those boundaries change during authoring.

Frames 9–16 exchange anatomical roles. They are separately resolved drawings,
including near/far overlap and costume detail; do not mirror the first half
or independently offset arm and leg strips to manufacture the second half.

### 8. Establish posture and expression

Use a modest forward lean appropriate to Caelan's ordinary run:

- Keep the head looking primarily in the travel direction.
- Maintain a connected neck, shoulder line, ribcage and pelvis.
- Convey forward intent through posture rather than stretching the torso.
- Allow restrained shoulder/pelvis counter-rotation.
- Keep the expression focused and consistent with his approved face.
- Avoid an exaggerated sprinting grimace unless a separate sprint calls for it.

The lean should feel supported by the whole body. Avoid folding sharply at the
waist while leaving the hips behind. Preserve Caelan's recognizable face as
small head/torso orientation changes express movement.

### 9. Register the body and author the vertical motion

Running can have more vertical motion than walking, but it follows weight
transfer: lower during compression, rise through push-off, reach the upper
part of the arc during flight, and descend into the next contact.

For Caelan's artwork density, begin with approximately **2–3 artwork pixels of
total crown excursion**, then judge the result visually. This is a starting
range, not a universal requirement. Reserve headroom in the run posture for
flight; add transparent padding if needed rather than clipping the crown.

Keep head size, neck length, torso length and limb proportions stable. Do not
scale or position each frame using occupied height or the lowest boot. Bent
knees and airborne feet naturally change those bounds. The declared foot
anchor is a registration reference, not an instruction to align every pose
by its lowest pixel.

Do not freeze the head so rigidly that the torso stretches beneath it. Keep
the whole body coherent through authored motion, and do not add runtime bobbing
to drawings that already include it. Apply the shared body-landmark registration
rules to all batches and review batch joins as adjacent animation frames.

### 10. Preserve costume identity and secondary motion

For Caelan:

- Retain chestnut hair, ivory sleeves, teal-and-gold tabard, brown bracers and boots.
- Keep the single pouch on anatomical left: **far side in right profile**.
- Let hair and tabard tails follow the motion with restrained lag.
- Keep the pouch attached to the belt, with modest movement rather than floating.
- Preserve the thin black exterior contour and consistent material palette.

Secondary motion must loop cleanly. It must not introduce changing hair volume,
garment length, extra accessories or incorrect costume sides. Other directions
use their own approved appearance and occlusion; reflected motion guides do
not authorize flipping the finished asymmetric costume.

### 11. Construct complete drawings and correct locally

Author every pose as a complete character image. Use small batches against the
same approved keys and landmark grid. Inspect each batch before generating
more transitions; do not generate a larger batch to compensate for bad keys.

When correcting a defect:

1. Identify the affected anatomical chain and frames.
2. Preserve snapshots of accepted work.
3. Redraw complete poses with the specific correction.
4. Restore accepted regions only where appropriate.
5. Inspect the repair boundary, neighboring frames and loop seam.

Preserved regions must belong to the **same movement phase**. Combining
independently timed arms and legs can recreate the rear-walk problem even when
each region looks acceptable separately. Keep source history, repair windows
and preservation hashes under the shared correction/export rules.

### 12. Review movement quality without forcing perfect speed matching

Review the run in place and traveling through actual scenery. Prioritize:

- Readable alternating support and flight.
- Correct near/far limb progression.
- Natural knee and elbow flexion.
- Smooth release, recovery and landing.
- Stable proportions and coherent body motion.
- Clean transitions and loop seam.

Record visible sliding and cadence observations. Under the current approved
art direction, perfect real-world speed matching is not a requirement for
approving an otherwise convincing stylized animation. Prioritize believable
limb sequencing and expression without forcing a numeric contact target to
distort anatomy. Report measured limits honestly; passing pose checks does
not prove world-ground locking.

Preserve gameplay speed and Caelan's existing 400 ms run cadence unless a
separate change is explicitly reviewed. Keep established cadences for other
characters unless their own scoped changes authorize retiming. Do not modify
collision geometry to chase artwork or reopen the approved walking cycles
as part of the run work.

### 13. Export and acceptance checklist

The review package must include:

- Sixteen complete native RGBA frames and a reconstructable spritesheet for
  Caelan's target; other scoped runs retain their declared frame budget.
- Explicit frame order, durations, contact foot and flight intervals.
- Source drawings, selected cells, registration, palette/alpha settings and hashes.
- Normal-speed and clearly labeled half-speed previews.
- Numbered frame sheet and approved-idle comparison at cast scale.
- Traveling footage when integrating into gameplay.

Automated checks verify dimensions, hard transparency, unclipped margins,
timing, source preservation, loading and measured continuity. Contact/flight
metadata must agree with the visual poses; neither labels nor frame uniqueness
alone prove a run. Keep design approval, artwork approval, merge state and
runtime integration distinct. Preserve approved references when exporting.

For 25 ms GIF playback, alternate **20/30 ms delays** to preserve the average
cadence. Label half-speed playback clearly and verify actual saved durations.
Exact RGBA PNGs remain the authority for color, alpha and fine detail.

**Visual acceptance requires checking all four limb chains across both steps,
every batch join and frame 16 → 1. Passing export tests alone does not establish
a convincing run.**

## 6. Correct one defect while protecting accepted work

First identify the failing frames and anatomical chain. Preserve snapshots of
the accepted parts before editing. Ask image generation to redraw complete poses
with the specific defect corrected, using the approved appearance and motion
references. Do not request unrelated redesigns during a foot correction.

A documented regional edit may restore accepted pixels outside the repair area
after a complete drawing is redrawn. This protects approved arms, boots or body
detail against incidental generation drift; it is not a detached-limb animation
system. Do not rotate, translate or stretch an isolated leg to manufacture poses.
Save the complete generated master, protected snapshot, repair window and hashes.

Inspect the repair boundary on every frame. Check knee continuity, cloth/skin
joins, duplicated outlines, stale boots and floating coat hems. A protected
upper region can preserve an existing body-height defect; passing a pixel-equality
test only proves preservation. Expand the scoped redraw when the actual defect
crosses the boundary, and document which previously protected pixels changed.

## 7. Export reproducibly

Retain original sources unchanged under `assets/source/`, plus the recipe,
source hashes, selected cells/order, landmark coordinates, scales, origins,
palette/alpha settings, protected regions and approval state. Keep superseded
attempts and previews labeled as history. Record which revision is current.

Export to the character's existing asset layout: complete frame PNGs, native
spritesheet, and metadata containing frame rectangles, individual durations,
loop behavior, density and anchors. Use uniform nearest-neighbor sampling for
pixel art and hard transparency where the existing character format requires
it. Remove background fringe without destroying slim fingers, braid strands,
boot gaps or the outline. Inspect component extraction; the largest connected
component is not automatically the whole valid drawing.

Rebuilds must preserve approval state and leave approved references unchanged.
Do not silently regenerate the idle, other directions, portrait or costume while
exporting one walk. Keep asset approval, merge state and runtime activation
distinct; a merged animation pack does not imply that actor selection uses it.

GIF delays are quantized to centiseconds. For 35 ms playback, alternating
30/40 ms delays reproduces the average cadence and total duration. Label slow
previews clearly and verify the actual saved GIF timing. Review PNGs remain the
reference for exact colors, alpha and fine detail.

## 8. Review at three levels before declaring completion

1. **Drawings:** numbered native frame sheet with constant nearest-neighbor
   enlargement. Trace all limbs; inspect identity, outlines, face, costume sides,
   hair, body landmarks, feet and edit seams. Include last → first.
2. **Motion:** normal-speed loop alongside half-speed playback and native-size
   examples. Compare with the approved idle and cast scale. Inspect contact,
   passing and weight transfer; more unique files alone do not establish motion.
3. **Game rendering when integrating:** travel against actual scenery at the
   intended speed and detail density, with relevant light/dark backgrounds,
   camera scale, idle/walk/direction transitions and depth occlusion. Use temporary
   saves or nonpersistent fixtures. A standalone asset review may defer this
   integration check, but must say so.

Use focused automated checks for the actual defect and export contract:
dimensions, alpha, unclipped bounds, frame ordering/count and timing, sheet
reconstruction, loading, landmark continuity, loop seam, expected contact phases,
and exact preservation of explicitly protected artwork. Where a motion landmark
is occluded, annotate its phase or inspect it manually rather than measuring an
unrelated visible component. Do not add anatomy-distorting tests to satisfy
arbitrary joint angles or exact hand positions. Count/uniqueness checks alone
cannot certify a gait, and passing tests never replaces viewing the frames.

### Completion checklist

- [ ] Approved design and direction references; explicit anatomical sides.
- [ ] Coherent full-body drawings; all four limb paths account for occlusion.
- [ ] Continuous support, passing and contact; no parked-foot snap or extra limbs.
- [ ] Stable head/torso proportions and landmark registration; deliberate modest bob.
- [ ] Correct directional costume/hair, restrained secondary motion, readable outlines.
- [ ] Clean repair boundaries, unclipped pixels and smooth final → first transition.
- [ ] Reproducible sources, manifests, timing, anchors and current revision/status.
- [ ] Normal/slow preview, numbered sheet and scale comparison visually inspected.
- [ ] Appropriate checks pass; runtime integration validated or explicitly deferred.
- [ ] Requested review/merge boundary respected; describe remaining limitations plainly.

## 9. Diagnose before regenerating

| Observed defect | Likely cause | Targeted correction |
| --- | --- | --- |
| Near side walks; far side stays parked | Only the visible-side chain was planned | Trace all four limbs through contact/passing and redraw hidden/reappearing phases. |
| Three arms, hands or boots | Old pose pixels survived a replacement | Remove the obsolete silhouette and resolve overlaps in the complete drawing. |
| Foot wiggles ahead, then jumps behind | Repeated extreme poses; missing progression | Rebuild stance/passing in-betweens and verify landmark progression. |
| High kick followed by a sharp landing | Excessive reach/lift and insufficient recovery | Reduce excursion and distribute the approach to contact across drawings. |
| Character grows/shrinks or twitches | Source proportion drift; foot/height-based normalization | Audit head, neck, belt and shoulders; redraw inconsistent proportions and register by body landmarks. |
| Floating silver hem or broken knee | Partial edit restored stale pixels at its seam | Redraw a coherent boundary and protect artwork beyond it. |
| Opposite direction swaps braid/mantle | Finished asymmetric sprite was mirrored | Use mirrored motion only as a guide and redraw direction-specific appearance. |
| Body looks fine enlarged but skates in game | Cadence/stride mismatch or wrong world/art units | Compare stance with actor travel and verify density/anchor use. |
| First frame pops after the last | Endpoints and secondary motion were reviewed separately | Inspect the loop seam as an ordinary adjacent pair and draw its missing transition. |

## Implementation references (examples, not competing standards)

- [Iselin front walk](reviews/iselin_front_walk/README.md): complete-frame source
  and the 16-frame cadence.
- [Right walk leg correction](reviews/iselin_right_walk_redrawn/LEG_REVISION.md):
  preserve accepted arms while repairing foot progression.
- [Left walk](reviews/iselin_left_walk_redrawn/README.md): reuse approved motion
  with direction-specific costume and braid motion.
- [Rear walk, final body revision](reviews/iselin_back_walk/README.md#body-stability-correction-revision-3-current):
  smaller boot lift, body-landmark registration, controlled bob and seam cleanup.
- [Iselin detailed idle rendering](reviews/iselin_first_assets/IMPLEMENTED.md):
  artwork/world density and production occlusion.
- [Iselin runtime walking](reviews/iselin_walk_integration/README.md): shared
  logical/detail timing, navigation, stopping, turning and real foliage occlusion.
- [Asset tool catalogue](../tools/README.md): commands and local implementation
  details, including legacy builders retained for reproducibility.

### Integrated Eldenmere town and businesses

The complete live map uses native 2× environment art with unchanged character and
world proportions. The classroom map is re-sampled from its retained approved
Auratia wall-map drawing; the full world map and its geography remain unchanged.
All thirteen town building exteriors and fifteen established interiors are
integrated. Serene, Caelan and Tomas’s hall, bedroom and dining room retain their
curated household bank and remain distinct from the regional Sanctuary. One
additional `inn_guest_floor` is registered through the existing interior system.
The separate upstream scene is migrated. Regional Sanctuary/cave scenes and NPC
body/gait banks retain their own migration status.

The town expands twelve tile rows south, without shifting existing coordinates.
The inn is at `[192,1224]` and item shop at `[624,1272]` logical units; both connect
to the existing southbound lane and have furnished, enterable interiors. The inn
uses the shared confirmed party-rest/save behavior at its guest bed, with an
eligible discovery cue. The shop's exterior stock stays fixed behind glass and
its furnished counter adds no automatic item grants. Currency, prices and merchant
transactions remain a separately specified gameplay system.

The source-owned `tools/eldenmere_interior_architecture.py` extension runs inside
that same live composer. It preserves room identities, fixture positions, stateful
quest objects, actor ownership and services. Southern cutaway exits show an actual
opening, side returns and threshold rather than a mat against continuous walls.
Put the high-contrast sill on the existing transfer line and a shallow strip
of destination material beyond it. Use plaster-and-timber or masonry returns
appropriate to the room; don't add a full-height frame over a south cutaway.
For north-wall doors, keep the frame and sill registered while the leaf opens
over a shaded destination floor. The inn distinguishes climbing from
descending with riser lighting and a recessed well, not directional markers.
The mill’s east-wall axle, gearing, spindle and stones form one processing assembly;
its motion reads the existing wheel stop state, with fixed supports and a static
reduced-motion frame. Workshop supplies, household storage/bedding and decorative
shop potion/weapon/armor displays communicate use without creating occupations,
collectibles or purchasable equipment.

The inn retains its existing ground-floor rest bed, keeper and exterior portal.
Four ordinary upstairs guest bays correspond to its guest-storey window bays.
Reciprocal stair doors use explicit safe landings and opt-in excursion rearming,
including after Continue; no upstairs price or recovery system is introduced.
Named minimal mill/stair/hearth occupancy additions are recorded in the existing
architecture schedule. Existing restoration retains valid old positions and uses
its checked room-entry fallback for a newly occupied footprint, without changing
quest, inventory, party or currency state.

Lantern construction phases retain the actual canonical frame/material drawings,
not generic paper stock. Those small existing action/carry/home drawings remain
explicit compatibility artwork, uniformly sampled at 2× rather than claimed as
new HD poses. The collected contents retain their canonical empty overlay; the
separately owned real table/support remains visible while one frame moves to its
existing carrier/home owner at the authored transfer cue.

Building shells keep clear authoritative portals; separate five-state doors
retain their logical geometry and 100 ms timing. The mill wheel has an independent
48-frame, 9.6-second clock and shares the existing story-controlled stop state.
Reduced motion holds ambient scenery. Explicit still images remove smoke without
extending animation loops. Foreground rails/canopies retain actor readability.

New retained specialist drawings cover bridges, the working well, workshop props,
school furnishings and small quest/household objects. Source extraction isolates
the intended connected silhouette before fitting; neighboring atlas-cell fragments
must never become part of a prop. Preserve occupied bounds as well as the canvas:
a small bucket or bowl must not expand to fill its transparent padding.

Scene-local presentation replacements preserve object ownership, state and work
cues. Held sacks and Elira's memorial lantern are re-composited with the existing
approved complete Caelan body drawings; travel/body source artwork is unchanged.
The shelf, first take pose and deposited lantern use the same canonical native
object, preserving the transfer pixel registration. Do not stretch anatomy to
match a replacement object.

The [terrain integration reference](TERRAIN_ART_STANDARD.md#integrated-eldenmere-town-and-upstream)
owns build/check commands, native chunking and compatibility details. Source-bank
sections below describe original delivery inventories; the live integration
registry owns current consumers. [Actual-game review evidence](reviews/eldenmere_town_hd/README.md)
is separate from the older offline pack compositions.

The replacement well/pail bank is separately staged under
`assets/terrain/eldenmere/well_hd/`; its broad top opening, low masonry and rear
canopy are new coherent drawings registered as a whole. It preserves the current
physical support as a target while declaring its own draw, ground and mechanism
anchors. The existing live rig remains active until the later mechanism, actor
and integration deliveries. Static pack previews do not approve animation,
hand contact or runtime layer ordering. The
[staged well reference](TERRAIN_ART_STANDARD.md#staged-eldenmere-well-and-pail)
owns its source/export commands and status.

The staged gardener performance is separately exported to
`assets/characters/npcs/female_02/gardener_well_hd/` by
`tools/build_gardener_well_hd.py`. Its new complete action drawings use native
96×96 artwork in the existing 48×48 logical action canvas, with distinct draw
anchor `[24,36]` and visible foot registration `[24,40]`. Sixteen lowering and
sixteen heavier raising drawings follow the shared mechanism crank sample;
the read-only `gardener_well_presentation.py` adapter adds no animation clock,
water accounting or object transfers. Back-facing reach/hold/recovery keys bind
the canonical pail across the mechanism's ownership cues. Distinct engage,
brace and brake poses, pickup/setdown and both ground/raised left/right pours
are also staged. Four-direction travel explicitly retains the existing complete
four-frame compatibility bodies and 560 ms cadence; it is not a new HD gait.
The [performance review](reviews/gardener_well_hd/README.md) records source
provenance, calibrated stations, actual-controller offline previews and limits.
These exports do not select a new live gardener routine or approve final runtime
navigation, state restoration or well/actor depth ordering.

### Integrated Sanctuary exterior

The courtyard migration registers the Sanctuary facade at 216×216 logical units
with native 432×432 artwork. Its five door states use native 64×84 artwork in the
original 32×42 portal; host, entry anchor, thresholds, destination and arrival are
unchanged. The fresh facade source separates the bell and planters so the two
herb beds remain at their existing gardener stations. Bench and provision basket
also keep their established physical canvases, positions and depth baselines.

The bell's mount, lantern bracket, planter boxes and building remain fixed.
Window lighting stays steady throughout the ambient cycle; smoke uses the
200 ms clock and the bell uses nine 600 ms phases within a 10.8-second combined loop. `reduced_motion_image` supplies
a distinct smoke-free, steady-light still without extending the animation loop.
The thin dark contours and native detail are preserved through the scene buffer.

Source, provenance, exports and the scoped build command are listed in the
[terrain integration reference](TERRAIN_ART_STANDARD.md#integrated-sanctuary-courtyard-and-approach).
Other exterior designs, inn/shop profiles and their props remain staged; this
migration does not add new buildings or retire banks still used elsewhere.

### Integrated Elden Vale Sanctuary reserve

Creative direction is centralized in the
[Elden Vale regional design guidance](world/regions/ELDEN_VALE.md). The Pale
Antlers are integrated and Rising Rain remains a future target; this section
records the already integrated environment bank.

The reserve exterior, cave approach, hall and relief room now use native 2×
environment art at their established logical sizes. Pale limestone, slate,
emerald woodland, the silver-green memorial tree and cyan/amethyst/opal crystal
accents preserve the region's identity. The hall/cloister, entrance arch, cave,
ridges, basin, memorial tree and ceremonial table use retained new master art;
ordinary terrain, vegetation and furnishings reuse the current HD banks.
The cave interior is a separate migration. Existing NPC body banks are retained;
caretaker pails and grove particles use explicit native presentation.

The [terrain integration reference](TERRAIN_ART_STANDARD.md#integrated-elden-vale-sanctuary-reserve)
owns source/export commands, collision preservation, architectural opening masks,
chunk/cache behavior and review provenance. Repeatable marker/ledger/cabinet/table
inspections and the relief bed use the shared eligibility-driven discovery cues.
Window/lamp colors remain steady; pause, focus and reduced motion govern ambient
motion. Do not infer gameplay footprints from the new visible silhouettes.

### Integrated Elden Vale regional foundation

The regional `hd_art_manifest` overlay selects
`assets/maps/overworld/elden_vale/hd_integration/manifest.json`. Its selected
terrain and scenery are integrated at 2× density while retaining regional logical
canvases, foot anchors, collision ownership and travel coordinates. This is a
separate adapted registry; the original PR 1 foundation pack retains its staged
`not_integrated` metadata. Build/check commands and material construction are in
the [central terrain reference](TERRAIN_ART_STANDARD.md#integrated-elden-vale-regional-foundation).

Vegetation frame sets use one union crop, scale and registration across idle,
moving and fixed states. Their breeze follows the exploration clock with stable
reduced-motion frames. Ground and animated water retain native detail through
global phase-aware composition and bounded helpers/chunk caches; logical masks
continue to own geometry. Existing character, wildlife and work controllers are
unchanged. The Sanctuary miniature remains separately owned.

The [regional creative guide](world/regions/ELDEN_VALE.md) remains the single design
authority. Its six-area foundation and nonblocking future landmark reservations
are recorded in the active layout. Pale Antlers and Sanctuary views now use the
explicit landmark layers. Selected causeway structures and reused masonry are
also integrated; Rising Rain and final atlas updates remain deferred. See the
[gameplay foundation review](reviews/elden_vale_hd_integration/README.md) for current
evidence rather than treating offline source-pack compositions as integration.

## Audited Eldenmere exterior architecture

The thirteen live town building shells now use the native authoring module
`tools/eldenmere_architecture_art.py`, with source drawings, explicit pane/material
masks and geometry records under each existing exterior source recipe's
`architecture_audit/` directory. The maintained exterior/business builders and town
composer select these drawings explicitly. Unused staged variants retain their
historical path; they are not evidence that portal-first facade strip fitting is
an acceptable construction method for the new live shells.

The existing town architecture schedule records reviewed roof planes, wall
contacts and exact cap emitters independently from the unchanged ground/door
registration. The roof-only correction restores the actual 24px cottage,
workshop, school and household **low silhouettes and eave spans**, not only their
shingle style. Author the detail natively at 2×: tapered pitched ends, quiet
staggered courses, restrained bevels and narrow ridge caps. A roof's visible
height must not be expanded to cover the numeric depth of its ground footprint.
That former minimum-height interpretation, retained by #256, is superseded;
conflicting geometry tests and old review prescriptions are historical evidence,
not permission to recreate tall roofs.

Preserve current wall/facade pixels, eave elevations, canvas sizes, thresholds,
occupied ground, depth baselines and viewport anchors. Restore roof dimensions
above those retained eaves; do not stretch walls or move gameplay to force the
old roof-to-total-body fraction. Keep flues aligned to their hearths. Roof-only attachments may shift vertically
with the roof; move each cap or bell and its visual mounting point together so
nothing floats. Leave gameplay attachment and interaction points in place.
The mill retains an actual front-gabled processing bay, a distinct low receiving
annex, its hoist, wheel contacts and yard. Inn/shop have no 24px predecessors:
their own earlier HD silhouettes inform their low roof proportions without
pretending they are historic cottage assets. The inn remains two-storey; its
real guest-floor integration remains PR4 work.

See the [roof proportion correction](reviews/eldenmere_roof_proportions/README.md)
for measurement conventions, historical references and intentional adaptations.
The [#256 roof-style review](reviews/eldenmere_roof_style/README.md) retains its
historical captures and validation results, but its statement that roof envelopes
retain audited depth is superseded. Mill/school walls fit their retained occupied
ground; overhangs do not enlarge blockers. Preserve the #254 household courtyard
and #255 workshop/mill workyards. Mira's, the school's and the mill's registered
hearth/flue relationships remain intact.

Pane masks are constructed from individually reviewed panes, never broad slate
or masonry color selections. Material masks have exclusive visible ownership.
Native window light, smoke and the fixed shop stock remain separate. Normal and
Reduced Motion retain identical roof materials and underlying structure. Runtime
maps, collision, door thresholds, NPC/quest ownership, shops/services and the
southern departure/return retain their established contracts. Source boards and
footprint diagrams are labelled separately from the actual native Game captures
in [the exterior architecture review](reviews/eldenmere_exterior_architecture/README.md).

## Staged Eldenmere HD building exteriors

Source recipe: `assets/source/terrain/eldenmere/exteriors_hd/recipe.json`.
Staged manifest: `assets/terrain/eldenmere/exteriors_hd/manifest.json`.
Original delivery state was **rebuilt / not integrated**. Selected live Eldenmere consumers are now integrated above. Merge and user visual approval are separate;
visual approval remains not reviewed. This bank follows the global sizing,
rendering, contour and object-cue rules above. Terrain companions remain governed
by [the terrain standard](TERRAIN_ART_STANDARD.md).

The bank provides ten cottage options and four bespoke landmarks. Nine cottages
combine compact, standard and wide shapes with gardener, craft-household and
weathered visual treatments; a heather-roof standard option preserves the existing
home's palette identity. Landmarks are Mira's workshop, the watermill, village
school and Sanctuary/Serene's home. These profiles describe visual dressing,
not new authoritative occupations, businesses, quests or destinations.

Twenty-four separate charm props include pots/planters, three window boxes,
firewood, broom, boots, rain barrel, watering can, stool, orchard basket, herb
bundles, wood shavings, two awnings, a laundry line, fence panel, closed garden gate,
climbing ivy and cog/leaf/book signs. Larger props have individually declared
canvases; do not fit all objects into a uniform visible size. Boots and watering
cans remain appropriately smaller than a person. Mounted props have attachment
anchors; grounded props have foot anchors and separate depth baselines.

Retain the new source drawings and their hashes. Source processing removes the
magenta background and connected color spill, registers the upper roof/body as
one plane, and registers lower facade strips around the authoritative portal.
It samples fine detail into 2× artwork rather than enlarging legacy color pixels.
Existing wood, stone, plaster, iron, glass and four roof ramps remain the palette
references; plants use the current emerald ramp. Window light, fabric and flower
accents have explicit palette roles. Distinct silhouettes receive thin dark
contours. Repaired plaster, replacement shutters, worn thresholds, patched shingles,
restrained moss, window boxes and side clutter should suggest household use while
keeping entrances clear. Exposed roof patches remain wood rather than becoming
roof-colored noise. Continuous ground follows terrain boundary rules.

The audit snapshots all eleven current building consumers: their canvas sizes,
world positions, sort baselines, local/world door rectangles, entry anchors and
widths, open/close radii, destinations, spawns and arrival behavior. Bindings keep
these logical facts independent from the new silhouette. The snapshot is versioned
baseline evidence, not a permanent unit-test freeze on unrelated map development.
Building canvases remain 96/120/144×144 logical for cottages, 168×168 for the
workshop, 144×168 for the mill, 192×192 for the school and 216×216 for the Sanctuary.
Exported artwork dimensions double those values. Ground rectangles retain their
existing logical definitions. Do not infer navigation or collision from art alpha.

Fixed structure, door states, smoke and window light are separate layers. Clear
the exact authoritative portal from the shell, then place its separately drawn
five states at the declared local logical position. Door states are 100 ms,
nonlooping; hold indices are closed=0/open=4 and closing reverses the order.
Single doors are west-hinged; Sanctuary leaves open at both outer jambs. Preserve
live entry gating, thresholds, widths, transitions and arrival behavior when
integrating. Decorative props must not overlap the declared approach envelope.

Ambient smoke/window layers use eighteen 200 ms frames (3.6 seconds). Smoke begins
at the actual chimney, including its height relative to a taller bell turret,
and disperses above it. Structures, panes' leadwork and door leaves stay fixed.
Window masks select only glass or explicitly allowed warm panes; bright blue glass
must not be classified as amber light, and plaster/beam highlights must not flicker.
Window lighting must remain constant across ambient frames: no alternating pane
colors or brightness pulses. Smoke, signs and cloth may animate independently.
Window light is optional for scene/time-of-day use; reduced motion uses the explicit
closed/open stills without ambient effects. Bell turrets and shutters remain fixed
parts of this staged artwork.

Hanging props sway by at most one artwork pixel with fixed mounting hardware.
Awnings bend at their actual lower cloth edge while their top mount remains fixed.
Laundry posts and line stay registered. Their optional ambient loops share the
3.6-second period; idle files provide reduced motion. The gate sprite is a closed
visual asset, with no new passability or interaction registration. Ordinary props,
signs, doors and buildings do not automatically receive discovery glints or yellow
outlines. A future quest interaction must opt into the existing eligibility system.

The mill has a separately authored wheel and fixed structure/axle. Its 48×48
logical wheel canvas remains at local [88,94], with axle [112,118]. Forty-eight
200 ms frames rotate clockwise by 7.5 degrees per frame, preserving the existing
implied full-turn speed of 9.6 seconds. The complete turn avoids assuming an
imperfectly textured wheel repeats exactly every 45 degrees. Keep the fixed hub
and facade stationary. The wheel uses an independent clock from smoke/window light;
reduced motion uses wheel frame zero. The small foreground fence retains the
left-side placement without covering the entrance.

```sh
python tools/build_eldenmere_exteriors_hd.py
python tools/build_eldenmere_exteriors_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_exteriors_hd
```

[Exterior review evidence](reviews/eldenmere_exteriors_hd/README.md) includes native
family boards, door/opening reviews, ambient loops, wheel rotation, enlarged prop
motion and reconstructible 960×640 compositions with unchanged approved Caelan and
Iselin. These are offline fixtures, not live gameplay captures. Actual integration
must migrate consumers explicitly, preserve map/door geometry, use native renderer
adapters, and verify foreground occlusion, traversal, pause/focus and reduced motion.
That original pack export did not change maps or gameplay. Current integration is
owned by the town registry above. Keep shared legacy banks while other consumers
still require them.

## Staged Eldenmere inns and item shops

Source recipe: `assets/source/terrain/eldenmere/business_exteriors_hd/recipe.json`.
Staged manifest: `assets/terrain/eldenmere/business_exteriors_hd/manifest.json`.
Original delivery state was **rebuilt / not integrated**; the maintained inn/shop now have live Eldenmere bindings above, with visual approval recorded separately.
This extends the preceding architecture bank with maintained and weathered
versions of a two-story inn and a one-story item shop. Each pair shares logical
canvases, footprints and entrance geometry for reuse elsewhere.

The inn uses a 192×240 logical / 384×480 artwork canvas and a 168×96 logical ground
footprint. Its porch, four guest windows, varied curtains, terracotta roof, chimney,
bench/firewood and bed pictogram establish a welcoming lodging house. The shop uses
168×192 logical / 336×384 artwork with a 144×96 logical ground footprint, slate roof,
blue-green awning, delivery hatch, supply baskets, rain barrel and satchel/potion
pictogram. Weathered variants retain readable stock and entrances rather than
turning into ruins. Source silhouettes use explicitly inspected crop rectangles;
do not assume a generated sheet follows its nominal grid or clip neighboring
objects into a cell.

The item shop's framed glass display is a separate fixed component at local
[70,136,78,48] logical units, exported at 156×96 artwork pixels. Its left section
shows red, blue, green and violet potions in round flasks, square bottles and
conical vials. The center holds a sword and round shield; the right shows a helmet
and breastplate. Dedicated potion/steel palette roles preserve color and material
separation at native scale. Subtle source-drawn diagonal reflections sit across
the stock, with fixed mullions and frame. This is decorative visual merchandise,
not an inventory/catalog binding, pickup, grant or guaranteed future assortment.
Keep every display pixel fixed through ambient frames. Pane-light masks and cloth
motion must not recolor, pulse or obscure the goods; do not add discovery glints,
labels or yellow outlines to ordinary shop stock.

Separate source-drawn signs replace the baked signs removed from the fixed shells.
Signs retain their mounting hardware while swaying by at most one artwork pixel.
Shop awning motion is restricted to the cloth interior at its lower edge, away
from the display and fixed supports. Inn smoke and optional window light follow
the established eighteen 200 ms frames (3.6 seconds). Door leaves reuse the prior
bank's drawn five-state, 100 ms, west-hinged convention at explicitly registered
portals. Closed/open stills provide reduced-motion alternatives. Six reusable
props include both signs, a porch bench, sheltered firewood, travel boots and a
pack/blanket. Their individual logical sizes and mount/ground anchors are recorded.

The pack retains its original **candidate placement plan** as historical evidence.
The live southern expansion uses the integration recipe above instead.
The inn candidate is on the western southern grass plot; the shop candidate is
southeast of the central residential area. Both footprints and proposed 24-unit
access corridors were clear in the recorded collision baseline. Proposed routes
connect to recorded existing dirt-lane points. Their context PNG is a retained
legacy-density reference used only in a labeled logical-resolution planning
diagram; native artwork is reviewed separately. Seven logical collision snapshots
retain baseline evidence without permanently freezing current maps in unit tests.
Before integration, revalidate then-current buildings, terrain, water/irrigation,
quests, NPC routines and navigation; add the approaches and allowed routes explicitly.

The generated review `integration_spec.json` scopes future interiors, keeper/
merchant stations, dialogue, a currency model, atomic purchase/rest transactions,
inventory limits, save persistence and failure/cancellation handling. Existing
consumables are referenced as possible starting stock; ordinary equipment catalog
entries and balance decisions remain prerequisites. Unique story gear and key
items must not be treated as ordinary stock. The original exterior pack supplied artwork and planning evidence. The live town
integration now supplies entrances, interiors, keeper stations and shared inn
recovery. Keeper services now support free consumable purchases and inn stays;
[the inventory guide](INVENTORY.md#eldenmere-town-services-and-gold) owns prices,
transactions and currency behavior. The retained
specification describes those prerequisites rather than preventing access to the
integrated buildings.

```sh
python tools/build_eldenmere_business_exteriors_hd.py
python tools/build_eldenmere_business_exteriors_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_business_exteriors_hd
```

[Inn and item-shop review evidence](reviews/eldenmere_business_exteriors_hd/README.md)
includes both variants at native scale beside unchanged Caelan/Iselin, enlarged
glass displays, ambient loops, props, the planning diagram and service specification.
Source art and prior-bank door/smoke dependencies are hashed. Exporters write only
the new bank and review directory; runtime maps, existing assets, inventory,
interaction eligibility and saves remain unchanged.

### Staged Rising Rain actions and wildlife

Elden Vale's third asset pack is built by
`tools/build_elden_vale_rising_rain_hd.py`; the
[central terrain reference](TERRAIN_ART_STANDARD.md#staged-elden-vale-rising-rain)
owns environment maintenance. All new banks remain **not integrated** and
**not reviewed by the user**. Existing idles, gaits, cast placement and selectors
are unchanged.

Eight complete drawn poses each cover right-facing washing gathering for
`npcs/female_01`, cloth deployment for `npcs/male_02`, and a leaf-catching identity
study for `liam`. Staged exports live in each actor's `rising_rain_hd/` directory.
The 96×112 artwork / 48×56 logical action canvas includes reach padding; soles
register at [48,104] artwork / [24,52] logical. One scale per source strip preserves
anatomy while bending; adult body heights remain 68 artwork pixels and Liam's
52, matching twice their original occupied idle heights. Do not normalize every
pose independently or manufacture movement with detached limbs.

Manifests record frame order/timing, grips, station anchors and ownership cues.
The stateless preview samples one object location per authored time, including
interrupted/seeked playback. Gathering finishes holding transport cloth, deployed
cloth remains at its supports, and the lowered leaf returns to its station.
Production integration must retain authoritative object ownership, close natural
reach, actor/prop occlusion, action completion and personal-prop visibility.
Existing legacy walk frames appear only as approach compatibility references in
offline previews; no new carrying gait is implied.

The brown/cream bird has sixteen complete drawings: four perch/alert, four takeoff
and eight flight. Its 64×64 artwork / 32×32 logical canvas is transparent wing
padding, not an enlarged body. Body scale derives from the original regional perch;
a cream-breast landmark registers changing wing silhouettes. The separate preview
trajectory does not change anatomy or commit an animal route. Stable perch artwork
serves reduced motion. Other wildlife banks and actor IDs remain untouched.

[Numbered sheets, contacts and normal/slow previews](reviews/elden_vale_rising_rain_hd/README.md)
are offline review evidence. Actual gameplay camera, transitions, actor/workstation
spacing, interruption/Continue and reduced-motion lifecycle require integration
review. The optional map event glyph does not activate a forecast UI.

### Explicit landmark layers

`landmark_layers.LandmarkLayers` is shared by detailed `World` and the regional
renderer. `landmark_layers` records declare an image, native density, logical
canvas, top-left logical position and `distant`, `ground` or `overhead` role.
Distant and ground passes precede nearby depth-sorted scenery; overhead follows
actors. Empty registries preserve existing presentation. These records never
create collision or interaction cues. Builders separately validate physical
contacts against protected geometry.

Complete placed bounds determine visibility independently of ordinary regional
scenery root searches. The source LRU is capped at 16 MiB per world; mutable
cutaway crops are viewport-bounded and never cached by actor position. Authored
grayscale masks constrain immediate local fades around visible actor bodies,
including story positions and travelling-party render actors, and explicitly
authored interaction visibility points. Source pixels are never mutated.
The same stable assistance applies under reduced motion, pause and focus loss.
Disposable actual-game evidence and the cross-scale placement review live in
[the landmark framework review](reviews/elden_vale_landmark_framework/README.md).
This framework alone activates no production landmark.


### Integrated signature landscape presentation

The live regional registry explicitly adapts the signature asset schema; its
miniature keeps96×80 logical presentation and the existing transfer contract.
Eldenmere has no town landmark placement. Regional and detailed views preserve
shared anatomical transforms and independently registered overhead pieces. The
detailed reserve samples the coherent master once into a dedicated980×660 native
rendition, then segments on even native boundaries. It does not runtime-downsample
legacy logical pixels. The selected490×330 logical composition preserves camera
coverage and existing solid contacts rather than stretching to a reservation.
Only lower terrestrial fringe is embedded/occluded against named existing ridge
geometry, protecting the jaw/anatomy. Raised skull and branches retain authored
mask cutaways for actors and required interactions.

The former town skyline/vista configuration was removed by the architectural
registration audit. Historical town captures remain evidence of the previous
implementation, not the current placement contract. Shared distant artwork and
regional/Sanctuary landmark consumers remain available to their owning systems.


### Causeway structural registration

The open arch preserves one uniformly projected master and registered parts.
The lintel is overhead; tall piers use ordinary foot-baseline sorting so actors
never paint onto their vertical faces. Explicit pier bases own collision. The
1.25 presentation choice preserves the protected diagonal road rather than
shrinking the player probe or narrowing circulation. Raised deck remnants and
parapets stay beside the continuous route; surface-only paving remains under
actors. New ruins use the same restrained local overhead visibility and native
composition as the Pale Antlers, without new interaction cues or save fields.
