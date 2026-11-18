# Live Eldenmere well integration

The replacement well now runs in ordinary Eldenmere gameplay. The production
`World` compositor draws its native layers, and the gardener approaches and
operates it through the actual collision-aware routine. The independent
`WellMechanism` owns the operating clock, water contact and attachment cues;
rendering does not advance it.

The current `adult_woman_02` gardener appearance and recently integrated work
drawings remain selected. The sixteen mechanism samples use the registered
nearest existing operating key, rather than reverting her appearance to the
older `female_02` staged work pack. The canonical replacement pail is shared by
the well and every actor-held state. This integration does not claim sixteen
newly drawn operating body poses or a new walking gait.

[Implementation scope and lifecycle](implementation.md) records the source
activation, ownership, interruption and restoration decisions. The earlier
[mechanism](../eldenmere_well_mechanism/README.md) and
[staged performance](../gardener_well_hd/README.md) retain their historical source
and offline review evidence.

## Actual-game evidence

Run from the repository root with normal Pillow/Pygame dependencies installed:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_well_live.py
```

The helper constructs a normal `Game` with disposable save/settings paths and
advances it through `Game.update`. It seeds the initial rest duration and skips
most of that long rest. It does not step the mechanism separately, teleport the
gardener, or signal readiness. The player remains out of the route during the
normal simulation. All source collision checks use the real live foot probe.

- [Well operation](well_operation.gif) and its
  [half-speed companion](well_operation_slow.gif) are native crops from the
  actual 960×640 production compositor, sampled every 100 ms. Half-speed review
  changes saved playback delay only.
- [Complete watering trip](complete_trip.gif) follows the same uninterrupted
  simulation through native crops sampled every 500 ms; the long rest is
  omitted. It is a route overview, not a full-frame-rate gait review.
- [Watering](watering.gif) retains all watering actions, including both sides
  and both raised troughs. Travel between stops is omitted from this excerpt.
- [Pickup/setdown](pickup_setdown.gif) retains those two actions from the same
  complete trip; their intervening route is shown separately.
- [Ownership cues](handoff_cues.png) bracket both transfers in the actual trace.
  [Operating contacts](operating_contacts.png) show all sixteen mechanism
  indices in each direction, sampled with the corresponding live body drawing.
- The `phase_*.png` files retain native full-viewport RGB for source colors and
  scale. `depth_north.png`, `depth_south.png` and `reduced_motion_fill.png`
  show production depth and the reduced-motion setting at a held model state.
  Only the two depth stills reposition the disposable player diagnostically.
- [Observations](observations.json) record the sampled model/actor state,
  watering and mechanism cues, source hashes, artifact hashes and exact saved
  GIF durations. The GIFs use a shared 256-color palette; PNGs retain exact RGB.

The helper never writes a normal user save. Static screenshots and captures
supplement the focused state, collision and lifecycle tests; they do not replace
those checks or certify unrelated NPC routines and story scenes.

## Validation

All 211 focused cases were verified across the live well, gardener/current HD
identity, source packs, commons/framework, saves, social and roster suites. The
broad run passed 210 cases; its remaining depth fixture sampled transparent
padding from the former high roof. Correcting that sample to the new authored
canopy passed on rerun, alongside the strengthened complete-trip cue test.
The production code did not change during that correction.

Checks cover blocked loading/operator/retrieval stations, once-only ownership
and water cues, all six targets, pause/menu/focus loss, indoor continuity,
New Game/Continue checkpoints, stale tokens, native depth, reduced motion and
launching with Pillow imports blocked. Independent 30/60/144 Hz traces match;
two consecutive complete trips at 15 Hz each finish in 83.333 seconds with six
ordered pours and one empty pail at rest.

All three read-only exporters verify their 28/49/161 products. The town rebuild
verified all 997 products; its only four generated changes are the playable map,
overview and two integration manifests. Collision/navigation, doors, destinations,
player probes and all 80 other town entities remain unchanged. Retained well,
pail, earlier staged character and current roster artwork is byte-identical.
The final review verifies eight runtime-source hashes and 29 image/GIF hashes.

The current eight body keys serve sixteen mechanism samples. Registered hand
gaps reach at most 2.7 logical units; the loading handoff uses a small two-unit
snap. The native contact/cue boards retain that limitation explicitly rather
than implying newly drawn sixteen-frame work cycles or exact finger contact.

The final capture contains **852 actual Game samples** over **85.1 seconds**.
Its `active_review_duration_ms` field is **84,300 ms from review start to the
first completed cycle**; that interval still includes the last sampled portion
of the initial rest. A further 800 ms holds the completed arrangement. The route
GIF lasts 85.5 seconds because its final sample retains a full 500 ms delay.
Separate focused validation completed two consecutive trips at 15 Hz, each
approximately **83.333 seconds of active routine time**, with operation IDs
1 then 2, all six targets once, zero remaining water, one resting pail and no
remaining well reservation. Those two-cycle results are independent test
evidence; the retained visual trace above is the single captured trip.

## Draw and cache measurements

The retained [baseline](performance_baseline.json) and
[integrated](performance_integrated.json) records use the same seeded,
temporary-save fixture, native 960×640 target and logical camera `[288,660]`.
Each case measures thirty production `World.draw` calls, including native-buffer
reset. Updates, PNG conversion, interface drawing and display presentation are
outside the timer. These are hardware-specific samples.

| Actual lowering scene | Baseline `7dfa732e` | Integrated native well |
| --- | ---: | ---: |
| Warm static median | 1.69 ms | 1.77 ms |
| Moving draw median | 1.71 ms | 1.85 ms |
| Moving draw 95th percentile | 1.83 ms | 3.53 ms |
| First lowering-scene draw | 2.85 ms | 4.09 ms |

The moving case performs an actual 1/60-second `Game.update` between draws,
exercising changing crank/pail poses and cold pose-cache entries. The first
full scene draw, which also warms scenery chunks, took 45.00/43.07 ms for the
baseline/integrated fixture. Median differences this small are within normal
run variation; this is a scoped draw-cost measurement, not a whole-game frame
rate claim.

The [isolated well profile](performance_components.json) establishes a **20 MiB
well-rendering retention budget**: its full 48-pair native/logical LRU uses
12,165,120 bytes, and retained components/masks bring the total to **18,601,600
bytes (17.74 MiB)**. Warm poses reopen no source image. This bound covers the
well renderer, independently of existing world and character-bank caches.
Its isolated moving median is 0.296 ms and 95th percentile is 1.115 ms across
371 actual mechanism snapshots. That isolated fixture signals readiness
synthetically; the full trip capture above validates actual actor navigation.

Reproduce either checkout's full-scene measurement with the retained driver:

```sh
python docs/reviews/well_live/profile_scene.py /path/to/checkout /tmp/well-profile.json
```

The driver imports `Game` from the explicitly supplied checkout and records
its source hashes, revision and its own hash. The integrated runtime uses
Pygame/NumPy; Pillow is required for review/export tooling only.
