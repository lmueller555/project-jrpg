# Eldenmere bridges and mill service landing

PR2 local candidate, based on PR1 commit `6de3a061`. These are actual initialized-Game captures, not construction diagrams or isolated artwork. Native PNGs are unmodified 960x640 world buffers from `Game.draw`; motion uses real `Game.update`, collision, actors and following camera. Static placements are disclosed review fixtures, not a continuous quest playthrough.

## Same-camera native comparisons

| Crossing | Before | After | Reduced Motion |
| --- | --- | --- | --- |
| Upper | [Before](before_upper_bridge_native.png) | [After](after_upper_bridge_native.png) | [Reduced](after_upper_bridge_reduced_native.png) |
| Main | [Before](before_main_bridge_native.png) | [After](after_main_bridge_native.png) | [Reduced](after_main_bridge_reduced_native.png) |
| Mill service | [Before](before_mill_landing_native.png) | [Complete dry landing](after_mill_landing_native.png) | [Reduced](after_mill_landing_reduced_native.png) |

Both bridge decks occupy their full spans: 144/168 logical units, rather than differently sized transparent canvases containing a similar small donor. Genuinely occupied rail lengths are 141/165 logical units. Walking surfaces are 48 units deep and 100% opaque. Far rails remain behind actors; near rails cover only appropriate lower portions. See [upper far edge](after_upper_bridge_far_rail_native.png), [upper near edge](after_upper_bridge_near_rail_native.png), [main far edge](after_main_bridge_far_rail_native.png) and [main near edge](after_main_bridge_near_rail_native.png).

## Actual movement

Native-resolution GIFs use an indexed palette; the accompanying PNGs retain exact native rendered RGB. No source art or replacement scenery was inserted.

- [Upper far-edge walk](after_upper_far_walk_native_resolution.gif), [native motion frame](after_upper_far_walk_actual_movement_native.png).
- [Main near-edge reverse run](after_main_near_run_return_native_resolution.gif), [native motion frame](after_main_near_run_return_actual_movement_native.png).
- [Mill east-apron approach fanning into doorway](after_mill_east_apron_fan_walk_native_resolution.gif), [native motion frame](after_mill_east_apron_fan_walk_actual_movement_native.png).

The unchanged player foot probe is 24x12 logical units. Upper bridge centers y=462/480/498 and main centers y=1014/1032/1050 traverse their maximal usable width. Mill apron centers x=960/971/984 fan at y=372 to x=971 before its existing narrow doorway throat. Straight x=978 at y354 was blocked before this PR and remains blocked. No probe shrinking, collision enlargement or entrance move hides that fact.

## Validation and intentional scope

- 55 focused tests pass, including 6 production-Game integration checks. 49 additional preservation tests pass; 4 upstream MQ02 route tests fail identically on unchanged 57d0613c. See [validation](validation.json), [preservation details](preservation_tests.json) and [baseline failure output](baseline_upstream_trigger_failures.txt).
- 842 town exports reproduce. The source bank uses authored repeated boards/posts/endcaps, not stretched donor drawings.
- 192 native views,63 real movement/door/road checks and 3 center-crossing Save/Continue checks have no failures or unsafe feet. This includes 36 maximal-width walking/running/bidirectional traversals, all 13 town door roundtrips and actual southern departure/return. A separately labelled seeded Rhea regression covers following and Continue with persistent state retained.
- Live runtime ground pixels equal the authored opaque deck in all 6 water phases and Reduced Motion. Water remains visible and animated beside the structures and freezes normally in Reduced Motion.
- Collision/navigation bytes and all existing map records remain identical. The town map only adds the mill foreground rail. Every changed ground-chunk pixel lies within one of the three crossing artwork canvases. Mill exterior changes are confined to the reassigned old fence fragment `[938,345,20,14]`; the complete landing owns that interface now. See [intentional diff](intentional_diff.json) and [capture metadata](selected_evidence.json).
- Regional and detailed Sanctuary antler native images remain byte-identical to PR1. Southern exit, service, door, quest, NPC, interior and upstream geometry are unchanged.

The mill roof mask and building-wall mismatches deliberately remain for PR3. Passing tests do not substitute for native visual review. This is local candidate evidence, not a claim of published or merged status.

## Reproduce

```
python tools/eldenmere_crossing_art.py --check
python tools/build_eldenmere_hd.py --check
PYTHONPATH=.:tests python -m unittest test_eldenmere_crossing_integration test_eldenmere_crossing_art test_eldenmere_architecture_review test_eldenmere_architecture_contracts test_town_southern_exit test_town_services
python tools/capture_eldenmere_architecture_audit.py /tmp/eldenmere-crossing-review --fixture docs/reviews/eldenmere_architecture_contracts/gameplay_fixture.json --movement
```

## Latest-main replay after #247 and merged PR1 #248

This replay preserves upstream settlement framework `8022e7d5` and the merged PR1 content. Local PR1 `3ac785c5` and actual merged main `af11ecb6` have the exact same tree, `d6b3c72c98d94eb4bec4eddaf5fad9588744515d`; the direct-main-parent candidate is content-equivalent to the locally replayed candidate.

**112 relevant tests pass**, including settlement protections and the actual-Game crossing/movement/Continue checks. **843 exports reproduce** with the new settlement report retained. All **114 protected spaces**, geometry/interfaces and **200 semantic asset records** are preserved with zero active settlement dressing. The report's source provenance is regenerated, not manually repinned. The only extra generated difference relative to the earlier PR2 replay is that settlement report metadata.

All **826 native export hashes** and the runtime town map match the earlier PR2 candidate exactly. A fresh **191-view native Game capture** matches every corresponding earlier frame byte-for-byte, with safe feet throughout. The earlier motion clips remain historical captured evidence of the exact same runtime assets; fresh real movement tests also pass. See [latest test report](latest_main_tests.json) and [latest preservation proof](latest_main_preservation.json). The four previously documented upstream trigger failures remain historical baseline findings, not failures of this 112-test selection.
