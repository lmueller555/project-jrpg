# Crown soldier — frontal running performance

> **Superseded performance.** The current selection is
> [source_art_48.json](source_art_48.json): 48 complete drawings over 800 ms.
> See [run_v3/README.md](run_v3/README.md) for its sources, registration and
> reproduction command. Everything below describes the historical 24-pose,
> 400 ms implementation; its images, scripts and review evidence are retained.

`source_art_24.json` is the active selection of 24 complete frontal drawings in
a 400 ms cycle. Anatomical right (viewer left) is the sword side; anatomical
left (viewer right) carries the plain steel boss shield. Contact metadata uses
`near` for right/frame0 and `far` for left/frame12 to retain the shared Foley
contract. The ordinary Crown palette is steel, navy cloth and brown leather.

The complete figures use the frozen guards' detailed painted material treatment
and natural proportions, with an exposed ordinary young man's face under the
open helmet. Face identity, equipment ownership and clothing remain consistent.
No blink or glance is embedded in the repeating 400 ms cycle.

## Sources and mechanical export

The original ImageGen outputs are `batch_00_03.png` through `batch_20_23.png`.
Prompts and `production_generation_24.json` record the six generation IDs,
appearance references and hashes. `keys_generated.png` and its generation
record establish the four contact/flight keys; their cropped references are
authoring guides, not runtime frames.

Run from the repository root:

```sh
python assets/source/cinematics/fire_veinhold/face_reveal/crown_soldier/register_source.py
python tools/export_prologue_faces.py --actor crown_soldier
python tools/export_prologue_faces.py --actor crown_soldier --check
```

Registration uses a fixed 1.25 uniform whole-image density, actual exposed-eye
appearance landmarks, and an authored small periodic recoil. Separate actual
throat and buckle patches measure source proportions against each master's
first drawing. The full drawing translates together; no face or limb is pasted,
warped or independently repositioned. Source landmarks use source-cell pixels.
Neither occupied bounds nor the lowest boot determines the scale or origin.

The alpha-only derivatives retain every original RGB byte and original alpha
within two source pixels of any alpha>=192 core. Other alpha is set to zero to
remove low-alpha ambient haze and faint guide lines generated outside figures.
`alpha_recipe.json` records the exact operation and both hashes. Whole figures,
including the thin sword, shield, hands and separated boots, were inspected
after matting. Raw masters remain unchanged.

The final 768×1024 frames have anchor `[384,960]`. Whole figures and native face
contact sheets are exported under `docs/reviews/veinhold_face_reveal/`; final
camera framing, perspective scale and movement receive production-shot review.

## Historical candidates

`history/rejected_batch_*_wholekeys.png` are the initial failed microstep
attempts. Supplying the complete four-key layout prompted quarter-cycle poses
instead of consecutive steps. They are explicitly unselected. The active six
masters instead use a single phase appearance reference per request and describe
only a short consecutive portion of the cycle. Contact sheets and coordinate
proofs in this folder are authoring diagnostics rather than runtime assets.
