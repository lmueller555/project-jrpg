# Staged gardener well performance

This is the additive PR3 character delivery. The existing gardener routine,
legacy character bank, live well rig, town map and collision remain active and
unchanged. These exports are not selected by Game. Visual approval remains
`pending_user_review`; PR4 owns live actor integration, navigation, water
accounting, lifecycle, save restoration and final scene depth.

## Delivered artwork and registration

The staged source lives in
`assets/source/characters/npcs/female_02/gardener_well_hd/`; the isolated export
bank is `assets/characters/npcs/female_02/gardener_well_hd/`.

- 88 new, complete image-authored drawings: sixteen lowering, sixteen distinct
  heavier raising, eight back handoff/recovery, eight pickup, thirty-two pours
  (left/right ground and raised trough), and eight engage/brace/brake/recovery.
- 32 explicitly retained legacy complete travel drawings: four frames for each
  direction, empty/full, preserving the 140 ms frame and 560 ms cycle cadence.
  Those travel bodies are compatibility artwork enlarged uniformly from 1×;
  they are not newly authored HD walking cycles. Speeds remain 60/50 logical
  units per second for empty/loaded travel.
- 120 exported complete poses, 22 clips, 35 canonical pail variants (five rigid
  tilt angles, seven fill levels), five interior masks and one manifest:
  **161 deterministic exported files**.
- New action drawings use 96×96 native artwork in a 48×48 logical action canvas.
  Draw anchor `[24,36]` and visible foot anchor `[24,40]` are distinct. Per-master
  uniform sampling and explicit foot registration preserve pose changes without
  independently fitting every silhouette.

Retained image-generation masters, extraction scripts, SHA256 provenance and
native frame sources are in `operating_art/` and `handoff_art/`. No body parts
rotate, stretch or warp in the exporter. Only the rigid canonical PR1 pail is
rotated on a padded 64×64 artwork canvas; fill changes are restricted to the
correspondingly transformed interior. Earlier operating attempts remain clearly
labelled historical in the recipe and are not consumed by any current clip.
The source-cell order is explicitly mapped to crank phase; sixteen files alone
are not proof of correctly ordered movement.

## Snapshot adapter and ownership

`gardener_well_presentation.py` samples an external immutable model snapshot.
It introduces no mechanism clock, gameplay cues, ownership transfers or water
changes. It uses the authoritative sixteen-sample crank phase, including the
nonzero stopped fill angle. Dedicated brace/brake drawings cover the calibrated
rest quadrant; other operating angles use their matching complete drawing.
The optional `select_pose(..., facing=...)` argument asserts the required
phase-facing and rejects a conflicting direction. Cached native images and the
public manifest are protected from caller mutation.

Back handoff keys reach the loading grip before the model's 70% attach or 65%
detach cue, hold through transfer, then lower to carrying height. The pail is
drawn by the actor only when the snapshot says `pail_owner == 'actor'`; the
mechanism renderer draws it only for `well`. There is one canonical pail,
including pickup/setdown, four carry directions and four pour modes. Back carry
and handoff apply torso occlusion. Pour streams start at the transformed mouth
edge; their bed target is a presentation input, not a watering event.
`carry_pose` accepts a normalized walk phase, not milliseconds.

The exact merged PR2 contract is copied read-only as
`mechanism_reference.json` (SHA256
`049a51cc1b13049866737c6afaa20ecea936d150a8db20080a095dcc59d731e5`).
It owns the calibrated loading station `[528,894]`, operator `[564,866]` and
world origin `[492,800]`. PR1's historical coordinates were not rewritten.

## Review evidence

- [Joint operation](joint_operation.gif) and [half-speed operation](joint_operation_slow.gif)
  use the actual merged `WellMechanism` and `WellMechanismPresentation` at
  native 2× density. Readiness waits while an explicit offline actor fixture
  travels `[528,894] → [564,894] → [564,866]`, reversed for retrieval. The model
  remains the sole mechanism clock. Travel is 60 logical units per second;
  every sampled 12×8 gardener and 24×12 player probe clears the unchanged static
  collision. This is an offline route proof, not a live NPC navigation test.
- [Lowering numbered sheet](lower_numbered.png) and
  [raising numbered sheet](raise_numbered.png) list all sixteen crank indices.
  [Lowering loop](lower_loop.gif), [raising loop](raise_loop.gif) and their
  `*_loop_slow.gif` companions replay the full corresponding actual-model phase
  in chronological order with 50/100 ms samples. Raising therefore traverses
  the opposite crank direction. Repetition restarts the whole operation phase,
  including the bucket position; numbered sheets are index references.
- [Ownership cues](handoff_cues.png) show before/after attach and retrieve.
- [Directional carry](directional_carry.png), [four pours](pour_bindings.png)
  and [pickup/setdown](pickup_setdown.png) show complete body/pail bindings.
- [Observations](observations.json) retain all 371 actual-model samples, events,
  source/contract hashes, 32 measured hand contacts, static-route probe proof
  and artifact hashes. Normal operation reaches completion at 17.75 seconds;
  the stable completion arrangement remains briefly for review.

The reviewed drawings retain the gardener's chestnut bob, sage clothing and
brown boots. Raising reads stockier, with a wider three-quarter head and an
exertion crouch compared with profile lowering/support. This difference was
accepted for this staged delivery; it is not an exact silhouette match. Feet
remain stable (lowering quantizes within one artwork pixel). Some working
finger/knob gaps remain visible, all below four logical units; these are natural
near-contact drawings, not exact finger contact. The back handoff pail is almost
entirely hidden by the torso, with no jump across either ownership cue.

The joint preview composites the whole well and then the actor. It demonstrates
phase, pose, station and object continuity; it does not approve final runtime
well/actor split-layer ordering, NPC blockers, cancellation recovery or save/load.

## Reproduce and validate

From the repository root, with the normal Pillow/Pygame dependencies installed:

```sh
python tools/build_gardener_well_hd.py
python tools/build_gardener_well_hd.py --check
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_gardener_well_hd.py
python -m unittest discover -s tests -p test_gardener_well_hd.py
```

The exporter writes only its isolated namespace; `--check` is read-only and
fails on stale exports. Focused tests cover native registration, retained-source
fidelity, per-master sampling, crank selection, frozen input state, ownership
cues, pickup/setdown, carry depth/cadence and canonical interior-only fill
changes. Independent PR1/PR2 checks and preservation hashes accompany the PR;
passing tests do not substitute for the visual evidence above.
