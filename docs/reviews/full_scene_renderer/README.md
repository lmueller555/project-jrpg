# Full-scene renderer implementation review

The 480×320 gameplay viewport now composes a complete 960×640 scene in
`rendering.WorldCanvas.native`. Explicit primitive/transform adapters preserve
logical coordinates and native detail through exploration, combat, cinematic
layers, occlusion, lighting, Gallery/playtests and snapshots. Final presentation
uses that complete scene before display-space UI. The old detailed-actor patch
repair path is removed. No PNG, animation frame, collision export, or gameplay
coordinate was changed.

The [visual art standard](../../VISUAL_ART_STANDARD.md#runtime-apis-and-metadata)
is the API and sizing reference. This directory records implementation evidence,
not another construction guide.

## Compatibility and migration limits

Legacy artwork keeps density 1 and its existing logical footprint. New banks
explicitly declare density 2. Iselin retains her original approved artwork.
Terrain chunks made exclusively of legacy tiles retain their original raster;
declared 2× tiles select native chunks. Legacy aerial and Ice Reaper scenic
projections keep their logical sampling grid, then compose into the native
scene before actors/effects. Their documented density metadata enables native
projection when those backdrops are rebuilt. The rune, actor source projections,
foreground, intermediate layers and transitions preserve native detail now.
A synthetic projection test verifies that a single native texel survives each
native projection switch. Cave light-field sampling remains logical while its
multiplier covers the full scene and emission masks retain source detail.

A bare `pygame.draw`, pixel-array write or ordinary Surface `blit` consumes only
the compatibility mirror. Future world drawing must use the documented adapters
or explicitly synchronize a shader's native result and mirror. Neither the new
renderer nor this review certifies unconverted artwork as rebuilt.

## Draw benchmark

[benchmark.json](benchmark.json) retains baseline and renderer measurements.
The baseline is commit `9cfc8e1cc97ffffb63beb5ec27ad427d92780808`, with original
runtime Python files and unchanged assets. Both runs use the same interpreter,
SDL dummy 960×640 display, four warmup draws and 60 measured draws per scene.
Runs were sequential, without concurrent test processes. Temporary save/settings
paths isolate user progress. Simulation update is excluded. The moving-camera
samples advance the aerial gate and Ice Reaper cameras by 1/60 second per draw;
static frames alone would hide their projection cost.

| Scene | Baseline median ms | Renderer median ms | Renderer p95 ms |
| --- | ---: | ---: | ---: |
| town | 1.046 | 2.737 | 3.155 |
| dining | 0.899 | 2.473 | 2.970 |
| cave | 1.093 | 2.960 | 3.252 |
| overworld | 4.508 | 5.917 | 14.811 |
| battle | 4.466 | 5.795 | 8.591 |
| regent_arrival | 2.080 | 3.803 | 4.222 |
| aerial_camera_motion | 6.236 | 8.689 | 27.986 |
| ice_reaper_opening | 4.868 | 14.623 | 16.193 |
| ice_reaper_camera_motion | 32.216 | 37.179 | 48.203 |

Exploration and combat samples remain below 16.7 ms at p95 on this host, but
these are draw-only measurements, not a guaranteed 60 FPS simulation budget.
The moving Ice Reaper sequence remains CPU-heavy: approximately 37 ms median
versus 32 ms baseline, exceeding a 33.3 ms draw budget. Its native rune retains
more detail. Further projection optimization and target-hardware profiling are
needed before converting those legacy cinematic backdrops to native sampling.
The aerial p95 also exceeds 16.7 ms. Do not infer universal performance from
warm/static samples or the SDL dummy driver.

The immutable transform/normalized-art cache is bounded at 32 MiB (12.8 MiB
in this run). Projected banks use 64 MiB LRU budgets, including both buffers;
individual oversized projections remain transient. Terrain retains its existing
64 MiB budget (6.75 MiB for 12 legacy chunks here). The independent process peak
RSS was 1250.7 MiB baseline and 1136.7 MiB renderer across multiple game/Gallery
instances. Those high-water marks include decoded assets, audio and scene
initialization; they are not renderer-only memory measurements.

Reproduce with `python tools/profile_renderer.py --frames 60 --output /tmp/renderer.json`.
Optional `--capture /tmp/renderer-captures` captures private inspection frames;
no new visual previews or source artwork are committed in this PR.

## Verification

Focused checks cover exact native texels, half-unit anchors and edge clipping,
logical collision, metadata validation, density-selected projections, shared
subsurfaces, transforms, foreground alpha/depth, source-atlas sampling, snapshots,
BattleTransition capture independence, cache eviction and ordinary Pygame/UI
compatibility. The actual World loader and streamed 2× terrain chunks have
integration coverage. Existing Iselin gait, cave illumination, source-art,
cinematic, environment and UI regressions were also exercised.

The release playback batch passed 20 checks, including every registered Gallery
scene completing through rendered dialogue/real input and quest playtest
sessions. Earlier focused regression batches passed 85, 90 and 73 checks
(overlapping coverage, not a sum). Final verification is recorded below.

Private production-frame inspection covered town proportions, dining-room
occlusion, cave lighting, terrain, battle and moving Ice Reaper/rune composition.
These checks assess rendering integration; this PR changes no character drawing
or object-interaction choreography.

### Existing baseline failures

The broader gameplay batch ran 118 tests and reported seven failures/nine errors.
Every failing/error description reproduced on the unchanged baseline runtime:
old battle-status fixtures omit the Items menu, three Lucan guest boss helpers
expect battle entry before the current rescue trigger, and the sanctuary boss
route fixture stalls at reserve coordinates (444,642) en route to (774,642).
The door test separately expects 13 rooms while the current map has 15; this
also reproduces on baseline. These unrelated expectations were not rewritten to
make the renderer PR appear fully green. Full-suite success is not claimed.

### Final combined run

143 tests passed with:

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest \
  test_rendering test_dense_art test_regent_aerial test_ice_reaper_action \
  test_ice_reaper_rune test_regent_road_pan test_overworld_streaming \
  test_gallery_session test_quest_playtest_session
```

The final density-only run also passed all 16 checks after completing native
projection density registration. All changed Python files compile, changed
Markdown file links resolve, and `git diff --check` passes.
