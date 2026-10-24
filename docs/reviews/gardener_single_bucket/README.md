# Gardener — attach, fill and reclaim her own pail

Status: awaiting user review. Implemented in `main.py`; supersedes the two-bucket transfer.

Superseded by the [centered near-side revision](../gardener_near_side/README.md). The user rejected this version because the side pose stretched her arms and placed the rope too far toward the well’s edge. These files remain the historical comparison; the live game and capture command now use the near-side routine.

- [6× looping well close-up](well_drawing.gif): arrive with her pail, raise it in both hands, fasten its handle to the hook, lower/fill/raise it, return to grasp the handle, unhook it and lower it into her carrying pose. Includes arrival and departure so the empty hook is visible between visits.
- [Full routine](full_routine.gif): native-scale route overview, at real game speed. Most of the initial random rest is omitted.
- [6× watering montage](watering.gif): all four flower patches and both raised window troughs, with cuts between stops.
- Still images: [unhooking](well_drawing.png), [full route](full_routine.png), [watering](watering.png).

There is exactly one pail, belonging to the gardener. The idle well has a short rope and metal hook near the right end of its windlass, within her reach from the east side. She never sets a second pail on the ground and there is no transfer stream or sideways movement of a suspended bucket.

Her hand and pail grips use the same registered coordinates throughout attachment and retrieval. At attachment the renderer changes ownership from hands to rope at identical coordinates; on removal it changes back only after her hands reach the handle. The hook opens while she supports the full pail. Only then does she bring it down into her approved carrying pose. The suspended pail travels in one vertical column; the front lip hides it below the rim. Crank rotation reverses and slows for the loaded ascent. Her pail fills while submerged, and returns full before she unhooks it.

The hook-side poses draw her hands in front of the well so the grasp is visible. Roof, stone, posts, solid footprint and town layout retain their dimensions. The terrain exports, runtime entity frames and in-game map overview all use the bucketless idle. The original concept source remains preserved.

The six watering stops, slower loaded travel, collision/yield behavior, persistent scene progress and random 3–5 minute rest remain. The well accepts one operator at a time. Preview timings and sampled rests are recorded in `capture.json`.

Reproduce:

```bash
python tools/build_well_drawing.py
python tools/build_playable_eldenmere.py
python tools/capture_gardener_well.py
python -m unittest discover -s tests -v
```

Close-ups use integer nearest-neighbor enlargement and 100 ms capture intervals; the overview uses 200 ms intervals. Travel and actions run at actual game speed. A seeded random generator makes previews repeatable; live games use independent entropy. GIF exports verify decoded colors and timing against the runtime captures. Tests cover exact handoffs, hand/crank registration, vertical-only suspension, water quantities, rim occlusion, occupied workstations, scene persistence, the six-target trip and the existing gameplay checks.
