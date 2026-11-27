# Cinder Isles — dormant main volcano, bridges and billowing smoke

The main isle now has substantial coastal terraces around its dormant volcano,
with space for the future Veinhold and reservoir. The main crater has no lava
or eruptive fire because the facility is draining its Fire-aspected aether.
The smaller distant volcano remains active. Two large steel bridges connect
the main island to Merovar and Othara's Damar Drylands, with landings and piers
scaled to their respective perspectives.

- [Updated production preview](shot01.mp4)
- [Reduced Motion preview](shot01_reduced_motion.mp4)
- [Full sequence filmstrip](filmstrip.png)
- [Animated-plume detail filmstrip](smoke_filmstrip.png)
- [Vista at 20 seconds](shot01_600.png)
- [Actual Gallery replay](gallery_replay.png)
- [Complete entry](gallery/complete_selected.png)
- [Individual entry](gallery/shot_selected.png)

The sequence still lasts **25 seconds**: 15 seconds to crest and ten seconds
for the island view. The vista source window shifts down to y50 to retain the
near Merovar bridge's mainland landing. The island, bridges, coast and approach
remain in one continuous painting, preserving their relative movement. The
fortress/reservoir close-up remains a subsequent shot's work.

Both volcano mouths now emit animated textured billows. Main-island steam is
lighter; distant active ash is denser. Billows rise, expand, vary their drift
and dissolve, rather than moving a static painted plume. Their source-art
anchors use exactly the same projection as the terrain. Pause/focus freeze the
shot clock; restart reconstructs the same prewarmed plumes. Reduced Motion
lowers lateral turbulence while retaining visible billowing.

The new source panorama and cloud atlas, exact prompts, hashes and recipes are
retained under `assets/source/cinematics/fire_veinhold/shot01/environment/`.
The exporter isolates one complete authored cloud with transparent margins
from the atlas; particle growth, advection and alpha provide its animation.
The panorama itself has no baked smoke. Native runtime frames at 15/16/17s
were inspected in the plume filmstrip, alongside full views for both bridge
landings, terrain space, crater state, plume alignment and image edges.

## Verification

**157 targeted tests passed**, including deterministic particle growth/fade,
visible motion from both emitters, bounded seeks, invalid emitter rejection,
clock/focus/restart behavior, terrain registration and the existing controller,
Gallery, save/settings, Ice Reaper and opening-retirement regressions. See
[complete output](tests.log). Twenty unrelated Gallery thumbnails and records
remain byte-identical to the preceding main revision.

Both movies contain **750 actual production Game.draw frames at 30 Hz** in a
960×640 Gallery viewport, with natural completion and no save/settings writes.
Their capture JSON records exact scene/runtime hashes, including
`cinematic_smoke.py`. Audio remains the existing production cue reconstruction;
this is not a hardware-loopback listening claim.

Reproduction:

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest \
  tests.test_cinematic_smoke tests.test_fire_veinhold_opening \
  tests.test_prologue_eagle_assets tests.test_prologue_mountain_export \
  tests.test_prologue_flight_audio tests.test_gallery_catalogue \
  tests.test_gallery_ui tests.test_gallery_session tests.test_cinematic_player \
  tests.test_ice_reaper_opening tests.test_opening_retirement -v
python tools/build_prologue_mountains.py --check
python tools/capture_fire_veinhold_opening.py
python tools/capture_fire_veinhold_opening.py --reduced-motion
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --out docs/reviews/cinder_bridges_smoke/gallery
```

The [scene owner](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md) records the
rendering/staging contract; the [Cinder Isles owner](../../narrative/world/POLAR_REGIONS.md#cinder-isles)
records the dormancy and crossings. The canonical world-map image and current
playable quest routes are unchanged. Previous capture folders retain their
historical revisions. New Game continues to use the bedroom until the full
prologue and playable handoff are ready.
