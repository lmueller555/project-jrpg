# Iselin — approved detailed gate approach and stop

This self-contained pack preserves the detailed R2 animation the user approved
on 2026-11-18 and subsequently authorized for the live arrival cutscene. The
25 exported PNGs retain the approved file bytes, colors, alpha, 80×96 cinematic
canvas and `[40,92]` anchor. There is no 24×36 intermediate or additional
anatomy construction during export.

The [sprite and animation standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md)
owns general authoring guidance. These notes record this pack's sources,
registration, approval boundary and reproducible production outputs.

## Approved scope and selection

`gate_walk_left` supplies the sixteen approach poses, `stop_left` supplies the
700 ms stopping action, and `gate_stand_left` supplies its final whole drawing.
The detailed final stop and standing PNGs are identical. Timing remains sixteen
35 ms walk frames, a 40 ms final-walk handoff, eight 60 ms stopping drawings,
a 60 ms hold and a 120 ms standing recovery.

The late approach is anticipation for this particular gate stop. Its last-to-
first seam is not approved as a generic looping travel cycle. Separate ordinary
travel loops, other cinematic directions, listening and gesture poses, aerial
art, overworld sprites and the portrait are outside this pack's approval.
The owning scene and combined actor builder determine those selections.

Live integration reuses the first eight approved complete drawings as
`gate_incoming_left` during the ground-reference portion of aerial descent.
That limited cycle has its own reviewed 8→1 seam and a 16-pixel stride, retaining
the same two-pixel pose spacing. It joins `gate_walk_left` on the identical first
drawing at the ground-shot boundary without repeating stop anticipation or
altering the generic world-travel banks. The aerial overhead/oblique artwork
remains separate and unchanged.

## Complete original drawings

`recipe.json` records fixed whole-master scale, crop, source anchor and the
protected head window. The exporter never fits occupied pose bounds, slides a
foot, stretches anatomy or constructs detached limbs.

| Original master | Selected drawings |
| --- | --- |
| `masters/walk_12_compact_single.png` | Approach 12 |
| `masters/walk_13_14_pair.png` | Approaches 13–14 |
| `masters/walk_15_16_pair.png` | Approaches 15–16 |
| `masters/stop_01_04_quad.png` | Stops 1–3; unused original fourth drawing retained |
| `masters/stop_04_compact_single.png` | Corrected stop 4 |
| `masters/stop_05_08_quad.png` | Stops 5–8 and final standing pose |

Approaches 1–11 reuse the original complete R1 camera drawings in
`references/walk_left/`. The accepted high-resolution head/neck is retained in
rows 0–34 across the completed R2 drawings, using `references/stand_left.png`.
The moving bodies below that window remain complete authored poses. This
documented identity preservation does not provide procedural limb animation.

`lineage.json` records how those twelve complete references were originally
sampled from the unchanged `lineage/masters/walk_a.png`, `walk_b.png` and
`stop.png` generated masters. The exporter verifies the reference pixels
against those original source crops before applying R2 preservation. Thus
regeneration has no dependency on an external review worktree or an
`assets/review/` directory. Earlier unselected studies remain historical in
their original review workspace; they are not inputs to the live pack.

## Approval and reproduction

`approval.json` is the immutable approved-art snapshot: production-relative
paths, original review provenance, PNG and RGBA hashes, canvas, anchor, timing
and hashes of all active source inputs. Export fails if a source changes or
if any of the 25 resulting drawings differs from that snapshot. Approval of
artwork and activation by the live scene remain distinct facts.

The exporter returns production PNGs and `registration.json`, together with a
manifest merge piece. `tools/build_regent_iselin.py` owns the combined actor
manifest and preserves the separate travel and directional banks.

```sh
python tools/build_regent_iselin.py
python tools/build_regent_iselin.py --check
python tools/export_iselin_gate_detail.py --check
```

`registration.json` records the complete-drawing source/region hashes,
sampling, stable identity window, final pixels, output hashes and manifest
piece. Rebuilding reproduces the approved artwork; scene motion, lifecycle and
actual camera playback still require their own integration checks.
