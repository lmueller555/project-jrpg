# Painted motion regression observations

`before/manifest.json` records selected rejected **actual paintings** in authored
profile order, with original source paths, complete source cells, measured
registration and SHA-256 hashes. The PNG copies were captured before the current
correction. Lucan covers the held/rushed first exchange and second-half snap;
Iselin covers the material loop join; Crown covers the recovery-foot lift/reset.
The fixture drawings are deliberately unacceptable. Do not update them when
accepting a new drawing bank.

`contract.json` contains conservative limits independently reviewed against these
paintings before candidate adoption. Boot measurements are opaque distal-contour
quantiles in identity-reviewed regions, not ankle joints or world contact points.
The maximum adjacent displacement is 65 artwork pixels. The Lucan 7–18 exchange
has an additional scoped early-progress check and a concentration review
diagnostic. Those checks are not a universal running formula. A 120 pixel
full-cycle regional range rejects a frozen figure. Occlusion, foreshortening and
bent knees prevent a constant 2D summed limb length rule from being valid.

The projected vertical neck-to-belt span must remain positive and within ten
percent of the fixed original bank median. This conservative torso-model guard
uses measured, hash-bound registration and whole-image density; it does not
establish hidden anatomy or prevent legitimate frontal twist and lean. The
reference median is not recomputed from a candidate bank.

Whole-export registration is checked separately from the body-relative contour
measurements: adjacent exported neck and belt points may move at most 20 and
30 pixels respectively, including the loop seam. The calculation uses the
exporter's rounded whole-image origin. These conservative bounds catch gross
registration jumps without pinning the authored bob or certifying weight transfer.

The concentration trigger remains 0.70, but is a **review diagnostic**, not a hard
anatomical constraint. During independent review, continuous calf folding in the
revised Lucan 9–12 drawings produced 72.2% versus the original 70% proposal: a
4.56-pixel excess consistent with toe rotation/contour variation. Review found no
defensible quality boundary at that difference. The trigger was not raised and
the artwork was not forced to a tiny toe coordinate. The original paintings still
fail hard held-exchange and actual per-tick snap checks, and their concentrated
exchange remains reported. The ratio does not certify natural timing; inspect the
complete 7–18 sequence and its neighbors at the intended presentation.

Iselin hair, shawl and free coat use separate alpha-contour regions. Symmetric
90th-percentile nearest-contour distances have respective limits of 28, 30 and
35 artwork pixels. A conservative five-pixel RMS full-cycle excursion in contour
quantile features rejects frozen secondary regions. These checks do not demand
uniform pixel changes or certify coherent internal folds, material mass or rich
follow-through. Seam feature velocities are diagnostics: quantile correspondence
does not establish persistent cloth or hair points, and natural reversals exist.

The generic boot strip sometimes selects the opposite foot near the centerline.
Explicit hash-bound alternative sole windows correct those extraction errors;
they do not waive the adjacent displacement check. Their visible sole points,
uncertainty estimates, reasons and review evidence are recorded in the contract
and the accompanying overlays. Heel points and invisible joints are not inferred.
Distal points near a measurement-window edge produce a review diagnostic.
For an explicitly reviewed lowest-visible sole annotation, the actual alpha
quantile must support its y coordinate within the recorded three-pixel uncertainty
plus a one-pixel sampling margin. This validates that observation inside its
identity-reviewed ROI; it does not discover anatomical identity or infer a joint.

`registration_observations.json` binds the source path, cell crop, whole-image
origin, measured source neck/belt positions and density to the actual PNG hashes.
These registration inputs are
distinct from authoring targets. A new drawing or changed measurement needs visual
registration review and an explicit observation-artifact update. Original
template uncertainty was not independently calibrated; the values do not imply
subpixel anatomical accuracy. Generation prompts, desired hand/toe targets and
phase labels never establish output motion.

Run the deliberately rejected-art audit (expected exit status **1**):

