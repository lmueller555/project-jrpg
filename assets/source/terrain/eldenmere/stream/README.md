# Eldenmere — stream material and animation source

Status: draft artwork for review; the stream-and-bank design plan is approved.

`materials_concept.png` is the generated water/shore reference guided by the approved grass/dirt materials. Its top-left panel supplies restrained depth texture, and the top-right supplies source ripple shapes. Lower panels guide the earth/grass/water boundary. The native export keeps the approved ground colors and thinner bank edges, rather than treating the dense reference as a finished tileset.

`recipe.json` records source crops, native glyph dimensions and threshold, named water colors, sparse depth windows, six ripple poses, two spatial ripple arrangements, 200 ms timing, bank width and review scales. `parts/` retains the opaque native surface base and three binary ripple masks. Sampling uses nearest-neighbor. Ripple clusters drift at most two pixels, brighten locally and dissolve with staggered phases; the body of water has a constant base color. No interpolation, partial alpha or whole-tile brightness cycling is used.

`quarters/` retains twenty 12×12 oriented bank/shallow pieces and twenty matching water-alpha pieces. They reuse the approved grass/dirt blob geometry through the existing read-only helper, with two native pixels of earth and one shallow rim. Neighborhood halos keep these layers continuous across tile boundaries. The bank overlay covers the water's shallow rim, so animation cannot move the shoreline.

`python tools/build_eldenmere_stream.py` exports 47 bank states, two six-frame surface variations, and six complete atlases for variation 00 (282 composed frames). Both surface variations are used in the review through the same bank/mask layers and global clock. The scene JSON explicitly records the chosen variation per wet cell. The complete canonical atlas remains convenient for engines that prefer baked sprites; the second variation is supplied as layered surface frames.

The existing terrain scene is read as a base. Water replaces some dirt cells, dry-path masks are recomputed, and two characters are moved onto dry ground. The original scene, grass/dirt exports, native characters and narrative documents are never rewritten. This scene is illustrative and establishes no story geography or map layout.

Tests independently reconstruct all atlases and every scene phase. They check all raw neighbor states, hard alpha, exact palette, quarter composition, stationary banks, localized water motion, all 2,048 adjacent neighborhoods across six phases and every surface pair, character scale/dry footing, GIF timing and pixel-exact enlarged scene playback. The source recipe is the artwork approval record and survives rebuilds.
