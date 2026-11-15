# Caelan right run — artwork review

Status: awaiting user artwork approval. Not merged or integrated into gameplay.
The existing directional idles, walks, approved front/rear runs and live registry
are unchanged.

- [Normal/half-speed preview with approved profile idle](preview.gif)
- [Numbered complete drawings](frames.png)
- [Native bank and phase metadata](../../../assets/characters/caelan/review_hd/run_right/animation.json)

## Animation and sizing

Sixteen complete drawings at 25 ms each retain the existing 400 ms run cadence.
Right arm and leg are near; left arm and leg are far throughout. The single
anatomical-left pouch is occluded on the far side. Both limb pairs progress
through the cycle with the same-side arm countering its leg. Natural torso and
near-limb overlap hide parts of the far chains without leaving extra hands.

Density remains 2 artwork pixels per logical world unit. Canvas is **56×76**
artwork / **28×38** logical; draw anchor [28,64], foot reference [28,72].
Relative to the base idle, transparent padding adds eight artwork pixels of
width and four of height. Both anchors move together by [4,4]. This fits the
profile stride without shrinking the body or clipping boots. The preview aligns
draw anchors and includes native-size examples. Runtime integration must honor
the per-bank anchors; it remains deferred.

| Frames | Selected pose phases |
| --- | --- |
| 1–5 | Near-right contact, compression, support, late support and toe-off |
| 6–7 | Flight and descending approach to left landing |
| 8–9 | Far-left touchdown and contact |
| 10–13 | Left compression, support, late support and toe-off |
| 14–15 | Flight and descending approach to right landing |
| 16 → 1 | Right touchdown continues into the initial contact |

The drawings determine the support labels; the starting guide's frame-number
template is not imposed on a pose that already begins contact.

## Sources and export

Canonical rules: [Visual art standard](../../VISUAL_ART_STANDARD.md#running-animations).
Rebuild with `python tools/export_caelan_right_run_hd.py` and Pillow installed.

Source folder: `assets/source/characters/caelan/run_right_hd_review/`.
`idle_reference.png` is a crop of the approved right idle master. `keys.png`
establishes contact/flight appearances. `A.png`–`D.png` retain the original
chronological batches. `contact_correction.png` supplies 5, 8 and 13;
`flight_correction.png` supplies 6, 7, 14 and 15. `D.png` supplies 16. The
remaining source cells and `arm_correction.png` retain superseded construction
history, not additional active frames. `near_arm_back_reference.png` is a crop
of the initial trailing-arm pose used as an explicit correction reference.

`provenance.json` records generated originals, hashes and correction purposes.
`registration.json` records the selected cell, bounds, source landmarks, uniform
scale, whole-pose translation, alpha threshold, timing and phases for each frame.
`protected_references.json` protects 196 pre-existing files, including both
approved HD runs and their review previews.

All creative poses were authored as complete image-generation drawings.
Technical export extracts the connected alpha body, samples whole drawings at
uniform .124 density using nearest-neighbor, registers cranial centers and the
neck/belt arc, applies the established shared Caelan palette and inside outline,
and writes flattened RGBA images. There are no limb rigs, detached transforms,
independently phased upper/lower strips, idle warps or runtime bob. Sampling
never normalizes occupied height or aligns by whichever boot is lowest.

## Review and validation

Reviewed all four anatomical chains across both steps, all batch joins and
16 → 1. Repairs addressed near-arm reversals during flight, initial contact
registration, and overly abrupt heel recovery after toe-off. Early recovery now
begins with a modest knee bend before the stronger fold. Far limbs retain their
own swing instead of remaining parked behind the near pair.

The exported crown ranges from 5 to 8 artwork pixels; maximum adjacent change
is two pixels, including the loop seam. Recorded support-sole spans progress
backward in both stances. Their centers are:

- Right support 1–5: 42, 28, 22, 7.5, 6 artwork pixels.
- Left support 9–13: 40.5, 27, 23.5, 14, 8 artwork pixels.

Those are visible sole-span centers, not ankle joints. The rate is uneven and
is not calibrated to cancel actor travel. This in-place review does not establish
world-ground locking. Sole heights vary by up to two artwork pixels in the
audited support poses; boot rotation and pixel quantization remain visible.

Checks pass for sixteen unique hard-alpha frames, unclipped transparent margins,
exact sheet reconstruction, source hashes, 196 protected files, source-density
and anchor records, backward support progression, crown continuity and 400 ms
cycle timing. The GIF has 32 alternating 20/30 ms delays totaling 800 ms: two
normal cycles and one half-speed cycle. Exact PNGs are authoritative for color
and alpha. Existing directional walk suites pass (25 tests).

Gameplay speed, collision and live actor selection remain unchanged. Scenery
travel, padded-bank loading and direction/idle transitions will be checked during
the later runtime integration after artwork approval.
