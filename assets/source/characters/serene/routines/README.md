# Serene sanctuary routines

`recipe.json` describes four planted-foot work loops built from Serene's approved
back-facing artwork. Coordinates are native 24×36 character pixels;
the builder registers them on a 48×48 action canvas at `[12, 6]` so hands and
props can extend beyond the normal walk frame without changing her foot anchor.

Run `python tools/build_serene_routines.py` from the repository root. The build
is deterministic and writes the runtime manifest, native frames, sprite sheets
and nearest-neighbour review animations to
`assets/characters/serene/routines/`.
