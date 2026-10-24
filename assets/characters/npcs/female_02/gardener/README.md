# Sanctuary gardener — bucket routine

Status: **routine and body motion approved by the user**. The shared left/right profile-jaw cleanup is awaiting review. The gardener's auburn hair, green eyes and sage dress retain their approved design; her rebuilt carrying and work poses use the corrected female_02 heads.

She rests beside the sanctuary's southwest flowers, picks up her empty wooden bucket, descends the stairs, follows the lane south of Mira's doorway and collects from the main brook's west bank north of the upper bridge. She returns up the stairs and waters west white, southwest violet, southeast white and east yellow flowers, followed by both window troughs. For the troughs she stands between them, turning left and right and lifting the bucket above their soil level. Each target gets two small pours. She sets down the empty bucket and rests again. An unobstructed working trip takes approximately 68 seconds, followed by a **random 3–5-minute rest**.

The same bucket holds six measured portions, with six visible water levels gained only while dipped. It loses one unit after each flower patch or trough. The gardener travels at 60 native pixels/second with an empty bucket and 50 with a loaded one; stride advances by distance, keeping the same step length. She supports the full bucket with both arms, pauses if blocked, and attempts a safe detour after a sustained obstruction. She waits if a destination remains occupied. Feet stay on dry ground at the brook; water effects originate at the bucket and end at the roots or trough soil.

Each rest duration is sampled once, uniformly between 180,000 and 300,000 milliseconds inclusive, including the initial rest when the game starts. Drawing, blocked paths and scene changes do not resample it. The countdown continues while indoors. Review captures omit most of this long wait.

`animations.json` contains four-direction empty/full carrying cycles, carrying idles, pickup/setdown, filling, ground-level pouring and higher trough-pouring sequences. Body poses reuse the approved head, neckline, dress/skirt and leg parts, with dedicated occupied arms. Character scale remains **24×36**. Runtime pose canvases are 48×48 with body registration `[12,6]`, draw anchor `[24,36]` and art foot anchor `[24,40]`, allowing the bucket and water to extend beyond the body without clipping. No character is enlarged in-game.

- Named body PNGs: character and articulated arms, with transparent action padding.
- `bucket_<angle>_<level>.png`: native wooden pail, handle, iron bands and visible water.
- `poses_review.png`: enlarged contact sheet.
- [Runtime route, filling and watering previews](../../../../../docs/reviews/sanctuary_gardener/README.md).
- Behavior and collision-safe task registrations: `assets/maps/eldenmere/routines/gardener.json`.

Rebuild with `python tools/build_gardener.py`; capture with `python tools/capture_gardener.py`, using the Pillow/Pygame asset environment. The playable game itself needs only Pygame and these checked-in files. The routine updates while offscreen or indoors; no additional gardener is spawned when scenes change. There is no dialogue, quest completion or permanent flower-growth effect in this milestone.
