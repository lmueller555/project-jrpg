# Fire Veinhold running shot and faction identity

The production Gallery film now contains six shots over 42 seconds. The new
39–42s shot tracks the party's legs running across the steel bridge toward the
Veinhold. The [scene owner](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md)
records framing, formation, disclosure and faction appearance. The earlier
[39-second review](../veinhold_orbit/README.md) remains historical evidence of
its original film length and guard/banner palette.

## Review outputs

- [Small complete preview, 2.9 MB, 600×400 at 60 FPS](complete_small.mp4)
- [Complete production film, 960×640 at 60 FPS](complete.mp4)
- [Complete Reduced Motion film](complete_reduced_motion.mp4)
- [Complete sequence contact sheet](complete_filmstrip.png)
- [Reduced Motion contact sheet](complete_reduced_motion_filmstrip.png)
- [Running-party shot](shot06.mp4)
- [Running-party Reduced Motion shot](shot06_reduced_motion.mp4)
- [Silent quarter-speed running inspection](shot06_slow.mp4)
- [Running-shot production stills](shot06_filmstrip.png)
- [Eagle approach and updated fortress banners](shot01.mp4)
- [Island orbit and updated fortress banners](shot02.mp4)
- [Orbit camera checkpoints](shot02_camera_contact_sheet.png)
- [Four-second alarm lead-in](shot03.mp4)
- [One-second bridge rush](shot04.mp4)
- [Revised Carcovian frozen guards](shot05.mp4)
- [Faction banner comparison](faction_banner_comparison.png)
- [Faction uniform comparison](faction_uniform_comparison.png)
- [Lucan's numbered drawings](lucan_drawn_contact_sheet.png) and [boots](lucan_boots_contact_sheet.png)
- [Iselin's numbered drawings](iselin_drawn_contact_sheet.png) and [boots](iselin_boots_contact_sheet.png)
- [Crown soldier's numbered drawings](crown_soldier_drawn_contact_sheet.png) and [boots](crown_soldier_boots_contact_sheet.png)

The small video retains all 42 seconds, 2,520 displayed frames, 60 FPS and audio.
Download it and open it in QuickTime, VLC or a browser to review outside the
game. It is a compressed derivative of the native production film;
[its recipe](complete_small.json) records source/output hashes and settings.
The silent slow inspection repeats source frames at quarter speed; it supplies
no additional authored poses.

## Picture, movement and faction continuity

Carcovian guards and banners use charcoal, gunmetal and restrained copper,
with a split-ring/vertical-bar visual mark. Red warning fixtures continue to
blink independently of those material colors. Lucan retains his approved
polished steel, oxblood cloth and gold trim. Iselin retains blue/silver clothing,
and the ordinary Crown soldier has simpler equipment belonging with the party.

The running view reveals lower-body movement while faces remain outside the
frame. Lucan leads; Iselin follows close on his anatomical right. The Crown
soldier remains on Lucan's anatomical left about ten feet behind, with the
trailing appearance allowed near the frame edge. Each actor has 24 complete
authored poses in a 400 ms cycle. Every 60 Hz display tick advances to the next
pose; the three-second shot displays 180 such ticks. Lucan's phase offset is
zero, Iselin's is five ticks and the Crown soldier's nine. Complete drawings
resolve near/far limbs rather than assembling independent animated body parts.
The ground scroll and contact cues share the production clock. Source-floor
fitting supplies approximate staging, not a guarantee of perfect foot locking
at every phase. Reduced Motion retains the same ground speed and cadence while
removing optional camera back-drift. Far sky, sea and mountains remain
fixed; only the separate transparent rail/deck layer follows camera travel.

Visual review is scoped to the visible boot-height performance, its transitions,
near/far leg movement and the numbered lower-body source sheets. Full-character
drawings retain costume/proportion references; a later frontal running shot
still needs its own performance and facial-framing review.

The preceding orbit remains an offline spatial composition with painted
surfaces, a brief opening relief and separate rigid frozen-guard image planes.
Smoke uses complete vent-anchored plume drawings with geometric occlusion.
These methods do not claim volumetric character or fluid simulation. The new
running shot combines authored character frames with the lateral bridge
painting, rather than stretching detached limbs or a frozen idle.

## Capture and verification method

Native movies tap the clean picture returned by the production renderer during
`Game.draw` in a disposable, save-disabled Gallery, before pause/Skip controls
are added. The same draw still produces its normal UI; separate Gallery replay
screenshots retain that toolbar. Encoding and numbered stills use this one
rendered picture, without an additional cinematic render. Every movie's
companion JSON records full-reel offset,
representative scene states, frame count, source/runtime hashes and completion.
Audio is reconstructed offline from production WAVs and the same global cue
curves, including manifest-derived foot contacts. Live capture effects are
muted; this is not mixer-hardware loopback or a physical-device listening claim.
The [audio validation](audio_validation.json) records 45 contact cues aligned
with their rendered 60 Hz poses, unclipped full/standalone mixes and shared
effect timing. It likewise describes source reconstruction rather than a
hardware listening review.

Capture timing uses SDL dummy on the capture machine and includes the clean
native-picture copy. It excludes encoder writes and review stills. It does not
establish a hardware-independent frame rate. Metadata reports the perspective
decoder's bounded cache separately from
the runner/background image cache and records their empty completion states.
Native stills and motion review remain necessary for anatomy and perceived
movement; passing completion tests alone does not establish visual quality.

The isolated [production profile](production_profile.json) runs controller
updates and clean native rendering for the final 17 seconds at real 60 Hz
deadlines, without concurrent rendering, tests or video encoding. It excludes
Gallery UI/scaling, this capture tool's picture copy and the preceding 25-second
eagle shot. Its 1,020 frames averaged **6.09 ms**, with **10.97 ms p95** and zero
foreground decoder waits. The 180 running frames averaged **5.32 ms**, with
**7.76 ms p95** and **14.25 ms maximum**; every running frame met the 16.67 ms
budget. One earlier frozen-reveal frame took **22.05 ms**. Peak recorded image
reservations were 57,139,200 bytes for perspectives, 25,804,800 bytes for the
runner/background cache and 76,185,600 bytes combined at the same instant.
Completion drained the frame owners and cleared images/audio in **0.86 ms**.
These measurements describe the recorded machine and conditions.

**194 tests passed:** **124 core checks** across cinematic timing, running
performance, capture, streaming, audio and assets, plus **70 Gallery checks**
covering all 27 registered entries, actual completion, controls and persistent
state isolation. See [core output](core_tests.log) and
[Gallery output](gallery_tests.log).
[Capture validation](capture_validation.json) verifies all nine native movies'
dimensions, exact durations and 60 FPS frame counts, the three existing
pixel-identical continuation joins, source/runtime/movie hashes and empty
caches at natural Gallery completion. The running shot begins with its intended
hard cut at 39s. All seven updated prologue thumbnails preserve the other
**20 Gallery PNGs** and **19 provenance records** unchanged. The compact film
is 2,854,108 bytes, below 3 MiB. The silent slow derivative's actual stream timing
is recorded separately in the validation JSON. Compilation, authored export
reproduction checks and whitespace validation passed.

## Reproduction

Run from the repository root with pygame, numpy, Pillow and ffmpeg available:

```sh
python tools/capture_fire_veinhold_opening.py --fps 60
python tools/capture_fire_veinhold_opening.py --fps 60 --reduced-motion
python tools/capture_fire_veinhold_opening.py --shot-id bridge_running --fps 60
python tools/capture_fire_veinhold_opening.py --shot-id bridge_running --fps 60 --reduced-motion
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --scene fire_veinhold_shot_02 --scene fire_veinhold_shot_03 \
  --scene fire_veinhold_shot_04 --scene fire_veinhold_shot_05 \
  --scene fire_veinhold_shot_06 --out docs/reviews/veinhold_bridge_run/gallery
```

To reproduce the isolated playback profile, run from the repository root with
no other heavy rendering, capture or test process active:

```sh
python docs/reviews/veinhold_bridge_run/profile_production.py
```

Use `--shot-id eagle_ascent`, `island_orbit`, `alarm_hold`, `bridge_rush` or
`frozen_bridge` to reproduce the other native clips. The lateral painting
reproduces with `python tools/export_prologue_bridge_background.py --check`;
runner sources and their own export recipe remain under
`assets/source/cinematics/fire_veinhold/bridge_running/`.

Create the compact derivative from the captured native film:

```sh
ffmpeg -hide_banner -loglevel error -y -i docs/reviews/veinhold_bridge_run/complete.mp4 \
  -vf scale=600:400:flags=lanczos -r 60 -c:v libx264 -preset medium -crf 30 \
  -maxrate 500k -bufsize 1000k -pix_fmt yuv420p -c:a aac -b:a 64k \
  -movflags +faststart docs/reviews/veinhold_bridge_run/complete_small.mp4
```
