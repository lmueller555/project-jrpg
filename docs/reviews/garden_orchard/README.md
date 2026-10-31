# Garden and orchard gameplay review

The new work poses and props are **implementation review**, with no user art
approval claimed. Approved source appearances and walks remain unchanged.
The [art manifest](../../../assets/characters/garden_workers/art.json) records
native registration, generated prop crops, and layered pose sources.

These clips use production `Game.update` and `Game.draw`, a 480×320 world canvas
at the normal 960×640 display size, 30 simulation updates and 15 encoded frames
per second. Playback is real time. No painted scene overlays or alternative
renderer are used. Corresponding `*_native.png` frames preserve the unscaled
world canvas; their display counterparts include the real interface.

- [Garden work and care](garden_work_and_care.mp4): visible rainwater collection,
  carrying, two selected beds, weeding, a finite two-turnip harvest, the optional
  exchange with Caelan, and moving the struggling plant into hedge shade.
- [Orchard harvest and rest](orchard_harvest_and_rest.mp4): three accessible
  fruit picked along existing aisles, inspection, usable/bruised basket sorting,
  the best apple held for a moment, and the existing resting nook.
- [Blocked route and Continue](blocked_and_continue.mp4): the gardener waits
  when Caelan occupies the lane, resumes when he steps aside, then continues
  through real save/title restoration while carrying water and again while
  carrying the plant after the conversation has been read.

The fixture uses temporary saves and seeds completed predecessor quests with
`seed_previous_quests`, as the farm and bridge review tools do. Caelan and the
camera begin near the selected existing site. It does not claim to capture a
full journey from town or the seeded quests. Worker steps, object locations,
completed work, and dialogue flags are not manually advanced. E and dialogue
page advances are scripted. The blocked-path fixture explicitly places Caelan
in the lane and then uses ordinary movement to clear it. A marked reposition
places Caelan beside the shaded plant solely to show the short repeat line.
The current-errand panel is seeded journey UI, not a garden/orchard objective.

| Fixture | Caelan's regional feet | Camera focus |
| --- | --- | --- |
| Garden watcher | `(-526, 1214)` | `(-530, 1164)` |
| Orchard watcher | `(-115, -238)` | `(-167, -278)` |
| Blocked watering lane | `(-526, 1172)` | garden focus |
| Post-scene repeat | `(-526, 1160)` | garden focus |

Both Continue checks retain the same saved worker feet, action, action time,
and prop ownership; their paired PNGs can be compared directly. The water-carry
pair is byte-identical. The plant-carry pair differs only in the worker's stride
frame (the cosmetic walk clock restarts), while feet and held-pot location are
unchanged.

Audio comes from the shared regional allocator's accepted start/gain/stop event
stream and the identical production synthesis PCM. Since the headless device
cannot be recorded, the capture uses API-compatible channel leases and renders
that accepted stream offline at 48 kHz; it adds no music, unrelated effects,
normalization, or compression before AAC encoding. Event timestamps, gains,
peak levels, snapshots, and final save state are retained in each clip's
`*_report.json`. This demonstrates the emitted mix; subjective listening is
not represented as completed in this environment.

Reproduce with `python tools/capture_garden_orchard.py` in the project's Pygame,
Pillow, NumPy and FFmpeg environment. [Capture summary](capture_report.json)
records clip duration and technical audio levels. The final videos are 79.47s
(garden), 75.60s (orchard), and 75.23s (interruption), with peaks below −21 dBFS.
Each detailed report includes SHA256s of the controller, shared audio code, and
art manifest used for capture. Actual frames were inspected for watering and
branch reach, visible deposited produce, the shaded plant, bench alignment,
blocked-lane clearance, and reconstruction after Continue. The script asserts safe
watcher placement, stationary blocked feet, real Continue success, exact saved
controller restoration, and the scene's read flag surviving its carried payoff.
