# Registered title water

Generated from `assets/source/ui/title/water/recipe.json` by
`tools/build_title_water.py`. `animation.json` records position, frame size,
timing, background hash, region flow and pixel counts. `mask.png` and each region
mask retain the full 640×360 coordinate system; animation frames are cropped
to the union bounds, with their origin stored in the manifest.

Runtime playback in `title_water.py` uses only Pygame. It draws these hard-alpha
frames over the approved background before the separate wheel and atmospheric
layers. The final title scene and UI still compose into one opaque frame before
fullscreen presentation.
