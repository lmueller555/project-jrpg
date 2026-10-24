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

## Front walk — approved

`walk_front/` adds the first four-phase walk, assembled from the approved appearance and shared front stride. It includes a 20× looping preview, a 12× frame strip, native sheet, metadata and recipe. The head and shoulder mantle bob together; apron details remain visible through the skirt sway. Run `python tools/build_serene_walk.py` and `python tools/test_serene_walk.py`. Approved idle artwork remains unchanged.

## Left, right and back walks — approved

`walk_left/`, `walk_right/` and `walk_back/` add four-frame cycles from their approved directional idles. They use the shared directional arm/leg poses at 140 ms per phase, with one-pixel head-and-mantle bob and restrained skirt sway. Profile views retain a brown eye, silver temple and narrow apron with its patch; the back retains the bun and sage skirt without eyes or an apron panel.

Each directory contains a 20× opaque looping GIF, 12× frame strip, native 96×36 sheet, recipe and animation metadata. `walk_directions_review.gif` shows all four directions synchronized at 12×, with independent approval labels. `walk_directions.png` is a 96×144 native sheet: directions as rows, phases as columns. `walk_directions.json` records its rectangles and timing.

Run `python tools/build_serene_walk.py --direction remaining` to rebuild only the new walks and combined board; `--direction all` also rebuilds the approved front without changing its pixels. No other approved art is modified.

## Sanctuary work routines — awaiting review

`routines/` contains four 48×48 planted work loops derived from Serene's approved appearance: sorting provisions, consulting a preparation list, tending the hearth and folding hall linens. The larger canvas gives her hands and small props room while preserving the normal in-game registration, head, mantle and feet. Runtime metadata includes exact frame timing and the four action keys used by her persistent dining-room-to-hall schedule.

The [in-room review](../../../docs/reviews/serene_sanctuary_routines/README.md) shows every loop through the actual game renderer. Rebuild the native frames and isolated art previews with `python tools/build_serene_routines.py`; rebuild the room previews with `python tools/capture_serene_routines.py`.
