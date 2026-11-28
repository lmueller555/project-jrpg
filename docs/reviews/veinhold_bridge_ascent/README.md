# Fire Veinhold — Bridge Ascent

Status: implemented and validated. The source exports are frozen, the complete
native bank reproduces from source, and all four production Gallery captures
pass. The evidence below distinguishes source, native-picture and runtime checks.

## Scope

Append the approved eight-second bridge ascent at reel 47–55 seconds. The camera
continues from the face reveal, rises over Lucan and reveals the bridge, the
four frozen Carcovian guards behind the party and reinforcements at the fortress
end. Native presentation remains 960×640 at 60 Hz: 480 displayed intervals and one
inclusive terminal sample. The complete film contains 3300 displayed frames.

The existing seven shots and approved source artwork remain historical and
production inputs. The new shot requires view-correct whole-figure drawings and
newly exposed environmental surfaces; rotating a frontal picture does not
establish those views. Construction follows
[the global animation standard](../../SPRITE_ANIMATION_STANDARD.md); the
[scene owner](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md) owns cinematography
and approved disclosure.

## Entry and camera contract

At reel 47 seconds the camera begins at bridge-local [0, 57.26, 1.55], pitch −0.08 rad,
focal 900 pixels. Lucan starts at Y = 54.26 m and travels 4 m/s. Iselin remains on his
right, 0.5 m behind; the Crown soldier stays on his left, 3.048 m behind. Their 800 ms
gait phases are 0, 1/6 and 0.3 seconds respectively. Eight seconds covers ten cycles.

The camera retains screen-right −X throughout: mainland toward the top, fortress
toward the bottom. It clears the party before crossing overhead. Its optical
orientation and lens must keep the trailing soldier visible during the close
transition. The final frame covers the 299.08 m span at a height of
300 m with a 550-pixel lens; tiny distant figures communicate group movement.

Body size is registered from appropriate head/shoulder dimensions and the actual
pose projection, never by fitting occupied silhouette height. Overhead stride,
hair and clothing may occupy a longer footprint than a standing body. Whole
images retain their anatomy; proxy guides are authoring references only.

### Inherited background visibility

The approved face-reveal bank omits the four distant frozen guards. Adding them
at the identical opening camera changed 3194 pixels behind the runners and
created a visible cut-boundary addition. Shot 8 therefore retains that inherited
omission during the initial view, then restores the fixed-position overhead
drawings while their positions are outside the picture. This is an explicit
presentation-continuity treatment, not a claim that a physical obstacle hides
them. The earlier bank remains unchanged. The actual entry matches the preceding
terminal picture exactly, and native review covers the later reentry.

### Rejected drafts and useful controls

The initial one-second camera draft clipped the Crown soldier. Its actual
parameters are retained in the camera fixture; the revised optical path and
lens keep all three physical crowns inside the close view without relocating
the party. A passing camera test establishes framing, not drawing quality.

Early drawing trials also exposed problems that numerical camera tests cannot
catch: Lucan's recovering boot jumped at a source-batch boundary, Iselin's
palette and body posture changed between small-angle batches, and the Crown
soldier's uncalibrated drawings appeared too large. Source-size controls use the
same camera for both drawings; final acceptance requires chronological native
frames as well. Reusing approved early gait poses over a small, reviewed change
in view is distinct from using frontal drawings for the overhead portion.

### Transparent railing regression

The initial renderer treated each full railing panel as solid depth, including
its transparent brace gaps. At 0.4–0.8 seconds this left the earlier angular
background in those gaps instead of the intersected mainland or sea. The fixed
renderer composites the same painted braces over the actual world and records
depth only where the rail is materially occupied.

[Retained witnesses](render_regressions/witnesses.json) identify three actual
pixel rays. `tests/test_prologue_ascent_world.py` independently intersects those
rays with the rail and horizontal land/sea planes, confirms zero brace alpha,
and checks that depth reaches the physical surface. The
[control log](logs/rail_regression_control.log) deliberately runs the rejected
function: all three subtests fail as expected; the current renderer passes.
The reconstructed rejected function reproduces the retained actual frame 24
exactly. Its provenance is explicit: the complete original builder bytes were
not retained, so this is not presented as a pristine old-file snapshot.

### Actual opaque-background counterexample

The first exported overhead sheet retained its generated cell background. A
production-compositor probe exposed white/checkered rectangles around phases
0–15. The artist replaced that source through ImageGen; technical export does
not paint or key out a generated background manually.

An unaltered RGBA cell from the rejected sheet is retained as
`tests/fixtures/prologue_ascent_camera/rejected_opaque_cell.png`, with its source
hash and crop in the adjacent JSON. The production tests reject that actual
sample and check that every used party drawing has a cutout silhouette. This
loose matte check cannot establish limb ownership or smooth motion; those
remain source and native-frame review gates.

