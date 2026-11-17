# Eldenmere interior architecture review

Final PR 4 of the four-PR architecture audit. This extends the existing town
composer and source architecture schedule, not a separate art standard.

## Native gameplay comparison

Before captures use main `00572fd3`, including the exterior rebuild, crossing
assemblies, #250 Lantern fix and #252 pedestrian streets. After captures use the
corrected PR4 implementation `b5089cec`; subsequent review-document additions do
not change gameplay or exported artwork. Each pair has the same room, original
safe arrival, facing, camera reset, 400 ms ambient clock and 960×640 window.

| Purpose | Before | After |
| --- | --- | --- |
| Working mill | [Native before](before_mill.png) | [Native after](after_mill.png) |
| Mira's workshop | [Native before](before_mira.png) | [Native after](after_mira.png) |
| Inn common floor | [Native before](before_inn.png) | [Native after](after_inn.png) |
| Fixed shop stock | [Native before](before_item_shop.png) | [Native after](after_item_shop.png) |

- [New guest floor](after_inn_guest_floor.png): four ordinary guest bays and a
  reciprocal stairwell, not another rest or pricing system.
- [Reduced-motion mill](after_mill_reduced.png): fixed supports and one stationary
  mechanism frame; processing motion follows the existing stopped-wheel state.
- [All sixteen reviewed rooms, downscaled index](rooms_contact_index_DOWNSCALED.png).
  This is a labelled navigation index, not native-resolution evidence.
- [Real departure/return frame](actual_town_return.png), on the preserved streets.

The native PNGs are unmodified production `Game.draw` captures, not source-art
composites. Static room starts are disclosed review fixtures. The indexed-color
[continuous movement preview](rest_stairs_continue_return_PREVIEW.gif) is
480×320, not a native-pixel authority.

## What changed

- Fifteen established rooms keep their identities and real owned objects. South
  exits now cut through the wall base with jambs, return faces and a threshold.
  Open cutaways have no invented door leaf out of sync with the door controller.
- The mill is one tall processing bay: east-wall wheel axle, gearing, shaft,
  millstones, grain stores and the retained sorting/work table. The existing
  wheel-stop flag owns the mechanism, including first load and Continue.
- Mira's shelves hold repair supplies. Her workbench, repair table, action
  registrations, hearth and corresponding exterior flue are unchanged.
- School desks, chairs, board, map, teacher, lesson access and triggers remain
  their real objects. The retained rear/side faces are not forced to copy the
  exterior front windows.
- Halden, Elira, Venn and homes A/B/C use distinct linens and household storage,
  without assigning new occupations. Elira's memorial shelf remains stateful.
  Liam's toys, Daisy's objects and their routine ownership are untouched.
- Serene, Caelan and Tomas's hall, bedroom and dining room retain their curated
  domestic bank, meals, inspections, opening and rest routes. This household is
  not the regional Sanctuary.
- Indoor potions, weapon and armor display match the storefront. These are
  decorative, not extra purchasable equipment or an inventory change.
- The existing `inn` scene, keeper, exterior portal and ground-floor `guest_bed`
  remain. One `inn_guest_floor` uses the existing interior registry. Four upstairs
  bays correspond to the exterior guest-storey windows; the common-room hearth
  and upstairs flue explain the existing exterior chimney.
- Only the reciprocal stairs opt into excursion rearming. Both arrive facing
  front on clear `[366,300]` landings, with the existing 0.25 s transfer cooldown.
  Held north cannot bounce between floors; the player must leave the reserved
  stair/landing rectangle before deliberately approaching again. An NPC cannot
  rearm the player's sensor.
- Lantern phase aliases retain the canonical material/frame drawings and #250's
  transparent collected-contents surface. The full-width real table remains;
  exactly one frame moves from workshop to carrier to home at the existing cue.

## Deliberate occupancy and preservation

All rectangles are logical `[x,y,width,height]` and source-owned in the existing
architecture schedule and interior recipe. No exterior blockers or streets move.

| Room | Named addition |
| --- | --- |
| Mill | Processing base `[300,132,96,36]` |
| Inn | Stair stringers `[336,204,5,80]`, `[391,204,5,80]`; hearth base `[353,72,42,24]` |
| New guest floor | Three 5-unit bay screens and the same two stair stringers |

The builder also exports exact logical diagnostic deltas for the
[mill](../../../assets/maps/eldenmere/town_hd/rooms/interior_architecture/mill/collision_delta.png)
and [inn](../../../assets/maps/eldenmere/town_hd/rooms/interior_architecture/inn/collision_delta.png).
These are occupancy data, not gameplay screenshots.

The broad door audit caught an initial 6-unit clip into the old mill sorting
approach. The base was narrowed from x294 to x300, restoring the **unchanged**
`[288,168]` station and its entire 24×12 player probe. A regression now drives
real `Game.update` movement from the original mill arrival to that station.

