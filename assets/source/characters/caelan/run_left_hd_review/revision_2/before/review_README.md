# Caelan left run — artwork review

Status: awaiting user artwork approval. Not merged or integrated into gameplay.
Existing idles, walks, approved runs and live actor selection are unchanged.

- [Normal/half-speed preview with approved left idle](preview.gif)
- [Numbered full-body drawings](frames.png)
- [Native bank and phase metadata](../../../assets/characters/caelan/review_hd/run_left/animation.json)

## Contract and anatomy

Sixteen complete drawings at 25 ms retain the existing 400 ms two-step run.
The 56×76 artwork canvas, 28×38 logical canvas, density 2, draw anchor [28,64]
and foot reference [28,72] match the approved right run. Transparent padding
accommodates the stride without changing physical body scale or collision.
The preview aligns draw anchors and includes native artwork-size examples.

Left arm and leg are near; right arm and leg are far. The single brown pouch
is attached to the visible anatomical-left hip. The near arm may cover part of
it during passing. Left-specific hair, face, clothing and pouch are redrawn from
the approved left idle instead of flipping the finished right-facing costume.

The approved right run supplies reflected **motion guides only**. Guide order
is shifted eight frames so this bank retains right-foot contact first rather
than silently exchanging anatomical phases when changing facing. New left
drawings supply every exported pixel; no mirrored right-frame pixels are used
in the final bank.

| Frames | Selected phases |
| --- | --- |
| 1–5 | Far-right contact, compression, support, late support and toe-off |
| 6–7 | Flight and descending approach to left landing |
| 8–9 | Near-left touchdown and contact |
| 10–13 | Left compression, support, late support and toe-off |
| 14–15 | Flight and descending approach to right landing |
| 16 → 1 | Right touchdown continues into initial contact |

Both arms counter their same-side legs. The foreground chain changes between
the two halves; the far chain continues through its own motion and natural
torso/near-limb occlusion. Head/torso size and the pouch's belt attachment remain
consistent while hair and tabard have restrained secondary changes.

## Sources and reproduction

Follow the [global visual standard](../../VISUAL_ART_STANDARD.md#running-animations).
Rebuild with `python tools/export_caelan_left_run_hd.py` and Pillow installed.

Source directory: `assets/source/characters/caelan/run_left_hd_review/`.
`idle_reference.png` is a crop of the approved left idle master. `guide_A.png`
through `guide_D.png` are reflected source-cell motion references from approved
right frames 9–16 followed by 1–8. `A.png` through `D.png` contain four new
chronological batches of complete left-facing redraws, all selected.

`provenance.json` records original generated files, source hashes, appearance
reference, per-batch phases and the exact source-cell/reflection recipe for each
guide. `registration.json` records selected cells, cranial bounds, neck/belt
references, sampling, whole-pose translations, timing, support and sole spans.
`protected_references.json` protects 217 pre-existing files, including the
approved front, rear and right runs and their review previews.

Technical export uses connected alpha extraction, uniform .12 nearest-neighbor
sampling and cranial/neck/belt registration. The slightly different source
density reflects the new drawings' head/body proportions; it is one uniform
whole-drawing density across all four batches, not per-pose height normalization.
The existing Caelan palette and inside outline pass retain material consistency.
There are no detached-limb transforms, pose rigs, independently timed upper/lower
strips, idle warps or runtime bob. Boot measurements never position or scale art.

## Validation and limits

Inspected every native pose and enlarged drawing, both limb pairs through their
complete cycles, pouch visibility/occlusion, contacts, flight, batch joins and
16 → 1. The loop follows the approved motion reference with newly resolved
left-side overlaps. These visual checks supplement export checks; uniqueness
and phase labels alone do not establish anatomy.

Crown positions are `7,8,6,6,7,6,6,8,7,8,7,7,7,6,6,8`: two artwork pixels total
excursion, at most two between adjacent frames including the seam. Audited
visible support-sole centers progress backward (screen right) in both stances:

- Right 1–5: 15, 28, 31, 44.5, 50 artwork pixels.
- Left 9–13: 13.5, 28.5, 33, 50, 51 artwork pixels.

These are sole-span observations rather than ankle-joint tracks. Progression is
uneven and is not calibrated to cancel actor displacement. Support-sole heights
vary by up to two artwork pixels. The in-place preview does not establish world
foot locking; traveling footage remains an integration check.

Checks pass for 16 unique hard-alpha RGBA frames, unclipped transparent margins,
exact sheet reconstruction, source/guide hashes, all 217 protected files, backward
support progression, crown continuity and a 400 ms cycle. The saved GIF has 32
alternating 20/30 ms delays totaling 800 ms: two normal cycles and one half-speed
cycle. Exact PNGs are authoritative for color and alpha. Existing directional
walk regression suites pass (25 tests).

Runtime integration is deferred pending artwork approval. Gameplay speed,
collision, padded-bank loading and direction/idle transitions are unchanged
by this standalone review package.
