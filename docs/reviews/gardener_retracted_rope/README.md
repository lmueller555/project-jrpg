# Gardener — retracted-rope well handoff

Status: superseded by the [visible top-winch bucket handoff](../gardener_top_winch_bucket/README.md). Retained as a historical review record.

- [6× looping well close-up](well_drawing.gif): the complete approach, attachment, draw, retrieval and departure sequence.
- [Full watering trip](full_routine.gif): native-scale overview at actual game speed, with most of the initial 3–5-minute rest omitted.
- [6× watering montage](watering.gif): the unchanged four flower patches and two raised window troughs.
- PNG fallbacks: [rope-retracted retrieval pose](well_drawing.png), [full route](full_routine.png), and [watering](watering.png).

The near-rim guide has been removed. When no pail is attached, the rope is fully wound onto the windlass and only a three-native-pixel iron hook hangs beneath its center. The long working rope does not exist during the gardener's approach, attachment, unhooking or carrying poses.

She raises the pail behind her torso while the rope remains retracted. At the ownership transfer, the concealed pail makes the approved three-pixel vertical snap into the shaft and the working rope feeds down over the seven-frame settle motion. It remains visible while the well owns the pail through lowering, filling and raising. During retrieval, the rope winds smoothly back to the hook before the pail moves forward into her hands; the following unhook and carry poses again show only the short centered hook.

The actor-held pail remains behind her torso, with her articulated arms and hands composited over it. There is one pail throughout. Existing crank motion, water quantities, collision, yielding, scene persistence, watering targets and 3–5-minute rest timing remain unchanged.

Reproduce the result with:

```bash
python tools/build_well_drawing.py
python tools/build_playable_eldenmere.py
python tools/capture_gardener_well.py
python -m unittest discover -s tests -v
```

The close-up uses 100 ms captures and nearest-neighbor enlargement. Tests enforce the state-by-state rope visibility, three-pixel retracted hook and pail snap, body and arm occlusion, exclusive pail ownership, rim masking, unchanged roof pixels, centered suspension and complete watering trip.
