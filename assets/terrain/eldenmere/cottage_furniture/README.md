# Eldenmere basic cottage furniture — review

An approved wooden bed with a cream pillow and folded sage quilt, an approved worn plank table, and a refined chair in down, up, left and right facings. Bed and table artwork and placements are unchanged. All sprites are static, use binary transparency and retain native pixels. Chairs use only the existing wood ramp and outline.

| Asset | Export frame | Sample size | Registration |
| --- | --- | --- | --- |
| Bed | 48×72 | 32×60 | (8, 6) |
| Table | 48×48 | 48×38 | (0, 4) |
| Chair down | 24×36 | 18×30 | (3, 4) |
| Chair up | 24×36 | 18×27 | (3, 7) |
| Chair left / right | 24×36 | 18×31 | (3, 3) |

`sprites/` contains individual RGBA assets. `sprite_sheet.png` uses six 48×72 padded cells in three columns (144×144); `furniture.json` records each frame's actual atlas rectangle, asset approval status, suggested local floor occupancy, palette and source recipe. Direction means the direction a seated person would face. The up-facing sprite shows the chair's back; right mirrors left. Chairs share a baseline at y=34 and have narrower, shallower seats than the initial review. `chair.png` remains a default alias for `chair_down.png`. Occupancy is placement guidance; collision and interactions are not implemented.

Review files:

- `room_review.gif`: 4× looping furnished-room preview, 1152×1152, 5.4 seconds.
- `room_review.png`: matching still.
- `components_review.png`: 6× furniture views, with an original character scale reference at 3×.
- `furniture_layer.png`: native room-sized placement layer.
- `scene_frames/`: nine native 288×288 frames using the approved daylight overlays.

The expanded separate room and original Caelan are unchanged. The approved bed and table keep their positions. The up-facing chair sits below the table; the down view sits below the bed; left and right views occupy the lower left for comparison. A clear 72px central corridor connects the open south entry with the north door appearance sample. This remains an illustrative generic art review, not a finished level or assigned residence. Furniture does not move; only the approved floor daylight changes.

Rebuild using `tools/build_eldenmere_cottage_furniture.py` and verify with `tools/test_eldenmere_cottage_furniture.py` in the documented Pillow environment. Source and settings live under `assets/source/terrain/eldenmere/cottage_furniture/`. The bed and table are approved; the refined chair's four directions await approval.
