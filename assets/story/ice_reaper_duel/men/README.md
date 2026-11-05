# Wind reaction sprite actions

Caelan has six authored wind drawings in front, right, rear and left views. Lucan has six in front, right and rear views. Mira has four brace/react drawings in each of those views. All sprites use the existing 128×128 scene canvas, anchor `[64,116]`, and nominal body height82.

Manifests expose full `wind_{view}` sequences plus semantic hit/flight/land phases and a settled pose. Mira exposes `brace_{view}`, `react_{view}` and settled poses. View azimuths are front0°, right90°, rear180°, and Caelan left−90°. Equipment is separately drawn for each view; sprites are never mirrored.

The runtime owns the world-space wind flight and landing. These sheets supply the matching body poses. Rebuild with:

```sh
python3 tools/build_ice_duel_men.py
```

Generated sources, reference directions and extraction provenance are retained under `assets/source/cinematics/ice_reaper_duel/men/` and each actor's `provenance.json`.