## Required evidence

The `world_proofs/`, `entry_proofs/` and geometric blockout images are retained
authoring snapshots. They are not the final composed bank. Final picture evidence
belongs in `performance_proofs/` and the actual Gallery captures below.

- Camera blockout at the entry, every close angle change and the final wide.
- Source/model keys and complete transition/cycle drawings, with raw generated
  masters, exact prompts, generation identifiers and reference hashes.
- Actual native sequences across the 47-second join, view transitions, gait
  exchanges, source-batch boundaries and loop seams.
- World-fixed frozen-guard positions, true upper ice/armor surfaces and coherent
  reinforcement movement from the fortress.
- Continuous global alarm, smoke, wind and contact phases; distance-aware Foley
  and correct standalone Gallery seek state.
- Reproducible 481-picture bank, image integrity and explicit eight-slot streaming
  with no eager character bank. Four-frame handoff prefetch is measured separately.
- Real standalone/full-film Gallery captures in both presentation modes, controls,
  natural completion, cleanup and persistent-state isolation.
- Preserved earlier picture/WAV hashes, focused regression results, compilation
  and whitespace checks.

## Final validation

- [255 targeted tests pass](logs/final_tests.log), including actual entry/full-film
  picture controls, camera framing, retained failure controls, contact/audio
  continuity, streaming ownership, Gallery controls and cleanup.
- [All 71 changed/new Python files compile](logs/compilation.json). Runtime,
  tests, tools and documentation pass the scoped whitespace check. Frozen
  authoring sources and raw transcripts retain their recorded whitespace;
  [the scan records those cosmetic exceptions](logs/whitespace.json).
- [Frozen source receipts](source_checks/frozen_profiles.json) bind all three
  party profiles. Each has 133 logical transition rows and 48 cycle poses;
  Crown references 127 unique PNGs, Iselin 168 and Lucan 156. Their retained
  masters, prompts, reference hashes and export recipes remain available.
- [Bake](logs/bake.log), [integrity verification](logs/verify.log) and
  [fresh reproduction](logs/fresh_check.log) pass. Verification checks all 634
  bank files; fresh rendering reproduces every one of the 481 normal and
  Reduced Motion samples, metadata and source/camera/performance ledgers.
  The temporary environment cache is not used for that fresh check.
- [Independent native review](independent_review/final_bank_review.json) covers
  the actual entry, all twelve checkpoints, close source joins, overhead cycle,
  frozen-guard reentry and both late gate exits. The four frozen guards retain
  their world positions; all eight advancing guards retain coherent direction
  and staging. At the final wide, bodies are only 1–3 pixels: review establishes
  placement, direction and emergence there, rather than hidden joint anatomy.
- [Four actual Gallery captures](gallery/validation.json) pass encoded frame,
  clock, source-hash, cache, natural-completion and persistent-state checks.
  Twelve native still comparisons are RGB-exact between standalone and complete
  captures. Each session returns to the Gallery and leaves no save/settings file.
- [Preservation comparison](preservation_after.json): 1416 prior files checked,
  1412 byte-identical and no missing files. The four expected changes are scene
  metadata, audio metadata, Gallery metadata and the complete-film thumbnail.
  All earlier picture banks, twelve original WAVs and seven shot thumbnails
  remain byte-identical. The 39–47-second PCM preservation regression passes.

| Production Gallery capture | Frames at 60 Hz | Draw/update mean / p95 |
| --- | ---: | ---: |
| [Bridge Ascent](gallery/shot08.mp4) | 480 | 5.21 / 14.32 ms |
| [Bridge Ascent, Reduced Motion](gallery/shot08_reduced_motion.mp4) | 480 | 5.48 / 14.72 ms |
| [Complete film](gallery/complete.mp4) | 3300 | 7.03 / 12.61 ms |
| [Complete film, Reduced Motion](gallery/complete_reduced_motion.mp4) | 3300 | 6.03 / 10.52 ms |

Timing uses SDL dummy, includes the clean-picture copy and excludes encoder
writes. These are capture diagnostics, not a hardware-independent frame-rate
guarantee. The ascent uses at most eight native image slots, **18.75 MiB**, and
releases them at completion. The largest observed face/ascent handoff is
27.54 MiB, below the twelve-slot **28.125 MiB** bound. These figures describe
those image owners, not total process memory or every earlier owner: the normal
complete-film capture records 92 MiB for the combined image caches.

Review uses chronological native still sequences and the actual runtime
captures. Normal-speed movie watching and hardware listening are not claimed.
The movies' sound is reconstructed offline from production WAVs and the shared
scene clock. [The executed validator](gallery/validation_executed.py.txt) and
capture JSON retain the exact methods, hashes and measured limits.
