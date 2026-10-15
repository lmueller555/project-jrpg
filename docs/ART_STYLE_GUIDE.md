# Art Style Guide — Project JRPG

**Status:** Authoritative baseline  
**Version:** 1.0  
**Established:** 2026-10-13  
**Scope:** Visual direction, environments, maps, characters, props, animation, and game asset acceptance criteria.

## 1. Purpose and authority

This document is the source of truth for visual assets in Project JRPG. Game content, hand-authored art, AI-assisted art, procedural generators, rendering code, and new design proposals must conform to it. Changes to a mandatory rule require an explicit update to this document through review. When an individual asset conflicts with this guide, the guide wins until revised.

The visual inspiration is **Final Fantasy VI (SNES)**, not an instruction to copy its art. All shipped characters, locations, sprites, music, trademarks, and other creative content must be original or appropriately licensed. We seek a cohesive 16-bit-era fantasy visual language: readable silhouettes, expressive compact characters, hand-placed pixel clusters, rich but controlled palettes, and layered top-down environments.

## 2. Visual pillars

1. **SNES-era readability.** Every interactable object should be understandable at native resolution, including silhouettes and key color contrast.
2. **Cohesive pixel scale.** Every environment, entity, effect, and UI element should share a consistent virtual pixel density.
3. **Expressive within constraints.** Distinct faces, clothing, and character roles are conveyed through shapes and limited pixels rather than large portraits pasted into maps.
4. **Believable places.** Geography, roads, rivers, settlements, architecture, and interior arrangements should tell an internally consistent story.
5. **Gameplay first.** Walkways, entrances, hazards, collision, traversal, and important objects remain legible even in complex scenes.
6. **Original identity.** The visual system should evolve beyond its inspiration; do not trace or reproduce copyrighted game assets.

## 3. Technical baseline

| Item | Baseline | Notes |
| --- | --- | --- |
| Render style | 2D pixel art | Deliberate hard-edged pixels; no painterly smoothing |
| Perspective | Top-down / elevated 3-quarter RPG view | Consistent per scene; no isometric rotation |
| Logical viewport | 640 x 448 pixels (presentation canvas) | Twice the legacy world viewport in both axes, maintaining the same approximate visible map area |
| Display enlargement | Fullscreen integer scaling with letterboxing | Windowed fallback and small-screen fit; nearest-neighbor only |
| Map grid | 32 x 32 presentation pixels | Legacy world coordinates and JSON remain 16-unit cells during migration; drawn at 2× |
| Standard humanoid frame box | 32 x 48 presentation pixels | Caelen's approved sprite establishes the new production scale |
| Basic walk animations | Down, left, right, up; 3 frames each | 12 frames minimum for a moving humanoid |
| Color | Curated per-environment palettes | Prefer reusable ramps; no single absolute global color cap |
| Asset format | PNG with true alpha | No baked checkerboards; no fuzzy halo edges |
| Map authoring | Tile layers plus structured metadata | Maps must be editable and reconstructable, not flattened pictures |

**Decision (2026-10-14):** Caelen's approved 32×48 sprite sets the production character scale. World tiles and architecture target 32×32 presentation pixels. The current 16-cell map coordinate/collision system is intentionally retained and visually magnified 2× as a transitional compatibility layer; new PNGs should be authored at the 32px scale, not fabricated by permanently doubling 16px originals. Presentation viewport is 640×448 and fullscreen uses nearest-neighbor integer scaling with letterboxing. These values require art-level playtesting but are no longer the old nominal 16×24/16×16 target.

A 32 x 48 sprite may overlap more than one 32px presentation tile. This is intentional: its **foot point** (usually bottom-center at the feet) controls tile position, depth sorting, and interactions. Character visual height is not collision footprint.

## 4. Pixel-art craftsmanship rules

