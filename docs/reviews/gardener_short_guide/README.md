# Gardener — short-guide near-side handoff

Status: superseded by the [retracted-rope handoff](../gardener_retracted_rope/README.md). Retained as a historical review record.

- [6× looping well close-up](well_drawing.gif): the complete approach, attachment, draw, retrieval and departure sequence.
- [Full watering trip](full_routine.gif): native-scale overview at actual game speed, with most of the initial 3–5-minute rest omitted.
- [6× watering montage](watering.gif): the unchanged four flower patches and two raised window troughs.
- PNG fallbacks: [covered retrieval pose](well_drawing.png), [full route](full_routine.png), and [watering](watering.png).

The iron loading guide remains centered on the near capstone. Its hook now ends exactly three native pixels below the guide, and the former exposed rope tail down the front of the well has been removed. The pail makes one three-pixel vertical depth snap between the gardener's hands and the shaft centerline, with no horizontal movement.

During attachment and retrieval, the actor-held pail is drawn behind the gardener's body. Her torso fully obscures every overlapping pail pixel while her articulated arms and hands remain on top. The pail becomes visible naturally as she turns and lowers it into the side carrying pose. While the well owns the pail, the near rim masks it and the roof remains unchanged.

There is still one pail. The gardener brings it from the sanctuary, attaches it at the near side, operates the east crank, retrieves it from the same position, waters all six approved targets and rests for a random 3–5 minutes. Collision, yielding, scene persistence, water quantities and timing are unchanged.

Reproduce the result with:

```bash
python tools/build_well_drawing.py
python tools/build_playable_eldenmere.py
python tools/capture_gardener_well.py
python -m unittest discover -s tests -v
```

The close-up uses 100 ms captures and nearest-neighbor enlargement. Tests enforce the three-pixel hook limit and snap, pail-behind-torso-and-arms compositing, one-pail ownership, rim masking, unchanged roof pixels, centered vertical suspension, crank-hand alignment, occupied stations, scene persistence and the complete watering trip.
