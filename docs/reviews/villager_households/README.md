# Villager parents and assigned homes — awaiting review

- [All three parent pairs](parent_pairs.png) — approved sprite reference board.
- [Gardener's home / home_a](home_a.gif) — father inside; mother working outside.
- [Blue and rust pair / home_b](home_b.gif).
- [Plum and slate pair / home_c](home_c.gif).
- [Assigned homes on the town map](assigned_homes.png).

Room loops use the actual game renderer and placed actors at native pixel
scale enlarged 2×. All rooms retain their existing furniture, daylight and
hearth animations. Caelan is visible near the entrance for scale. The parent
board is a labeled appearance reference, separate from runtime placement.
The gardener is the existing outdoor NPC and has not been cloned into her home.

The five newly placed adults are stationary and silent. Each couple has linked
partner/home metadata. Names, ages, children and further daily routines remain
open. All three 13×10 homes retain clear entrances and furnishing access.

Reproduce with `python tools/build_villager_households.py`, then
`python tools/capture_villager_households.py`. `captures.json` records home
membership and actual actor presence; `validation.json` records verification.
This review branch builds on the pending school addition and is not merged
into main.