- Pixel edges remain crisp at all integer display scales. Disable bilinear/trilinear filtering and antialiasing on gameplay sprites.
- Use intentional pixel clusters and readable value groups; avoid stray single-pixel noise.
- Keep directional light, shadow lengths, line weight, and outline treatment consistent within an area.
- Avoid gradients or semi-transparent blur as a substitute for hand-placed shading. Transparency may be used intentionally for particles, water effects, shadows, or UI overlays when explicitly specified.
- Choose a limited set of shades per material and reuse them consistently. Avoid arbitrary color shifts between assets serving the same biome.
- Maintain coherent material language: wood grain, stone seams, foliage clusters, fabric folds, and metal highlights should look related across the atlas.
- Avoid accidental subpixel rendering, variable pixel block sizes, and mixed-resolution assets.
- Do not directly resize finished low-resolution sprites to a new logical dimension using smooth interpolation.

## 5. Characters and creatures

### 5.1 Proportions and consistency

Characters use stylized, slightly exaggerated 16-bit JRPG proportions: relatively large heads, readable hair and clothing masses, short expressive limbs, and identifiable outlines. Maintain a single standard per character class; do not mix very realistic human proportions with chibi proportions in the same in-world scene without a documented exception.

The nominal humanoid **frame canvas** is 16 x 24 logical pixels; actual opaque pixels may occupy less. Taller humanoids, children, bosses, and large monsters may use larger frames if their size reads intentionally relative to doors, terrain, and standard humanoids.

Every in-world character must have a consistent:
- foot anchor across directions and frames;
- baseline body height and approximate head-to-body relationship;
- directional lighting and palette;
- silhouette across animation frames;
- shadow / occlusion behavior in the engine.

### 5.2 Required movement and export

For moving humanoids, provide idle poses and walk animations for down, left, right, and up. Use a minimum of three frames per direction unless an approved asset-specific spec says otherwise. Mirror left/right only if asymmetrical clothing, weapons, hair, and lighting still make visual sense.

Export aligned frame sequences or an explicitly documented sprite sheet with frame width, frame height, ordering, timing, and foot anchors. No cut-off limbs or frame-to-frame sprite drift. Attack, casting, emotes, knockback, and combat sprites get separate specifications when those systems are designed.

### 5.3 Monsters and NPCs

Creature footprints and visual sizes may differ. Maintain readable class silhouettes and a consistent perspective. NPCs should look native to the same world even if they use fewer animations.

## 6. Overworld and map design

World maps must follow legible geographic reasoning rather than scattering arbitrary symbols:
- Mountain chains form plausible ranges and watersheds.
- Rivers usually originate in elevated or wet terrain and flow downhill toward lakes or seas; confluences are preferred over unexplained splitting.
- Forests, wetlands, deserts, snow regions, and farmland transition according to climate and terrain.
- Settlements have plausible access to fresh water, food, trade, defense, or a deliberate narrative reason for an exception.
- Roads connect meaningful destinations and account for rivers, bridges, passes, and terrain difficulty.
- Natural boundaries influence political territories and travel routes.
- Traversal obstacles should support exploration and progression without making the world feel randomly blocked.

Use distinct **scales of maps**: overworld, regional / route, settlement / dungeon, and interior. Do not imply that one map grid automatically represents the same physical distance at all scales. Record transitions explicitly.

Maps must use structured tile IDs and layers, including at minimum ground, details/decoration, collision/obstacles, above-player occlusion, and gameplay triggers. Where appropriate, include elevation or terrain metadata. A pretty flattened image is a concept reference, not the authoritative playable map file.

## 7. Towns, interiors, and dungeons

- Town footprints should plausibly support their story: dwellings, food access, commerce, water, civic or religious buildings, guards, and paths.
- Streets must leave workable clearance for a moving character. Entrances and exits must be obvious and reachable.
- Architecture should reflect local materials, climate, wealth, function, and culture.
- Indoors, furniture sizes must be proportional to characters; doors, beds, tables, and stairs should read correctly at native resolution.
- Dungeons should have plausible original purpose, progression, spatial navigation, and readable interaction points.
- Decorative density is welcome but must not obscure collision edges or destinations.

## 8. Tilesets, props, and layers

