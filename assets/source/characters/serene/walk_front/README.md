# Front-walk source components

`parts/` retains the head, shoulder mantle and bodice extracted from Serene's approved front idle, plus seven full-frame compositing layers for each walk phase. The frame metadata lists their order so the exported RGBA frames can be reconstructed exactly.

Appearance comes from the approved idle and named palette; no new concept or revised idle is introduced. Geometry and timing come from the approved shared front stride. Costume-specific skirt rows, calf/boot boundaries and input paths are retained in `assets/characters/serene/walk_front/recipe.json`. The builder reuses the existing dress leg adapter, and preserves the apron/pocket/patch while filling garment pixels previously hidden by still hands. The complete shoulder mantle and head share the same one-pixel vertical offset.

Run `python tools/build_serene_walk.py` from the repository root. This front-walk animation is approved.
