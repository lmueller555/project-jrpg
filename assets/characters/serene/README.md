# Mother Serene

Front idle **approved**, based on the approved caretaker design.

- `idle_front.png`: native RGBA 24×36, hard alpha, foot anchor `[12,34]`, clear bottom row.
- `idle_front.json`: frame, palette, source/layer paths and review status.
- `palette.json`: named clothing, hair, skin and eye colors.
- `idle_front_review.png`: opaque RGB preview, enlarged 24× with nearest-neighbor sampling.
- `scale_comparison.png`: Caelan, Serene and Mira at the same 16× scale and foot baseline.

The source concepts and reproducible export recipes are under `assets/source/characters/serene/`. Run `python tools/build_serene_idle.py` from the repository root to rebuild the front. The builder preserves an existing approval status when rebuilding.

Review images retain their original review labels as a record of the approved artwork.

## Directional idles — approved

`idle_left.png`, `idle_right.png` and `idle_back.png` add three native 24×36 still poses. Each has its own metadata and opaque 24× review PNG. Profiles have one brown eye and a silver temple; the back has no eyes, a visible bun, a short mantle and a sage skirt with a buttoned apron waist fastening. No cloth ties are present.

`idle_turnaround_review.png` shows the three new views at 24×. `idle_all_review.png` compares them with the unchanged approved front at 12×. `idle_all.png` is a 96×36 transparent sheet ordered front, left, right, back; `idle_all.json` records each frame's independent status and rectangle.

Rebuild these views and boards with `python tools/build_serene_directional_idles.py`. It preserves existing approval statuses and reads the approved front and palette without rewriting them.

## Front walk — awaiting review

`walk_front/` adds the first four-phase walk, assembled from the approved appearance and shared front stride. It includes a 20× looping preview, a 12× frame strip, native sheet, metadata and recipe. The head and shoulder mantle bob together; apron details remain visible through the skirt sway. Run `python tools/build_serene_walk.py` and `python tools/test_serene_walk.py`. Approved idle artwork remains unchanged.
