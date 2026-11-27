# Fire Veinhold wide reveal and replacement drawn smoke

The existing 25-second shot now reveals the Fire Veinhold on the front-right
terrace of the main Cinder island: a basalt/steel/bronze fortress with braced
lower-flank extraction works, two reinforced amber conduits, a circular ember
containment reservoir, command keep, walls, barracks and connected gatehouses
at both bridge approaches. The main crater remains dark and dormant; only the
distant volcano retains eruptive glow.

- [Full production preview](shot01.mp4)
- [Magnified smoke review clip](plume_detail.mp4)
- [Reduced Motion preview](shot01_reduced_motion.mp4)
- [Wide-shot filmstrip](filmstrip.png)
- [Registered plume frame filmstrip](plume_filmstrip.png)
- [Fortress view at 20 seconds](shot01_600.png)
- [Actual Gallery replay](gallery_replay.png)
- [Complete entry](gallery/complete_selected.png)
- [Individual entry](gallery/shot_selected.png)

The closer facility view remains a future shot. This change adds the fortress
to the current wide composition while retaining the 15-second ascent and ten
seconds to take it in. The camera widens slightly at the crest to fit the
expanded complex and near bridge landing, then makes a restrained push.

## Smoke replacement

The old emitted-puff implementation and runtime `smoke_puff.png` are removed.
Both vents now use **16 complete drawn plume frames**, with explicit mouth
registration on a shared 256×256 canvas. Each drawing has clean transparent
margins, and the plume remains attached to its crater throughout its four-second
cycle. Main steam is lighter; distant ash is denser and uses a different phase.
The loop slows under Reduced Motion and freezes with pause/focus loss.

A first atlas failed boundary inspection because clouds overlapped neighboring
cells. It was rejected and used only as the reference for a redrawn, separated
atlas. Its final source cells are alpha-cleaned and sampled on one fixed canvas,
then registered by their vent landmarks. Source images, exact prompts, hashes,
registration and export recipe remain in the environment source folder.

Adjacent frames blend in **premultiplied alpha**, avoiding rectangular PNG
backgrounds and the opacity dip caused by overlapping ordinary cross-fades.
The effect does not translate, emit or despawn copies of a puff. The native
plume filmstrip was inspected for fixed vent positions, evolving cloud shapes,
clear backgrounds and loop framing. The smoke review movie is an eight-second
magnified crop of the actual production capture, not a different animation.

## Facility effects

Slow red beacon highlights establish an emergency on gatehouses and reservoir
towers. Amber packets move down both authored conduit paths toward the basin;
floating ember accents stay inside its interior. The architecture and windows
remain steady. Reduced Motion uses steady warning lights and static power
accents. All effects share the panorama projection and shot clock.

## Validation and reproduction

**161 targeted tests passed.** See [complete output](tests.log). Coverage includes
transparent frame boundaries, hidden RGB remaining invisible, premultiplied
interpolation retaining opacity, fixed plume anchors and loop/seeking behavior,
both visible plume cycles, conduit direction, distinct red/amber signals,
Reduced Motion, and existing Gallery/save/settings/cinematic regressions.
Twenty unrelated Gallery thumbnails and metadata records remain unchanged.

Normal and Reduced Motion captures each contain 750 actual production
`Game.draw` frames at 30 Hz in a native 960×640 Gallery viewport, with natural
completion at 25 seconds. Their JSON records pin current runtime/art hashes,
including both VFX modules. Movie audio remains the production cue
reconstruction; hardware-loopback listening is not claimed.

```sh
PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m unittest \
  tests.test_cinematic_smoke tests.test_cinematic_facility \
  tests.test_fire_veinhold_opening tests.test_prologue_eagle_assets \
  tests.test_prologue_mountain_export tests.test_prologue_flight_audio \
  tests.test_gallery_catalogue tests.test_gallery_ui tests.test_gallery_session \
  tests.test_cinematic_player tests.test_ice_reaper_opening \
  tests.test_opening_retirement -v
python tools/build_prologue_mountains.py --check
python tools/capture_fire_veinhold_opening.py
python tools/capture_fire_veinhold_opening.py --reduced-motion
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --out docs/reviews/veinhold_reveal/gallery
```

The [scene owner](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md) records current
presentation; the [Cinder Isles owner](../../narrative/world/POLAR_REGIONS.md#cinder-isles)
records approved architecture and geography. Previous reviews retain their
historical versions. New Game remains the bedroom morning until the full
prologue and playable handoff are ready.
