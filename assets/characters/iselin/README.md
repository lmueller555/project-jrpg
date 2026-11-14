# Iselin — front-facing idle

**Current assets:** the 42×72 idle and dialogue portrait are approved. The
registered idle actor is `actor.json`; `animation.json` supplies a logical
fallback and the display-density idle. See
`docs/reviews/iselin_first_assets/IMPLEMENTED.md`. Older review notes follow.

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

`idle_front_42x72.png` and its JSON are an additional requested resolution study,
not an activated replacement. Its 42×72 canvas contains a proportion-preserved
26×68 drawing. The proposed artwork density is 2 image pixels per logical world
pixel (21×36 logical frame). Current actor rendering does not consume this
metadata; drawing the image unchanged today would make it twice as tall.
See `docs/reviews/iselin_first_assets/resolution_42x72.png` for the labeled
same-height and current-renderer mock-ups.
