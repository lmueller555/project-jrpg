# Eldenmere Sanctuary — Production Asset Checklist and First Art Pass

**Status:** AUTHORITATIVE art production checklist v1.0; the integrated atlas is a **first-pass implementation, not a final quality approval**.  
**References:** [Art Style Guide](ART_STYLE_GUIDE.md), [Asset and Renderer Architecture](ASSET_RENDERER_ARCHITECTURE.md), [Chapter 1](narrative/game_01/CHAPTER_01.md).

## Visual brief

Eldenmere Sanctuary must read as a warm mountain-village sanctuary used for practical service, study, memory, and communal meals. Morning sunlight enters through north-wall windows, creating gently breathing shafts, warm stone highlights, and drifting dust. All environment art uses the approved 32×32 production scale so Caelen's 32×48 character retains his proper proportions. Lighting must enrich, never obscure, his silhouette.

## Exact production checklist

| Asset / system | ID / family | Size / rule | First pass |
|---|---|---|---|
| Warm fitted-stone floor | `interior.sanctuary.floor` | 32×32 seamless | Implemented |
| Worn floor variation | `interior.sanctuary.floor_variant` | 32×32 | Implemented |
| Stone wall courses | `interior.sanctuary.stone_wall` | 32×32 | Implemented |
| Timber / masonry trim | `interior.sanctuary.wall_trim` | 32×32 | Implemented |
| Tall glazed sanctuary window | `interior.sanctuary.window` | 32×32 module | Implemented |
| Woven runner | `interior.sanctuary.rug` | 32×32 module | Implemented |
| Communal table | `interior.sanctuary.table` | 32×32 module | Implemented |
| Records shelving | `interior.sanctuary.bookshelf` | 32×32 module | Implemented |
| Devotional altar | `interior.sanctuary.altar` | 32×32 module | Implemented |
| Flowers/herbs in vase | `interior.sanctuary.flowers` | 32×32 | Implemented |
| Village doorway | `interior.sanctuary.door` | 32×32 module | Implemented |
| Worn wooden floor boards | `interior.sanctuary.planks` | 32×32 | Implemented |
| Votive candles | `interior.sanctuary.candles` | 32×32 | Implemented |
| Bench | `interior.sanctuary.bench` | 32×32 module | Implemented |
| Timber support beam | `interior.sanctuary.beam` | 32×32 | Implemented |
| Sacred floor motif | `interior.sanctuary.motif` | 32×32 | Implemented |
| Directional window shafts | `engine/sanctuary_visuals.py` | Native pixel alpha composite | Implemented |
| Slowly pulsing warm glow | `draw_sunlight` | Bounded alpha, non-flashing | Implemented |
| Floating dust motes | `draw_sunlight` | Deterministic slow motion | Implemented |
| Candle flame animation | `effect.sanctuary.candle` | Loop, additional PNG frames | Later |
| Distinct furniture silhouettes and wall/roof occlusion | Composite atlas | Custom multi-tile variants | Later |
| True window alcove, side walls, stair and structural detail | Modular wall family | Collision-preserving | Later |
| Ambient graded indoor shadows, occlusion and contact shadow | Renderer passes | Bounded, palette-aware | Later |
| Interior lighting in cutscenes/time-of-day | Lighting states | Morning first, later evening/night | Later |

## Current production constraints

The first atlas is `assets/atlases/interiors/sanctuary.png`, containing a 256×128 RGBA sheet of sixteen 32×32 modules; individual regions are declared by semantic ID in `assets/manifests/assets.json`. The interior renderer draws them directly to the 640×448 presentation canvas—**not** through the old 16px placeholder upscale. Caelen remains on the character entity layer. Source map collision, triggers, door coordinates and geometry remain unchanged.

The first art pass adds repeatable native materials and sunlight effects but is **not declared visually final**. Some complex furnishings are assembled by repeating compact modules; they require bespoke larger silhouettes before final art sign-off. The north wall, altar, records corner and furnishings must ultimately be reviewed together in actual Pygame screenshots.

## Lighting contract

Two upper wall windows project golden angled beams into the occupied room. Each shaft combines a broad faint shape, a brighter interior, and a small warm floor pool. Subtle sine-wave breathing (only a few alpha values) and a few slow drifting motes give a lived-in feeling without overwhelming the screen. Rendering happens in logical integer pixels with alpha—no blurry scaling or modern bloom. The scene remains legible even with effects hidden.

## Acceptance tests

1. Atlas decodes in Pygame; every semantic region fits the texture.
2. Room loads without changing the 16-unit tile map, collision mask or exit transition.
3. Caelen remains visually distinguishable when walking through sunlight.
4. Sunlight has stable placement at the north windows and remains gentle in motion.
5. No flicker caused by random per-frame redraw; no soft interpolation.
6. Existing exterior display and terrain remain unaffected.
7. A human reviewer examines screenshots at 1× presentation resolution and at fullscreen integer scale before declaring art final.
