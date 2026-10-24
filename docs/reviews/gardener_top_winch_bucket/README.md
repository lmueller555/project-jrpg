# Gardener — visible top-winch bucket handoff

Status: awaiting user review. Implemented in the playable town launched by `main.py`.

- [6× looping well close-up](well_drawing.gif): attachment, visible parking, lowering, filling, raising, retrieval and departure.
- [Parked bucket still](parked_bucket.png): the full pail visible directly beneath the windlass before retrieval.
- [Full watering trip](full_routine.gif): native-scale overview at actual game speed, with most of the initial 3–5-minute rest omitted.
- [6× watering montage](watering.gif): the unchanged four flower patches and two raised window troughs.
- Additional PNG fallbacks: [concealed retrieval pose](well_drawing.png), [full route](full_routine.png), and [watering](watering.png).

The empty well shows only a three-native-pixel hook beneath the windlass. The gardener turns away and raises her pail behind her torso. At the final fastening pose, the concealed pail deliberately snaps to local grip `[40,51]`, directly beneath the spindle, where its complete silhouette is visible in the dark opening. It settles down one pixel and returns before she walks to the crank.

The pail and rope then move as one registration from the parked top position to the water. The bucket begins fully visible, is progressively masked by the front stone rim as it descends, remains hidden while filling, and reappears in reverse while rising. It stays visibly parked beneath the winch while she returns to the near side. At the retrieval contact frame, it snaps from that position behind her torso, leaving the short bare hook; it then emerges naturally into her side carrying pose.

There is one pail throughout. Existing crank motion, water quantities, collision, yielding, room-transition persistence, six watering targets and 3–5-minute rest timing remain unchanged.

Reproduce the result with:

```bash
python tools/build_well_drawing.py
python tools/build_playable_eldenmere.py
python tools/capture_gardener_well.py
python -m unittest discover -s tests -v
```

The close-up uses 100 ms captures and nearest-neighbor enlargement. Tests enforce the exact top-winch registration, one-pixel settle, synchronized rope and pail movement, progressive rim masking, both deliberate snaps, body and arm occlusion, exclusive pail ownership, unchanged roof pixels and the complete watering trip.
