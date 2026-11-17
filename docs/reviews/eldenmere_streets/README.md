# Eldenmere streets and pedestrian connections — settlement PR 2

This implements the second of eight settlement-composition PRs. It follows the
metadata-only [framework](../eldenmere_settlement_framework/README.md) and uses
its 114 protected spaces. The [central terrain standard](../../TERRAIN_ART_STANDARD.md#eldenmere-settlement-framework)
remains the maintenance reference; the regional guide remains the creative brief.

## Scope and implementation

The town gains a clearer walking network through existing native material banks:

- Six compact-earth treatments reinforce the western/southern through-road,
  two-bridge loop and business lane. Existing road artwork is retained beneath
  these additions; usable route widths are not reduced.
- Ten small stone treatments mark four junction bands, four bridge approaches
  and two stair feet. They remain ground surfaces, without curbs or collision.
- Thirteen doorsteps follow the actual loaded door anchors, including fractional
  positions. Business anchors resolve from the current source recipe before
  painting, so an edited business cannot retain a previous-build doorstep.
- Two narrow desire paths acknowledge existing grass travel from school toward
  the commons and from Elira toward the lower loop.

There are **31 active ground treatments, zero prop placements and 50 compiled
cartographic records**. Courtyard furniture, workyard storage, civic dressing,
household gardens, Venn's growing plots and southern planting remain PRs 3–8.
No new service, interaction cue, quest objective, scene or save field is added.

The source recipe explicitly enables `ground_only`. The validator still rejects
prop activation, unsupported materials, unknown treatment keys, invalid logical
geometry, nonfinite coordinates and source references that no longer resolve.
Cartographic source records also guard the selected road's identity so source
reordering requires review instead of silently changing a named connection.

The sole town composer paints native terrain before masonry, stairs, water and
bridges. It retains hard alpha, authored blob boundaries and the stone bank's
four world-registered spatial phases. Collision clips new surfaces; it is not
generated from them. The compiled coverage image records every native pixel the
pass can affect. Existing bridge assemblies remain after water in every phase,
with their near rails in the independent foreground pass.

The illustrated town map consumes the same treatments and maintained route
sources. Its complete network replaces the old plan/extension/addition road
traces; it does not layer a second road diagram on top. Existing maps without
that key retain their fallback. Runtime map drawing reads compiled town data.

Visual review reduced freestanding paving squares to short junction bands and
trimmed the business-lane end. These are source-geometry refinements; no movement
or collision adjustment was used to fit them.

## Evidence and validation

The final comparison uses clean main **`d758a368`**, including the independently
merged 13-building exterior rebuild. [Before-revision evidence](before_revision.json)
records the isolated checkout. The original framework review remains historical;
these new before/after witnesses include the latest building art.

- **163 tests pass on the combined implementation:** 123 core cases covering
  settlement contracts, native painting, cartography, town integration, southern
  departure/return, regional travel, rendering, crossings and the latest exterior
  integration; plus 40 actor-handoff, Regent and Lantern checkpoint cases.
- Both reproducible checks pass: **844 town exports** and the standalone
  settlement report. A 122-test full Lantern/household/Regent run also passed
  before integrating the non-overlapping exterior rebuild; the final 40 cases
  recheck transfers and saved checkpoints on the combined source.
- Across **all six native ground phases**, 117,602 pixels change in each phase,
  with **zero changes outside** the 687,153-pixel declared coverage mask.
- Collision and navigation PNG bytes are identical to the updated main baseline.
  All non-ground active artwork is unchanged. Only 48 active inputs change:
  the town metadata and 47 native ground chunks. The overview is rebuilt too.
- Only `cartography` and the new `settlement_streets` metadata change in the map;
  the existing chunk paths remain the same. All 13 doors, entrances, buildings,
  foregrounds, NPC records, destinations and scene/travel interfaces are preserved.
- **16 production walking/running checks** traverse the southern spine, both
  bridges and both desire paths in both directions: 4,080 update frames, zero
  stalls/replans, valid final ground and unchanged quest/party/inventory/flags.
  These runs retain ambient actors; only route starting positions are fixtures.

[Observations and movement traces](observations.json) contain source hashes,
per-phase differences and the full input traces. [Before observations](before_observations.json)
and [before town metadata](before_town.json) retain the original witnesses.
The screenshots use the production Game with disposable saves/settings. They are
initialized review fixtures, not a continuous quest playthrough. Existing quest
regressions separately exercise progression and restoration.

| Area | Native production evidence |
| --- | --- |
| Arrival and business connection | [Southern street](southern_arrival.png) |
| Household terrace and stairs | [Serene's terrace](serene_terrace.png) |
| Workshop and mill approaches | [Workshop](workshop_yard.png), [mill](mill_yard.png) |
| Civic and school connections | [Commons](commons.png), [school](school_frontage.png) |
| Eastern connections | [Eastern terrace](eastern_growing_area.png) |
| Full network | [Production town map](town_map.png) |

Before views use the matching `before_` filenames. The crossing samples and route
endpoint frames are linked by each movement record in the observations. Native
review confirms source detail, ground support, bridge foreground depth, readable
junction bands and compatible normal/reduced-motion presentation.

## Reproduce

Use the repository's Pygame, Pillow and NumPy dependencies with dummy SDL drivers
for headless verification. Disposable saves/settings isolate the captures.

```sh
python tools/build_eldenmere_hd.py --check
python tools/build_eldenmere_settlement_framework.py --check
python -m unittest discover -s tests -p 'test_eldenmere_settlement_streets.py' -v
python -m unittest discover -s tests -p 'test_eldenmere_settlement_framework.py' -v
python -m unittest discover -s tests -p 'test_map_ui_streets.py' -v
python tools/capture_eldenmere_streets.py /tmp/eldenmere-street-review
```

The capture command without a baseline checks the current production fixtures,
map and walking/running routes. `--baseline /path/to/pre-pass-folder` additionally
verifies intentional differences. That folder contains the original framework
`observations.json`, `town.json`, logical `collision.png`/`navigation_allowed.png`,
and all six full native `ground_phase_0.png` through `ground_phase_5.png` assembled
from the base revision's live chunks. Use a detached checkout of the recorded
base revision when reconstructing those original inputs. The historical framework
capture tool retains its exact-preservation comparison and is not weakened.
