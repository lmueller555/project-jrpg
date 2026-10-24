# Eldenmere dawn title screen

Status: awaiting user review. The title uses the working name **The Broken
Covenant**, which remains a proposal rather than an approved final game name.

`eldenmere_dawn.png` is a 640×360 export of newly generated pixel-art scenery.
The original is preserved at `assets/source/ui/title/eldenmere_dawn.png`.
Generation used the approved sanctuary, watermill and main-cast portraits as
visual references. This is an illustrative vista, not a navigable map or a
replacement for the approved town layout. Caelan and Tomas appear on the bridge.

`title_screen.py` supplies the cream-and-gold logo and bottom-center vertical
menu. Scene art fills the display using proportional cover scaling; the UI is
scaled separately to fit, keeping all options visible on 4:3, 16:9 and ultrawide
displays. Mouse positions use the inverse UI transform. Gameplay retains its
existing 480×320 canvas and integer scaling.

Runtime animations include the painted wheel rotating in its elliptical
footprint, complete registered water regions, chimney wisps, lantern light and
occasional distant birds. Twenty-four water overlay frames animate the full
course with faster falls and slower surface motion. The original scenery
remains a single master image.

`eldenmere_theme.wav` is the lossless master of an original 88.89-second stereo
theme; `eldenmere_theme.ogg` is the smaller runtime export. It moves through
Home, Curiosity, Fragility and Return in 6/8 at dotted-quarter = 54, with D-major
and B-minor treatments of a recurring motif. Flute, harp, warm strings, pizzicato
answers, bass and sparse bells use expressive envelopes and stereo reverb.
`music_score.json` preserves the arrangement and note events. It uses no external
recordings or sample libraries. The music loops, can be muted in Settings, and
fades out on New Game. Headless verification does not initialize music.

The two bundled DejaVu fonts have their license and attribution in
`assets/ui/fonts/LICENSE-DejaVu.txt`. Only Pygame is required by the game;
Pillow and NumPy are used to build artwork/audio and capture review images;
FFmpeg encodes the runtime Ogg and review video.

Reproduce assets:

```sh
python tools/export_title_art.py
python tools/build_title_water.py
python tools/build_title_music.py
```

The theme does not change gameplay music, which is not implemented yet.
