# Sanctuary native pixel assets

The reserve is authored by the placement recipe in
`assets/source/maps/elden_vale_sanctuary/recipe.json`. It reuses Eldenmere
24px grass/dirt, foliage, flowers, benches, planters and masonry packs, plus the
source-derived modular limestone kit built by `tools/reserve_stone_kit.py`.

Run `python tools/build_elden_vale_sanctuary.py` to compose all terrain,
independent objects, source provenance, collision and map metadata. Use
`--check` to verify deterministic exports. The generated `art.json` records
every source path and SHA-256. The previous painted backdrop and traced
depth silhouettes have been removed.
