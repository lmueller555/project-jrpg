# Eldenmere exterior architecture audit

PR3 local candidate, direct parent main `e13a9846` after independent Lantern fix #250. The complete 137-check/movement review below was first captured on `8d63b1b` over merged PR2 `aa231d8d`. The settlement framework from #247 remains intact and metadata-only. These
are actual initialized-Game native captures, not isolated source art. PNGs are
unmodified 960x640 buffers from `Game.draw`; movement uses `Game.update`, the
unchanged full 24x12 foot probe, ordinary collision, actors and camera.

Static survey cameras and safe placements are disclosed review fixtures, not an
uninterrupted story playthrough. Before images are the exact PR2 parent and use
the same player, camera, clock and Reduced Motion fixture fields as the after
images. All 191 paired fixed-view records, plus the additional actual southern return, are in [the capture evidence](gameplay_evidence.json).

## Every live building, native and at Caelan scale

| Building | PR2 before | PR3 after | Reduced Motion | Entrance view |
| --- | --- | --- | --- | --- |
| sanctuary | [Before](before_sanctuary_native.png) | [After](after_sanctuary_native.png) | [Reduced](after_sanctuary_reduced_native.png) | [Entrance](after_sanctuary_entrance_native.png) |
| mira | [Before](before_mira_native.png) | [After](after_mira_native.png) | [Reduced](after_mira_reduced_native.png) | [Entrance](after_mira_entrance_native.png) |
| mill | [Before](before_mill_native.png) | [After](after_mill_native.png) | [Reduced](after_mill_reduced_native.png) | [Entrance](after_mill_entrance_native.png) |
| school | [Before](before_school_native.png) | [After](after_school_native.png) | [Reduced](after_school_reduced_native.png) | [Entrance](after_school_entrance_native.png) |
| halden | [Before](before_halden_native.png) | [After](after_halden_native.png) | [Reduced](after_halden_reduced_native.png) | [Entrance](after_halden_entrance_native.png) |
| elira | [Before](before_elira_native.png) | [After](after_elira_native.png) | [Reduced](after_elira_reduced_native.png) | [Entrance](after_elira_entrance_native.png) |
| venn | [Before](before_venn_native.png) | [After](after_venn_native.png) | [Reduced](after_venn_reduced_native.png) | [Entrance](after_venn_entrance_native.png) |
| home_a | [Before](before_home_a_native.png) | [After](after_home_a_native.png) | [Reduced](after_home_a_reduced_native.png) | [Entrance](after_home_a_entrance_native.png) |
| home_b | [Before](before_home_b_native.png) | [After](after_home_b_native.png) | [Reduced](after_home_b_reduced_native.png) | [Entrance](after_home_b_entrance_native.png) |
| home_c | [Before](before_home_c_native.png) | [After](after_home_c_native.png) | [Reduced](after_home_c_reduced_native.png) | [Entrance](after_home_c_entrance_native.png) |
| liam_house | [Before](before_liam_house_native.png) | [After](after_liam_house_native.png) | [Reduced](after_liam_house_reduced_native.png) | [Entrance](after_liam_house_entrance_native.png) |
| inn | [Before](before_inn_native.png) | [After](after_inn_native.png) | [Reduced](after_inn_reduced_native.png) | [Entrance](after_inn_entrance_native.png) |
| item_shop | [Before](before_item_shop_native.png) | [After](after_item_shop_native.png) | [Reduced](after_item_shop_reduced_native.png) | [Entrance](after_item_shop_entrance_native.png) |

[Downscaled index](all_thirteen_DOWNSCALED_INDEX.png) is only a navigation aid;
the linked native images are the authoritative visual evidence. Source/contact,
footprint and explicit pane-ownership boards are separately labelled authoring
fixtures under `assets/source/terrain/eldenmere/exteriors_hd/architecture_audit/`.
They are not presented as gameplay.

## Construction and material changes

- Native roof planes now cover their occupied ground depth with consistent map
  axes and physical eave heights. Main and annex volumes are explicit; roof/eave
  overhang is not an occupied wall or a reason to enlarge collision.
- Mill receiving-annex/foundation walls start at the retained occupied x24,
  rather than painting a ground-level wall into the traversable west approach.
  Its joined higher processing bay has a loading hatch and hoist, not unexplained
  residential storeys. Wheel placement [88,94] and axle [112,118] are unchanged.
