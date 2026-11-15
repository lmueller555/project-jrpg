# Caelan front run — artwork review

Status: user-approved artwork, accepted for merge into main. Gameplay integration
remains deferred. The approved directional design is retained. The live registry
and legacy run bank are unchanged.

- [Normal/half-speed preview with approved idle](preview.gif)
- [Numbered complete frame drawings](frames.png)
- [Native bank and phase metadata](../../../assets/characters/caelan/review_hd/run_front/animation.json)

Sixteen complete generated drawings, 25 ms each, retain the existing 400 ms
two-step cadence. Front-view anatomical right is viewer left; the single pouch
stays on anatomical left, viewer right. Both arms counter their same-side legs,
with bent elbows and alternating recovery, support and flight. The final pose
already begins right touchdown, continuing into frame 1; left touchdown begins
at frame 8. Flight is frames 6–7 and 14–15. The metadata reflects these drawings
rather than imposing the original profile guide's phase boundaries.

The native canvas is **48×76**, density 2, logical canvas 24×38. Four extra
transparent vertical pixels permit complete drawings at the same uniform
sampling density as the approved walks instead of shrinking the body. Draw
anchor is [24,64], foot reference [24,72]; both shift together by four artwork
pixels from the idle. The idle comparison aligns draw anchors. Future runtime
integration must honor these per-bank anchors; the live fixed-canvas loader is
not changed by this review. Collision and movement speed remain unchanged.

## Construction and reproduction

Canonical guidance: [Visual art standard](../../VISUAL_ART_STANDARD.md#running-animations).
Run `python tools/export_caelan_front_run_hd.py` with Pillow installed.

Sources are under `assets/source/characters/caelan/run_front_hd_review/`:

- `idle_reference.png`: technical crop of the approved front idle master.
- `keys.png`: generated contact/flight key studies.
- `A.png` through `D.png`: four chronological batches of complete drawings.
- `support_correction.png`: complete replacements for 4, 8, 12 and 16.
- `flight_correction.png`: complete replacements for 7 and 15.
- `registration.json`: selected source cells, hashes, scale, translations and phases.
- `protected_references.json`: hashes of 159 pre-existing asset/review files.

All creative poses were made with image generation against the approved design.
The exporter extracts the connected alpha body, uniformly samples whole poses
at .124 with nearest-neighbor, registers cranial centers and the body arc, uses
the existing shared Caelan palette, and applies the established inside contour.
Whole-body vertical offsets reconcile crown/neck/belt placement across batches;
there are no detached-limb transforms, pose rigs, stretched parts, independently
timed body strips or idle warps. Original generated sheets remain intact.

## Validation and limits

Checked all sixteen native drawings, both contacts, flight, batch joins and
the loop seam. A complete-pose correction addressed premature support release;
another addressed the approaching boots during flight. Crown excursion is three
artwork pixels overall, with at most two pixels between neighboring drawings.
Pixel quantization leaves small differences in projected features and sole
height; this is a stylized cycle, not evidence of world-foot locking.

Export checks verify sixteen unique hard-alpha RGBA frames, unclipped transparent
margins, exact spritesheet reconstruction, source hashes, unchanged protected
references and the 400 ms cycle. GIF verification checks 32 alternating 20/30 ms
delays totaling 800 ms: two normal cycles and one half-speed cycle. Exact PNGs
are authoritative for color and alpha.

The existing right, left, front and rear walk regression suites pass (25 tests).
Traveling footage is deferred until authorized runtime integration; this package
reviews the in-place animation and approved-idle scale comparison.
