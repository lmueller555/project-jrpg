# Elden Vale cartographic art

These original image generations supply illustrated materials, forest masses,
foothill relief and miniature place symbols for the regional atlas and minimap.
They are separate from gameplay sprites and terrain.

The approved Auratia world map supplies the visual reference: restrained green
land, blue waterways, dimensional woodland and stone, and warm settlement roofs.
The exact geography is supplied by the independent `survey.png` / `survey.json`
and the runtime region manifest. No labels or operational states are baked into
the terrain illustration.

- `materials_sheet.png`, `masses_sheet.png`, `icons_sheet.png`: unaltered outputs.
- `prompts.json`: submitted generation prompts and transparency choices.
- `recipe.json`: pinned source hashes, source crop rectangles, native sizes,
  palette limits and alpha cleanup threshold.
- `native_review.png`: native-size contact sheet.

```sh
python tools/build_cartography_art.py
python tools/build_cartography_art.py --check
```

The exporter crops separate sprites, scales them uniformly, reduces palettes,
cleans low-alpha fringes and pads transparent canvases. It does not paint art.
The atlas builder separately composes these materials and silhouettes against
surveyed geographic masks and exports bounded map tiles. Roads, walls, names,
selection, discovery and passage states remain live overlays.
