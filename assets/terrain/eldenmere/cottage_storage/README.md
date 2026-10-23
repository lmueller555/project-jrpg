# Eldenmere shelf and cupboard — approved

Two reusable static cottage props: a bracketed wall shelf with books and cream pottery, and a closed two-door cupboard with recessed panels and iron handles. Materials match the approved interior furniture. The hearth is deferred.

| Asset | Frame | Native sample | Registration |
| --- | --- | --- | --- |
| Shelf | 48×24 | 40×20 | (4, 2) |
| Cupboard | 48×48 | 40×44 | (4, 2) |

`sprites/` contains individual binary-alpha RGBA assets. `sprite_sheet.png` is a 96×48 atlas with two padded 48×48 cells. `storage.json` records actual atlas rectangles, palette, source recipe, mounting and suggested cupboard floor occupancy. Cupboard doors are closed artwork; collision and interaction are not implemented.

Review files:

- `room_review.gif`: enlarged 4× looping interior, 1152×1152, 5.4 seconds.
- `room_review.png`: matching still.
- `components_review.png`: shelf and cupboard enlarged 8×.
- `storage_layer.png`: native room-sized prop layer.
- `scene_frames/`: nine native 288×288 scene frames.

The shelf mounts in the clear north-wall bay beside the door; the cupboard sits below the right window. Windows, door, original character and approved bed, table and four chairs stay clear and unchanged. The central 72px path remains open. Only the approved daylight changes; the cupboard obscures projected floor light behind its body. This is an illustrative expanded separate room for art review, not a final household layout.

Rebuild with `tools/build_eldenmere_cottage_storage.py`; verify with `tools/test_eldenmere_cottage_storage.py` in the documented Pillow environment. Source/settings live under `assets/source/terrain/eldenmere/cottage_storage/`. These designs are approved for main.
