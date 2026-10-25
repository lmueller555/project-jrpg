# Daisy's woven rug — review pending

`rug.png` is a transparent 64×36 floor sprite at the game's native pixel scale.
Its teal weave, ivory border/fringe and small terracotta diamonds use six colors
and hard alpha. It is flat and nonblocking, with no animation. In Liam's house
it is drawn at `[80,258]`, below all furniture and actors.

`rug.json` links the recipe and retained layer PNGs in
`assets/source/terrain/eldenmere/liam_home/`. Rebuild with
`python tools/build_liam_household_assets.py`, or through the family-home builder.
See the [in-game household and close-up](../../../../docs/reviews/liam_household/README.md).
