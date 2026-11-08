# Limestone dungeon structure

Status: pending visual review.

Native directional walls, caps, bases, ledges, shelves, ramps, worn steps,
passage mouths and shallow alcoves extend the existing limestone pack.
Ramps and steps use ordinary walking; elevation is a visual composition value.
`walkable_regions` identify clear passage surfaces, while `footprints` describe
solid rock only. All coordinates are local to the unscaled native module.

Rebuild with `python tools/build_dungeon_structure.py`; append `--check`
for deterministic verification. Source: `assets/source/terrain/limestone_cave/structure.json`.
