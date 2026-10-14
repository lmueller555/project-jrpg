# Project JRPG — Production Asset Pipeline, Renderer & Animation Architecture

**Status: AUTHORITATIVE technical specification v1.0**  
**Scope:** production 2D pixel-art resources, export, validation, world/battle rendering, and animation playback.  
**Dependencies:** [Art Style Guide](ART_STYLE_GUIDE.md) controls artistic direction and pixel proportions. This document controls technical contracts. Neither document establishes story, battle mechanics or geography.  
**Implementation status:** Design specification only. Existing `main.py` and `visuals.py` remain a prototype until migrated and validated.

## 1. Non-negotiable contracts

1. World/maps reference **stable semantic asset IDs**, not atlas cell positions or file-system paths.
2. Shipped art is inspectable **RGBA PNG** plus versioned JSON metadata. Editable art sources are retained separately; runtime never requires source-file formats.
3. **Current approved presentation scale (2026-10-14):** world tiles **32 × 32**, humanoids **32 × 48**, presentation canvas **640 × 448**; integer-nearest fullscreen with letterboxing. Existing map JSON and collision continue in the older 16-unit coordinate grid and are mapped 2× to presentation pixels while migration proceeds. The legacy 320×224 environment render pass is transitional, not the target resolution for newly authored PNGs.
4. Logical position, collision footprint, draw bounds, anchor, and occlusion region are **distinct data**. Art replacement cannot silently change movement rules.
5. Assets must render deterministically independent of frame rate. Animation time is elapsed simulation time; render frequency only samples its state.
6. No copyrighted game art is copied or traced. Source and license/provenance records are mandatory.
7. Final graphical assets are not drawn in gameplay code. Runtime-generated temporary visuals may remain as clearly labeled fallback/debug assets only.

## 2. Repository structure and stages

```text
art_source/                  # editable originals, artist notes, sources
assets/
  palettes/eldenmere.json
  atlases/terrain/grassland.png
  atlases/terrain/grassland.atlas.json
  atlases/architecture/mountain_village.png
  atlases/architecture/mountain_village.atlas.json
  atlases/characters/caelen.png
  atlases/characters/caelen.atlas.json
  atlases/effects/weather.png
  atlases/effects/weather.atlas.json
  manifests/assets.json      # stable ID -> atlas+region+animation definition
maps/towns/eldenmere.json
engine/assets.py             # manifest loader, validation, atlas cache
engine/world_map.py          # map layers, triggers, collision data
engine/renderer.py           # camera, culling, draw queue, occlusion
engine/animation.py          # state machine, timeline, event sampling
engine/effects.py            # weather/ambient particles and lifetime
tools/validate_assets.py     # offline, deterministic CI checks
tests/fixtures/visual/       # seam sheets, animation strips, reference renders
```

**Pipeline:** editable source → palette/style review → nearest-neighbor native-pixel export → metadata+manifest → automated validation → visual seam/animation review → Pygame integration test → accepted release asset. No generated illustration automatically becomes a production atlas.

## 3. Format, identity, atlas packing

**PNG:** RGBA8, sRGB, lossless, true alpha for cutout sprites; tile backgrounds may be fully opaque. Color-key transparency is forbidden. Disable filter smoothing, mipmaps and half-pixel placement. Atlas width/height must be positive integers; prefer power-of-two dimensions only if a measured renderer/backend need is found. Do not introduce spacing or extruded borders unless atlas metadata records them.

**IDs:** lower-case dot-separated namespace paths, e.g. `terrain.grass.meadow.center_a`, `terrain.path.dirt.edge_n`, `architecture.eldenmere.cottage.roof_left`, `character.caelen`, `effect.chimney_smoke`. IDs are unique across the project and stable after publication. Renames require an explicit alias/migration; no map is allowed to depend on texture cell index. Distinguish *asset ID* from map *instance ID*.

**Region metadata:** texture atlas path, integer pixel rectangle `[x,y,w,h]`, display dimensions, anchor `[x,y]` in local pixels, intended layer, optional animation ID and material tags. Rectangle must be contained within image dimensions and must not inadvertently overlap another region (intentional shared regions explicitly flagged). A static 16×16 terrain region must be 16×16; multi-tile sprites declare independent dimensions.