```sh
python tools/audit_prologue_motion.py --before --output /tmp/motion-before.json --overlay /tmp/motion-before
```

Run negative controls, including repetitions, reordered actual drawings, frozen
actual material regions, idealized guide labels, changed crop/origin/registration and missing
coverage:

```sh
python -m unittest tests.test_prologue_motion.PaintedMotionNegativeControls -v
```

The production test covers every adjacent profile transition, repair join and
loop seam, the measured registration observations and 48 drawings / 800 ms.
Full shot playback remains necessary to assess anatomical construction, depth,
contact/release intent, carried equipment and secondary material action. The
settled frontal crop hides the ground/soles below the visible frame, so these
source-space contour checks do not claim production ground locking.

The internal braid uses a separate RGB check in `tools/audit_prologue_braid.py`.
It can cross opaque torso pixels, where alpha does not reveal its movement.
Source-bound distal-region boxes select actual light silver/gray hair pixels;
the cyan contributor overlay must be identity-reviewed to exclude cuffs, skin
and costume fasteners. The statistic is a regional centroid, which can lie in
the empty middle of a C-shaped curl. It is not an exact strand endpoint or
persistent material particle. Diffuse-end observations retain 20-pixel semantic
uncertainty. The default gross centroid step is 65 pixels, the minimum full-cycle
excursion is five pixels, and at least 50 selected pixels support a visible region.

`braid_contract.json` binds source hashes, actual exported RGBA pixel hashes and
exported neck registration. Registered-export fixtures use an explicit identity
transform so already-exported edge colors are preserved. A changed crop, scale,
origin or neck cannot silently reuse the old region approval. The retained braid
fixtures distinguish the original outward helper-15 reach jump from a later
rejected bulky edit and from the subsequent 38–39 release. The ordinary 31–32 and
33–34 pairs are positive controls; no frame number is programmed to fail.

Some statistics need exact-input reviewed diagnostics. Alpha-contour q90 is not
a metric with a triangle inequality: small matte changes can alter boundary
population/ranks and greatly change a cross-frame percentile. Native review of
the final palette-only 13/14 edits accepted continuous cloth action even though
shawl 13–14 measures 45.13 pixels against the unchanged default 30. Braid region
centroids can likewise mix different amounts of last-plait core and loose curl.
The contracts preserve each measured breach and its review reason. Exceptions
bind exact source/rendered pixels, registration, region and metric configuration,
and only a one-pixel band around the actual reviewed value. Changed inputs,
regions, or larger magnitudes lose that diagnostic classification. The original
rejected images still fail the default hard checks.

Run the actual rejected internal-braid RGB cases (expected exit status **1**):

```sh
python tools/audit_prologue_braid.py --before --output /tmp/braid-before.json --overlay /tmp/braid-before
python -m unittest tests.test_prologue_braid.PaintedBraidNegativeControls -v
```

`hand_before/` preserves the rejected v3 Crown 29–31 carry dip and independent
review strip. That below-gross-threshold hitch is manual visual evidence. There
is no invented monotonicity rule or claim that the 60-pixel hand bound detected it.

Final source identity review covers all 96 visible sole observations per actor.
Source-specific corrections at Lucan 23/26/27 and Iselin 25/31–33/37/38
exclude the opposite foreground calf. These are actual-image extraction
corrections, not skipped transitions or changed gait limits. The retained wrong
window regression deliberately restores the contaminated windows and requires
the independent observed-sole pixel support check to reject them.

All 48 final Iselin braid regions are identity reviewed on their actual selected
RGB pixels. The default 65-pixel regional step remains in force; exact reviewed
diagnostics preserve 13–14 = 73.563, 32–33 = 68.977 and 37–38 = 71.362 pixels.
These continuous bends illustrate the limit of a centroid of a changing painted
plait/curl population. Each diagnostic binds the source, rendered RGBA pixels,
registration, boxes, color rule and measured magnitude, with at most one pixel
of sampling tolerance. The retained old reach replacements still fail.
