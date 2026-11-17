# Eldenmere roof-style restoration

The original paired review below is pinned to main `3481e2b7` (through
Serene's courtyard #254). The implementation is now rebased over main
`b47b027d804a167d30988b56c0fb9650a89f48fe`, preserving the independently merged
workshop/mill yards #255. See [current-main follow-through](#current-main-follow-through-255)
for fresh current-base evidence. The original comparisons remain historical,
explicitly #254-pinned; they are not claimed as captures of the #255 yard dressing.
The historical references are the **actual 24px bank**, recovered from
`7cebbd6006a1d925163ffe607443059ffff79880`, immediately before the HD exterior
bank. They are not the pre-audit HD drawings. Their exact Git paths and hashes
are recorded in [validation.json](validation.json).

## Style comparison

[Historical / main-before / revised at common native gameplay scale](historical_before_revised_native_scale.png)
compares the old cottage, workshop and mill with the current audited shells.
The historical drawings alone are enlarged 2× with nearest-neighbor for a fair
world-scale comparison. The before/revised drawings are native 2× source art;
this board is **not gameplay**. The preserved [school](reference_school_24px.png)
and [household](reference_sanctuary_24px.png) references also informed the pass.
The inn and item shop debuted in the HD bank, so they adopt this material language
without pretending to have 24px predecessors.

The existing four roof ramps were already close to the old palette. The main
regressions were rectangular slabs, an intrusive ridge across the upper quarter,
and busy fragments sampled from the HD concept sheet. The revision instead
uses native-authored staggered slates/terracotta tiles, restrained whole-shingle
value variation, fine bevels, overlapping lower lips, dark edge/timber fascia,
tapered pitched ends and a narrow top cap. The mill has two separately shaded,
sloping wings and a front gable rather than another generic slab. No enlarged
legacy pixels or sampled HD shingle fragments supply the new material.

The roof envelopes retain the audited depth, eave contacts and occupied-ground
contract. This does **not** revert the modern walls, building sizes, hearth/flue
positions, doors, interior art, or current courtyard to the 24px implementation.

## Actual native Game views (#254-pinned)

[Before/revised native Game crops](gameplay_before_revised_native_crops.png)
arranges unscaled crops from the initialized production `Game.draw` buffers.
The crops do not substitute art, actors or ground. The raw before views for
[Halden](before_halden_native.png), [Mira](before_mira_native.png),
[mill](before_mill_native.png) and [Serene's household](before_sanctuary_native.png)
remain full 960×640. Every after view below is also an unmodified 960×640 buffer.

| Live building | Native normal | Native Reduced Motion |
| --- | --- | --- |
| Halden | [View](after_halden_normal_native.png) | [View](after_halden_reduced_native.png) |
| Elira | [View](after_elira_normal_native.png) | [View](after_elira_reduced_native.png) |
| Venn | [View](after_venn_normal_native.png) | [View](after_venn_reduced_native.png) |
| Home A | [View](after_home_a_normal_native.png) | [View](after_home_a_reduced_native.png) |
| Home B | [View](after_home_b_normal_native.png) | [View](after_home_b_reduced_native.png) |
| Home C | [View](after_home_c_normal_native.png) | [View](after_home_c_reduced_native.png) |
| Liam's household | [View](after_liam_house_normal_native.png) | [View](after_liam_house_reduced_native.png) |
| Mira | [View](after_mira_normal_native.png) | [View](after_mira_reduced_native.png) |
| Mill | [View](after_mill_normal_native.png) | [View](after_mill_reduced_native.png) |
| School | [View](after_school_normal_native.png) | [View](after_school_reduced_native.png) |
| Serene's household | [View](after_sanctuary_normal_native.png) | [View](after_sanctuary_reduced_native.png) |
| Inn | [View](after_inn_normal_native.png) | [View](after_inn_reduced_native.png) |
| Item shop | [View](after_item_shop_normal_native.png) | [View](after_item_shop_reduced_native.png) |

[The downscaled index](all_thirteen_DOWNSCALED_INDEX.png) is a navigation aid,
not evidence of fine native detail. Review checked the complete silhouettes,
shingle courses and palette at Caelan's scale, including the mill wing/flue/hoist
contacts, school bell, Serene's retained bell and latest courtyard, roof patches,
and the shop awning/display.

The [fixture](gameplay_fixture.json) records fixed player, camera and clock
positions. Survey images explicitly use the production CameraDirector to frame
tall roofs. These are disclosed initialized-Game review fixtures, not an
uninterrupted story playthrough. Movement uses ordinary `Game.update` with the
unchanged full foot probe and existing actors; no NPC is deleted for the check.

## Preservation and verification (#254-pinned)

- 193 native Game views, including 192 exact before/after fixtures. All fixture
  player/camera/clock/door fields agree. All 29 paired interior views and both
  regional/detailed landmark views are pixel-identical to main.
- 63 actual movement checks pass, including all 13 building entry/return trips,
  full-width crossings, walking/running in both directions, and actual southern
  departure/return. Three crossing Continue checks preserve exact journey state.
- All 13 architecture metadata records and pane masks are exact. Structure
  differences are confined to roof envelopes and the removed legacy cap overrun.
  Window light and smoke retain their separate ownership; roof structure stays
  fixed in Reduced Motion.
- Architecture schedule, wall/door registrations, every town ground chunk,
  collisions, navigation, interiors, crossings, streets, courtyard placement,
  NPC/quest records, services and gameplay code are unchanged. The playable map
  and settlement manifest only refresh exterior-source manifest hashes.
- 154 focused regressions pass across architecture, live rendering/doors,
  crossings, HD integration, interiors, settlement framework, streets/courtyard,
  southern travel and services. Memory-heavy checks ran in isolated processes
  after two aggregate runs were killed by memory pressure. The full repository
  suite was not run.
- The four exporters regenerate exactly: 122 architecture, 1,301 exterior,
  535 business and 955 town products verified with `--check`.

[Validation](validation.json) includes historical provenance, paired pixel
hashes, scope checks and current check results. Full observation/trace records
are retained as [before](gameplay_before_observations.json) and
[after](gameplay_after_observations.json). Tests are technical evidence, not a
claim of owner visual approval.

## Reproduce

```sh
python tools/eldenmere_architecture_art.py --check
python tools/build_eldenmere_exteriors_hd.py --check
python tools/build_eldenmere_business_exteriors_hd.py --check
python tools/build_eldenmere_hd.py --check
python tools/capture_eldenmere_architecture_audit.py /tmp/roof-review \
  --fixture docs/reviews/eldenmere_roof_style/gameplay_fixture.json --movement
```

Before captures use the same command/fixture against unmodified `3481e2b7`.
Disposable journey/settings files keep the user's saves untouched.


## Current-main follow-through (#255)

The rebase retains **all** workshop/mill yard sources, current earth/flat-shaving
pixels, four props, additive collision supports, navigation, workstations,
quest staging and the previous courtyard. The only current live-map JSON changes
are refreshed exterior-manifest provenance hashes. The four overlapping generated
outputs were recomposed with the current town builder, not selected from the
older #254 build. Roof art/code and historical 24px references are unchanged.

[Current-main before/revised comparison](main255_before_revised_native_crops.png)
uses unscaled native Game crops. Raw current-main before images are retained for
[Mira](main255_before_mira_native.png) and [mill](main255_before_mill_native.png).
The revised current-base surveys retain both [Mira normal](main255_after_mira_normal_native.png)
and [Reduced Motion](main255_after_mira_reduced_native.png), plus
[mill normal](main255_after_mill_normal_native.png) and
[Reduced Motion](main255_after_mill_reduced_native.png).

| Fresh current-base yard detail | Normal | Reduced Motion |
| --- | --- | --- |
| Workshop front | [View](main255_workshop_front.png) | [View](main255_workshop_front_reduced.png) |
| Workshop west | [View](main255_workshop_west.png) | [View](main255_workshop_west_reduced.png) |
| Mill landing | [View](main255_mill_landing.png) | [View](main255_mill_landing_reduced.png) |
| Mill service side | [View](main255_mill_service.png) | [View](main255_mill_service_reduced.png) |

Fresh verification compares 192 exact static fixtures against unmodified #255
main. All player/camera/clock/door fields match, with no capture failures. The
workyard-specific driver passes 16 walk/run movement routes and four actual
workshop/mill doorway roundtrips. Save/Continue preserves all four unique solid
props, flat patch, supports, courtyard and quest/party/inventory/flags. Each of
the four detailed Reduced Motion views remains pixel-identical after 600 ms.
The complete 947-file production input snapshot matches the integration commit.
122 focused current-base regressions pass across roof rendering, workyards,
HD integration, settlement framework, streets/courtyard, crossings, southern
travel and services. HD gameplay checks used isolated processes after a combined
process hit memory pressure during capture. The current composer (955 products),
standalone settlement report, retained workyard-prop exporter (4 products), and
native architecture exporter (122 products) pass their reproducibility checks.

[Current validation](main255_validation.json) records current-base comparisons,
map-field preservation and rerun checks. [Workyard observations](main255_workyard_observations.json)
retain full actual input traces, doorway and Continue evidence. The original
63-check #254 movement pass above is retained as historical evidence, not relabelled
as a new #255 pass. Full repository-suite testing is not claimed.

```sh
python tools/export_eldenmere_workyard_props.py --check
python tools/eldenmere_settlement.py --check
python tools/build_eldenmere_hd.py --check
python tools/capture_eldenmere_workyards.py /tmp/roof-workyard-review
```
