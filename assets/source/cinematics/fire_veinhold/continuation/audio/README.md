# Fire Veinhold continuation effects

Original deterministic synthesis, with no third-party recordings or plugins.
The retained authoring code is
[`tools/build_prologue_alert_audio.py`](../../../../../../tools/build_prologue_alert_audio.py).
`recipe.json` records its seed, format and approved cue times. The runtime
manifest records each export's SHA-256, peak, RMS and duration.

Reproduce and verify from the repository root:

```sh
python tools/build_prologue_alert_audio.py
python tools/build_prologue_alert_audio.py --check
python -m unittest discover -s tests -p test_prologue_alert_audio.py
```

The warning is a two-second motor-driven horn cycle, with a continuously
changing fundamental, restrained harmonics, motor resonances and filtered air.
Its far-field version preserves the same sample phase with softened high
frequencies and a short reflected component. The two loops crossfade during
the bridge rush; switching clips does not restart either loop.

The rush combines shaped air bands with short metal-span resonances. A quiet,
short creak accompanies the settled ice view; it is not a shattering effect.
The machinery bed combines low turbine air with steady steel resonances. It
begins during the orbit at 25 seconds, remains quiet beneath the warning and
falls from gain 0.12 to a distant 0.015 as the camera leaves the fortress.
It has no rhythmic beep or warning pulse and uses its own two-second loop phase.
Every export is 48 kHz stereo PCM16 and remains below clipping.

The running shot adds six individual 0.22-second contact sounds: near/far boot
impacts for Lucan, Iselin and the Crown soldier. Lucan has a heavier low deck
impact and armor response; Iselin has a lighter sole impact and more cloth;
the trailing soldier is quieter. Each sound includes its short equipment
response after the impact. These sources contain no prearranged running rhythm.
Separate deterministic seeds retain the preceding five WAVs byte-for-byte.

`cinematic_bridge_run.read_run_timing()` reads the same frame durations,
near/far contact landmarks and positive phase offsets used by the picture.
The audio owner reads that metadata once and schedules each contact from the
global 39-second cut through the 47-second endpoint. The side view cuts to the
frontal reveal at 42 seconds without restarting the audio owner or contact
table. Frontal phase advances of 0.2, 17/60 and 21/60 seconds continue the
side view's 0, 5/60 and 9/60 phases after three elapsed seconds. Starts within a current
contact play only its remaining PCM tail; long seeks and unmute do not replay
old steps. Preview mixing uses the same contact table and integer sample
positions so an isolated running clip matches its interval in the complete film.
At the frontal cut, step panning follows the newly visible formation: Lucan
central, Iselin on viewer left and the Crown soldier on viewer right. Existing
contact tails retain their PCM lease and change pan with the camera; their cue
identity and sample phase do not restart. Wind and siren phases remain continuous.

The close frontal view adds a quiet unvoiced breathing bed at 42 seconds.
Its 3.6-second source contains three slightly varied inhale/exhale phrases,
approximately 1.2 seconds apart, independent of the 400 ms running cycle.
Band-limited air supplies mouth/nose texture without dialogue or pitched voice.
An independent synthesis seed preserves all eleven earlier WAVs. The bed uses
gain 0.075 and the silent near-warning channel; that warning has had zero gain
since the rush ended at 35 seconds. Audible machinery, distant siren and wind
retain their existing leases and PCM phase. This keeps overlapping contacts
and breathing within the existing eight-channel mixer budget.
The current drawings use 24 poses per 0.4-second cycle, with contacts at frames
0 and 12. Actor phase advances are 0, 5/60 and 9/60 seconds at the 39-second
start; all 120 contacts (45 side-view and 75 frontal-view contacts)
therefore coincide with exact 60 Hz display ticks. Contact scheduling consumes
the metadata rather than hard-coding that particular cadence.

`prologue_alert_audio.py` owns playback using the full-reel clock: warning at
30 seconds, machinery at 25, four-second warning lead-in, rush at 34, distant warning and ice at 35,
running at 39, the frontal cut at 42 and cleanup at 47. It leases free effects channels and respects pause, focus,
effects volume, mute, restart, seek and Gallery cleanup. The existing flight
owner retains wind. Offline preview movies use `mix_alert_audio()` and are
reconstructions from the exports, not hardware-loopback recordings.
