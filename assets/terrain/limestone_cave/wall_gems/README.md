# Embedded wall microcrystals

Status: pending visual review; not merged into the live game.

Red, Blue, Green, White, Orange and Purple microcrystals follow
irregular branching seams in limestone. The transparent modules leave
the existing rock visible between separated mineral grains. There are
no large gemstones, bezels, standing shards or floor footprints.

Every color has three fields containing 24, 28 or 32 tiny facets.
Individual grains measure 1-4 by 1-5 native pixels, mostly 2 by 3.
`core_components`, `crystal_sizes` and `crystal_count` record this
scale. `emission_bounds` encloses the complete field, while each
component records one separated grain. Anchors identify field centers.

Six frames vary brightness only. Neutral hairline crevices and small
rock lips stay fixed. The production six-second pulse controls the
facets and the colored illumination on nearby stone and floor.

Rebuild with `python tools/build_wall_gems.py`; append `--check` for
deterministic validation. The source recipe is
`assets/source/terrain/limestone_cave/wall_gems.json`.
