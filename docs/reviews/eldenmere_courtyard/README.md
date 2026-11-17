# Serene's household courtyard — settlement PR 3

This is the third of eight settlement-composition PRs. It gives Serene, Caelan
and Tomas's home terrace a small domestic herb pocket and planted/storage edges.
The regional Sanctuary remains a separate place. The [central terrain standard](../../TERRAIN_ART_STANDARD.md#eldenmere-settlement-framework)
owns construction and maintenance guidance; this review records implementation
facts, scope and evidence.

## Composition and ownership

The source recipe activates `courtyard_dressing` only for `serene_terrace`:

- Seven solid props: a rain barrel, two herb planters, one herb pot, a flowerpot
  pair, a small firewood pile and one short horizontal fence panel.
- Four low, nonblocking plant groupings: white/violet flowers and two clover
  patches. Their native breeze animation and reduced-motion art come from the
  existing vegetation bank.
- Six grass/dirt blob cells form a quiet eastern soil patch. Seven explicit
  meadow instances are retired where they would grow through the garden.

All 11 new entities reuse native 2× source art at its existing logical size.
The source metadata owns frame cadence, depth and occupied silhouettes; the
composer does not resize or invent per-instance animation. Existing windows,
roof, troughs, shade tree, bench, provision basket and watered flower beds retain
all their records. New scenery grants no harvesting, watering, loot or dialogue.
The gardener still obtains water at the well and services her six existing beds.

The central apron, doorway, terrace stairs, Tomas's steps and Regent gathering
stations remain open. The eastern pocket was fitted against Mira's real roof
silhouette as well as movement reservations; a proposed flower placement that
overlapped it was moved before integration. New garden containers form a row
with clear access in front rather than requiring travel between close pots.

## Build and physical contract

`tools/build_eldenmere_hd.py` remains the only town map writer. The new
`tools/eldenmere_settlement_dressing.py` validates the bounded activation,
source-native art, actor sightlines, explicit supports and occupied artwork.
It reads freshly composed existing art through the export buffer, avoiding a
previous-build validation lag.

Each solid object declares an integer logical support. These seven supports
add exactly **520 collision pixels**. No old blocker is cleared; navigation
remains byte-identical. The source collision check reconstructs the original
mask plus exactly the published supports, and independent tests/captures check
that union. It does not broadly permit arbitrary collision differences.

The compiled `settlement_dressing` ledger owns entities, supports, grass
retirements, soil cells and source hashes. Rebuilding reconciles only declared
courtyard instances and retired records. Other owners remain intact. Unknown
courtyard instances and deactivation without explicit cleanup fail validation,
preventing retained objects from silently losing physical support.

There is no new runtime module, scene, service or save field. Older saves at a
newly occupied support use the existing clear-ground restoration path. A real
Continue regression verifies successful recovery in town with unchanged quest,
party and inventory state and no duplicate courtyard objects.

## Verification and evidence

The final baseline is **`d2bd1613`**, including main's independently merged
interior rebuild and inn guest floor. [Revision evidence](before_revision.json)
records its detached checkout. The merged source preserves those rooms and their
stair/door behavior; this PR's exterior geometry is compared with that current base.

- **221 tests pass on the merged implementation:** 154 core cases covering
  courtyard contracts, gardener behavior, streets/maps, old-save recovery,
  entrances/travel, native rendering, crossings and the new interiors; plus
  67 opening, Regent, actor-handoff and Lantern checkpoint cases.
- Reproducible checks verify **955 town exports** and the standalone settlement
  report. Both checks run on the merged source.
- Six native ground phases each change **11,564 pixels**, with **zero changes
  outside** the soil cells' declared one-tile transition rim.
- All 13 native overview fixtures match outside the courtyard. Eleven complete
  views remain pixel-identical, including both water presentations. Existing
  entity records and non-ground artwork remain unchanged.
- Collision is exactly the baseline plus the seven support rectangles. All
  **520** changed logical pixels are additions inside those supports; navigation
  PNG bytes are identical. Door interfaces, streets and story coordinates remain
  unchanged. Grass changes are exactly the seven retired source records.
- **16 walking/running route checks**, in both directions, cover the public apron,
  stairs, garden approach and western edge: 991 production updates with no route
  replans. Two actual doorway roundtrips enter `sanctuary_hall` and return normally.
  The driver uses production pathfinding around live household actors and records
  the actual clear fixture positions; NPCs are never removed to force passage.
- Save/Continue preserves all 11 unique new props, every support pixel, clear
  player ground and quest/party/inventory/flags. A separate real old-save test
  loads from newly occupied ground and confirms safe recovery without lost progress.
- Four additional native courtyard closeups retain detail and readable actor/prop
  depth. Their reduced-motion samples remain exactly still; normal water retains
  its existing animation and reduced water remains still.

[Observations](observations.json) record source hashes, explicit support deltas,
ground-phase differences, movement traces, doorway approaches and Continue state.
[Before observations](before_observations.json) and [town metadata](before_town.json)
retain the original witnesses. The images are production-Game fixtures with
isolated saves, not a continuous quest playthrough. The separate story tests
exercise actual progression and restoration.

| Area | Native production evidence |
| --- | --- |
| Whole household terrace | [Terrace](serene_terrace.png) |
| Resting and domestic edge | [Western courtyard](courtyard_west.png) |
| Herb garden and roof clearance | [Eastern courtyard](courtyard_east.png) |
| Doorway and shared apron | [Door](courtyard_door.png) |
| Public stairs | [Stairs](courtyard_stairs.png) |
| Actual return from the home | [Walking](doorway_walk.png), [running](doorway_run.png) |
| Save restoration | [Continue](continue_courtyard.png) |

Matching before views and reduced-motion samples are retained beside these files.
The random doorway obstruction observed during driver development was Tomas
crossing or occupying a fixture in the entrance aisle, with no dialogue lock.
The review driver was corrected to use valid clear starts and real pathfinding;
production collision and actor ownership were not changed to hide it.

## Reproduce

Use the repository's Pygame, Pillow and NumPy tooling. Captures use disposable
saves/settings and default to dummy SDL drivers.

```sh
python tools/build_eldenmere_hd.py --check
python tools/build_eldenmere_settlement_framework.py --check
python -m unittest discover -s tests -p 'test_eldenmere_settlement_courtyard.py' -v
python -m unittest discover -s tests -p 'test_gardener.py' -v
python tools/capture_eldenmere_courtyard.py /tmp/courtyard-review
```

For intentional-difference checks, add `--baseline-dir /path/to/pre-pass-folder`.
That folder contains framework `observations.json`, `town.json`, logical
`collision.png`/`navigation_allowed.png`, six full native `ground_phase_0.png`
through `ground_phase_5.png`, and the recorded `baseline_revision.json`. The
baseline can be reconstructed from the recorded detached main revision. It also
retains four actual clear-ground courtyard camera fixtures in
`courtyard_details.json`; requested and actual player positions are distinguished.
The historical framework/street reviews remain unchanged.
