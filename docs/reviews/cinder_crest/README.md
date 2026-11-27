# Cinder Isles crest — 25-second opening shot

The eagle now starts closer to the summit, flies faster, clears the ridge by
15 seconds and leaves ten full seconds to take in the Cinder Isles. Both the
individual Shot 1 and complete-cutscene Gallery entries use this sequence.
New Game still retains the bedroom morning while the full prologue is unfinished.

- [Normal-speed production preview with reconstructed audio](shot01.mp4)
- [Reduced Motion preview](shot01_reduced_motion.mp4)
- [Six-frame filmstrip](filmstrip.png)
- [View at the 15-second crest](shot01_450.png)
- [Actual Gallery replay](gallery_replay.png)
- [Complete Gallery entry](gallery/complete_selected.png)
- [Individual Gallery entry](gallery/shot_selected.png)

The canonical map was inspected before authoring. Facing east-southeast from
Merovar's mountains southeast of Eldenmere, the painting shows mainland rock,
a broad open-water channel, the main red/black volcanic island, a smaller
active island farther beyond, southern skerries to the right and Othara's red
headlands on the distant left horizon. Istrava is outside the framing. The
[scene guide](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md) owns timing and
production details; the [Cinder Isles owner](../../narrative/world/POLAR_REGIONS.md#cinder-isles)
records the approved location without changing the map or assigning distances.

The new source is one opaque 1024×1536 moonlit panorama, preserving geographic
relationships through a single camera transform. A vertical source-window
move carries the camera from the near summit approach into the upper vista.
The closest ridge has passed beneath the main view at 15s. The scene then
continues with a restrained camera push while the eagle flies into the distance.
The main crater stays unobstructed. No independent mountain groups or terrain
cross-fades were reintroduced. Native frames at 0/5/10/15/20/24.97s were inspected
for framing, continuity, island separation and image edges.

Each movie captures **750 production Game.draw frames at 30 Hz**, in an exact
960×640 Gallery viewport, including natural completion at 25s and return to the
catalogue. Capture JSON retains runtime/art hashes, phase states and audio cue
times. Movie audio is reconstructed offline from the production WAVs and cue
metadata; hardware-loopback listening is not claimed. Wind continues across
the crest, with feather Foley on all 13 powered downstrokes and a crest gust
at 14.65s. The 750ms wing cadence remains unchanged by the longer scene.

## Verification

**152 targeted tests passed.** The final 21 controller tests also passed again
after adding malformed phase/framing checks. The broader regression run covers both Gallery entries and all retained Gallery scenes, save/settings
isolation, pause/focus/restart/skip, native-detail output, Ice Reaper playback,
and opening retirement. Results are retained in `tests.log`; final controller
metadata checks are retained in `controller_tests.log`.

The timing regression verifies ascent immediately before 15s, vista at exactly
15s, continued playback immediately before 25s, and one completion at 25s for
both 30/60Hz clocks. Framing checks verify that the upper vista is exposed at
the crest. Malformed phase lengths and non-finite source windows fail as
recoverable authoring errors. Twenty unrelated Gallery thumbnails and records
remain byte-identical to the previous main revision.

Reproduce from the repository root:

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest \
  tests.test_fire_veinhold_opening tests.test_prologue_eagle_assets \
  tests.test_prologue_mountain_export tests.test_prologue_flight_audio \
  tests.test_gallery_catalogue tests.test_gallery_ui tests.test_gallery_session \
  tests.test_cinematic_player tests.test_ice_reaper_opening \
  tests.test_opening_retirement -v
python tools/build_prologue_mountains.py --check
python assets/source/audio/fire_veinhold/shot01/build.py --check
python tools/capture_fire_veinhold_opening.py
python tools/capture_fire_veinhold_opening.py --reduced-motion
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --out docs/reviews/cinder_crest/gallery
```

The fortress/reservoir close-up remains the next shot's work. This revision
implements the geographic reveal and viewing time, rather than the entire
playable infiltration. Earlier review directories retain their historical
captures and results.
