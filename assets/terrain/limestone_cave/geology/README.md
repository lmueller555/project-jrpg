# Limestone loose geology and entrance treatments

Status: pending visual review; isolated from live maps.

Four native variants each: small pebbles, rubble, wall-foot talus,
raised fallen slabs, branching cracks, erosion channels, calcite
crust, damp staining, exposed roots, emerald moss and leaf litter.
Four 24-pixel earth fills and two variants of every cardinal,
inside-corner and outside-corner earth-to-stone transition complete
the entrance material coverage.

Every module declares its native size, anchor and footprints.
Most are ground decals and never add collision. Raised slabs own
a shallow physical footing matching their visible lower edge.
Roots, moss and leaves are intended for the cave threshold and
daylight margins rather than dense growth throughout the dungeon.

Rebuild with `python tools/build_dungeon_geology.py`; use `--check`
to validate deterministic exports without modifying files.
