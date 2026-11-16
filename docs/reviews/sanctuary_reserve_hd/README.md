# Sanctuary reserve native-detail migration

The reserve exterior/cave approach, public hall and visitor relief room now use
2× environment artwork at their established logical sizes. A retained new
12-object master supplies the hall, cloister roof/arches/columns, entrance arch,
limestone cave/ridges, basin, memorial tree, crystals, ceremonial table and stele.
Current native terrain, vegetation and furnishing banks supply the other assets.
Existing character bodies and approved story performances retain their banks;
caretaker pails use explicit native replacements. The dungeon interior is outside
this migration.

All three collision files remain byte-identical. Entrances, spawns, world links,
full player footprint, NPC/quest stations, inspection approaches, furniture
footprints and grass roots/phases remain unchanged. New silhouettes never define
collision. The memorial tree retains three sorted layers. A retained monochrome
architecture-coverage source keeps the cloister's original openings clear around
the story cast, while visible stone color/detail comes from the new drawing.
Decorative crystals preserve an empty cave mouth. The story-controlled keeper
rail retains its identity and removal lifecycle.

These are actual 960×640 Game captures from a disposable initialized exploration
fixture. Subsequent walking/running, route traversal and four door transfers use
production movement and doors. The separately initialized arrival preview uses
the actual story director and acknowledged dialogue through completion. No
player journey or settings file is modified.

- [Entrance](arrival.png), [memorial grove](grove.png), [caretaker](caretaker.png),
  [watering](caretaker_pour.png), [cloister](cloister.png), [survey](survey.png).
- [Cave approach](cave_approach.png), [closed entrance](cave_closed.png),
  [open entrance after arrival](cave_open_after_arrival.png).
- [Hall remembrance table](hall_remembrance.png), [records](hall_records.png),
  [relief room](relief_room.png), [rest offer](relief_rest_offer.png).
- [Actual walk](entrance_walk.gif), [actual run](entrance_run.gif),
  [reduced motion](reduced_motion.png).
- Actual arrival preview: [entrance](arrival_story_0.png),
  [care scene](arrival_story_1.png), [cave handoff](arrival_story_7.png).

Visual review checked physical scale, fixed stone/furniture supports, canopy and
cloister occlusion, cave clearance, steady windows/lamps, caretaker pail/stream,
inspection/rest cues and character readability. GIFs share one fixed palette;
PNGs retain authoritative native color/detail. Small repeatable inspections and
the relief bed use controller-driven cues; ordinary buildings/crystals do not.

`observations.json` records movement traces, actual door transitions, the live
rest offer, completed arrival preview and renderer measurements. Thirty warm
world draws per view measured approximately 0.9–2.8 ms on this SDL dummy execution
environment, excluding simulation/display UI. Peak capture-process RSS was about
820 MiB. Ground chunks use the existing 48 MiB scene cache (about 15 MiB resident
in the fully visited exterior). These are fixture measurements, not a hardware
performance guarantee.

**176 distinct checks passed** across `environment_checks.json` (79) and
`story_checks.json` (97). `final_source_checks.json` records nine final native/source
checks after isolating the unchanged architectural coverage into its retained
monochrome source. All 343 exports verify reproducibly.

Validation reports cover native assets, byte-preserved geometry, full-foot flood
connectivity, real walking/doors, save/Continue, relief rest, discovery cues,
particle/cache bounds, reduced motion/focus, MQ03, arrival props/cast and rescue
lifecycle. Legacy visual tests now inspect current native source/presentation
rather than the retired 1× bank or exact old leaf gaps. A pre-existing relief
fixture failure was reproduced on unmodified main `526ad26a`: it attempted free
movement during the mandatory arrival scene. The fixture now acknowledges that
scene and the first cave-entry exchange, retaining the actual guest roster and
phase-appropriate music. Production story locks were not weakened.

Reproduce:

```sh
python tools/build_sanctuary_reserve_hd.py --check
python tools/capture_sanctuary_reserve_hd.py /tmp/reserve-review
python tools/check_eldenmere_hd.py test_sanctuary_reserve_hd test_sanctuary_reserve_geometry test_reserve_free_roam test_sanctuary_reserve_hall test_sanctuary_relief_map test_sanctuary_reserve_travel test_sanctuary_reserve_life test_sanctuary_fantasy_scene test_sanctuary_atmosphere test_sanctuary_depth test_sanctuary_grass test_sanctuary_reserve_map
```

The [central terrain guide](../../TERRAIN_ART_STANDARD.md#integrated-elden-vale-sanctuary-reserve)
owns the maintained build/registration workflow; this folder records evidence.