**Character atlas:** 16×24 frames with a consistent foot anchor, initially `[16,47]`, across directions and poses. Frame order is explicitly declared, never guessed from rows. Motion uses frame sequences and timing, not naive sprite-sheet scanning.

**Packing:** curate by biome/material/function, not per-map snapshot. Multiple small atlases are allowed. Cache atlas surfaces once and obtain immutable subregions; do not load or crop PNGs for every draw call.

### Minimum manifest example (illustrative contract)

```json
{
  "schema_version": 1,
  "assets": {
    "terrain.grass.meadow.center_a": {
      "atlas": "atlases/terrain/grassland.png",
      "rect": [0, 0, 16, 16],
      "anchor": [0, 0],
      "layer": "ground",
      "palette": "eldenmere.outdoor"
    },
    "character.caelen": {
      "atlas": "atlases/characters/caelen.png",
      "rect": [0, 0, 16, 24],
      "anchor": [8, 23],
      "layer": "entities",
      "animation_set": "caelen.world"
    }
  }
}
```

Atlas descriptors may hold regions, tags and source provenance. One manifest resolves semantic IDs; builds fail for unresolved IDs or schema versions they cannot interpret.

## 4. Palette, lighting and pixel rules

- Every environment family declares a named palette with **material ramps** (shadow, base, light, highlight) for grass, wood, masonry, foliage, water, metals and cloth; avoid mixing unrelated color temperatures within one region.
- **Default daylight:** light from visual upper-left; highlights on upper/left-facing planes, primary cast shadows down/right. Roofs, walls, tree canopies and props must agree. Architectural interiors may specify their own explicit light rig (window/lantern), with continuity at door transitions.
- Outlines are darkest material-family shades, not indiscriminate pure black. Pixel clustering and edge contrast must remain readable at 1×.
- Outdoor tiles and character sprites share compatible saturation/value hierarchy: characters/doors/interactables distinguishable from busy ground.
- Animation frames do not shift palette or light direction without an intentional effect. Alternate palettes (night/rain) derive from documented ramps or explicitly authored variants; broad smooth filters must not substitute for base craftsmanship.
- No mixed logical pixel density, antialiasing, bilinear upscaling, blur, or arbitrary image resize.

## 5. Terrain adjacency and autotiling

**Engine concept:** map stores terrain *material* plus optional authored variant/override; a resolver chooses semantic tile IDs from neighborhood topology. Baking the chosen atlas coordinates into a map is forbidden.

- **Organic ground:** use a canonical **47-tile blob** neighborhood scheme (8 surrounding cells, normalized masks, cardinal constraints on diagonals), with explicit documented bit convention and a complete ID-to-mask lookup. Include interior, outside corners, inside corners and straight borders.
- **Grass/path, grass/stone, shoreline:** each ordered material pair defines border priorities and permissible overlap. Cross-material corners and T-junctions need deterministic precedence; an explicit manual override supports artistic exceptions.
- **Water:** directional banks, bends, inner/outside corners, current/highlight animation and bridge joins. Animated water border frames retain exactly the same shoreline geometry so collision and silhouette do not flicker.
- **Cliffs/raised terrain:** separate elevation and face data; do not infer walkability solely from visible slope art.
- **Architecture:** use roof/wall/edge/corner modules with deliberate composition, not blanket 47-blob rules.
- **Variant selection:** seeded stable hash of map ID + cell coordinates + material and a published selection policy; no frame-random variation. An editor may lock a particular variant.
- **Validation:** each transition collection must contain all declared canonical masks, and test scenes include long straight edges, all corner cases, intersections, transitions near structures, and repeat patterns; fail missing variants.

## 6. Map format, layers, depth

Map source retains structured geometry and layered tiles. Preserve the current JSON maps during migration; add a conversion layer rather than breaking existing collision data.

