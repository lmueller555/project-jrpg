# Woven rug source

`rug_recipe.json` defines the 64×36 rug's six-color palette, border and diamond
motifs. `parts/` retains the woven base, border/motif and fringe layers; they
reconstruct the final hard-alpha sprite without resampling.

Build with `python tools/build_liam_household_assets.py`. The resulting rug is
flat, static and nonblocking. Its placement belongs to the family-home recipe.

## Wooden bowls

`bowls_recipe.json` defines two matching food/water bowls with full, half-full
and empty states. Wood and water colors reference the existing furniture and
kitchen palettes. `bowls_parts/` contains shared wooden body/front lip layers
and six contents layers. `tools/build_daisy_bowls.py` exports the registered
24×24 sprites, masks, state manifest and native strip.
