# Eldenmere shelf and cupboard source — approved

A wall shelf with three muted books, a cream jug and bowl, plus a closed two-door cupboard with recessed panels, small iron handles and short feet. Both use the approved warm wood palette and the same orthographic top-down camera as the cottage furniture. These props are static; the room retains its approved daylight animation. No hearth is included.

`storage_concept.png` retains the generated source, originally `/workspace/generated_images/exec-da5a7a63-d1f0-48ae-849d-17036d540055.png`. The approved furnished room supplied the visual reference. The committed copy makes rebuilding independent of that workspace path.

`recipe.json` records source crops, nearest-neighbor sample sizes, frame registration, named palette and placements. The shelf sample is 40×20 inside a 48×24 frame, leaving transparent padding; the cupboard is 40×44 inside 48×48. Magenta removal uses red >160, blue >120, and both > green+70. Surviving RGB samples map to the nearest allowed material color. In the cupboard's native handle sample region `[16,20,8,7]`, source gray/blue pixels (RGB spread <24, or green and blue above red) use the iron ramp so both small handles remain readable. All exported alpha is binary. No smoothing, dithering or runtime resizing is used.

Wood, linen, iron and slate reuse approved interior material colors; the books reuse the quilt's muted sage shades. Native source parts are retained here and copied to the runtime pack. The atlas is 96×48 with two padded 48×48 cells and each actual frame rectangle recorded in metadata.

The 288×288 review adds a shelf at `[100,44]` to the empty north-wall bay immediately left of the door, and a cupboard at `[204,60]` below the right window. Their opaque pixels leave the windows, door, beams, original furniture and Caelan clear. The shelf is wall mounted; the cupboard's local floor occupancy `[4,30,40,16]` describes its base, with the upper body projecting onto the wall. This is placement guidance, not implemented collision. The 72px central corridor stays clear. Existing room fixtures and all approved furniture remain unchanged and keep their positions.

The builder reads the approved interior structure, nine daylight overlays and furniture layer without rewriting them. Draw order is structure, approved daylight, approved furniture, storage, original Caelan. Cupboard pixels correctly obscure any floor light behind them. Review placements remain illustrative, with no named residence or final level assignment.

Build: `PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_cottage_storage.py`.

Check: use the same interpreter with `tools/test_eldenmere_cottage_storage.py`. The review loop is 4× nearest-neighbor enlargement, nine 600ms source frames, 5.4 seconds total; GIF encoding may combine held poses. The component board is enlarged 8×.

The shelf and cupboard designs are approved. Door interactions, alternate arrangements, engine collision and the animated hearth remain future work.
