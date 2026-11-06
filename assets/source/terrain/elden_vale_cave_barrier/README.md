The retained imagegen sources supply an isolated temporary safety barrier for
the existing natural cave entrance. The second source adds the small hanging
notice to the first source's rope and stakes. No existing sanctuary image is
changed by this asset.

Run `python tools/build_sanctuary_cave_barrier.py` from the repository root to
rebuild the native transparent prop and placement manifest. Use `--check` to
verify retained source hashes and exact exported bytes without writing files.
`art_recipe.json` records the retained source, crop, nearest-neighbor export,
native placement, foot anchor, sort baseline and blocking rectangle.

The manifest's `position` is the sprite's top-left at (965, 331). Its bottom
center foot anchor is (1009, 379), with the rope spanning the cave mouth above
the blocking rectangle (974, 364, 70, 13). The path approach (1008, 406) remains
an open shallow apron. Runtime placement, collision and notice dialogue belong
to the sanctuary scene builder.
