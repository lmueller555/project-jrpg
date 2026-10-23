# Eldenmere cottage interior foundations — review

Warm plank flooring, cream plaster and exposed timber begin the reusable cottage interior kit. Windows, a closed inside-facing door and the existing stone doorstep match the approved exterior materials. Interiors use expanded, separate room maps; the first review has a 10×8-tile floor. This milestone establishes the room shell before furniture placement.

| Component | Native dimensions |
| --- | --- |
| Floor variants A/B/C | 24×24 each |
| North wall A/B and upper corners | 24×48 each |
| Side walls and lower corner slots | 24×24 each |
| Front cap and entry threshold | 24×8 each |
| Window | 24×30 |
| Closed door | 24×36 |

`tiles/` contains thirteen architecture tiles. `tile_sheet.png` packs them into seven columns of 24×48 padded slots, and `interior.json` records their actual frame sizes and atlas rectangles. `parts/` contains source-derived floors, plaster, timber, window and door appearances. Three floor variations share aligned plank rows and staggered end joints, with restrained highlights for readability.

The 288×288 review room includes its 240×192 floor, a 48-pixel north wall, narrow side walls, low front cutaway and clear 24-pixel entry. The northern closed door is an adjoining-room appearance sample; the south opening is the review entry. Individual floor/wall/support/fixture/contact-shadow layers and their composite are retained in `room/`. `room.json` records registration and placements. The unchanged Caelan sprite remains 24×36.

Subtle daylight uses the window's four glass panes to cast a fixed floor pattern. Nine 600 ms poses change only named floor-light colors over 5.4 seconds. Walls, timber, windows and characters remain still. The floor joints stay visible through the light, and mullion gaps remain unlit. Each `lighting/` image is a transparent overlay with hard alpha; draw structure, daylight, then actors.

Review files:

- `room_review.gif`: enlarged 4× looping room preview.
- `room_review.png`: matching static preview.
- `components_review.png`: architecture components at 5×.
- `scene_frames/`: nine native room frames; GIF encoding may merge held poses while preserving the full timeline.

Rebuild with `python tools/build_eldenmere_cottage_interior.py`; verify with `python tools/test_eldenmere_cottage_interior.py` in the documented Pillow environment. Source/settings live under `assets/source/terrain/eldenmere/cottage_interior/`. The room is an unfurnished art review, not a named residence or final game level; exterior transitions and engine collision/navigation are not implemented. These foundations and their daylight animation await approval.
