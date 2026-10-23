# Eldenmere — wooden bridge

Status: draft artwork for visual review.

The first bridge runs east–west across the stream, with a **48-pixel-wide flat walking deck**, weathered transverse planks, low timber rails, simple iron straps and warm-gray stone abutments. All colors reuse the approved gate/terrain palette exactly. Two small cream-paper lanterns sway by one native pixel; small downstream wakes animate beside the timber support feet. The deck, railings, thresholds and stonework remain stationary.

## Review previews

- `review_scene.gif`: updated 22×26-tile scene, native 528×624 enlarged 3× to 1584×1872.
- `bridge_closeup.gif`: the bridge, both approaches, Caelan and water beneath it, enlarged 5× to 960×720.
- `modules_review.gif`: west end, two middle alternatives and east end, enlarged 7×.
- Matching PNG files are static first-phase previews.
- `scene_frames/frame_01.png`–`06.png`: native scene phases.
- `review_scene.json`: source frames, placements, terrain extension, character move, elevations and layer order.

Both ends sit on dry banks at the **same elevation**. The walking deck is level with both approaches; stone thresholds are flush and introduce no step or slope. The water surface is below the deck, flowing north to south underneath the east–west crossing. The two middle sections span the water; the end sections rest on the banks. Short timber feet below the near railing meet the water beside the small wakes.

The review extends the previous scene by two grass columns on the right to show the eastern approach. The approved gate is held open using its six matching water phases. Caelan moves from the central path onto the bridge using his unchanged 24×36 right-facing idle, giving a direct scale reference. Other characters, the gate, terrace and earlier example layout stay as they were. This is an art/scale review, not a canonical level or playable bridge.

## Native modules and layers

Each **24×72 module** is one grid column with three 24×24 sprite cells. Four modules form the review's **96×72 prefab**: `west`, `middle_a`, `middle_b`, `east`. Its ground/deck rectangle is `[0,12,96,48]`; twelve pixels project north for the rear railing, and space below the deck holds the near railing, stone/pile feet and water effects. The rail's visual projection can overlap characters, so it has its own foreground layer.

- `modules/<id>/base.png`: static deck, rear rail, thresholds and supports.
- `modules/<id>/foreground.png`: static near rail and its posts.
- `base.png`, `foreground.png`: complete four-column layers.
- `lanterns/frame_01.png`–`06.png`: separate rear lantern/bracket layers.
- `water_shadow.png`: fixed shadow for water beneath the near deck edge.
- `wakes/frame_01.png`–`06.png`: small animated support wakes.
- `frames/frame_01.png`–`06.png`: flattened bridge sprites, including lanterns and rails, without world water effects or characters.
- `bridge.png`: first flattened phase; `bridge_sheet.png`: six phases stacked, 96×432.
- `tileset.json`: module paths, assembly columns, layer paths, native rectangles and timing.
- `palette.json`: reused named material ramps and independent artwork approval status.

Build another length as **west + one or more middle sections + east**. Both middle alternatives repeat and mix; their deck and rail boundary profiles match. Keep the corresponding columns aligned across base, foreground, lantern, shadow and wake layers. `assembly_column` identifies the source column to crop from shared overlays. The deck stays two cells wide as the span grows. This milestone supplies only the east–west orientation.

Use this draw order: water/background, clipped water shadow and wakes, base/rear rail, lanterns, characters, foreground rail. Water effects are clipped to water colors in the review so they never draw over land. The same six 200 ms phases as the existing stream give a 1.2-second loop. Navigation, collision, interaction and map integration remain future work.

Rebuild with `python tools/build_eldenmere_bridge.py`; validate with `python tools/test_eldenmere_bridge.py`. The retained source recipe controls approval state and deterministic exports. Existing artwork and narrative files are unchanged.
