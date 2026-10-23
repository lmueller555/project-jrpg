# Mother Serene

Front idle **approved**, based on the approved caretaker design.

- `idle_front.png`: native RGBA 24×36, hard alpha, foot anchor `[12,34]`, clear bottom row.
- `idle_front.json`: frame, palette, source/layer paths and review status.
- `palette.json`: named clothing, hair, skin and eye colors.
- `idle_front_review.png`: opaque RGB preview, enlarged 24× with nearest-neighbor sampling.
- `scale_comparison.png`: Caelan, Serene and Mira at the same 16× scale and foot baseline.

The source concept and reproducible export recipe are under `assets/source/characters/serene/`. Run `python tools/build_serene_idle.py` from the repository root. The builder preserves an existing approval status when rebuilding. This package adds only one still front-facing pose.

Review images retain their original review labels as a record of the approved artwork.