- School walls terminate at x24..168. Its book entrance, bell and classroom bays
  remain readable; the existing shade tree remains a separately owned foreground
  plant rather than a transparent-wall workaround.
- Mira, mill and school flues match their retained right/rear hearths. All cap
  emitters and roof planes are recorded in the existing architecture schedule.
- The seven households have distinct bay rhythms, framing, roof repairs and
  domestic storage/planting arrangements without assigning residents new jobs.
  Serene's household keeps its bell, entrance and family role, separate from the
  regional Sanctuary. The inn remains two-storey with four guest bays and the
  reserved east stair zone; accessible guest-floor work follows in PR4.
- Glass masks are drawn per pane and exclude roof, stone, timber, curtains and
  fixed shop stock. Material masks have exclusive visible ownership. Window
  light stays steady; smoke and cloth move independently. Existing business
  signs have one separate owner, not a baked duplicate plus a second sign layer.
- Fixed shop stock retains the potion, sword/shield and helmet/breastplate
  presentation without changing inventory, services or prices.

## Physical movement and door proof

The old painted-wall routes now leave Caelan visible beside the building:

- Mill: [before](before_mill_left_wall_perimeter_native.png),
  [after](after_mill_left_wall_perimeter_native.png),
  [actual walk](after_mill_left_wall_actual_walk_native_resolution.gif).
- School: [before](before_school_west_wall_perimeter_native.png),
  [after](after_school_west_wall_perimeter_native.png),
  [actual walk](after_school_west_wall_actual_walk_native_resolution.gif).

[Eight recorded perimeter traces](perimeter_movement.json) cover walking/running
and both directions. Native-resolution GIFs are palette-indexed; PNGs retain
exact RGB. The full fixture passes all 63 movement/door/road checks, including all
13 ordinary entry/return roundtrips, maximum-width PR2 crossings and actual
southern departure/return. Resident and companion ownership is unchanged; no NPC
was deleted or teleported to make the checks pass. Every door's reversible
states also pass an actual-scene assertion that only its registered portal
changes. Selected full native states are retained for Mira, mill and school.

## PR2 and unchanged-state preservation

[Upper bridge](preserved_upper_bridge_native.png),
[main bridge](preserved_main_bridge_native.png), and
[mill landing](preserved_mill_landing_native.png) retain their exact selected
assemblies. All crossing source/rail assets, all town ground chunks, collision
and navigation are byte-identical to PR2. Native ground still equals the opaque
walk surface through every water phase and Reduced Motion. Full-width routes,
rail layering, seeded companion following and Continue checks pass.

Door records, physical canvases, baselines, streets, NPC/quest/household records,
services and the repaired southern exit are preserved. See
[actual southern return](after_actual_southern_return_native.png) and
[the business lane](after_southern_lane_native.png). Regional/detailed antler
views remain byte-identical to PR2. No town antler or shadow is reintroduced.

The prior full 137-test run passed, including all 14 settlement framework checks and all 6 school checks. On current main `e13a9846`, 92 focused checks passed, including all 22 Lantern-rest tests. Both upstream Lantern files are preserved byte-for-byte; they do not overlap PR3 files. 843 town outputs regenerate unchanged, all 826 native export hashes remain identical, and a fresh 191-view static Game capture matches the prior RGB buffers exactly. The longer 63-check scripted movement/movie pass was not repeated; fresh focused tests still exercise real wall, door-state, crossing and Continue behavior.

[Validation and intentional-diff details](validation.json) records the exact
checks. Passing tests do not constitute owner visual approval. This is scoped
local candidate evidence, not a claim of publication or merge.

## Historical source evidence

The prior [cottage board](before_authored_family_historical.png),
[landmarks](before_authored_landmarks_historical.png), and
[businesses](before_authored_businesses_historical.png) are preserved as labelled
historical AUTHORING evidence. They are not native gameplay screenshots.

## Reproduce

```
python tools/eldenmere_architecture_art.py --check
python tools/eldenmere_crossing_art.py --check
python tools/build_eldenmere_exteriors_hd.py --check
python tools/build_eldenmere_business_exteriors_hd.py --check
python tools/build_eldenmere_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_architecture_art test_eldenmere_exterior_integration test_eldenmere_architecture_review test_eldenmere_crossing_integration test_eldenmere_hd_integration test_town_southern_exit test_town_services
python tools/capture_eldenmere_architecture_audit.py /tmp/eldenmere-exterior-review --fixture docs/reviews/eldenmere_exterior_architecture/gameplay_fixture.json --movement
```
