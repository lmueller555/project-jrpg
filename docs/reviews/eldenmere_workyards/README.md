# Workshop and mill yards — settlement PR 4

This fourth settlement-composition PR establishes a small repair bay beside
Mira's workshop and a clear delivery apron at the mill. The
[central terrain standard](../../TERRAIN_ART_STANDARD.md#eldenmere-settlement-framework)
owns maintenance guidance. The [previous courtyard](../eldenmere_courtyard/README.md)
remains intact; civic, household, eastern-growing and southern-frontage work
remain later deliveries.

## Scope and composition

The shared settlement recipe enables `workyard_dressing` for the existing
courtyard plus the bounded `workshop_mill` district. Its independently owned
`settlement.workyards.*` records add:

- A toolbox and empty crate in a small repair-side bay.
- A plain grain sack and empty crate along the mill apron's eastern edge.
- One flat shaving patch between the repair containers, baked into native ground
  before actors rather than drawn over their feet.
- Eighteen native earth cells: six for the repair bay and twelve for the delivery
  apron. No meadow retirement is needed in these areas.

The inward mill-stock alternative conflicted with Lantern's Tomas station, so
stock stays at the perimeter with access from the west. The historical mill-yard
rectangle overlaps Halden's roof and was not used as an empty placement area.
The front inspection, delivery and gathering space remains open. Mira's existing
workbench, rack, fittings and stool/can retain their exact records and owners.
The mill wheel, all three crossing/landing assemblies, entrances and water remain
independently owned.

These are ordinary decorative supplies. They add no pickup, reward, service,
interaction cue or quest object. The three retained-source native prop records
register real sack, empty-crate and toolbox drawings; fruit baskets and provisions
are not relabeled. The sources already supply native detail, and the exporter
preserves their scale, hard alpha, depth and source hashes. It does not enlarge
old map pixels or create another live representation of a quest object.

## Integration and safety

One parameterized resolver supports both districts, with separate scope,
namespace, ledger and source configuration. The courtyard's API and compiled
ledger remain byte-identical. The combined framework checks proposed occupied
artwork across district boundaries before publishing either. Rebuilds reconcile
only trusted owned instances; unsupported activation and unsafe deactivation
remain errors.

The new ledger is `settlement_workyards`. It contains four world entities,
separate `ground_entities` for flat wear, explicit supports, `ground_cells` and
source provenance. Source metadata owns native frames, cadence and depth.
The existing town composer remains the sole map writer and checks the independent
workyard-prop exports before building the town.

The four solid props add exactly **432 logical collision pixels**. The source
mask plus the prior courtyard supports plus these new supports is the complete
physical contract; old blockers are never cleared. Navigation bytes, entrances,
travel contacts, streets and original work/story stations remain unchanged.
Normal movement, old-save recovery and ownership restoration are checked through
the actual Game. No runtime controller, dialogue, scene or save schema changes.

## Validation and evidence

The baseline is clean main **`3481e2b7`**, recorded in
[before revision](before_revision.json). Validation includes:

- **167 core tests pass**, covering both district contracts, native exports,
  collision/ownership, map/exit/travel, renderer, gardener, crossings and interiors.
- **79 MQ02, gift, Lantern and actor-handoff tests pass**, including the full mill
  quest progression. After final flat-shaving registration, all 13 focused
  workyard cases pass again, including real old-save recovery.
- **955 town exports**, the standalone settlement report and all **four native
  prop-bank outputs** verify reproducibly. The catalogue contains 203 semantic
  assets and validates 1,154 native images.
- Six native ground phases each change **39,388 pixels**, with zero differences
  outside the declared earth transition rim and flat-patch coverage.
- All **18 crossing/landing walk-surface comparisons** (three assemblies across
  six phases) remain exact. Existing entities and non-ground art remain unchanged;
  the prior courtyard ledger is identical. Navigation is byte-identical and
  collision equals exactly the additive support union.
- **16 walking/running checks**, in both directions, complete 1,601 production
  updates with no replans. Four actual doorway roundtrips cover Mira's workshop
  and the mill, walking and running, with ambient actors retained.
- Save/Continue preserves four unique new solid props, the flat patch, every new
  support and the existing courtyard without changing quest/party/inventory/flags.
- All 13 overview fixtures match outside the workyard; 11 entire views remain
  pixel-identical. Four closer native views retain correct scale/depth and their
  reduced-motion samples freeze exactly.

[Observations and traces](observations.json) retain the checks, source hashes,
full input traces and doorway/Continue evidence. [Before observations](before_observations.json)
and [town metadata](before_town.json) retain original witnesses. These are
production-Game fixtures with disposable saves, not one uninterrupted quest
playthrough. Normal Mira work chatter can accompany movement; the driver records
it rather than treating exchange ownership as a movement lock. Odd-coordinate
door contacts retain their authored positions, with final short approaches made
through ordinary player input after grid pathfinding.

| Area | Native production evidence |
| --- | --- |
| Workshop work and repair bay | [Front](workshop_front.png), [west approach](workshop_west.png) |
| Mill landing and delivery apron | [Landing](mill_landing.png), [service side](mill_service.png) |
| Real workshop doorway | [Walking](doorway_mira_walk.png), [running](doorway_mira_run.png) |
| Real mill doorway | [Walking](doorway_mill_walk.png), [running](doorway_mill_run.png) |
| Save restoration | [Continue](continue_workyards.png) |

Matching before and reduced-motion views are retained alongside these files.

## Existing upstream trigger-test limitation

The separate ten-case `test_mill_trigger_geometry.py` suite has **six passing
cases and four failures on both clean main and this branch**, with identical
assertion diagnostics. All four stop at the unchanged upstream bypass approach
`(479,287)` before their later steps. This review does not count those failures
as passing or claim to fix that existing upstream approach.

[The comparison](mq02_trigger_comparison.json) records both outcomes, exact
failing cases and hashes proving that `main.py`, `mill_quest.py`, the trigger
suite, upstream map and upstream collision are unchanged. The ordinary mill
progression/controller suite and the new town workyard checks pass separately.

## Reproduce

Use the repository's Pygame/Pillow/NumPy tooling. Captures default to dummy SDL
drivers and use disposable saves/settings.

```sh
python tools/export_eldenmere_workyard_props.py --check
python tools/build_eldenmere_hd.py --check
python tools/build_eldenmere_settlement_framework.py --check
python -m unittest discover -s tests -p 'test_eldenmere_settlement_workyards.py' -v
python tools/capture_eldenmere_workyards.py /tmp/workyard-review
```

Add `--baseline-dir /path/to/pre-pass-folder` for strict intentional-difference
checks. That folder contains framework observations, town metadata, exact logical
collision/navigation copies, six full native ground phases, revision provenance
and the actual clear-point workyard fixtures in `workyard_details.json`. It can
be reconstructed from the recorded base revision. Historical reviews are kept
as evidence, not rewritten to imply this pass existed earlier.
