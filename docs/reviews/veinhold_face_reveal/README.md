# Fire Veinhold frontal running-party reveal

Historical review of the original 24-pose/400 ms implementation. The player
subsequently identified insufficient arm action, excessive cadence and poor
hair/cloth follow-through. The [running correction](../veinhold_running_polish/README.md)
supersedes its motion, timing and runtime cache facts. These captures retain
the original result; the checks below did not establish convincing animation.

The production Gallery film now contains seven shots over 47 seconds. The new
42–47s shot tracks backward in front of Lucan, Iselin and the Crown soldier,
tilting down from above their heads over 1.5 seconds to reveal their faces.
The [scene owner](../../narrative/scenes/FIRE_VEINHOLD_PROLOGUE.md) records the
framing, formation and disclosure contract. The earlier
[42-second running-shot review](../veinhold_bridge_run/README.md) remains
historical evidence of the side-on performance and faction revision.

## Review outputs

- [Five-second face reveal, 0.8 MB](shot07_small.mp4)
- [Small complete preview, 2.8 MB, 600×400 at 60 FPS](complete_small.mp4)
- [Complete production film, 960×640 at 60 FPS](complete.mp4)
- [Complete Reduced Motion film](complete_reduced_motion.mp4)
- [Complete sequence contact sheet](complete_filmstrip.png)
- [Reduced Motion contact sheet](complete_reduced_motion_filmstrip.png)
- [Frontal face reveal](shot07.mp4)
- [Frontal Reduced Motion reveal](shot07_reduced_motion.mp4)
- [Silent quarter-speed frontal inspection](shot07_slow.mp4)
- [Frontal production stills](shot07_filmstrip.png)
- [Eagle approach and fortress](shot01.mp4)
- [Island orbit](shot02.mp4)
- [Orbit camera checkpoints](shot02_camera_contact_sheet.png)
- [Four-second alarm lead-in](shot03.mp4)
- [One-second bridge rush](shot04.mp4)
- [Frozen Carcovian guards](shot05.mp4)
- [Side-on running-party shot](shot06.mp4)
- [Lucan's numbered frontal drawings](lucan_drawn_contact_sheet.jpg) and [face details](lucan_faces_contact_sheet.png)
- [Iselin's numbered frontal drawings](iselin_drawn_contact_sheet.jpg) and [face details](iselin_faces_contact_sheet.png)
- [Crown soldier's numbered frontal drawings](crown_soldier_drawn_contact_sheet.jpg) and [face details](crown_soldier_faces_contact_sheet.png)
- [Environment camera checkpoints](environment_contact.jpg)
- [Environment reproduction validation](environment_validation.json)

The small video retains all 47 seconds, 2,820 displayed frames, 60 FPS and audio.
Download it and open it in QuickTime, VLC or a browser to review outside the
game. It is a compressed derivative of the native production film;
[its recipe](complete_small.json) records source/output hashes and settings.
The [short preview recipe](shot07_small.json) records the same details for the
five-second frontal clip. Both retain 60 FPS and audio. The silent slow
inspection holds each existing source frame for four display ticks, producing
20 seconds at 60 FPS without introducing new poses.

## Picture and performance scope

The new frontal characters use the detailed painterly treatment of the frozen
guards while retaining the companions' approved identities. Lucan remains in
polished steel, oxblood cloth and gold trim; Iselin retains white hair, blue eyes
and blue/silver royal clothing. The ordinary Crown soldier has simpler allied
equipment, distinct from Carcovian charcoal, gunmetal and copper.

Lucan leads in the center. Iselin is close behind on his anatomical right,
screen left. The Crown soldier stays on Lucan's anatomical left, screen right,
3.048 metres behind. The moving camera and their projected scales preserve
that formation. The first 1.5 seconds supply the essential downward reveal;
the remaining 3.5 seconds keep their faces readable while they run. Reduced
Motion retains the reveal and cadence while removing optional camera accents.

Each actor uses 24 complete authored frontal poses over 400 ms. Every 60 Hz
display tick advances to the next pose. At the 42s cut the existing run clock
continues: Lucan begins at phase 0.2 seconds, Iselin at 0.283333… and the Crown
soldier at 0.35, corresponding to source poses 12, 17 and 21. This is a new
frontal performance; the preceding lower-body review alone does not establish
its anatomy, facial consistency or arm/equipment occlusion.

Camera-registered environment frames supply 301 inclusive samples over five
seconds; 300 display intervals preserve the authored duration. Characters use
complete drawings rather than independently warped limbs. These are painted
characters combined with offline-rendered scenery, not volumetric actors.
The frontal reveal introduces no dialogue, overhead ascent, gameplay handoff
or journey progress.

## Capture and verification method

Native movies tap the clean picture returned by the production renderer during
`Game.draw` in a disposable, save-disabled Gallery, before pause/Skip controls
are added. The same draw still produces normal UI; separate Gallery replay
screenshots retain its toolbar. Encoding and numbered stills share this one
rendered picture. Each movie's companion JSON records full-reel offset,
representative scene states, frame count, source/runtime hashes and completion.

Audio is reconstructed offline from production WAVs and the shared global
warning, wind and contact curves. Live capture effects are muted; this is not
hardware loopback or a physical-device listening claim. The running schedule
continues through 47s, with no siren/step reset at the viewpoint change.
The frontal shot adds a restrained unvoiced breathing bed on the channel whose
near warning has already become silent; the active scene effects continue.
The [audio validation](audio_validation.json) records 120 running contact cues,
including 75 frontal onsets aligned to the actual landing poses. The preceding
0–42s alert mix and original eleven continuation WAVs remain byte-identical;
breathing is the twelfth continuation export. The SDL-dummy eight-channel probe played all 75 frontal
contacts while reusing the silent near-warning slot for breathing. Full-film
and frontal mixes remain unclipped. These are reconstruction, mixer ownership
and cue-alignment checks, not physical-device listening evidence.

Capture timing uses SDL dummy on the capture machine and includes the clean
native-picture copy. It excludes encoder writes and review stills. It does not
establish a hardware-independent frame rate. The new actor/environment cache
uses heterogeneous source dimensions: metadata records their individual
decoded/pending bytes, their combined face-reveal bytes and completion states.
Its slot count must not be interpreted as uniformly sized 960×640 surfaces.
The preceding perspective and side-run caches are reported separately.

The frontal renderer retains one complete 24-pose cycle for each of the three
actors: 72 decoded 768×1024 RGBA drawings, bounded to **216 MiB**. Eight native
960×640 environment slots add **18.75 MiB**, for a **234.75 MiB** face-reveal
image-cache budget, including pending reservations and excluding temporary
conversion/drawing buffers. Full-film and standalone frontal playback prepare
that cycle before the presentation clock and audio start. Other individual
clips do not load the frontal owner. Software workers decode source images;
display conversion stays on the main thread. The measured startup cost is
**1.55 seconds**, keeping the preparation outside the running shots.

The [initial profile](production_profile_before_warm_cache.json) records the
earlier small-cycle-cache measurement that exposed repeated PNG decode waits.
The [during-film warmup profile](production_profile_during_warmup.json) records
the cost of preparing the larger cache during the preceding side shot. Both
remain evidence for the decoded-cycle/startup policy, rather than current
performance results.

The final [production profile](production_profile.json) measures controller
updates plus clean native rendering at real 60 Hz deadlines for the final
22 seconds. It excludes Gallery UI/scaling, the capture tool's picture copy,
video encoding and the preceding 25-second eagle shot. It ran without other
heavy rendering or test processes. The 1,320 frames averaged **5.82 ms**, with
**10.89 ms p95**. Eleven transient frames exceeded the 16.67 ms budget.

| Scope | Frames | Mean | p95 | Maximum | Frames above 16.67 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frontal reveal | 300 | 4.44 ms | 7.66 ms | 21.78 ms | 1 |
| Preceding side run | 180 | 5.47 ms | 7.37 ms | 25.56 ms | 3 |
| All measured continuation shots | 1,320 | 5.82 ms | 10.89 ms | 29.25 ms | 11 |

There were **zero foreground decoder waits** across the frame owners. Peak
face-reveal reservations were 246,153,216 bytes; all image caches together
peaked at 322,338,816 bytes at the same instant. Completion drained the frame
owners and released images/audio in **0.75 ms**. These measurements describe
the recorded machine and conditions, not a hardware-independent guarantee or
a claim that every frame met the deadline.

[Pixel equivalence](pixel_equivalence.json) compares six native production
stills before and after the cache policy change: local times 0, 0.5, 1.5, 2.5,
3.5 and 299/60 seconds. All decoded RGB pixels match exactly. The report retains
old/new PNG and RGB hashes plus both capture source/runtime fingerprints; it
is a representative-frame comparison rather than an all-frame equality claim.

**217 tests passed:** **146 core checks** across cinematic timing, streaming,
frontal staging, audio, captures and assets, plus **71 Gallery checks** covering
all 28 registered entries, actual completion, controls and persistent state
isolation. There were no skips. See [core output](core_tests.log) and
[Gallery output](gallery_tests.log).

[Capture validation](capture_validation.json) verifies all ten native movies'
960×640 dimensions, exact durations and 60 FPS frame counts, the three existing
pixel-identical continuation joins, source/runtime/movie fingerprints and empty
caches at natural Gallery completion. The running and frontal shots retain
their intended cuts at 39s and 42s. All eight updated prologue thumbnails
preserve the other **20 Gallery PNGs** and **19 provenance records** unchanged.
The compact full film is **2,821,450 bytes**, below 3 MiB; the compact frontal
clip is **772,823 bytes**, below 1.5 MiB. Both are H.264/AAC at 600×400 and 60 FPS,
with 2,820 and 300 video frames respectively. The silent slow inspection has
1,200 frames over exactly 20 seconds. Compilation, authored export reproduction
checks and whitespace validation passed.

## Reproduction

Run from the repository root with pygame, numpy, Pillow and ffmpeg available:

```sh
python tools/capture_fire_veinhold_opening.py --fps 60
python tools/capture_fire_veinhold_opening.py --fps 60 --reduced-motion
python tools/capture_fire_veinhold_opening.py --shot-id face_reveal --fps 60
python tools/capture_fire_veinhold_opening.py --shot-id face_reveal --fps 60 --reduced-motion
python tools/capture_gallery.py --mode thumbnails \
  --scene fire_veinhold_opening --scene fire_veinhold_shot_01 \
  --scene fire_veinhold_shot_02 --scene fire_veinhold_shot_03 \
  --scene fire_veinhold_shot_04 --scene fire_veinhold_shot_05 \
  --scene fire_veinhold_shot_06 --scene fire_veinhold_shot_07 \
  --out docs/reviews/veinhold_face_reveal/gallery
```

Use `--shot-id eagle_ascent`, `island_orbit`, `alarm_hold`, `bridge_rush`,
`frozen_bridge` or `bridge_running` to reproduce the preceding native clips.
Sources and export recipes for the new artwork remain under
`assets/source/cinematics/fire_veinhold/face_reveal/`.
The environment can be regenerated with
`python tools/build_prologue_face_environment.py`; `--check` rerenders all 301
perspectives and compares their exact PNG bytes, camera metadata and recipe.

To reproduce the isolated profile, run from the repository root with no other
heavy rendering, capture or test process active:

```sh
python docs/reviews/veinhold_face_reveal/profile_production.py
```

Create the compact derivative from the captured native film:

```sh
ffmpeg -hide_banner -loglevel error -y -i docs/reviews/veinhold_face_reveal/complete.mp4 \
  -vf scale=600:400:flags=lanczos -r 60 -c:v libx264 -preset medium -crf 30 \
  -maxrate 425k -bufsize 850k -pix_fmt yuv420p -c:a aac -b:a 64k \
  -movflags +faststart docs/reviews/veinhold_face_reveal/complete_small.mp4
```
