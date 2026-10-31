# Elden Vale atlas and overworld minimap

Elden Vale uses an illustrated regional atlas with live routes, place names,
discovery and passage information. A local minimap appears at the bottom right
during normal overworld exploration. The former Menu button is removed from
the exploration HUD in every location; Escape still opens the pause interface.

## Regional atlas

Press **M**, or click the overworld minimap, to open the atlas. Its initial view
frames Eldenmere, the two rivers, the ruined western crossing and both guarded
checkpoints. The map preserves geographic proportions and supports closer
inspection and exploration of the surrounding chart.

- Scroll over the map to zoom around the pointer; drag to pan.
- Click a known place or use arrows/WASD to select it and inspect its card.
- Scroll over the card, or use Page Up/Down, Home and End, to read longer entries.
- Use Fit/F to return to the regional overview.
- M, Escape or the close control returns to exploration.

Names and symbols distinguish settlements, crossings, checkpoints and local
landmarks. Important names remain readable in the overview; minor discovered
places gain labels when space permits. Selection and Caelan's directional
position marker remain distinct even when they occupy the same location.
Closed gates and the ruined bridge have shape and text cues as well as color.

Terrain is illustrated pixel cartography, while text is rendered separately at
display resolution. The header is compact and the selected-place card appears
when requested. Text size, wrapping and scrolling follow the game's readability
settings. The existing town map and classroom world atlas retain their own views.

## Minimap

The north-up minimap follows Caelan continuously at local scale, using the same
cartography and geographic transform as the full atlas. Its player arrow shows
facing direction. Nearby settlement, crossing, checkpoint and known landmark
symbols provide orientation without covering the world with labels.

The minimap is limited to the regional overworld. Towns, interiors and the
detailed millrace use their existing HUD. It yields to dialogue, combat,
cinematics and other interface screens. Clicking it opens the regional atlas;
the click is consumed so it cannot also activate the world behind the map.
Interaction prompts and save messages account for the minimap's footprint.

## Artwork, registration and bounded rendering

`regional_cartography.py` provides the shared cartography service. It reads a
georeferenced map manifest and loads only the needed fixed-size image tiles and
level of detail. The image cache has a fixed budget shared by the full map and
minimap (24 MiB for terrain and 2 MiB for icons). Neither view renders gameplay terrain chunks or constructs a
world-sized surface. Icons use a separate small bounded cache.

The offline builder derives the survey and geographic masks from the final
runtime region. Original cartographic materials, canopy masses, relief and
miniature symbols supply the illustration. Roads, walls, operational markers,
place labels and player position remain live overlays. Geometry fingerprints
detect stale artwork; nonstandard fixtures can use a bounded geographic fallback.

Gameplay geography, world/landmark identities, discovery saves and independent
gate/bridge facts remain unchanged. The original Auratia atlas supplies style
context; its approved artwork is preserved.

Sources and tools:

- `assets/source/cartography/elden_vale/`: source generations, prompts, recipes
  and the geographic survey.
- `assets/cartography/elden_vale/art/`: exported cartographic materials and icons.
- `assets/cartography/elden_vale/manifest.json` and `tiles/`: tiled regional chart.
- `tools/build_cartography_art.py`: reproducible native art export.
- `tools/build_elden_vale_cartography.py`: registered chart and level-of-detail build.
- `tools/capture_elden_vale_atlas.py`: production-game UI review captures.

```sh
python tools/build_cartography_art.py --check
python tools/build_elden_vale_cartography.py --check
python -m unittest discover -s tests -p 'test_*cartography*.py' -v
python -m unittest discover -s tests -p 'test_overworld_*map*.py' -v
python tools/capture_elden_vale_atlas.py
```

See the [actual atlas and minimap review](reviews/elden_vale_atlas/README.md).
