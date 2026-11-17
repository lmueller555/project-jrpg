# Liam's block box: production asset and interaction audit

Baseline: `5630648b`, the merged household-plots main. This is a scoped correction,
not a new room layout or routine design.

## Native production evidence

- [Before reach/pickup/return](before_contacts.png), [before actual room](before_take_2.png).
- [After reach/pickup/return](after_contacts.png), [after actual room](after_take_2.png).
- [All six live box counts](after_counts.png).
- [Actual-route four-direction carrying](after_carry_views.png).
- Actual-speed, lossless native crops: [taking](take_native.png) and
  [returning](return_block_native.png). These PNGs contain animation frames.
- [Capture/state/preservation results](validation.json); [baseline frame log](before_frames.json).

These are `Game.draw()` frames from the authoritative 960×640 native buffer,
not the logical mirror, isolated compositing mockups or enlarged screenshots.
Sheets only arrange native crops with labels. The normal controller completes
its full 79.3-second session. The initial long wait is skipped, accident/forget
choices are forced off, and Liam follows his real collision-aware paths and
poses. No actor position is changed after beginning the routine. A separate
capture covers every carry direction naturally encountered by that path.

## Cause and correction

The initial five-count frame came from a generic toy chest. Count changes used
a different generic empty-box drawing plus independently extracted toy icons.
An unrelated cropped front face was then painted over the held piece. The three
silhouettes, dimensions and projections disagreed, so the box changed design at
the first cue and its front appeared detached. Retained room aliases could also
override a new global prop replacement.

`tools/liam_block_art.py` now owns one native 64×48 drawing at 2× artwork density
and the same 32×24 logical canvas. Rear and front rims are parallel, sides are
vertical, and the rectangular opening agrees with Eldenmere's orthogonal camera.
Pinned oak planks, worn edges, recessed interior and four painted wooden cuboids
plus one long oak block are drawn directly at native density. Fine contours and
grain are one artwork pixel. No generated furniture-sheet cutout participates
in Liam's live box, loose pieces or lip.

All 32 identity combinations share byte-identical structural layers. The lip is
the literal front layer from that drawing and is therefore pixel-identical to
every complete state. It uses the actual entity origin and is only repainted
when a held piece crosses it during a box reach. Dormant legacy aliases in other
rooms remain unchanged; Liam's room explicitly owns its corrected aliases.
Separated empty/full source-layer proofs are exported beside the live assets;
logical support, depth and contact registration are declared on the entity.

The runtime chooses box contents by the actual five identities, not just the
number present. At the authored third pose, the same piece leaves the box and
appears in the hand, or leaves the hand and returns to storage. This also fixes
count-only cleanup showing a different piece from the one just returned.

## Poses, staging and lifecycle

The existing four-pose kneel/reach/grasp/recovery sequence was inspected at native
size. Its child silhouette, folded knees, planted support, physical reach and
short deliberate cue are retained. Facing is explicitly published before each
left/right action instead of inheriting the last travel waypoint. No approved
actor PNG, body proportions, action timing or hand/contact coordinates changed.
Directional carrying uses the appropriate side/front grip; rear travel draws the
piece behind the body so opaque torso pixels properly obscure it. No prop remains
floating after placement or cleanup.

Passed checks:

- Dedicated four-test source/native suite: all 32 states, exact live aliases and
  lip registration, per-identity cue conservation, focus loss, pause, interrupted
  cleanup, owner release and existing Continue/New Game reset staging.
- Existing focused cases, each in a fresh process: full build/return; forgotten
  block with room re-entry and next-cycle recovery; Daisy accident and return;
  blocked approach and shared chase ownership; quest claim while holding a piece;
  reset during a pending claim.
- `python tools/build_eldenmere_hd.py --check` and native normal/reduced-motion
  box comparison. Reduced motion preserves exactly the same box pixels.
- Exact preservation checks against baseline: adult/NPC records and paths, room
  dimensions, spawn, probe, doors, collision, destinations, ground, foreground,
  every non-box entity, and the complete routine configuration.
- Every `LiamDaisyPlay` method AST is unchanged. Its source-file proof hash was
  refreshed solely because `PlayActor` gained a background-carry drawing hook.

Toys remain the same ambient, unpersisted activity: in-session room re-entry
retains a forgotten piece, and Continue uses the established five-piece reset.
There is no new save schema, quest reward, inventory mutation or movement goal.

An initial multi-case legacy test process exited 137 without an assertion;
repeated native `Game` allocations accumulate heavily in those old fixtures.
The listed focused cases all passed when isolated in fresh processes.

## Reproduction

Run the live composer, not an older whole-room/legacy block builder:

```sh
python tools/build_eldenmere_hd.py
python tools/build_eldenmere_hd.py --check
python -m unittest tests.test_liam_block_box_art
python tools/capture_liam_block_box_audit.py
```

The capture command refreshes after images and native runtime evidence. Baseline
images retain their original commit provenance. Production box/prop construction
is consumed directly by the town composer; no separate producer is necessary.
