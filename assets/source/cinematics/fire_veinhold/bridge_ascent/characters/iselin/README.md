# Iselin: bridge-ascent source performance

These are complete ImageGen-authored cinematic drawings. Final figure pixels
never come from Blender, a procedural character renderer, detached limbs,
warped frontal sprites, crossfaded poses or a pasted portrait. Blender files and
colored knee/boot annotations are construction references only.

The approved identity is white/silver long hair, blue eyes when visible, a blue
and silver coat, mantle on anatomical right and a single forward braid on
anatomical left. With this camera, anatomical right is image left. Wind trails
behind the runner and toward image left. The face becomes occluded by the
crown as the camera rises; the character does not look up to preserve a face.

## Source selection and provenance

`generation.json` beside each batch records the unchanged generated master,
generation identifier, exact prompt SHA and every actual input-image SHA.
Whole-sheet transparency edits have their own retained input, raw master and
generation record. Old trials remain as authoring history; their presence is
not evidence of production selection or approval. The exporter and
`export_registration.json` identify the sources actually sampled.

- Transition0–19 directly references the unchanged approved shot07 paintings.
  Those1024×1024 images retain anchor512,960 and their exact bytes, preserving
  the preceding shot's inclusive endpoint.
- Transition20–55 uses the explicit selection in
  `register_close_candidates.py`. Native reviews rejected early darkened,
  tucked-head batches and the initial43→44 and47→48 construction resets.
  Complete redraws repair those joins; no RGB grade or regional transform
  conceals them.
- Transition56–117 uses the complete elevated drawings explicitly selected in
  `export_performance.py`. Labelled knee/boot chains distinguish a projecting
  knee from the calf folded back toward its boot. An extended knee does not
  imply an extended straight shin.
- Bounded complete redraws72–79 and88–95 bridge the observed hair/mantle regime
  changes between existing neighboring performances. Their reference pairs
  preserve both material endpoints; whole-sheet leg corrections retain those
  material drawings while following the labelled folded calf/boot chains.
  Continuations80–87 and96–103 replace the intervening original model islands,
  using the exact new79/88 and95/104 bracketing drawings. Phase0 contact remains
  at86. No endpoint is concealed by a pose blend or a fitted hair cloud.
- Transition118–119 exposes one complete high-view phase32 passing drawing for
  two ticks. The camera/root and target gait clock continue at60Hz; both actual
  target phases are declared. This interval contains no skipped contact.
- Transition120–132 and the later small actor use the newly drawn48-pose
  overhead cycle, matched to the active gait phase. The source is90° overhead;
  the actual late transition elevation is declared separately.
- The48 cycle drawings are selected by the three `selection.json` files in
  `overhead_000_015_validated_chain`, `overhead_016_031_pose_retry` and
  `overhead_032_047_pose_retry`. Passing/contact construction and all selected
  source-cell alpha corners were reviewed. Specific corrections replace the
  first trials' prematurely extended shins.

## Registration and export

Run from the repository root with the authoring environment (Python, Pillow,
NumPy and the existing OpenCV registration helpers). The deterministic export
itself needs Pillow; game playback does not load these authoring helpers.

```sh
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/iselin/register_close_candidates.py
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/iselin/export_performance.py
python assets/source/cinematics/fire_veinhold/bridge_ascent/characters/iselin/export_performance.py --check
```

Export operations are whole-figure cell crop, uniform premultiplied resampling,
translation and the documented alpha≤16 floor. Output is1024×1536 with internal
ground/root anchor512,960 and500artpx/metre. Occupied figure height is never a
density ruler: overhead footprint naturally shortens, while observed cranium
and shoulder size remain stable. Actual observed feature points, uncertainties
and overlays are retained. A crown-correlation center does not establish that
its correlation-box width measures a rigid skull. The rounded visible hair cap
can merge with wind-blown hair; neither that envelope nor exposed face area is
a reliable rigid ruler after occlusion grows.

The cycle retains its independently reviewed uniform master densities. For the
two material bridges, the same visible beaded temple motif supplies a bounded
adjacent-view appearance check. Measured18→20sourcepx growth of that motif within
the56–71 sheet supports an endpoint-calibrated framing estimate: the passed
first56 drawing is unchanged, and whole-image density reduces about10% by71.
Intermediate widths are explicitly estimates between measured endpoints, not
invented independent observations. The physical hair envelope is never forced
to a constant width. Per-pose uniform whole-image density is allowed when actual
source framing changes; limbs or body regions are never rescaled separately.
The old warm-skin detector's false braid-ornament match is explicitly rejected.

The white-crown projection feature is calibrated to the accepted close-entry
registration; it is not a claim about a hidden skeletal joint or adult height.
The final portable `actorperformance.json` declares133 chronological transition
records,48 overhead poses and an exact SHA for every referenced PNG. `--check`
reconstructs new exports in memory, verifies raw masters and exact authoring
inputs, and compares profile/PNG bytes.

## Guide diagnostics and review limits

`build_pose_guides.py` and its original guide images are retained. The separate
`build_pose_guides_v2.py` uses explicit rest-radius/length scaling and checks the
actual evaluated cylinder cap centers through `matrix_world`, across all48
poses and eight limb segments. Maximum observed error is1.0734µm. Before/after
renders did not establish a stretched-mesh defect: the apparent low segment was
an advancing knee with a folded-back boot. Diagnostic labels made that reading
clear to the image authoring tool. No guide pixels enter exported figures.

One diagnostic overwrote raw guide0 before archival. Its original image pixels
survived in an unchanged input atlas; the original full PNG bytes were recovered
against the already recorded SHA by restoring the transient Blender metadata.
`guide_revisions/legacy/guide0_recovery.json` records the exact recovery. Original
raw-guide and actual ImageGen input-image hashes are now preserved.

Source-cell corners, individual figure crops, rigid-size registration,
chronological joins, real native camera composition and runtime playback are
different review gates. Small translucent edge samples in cycle6/7/10/11 are
declared in their selection receipt; a corner check alone cannot prove an
unclipped silhouette. Final full-scene acceptance belongs in the repository's
bridge-ascent review record, outside this hashed source directory. A complete
manifest or passing source key alone does not claim that final playback passed.
