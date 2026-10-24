# Sanctuary gardener — runtime review

Status: approved by the user. The previews preserve the approved artwork and timing.

Historical record: the current game uses the [centered near-side well routine](../gardener_near_side/README.md), awaiting review. These brook previews remain unchanged. `python tools/capture_gardener.py` now captures the current well routine into its separate review folder.

- [Complete collection and watering trip](route.gif): native-scale overview of the real runtime, showing the stairs, workshop lane, brook, four flower patches and both window troughs. Kept compact for direct GitHub image delivery; the action previews below are enlarged.
- [Collecting water](filling.gif): 6× close-up of lowering, dipping, filling and lifting the bucket.
- [Watering all six targets](watering.gif): 6× montage of the consecutive inspection and pouring stops.
- [Watering the window troughs](troughs.gif): 6× close-up of lifting the bucket and pouring downward into both troughs.
- Still images: [route](route.png), [filling](filling.png), [watering](watering.png), [troughs](troughs.png).

Travel and actions use actual game timing. **The random 3–5-minute rests are mostly omitted from the previews**: the route excerpt starts two seconds before the initial rest ends and finishes just after the next begins. The selected countdown is shown in the caption. Working trips take approximately 68 seconds. Captions and the wider stitched overview are review presentation. Close-ups cut between workstations; the game walks between them. Scenery continues using its independent ambient clocks, so those longer cycles can restart at the excerpt's loop boundary.

Run `python main.py` and visit the sanctuary courtyard to meet her. She is the auburn-haired woman in a sage dress. The role has one persistent identity; entering interiors preserves her position, bucket water and task progress. The brook collection point works independently of the mill-supply quest.

These previews were captured with the actual renderer and simulation, with a seeded random generator only for repeatable captures. Live games use an independent entropy-seeded generator. The GIF encoder verifies exact colors and decoded timing against the captured frames. `capture.json` records the historical state transitions, six-target water accounting and sampled rest durations.
