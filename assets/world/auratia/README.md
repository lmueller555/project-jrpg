# Auratia world map

`world_map.png` is the exact approved southern-Merovar world-map PNG, at
1448×1086 pixels. The full-screen classroom viewer loads this file directly,
keeping its labels and terrain detail available when zooming.

`wall_map.png` is a separate 42×40 native pixel sprite for the existing school
wall slot. Its simplified blue sea, four continental landmasses, island chain
and white polar areas remain readable without attempting miniature labels.
The generated prop source is retained in
[`assets/source/world/auratia`](../../source/world/auratia/README.md).
Its long western Merovar, northern mountain enclosure, central river and paired
southern rivers follow the same geography as the detailed map.

Rebuild the native prop and provenance manifest with:

```sh
python tools/build_auratia_world_map.py
python tools/build_auratia_world_map.py --check
```

The exporter uses nearest-neighbor sampling, a modest palette and binary alpha.
It does not rewrite the approved full-size map. The input
[`approval.json`](../../source/world/auratia/approval.json) pins the approved
filename, image hash and size, the derived prop source, and the map revision
that source depicts. Validation happens before export writes. `map.json`
records those inputs and generated sprite metadata; `--check` verifies inputs
and exports without repairing or overwriting files. Geographic authority remains the
[world atlas](../../../docs/narrative/world/WORLD_ATLAS.md) and
[polar-region guide](../../../docs/narrative/world/POLAR_REGIONS.md).
Current integration captures and preservation checks are in the
[map revision review](../../../docs/reviews/merovar_world_map/README.md).