**World draw pipeline (back to front):**
1. `ground`: biome/base terrain
2. `ground_details`: flowers, pebbles, decals
3. `below_entities`: foundations, ground-level props, lower structure parts
4. `entities`: dynamic actors and Y/foot-anchor-sorted world objects
5. `foreground`: tree canopies, roof overhangs, arches, upper walls (optional cutaway/alpha rule)
6. `world_effects`: local particles, smoke, precipitation behind or ahead of actors as tagged
7. `lighting_weather`: restrained full-scene grade, rain haze etc.
8. `screen_ui`: dialogue, menus, HUD, transitions

The weather/effects stages are **render passes**, not permission for every effect to sit above every actor: effects declare specific depth bands and are inserted at the appropriate stage (e.g., distant rain behind sprites, near rain in front; chimney smoke behind a roof edge). Preserve a stable tie-breaker for objects sharing Y.

**Coordinate contract:** map cell origin is top-left; world coordinates are logical pixels; sprite position is its anchor/foot point. A sprite's destination blit top-left is `world_anchor - sprite_anchor - camera_offset`. All game-world positions are integers when rasterized.

**Depth:** a tall object may split into base and canopy/roof overlays with separate draw layers; avoid showing the character walking over a canopy solely because its sprite was drawn first. Occlusion is visual, not collision.

**Performance:** cull offscreen regions, cache immutable atlas surfaces, batch by layer/atlas where practical, avoid per-frame tile image generation and per-frame disk I/O. Measure performance on the target Mac before optimizing prematurely.

## 7. Collision, interaction, transition separation

- Map-level terrain collision and entity/object collision are authored as shapes or small occupancy masks in **world coordinates**, independent of visible sprite boundaries and transparent pixels.
- Solid foot regions are distinct from a character's 16×24 draw box; tree trunks may block while canopy is visually passable behind.
- Doorways are **explicit passable trigger volumes**, not a side effect of coloring pixels like doors. A transition specifies destination map ID, destination spawn ID, optional facing, and prerequisite flags.
- Interactive areas are their own trigger shapes; reaching a visual object should not require overlapping a solid object interior.
- An art-only replacement must not modify collision/interaction/trigger metadata. Any geometry edit is a gameplay change requiring tests and review.
- Existing prototype world collisions are a baseline to preserve; migrate with parity tests for blocked tiles, reachable doors, player spawn positions, and NPC encounters.

## 8. Animation system — required, first-class architecture

Animations are **data-authored timelines referencing PNG frames**, not hard-coded frame indices in `main.py`. The same runner plays characters, creatures, battle actions, props, water, weather strips, lamps and smoke sprites, with specialized gameplay adapters where appropriate.

### 8.1 Animation definition

Each clip specifies ID, ordered `frames` (semantic frame/region IDs, or atlas frame refs), per-frame **duration_ms** (positive integer), playback mode (`loop`, `once`, `ping_pong`, `hold_last`), directional context where relevant, stable local anchor, optional layer and ordered events. Clips for a character are grouped in a state machine (idle, walk, interact, cast, attack, defend, hit, down). Noncombat world actors need **four-direction idle plus three-frame four-direction walks** at minimum as required by the Art Style Guide.

**Example:**
```json
{
  "schema_version": 1,
  "animation_sets": {
    "caelen.world": {
      "initial": "idle_down",
      "clips": {
        "walk_down": {
          "mode": "loop",
          "frames": [
            {"asset": "character.caelen.walk_down_0", "duration_ms": 110},
            {"asset": "character.caelen.walk_down_1", "duration_ms": 110},
            {"asset": "character.caelen.walk_down_2", "duration_ms": 110}
          ]
        }
      }
    }
  }
}
```

For each clip: metadata declares origin, frame canvas, consistent anchors, timing, and visual offsets (if any). If a character can pivot, orientation must come from direction state, not arbitrary art mirroring that breaks asymmetric details.

### 8.2 Time and update semantics

