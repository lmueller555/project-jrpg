# Fantasy Sanctuary — actual-game review

![Reserve and hall views](contact_sheet.png)

[Walking, running and standing](sanctuary_fantasy.mp4) · [Full reserve](reserve_overview.png) · [Hall overview](hall_overview.png) · [Local map](local_map.png)

[Placement and access diagram](placement_sheet.png) is explicitly annotated;
the other scene photographs remain unpainted production gameplay views.

The screenshots and silent movie use the production Game, character sprites,
camera and renderer. An ordinary disposable exploration journey walks from
Eldenmere through the normal overworld and Sanctuary contacts, visits the grove,
crystal cave, spring, woodland circuit and open grass, then enters the hall and
returns through the ordinary doors and exits. Long transit between demonstrations
is walked normally and omitted from the focused recording. Standing segments
continue real simulation so shimmer, foliage and atmospheric motion remain live.

The review covers walking and running, front/behind landmark views, reduced
motion, the cave's closed keeper rail, optional hall inspections and Save/Continue
in both scenes. Quests, inventory, party, character attributes, dialogue flags,
abilities and desired music remain unchanged. Temporary save/settings files
leave player journeys untouched. The full reserve image stitches bounded
production World.draw views; no scenery or character pose is painted into it.

[Verification](verification.json) retains actual positions, sprite visibility
observations, complete foot-probe connectivity and source/artifact fingerprints.
Reproduce with `python tools/capture_sanctuary_fantasy.py`; verify retained
evidence with `python tools/capture_sanctuary_fantasy.py --check`.

Final validation passes **248 tests and 4,036 subtests** across native asset
exports, landmark depth, reduced motion, audio ownership/error handling,
navigation, grass, party travel, quests, saves and Gallery sessions. Crystal,
grove, reserve, hall and miniature deterministic build checks pass. The retained
grass reviews were refreshed against the final scenery and runtime.

Both reserve and hall collision masks remain byte-for-byte identical to their
pre-expansion versions. All 96 interactive grass placements remain unchanged.
The final silent video is **43.35 seconds**, with **867 frames at 960 × 640 /
20 fps**. Source/artifact fingerprints and video metadata pass verification;
deliberately stale source records and changed artifacts are rejected.
