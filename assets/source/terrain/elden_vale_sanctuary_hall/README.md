# Elden Vale Sanctuary hall pixel modules

`recipe.json` authors a 24-pixel-grid public hall from the existing Eldenmere
asset packs. Its `assets` table records each immutable source image and SHA-256.
The native 576×384 room contains a remembrance table, quiet reading benches,
bookstands and public records. It is separate from Serene's household rooms.

The floor uses the cottage interior's three native timber tiles; wall courses
reuse terrace masonry pixels with an explicit indoor limestone palette.
Seating, tables, bookshelves, notes, baskets, planters and the small
woven rug retain their pack-native pixels and scale. The longer remembrance
and records tables join existing table modules and carry independently authored
surface props; their composites have explicit ground-contact footprints.

`tools/build_sanctuary_reserve_hall.py` exports the assembled floor/wall cache,
separate transparent furniture entities, collision, overview and source
metadata. No background painting or extracted painting silhouette supplies the
runtime scene. The previous generated image and depth cutouts have been removed.

The whole visible floor remains open except physical furniture and masonry.
Characters pass behind benches, tables, plants and bookcases at their ground
anchors; transparent furniture and leaf gaps retain the underlying actor.
The central aisle, all inspection approaches and the southern exit are clear
for the full 24×12 player footprint. Existing scene identity, travel anchors and
inspection IDs are retained.

The `fantasy` recipe section adds native faceted crystal panes, branching wall
carvings, a circular renewal medallion and warm memorial lamps. These mounted
details occupy the existing north wall above the walkable floor. Their exported
modules live in `assets/terrain/elden_vale_sanctuary_hall/fantasy/`; furniture,
doorway, inspection points and collision are unchanged.

Build with `python tools/build_sanctuary_reserve_hall.py`; `--check` verifies
source hashes and byte-for-byte deterministic exports and rejects obsolete art.
