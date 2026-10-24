# Title water and expanded music

Implemented and merged at the user's request for review in the running game.
Launch `python main.py`; the existing bottom-center menu and opaque fullscreen
presentation remain in place.

- [Full title preview with the complete soundtrack](title_with_music.mp4)
- [Foreground water animation, enlarged 3×](water_closeup.gif)
- [Still title capture](title_screen.png)
- [Music only, Ogg Vorbis](../../../assets/ui/title/eldenmere_theme.ogg)
- [Lossless WAV music master](../../../assets/ui/title/eldenmere_theme.wav)

The video records the actual `main.Game` renderer at 640×360 and 10 fps for the
whole 88.89-second composition. It contains the newly shipped music encoded as
AAC. The water GIF isolates the shipped water layer over the original art for
inspection, at 3× nearest-neighbor scale with one shared palette. It is silent.

## Water

Eleven registered regions cover the distant brook, upstream water and fall,
mill discharge, main stream, bridge fall, upper pool, foreground cascades,
lower pool, foam and bank trickle. Twenty-four 100 ms hard-alpha frames give a
2.4-second surface loop. Cascades and discharge complete three moving cycles
inside that period; slower surface patterns complete one. Reflections change
across full water regions rather than only isolated decorative glints.

The masks combine hand-authored water outlines, a water-color selection and
explicit exclusions for rocks. Texture samples are taken only from within the
same registered region. The buildings, characters, banks, bridge and rocks stay
in the approved background; water layers cannot displace them. The rotating
mill wheel, chimney wisps and lantern animation remain separate.

## Music

The original theme is now about 89 seconds, in 6/8 at dotted-quarter = 54,
with the rising D–E–F♯–A motif recurring across four connected passages:

| Passage | Begins | Musical treatment |
| --- | --- | --- |
| Home | 0:00 | D major, lilting harp, warm flute and open harmony |
| Curiosity | 0:22 | More active pizzicato answers and supporting strings |
| Fragility | 0:44 | B-minor setting, lower melodic register, suspensions and a brief borrowed minor chord |
| Return | 1:07 | D-major return with fuller, hopeful accompaniment |

Harp attacks and tuning vary slightly; flute phrases have breath noise, delayed
vibrato and shaped releases. Strings enter slowly with detuned voices. Sparse
bell notes and stereo reverberation add space. Note and reverb tails wrap across
the loop boundary rather than being cut off or separated by an inserted pause.
The score and synthesis are original; no external recordings are used.

The lossless master is stereo 44.1 kHz/16-bit PCM, with approximately -3.1 dBFS
peak headroom. The game streams the smaller Ogg version and retains Settings
music on/off and the New Game fade-out. All title sound remains instrumental.

Reproduce using the asset environment (Pillow, NumPy and FFmpeg):

```sh
python tools/build_title_water.py
python tools/build_title_music.py
python tools/capture_title_water_music.py
```

The game runtime still requires only Pygame. Tests check mask registration,
water-only changes, motion in every region, protected landmarks, faster falls,
audio length/stereo/headroom/loop seam and actual Ogg playback/muting.
