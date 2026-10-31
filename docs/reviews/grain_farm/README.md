# Western grain farm review

These clips come from the production `Game.update` and `Game.draw` at the normal
480×320 world resolution displayed at 960×640. Capture runs 30 updates/second and
records 15 frames/second with original timing. No scene artwork, actors, dialogue,
or explanatory overlays are painted over the game output. Sound is muted.

- [Before repair — 20 seconds](before_repair.mp4): waiting grain, covering,
  coworker route and the loader's first greeting. Nothing loads before repair.
- [Loading and full vignette — 51 seconds](loading_and_vignette.mp4): two finite
  loading trips, explicit conversation, every line of the exchange, shared
  placement of the spare sack, and the loader's unprompted lashing check.
- [Blocked path and Continue — 31 seconds](blocked_path_and_continue.mp4): the
  loader waits with a single sack while Caelan blocks the lane, resumes once
  Caelan walks aside, then Continue reconstructs a mid-carry save with the first
  sack retained on the cart and the unplaced second sack at storage.

The capture harness seeds existing quest facts for the post-repair fixture and
places Caelan at the start of each scenario. The obstruction is a deliberately
placed test fixture; clearing it uses normal player movement. Dialogue advances
through the production social controller. Continue uses the real journey save
and `Game.begin_journey(True)`. The harness does not assign routine stages or
advance loading/scene completion itself. The quest tracker visible in the
post-repair fixture is existing UI, not a new farm quest.

[Capture timings and cache measurements](capture_report.json) accompany the
clips. Key stills show the [shared grip](shared_grip.png), [loaded cart](loaded_cart.png),
[blocked loader](yielding.png), and [reconstructed save](after_continue.png).

Visual review checked worker/player scale, grounded walk phases, hand/sack
contacts, foreground placement of the loaded sacks on the cart, the separate
coworker route, and the six-line exchange at normal zoom. Review fixes include
holding the carry pose when blocked and retaining the grip during the axle glance.
The generated work-pose reference and deterministic appearance-part exports are
recorded in `assets/source/characters/grain_workers/README.md`.

The eight integration tests in `tests/test_grain_farm.py` exercise the physical
repair flag, finite stock, blocked recovery, optional/cancelled dialogue, paused
map and journal, interrupted carry Continue, read-scene Continue, invalid save
records and chunk eviction/region departure. Existing overworld tests cover
checkpoint/bridge independence and virtual companion ownership.

Intentional boundaries: the cart never leaves; the original decorative sack
pile represents reserve grain; only the three handled sacks belong to this
finite batch. An uncommitted lift restarts at storage after Continue, while a
normal leave/return retains live positions. No remote farming schedule runs
outside the local 260-pixel activity radius. New work art is marked for review;
approval labels on existing villagers and scenery remain unchanged.

```sh
python tools/build_grain_workers.py
python -m unittest discover -s tests -p 'test_grain_farm.py' -v
python -m unittest discover -s tests -p 'test_overworld_*.py' -v
python -m unittest discover -s tests -v
python tools/capture_grain_farm.py
```
