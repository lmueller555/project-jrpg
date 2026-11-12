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
| `Elden Vale Sanctuary Cave.m4a` | `runtime/elden_vale_sanctuary_cave.ogg` | Non-battle exploration throughout the Sanctuary cave, including the optional elemental chambers |
| `Kindled Courage.m4a` | `runtime/kindled_courage.ogg` | Battles; MQ02 begins it after the return camera pan and acknowledgment of Mira's warning |
| `Triumphal Fanfare.m4a` | `runtime/triumphal_fanfare.ogg` | Retained one-shot cue; combat results now resume the interrupted soundtrack |
| `Royalty of the Realm.m4a` | `runtime/royalty_of_the_realm.ogg` | Regent Aldric's arrival cinematic |
| `Dare to Dream Leitmotif.m4a` | `runtime/dare_to_dream_leitmotif.ogg` | The New Game opening cinematic; repeats throughout the scene and retains its playback position while paused |
| `Wintermute 2.m4a` | `runtime/wintermute2.ogg` | Retained previous Ice Reaper cue |
| `Those I Swore to Save.m4a` | `runtime/those_i_swore_to_save.ogg` | Full Ice Reaper cinematic, starting at track position zero |

[`tracks.json`](tracks.json) identifies the approved runtime files and their
mix levels. `loop: false` marks the victory fanfare and cinematic
cues as one-shots; the world
and battle cues use the default repeating playback. The opening leitmotif
explicitly sets `loop: true`. New uploads remain
available for review until assigned to playback.

**Elden Vale Sanctuary Cave** repeats throughout the continuous cave without
restarting between rooms, including during non-battle dialogue and menus.
The first successful cave entry permanently ends MQ03's emergency music
override for that journey. Exiting the cave then restores normal area music,
including on later visits to the Sanctuary or Eldenmere. Continue preserves
that release and selects the cave cue before restoring an underground encounter
or rewards screen. Ordinary battles still bookmark and resume their area cue.
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
reward retries and dismissal do not restart it. An encounter during MQ03's
emergency interrupts **Something is Wrong** and resumes it afterward.
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

**Something is Wrong** (`something_is_wrong`) scores MQ03’s emergency report,
departure and Sanctuary arrival. It begins after the survivor’s first two
statements, on Serene’s “What men?”, and loops until the first cave entry
releases the story override. The runtime Ogg preserves the full uploaded source
without trimming, normalization or rearrangement. Combat continues to use
**Kindled Courage** independently. Rebuild with
`python tools/build_runtime_music.py --track something_is_wrong`.
