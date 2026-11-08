# Microcrystal seam adapters

Status: additions pending review. The existing cave and approved microcrystal fields are unchanged.

Seven new field patterns support vertical and diagonal fractures, concave and convex wall turns, sparse isolated grains and denser mineral pockets. Every pattern is provided in Red, Blue, Green, White, Orange and Purple.

All individual facets reuse exact native pixel crops from the existing microcrystal pack. Their size, shading direction and six brightness levels are preserved; only their positions change. Fields are transparent, with fixed neutral hairline crevices and no floor footprints.

`assets.json` records anchors, core rectangles, grain counts, color light values and semantic connection ports. Place the colored cores within rock faces and assign a nearby exposed floor light root using the existing cave renderer. `frame_duration_ms` describes review playback; production crystal lighting selects frames from its shared six-second pulse.

The PNG and GIF boards display every new field at exactly 2x native scale with Caelan for reference.

Rebuild with `python tools/build_microcrystal_adapters.py`; add `--check` for a read-only deterministic verification. The authoritative source is `assets/source/terrain/limestone_cave/micro_adapters.json`.
