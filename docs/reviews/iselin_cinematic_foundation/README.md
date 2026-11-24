# Iselin cinematic action foundation

This review adds playback mechanics and a reusable preview tool. It adds no new
performance drawings and installs no actions in production manifests. The
[Regent arrival guide](../../narrative/scenes/REGENT_ARRIVAL.md) and
[sprite animation standard](../../SPRITE_ANIMATION_STANDARD.md) remain the
authoring guidance.

The [reference board](reference_board.png) shows the existing approved native
front/left/right/back idles, current seated pose, six ground cinematic poses and
two aerial poses. Each group identifies its canvas and inspection enlargement;
the different camera slots are not interchangeable actor sizes.

## Captured mechanics

The [normal preview](preview.gif), [quarter-speed preview](preview_slow.gif) and
[sample board](samples.png) use the production `Game.draw()` renderer through an
actual isolated arrival Gallery child. They select the `relief` shot at its
authored starting time and inject the
[synthetic probe](synthetic_probe.json) through the ordinary action loader.
Root paths, camera, scale and foreground drawing remain the shot's own. The
parent game's save and settings paths are temporary.

The probe switches existing still poses. It demonstrates entry, an indefinite
hold, release, recovery and persistent rest; it is explicitly a mechanics test,
not an authored gesture animation. It enters for 100 ms, holds `gesture_left`,
releases at 300 ms, recovers for 120 ms and rests in `stand_left` from 420 ms.

| Simulation time | State | Actual rendered capture |
| --- | --- | --- |
| 0 ms | Entry | [Entry](sample_00.png) |
| 50 ms | Entry | [Entry in progress](sample_01.png) |
| 100 ms | Hold | [Hold](sample_02.png) |
| 300 ms | Recovery | [Release](sample_03.png) |
| 420 ms | Rest | [Recovery complete](sample_04.png) |
| 700 ms | Rest | [Persistent rest](sample_05.png) |

The separate [early release capture](early_release.png) follows release at
50 ms: entry finishes before recovery, and the indefinite hold is skipped.
[Capture metadata](capture.json) records all 50 timeline samples, exact selected
shot times, cue states, source references, output hashes and nine mechanic
checks. Both GIFs use the same sampled simulation: normal playback is 1,000 ms
and quarter-speed playback is 4,000 ms. GIF palette quantization is confined to
the review media; the individual PNG samples are lossless game captures.

The recorded checks cover duplicate-cue rejection without reset, distinct busy
cue rejection, paused clock, pure repeated drawing, focus loss, early release
and same-cue restart. The focus check loses focus before scheduled release,
requests a 500 ms viewer advance, and verifies that viewer elapsed time and
the entire actor state remain unchanged. Regaining focus restores progression.

## Reproduce and use the tool

From the repository root, with Python dependencies installed:

```sh
python tools/preview_iselin_cinematics.py --list
python tools/preview_iselin_cinematics.py --headless --shot relief --probe \
  --release-at .3 --seconds 1 --check-preservation \
  --out docs/reviews/iselin_cinematic_foundation
```

Routine future previews default to `/tmp/iselin-cinematic-preview`, keeping this
historical evidence intact. Select an existing pose or walk loop, or inspect an
authored shot without a visual override:

```sh
python tools/preview_iselin_cinematics.py --pose gesture_left --shot relief
python tools/preview_iselin_cinematics.py --loop walk_left --shot gate_greeting
python tools/preview_iselin_cinematics.py --shot gate_greeting --shot-time .4
```

The interactive window uses Space to pause, R to restart, S to toggle normal and
quarter speed, Left/Right to scrub by 20 ms and pause, E to release an action, F
to save a labelled PNG and Escape to exit. Scrubbing clears and replays the
action from the selected shot time, including its scheduled release; it does
not edit a production scene. Headless use adds `--headless`; `--samples` selects
comma-separated simulation times, `--seconds` controls the GIF window, and
`--speed .25` selects a slower primary capture. The SDL dummy video driver is
set only for headless mode, so ordinary interactive use can open a real window.

Future action files can be reviewed without adding them to production:

```sh
python tools/preview_iselin_cinematics.py --action-file /path/clips.json \
  --action greeting --release-at .3 --shot relief
```

The external JSON wraps named clips in `actions`:

```json
{
  "actions": {
    "greeting": {
      "entry": [{"pose": "stand_left", "duration_ms": 100}],
      "hold": {"pose": "gesture_left", "duration_ms": null},
      "recovery": [{"pose": "listen_left", "duration_ms": 120}],
      "rest_pose": "stand_left"
    }
  }
}
```

A frame may use `"file": "entry_01.png"` instead of `pose`. These PNGs must be
local to the clip JSON and match the current 80×96 ground actor canvas. File
inputs pass through the production loader's confinement and canvas checks;
their hashes are included in capture metadata. A positive hold duration can
replace `null` for a timed hold. Ground action selection requires a shot that
contains ground Iselin; aerial shots retain their authored presentation.

## Preservation and validation

The opt-in [preservation baseline](preservation_baseline.json) freezes 135
production Iselin PNGs and 32 relevant actor, scene, layout and registration
JSONs at `02fb8de5f99f0488e9cd5c9d1c8467d53888aa36`. All match before and after
this capture. The reference board also records each source file's hash. The
historical check is deliberately optional: later intentional asset/action
changes can use the preview tool without rewriting this PR's baseline.

Additional smoke captures used an existing static pose, `walk_left`, and an
external clip mixing local file frames with existing pose references. All
completed through the production Gallery renderer. An automated SDL event
smoke exercised pause, forward/back stepping, restart, speed toggle, release,
snapshot and exit. This verifies event handling with the dummy driver; it is
not a claim of a manually inspected desktop window.

The foundation's targeted validation comprises 25 action/runtime tests and 223
existing regression tests, 248 unique passing checks. The preview helper also
compiles, preserves the baseline and verifies its saved GIF durations. This
review stages individual actual shots and exercises playback mechanics; it
does not claim a fully played arrival, quest, meal or battle walkthrough.
