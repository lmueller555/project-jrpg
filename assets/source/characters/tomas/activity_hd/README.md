# Tomas: dormant native activity bank

This package does not alter a live actor, schedule, story, prop owner, cue, or
cinematic. Activate only together with the canonical named Tomas base bank.

## Reproduction and identity

Run `python tools/export_tomas_activity_hd.py` (Pillow required); `--check`
verifies byte-exact output. `drawings.json` is the editable literal native
whole-pose source: complete costume/limb contours, native face registration,
and fixed prop placements. It is not an articulated joint/rotation rig.
`props.json` supplies native matching bundle, mechanism and sack contours.

Canonical input: `assets/characters/named_hd/tomas/idle_DIRECTION.png`, native
48x72, logical24x36. The frozen face and stationary boots come directly from
that approved-density bank, never enlarged legacy art. Complete walking lower
body drawings use its corresponding four authored gait phases; activity hands,
sleeves, seated legs and contact poses are separately drawn native contours.
Palette, blond head, clay tunic/cream sleeves, belt, brown boots and anatomical
left-knee patch remain Tomas's. The patch is visible in front/near-left leg
views, absent on back/right views, and naturally occluded behind a held sack.
Full-pose source contains every output coordinate; no source outside the repo
is needed. Provenance records hashes of the canonical input idles.

## Coverage and activation contract

- `routines`: 58 action +16 carry frames, native128x96, logical64x48,
  logical body offset20,6 and draw anchor32,36. Action records, phases, exact
  durations, prop_owner and carry cadence are unchanged. Matching native
  held/world bundle, stack and model props are included. Existing world HD
  storage box remains environmental dressing and is not replaced here.
- `breakfast`: 23 frames: seated, glance, four each of plate-push, eat, sit,
  stand, plus independently drawn right-facing seated/four eat frames for the
  Regent meal (no asymmetric costume flip). Native48x72 logical24x36 draw12,30. Existing eat/sit/stand manifests
  retain exact duration, wrist, display-position and registration fields.
  Plate push remains four180ms steps under Opening's original plate ownership.
  No plate, fork, cup, chair, table or control cue is duplicated in these bodies.
- `sack`: 36 body frames: hold, four carry, four lift in four directions.
  Native64x80 logical32x40 carry anchor16,34. Native sack32x36 has the original
  logical16x18 footprint and is composed behind the north-facing torso.
  Original720ms lift, contact frame2 and four140ms carry phase contracts remain.
- Cinematic audit retains the original four approved regent-arrival frames and
  their 80x96 projection in place. No pixel-count-only density relabeling, scale
  change or incidental costume edit. `cinematic_audit.json` lists their hashes.

## Consumers / ownership

RoutineNPC owns work/bundle transport, with room `surface_visibility` and
`prop_owner` controlling single-owner bundle custody. Opening owns seated,
plate-push, breakfast, stand/sit bodies; RegentActions also borrows tomas_eat.
Halden visit owns sack holds/carries/lifts and contact index. Lantern borrows
Tomas's existing actor/base bank and does not need a distinct new Tomas atlas.
RegentArrival owns the separately projected cinematic bank, retained here.

Normal and half-speed GIFs and contact sheets accompany the dormant output.
No raster limb scaling, runtime mirroring, baked actor-shadow layers, or new
schedule/state changes are introduced. Runtime staged sequence tests remain
required at activation; this source-only PR does not claim live integration.
