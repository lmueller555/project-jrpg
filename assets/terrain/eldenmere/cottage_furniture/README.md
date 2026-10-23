# Eldenmere basic cottage furniture — review

A wooden bed with a cream pillow and folded sage quilt, a worn plank table, and a simple south-facing chair. This first set uses the approved interior wood and linen palette with three new quilt colors. All sprites are static, use binary transparency and retain native pixels.

| Asset | Export frame | Sample size | Registration |
| --- | --- | --- | --- |
| Bed | 48×72 | 32×60 | (8, 6) |
| Table | 48×48 | 48×38 | (0, 4) |
| Chair | 24×48 | 20×38 | (2, 4) |

`sprites/` contains individual RGBA assets. `sprite_sheet.png` uses three 48×72 padded cells; `furniture.json` records each frame's actual atlas rectangle, suggested local floor occupancy, palette and source recipe. Occupancy is placement guidance; collision and interactions are not implemented.

Review files:

- `room_review.gif`: 4× looping furnished-room preview, 1152×1152, 5.4 seconds.
- `room_review.png`: matching still.
- `components_review.png`: 6× furniture views, with an original character scale reference at 3×.
- `furniture_layer.png`: native room-sized placement layer.
- `scene_frames/`: nine native 288×288 frames using the approved daylight overlays.

The expanded separate room and original Caelan are unchanged. The bed sits on the left; the table and chair sit on the right. A clear 72px central corridor connects the open south entry with the north door appearance sample. This remains an illustrative generic art review, not a finished level or assigned residence. Furniture does not move; only the approved floor daylight changes.

Rebuild using `tools/build_eldenmere_cottage_furniture.py` and verify with `tools/test_eldenmere_cottage_furniture.py` in the documented Pillow environment. Source and settings live under `assets/source/terrain/eldenmere/cottage_furniture/`. These furniture designs await approval.
