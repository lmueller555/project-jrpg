# Regent arrival: aerial bird effects

These are short, recorded sound effects for the hawk in the establishing
shot. Both recordings and the edited effects are **CC0 1.0 Universal**;
the complete legal text is in [CC0-1.0.txt](CC0-1.0.txt).

| Runtime file | Sound | Length | Format | Decoded peak | Decoded RMS |
| --- | --- | --- | --- | --- | --- |
| `hawk_call.ogg` | Recorded hawk screech, preserving the natural falling cry | 1.900 s | Mono, 48 kHz Vorbis quality 6 | -6.63 dBFS | -23.39 dBFS |
| `wing_flap.ogg` | One recorded cloth wingbeat, edited from coat-flapping foley | 0.300 s | Mono, 48 kHz Vorbis quality 6 | -6.43 dBFS | -26.00 dBFS |

The call uses a channel gain of `0.40`; wingbeats use `0.12`. With these
gains, wingbeats have approximately 13 dB less RMS level than the call.
The sound-effects setting applies in addition to those per-effect gains.
These files are one-shots, with short fades at both ends; neither contains
a music bed, synthetic bird oscillator, dialogue, or a continuous loop.

## Source recordings and attribution

Unmodified source WAVs are retained in `source/`. Downloaded from the
public [WilhelmSFX sound bank](https://github.com/Wh1teDuke/WilhelmSFX)
at commit `ec4875a35d265b5431e3ba81fef6cc0ca0281bfc`, whose
[`sources.txt`](https://github.com/Wh1teDuke/WilhelmSFX/blob/ec4875a35d265b5431e3ba81fef6cc0ca0281bfc/sources.txt)
maps these exact filenames to their original Freesound pages.
The CC0 licenses were also checked on each original Freesound sound page
on November 1, 2026; the mirror's code license is not the basis for
licensing the recordings.

### Hawk call

- **Title:** Hawk 2.wav
- **Creator:** basedMedia
- **Original page and license declaration:**
  <https://freesound.org/people/basedMedia/sounds/548118/>
- **License:** CC0 1.0 Universal,
  <https://creativecommons.org/publicdomain/zero/1.0/>
- **Original format:** 2.529433 s, stereo, 44.1 kHz, 32-bit WAV.
- **Exact downloaded binary:**
  <https://raw.githubusercontent.com/Wh1teDuke/WilhelmSFX/ec4875a35d265b5431e3ba81fef6cc0ca0281bfc/Samples/548118__basedmedia__hawk-2.wav>
- **Source SHA-256:**
  `d69ca3f24a9523293dc3ac209723aba61b408398710cd150725d1e8abf84a836`
- **Changes:** trim the quiet tail to 1.9 s; convert to mono/48 kHz;
  gently filter rumble/high-frequency noise; raise gain by 1.5;
  apply 8 ms attack and 90 ms tail fades; encode to Ogg Vorbis.

### Wingbeat

- **Title:** Wing Flap 1.wav
- **Creator:** _stubb
- **Original page and license declaration:**
  <https://freesound.org/people/_stubb/sounds/389634/>
- **License:** CC0 1.0 Universal,
  <https://creativecommons.org/publicdomain/zero/1.0/>
- **Recording method:** the creator describes flapping a large coat to
  record wing-flapping foley. This is a recorded physical sound.
- **Original format:** 0.933333 s, stereo, 48 kHz, 24-bit WAV.
- **Exact downloaded binary:**
  <https://raw.githubusercontent.com/Wh1teDuke/WilhelmSFX/ec4875a35d265b5431e3ba81fef6cc0ca0281bfc/Samples/389634__stubb__wing-flap-1.wav>
- **Source SHA-256:**
  `97b362d11f7d6b184d990cb2a7579f6da431b81bab927ed10c7857d714b5aea6`
- **Changes:** extract one stroke at 0.13–0.43 s; convert to mono/48 kHz;
  filter rumble/high-frequency noise; raise gain by 2;
  apply 10 ms attack and 30 ms tail fades; encode to Ogg Vorbis.

Attribution is provided voluntarily; CC0 does not require it.

## Offline rebuild and verification

With Python 3 and ffmpeg (including `libvorbis`) installed, run:

```sh
python assets/audio/sfx/regent_aerial/build.py
```

The script contains the exact ffmpeg arguments and filters. It reads only
the retained WAVs and writes only the two runtime OGGs, stripping source
metadata and marking each output `license=CC0-1.0`.

Both checked-in OGGs decode without errors to finite mono samples; peaks
are below -6 dBFS, with no clipped samples. Ogg bitstream serial numbers
can differ between rebuilds even when the decoded audio is identical.
