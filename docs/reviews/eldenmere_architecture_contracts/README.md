# Eldenmere architecture contracts and town landmark correction

PR 1 of the four-part architecture audit. This step changes only town landmark
selection and authoring metadata. Bridge, exterior and interior art follow in
separate sequential PRs. It does not activate Rising Rain or change the regional
causeway, shared landmark artwork or detailed Sanctuary.

## Actual initialized Game evidence

These are native 960×640 renders from `Game.draw`, with real production maps,
actors, doors, water phases and `CameraDirector`. Static positioning fixtures are
not an uninterrupted playthrough; the movement and transfer checks use
`Game.update`. All journeys/settings are temporary.

| View | Previous implementation | This correction |
| --- | --- | --- |
| North lane, ordinary player-tracked camera `[360,20]`, Caelan `[600,180]` | [Before](before_town_north_lane.png) | [No antlers or substitute](after_town_north_lane.png) |
| Household survey, explicitly focused production camera | [Before](before_sanctuary_survey.png) | [After](after_sanctuary_survey.png) |

- [Regional antlers retained](after_regional_antlers_preserved.png) and
  [detailed Sanctuary antlers retained](after_detailed_antlers_preserved.png)
  are byte-identical to their baseline native images.
- [Business lane](after_southern_business_lane.png) retains both businesses.
- [Actual departure and return](after_southern_actual_return.png) follows the
  public road from `[528,1260]` through the lane, automatically leaves town and
  returns at `[528,1572]`, facing back, with safe feet and no immediate bounce.
  [Full movement trace](gameplay_southern_return.json).

The same fixtures render 173 views per stage, including all 13 buildings, actual
five-state doors, normal/reduced motion, six water phases and current interiors.
There are 26 movement/door/road checks and three exact crossing Save/Continue
checks, with no failures or unsafe feet. The only changed baseline images are
those containing the former town antlers. Collision, door registration, NPCs,
quests, services and the repaired southern exit are unchanged. See the
[recorded evidence](gameplay_evidence.json) and [reusable fixture](gameplay_fixture.json).

The current documentation/test contract no longer requires a town glimpse.
Historical antler review images retain their names and are explicitly labelled as
the previous implementation. Shared antler art and regional/reserve consumers
are untouched.

## Construction references, not gameplay

The [projection reference](projection_reference.png) is a deliberately labelled
construction diagram with a 24-logical-unit ground grid and the approved Caelan
idle at 2×. It is not evidence of final building or bridge art.

The technical schedule lives beside the maintained town recipe at
`assets/source/maps/eldenmere/town_hd/architecture_schedule.json`. It covers all
13 exteriors, their rooms, canvases, actual ground boxes, depth baselines,
thresholds, approaches, eaves, occupied floors, hearths/flues and protected
fixtures/routes. It reserves the inn's east stair footprint and clear landings
on both floors, and declares all three crossing interfaces. No new art guide was
created: projection and crossing rules extend the existing global standards.

## Reproduction and review limits

```sh
python tools/build_eldenmere_hd.py --check
python tools/eldenmere_architecture_contracts.py --check
python tools/capture_eldenmere_architecture_audit.py /tmp/eldenmere-review --movement
python tools/check_eldenmere_hd.py
PYTHONPATH=.:tests python -m unittest test_eldenmere_architecture_contracts test_eldenmere_architecture_review test_elden_vale_antlers_integration test_elden_vale_antlers_reserve test_landmark_layers test_town_southern_exit test_town_services
```

Source hashes and generated selectors/metadata are checked. The new schedule
validator checks every retained building portal and hearth and the current exit.
The unchanged regional/reserve tests still protect anatomy, contacts and routes.
Passing tests do not certify art quality. This step's crossing movement is
centerline only; occupied/full-width artwork validation belongs to PR 2. Final
exteriors, footprint overlays, all interior functions and real inn stairs remain
their later PRs. Hosted CI status is recorded on each exact PR head separately;
local validation is not a hosted-CI pass.

## Verified local checks for this PR

- **73 affected-area tests passed**, covering architecture schedules, current
  town integration, doors, antlers/reserve, southern exit and services.
- **11 architecture/review tests passed** (some overlap the 73-test selection).
- Town builder: **841 exports verified**; construction diagrams reproduce.
- Full town aggregate was attempted, **not passed**. Its school-motion assertion
  expects multiple unique ambient frames although the unchanged school has no
  motion. Lantern rest raises `AttributeError: LanternRest.workshop_empty` when
  the carried frame leaves the workshop. Both failures were reproduced in the
  unchanged `57d0613c` checkout. The aggregate process ended with code 137 before
  a complete report. Neither is introduced by this PR. The school artwork is
  reviewed in PR 3; the real workshop relocation lifecycle crash is corrected
  with a focused regression in PR 4, not by suppressing tests here.

See [validation results](validation.json). Hosted checks, if configured, must be
verified on the published head; absence of checks is not a CI pass.

## Latest-main replay after settlement framework #247

This local replay has exact upstream parent `8022e7d5cdd939d832c26ffbc5b0a914ef69e564`. It preserves the new settlement source recipe, catalogue, tests, source-owned clearance contracts, documentation and metadata-only builder integration. No placements or ground treatments are activated.

All **92 relevant tests pass**, including settlement protections, architecture, doors, services, southern travel and both independent antler consumers. **842 exports reproduce**, including the settlement report. Its **114 protected spaces** and **200 semantic asset records** retain their geometry and interfaces; source provenance hashes are regenerated. See [latest tests](latest_main_tests.json) and [preservation evidence](latest_main_preservation.json).

The source schedule's `protected_baseline_commit` and original screenshot provenance remain the historical audit baseline, not a claim that this branch is based on that old revision. The replayed town map is byte-identical to the original PR1 result; #247's metadata-only additions are retained separately.
