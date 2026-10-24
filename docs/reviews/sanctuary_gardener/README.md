# Sanctuary gardener — runtime review

Status: awaiting user review.

- [Complete collection and watering trip](route.gif): native-scale overview of the real runtime, showing the stairs, workshop lane, brook and four flower stops. Kept compact for direct GitHub image delivery; the action previews below are enlarged.
- [Collecting water](filling.gif): 6× close-up of lowering, dipping, filling and lifting the bucket.
- [Watering all four patches](watering.gif): 6× montage of the consecutive inspection and pouring stops.
- Still images: [route](route.png), [filling](filling.png), [watering](watering.png).

Travel and actions use actual game timing. The route excerpt begins 7.5 seconds into the first rest to shorten its opening; the gardener otherwise takes about 67 seconds for an unobstructed cycle. Captions and the wider stitched overview are review presentation. The four-patch close-up cuts between workstations; the game walks between them. Scenery continues using its independent ambient clocks, so those longer cycles can restart at the excerpt's loop boundary.

Run `python main.py` and visit the sanctuary courtyard to meet her. She is the auburn-haired woman in a sage dress. The role has one persistent identity; entering interiors preserves her position, bucket water and task progress. The brook collection point works independently of the mill-supply quest.

`python tools/capture_gardener.py` reproduces the previews using the actual renderer and simulation. The GIF encoder verifies exact colors and decoded timing against the captured frames. `capture.json` records state transitions and water accounting. Run `python -m unittest discover -s tests -v` for full-cycle completion, dry-foot routes, stair use, door-arrival clearance, collision/yield/detours, filled/empty states, downward pours, room persistence, planted feet, depth sorting and stable behavior at different frame rates, plus existing game checks.
