# Eldenmere well square — review

Status: awaiting user review.

- [Updated overhead town layout](town_layout.png): the actual actor-free runtime overview, with door markers and gold outlines identifying the new square and southern connection.
- [Before and after the commons](commons_before_after.png): the local layout change at the same native scale.
- [Enlarged in-game square](well_square.gif): Caelan walks around all four sides of the solid well using actual game controls and collision.
- [Well close-up](well_closeup.gif): a full shaft-water cycle, with Caelan for scale.
- Still views: [square](well_square.png), [well](well_closeup.png).

Run `python main.py` and head south from the sanctuary along the western lane to the commons. The in-game map labels it **Well square**. The new well, paving, rounded dirt edges and southern path are installed in the playable town. Existing houses, quest destinations, bridges and descending water routes retain their placement. The west side of the square remains available for future gatherings.

The water glints are ambient. The hand-operated windlass remains still; there is no unattended bucket-lifting cycle. Drawing water and moving the gardener's collection task to the well can be added after the asset/layout review.

`tools/capture_eldenmere_well.py` reproduces these captures with the runtime renderer. `before_overview.png` retains the prior town overview from commit `1ae774a5c8901b7f15cc4af8163fde8c1377e869`. `capture.json` records the new registrations and completed walk. GIF colors/timing are verified against source captures. Tests cover collision from each side, a full walking ring, the southern connector, drawing approaches, roof occlusion, water-only animation, gathering clearance, all existing route destinations and building door round trips.
