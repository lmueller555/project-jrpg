# Sanctuary gardener — bucket routine

Status: **awaiting user review**. Uses the approved auburn-haired, green-eyed female_02 appearance and sage dress. The approved idles, walks, templates and town art are unchanged.

She rests beside the sanctuary's southwest flowers, picks up her empty wooden bucket, descends the stairs, follows the lane south of Mira's doorway and collects from the main brook's west bank north of the upper bridge. She returns up the stairs and waters west white, southwest violet, southeast white and east yellow flowers, in that order. Each patch gets two short pours. She sets down the empty bucket and rests again. One unobstructed cycle takes approximately 67 seconds; subsequent pauses vary between 8, 10 and 12 seconds.

The bucket gains four visible water levels only while dipped. It loses one unit after each patch. The gardener travels at 60 native pixels/second with an empty bucket and 50 with a loaded one; stride advances by distance, keeping the same step length. She supports the full bucket with both arms, pauses if blocked, and attempts a safe detour after a sustained obstruction. She waits if a destination remains occupied. Feet stay on dry ground at the brook; water effects originate at the bucket and end at the flower roots.

`animations.json` contains four-direction empty/full carrying cycles, carrying idles, pickup/setdown, filling and two-direction pouring sequences. Body poses reuse the approved head, neckline, dress/skirt and leg parts, with dedicated occupied arms. Character scale remains **24×36**. Runtime pose canvases are 48×48 with body registration `[12,6]`, draw anchor `[24,36]` and art foot anchor `[24,40]`, allowing the bucket and water to extend beyond the body without clipping. No character is enlarged in-game.

- Named body PNGs: character and articulated arms, with transparent action padding.
- `bucket_<angle>_<level>.png`: native wooden pail, handle, iron bands and visible water.
- `poses_review.png`: enlarged contact sheet.
- [Runtime route, filling and watering previews](../../../../../docs/reviews/sanctuary_gardener/README.md).
- Behavior and collision-safe task registrations: `assets/maps/eldenmere/routines/gardener.json`.

Rebuild with `python tools/build_gardener.py`; capture with `python tools/capture_gardener.py`, using the Pillow/Pygame asset environment. The playable game itself needs only Pygame and these checked-in files. The routine updates while offscreen or indoors; no additional gardener is spawned when scenes change. There is no dialogue, quest completion or permanent flower-growth effect in this milestone.