- Animation advances via `update(dt_ms)` from the game's simulation clock; clamp or subdivide abnormal elapsed-time spikes in the application loop, but do not make total playback depend on monitor refresh rate.
- Sampling timeline at a time offset is deterministic; `dt` can cross multiple frame boundaries without losing state. Never rely on `frame += 1 per render`.
- Movement speed and animation playback are separately configurable; walking clip selection depends on movement state/direction, with smooth frame continuity where desired.
- `once` animations emit a single completion signal and must not replay automatically. Pause, freeze-frame, visibility and scene transitions have explicit state policies.
- Random ambient starts use seeded instance offsets, **not** unsynchronized random calls each frame.

### 8.3 Character and NPC animation

**World minimum:** `idle_down/left/right/up` and `walk_down/left/right/up`; each walk contains at least three unique frames, plus 1+ idle frame per direction. Nominal 16×24 canvas and consistent foot anchor. Later interactions may add `talk`, `kneel`, `gesture`, `use_item`, `climb` on a per-actor basis. Facial/emotive overlays are optional and must align.

**Transition examples:** idle → walk on actual movement, walk → idle when halted, interact overrides locomotion where scripted. Facing updates on direction changes. Characters may stand behind foreground objects without altering animation state.

### 8.4 Combat animation and gameplay authority

Combat clips may include `ready`, `approach`, `attack`, `cast`, `defend`, `hit`, `knockback`, `down`, `victory`. Actor-specific clip sets can use larger canvases if documented; battle visual scale must be consistent within a battle scene. Effects such as sword trails, spells, impact sparks and status auras have their **own timed clips and depth bands**.

A combat controller orders the sequence. Animation events such as `windup_end`, `impact_visual`, `projectile_spawn_visual`, `animation_complete` are **presentation cues**. Authoritative damage, hit results, costs and turn legality are calculated by battle systems, not by sprites or rendering frame count. To avoid duplicate hits under lag, event delivery is at-most-once per clip instance; skips fast-forward through events deterministically or follow an explicit skip policy.

### 8.5 Environmental animation and atmosphere

Support world-space looping and one-shot clips for **water currents, ripples, grass sway, waving flags, lantern flame, torches, chimney smoke, drifting leaves, insects, rain, snow, fog, sparks and dust**.

- **Static-repeat animated tiles:** water/tall-grass variants retain edges/anchors and tile seams every frame. Neighboring water tiles may have synchronized phase for seamless current or deterministic offset only if visual seams stay continuous.
- **World props:** chimney/fire/smoke emitters attach to semantic sockets (e.g., `chimney_top`) declared on architecture objects; removing/replacing a roof shouldn't leave floating smoke.
- **Weather:** scene/region weather controllers define intensity, wind vector, particle distribution, spawning bounds and depth split. The renderer supports behind-actor and foreground rain/snow, with camera-safe recycling. Translucency is permitted for weather, not blurred sprite art.
- **Particles:** pooled instances with deterministic optional seeds, lifetime/velocity/gravity/drift, frame clips, opacity or discrete fade ramps, culling. Never allocate a new disk-loaded surface per particle.
- **Atmosphere:** effects express lived-in rhythms (smoke from a kitchen, moving water, a fluttering market banner), not constant distracting animation everywhere.
- **Pause/time:** choose and document whether atmospheric animations pause with game simulation or follow a dedicated presentation clock during dialogue and menus. Default: pause with simulation; exceptions declared per effect.

### 8.6 Animation API boundary

`AnimationLibrary` loads/validates sets; `AnimationPlayer` holds per-instance clip, elapsed time, direction, loops and event cursor; `AnimationSystem` updates players; `WorldRenderer` consumes immutable snapshots (frame asset ID, logical position, anchor, layer, frame transform). Game state never manipulates the pixel data to play a clip. Asset hot-reload is development-only and must invalidate dependent cached regions safely.

## 9. Quality gates and validation

### Automated (blocking CI for new production assets)

