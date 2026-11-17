# Old causeway and inhabited ruins: production gameplay review

Final production Game, generated regional recipe, HD bindings and ordinary native
960×640 drawing. The capture installs no replacement art, support masks or
in-memory scenery. All exploration saves/settings are disposable. The regional
[creative guide](../../world/regions/ELDEN_VALE.md) remains authoritative;
[OVERWORLD](../../OVERWORLD.md) owns maintenance facts. This is review evidence,
not user visual approval.

## Retained native evidence

| Actual production view | Capture |
| --- | --- |
| Complete open arch and maintained road | [Portal](portal.png) |
| Local visibility beneath the lintel | [Cutaway](lintel_cutaway.png) |
| Contact beside the left physical pier | [Pier approach](near_causeway_arch_left.png) |
| Authored joined raised remnant beside the route | [Deck and broken end](joined_remnant.png) |
| Reused resting edge with existing bench | [Resting corner](resting_edge.png) |
| Rooted foundation and registered fragment | [Optional fragments](rooted_foundation.png) |
| Northern landscape in the same active region | [Pale Antlers context](pale_antlers_context.png) |
| Actual expanded-town return | [Inn/shop business lane](expanded_town_return.png) |

[Bidirectional walking/running through the portal](portal_walk_run_preview.gif) records
actual movement and ordinary camera following. Its retained 480×320 animation is a
nearest-neighbor preview of the full 960×640 GIF, not native-detail evidence;
the eight native PNGs retain exact rendering detail. These images and one GIF are
retained to keep the review bank small. `observations.json` inventories the full
reproducible causeway capture bank and the retained subset. The complete Antlers,
transfer, follower and story regression is rerun into a separate output bank,
rather than duplicating all its screenshots in this PR.

The causeway and northeastern Antlers are too far apart to share an ordinary
480×320 logical viewport. The context image comes from a separately initialized
production journey walking from town to the Sanctuary, not a painted panorama or
a claim of one uninterrupted causeway-to-cave playthrough. Both journeys use the
same final live regional map and connect through the existing town/road network.

## Construction and visible contact review

The arch is deliberately projected as one coherent 1.25 physical rendition:
480×360 artwork / 240×180 logical units at density 2, not automatic enlargement
from higher artwork density. Its lintel is overhead. Its two supports are normal
depth-sorted props with explicit footprints, not collision from sprite alpha,
shadow or whole image rectangles. The final transparent aperture is 117.5 logical
units; independent reconstruction/aperture tests verify actual exported pixels.

The physical pier rectangles are `[122,-32,56,16]` and `[294,-32,59,16]`.
Their closest edge remains 49.049 units from both the reserved and generated-road
centerlines, preserving the full 96-unit protected travel envelope. Both declared
contact samples are visibly opaque and block the unchanged 24×12 player probe.
The detailed records include draw/foot anchors and native sample coordinates.

The short raised deck and broken end share the exact authored port `[-364,170]`.
Their overlapping joint and handed broken cap were inspected in the actual
renderer. Raised faces remain beside the essential travel surface, not fake
steps or pits across it. No climbing mechanic is implied. Curbs were removed
from flat surviving paving: four 50×46-logical interior slab patches overlay the
existing maintained road without collision or a silently walk-through raised lip.

The resting edge reuses the existing regional bench, with no new service, task
or discovery outline. Masonry stays outside the protected farm work area. The
small fragment's first centered footprint missed its thick grounded left end;
review corrected its physical foot/anchor together while preserving the exact
image origin `[-854,457]`. Its final 22×8 support is `[-852,483,22,8]`, with an
opaque declared contact. No artwork-alpha mask becomes collision. Builders and
focused tests guard explicit contacts, protected routes/work areas and chunk
ownership.

## Actual movement and saves

Exploration begins at the normal town spawn with only the opening director
disabled; it does not seed quest completion, equipment or party members. The
player leaves town through its production contact, then walks to the causeway.
Twelve complete generated-road sweeps cover walking/running, both directions,
and X-offset lanes -30/0/+30: **5,172 checked movement updates**. Changing lanes
or returning to an endpoint uses ordinary movement, never teleportation.
Offset lanes are a conservative portal sweep, not a claim of a fixed normal
cross-section on every curved-road sample.