All terrain tiles use the 16 x 16 logical-pixel grid unless an explicit exception is declared. Trees, buildings, cliffs, and other large assets may occupy multi-tile regions. Their draw bounds and collision footprints are independent metadata.

Tilesets should include required transition and edge variants, not just isolated center tiles: grass-to-dirt, coastlines, water edges, corners, cliffs, roofs, walls, doors, etc. Repeating tiles should not create obvious unwanted seams or checkerboard patterns.

Export props as individual transparent PNGs or deterministic sprite atlas regions; provide consistent origins and collision metadata. Avoid baking characters or dynamic events into static background tiles.

Depth sorting must allow characters to pass behind tree canopies, walls, roof edges, and tall props where appropriate.

## 9. UI, effects, and battle presentation

Menus, dialogue frames, type, iconography, particles, spell effects, and combat screens should share the same pixel vocabulary. Text must remain legible at the logical viewport; decorative frames must not compete with content. Combat sprites may use a different camera/framing scale only as an explicit, documented mode with internally consistent sizing.

Do not assume FFVI's exact battle UI, icons, spell effects, or layouts will be duplicated. Those require original design.

## 10. Asset pipeline and file organization

Recommended organization:

```text
assets/
  palettes/
  tilesets/
  characters/
  monsters/
  props/
  ui/
  effects/
maps/
  overworld/
  regions/
  towns/
  dungeons/
  interiors/
docs/
  ART_STYLE_GUIDE.md
```

Each production asset should have:
- a stable name and source/origin record;
- native logical pixel dimensions;
- a transparent export where applicable;
- palette/style references;
- frame and anchor information if animated;
- usage license and provenance;
- collision/trigger/occlusion metadata where relevant.

Keep editable source or generator inputs when available. A concept image is not automatically a final PNG, tileset, sprite sheet, or map specification.

## 11. AI-assisted generation and acceptance

AI-generated art may be used for concept exploration, composition, palette exploration, and candidate assets. **Generated images are not assumed to be game-ready.** Before acceptance:

1. Check native pixel dimensions, grid alignment, and pixel density.
2. Inspect silhouettes, proportions, lighting, and perspective against approved references.
3. Ensure transparent alpha or exact opaque boundaries; remove halos and background residue.
4. Validate tiling, seams, and all edge variants on a repeated map.
5. Validate walk animation frame alignment, direction and timing; reject inconsistent anatomy.
6. Confirm the asset can be placed, layered, and collided with in-engine.
7. Confirm originality, licensing, and provenance.

When precise results matter, hand-correct sprites or create them programmatically instead of assuming image generation has pixel-level accuracy.

## 12. First vertical-slice acceptance target

Before producing a huge world, ship an original **small village and nearby wilderness** art prototype with:
- coherent grass, dirt, path, water, trees, and shoreline/cliff transitions as needed;
- at least three distinct buildings, with usable doors;
- one standard humanoid with four-direction idle and walk sequences;
- a few correctly scaled props and NPCs;
- working collision, scene depth/occlusion, and at least one transition;
- integer-scaled crisp presentation in Python/Pygame.

Evaluate the scene at native resolution **and** 3x/4x scale. Reject assets that only look good enlarged or as standalone illustrations.

## 13. Governance and future decisions

This document specifies **visual** requirements, not story, combat, classes, progression, audio, or overall game mechanics. Those topics belong in separate authoritative documents.

Unresolved choices—exact palette sets, regional architecture, combat presentation, UI typography, final resolution, and final character frame heights—must be recorded as decisions before large-volume asset production. Propose changes with rationale, impact on existing assets, and updated examples. Never treat a single generated image as permission to silently revise the whole visual standard.


## Architecture and seam continuity (2026-10-15)

Reusable architectural geometry, wall/floor material transitions, window/door anchors, and mandatory visual validation are specified in [Architectural Composition](ARCHITECTURAL_COMPOSITION.md). This guidance takes precedence over stale 16px asset examples: production tiles are 32×32 presentation pixels while legacy collision/map cells remain 16 units. The sanctuary migration is a reference implementation, not proof that every transition-art variant already exists.
