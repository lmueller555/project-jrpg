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
| `Royalty of the Realm.m4a` | `runtime/royalty_of_the_realm.ogg` | Regent Aldric's arrival cinematic |
| `Dare to Dream Leitmotif.m4a` | `runtime/dare_to_dream_leitmotif.ogg` | The New Game opening cinematic; repeats throughout the scene and retains its playback position while paused |

**Royalty of the Realm** starts after Eldenmere's one-second fade during the
arrival blackout and repeats through the Aldric cinematic. Its native Vorbis
export contains the encoder's documented 56-frame lead-in; no music is trimmed
or rearranged.

| Original upload | Runtime asset | Use |
| --- | --- | --- |
| `Eldenmere Theme.m4a` | `runtime/eldenmere_theme.ogg` | Title screen |
| `Eldenmere.m4a` | `runtime/eldenmere.ogg` | Eldenmere, its interiors and millrace exploration; repeats without restarting across area transfers |
| `Kindled Courage.m4a` | `runtime/kindled_courage.ogg` | Battles; MQ02 begins it after the return camera pan and acknowledgment of Mira's warning |
| `Triumphal Fanfare.m4a` | `runtime/triumphal_fanfare.ogg` | Victory banner and Spoils of Battle; plays once, then stays silent until Spoils is left |
| `Royalty of the Realm.m4a` | `runtime/royalty_of_the_realm.ogg` | Regent Aldric's arrival cinematic |
| `Dare to Dream Leitmotif.m4a` | `runtime/dare_to_dream_leitmotif.ogg` | The New Game opening cinematic; repeats throughout the scene and retains its playback position while paused |
| `Wintermute 2.m4a` | `runtime/wintermute2.ogg` | Ice Reaper's five-second Gallery opening preview; the full cinematic and boss handoff remain planned |

[`tracks.json`](tracks.json) identifies the approved runtime files and their
mix levels. `loop: false` marks the victory fanfare and bounded Wintermute2
preview cue as one-shots; the world
and battle cues use the default repeating playback. The opening leitmotif
explicitly sets `loop: true`. New uploads remain
available for review until assigned to playback.

**Wintermute2:** `Wintermute 2.m4a` now has a full-length, untrimmed
`runtime/wintermute2.ogg` export for the five-second Ice Reaper Gallery preview.
The preview plays from the beginning once, honors music settings and pause,
and stops when its disposable playback closes. The planned full cinematic
uses the opening 45 seconds before continuing into the boss fight; that
main-story integration and final boss-loop behavior remain future work.
The original upload and existing title, exploration, battle and other cues
are unchanged. The runtime keeps the native encoder's documented 56 extra frames.

The original uploads are preserved unchanged. Their M4A containers contain
48 kHz stereo Opus audio. This Pygame build needs Ogg Vorbis runtime copies, so
the exporter creates high-quality Vorbis files at the same sample rate. It
does not normalize, stretch, rearrange or synthesize the music.

The title's Eldenmere Theme keeps its full 95.0935-second decoded cue.
The new Eldenmere exploration cue retains its complete decoded audio without
trimming or rearrangement. Like Royalty of the Realm, its native Vorbis export
includes the encoder's 56-frame lead-in. The title keeps its original music;
Continue and the end of the opening cinematic select the new exploration cue.
The battle runtime removes
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
returns to Eldenmere for the sanctuary morning.

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

To rebuild only the Eldenmere/millrace exploration cue:

```sh
python tools/build_runtime_music.py --track eldenmere
```

To rebuild only the Wintermute2 preview cue:

```sh
python tools/build_runtime_music.py --track wintermute2
```

The builder checks the original upload hashes, exports the selected files,
verifies their full decoded frame counts and Pygame streaming/repeat or one-shot
support, and writes
[`runtime/provenance.json`](runtime/provenance.json). The game plays the
pre-rendered files and does not need FFmpeg or NumPy installed.
