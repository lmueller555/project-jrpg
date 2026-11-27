# Fire Veinhold opening — Shot 1

Implemented the ten-second eagle ascent, with detailed source art and a new
production renderer. The Gallery offers the individual shot and a complete
cutscene entry driven by the same implemented-shot list. There is currently
one finished clip. The new prologue does not yet replace the bedroom New Game.

The [production scene guide](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md)
owns the storyboard, shot boundaries and later-shot integration contract.

## Review captures

- [Normal-speed shot with reconstructed audio](shot01.mp4)
- [Reduced Motion with reconstructed audio](shot01_reduced_motion.mp4)
- [Six-frame ascent filmstrip](filmstrip.png)
- [Actual Gallery replay](gallery_replay.png)
- [Complete entry selected](gallery/gallery_complete_selected.png)
- [Individual entry selected](gallery/gallery_shot_01_selected.png)
- [Complete-entry replay frame](gallery/regional_fire_veinhold_opening.png)
- [Individual-entry replay frame](gallery/regional_fire_veinhold_shot_01.png)

Both movies contain 300 actual production `Game.draw` frames at 30 Hz, with an
exact 960×640 replay viewport inside the isolated Gallery session. The toolbar
is outside that viewport. The frame clocks run normally and reach natural
completion at 10s, returning to the catalogue without writing journey/settings
files. The filmstrips show 0/2/4/6/8/9.97s. Capture JSON files retain shot states,
runtime/source hashes, audio cue times, video hashes and completion facts.

Audio in these movies is an **offline reconstruction** from the same production
WAVs, wind gain/panning and downstroke/cue metadata; it is not hardware loopback.
This review includes actual pygame decoder/channel smoke checks and numerical
peak/clipping checks, without claiming physical speaker/headphone listening.

## Visual checks and corrections

Inspected the complete eagle flap/bank drawings, numbered pose sheets and
normal/slow preview sequences retained with the source pack. Both wings have
complete authored motion, tucked feet and a stable head/chest/tail relationship.
The final exporter preserves one source sampling canvas rather than changing
sampling phase with wing bounds, and retains dark feather interiors during
alpha cleanup. The bank/glide joins share the level-wing pose.

The updated nighttime preview uses one opaque mountain-and-sky panorama and
one shared camera transform. This replaces the earlier six independently moving
mountain layers, whose relative movement gave inconsistent depth cues. Cool
moonlight and stars replace the sunrise, with corresponding cool eagle lighting.
Inspected the updated runtime filmstrip for terrain continuity and edge coverage.

The final frame retains camera velocity and an exposed handoff state rather
than easing to rest or fading to black. Shot2 must continue/cut from that state
to its future volcano/Veinhold reveal. The eagle reaches the central saddle at the end; Shot 2 will supply the view
beyond it.

## Validation

**Night revision: 24 focused tests passed** (controller, Gallery isolation and
environment exporter), including a regression check for one opaque panorama.
The earlier implementation passed **149 targeted tests**, covering:

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python -m unittest \
  tests.test_fire_veinhold_opening tests.test_prologue_eagle_assets \
  tests.test_prologue_mountain_export tests.test_prologue_flight_audio \
  tests.test_gallery_catalogue tests.test_gallery_ui tests.test_gallery_session \
  tests.test_cinematic_player tests.test_ice_reaper_opening \
  tests.test_opening_retirement -v
```

See [night revision output](night_tests.log) and [initial test output](tests.log). The new controller tests exercise exact 30/60 Hz
duration, genuine pre-boundary samples, pause/focus/skip/restart, native detail
through the live drawing branch, reduced-motion flight, camera continuity,
data-driven aggregate order, malformed asset recovery and atomic cache loading.
Gallery checks include every existing registered scene, both new entries,
existing 32s Ice Reaper playback and unchanged parent save/settings/Continue.

All three offline export reproduction checks pass:

```sh
python tools/build_prologue_eagle.py --check
python tools/build_prologue_mountains.py --check
python assets/source/audio/fire_veinhold/shot01/build.py --check
```

Compilation and whitespace checks pass. The two new thumbnail records pin the
current scene source hashes; the 20 previous records and PNGs remain unchanged.
This is a focused regression run rather than a claim that the entire repository
suite or a full playable Fire Veinhold mission has been tested.

## Reproduce the captures

```sh
python tools/capture_fire_veinhold_opening.py
python tools/capture_fire_veinhold_opening.py --reduced-motion
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --out docs/reviews/fire_veinhold_opening/gallery
```

Movie capture requires numpy, Pillow, pygame and ffmpeg. Both new Gallery
fixtures call `FireVeinholdOpening`; they contain no copied animation/story
script. Future shot PRs add their completed renderer/assets and ordered scene
record, producing another individual entry and extending the complete entry.
