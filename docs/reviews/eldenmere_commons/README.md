# Eldenmere civic commons

The well square now has a connected stone civic surface, a school approach and
a small southern resting edge. The existing well, pail ownership, school,
buildings, residents, scripts, entrances and navigation retain their owners.

| Clean main before PR 5 | Current production rendering |
| --- | --- |
| ![Original well square](before_commons_well_closeup.png) | ![Connected civic paving and resting edge](commons_well_closeup.png) |
| ![Original school approach](before_school_entrance_closeup.png) | ![Civic connection to the school](school_entrance_closeup.png) |

These are native 960×640 initialized-Game views, with disclosed player/camera
fixtures and disposable saves/settings. The opening is disabled; no quests are
seeded, residents moved, routines disabled or replacement scenery painted.
The four civic views also have `_reduced.png` witnesses. The separate coverage
image is a cropped diagnostic mask, not a gameplay screenshot.

[The verification record](observations.json) contains the exact baseline revision,
source hashes, camera/player fixtures, all 13 framework views and pixel counts,
native ground phase hashes, movement traces, doorway checks and Continue results.
[The baseline revision](before_revision.json) identifies clean main
`b47b027d804a167d30988b56c0fb9650a89f48fe`, after settlement PR 4.

The production checks passed:

- Every prior entity, courtyard/workyard ledger, street treatment and cartography
  record is retained. Existing non-ground artwork and grass are unchanged.
- Collision is exactly the baseline union the two declared supports:
  **252 added logical pixels**. Navigation is byte-identical.
- Each of six full native ground phases changes **97,077 pixels**; zero changed
  pixels leave source civic treatment cells plus their one-tile material fringe,
  intersected with the declared **[384, 720, 384, 288]** logical scope.
- All 13 framework views have zero changed pixels outside the scope. Only the
  commons and school views differ; the other 11 views are pixel-identical.
- Four independent well approaches, the south pail/service lane, the school
  link and neighboring household approaches pass walking and running in both
  directions: **24 routes, 2,202 actual Game.update frames, zero replans**.
- The existing school door enters and returns during both walking and running.
  Arrival guards rearm through real movement away from the contact.
- Save/Continue preserves unique civic entities, all three district ledgers,
  solid supports and progress. Two disposable older-checkpoint fixtures put
  only the saved player coordinate inside each new support; ordinary Continue
  recovers safely to the existing town entry **[384, 312]**.
- All four reduced-motion civic views remain pixel-identical at 0 and 600 ms.
  Quest, party, inventory, flags and production source inputs are unchanged.

The well route uses **[526, 900]**, the established south service waypoint.
The gardener's smaller probe can reach her authored **[526, 892]** source contact;
that point already lies too close to the well for the player's 24×12 probe.
The home-to-commons route follows the clear **[552, 714] → [552, 780]** lane;
the pre-existing school/garden collision covers **[576, 756]**.
These fixture choices preserve the production collision and author anchors.

This is a scoped production rendering, movement, doorway and save smoke review,
not a complete quest playthrough or a full gardener-cycle review.

The broader focused suite has **79 passing checks and two confirmed baseline
failures among 81 checks**. Story checks pass (79), core checks pass (167), and
business checks pass (13). The two original well-rendering tests are retained.
[Their clean-main comparison](well_baseline_comparison.json) records the stale
single-entity frame expectation and logical marker/depth test, plus native
evidence that the existing well's opaque front rim covers its idle water glints.
That pre-existing runtime limitation is outside this civic layout change.
The framework water-animation check samples the brook; animated pixels elsewhere
in a normal civic view do not demonstrate moving well water.

Regenerate after creating a fresh, clean-main baseline with the framework tool,
exact map/mask copies and six native ground phase witnesses:

```sh
python tools/capture_eldenmere_commons.py --baseline-dir /tmp/settlement-pr5-before
```

Large full-town ground/mask witnesses stay in the temporary baseline directory;
the committed review retains their hashes and useful native scene witnesses.
