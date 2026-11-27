# Fire Veinhold bridge running shot — authored sources

This folder retains the complete character drawings for the three-second, side-on, boot-height tracking shot. The active selections are:

- `lucan/source_art_24.json`
- `iselin/source_art_24.json`
- `crown_soldier/source_art_24.json`

Each profile selects **24 complete RGBA poses in a 400 ms sprint cycle**: one new pose per 60 Hz tick, with near and far foot contacts at frames 0 and 12. The shot presents a brief, heightened action sprint. It does not establish ordinary exploration movement speed or claim exact physical foot locking.

## Source and export

The `bank24/` atlases were authored with ImageGen as complete figures, four poses per master. Per-actor `production_generation_24.json` files retain generation IDs, prompts, appearance/pose references and source hashes. Where native review exposed a leg transition or excessive compression, ImageGen redrew the **entire figure**. The active profiles select those individual repairs instead of the superseded atlas cells. Lucan's far-support repairs also use the approved Crown figure's complete joint pose as an authoring reference, then redraw Lucan's identity and outfit as a whole image; they do not transplant limbs.

From the repository root:

```sh
python tools/export_prologue_runners.py
python tools/export_prologue_runners.py --check
```

Use `--actor lucan`, `--actor iselin` or `--actor crown_soldier` to rebuild one actor. The mechanical exporter crops the selected source cell, samples it uniformly, and places the complete drawing on its registered canvas. It writes the runtime frames and metadata under `assets/story/fire_veinhold_opening/shot06/characters/`, plus whole-figure and boots contact sheets under `docs/reviews/veinhold_bridge_run/`. It checks reproducibility, frame timing, source hashes and opaque clipping. It does not synthesize anatomy, rotate limbs, warp idles, interpolate body pixels or normalize each pose by its occupied bounding box.

Source-cell landmarks describe actual neck, belt and visible support points before uniform sampling. Registration preserves one canvas and anchor per actor. Authored whole-body compression and rise follow support/flight; airborne feet are not snapped to the floor. Small marker changes during heel-to-toe roll do not imply that every material point is exactly locked to a constant ground velocity.

## Review scope and historical material

The approved use is the **cropped lower-body shot**, including near/far leg progression, support release, two-foot anatomy, native framing, costume readability and phase continuity. Faces and much of the upper-body acting are outside that shot. These sources are not an approval of reusable full-body, frontal or dialogue animation; another shot must review the anatomy and acting it exposes.

Earlier 36-phase studies, four-key sheets, individual microstep pilots, pose guides, registration reports, backup profiles and rejected `repairs/` candidates remain authoring history. Some candidate filenames describe their intended phase rather than an accepted chronological pose. **Only the three active `source_art_24.json` profiles select production art.** Unselected files are not loaded by the runtime. Consult the active profiles and production generation manifests instead of assembling frames from filenames or historical contact sheets.
