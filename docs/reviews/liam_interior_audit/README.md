# Liam home: Daisy bowl registration and fill-state audit

Native game-room review, based on main `5630648b`. Fireplace and Liam block fixes
are separate changes in the combined interior audit.

## Findings and correction

The live HD bowls were not using the original wooden bowl bank: half-full was
painted as a dark vertical half, and Daisy overlaid the old wooden front rim on
the new ceramic body. Re-setting an initially full bowl also selected a separate
state filename, making the missing unified state/overlay contract easy to miss.

The scoped HD export now retains the existing ceramic body, decoration, outline,
footprint, depth and position. A single registered recess owns full, lower
half-full and empty contents. Food is readable kibble; water has a lowered
horizontal surface. Each bowl has its own exact front-lip overlay from that same
body. Water ripples clip per native render texel to the current level and disappear
in reduced-motion mode. The canonical full image is used from initial load onward.
Daisy's anatomy, pose timings, station, movement and consumption cues are unchanged.

## Native scene evidence

- [Before, actual eating scene](before_eating.png) and [after](after_eat_0.png).
- [Contact comparison montage](contact_review.png): baseline, corrected full/half
  food, full/half water, and both empty states (top to bottom).
- [Full room after](after_room.png).
- [Food: two complete visits, full → half-full → empty](food_depletion.gif).
- [Water: two complete visits, full → half-full → empty](water_depletion.gif).
- [After food half-full](after_food_half_full.png), [empty](after_food_empty.png).
- [After water half-full](after_water_half_full.png), [empty](after_water_empty.png).

The GIFs are native-density crops of actual `World.draw` frames, not isolated
asset composites. Review selects the next ordinary visit directly and skips the
long rug waits. All approach, feeding, consumption, raise and return timing uses
Daisy's production state machine at real speed. Replay resets the review only.

Historical behavior is preserved: no family refill UI/routine is added. A visit
consumes exactly one level at completion, an empty bowl is inspected without
consumption, reservations block outside changes until she steps clear, and cached
room re-entry preserves levels within the same session. A fresh session/Continue
starts ambient bowls full as before; permanently saving depletion with no refill
would be a gameplay change. Save schema and quest progress are untouched.

## Reproduction and coverage

```
python tools/build_daisy_bowls_hd.py --check
python tools/capture_daisy_bowls_hd.py
python tools/check_eldenmere_hd.py test_daisy_bowls_hd
python tools/check_eldenmere_hd.py test_daisy_routines
python tools/check_eldenmere_hd.py test_daisy_bowls
python tools/check_eldenmere_hd.py test_liam_daisy_play
```

The new native export/scene tests cover deterministic bytes and town integration,
unchanged body/alpha/lips, actual depletion and refill API, mouth registration,
per-render-texel ripple clipping, reduced motion, repeated full state, session
boundaries and pause/focus freezing without catchup. Existing tests cover
consumption exactly once, empty inspection, station blocking, offscreen progress,
room transfers, reservations, and the post-play drink (including empty water).
Run fixture-heavy modules separately: retaining the old bowl class fixture across
modules can exhaust the review process's memory. See the adjacent JSON/log evidence.

Validation on this bowl candidate: **9/9** HD bowl tests, **11/11** Daisy routine
checks, **5/5** original bowl checks and **6/6** Liam/Daisy play checks pass when
run in separate processes. The real checkpoint/Continue smoke check restores the
saved room and preserves the historical new-session full defaults. The scoped
builder reports zero export drift; Python compilation and `git diff --check` pass.
