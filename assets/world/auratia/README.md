# Auratia world map

`world_map.png` is the exact approved polar-region world-map PNG, at
1448×1086 pixels. The full-screen classroom viewer loads this file directly,
keeping its labels and terrain detail available when zooming.

`wall_map.png` is a separate 42×40 native pixel sprite for the existing school
wall slot. Its simplified blue sea, four continental landmasses, island chain
and white polar areas remain readable without attempting miniature labels.
The generated prop source is retained in
[`assets/source/world/auratia`](../../source/world/auratia/README.md).

Rebuild the native prop and provenance manifest with:

```sh
python tools/build_auratia_world_map.py
```

The exporter uses nearest-neighbor sampling, a modest palette and binary alpha.
It does not rewrite the approved full-size map. `map.json` records sizes,
source paths and SHA-256 values. Geographic authority remains the
[world atlas](../../../docs/world/WORLD_ATLAS.md) and
[polar-region guide](../../../docs/world/POLAR_REGIONS.md).
