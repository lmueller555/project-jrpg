# Schoolroom source layers

`tools/build_eldenmere_school_interior.py` assembles the room at native resolution
from approved cottage shell tiles and palette-compatible new school furniture.
`recipe.json` records registration, all object placements/footprints/access
points, source palettes and classroom details. `shell/` retains floor, walls and
fixtures; `sprites/` retains ordered transparent layers for every new prop;
`lighting/` retains each transparent lighting layer. Approved chairs and hearth
are referenced by path without alteration. Rebuild the script rather than
editing only flattened exports.
