# Canonical grassland blob-47 validation status

The atlas in `assets/atlases/terrain/grassland_v1.png` contains 63 source slots,
including 47 illustrated transition cells. It is **not proven to be a canonical
47-mask set**: there is no verified art-slot-to-mask assignment, and the
individual tile edges have not passed visual seam tests.

`engine/grassland_autotile.py` defines the 47 mathematically valid masks and
tests cardinal-conditioned diagonals, inside/outside corners, repeated cells,
and missing-map neighbors. Rendering with this atlas must remain blocked until
art has been mapped and a composed-map screenshot has been approved.

A future implementation must supply a complete, tested mapping from each mask
to the source artwork, compare adjacent 32x32 edges in assembled scenes, and
then integrate through the 16-cell Eldenmere map without altering collision.
Do not map `source_slot_XX` to masks by alphabetical/numeric order.
