# Eldenmere well — staged mechanism (PR 2)

**Status: staged, pending user visual review, not selected by gameplay.**
The new controller and presentation are additive. The existing well, gardener,
town map, collision, navigation, services and quest behavior remain unchanged.
PR 3 supplies matching actor artwork; PR 4 connects the coordinated replacement
to the live town. Examination and sound playback follow in PR 5.

## Review

- [Normal-speed operation](operation_normal.gif).
- [Half-speed inspection](operation_half_speed.gif).
- [Reduced ambient motion](operation_reduced_motion.gif).
- [Numbered controller phases](numbered_phases.png).
- [Lowering in the actual town backdrop](town_lower.png).
- [Raising in the actual town backdrop](town_raise.png).

These are **offline, controller-driven mechanism previews**. No moving gardener
is present: actor-owned pails are deliberately omitted before attachment and
after detachment. Their appearance/disappearance demonstrates the controller's
ownership rule, not an attachment/retrieval animation or proven hand contact.
The later actor/joint review must establish those performances.

The normal preview uses actual 50 ms controller updates and three disclosed
500 ms station-readiness holds. The operator is a synthetic identity, not an
NPC teleported through work stations. Normal and reduced previews retain the
same functional clock; half speed doubles only review playback delay. GIFs use
a common palette and delta frames; native PNGs remain the color reference.

The six town stills render a disposable initialized Game at native 960×640,
with the opening disabled and temporary saves/settings. Only the in-memory well
drawing is substituted. The ordinary town actors, buildings, ground and Caelan
remain unchanged; there are no simulation updates, seeded quests or new live
interactions. These compositions do not validate moving-actor depth.

## Source and interface

The source contract is
`assets/source/terrain/eldenmere/well_hd/mechanism/contract.json`.
`well_mechanism.py` owns operation tokens, station readiness, continuous time,
exclusive pail ownership and once-only cues. Immutable snapshots expose crank
phase, hook/rope/pail registration, water contact, fill and rendering region.
Presentation never advances time or performs transfers.

The artwork recipe is the adjacent `art_recipe.json`; the staged export registry
is `assets/terrain/eldenmere/well_hd/mechanism/manifest.json`.
`tools/build_eldenmere_well_mechanism.py` authors native rigid mechanical
geometry, not character limb animation: sixteen centered crank samples, sixteen
phase-locked winding-mark samples, a compact hook, rope material and six ambient
plus six contact-water overlays. It reuses PR 1's retained structure and pail
drawings without modifying or independently stretching them. Art and controller
agree on a one-logical-unit hook attachment-to-rope offset.

`well_mechanism_presentation.py` preloads those parts and the PR 1 layers/pails.
Its bounded 96-entry native pose cache stores at most 9,732,096 composite bytes;
returned images are copies so callers cannot corrupt cached artwork. This is an
offline allocation bound, not a claim about unmeasured live frame performance.

## Physical calibration

- The PR 1 loading hook target remains local `[36,74]`.
- Guide motion raises it continuously to `[36,54]`. The pail base is then at
  y66.5, safely above the water plane y69 and the near rim; this is where its
  region can change without a hidden teleport.
- Lowering proceeds from y54 to y72. Base contact and mouth submersion are
  separate geometric conditions; filling starts only after the mouth is below
  the water plane.
- Raising reverses the path. Secure motion returns the full pail from y54 to
  the reachable loading point in the foreground before retrieval.
- The bare hook and rope remain available at loading height while the actor
  owns the pail. No high-winch attachment jump is reintroduced.
- The coordinated operator target is world `[564,866]`; this additive contract
  records the later pose calibration without rewriting PR 1's historical pack.
- The loading target is world `[528,894]`. Both player and gardener probes are
  clear; the new back-facing key reaches the loading grip naturally while
  retaining the actor's distinct draw and visual-foot registrations.

All water glints, contact ripples and emergence droplets stay within the PR 1
painted-water mask. The shaft uses its shaped aperture and solid near coping;
only submerged load pixels below the authored water plane are covered. Drips
start below the pail's actual support point, not inside its wood body. Fixed
masonry, roof and posts remain stationary.

## Evidence and limits

[The trace](trace.json) records every actual controller sample and cue.
[The observation record](observations.json) retains the source contract,
controller, presentation, exporter and helper hashes, output hashes, disclosed
readiness fixture, native town context and cache state. It verifies all 969 live
production files and 207 protected legacy/runtime files against the retained
pre-rework baseline. No source is silently repinned.

The focused controller and presentation checks cover frame-rate invariance,
readiness holds, stale-token protection, immutable observations, continuous
registration, geometric fill eligibility, once-only events, cancellation/reset,
native mask confinement, canonical pail ownership, bounded cache behavior,
source/export provenance and genuinely read-only export checks. PR 1's original
pack checks continue to pass. Final verification passes **45 checks**: 17
controller checks, 14 presentation/export checks and the 14 retained PR 1 checks.
The staged exporter verifies **49 outputs** without writes.

Reproduce the staged review with:

```sh
python tools/build_eldenmere_well_mechanism.py --check
PYTHONPATH=.:tests python -m unittest test_well_mechanism test_well_mechanism_presentation test_eldenmere_well_pack
python tools/capture_eldenmere_well_mechanism.py
```

Live pause/focus wiring, moving-actor collision/occlusion, room travel, complete
garden trips, save reconstruction and operation audio remain integration work;
this staged preview does not certify them.
