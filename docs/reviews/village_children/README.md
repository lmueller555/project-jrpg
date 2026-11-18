# Five village children — approved

- [Liam and the five new children at the same scale](height_comparison.png).
- [All four idle directions](idle_directions.png).
- [All four walking directions](walks.gif) · [slow pose inspection](walks_slow.gif).
- [All four running directions](runs.gif) · [slow pose inspection](runs_slow.gif).
- [Gardener's household: Tessa and Finn](home_a.gif).
- [Village cottage: Rowan and Ada](home_b.gif).
- [South cottage: Pippa](home_c.gif).

The five designs use transparent 24×36 frames and a common foot baseline. Tessa
is 10 (28 pixels visible), Finn 6 (22), Rowan 9 (27), Ada 7 (24), and Pippa 8
(26); approved Liam is 8 and 26 pixels tall. The front comparison and all-facing
idle sheet make the height, hair and clothing differences directly comparable.

The sprite-pack GIFs show all five children in synchronized four-pose cycles.
Walking uses the production 140 ms per pose; running uses 100 ms. Slow review
loops hold each pose three times longer. These are asset inspection loops,
not autonomous movement routines in the world. The characters currently stand
in their assigned homes. Left-facing all-pose contact sheets are also retained
as `walks_left_phases.png` and `runs_left_phases.png`.

Each home preview uses the actual `main.py` room renderer, furniture depth,
lighting and actor placement. Two compact twin beds belong to Tessa/Finn in
home_a and Rowan/Ada in home_b; one belongs to Pippa in home_c. Each child's
bed is individually registered, with its own access point and solid footprint.
The original adult bed and other existing furnishings remain. Caelan is shown
near the entrance for scale; the gardener remains at her existing outdoor job.

Room loops last 10.8 seconds, showing the existing daylight/hearth animations.
No new school attendance, dialogue, sleep or play schedules are introduced in
this review. The same placed child objects persist on cached room re-entry.

Reproduce with `python tools/build_villager_households.py`, then
`python tools/capture_village_children.py`. `captures.json` records timing,
actual room membership and bed registration. The user approved the complete
sprite packs, compact twin beds and household placements for merging into main.
