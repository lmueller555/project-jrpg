> Historical evidence: these captures record the previous implementation. The
> later Eldenmere architecture audit removes the town antler instance and vista
> configuration; regional and detailed Sanctuary bindings remain active.

# Pale Antlers: active production integration review

Initialized **production Game**, live maps/bindings, unchanged logical collision,
ordinary cameras and native 960×640 drawing. No replacement scenery is installed.
The [regional design](../../world/regions/ELDEN_VALE.md) remains the creative
authority; [OVERWORLD](../../OVERWORLD.md) and the [reserve guide](../../SANCTUARY_RESERVE.md)
own maintenance facts. These captures are evidence, not user visual approval.

## Retained representative evidence

| Actual-game view | Native capture |
| --- | --- |
| Reachable town roof gap | [Distant tips](town_gap_0.png) |
| Northern lawn outside the authored vista | [No walk-through background bone](town_gap_1.png) |
| Ordinary regional approach | [Branches and skull](regional_approach.png) |
| Miniature approached from the west | [Miniature/forecourt](miniature_from_west.png) |
| Detailed northern loop | [Recognizable anatomy](north_reveal.png) |
| Detailed eastern circuit | [Raised-skull visibility](east_raised_skull.png) |
| Temporary real passive Mira follower | [Companion beneath span](companion_span.png) |
| Continue near bone | [Restored exact position](continue_near_bone.png) |
| Immediate stable reduced-motion assistance | [Reduced-motion span](reduced_motion_span.png) |
| Production care performance | [Mira treating the worker](care_treat.png) |

[Keeper-rail animation](keeper_rail.gif) records the actual production action,
including intermediate progress. Ten native PNGs and one GIF are retained to
avoid committing the entire capture bank. `observations.json` inventories all
41 reproducible views and the complete artifact hashes, alongside the retained
subset. The harness emits all walking/running, door/room, cave entry/return and
story views when rerun; those omitted views are not linked as missing files.

## Cross-scale visual findings

The town glimpse keeps one world anchor. Its authored south-of-roof vista uses
an immediate position-dependent boundary fade, not parallax or a general 3D
horizon. Walking north removes it rather than making distant bones appear on
reachable lawn. The town spawn itself does not show the glimpse.

The ordinary regional approach now reveals the coherent branches and skull east
of the miniature. It uses an existing lower ridge support instead of blindly
activating the original northern candidate above the approach camera. The
96×80-logical miniature uses anchor `[48,78]` against unchanged entry/return
contracts. Both east/west approaches are walked around its existing contact
area; its image canvas/alpha does not become a trigger or collision footprint.

The detailed forecourt intentionally screens much of the anatomy. Northern and
eastern circuits supply the near reveal. The coherent 0.625 detailed rendition
preserves anatomy/orientation; raised skull/branches receive local visibility
assistance and no collision. Lower earth/root contours register to retained
ridge ground. The final contact review removed a ruler-straight clipping scar;
passing support tests alone was not treated as visual acceptance.

## Exploration, movement, transfers and saves

The exploration fixture disables the opening director and starts at the normal
town spawn. It does **not** seed quest completion, equipment or party members.
It walks to the roof gaps, departs through the production town contact, follows
the generated road, visits the miniature from both sides and the northern
shoulder, enters the reserve normally, completes the full protected circuit in
both directions (walking/running), and visits every public approach plus the
grove, cloister, survey station and cave apron.

The report records 75 movement segments / 7,948 checked updates, four-direction
diagonal full-foot probes (all 24 updates moved), and selected span walk/run GIFs
in both directions. Movement uses `Game.update` and the existing 24×12 probe.
No route is cleared by shrinking probes, teleporting around supports or moving
quest stations.

All eight exploration scene transfers pass: town→region→reserve→hall→relief→
hall→reserve→region→town. The ordinary closed keeper rail blocks forward input.
The round trip preserves quests, inventory, dialogue flags, abilities, desired
music and unique ownership of stable authored town/persistent actors.

Continue near bone and beneath a span preserves exact player scene/position,
quests, party, dialogue flags and regional state. Screenshots wait for the
normal restore fade. Existing ambient routines restart on launch, so a resident
may resume inside rather than outside its house. Ownership follows stable
identities across **all** loaded scenes, not the changing outdoor subset; lost
or duplicated actors are still rejected. No new scenery save field is added.

A separately labelled temporary recruitment fixture stages the actual passive
Mira follower, then runs 45 ordinary following updates with full-foot checks on
both actors. The prior party is restored afterward. This is not a claim that
the unseeded tour recruited Mira through the story. Regional miniature scale
continues not to display passive detailed followers.

## Arrival, care, rail and return

A separate story fixture uses the production
`SanctuaryArrival.prepare_preview` prerequisite checkpoint. It is **not** an
uninterrupted opening-to-MQ03 playthrough. After setup, the actual director,
blocking, story-positioned actors, camera, care actions and rail run through
normal updates/input. All eight beats traverse and finish; observed care actions
include placement, cloth pickup, treatment, finishing and retrieval.

The rail reaches intermediate positions and opens, control returns to
exploration, and actual E links enter the existing cave and return to the
Sanctuary. No combat, rescue reward, deeper descent or new cave bypass is seeded.
Existing story state stays with the established directors.

## Native detail, stability and bounded costs

All 18 live landmark source records (town 1, regional 5, detailed 12) match their
native PNG buffers with **zero RGBA mismatches**. Game frames use native drawing,
not enlargement of a logical mirror. Isolated reduced-motion cutaway pixels
match normal immediate visibility and remain unchanged at later times. Pause
and focus loss preserve time, position and exact world-only native pixels beneath
the raised skull, then exploration resumes.

Warm 20-sample populated-reserve world-render measurements:

| View | Mean / maximum | Same-revision landmark-disabled timing control |
| --- | --- | --- |
| Northern reveal | 13.60 / 15.41 ms | 3.80 ms |
| Eastern circuit | 13.03 / 16.35 ms | 3.56 ms |
| Forecourt | 3.24 / 3.71 ms | 3.37 ms |

The control omits only landmark drawing for timing; it is not a gameplay capture,
changed map or historical step-1 executable. Measurements use SDL dummy and
exclude simulation, display and UI. They are hardware-specific, not an FPS
guarantee. Ground cache is 16,957,440 / 50,331,648 bytes; landmark sources are
7,228,020 / 16,777,216 bytes; largest recorded viewport work is 11,059,200 bytes.
Focused tests separately cover cache behavior, masks, retained collision and
cutaway/vista boundaries. Five reserve-antler tests and eight landmark tests
were independently rerun successfully; broader suites/build checks belong to
the PR verification report.

## Reproduce and limits

```sh
python tools/capture_elden_vale_antlers.py /tmp/elden-vale-antlers-review
python -m unittest discover -s tests -p 'test_elden_vale_antlers_reserve.py' -v
python -m unittest discover -s tests -p 'test_landmark_layers.py' -v
```

The harness uses disposable saves/settings and rejects relevant input changes
during capture. The full source/capture hashes, positions, movement traces,
Continue assertions, ownership, miniature registration, native comparisons,
story observations and performance scope are in `observations.json`.

No user artwork approval or uninterrupted quest playthrough is implied.
Causeway/arch activation remains PR 3. Rising Rain and associated routines/actions
remain the next phase. Atlas/minimap artwork is preexisting, not the final
landmark atlas update. Staged asset provenance stays distinct from active binds.
