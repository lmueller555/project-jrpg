# Eldenmere — fieldstone terraces, steps and spillway

Status: design and artwork approved following user review.

Warm gray, loosely coursed fieldstone uses the existing terrain stone midtone `#969284`, with a new restrained brown-gray-to-cream stone ramp. Grass, moss, dirt and water reuse the approved material ramps exactly. Source-derived stones have worn corners, sparse chips and small moss patches. Structural pixels stay still throughout playback.

## Review scene

- `review_scene.gif`: updated 20×26-tile scene at 3× enlargement, 1440×1872 pixels.
- `terrace_closeup.gif`: terrace, stairs and spillway at 4× enlargement, 1344×960 pixels.
- `modules_review.gif`: all 20 tile modules at 6× enlargement, with labels.
- Matching PNGs provide static first-phase previews.
- `review_scene_frame_01.png`–`06.png`: native 480×624 scene phases.
- `review_scene.json`: placements, elevation, materials, channel routes, characters and framing.

The upper sixteen tile rows preserve the approved irrigation scene pixel for pixel. Below that, one enclosed grassy terrace carries a connected upper channel, a small settling outlet, a south-facing staircase and a spillway into the lower channel. Mira stands on the upper level and a female NPC on the lower dirt approach. Native 24×36 character art is unchanged. The scene illustrates art, scale and elevation; it is not a canonical village map or implemented gameplay.

## Modules and dimensions

Each grid cell remains **24×24**. A single terrace's exposed front wall is **24 pixels high**, including the narrow coping. There are three interchangeable front textures, left/right outside corners, inside corners and exposed ends; short left/right side faces; a back coping edge and two back corners. All three front alternatives have matching boundary profiles for mixing along a wall. Side and back modules use transparency over grass.

The **south-facing staircase is 48×48**, split into four 24×24 quarters in the atlas and also exported as `stairs_south.png`. Four broad worn treads have low stone cheeks; the central 34 pixels are the visual walking area. The upper landing is north and the lower landing south. It represents a 24-pixel level change. Compacted dirt blends into the landing and approach using the approved dirt blob tiles. Other stair directions and higher walls are future milestones.

The **south-facing spillway is 24×48**, split into two vertically adjacent cells. Its northern eight-pixel water port passes through stone coping, narrows into a falling thread and reaches a shallow stone-edged basin. A southern eight-pixel port feeds the lower channel; its shallow edges and earth banks match the irrigation pack. Water and splash pixels alone animate, on the shared six-phase, 200 ms clock (1.2 seconds per loop). Falling highlights move downward; impact flecks and spreading ripples stay within the fixed water mask. There are no moving walls, stair pixels or shoreline outlines.

## Exports and use

- `tiles/`: 18 static native tiles (14 masonry modules and four stair quarters).
- `frames/frame_01.png`–`06.png`: 120×96 atlases, five columns by four rows, 20 tiles per phase.
- `terraces.png`: six atlases stacked vertically, 120×576; 120 tile slots in total, with static masonry repeated.
- `spillway/frame_01.png`–`06.png`: complete native 24×48 animated prefabs.
- `tileset.json`: atlas rectangles, frame timing, prefab dimensions, ports and stair elevation.
- `palette.json`: named material colors and independent artwork approval status.

Use the complete stair and spillway prefabs, or place their quarters together using the recorded rectangles. Play the spillway with the same phase index as its connected stream/channels. Static wall modules are drawn behind characters. Keep upper ground above the front coping line and the stair's north landing connected to it; its southern approach lies below the wall. Corner and end modules support later layouts but are not a 47-tile terrain blob system. Collision and navigation still need implementation when these assets enter a playable map.

Rebuild with `python tools/build_eldenmere_terraces.py`; validate with `python tools/test_eldenmere_terraces.py`. The retained source recipe controls approval status and deterministic exports. Existing terrain, sprites and narrative files remain unchanged.
