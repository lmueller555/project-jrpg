# Eldenmere — first terrain and building-placement pass

Status: review. This is the first assembled view of the approved town design using existing native artwork. It covers 64×56 tiles at 24px, native 1536×1344. It is a scene composition for layout review, not a runnable game map.

## Review

- `town_review.gif`: enlarged 2× overview, 3072×2808 including captions, 18 frames at 200ms = 3.6 seconds, looping.
- `town_review.png`: corresponding still.
- `labeled_layout.png`: full-size still with household names, commons, crossings, eastern steps, jammed gate and woodland connection.
- `scale_checks.png`: eight separate 3× Caelan snapshots at sanctuary steps, upper bridge, Halden's door, Elira's door, eastern steps, Venn's door, mill landing and main bridge. The same character is repeated for review; these are not extra actors in the village.
- `town_native.png`, `frames/`: clean native scene and all eighteen native animation frames.
- `layers/`: grass, 47-state paths and fixed masonry.
- `navigation/`: conservative foot-probe blockers, intended-route mask and reached probe centres.
- `scene.json`: source packs, native registrations, channels, fall/bridge/stair placements, animation clocks and access checks.
- `adapted_plan.json`: the approved plan with the documented native-art fitting changes.

The sanctuary and workshop use clearly marked measured placeholders. The mill and six cottages retain their exact native art sizes. Doors stay closed; chimney smoke, lanterns, water, spillways, bridge wakes and the mill animate. The Venn gate remains jammed, with reduced downstream flow. The independent brook and mill keep running.

The original district arrangement is preserved. The eastern approach now uses the existing south-facing stairs, the mill race is aligned to the source wheel/landing, the northern cascade stays straight, and doorway paths follow the actual exported centres. See the [retained recipe notes](../../../source/maps/eldenmere/terrain_foundation/README.md) for coordinates and rationale.

The commons and yards retain open walking/gathering space. Garden/field spaces are cleared earth reserves awaiting later dressing. Trees, shrubs, crops, fencing, festival decorations, final sanctuary/workshop art, new quest props and NPC staging are future passes. Interiors remain separate maps. No engine collision, door transitions, quest triggers, camera or live movement is implemented in this export.

Source assets and the approved blockout are unchanged. This scene awaits user review before merging into main.
