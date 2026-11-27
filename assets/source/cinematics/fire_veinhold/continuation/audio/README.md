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

`prologue_alert_audio.py` owns playback using the full-reel clock: warning at
30 seconds, machinery at 25, four-second warning lead-in, rush at 34, distant warning and ice at 35,
cleanup at 39. It leases free effects channels and respects pause, focus,
effects volume, mute, restart, seek and Gallery cleanup. The existing flight
owner retains wind. Offline preview movies use `mix_alert_audio()` and are
reconstructions from the exports, not hardware-loopback recordings.