The post-rebase run preserves the expanded town's true southern contact. The
actual departure walks through the inn/shop lane to logical y=1602 before transferring
near imported exit `[528,1620]`, not an obsolete interior trigger. A real return
from the causeway lands exactly at imported `[528,1572]`. Both imported runtime
contacts and `overworld_travel.py` are recorded in the source fingerprint.

Additional portal clips cover both directions at both speeds. Running diagonal
approaches around each pier retain full-foot safety, including collision against
real support corners. Source/trace records distinguish visible grounded piers
from the elevated lintel. Ordinary grass around optional remnants remains open.

Save/Continue at valid positions beside **both** supports and beneath the lintel
preserves exact player scene/position, quests, party, dialogue flags and regional
state. Stable authored/persistent actor identities retain one owner across all
loaded scenes; ambient routine rooms/phases may restart as described in the
[Antlers review](../elden_vale_pale_antlers/README.md).

**Historical-save limitation:** a separately labelled synthetic old save placed
exactly inside either newly solid off-road pier triggers the game's existing
generic clear-landing fallback, to regional spawn `[288,-600]`. Progression is
preserved. This is not an exact-position Continue pass, a new migration or new
save field, and it is not used as evidence for traversal clearance. No live
traversal actor is relocated to conceal a blocked route. Valid nearby saves keep
their exact positions.

## Restrictions, stability and fresh cross-scale regression

Transient isolated flag permutations test opening-region release and bridge
repair independently, then restore the live world flags. The causeway does not
cross a river or wall, unblock either guarded checkpoint, repair the western
bridge or change the cave restrictions. Portal/support collision remains the
same under all tested flag combinations. These probes do not award story facts
or write a repaired-bridge journey.

The lintel's immediate cutaway is exercised, remains identical under reduced
motion and is time-invariant at later samples. Pause/focus loss preserve time,
position and exact world-only native pixels, then exploration resumes.
Fourteen new/reused causeway source bindings match their native PNGs with
**zero RGBA mismatches**; logical-mirror enlargement is not used.

After causeway activation, the harness reruns the full production Antlers review:
75 movement segments / 8,063 updates, both reserve circuits, every public approach,
all eight exploration transfers through town/region/reserve/hall/relief and back,
two-position exact Continue, native detail, reduced/freeze and unique ownership.
Regional miniature scale still does not display passive detailed followers;
the actual detailed Mira-following fixture is rerun and labelled as temporary
recruitment, not new regional party behavior.

The separate production arrival prerequisite preview reruns all eight actual
arrival beats, care, intermediate keeper-rail operation, return to exploration
and cave E entry/return. It seeds prerequisites only as explicitly documented;
it is not a new uninterrupted quest playthrough, battle, rescue reward or deeper
cave descent. No old PR 2 completion result substitutes for these fresh checks.

## Rendering budgets and reproducibility

Twenty warm world-render samples per view, SDL dummy, excluding simulation,
display and UI: ordinary portal/remnant/resting views average 4.48–5.12 ms; the
cutaway-active lintel view averages 13.02 ms with maximum 15.03 ms. These are
hardware-specific measurements, not an FPS guarantee. The matched same-revision
timing control omits landmark passes only and still includes ordinary physical
props; it is not a historical PR 2 executable or a modified gameplay capture.

The regional render cache reaches 64,880,640 bytes within 67,108,864; metadata
remains within 64 chunks. Causeway landmark sources use 910,000 / 16,777,216 bytes;
cutaway work is viewport-bounded at 11,059,200 bytes, not cached per player
position. Trace/source/capture hashes and precise profiling scope are recorded
in `observations.json`; the run rejects relevant input changes during capture.
Eight final causeway tests were independently rerun successfully, including
contact registration, transparent aperture/reconstruction, exact added collision,
protected clearance rejection and joint ports. Broader suite/build results belong
to the PR verification report. Five southern-exit tests also passed after the
upstream reconciliation, including business access, old-save positions and
automatic walking/running round trips.

```sh
python tools/capture_elden_vale_causeway.py /tmp/elden-vale-causeway-review \
  --regression-output /tmp/elden-vale-causeway-antlers-regression
python -m unittest discover -s tests -p 'test_elden_vale_causeway_integration.py' -v
```

Ordinary scenery gains no blanket yellow outline or glint. Original builders,
inhabitants and purposes of the ruins remain unresolved. Rising Rain, associated
routines/actions and final atlas/minimap artwork remain the subsequent phase.
