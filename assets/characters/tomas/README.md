# Tomas — front idle

Visual design and native front idle **approved** in conversation.

The sprite has tousled honey-blond hair with a cowlick, two green eyes, a short rust-red tunic over an ivory shirt with rolled cuffs, dark brown trousers, a repaired patch on his anatomical left knee (viewer right), and worn brown ankle boots. His hands are empty. No cloth ties, tools, weapons or religious symbols are included. His exact age remains unspecified.

- `idle_front.png`: RGBA 24×36 frame, hard alpha; occupied bounds `[6,3,12,32]` (x, y, width, height).
- `idle_front.json`: frame, height comparison, eye/patch landmarks, palette/source paths and independent sprite approval status.
- `palette.json`: named materials and pupil/iris colors.
- `idle_front_review.png`: opaque RGB review at 24× nearest-neighbor scale.
- `scale_comparison.png`: Caelan, Tomas and Serene together at 16× with the same foot baseline.

Tomas is visibly 32 pixels tall, two pixels shorter than Caelan's 34, and narrower (12 versus 14 pixels across the full occupied bounds). All use 24×36 frames and `[12,34]` foot anchors. Transparent rows above Tomas accommodate the height difference. The patch is a small native accent; fine source details simplify at this resolution.

Rebuild the front with `python tools/build_tomas_idle.py` from the repository root. Retained concept, recipe and four reconstructable full-frame layers are under `assets/source/characters/tomas/`. Preview images retain their original review labels as a record of the approved artwork.

## Left, right and back idles — approved

`idle_left.png`, `idle_right.png` and `idle_back.png` add three still 24×36 views, each 32 visible pixels tall with foot anchor `[12,34]`. Each has independent status/landmarks in its JSON metadata and an opaque 24× review PNG. The cowlick, rust tunic, pale sleeves and dark trousers follow the approved front. Each profile shows one green eye; the back has no eyes.

The patch remains on the front of his anatomical left knee. It is visible on the near leg in the left-facing profile, occluded by the nearer right leg in the right-facing profile, and faces away in the back view. It is never mirrored onto the other leg.

`idle_turnaround_review.png` shows the three new views at 24×. `idle_all_review.png` compares all four views at 12×, using a shared baseline. `idle_all.png` is a native 96×36 sheet ordered front/left/right/back, with rectangles and per-view status in `idle_all.json`.

Run `python tools/build_tomas_directional_idles.py` to rebuild these views, their twelve source layers and review boards. The approved front, its source/layers and palette remain unchanged.

## Front walk — approved

`walk_front/` adds a four-phase front walk using the shared stride and timing, with arm poses registered to Tomas's proportions. Head and shoulders bob together; the patch follows the left knee rather than staying fixed on the sheet. He remains two pixels shorter than Caelan in matching phases.

The pack includes a 20× looping GIF, 12× frame strip, 16× synchronized Caelan comparison, native 96×36 sheet, recipe and animation metadata. Run `python tools/build_tomas_walk.py` and `python tools/test_tomas_walk.py`. Approved idle artwork is unchanged.

## Left, right and back walks — awaiting review

`walk_left/`, `walk_right/` and `walk_back/` add four-frame cycles from their approved idles. They share the directional stride/timing and the front walk's smaller arm registration, with the collar, head and shoulders rising together on passing phases. Tomas stays two pixels shorter than Caelan in matching phases. The patch follows the near left knee in the left profile, stays occluded in the right profile, and faces away in the back.

Each directory includes a 20× opaque looping GIF, 12× strip, 16× Caelan comparison, native sheet, recipe and metadata. `walk_directions_review.gif` shows all four directions synchronized at 12× with independent approval labels. `walk_directions.png` is a native 96×144 sheet, with directions as rows and phases as columns; `walk_directions.json` records rectangles and timing.

Run `python tools/build_tomas_walk.py --direction remaining` to rebuild only the new walks and combined board. `--direction all` also rebuilds the approved front with unchanged pixels; the default remains front-only. Run `python tools/test_tomas_walk.py` after all directions exist. Approved idles, palette and shared templates remain read only.
