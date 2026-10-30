# Music

Add music files you create to this folder. You can upload them on GitHub with
**Add file → Upload files**, or copy them here in your local checkout and commit them.

## Formats

- **WAV or FLAC:** preferred for original, lossless exports.
- **OGG Vorbis:** preferred for eventual game playback.
- **MP3:** welcome for auditions and review.
- **M4A:** original exports can be retained and converted for playback.

Stereo at 44.1 or 48 kHz is a useful export target. Keep your original export
when a playback conversion is also provided.

## Filenames

Use lowercase names with underscores and a version, for example:

```text
eldenmere_battle_v01.wav
eldenmere_battle_v02.wav
victory_v01.ogg
```

## Optional track notes

A matching text file, such as `eldenmere_battle_v01.txt`, can describe the intended
scene, creator or generation tool, and any known loop start/end times. These
notes are optional; you can add the audio on its own.

## Current game tracks

| Original upload | Runtime asset | Use |
| --- | --- | --- |
| `Eldenmere Theme.m4a` | `runtime/eldenmere_theme.ogg` | Title and Eldenmere/millrace exploration |
| `Kindled Courage.m4a` | `runtime/kindled_courage.ogg` | Battles; MQ02 begins it after the return camera pan and acknowledgment of Mira's warning |
| `Triumphal Fanfare.m4a` | `runtime/triumphal_fanfare.ogg` | Victory banner and Spoils of Battle; plays once, then stays silent until Spoils is left |
| `Dare to Dream Leitmotif.m4a` | `runtime/dare_to_dream_leitmotif.ogg` | The New Game opening cinematic; repeats throughout the scene and retains its playback position while paused |

[`tracks.json`](tracks.json) identifies the approved runtime files and their
mix levels. `loop: false` marks the victory fanfare as a one-shot; the world
and battle cues use the default repeating playback. The opening leitmotif
explicitly sets `loop: true`. New uploads remain
available for review until assigned to playback.

The original uploads are preserved unchanged. Their M4A containers contain
48 kHz stereo Opus audio. This Pygame build needs Ogg Vorbis runtime copies, so
the exporter creates high-quality Vorbis files at the same sample rate. It
does not normalize, stretch, rearrange or synthesize the music.

Eldenmere keeps its full 95.0935-second decoded cue. The battle runtime removes
only 1.1485 seconds of the final near-silent tail, retaining 25 ms after the last
5 ms RMS block above -60 dBFS. Five-millisecond de-clicks at its quiet boundaries
avoid clicks. Its runtime duration is 188.825 seconds. Both cues repeat as
authored; these exports do not claim a sample-accurate musical loop or recreate
missing musical transitions. The fanfare keeps its full natural ending and is
not repeated, faded out early or trimmed into a loop.

The opening uses **Dare to Dream Leitmotif**, not the separate `Dare to Dream`
upload. Its runtime retains the full 199.1735-second decoded cue. Five-millisecond
de-clicks at the beginning and end soften the sample discontinuity on repeat;
there is no trimming, phrase overlap or musical rearrangement. The track repeats
as authored. Pausing with Esc or losing window focus pauses the stream, and
resuming continues at the same position. Finishing or skipping the cinematic
returns to the Eldenmere Theme for the sanctuary morning.

## Rebuild runtime exports

From the repository root, with FFmpeg and the existing asset-tool requirements
installed:

```sh
python tools/build_runtime_music.py
```

To rebuild just the opening cue while preserving all other runtime exports:

```sh
python tools/build_runtime_music.py --track opening_leitmotif
```

The builder checks the original upload hashes, exports the selected files,
verifies their full decoded frame counts and Pygame streaming/repeat or one-shot
support, and writes
[`runtime/provenance.json`](runtime/provenance.json). The game plays the
pre-rendered files and does not need FFmpeg or NumPy installed.
