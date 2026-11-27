# Fire Veinhold orbit, alarm and frozen bridge

The complete Gallery presentation extends the existing eagle opening to 39
seconds. Its production controller uses the same five-shot list for the complete
film and individual previews. The [scene owner](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md)
records the approved staging and future party-reveal shots.

## Review outputs

- [Complete production film, 60 FPS](complete.mp4)
- [Complete Reduced Motion film, 60 FPS](complete_reduced_motion.mp4)
- [Complete sequence contact sheet](complete_filmstrip.png)
- [Reduced Motion contact sheet](complete_reduced_motion_filmstrip.png)
- [Eagle approach and vista](shot01.mp4)
- [301-perspective island orbit](shot02.mp4)
- [Orbit checkpoints, including both endpoints](shot02_camera_contact_sheet.png)
- [Four-second alarm lead-in](shot03.mp4)
- [One-second bridge rush](shot04.mp4)
- [Frozen Carcovian guards](shot05.mp4)

Every movie is captured through production `Game.draw` in the disposable,
save-disabled Gallery at native 960×640. The complete movie contains 2,340
displayed frames at 60 FPS. The orbit's 301 inclusive camera samples describe
300 intervals, exactly five seconds; sample 300 supplies the next shot's camera
pose instead of adding another display interval. The one-second rush likewise
has 61 inclusive samples. Four seconds of visible/audible alarm precede the rush.

The offline scene combines shared island/fortress geometry and painted surfaces,
a limited opening relief over the first three degrees, and four complete frozen
guard drawings placed on independent rigid RGBA planes at calibrated depths.
The final framing clearly shows **three guards**; the source contains four
staged guard planes. The scene meets the brief's several frozen soldiers without
claiming that all four authored planes produce separately visible figures.
The bridge/deck background is separate from those character silhouettes. These
are camera renders of a spatial composition, rather than 301 independently
painted angles. Smoke reuses the complete approved plume drawings on
vent-anchored, camera-facing surfaces with depth occlusion; no volumetric fluid
simulation or physically fixed plume-wind direction is claimed.

Capture JSON beside each movie records actual frame count, full-reel clip
offset, representative scene states, source/runtime hashes, natural Gallery
completion and absence of persistent journey/settings writes. Audio is an
**offline reconstruction** from production WAVs, gain/pan curves and global cue
phase at unit effects volume. Live capture effects are muted. It is not mixer
hardware loopback or a claim of listening through a physical output device.
Visual frames come from the live presentation path.

Performance metadata reports measured SDL-dummy draw/update times, Gallery
startup, decoded perspective-cache bytes and the bound including pending-load
reservations (24 slots, at most 56.25 MiB, plus temporary drawing/conversion
buffers). Cache wait counts and empty completion state are recorded separately.
Encoder writes and review stills are excluded from frame timing. These are measurements on the capture
machine, not a hardware-independent 60 FPS guarantee.

The separate [production playback profile](production_profile.json) measures
controller updates plus native rendering for the 14-second continuation;
it excludes Gallery UI/scaling, video encoding and the preceding 25 seconds.
The 840-frame run averaged **6.27 ms**, with **11.15 ms p95** and no foreground
decoder waits. The rush's p95 was **12.81 ms** and maximum **15.96 ms**. One
reveal frame took **17.66 ms**, exceeding the 16.67 ms budget; the other 839
frames remained within it. Peak recorded cache reservations were **54.5 MiB**.
The JSON records the exact playback conditions and source/art fingerprints.

[Capture validation](capture_validation.json) verifies all seven movies' native
dimensions, exact durations and 60 FPS frame counts, all three pixel-exact RGB
camera joins, current source/runtime/movie hashes, empty caches at completion,
and natural Gallery return without persistent writes. The six updated Gallery
thumbnails preserve all **20 unrelated PNGs** and **19 existing unrelated
provenance records** unchanged. Visual review includes the thirteen orbit
checkpoints, the rush filmstrip and the final bridge composition.

## Verification

**169 tests passed** across thirteen distinct modules: **100 core checks**
for cinematic timing, streaming, audio, assets and integration, plus **69 Gallery
checks** for all 26 registered entries, persistent state isolation, controls,
layout and actual fixture completion. See [core output](core_tests.log) and
[Gallery output](gallery_tests.log). All seven capture verifications passed;
compilation, source/asset reproduction checks and whitespace validation passed.

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest \
  tests.test_cinematic_perspective tests.test_veinhold_continuation \
  tests.test_prologue_alert_audio tests.test_prologue_flight_audio \
  tests.test_fire_veinhold_opening tests.test_cinematic_facility \
  tests.test_cinematic_smoke tests.test_prologue_mountain_export \
  tests.test_prologue_eagle_assets tests.test_prologue_capture -v
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest \
  tests.test_gallery_catalogue tests.test_gallery_session tests.test_gallery_ui -v
```

## Reproduction

Run from the repository root with pygame, numpy, Pillow and ffmpeg available:

```sh
python tools/capture_fire_veinhold_opening.py --fps 60
python tools/capture_fire_veinhold_opening.py --fps 60 --reduced-motion
python tools/capture_fire_veinhold_opening.py --shot-id eagle_ascent --fps 60
python tools/capture_fire_veinhold_opening.py --shot-id island_orbit --fps 60
python tools/capture_fire_veinhold_opening.py --shot-id alarm_hold --fps 60
python tools/capture_fire_veinhold_opening.py --shot-id bridge_rush --fps 60
python tools/capture_fire_veinhold_opening.py --shot-id frozen_bridge --fps 60
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --scene fire_veinhold_shot_02 --scene fire_veinhold_shot_03 \
  --scene fire_veinhold_shot_04 --scene fire_veinhold_shot_05 \
  --out docs/reviews/veinhold_orbit/gallery
```

Focused capture tests protect late-clip offsets, alarm onset, representative
thumbnail timing for the short rush and playable movie boundaries. Gallery
catalogue tests cover individual/complete fixtures, natural completion,
thumbnail metadata and isolation from persistent gameplay. Earlier review folders retain their
recorded versions.
