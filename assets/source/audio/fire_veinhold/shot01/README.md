# Fire Veinhold prologue — mountain flight, shot 1

This source pack owns only the 25-second exterior flight and Cinder Isles reveal. It contains
air and close feather movement, with no hawk call, dialogue, music, alarms,
machinery, artillery or volcanic sound revealing the later destination.

`prologue_flight_audio.py` starts a continuous stereo wind loop, adds short air
passes at 0.85, 2.70, 5.45 and 14.65 seconds, and follows the actual flight-cycle
downstroke at phase 0.25 of a 0.75-second cycle. The first flap uses `(t+.391)/.75`;
the second uses `3+(t-5+.141)/.75`, with bank and crest holding phases 3.188
and 14.188. These offsets match the art's neutral-frame transitions. Feather Foley sounds only during
the authored flap intervals [0,2) and [5,13.25); the banking and crest glides have
none. The renderer supplies previous/current unwrapped cycles to keep animation
and sound together. No effect uses an eagle screech or the old hawk recording.

The wind export is a six-second periodic filtered-noise loop with decorrelated
stereo air. Integer-period modulation and periodic FFT filtering preserve the
loop boundary. The player applies a short channel fade only when starting the
bed; the asset contains no repeated fade. Wind retains a nonzero level through the full 25
seconds and continues until its cinematic owner stops or hands off the flight
audio. A composite cinematic can retain this same instance across its shot cut;
the standalone Gallery controller stops it when closing or restarting playback.
`begin_shot(local_elapsed=0)` rearms adjacent flight-clip cues without replacing
the wind channel or resetting its continuous volume/pan clock.

## Sources and copyright

The five wind/rush sounds are original procedural audio generated from the
retained Python recipe with seed 741915. No downloaded wind recording or third
party music is used. They are project-created assets; no third-party attribution
is required for those five exports. This statement does not assign a new
licensing policy to other project assets.

`wing_flap_source.wav` is an exact retained copy of **Wing Flap 1.wav** by
**_stubb**, a physical coat-flapping Foley recording under **CC0 1.0 Universal**:
<https://freesound.org/people/_stubb/sounds/389634/>. Its source SHA-256 is
`97b362d11f7d6b184d990cb2a7579f6da431b81bab927ed10c7857d714b5aea6`.
The legal text is retained in [CC0-1.0.txt](CC0-1.0.txt).

It was already verified and retained for the old aerial art library; provenance
and original mirror details remain in
[that pack's record](../../../../audio/sfx/regent_aerial/README.md).
This derivative extracts 0.13–0.43 seconds, filters rumble and upper hiss,
normalizes a restrained transient, applies 12 ms attack/45 ms release fades,
and exports a soft stereo feather stroke. The original hawk-call source is not
copied, loaded or played.

## Offline generation and verification

From the repository root, with Python and numpy installed:

```sh
python assets/source/audio/fire_veinhold/shot01/build.py
python assets/source/audio/fire_veinhold/shot01/build.py --check
```

The builder reads only this directory, produces six deterministic 48 kHz,
16-bit stereo PCM WAV files and a measured manifest under
`assets/audio/sfx/fire_veinhold/shot01/`, and needs no network or external codec.
PCM preserves byte-stable verification. The longest buffer is six seconds;
runtime decodes the finite exports and does no synthesis. The manifest records
duration, peak, RMS, clipped sample count, source hash and handoff metadata.

Playback follows the Effects setting and uses only available mixer channels.
Pause/focus suspends owned leases; mute stops them without banking one-shots.
Closing or restart stops only channels still holding this owner's exact Sound
object. Music and other scenes' channels remain under their existing owners.
