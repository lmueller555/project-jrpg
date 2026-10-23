# Eldenmere garden fence and gate — approved

A low, weathered two-rail fence uses cottage-brown wood, lighter worn tops, small knots and restrained moss at the post bases. Two subtle rail-wear appearances reduce repetition. There are no cloth ties or hanging details. Fence posts, rails, hardware pins and ground shadows remain fixed.

Thirty reusable modules cover every nonempty cardinal connection mask in both wear appearances: horizontal/vertical runs, four corners, four junctions, a cross and four end posts per appearance. Each places on one 24×24 ground cell. Its 24×48 padded drawing frame has ground rectangle `[0,20,24,24]` and post anchor `[12,32]`; the taller frame accommodates projected post/rail overhang. Posts stand 18 pixels high, with rails 16 and 6 pixels above the ground anchor.

`modules/<connections>_<wear>/` contains `shadow.png`, `rails.png`, `post.png` and their composite `module.png`. `modules.png` packs all thirty frames; `fence.json` records connections, dimensions, ports and sheet rectangles. Across a placement group, draw shadows, then all rails, then all posts. Source rail samples and native posts are retained in `parts/`.

The garden gate uses a 48×48 padded frame, 18-pixel fixed posts, dark iron pins, a small latch and a 24×14 braced panel. Its opening is a full 24 pixels wide. The latch lifts before the gate swings north into the garden, reaches its stop, rebounds one pixel and settles. `gate/` contains eight poses, separate leaves, fixed layers, panel/latch parts, open/closed states, a sheet and `gate.json`. Opening/closing play once when triggered; the repeated use in the review is a demonstration, not an autonomous game behavior. No engine collision or navigation is implemented.

Review files:

- `garden_closeup.gif` / `.png`: 4× cottage, enclosure and gate demonstration.
- `review_scene.gif` / `.png`: full 40×54-tile review scene at 2×.
- `modules_review.gif` / `.png`: representative modules and animated gate at 6×, with unchanged Caelan and gate at matching 3× scale.
- `scene_frames/`: 108 native 960×1296 frames at 100 ms.
- `review_ground.png` / `review_path.png`: retained background and dry path layers for reconstruction.

The enclosure sits beside the existing heather cottage in a dry eastward scene extension. Its path connects to the cottage road and continues through the opening; existing plants animate inside the garden, with room left for the gate swing. The full 10.8-second loop retains all previous animation timing and repeats the gate demonstration twice. Native structural layers remain static. GIF holds may merge while retaining exact pixels and timing. This is an asset-review layout rather than a playable or canonical village map.

Rebuild with `python tools/build_eldenmere_garden_fence.py`; verify with `python tools/test_eldenmere_garden_fence.py` in the documented Pillow environment. Source settings live under `assets/source/terrain/eldenmere/garden_fence/`. The fence and garden gate designs and animations are approved for main.
