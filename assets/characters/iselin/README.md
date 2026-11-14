# Iselin — front-facing idle

**Design:** approved Design A / Royal Envoy. **Artwork:** awaiting user review.

`idle_front.png` is a single transparent 24×36 idle frame. It uses the existing
foot anchor `[12, 34]` and map draw anchor `[12, 30]`. Her braid is on anatomical
left (viewer right), with the short navy mantle over anatomical right. Royal-blue
clothing, silver details, blue eyes and a dark contour retain the approved design.

This milestone also supplies `assets/portraits/eldenmere/iselin_neutral.png`, a
72×72 RGB dialogue portrait. Neither file is wired into the current regent actor
or speaker registry. Other directions, walking and cinematic poses belong to the
later full character replacement.

Source artwork and provenance are retained under
`assets/source/characters/iselin/`; the portrait master is under
`assets/source/portraits/eldenmere/`. Rebuild with
`python tools/export_iselin_first_assets.py` and verify with `--check`.
