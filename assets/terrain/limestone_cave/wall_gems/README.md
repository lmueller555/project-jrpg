# Embedded cave wall gems

Status: pending visual review; not merged into the live game.

Red, Blue, Green, White, Orange and Purple gemstones sit flush inside
chipped limestone cavities. Fixed stone lips partially cover each
mineral core. These modules have no floor footprint or standing shards.

Each color has three native silhouettes and six frames of increasing
facet brightness. Anchors point to the gem center, not the floor.
`emission_bounds` records the core rectangle; the rock surround is
kept below the production renderer's mineral emission thresholds.

The existing six-second cave pulse selects the frame and illuminates
nearby walls, floor and characters through an exposed light root.
The colors do not establish elemental relationships.

Rebuild with `python tools/build_wall_gems.py`; append `--check` for a
read-only deterministic validation. The editable source recipe is
`assets/source/terrain/limestone_cave/wall_gems.json`.
