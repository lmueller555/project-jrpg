# Woven rug source

`rug_recipe.json` defines the 64×36 rug's six-color palette, border and diamond
motifs. `parts/` retains the woven base, border/motif and fringe layers; they
reconstruct the final hard-alpha sprite without resampling.

Build with `python tools/build_liam_household_assets.py`. The resulting rug is
flat, static and nonblocking. Its placement belongs to the family-home recipe.
