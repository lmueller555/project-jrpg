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
| `Eldenmere Theme.m4a` | `runtime/eldenmere_theme.ogg` | Title screen |
| `Eldenmere.m4a` | `runtime/eldenmere.ogg` | Eldenmere, its interiors and millrace exploration; repeats without restarting across area transfers |
| `Elden Vale Sanctuary Cave.m4a` | `runtime/elden_vale_sanctuary_cave.ogg` | Non-battle exploration throughout the Sanctuary cave, including the optional elemental chambers |
| `Kindled Courage.m4a` | `runtime/kindled_courage.ogg` | Battles; MQ02 begins it after the return camera pan and acknowledgment of Mira's warning |
| `Triumphal Fanfare.m4a` | `runtime/triumphal_fanfare.ogg` | Retained one-shot cue; combat results now resume the interrupted soundtrack |
| `Royalty of the Realm.m4a` | `runtime/royalty_of_the_realm.ogg` | Retained unassigned cue; the former arrival scene is removed |
| `Wintermute 2.m4a` | `runtime/wintermute2.ogg` | Retained previous Ice Reaper cue |
| `Those I Swore to Save.m4a` | `runtime/those_i_swore_to_save.ogg` | Full Ice Reaper cinematic, starting at track position zero |

[`tracks.json`](tracks.json) identifies the approved runtime files and their
mix levels. `loop: false` marks the victory fanfare and cinematic
cues as one-shots; the world
and battle cues use the default repeating playback. There is no registered
New Game opening leitmotif. New uploads remain
available for review until assigned to playback.

**Elden Vale Sanctuary Cave** repeats throughout the continuous cave without
restarting between rooms, including during non-battle dialogue and menus.
There is no MQ03 emergency override. Leaving the cave restores ordinary area
music; Continue selects the cave cue for an underground journey. Battles
bookmark and resume the actual interrupted area cue.
The full source is preserved without trimming, normalization or rearrangement.
Its native Vorbis export includes the encoder's documented 56 extra frames.

### Combat interruption and return

Entering a Bat, millrace or cave encounter remembers the selected soundtrack
and its current playback position, then switches to Kindled Courage. The
millrace cue still waits for the camera's return and Mira's acknowledged
warning; cave encounters switch when their entry sequence begins.

When combat resolves through victory, fleeing or defeat, the interrupted
track fades in from that saved position. Cave encounters return to
**Elden Vale Sanctuary Cave**. The result banner, rewards screen
and return to exploration share that resumed stream. Repeated result updates,
reward retries and dismissal do not restart it.
Entering from silence returns to silence.

Resume positions use the streamed decoder clock and Ogg seeking, including
the original seek offset after earlier battles and wrapping at a looping
track's length. Pausing, losing focus or muting music does not advance the
interrupted track. The Music slider and dialogue ducking still apply to fades.
Positions are held for the running journey; loading a journey reconstructs
the appropriate world or story cue as before, rather than saving audio clocks.

**Ice Reaper:** The full 32-second cinematic uses Those I Swore to Save.
It plays from the beginning once, honors music settings and pause, and stops
when its disposable gallery playback closes. The previous Wintermute2 source
and runtime export remain available.
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
Continue and the bedroom opening select the exploration cue.
The battle runtime removes
only 1.1485 seconds of the final near-silent tail, retaining 25 ms after the last
5 ms RMS block above -60 dBFS. Five-millisecond de-clicks at its quiet boundaries
avoid clicks. Its runtime duration is 188.825 seconds. Both cues repeat as
authored; these exports do not claim a sample-accurate musical loop or recreate
missing musical transitions. The fanfare keeps its full natural ending and is
not repeated, faded out early or trimmed into a loop.

The original **Dare to Dream Leitmotif** and **Dare to Dream** uploads remain
source material. The retired flashforward's dedicated runtime export,
registration and exporter target are removed; no new prologue music is assigned
by this retirement.

## Rebuild runtime exports

From the repository root, with FFmpeg and the existing asset-tool requirements
installed:

```sh
python tools/build_runtime_music.py
```

To rebuild only the Eldenmere/millrace exploration cue:

```sh
python tools/build_runtime_music.py --track eldenmere
```

Replacing an original upload, even with the same filename, does not update its
runtime OGG. After intentionally replacing a song, update that track's `git_sha`
in `tools/build_runtime_music.py` to the new value printed by
`git hash-object "assets/music/<source filename>"`. Rebuild that track and commit
the replacement source, runtime OGG, provenance and builder change together.
Restart the game to load the rebuilt track.

To rebuild only the Sanctuary cave exploration cue:

```sh
python tools/build_runtime_music.py --track sanctuary_cave
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

The full Ice Reaper cinematic uses `Those I Swore to Save.m4a`, exported as
`runtime/those_i_swore_to_save.ogg`. It starts at the beginning of the scene
and follows gallery pause, restart and exit behavior. Rebuild with
`python tools/build_runtime_music.py --track those_i_swore_to_save`.

**Something is Wrong** (`something_is_wrong`) remains a reusable exported cue,
with no active MQ03 report, departure, arrival or emergency override. The old
scene is removed; the track is not automatically assigned to the future Fire
opening. Its original upload and native Vorbis export remain unaltered.
