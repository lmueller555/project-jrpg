# Heavy pressure release

Approved replacement for Rhea's ice-prison breakout (Ice B). The launcher and
all cinematic visuals remain unchanged. Play at 17.100 seconds: the 200ms
pressure buildup places the rupture at the existing 17.300-second shatter.

`pressure_release_master.wav` is the lossless, level-matched master reviewed
by the user (48kHz stereo, 24-bit PCM). Its SHA-256 is
`1854a26f43be03e4746597b78c4150bb642189a057715c92654ce4997eea1b0e`.
It layers pitched, filtered and reversed recordings of real ice dropping,
with restrained reflections; there are no glass or synthesized impact layers.

Run `python tools/build_ice_reaper_breakout_audio.py` with NumPy and FFmpeg to
rebuild the runtime Vorbis asset and manifest. It reproduces the reviewed
6dB debris-tail recession as the camera retreats. The master already includes
the listening level, so encoding compensates for the existing 0.58 runtime cue
gain, avoiding double attenuation. The legacy rescue builder still generates
its original unused burst; this dedicated replacement is independently built.

## Source credits

Both original recordings are by **Anthousai**, dedicated under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/):

- [406217 — Ice cubes onto concrete](https://freesound.org/people/Anthousai/sounds/406217/).
  Original SHA-256: `ff082c50bd965b3743fc8a0ce22206cbe5f1865eb8f4dac9a55cd7465b85ab16`.
- [406218 — Ice from a second-story railing onto grass](https://freesound.org/people/Anthousai/sounds/406218/).
  Original SHA-256: `8ef22161da5fee8f4db3335e519db1c320a69d063ab790b4ea707a57f92167bf`.

Original recordings: 96kHz, stereo, 24-bit; licenses verified on 2026-11-05.
Retrieved from `Samples/` in the public `Wh1teDuke/WilhelmSFX` mirror, pinned to
commit `ec4875a35d265b5431e3ba81fef6cc0ca0281bfc`. Licensing rests on the
individual recordings' CC0 dedications. The derived editing master is retained
here so the runtime encode can be rebuilt without downloading audition files.
