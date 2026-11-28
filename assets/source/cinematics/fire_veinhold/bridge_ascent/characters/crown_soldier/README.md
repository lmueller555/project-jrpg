# Crown soldier — bridge ascent source

State: prepared for in-game review. Independent source/native entry, later-angle
continuity and tiny-cycle gates passed provisionally. Final composed chronological
shot review belongs to the shared shot08 bank and is recorded separately in
`docs/reviews/veinhold_bridge_ascent/independent_review/`.
This source state does not claim user approval or a completed full-scene review.

The active portable actor manifest is
`assets/story/fire_veinhold_opening/shot08/characters/crown_soldier/actorperformance.json`.
It binds all127 used PNGs,133 transition clock samples and48 chronological
overhead run phases. The run remains800ms; the initial phase is18 (.3s).

- Entry ticks0–25 retain exact approved shot07 phase18–43 PNG bytes, with
  their original768×1024 canvas,384/960 anchor and500artpixels/metre.
- Tick26 uses the accepted complete phase44 continuity drawing
  `first_batch/entry_026_close_model.png`.
- Camera-specific complete drawings at ticks28,30,...130 use30Hz drawing
  exposure. Each following odd tick holds the preceding whole drawing while
  the scene clock and logical/audio phase continue at60Hz. Tick30 is phase0.
- Tick132 and the far-bank entry share the exact overhead phase6 bitmap.
  The48-pose overhead bank thereafter follows the actual60Hz phase clock.
  These records are not a claim of133 unique transition paintings.

Every final pose is a complete ImageGen-authored figure. The source-only Blender
guides establish camera volume and connected anatomy; they are never runtime
body parts or final character renders. Their numerical joint plans are distinct
from observations of the painted drawings.

Registration uses a uniform whole-sheet density calibrated from actual rigid
steel helmet measurements. Complete drawings are translated and padded on
transparent canvases. Early registration bridges the exact approved bitmap
handoff. The nine minimal continuity drawings preserve matching-phase action
and use a reviewed rigid pauldron patch for whole-image translation at the
declared cell-resolution ratio. No occupied-height or foot-bound fitting,
body-proportion normalization, limb rigging, pasted regions, anatomy warps or
crossfaded poses are used. The raw masters remain unchanged; technical exports
remove alpha≤16 fringe before premultiplied sampling.

Active selections and their whole-cell provenance are in
`selection_provenance.json` and
`registered_atlases/registration_report.json`. Generation records retain exact
prompts, generation IDs, raw output paths, source hashes and reference hashes.

Historical candidates are retained as evidence. In particular, the initial
`transition_00.png` had a palette/posture/shield handoff failure; the v2 atlas
is used only from tick28. Earlier overhead direction keys included rejected
frontal-body and extra-boot attempts. The broad `repairs/late01.png`,
`late02_clean.png` and `late03.png` corrections changed boot projections;
the selected corrections are the corresponding `*_minimal.png` complete
drawings. `overhead_00_initial.png` retains its rejected haze, and its original
metadata intentionally names the historical output path; the corrected
`overhead_00.png` has a chained transparency-repair record.

From the repository root, rebuild selected actor inputs with:

```sh
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/crown_soldier/authoring/build_selected.py
```

Check the deterministic selected export and raw/reference provenance with:

```sh
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/crown_soldier/authoring/build_selected.py --check
```

The check verifies all127 actual published PNG hashes, logical phase coverage,
the26 exact entry copies, the shared phase6 bank join, and all42 retained
generation records. Source-only proof scripts generate fixed-scale native
camera contact sheets and diagnostic normal/slow GIFs. They do not establish
real-time gallery playback or final composed-bank acceptance.