Valid old save positions stay exact. Positions inside newly occupied mill,
stair or hearth footprints use the existing checked room-spawn fallback, without
changing quests, party, inventory or currency. Tests cover representative old
positions at every new downstairs occupancy and an unchanged valid position.

[Exact preservation results](preservation.json) verify all 17 prior registered
interiors' old metadata, portals, NPCs and fixture positions/depth/state images.
All 116 nonshared paths from #252 remain byte-identical. The town JSON changes
only `interior_scenes` and `art_replacements`. Ground chunks, coverage, street
network, districts, protections, navigation, collision and movement routes are
exact. Shared generated manifests are recomposed from authoritative recipes;
only the new interior inventory/interfaces and dependency hashes change.
Services, bed-rest, Mira quest/party runtime and #250 Lantern runtime/data remain
byte-identical.

## Gameplay and state verification

[Stair/rest/save metadata](gameplay_evidence.json) records 52 native views and 8
real doorway transfers. One continuous input sequence enters from town, confirms
the original downstairs guest-bed recovery, climbs upstairs, creates a fresh
`Game` and uses disk Continue upstairs, descends and returns outside. It does not
teleport between those steps. Walk and run both work in both stair directions;
held-input cooldown/rearming, companions and persistent ownership are checked.
Manual-slot and disk Continue work on both floors, preserving party, quests,
inventory and gold. The existing rest price is zero and remains zero.

[Final town-route summary](town_route_summary.json) covers all thirteen exterior
round trips, the two bridges across the usable width, mill landing, crossing
Save/Continue, and real south departure/return. [Street-route summary](street_route_summary.json)
adds sixteen walk/run routes on #252's updated pedestrian network.

Story Mira traverses the same reciprocal doors, survives upstairs Continue and
returns downstairs with one persistent owner. A separate existing Lantern
production-action capture passes workshop collection, held-frame travel,
home placement, snack/rest and later return; its
[timed ownership/source metadata](lantern_regression_metadata.json) is kept
separate from the inn sequence. Full Lantern regression tests also cover
interrupted pickup/placement, Continue and completed-frame ownership.

## Reproduce

Use the repository's Pygame runtime and Pillow asset environment. Headless runs
use `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` and disposable saves/settings.

```sh
python tools/build_eldenmere_hd.py --check
python -m unittest discover -s tests -p 'test_eldenmere_interior_architecture.py' -v
python -m unittest discover -s tests -p 'test_doors.py' -v
python tools/capture_eldenmere_interior_architecture.py /tmp/eldenmere-interiors
python tools/capture_eldenmere_interior_architecture.py /tmp/eldenmere-lantern --lantern
python tools/capture_eldenmere_architecture_audit.py /tmp/eldenmere-route --movement
python tools/capture_eldenmere_streets.py /tmp/eldenmere-streets
python docs/reviews/eldenmere_interior_architecture/capture_before.py /path/to/00572fd3 /tmp/eldenmere-before
```

The builder verifies **955 byte-reproducible exports**. Detailed module counts,
results and the known baseline failures are in [test_results.json](test_results.json):
**424 passing cases, five exact-main baseline-parity failures, zero new failures
or errors, across 429 scoped executions in 33 modules.**

## Verification limits

These are production-rendered fixture and movement checks, not an uninterrupted
story playthrough or a claim that every legacy actor pose has been rebuilt.
Rhea recruitment, depleted resources and the existing shipped MQ04 prerequisite
checkpoint are explicitly disclosed fixtures; no new quest progress is invented.
Static room images do not independently establish movement or object ownership.
The [normal/reduced pairs](normal_reduced_review.json) were reviewed for all rooms; selected native witnesses
keep this review below 3 MB instead of committing the entire capture output.

The complete repository test suite was not run. Initial concurrent attempts hit
OS memory limits and one direct-selection attempt missed the repository's
top-level test-helper import path; bounded discovery reruns replace those
incomplete attempts. Four existing MQ02 geometry tests still fail identically on
main and PR4 because the helper's 2-unit grid cannot reach odd target `[479,287]`.
The [parity record](mq02_parity.json) and separate
[main](mq02_main-reachability.json)/[PR4](mq02_final-reachability.json) movement
witnesses show the target is standable, real `Game.update` reaches it, and the
actual prepare action completes on both revisions. No unrelated MQ02 runtime/helper change is
included. One additional existing Regent assertion expects Continue to disappear
after the active resume loses its checkpoint; it fails identically on exact
main and PR4 because a validated library checkpoint remains available. The
[separate parity proof](regent_parity.json) records this behavior. All five
failures are reported, not hidden or waived as a full-suite pass.
