# Replacement title composition and sampled instruments

The discarded flute/harp score and oscillator-based renderer have been replaced
by **Eldenmere — A Place to Return To**, an original piano/cello composition.
The musical source is the score in `tools/build_title_music.py`; the exported
note events and rendering information are in `assets/ui/title/music_score.json`.

The renderer uses GeneralUser GS 2.0.3 by S. Christian Collins through the
system FluidSynth library. Its supplied license expressly allows unrestricted
private/commercial music creation and recordings. The original license is
preserved in `GeneralUser-GS-LICENSE.txt`. The SoundFont itself is not bundled
with the game; the game plays the pre-rendered Ogg using Pygame.

Source: https://github.com/mrbumpy409/GeneralUser-GS

Pinned revision: `684543d5e5efaef08d02be50dcda8d552478fa60`

SoundFont SHA-256:
`9575028c7a1f589f5770fccc8cff2734566af40cd26ed836944e9a5152688cfe`

To reproduce, install the asset requirements, FFmpeg and libfluidsynth, obtain
`GeneralUser-GS.sf2` from the pinned upstream revision, then run:

```sh
python tools/build_title_music.py --soundfont /path/to/GeneralUser-GS.sf2
```

Only rendered audio and the license/provenance are committed. No demonstration
MIDI compositions or audio from the upstream library are used.

All score entrances/releases lie on integer quarter-note beats at 72 BPM in
4/4. Dynamics vary, timing does not. Each sample/pitch/velocity's attack is
calibrated and advanced during rendering so its audible entrance aligns with
the written beat. The final audio is a single mixed stream, not independently
running instrument loops. Shared diffuse room ambience supplies space without
rhythmic delay echoes. Instrument release tails remain natural.
