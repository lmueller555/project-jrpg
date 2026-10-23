# Elira's bridge cottage — approved

Furnished compact 10×10-floor cottage with memorial festival lantern, high shelf and two-step stool for the opening delivery quest. Native terrain is 24px; Caelan remains 24×36. All approved furnishings, the room envelope, entry, chimney and character placement are preserved.

- `room_states_review.gif`: synchronized looping before/after comparison at 3×, 1800×1110, 36 × 300ms = 10.8 seconds.
- `room_states_review.png`: matching first frame.
- `before/room_review.png`, `after/room_review.png`: individual room states at 4×.
- `before/scene_frames/`, `after/scene_frames/`: native 288×336 room frames.
- `components_review.png`: enlarged lantern, stool and shelf states.
- `sprites/`: transparent native unlit lantern, stool, shelf with lantern and shelf after removal.
- `blocking.png`, `navigable_centres.png`: conservative 24×12 actor-probe planning masks.
- `room.json`: placements, approach, state assets and frame timing.

The lantern occupies a clear space between the approved shelf's books and pottery. After retrieval, the same shelf stays in place and only the lantern disappears. The fixed stool remains beneath it. Existing fire and daylight animate identically in both panels; the lantern is stored unlit. This illustrates quest asset states, not a playable retrieval or climbing animation.

Rebuild with `tools/build_elira_interior.py`; validate with `tools/test_elira_interior.py`. Retained source, palette and crop recipe are under `assets/source/terrain/eldenmere/elira_interior/`. The lantern, stool and before/after household dressing are approved for main.
