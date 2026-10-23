# Eldenmere cottage kitchen — review

Three static reusable kitchen assets matching the approved interior palette:

| Asset | Frame | Native sample | Registration |
| --- | --- | --- | --- |
| Counter with cutting board | 48×48 | 44×34 | (2,8) |
| Ceramic washbasin on stand | 24×36 | 20×28 | (2,4) |
| Narrow open pantry | 24×48 | 22×44 | (1,2) |

`sprites/` contains binary-alpha RGBA assets. `sprite_sheet.png` is a 144×48 atlas with three padded 48×48 cells; `kitchen.json` records actual rectangles, palette, source recipe and suggested floor footprints. Kitchen props, basin water and pantry contents are static. Collision and interaction are not implemented.

- `room_review.gif`: enlarged 4× looping interior, 1152×1152, 10.8 seconds.
- `room_review.png`: matching still.
- `components_review.png`: all three props at 8×.
- `kitchen_layer.png`: native room-sized kitchen placement layer.
- `approved_furnishings_layer.png`: read-only source sprites assembled in the new illustrative arrangement.
- `scene_frames/`: 36 native 288×288 room frames with the unchanged hearth/daylight timing.

Counter and washbasin sit below the right window; pantry sits below the wall shelf. The original cupboard moves beside the bed and one dining chair is displayed. Bed and table retain their positions; all previously approved artwork and review packs are unchanged. The central 72px route and windows/door stay clear.

This remains a 10×8-floor asset showroom. The proposed cottage-size layouts in `docs/art/COTTAGE_INTERIOR_PLAN.md` are separate discussion work. Rebuild using `tools/build_eldenmere_cottage_kitchen.py`; verify with `tools/test_eldenmere_cottage_kitchen.py` in the documented Pillow environment. Source and settings live under `assets/source/terrain/eldenmere/cottage_kitchen/`. Kitchen designs await approval.
