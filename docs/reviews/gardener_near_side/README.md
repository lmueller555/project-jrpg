# Gardener — centered near-side well routine

Status: superseded by the [short-guide, body-occluded handoff](../gardener_short_guide/README.md). Retained as a historical review record.

- [6× looping well close-up](well_drawing.gif): approach from the near side, lift and hook her pail, release it behind the rim, operate the crank, then catch, unhook and carry it away.
- [Full watering trip](full_routine.gif): native-scale overview at actual game speed, with most of the initial 3–5-minute rest omitted.
- [6× watering montage](watering.gif): the unchanged four flower patches and two raised window troughs.
- PNG fallbacks: [well handoff](well_drawing.png), [full route](full_routine.png), and [watering](watering.png).

The loading guide, rope and pail share local x=40, world x=526: the true horizontal center of the well shaft. The gardener stands at `[526,892]`, immediately south of the existing solid footprint, and faces away from the camera. Her roof never needs a cutaway.

Her upper arms and forearms remain at most seven native pixels per segment. The pail follows her registered hand grip while she raises or lowers it. On release it changes from the near loading grip to the shaft grip by one six-pixel vertical depth snap, with no horizontal movement; the foreground rim masks the transition. Retrieval reverses those same registrations after both hands reach the handle. While attached, the pail stays at x=40 and moves only vertically.

There is one pail. Ownership changes from actor to well after the hook-and-release pose and returns to the actor after the catch-and-unhook pose. The idle well retains a bare centered hook and a small iron loading guide on the near capstone. The existing roof, posts, stone footprint and town elevation remain unchanged.

The approved crank motion, progressively filling water, slower loaded walk, all six watering targets, collision/yield behavior, room-transition persistence and random rest timing remain. `capture.json` records the runtime states, positions, water quantities and preview timings.

Reproduce the result with:

```bash
python tools/build_well_drawing.py
python tools/build_playable_eldenmere.py
python tools/capture_gardener_well.py
python -m unittest discover -s tests -v
```

The close-up uses 100 ms captures and nearest-neighbor enlargement. The route uses 200 ms captures. Tests cover arm lengths, exact centered registrations, six-pixel depth snaps, exclusive pail ownership, rim masking, unchanged roof pixels, vertical-only suspension, crank-hand alignment, occupied stations, scene persistence, water accounting and the complete watering trip.