1. Metadata schema version and all referenced files/IDs resolvable, unique and case-stable.
2. PNG decodes, declared RGBA8/dimensions match, regions lie inside atlas; no unauthorized frame overlap, empty unexpected region or invalid alpha mode.
3. Region sizes are compatible with declared use; 16×16 tile grid and 16×24 standard humanoid frame contract enforced unless explicit exception.
4. Palette IDs resolve and color deviations conform to approved ramp/tolerance policy; exact palette indexes may be enforced for curated families.
5. Autotile masks complete and all region references exist; edge variants and animated coastline geometry consistency verifiable.
6. Animation clips have 1+ frames, strictly positive durations, valid mode, valid frame IDs and consistent anchors; four directional idle and three-frame walks per direction for standard humanoid production sets.
7. Events within clip duration, uniquely identified if needed; `once` completion and event delivery tested across variable delta sizes and large frame skips.
8. Map IDs and layers resolve; no unexpected modifications to blocked cells, door triggers or spawn reachability when art-only PRs land.
9. Provenance/license fields and corresponding source records present for all final shipped art.
10. Asset loading and playback do not require network resources, external image generators or source-editor applications.

### Visual review (blocking human acceptance)

- 1× logical and integer 3×/4× views; readability, seams, no filtering artifacts.
- Repeated 5×5 and 10×10 terrain patches, every edge/corner/T-junction, roofs and door alignment.
- Outdoor and indoor shared lighting; animated frames free of sprite drift, foot sliding, palette flash or unexpected silhouette change.
- Movement in four directions, obstacle occlusion, tree canopy and doorway passage, animation while camera scrolls.
- Combat impact timing aligns with results, no double visual hits under dropped frames.
- Rain/snow do not hide critical traversal; smoke originates from structures; effect density remains legible.
- Compare old/new collision test vectors and verify an actor can traverse known world routes.

### Review artifacts

For every new atlas family attach: a contact sheet with labeled semantic IDs, complete seams/corners test layout, palette swatches, animation playback preview or frame strip, actual in-engine screenshot at native scale, provenance/license record, and validation output. Any failure requires re-export or metadata correction; attractive concept art alone is insufficient.

## 10. Migration order and release strategy

1. **Asset registry/loader + schema validator** with a tiny authored grass/path PNG set. Keep the current renderer as opt-in fallback only during migration.
2. **Layered world renderer + autotile resolver** for a small sanctuary-adjacent test patch, comparing collision and interaction parity with existing maps.
3. **Humanoid animation runner** with real four-direction 3-frame walks; replace Caelen placeholder, then NPCs.
4. **Architecture kit + foreground masks** for sanctuary, mill, cottage, tree canopy and doorway layering.
5. **Ambient effect subsystem** for water, smoke and weather; test layering and performance.
6. **Battle animation adapters** when the combat system exists; the generic clip/event contracts are established now, but do not prematurely invent combat mechanics.
7. Gradually replace procedural draw code; remove it only after atlas coverage and visual acceptance.

Avoid a bulk conversion of all Eldenmere art before the first complete tile seam + walk animation vertical slice works.

## 11. Change control

This is an authoritative **v1** contract for future art and rendering PRs. Changes to identifiers, schemas, time semantics, coordinate origin, layer names, interpolation, or collision rules require: a versioned design change, compatibility/migration plan, regression fixtures, and review. Art Style Guide governs aesthetic conflicts; this technical specification governs export and runtime contracts. Document exceptions in asset metadata, not ad-hoc code branches.

## 12. Approved pixel-scale migration (2026-10-14)

The user approved Caelen's visually larger, detailed 32×48 sprite as the reference scale for **all** future characters, structures, vegetation and terrain. New artwork must use a coherent 32px tile vocabulary, not simply mix 32×48 character images with 16×16 structures. During the interim, the engine enlarges the current 16-unit map/background by 2× while rendering Caelen's 32×48 atlas without resampling; temporary NPC sprites scale from 16×24 to 32×48. The transition **does not** double movement speed, change collision footprints in map units, or rewrite map coordinates. Future atlas migration should render 32px-native terrain/architecture directly in the 640×448 presentation surface and remove the transitional background upscaling only when parity is verified.

Fullscreen is the default, with F11/F toggling a resizable window, a nearest-neighbor integer scale to fit the display, centered letterboxing for aspect mismatch, and a fitted fallback only when the monitor is smaller than the canvas. Preserve all 4 directional Caelen animations at 32×48 and a consistent foot anchor of [16,47].
