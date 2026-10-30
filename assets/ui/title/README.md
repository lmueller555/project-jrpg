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

The current title soundtrack is the user-provided **Eldenmere Theme** from
`assets/music/`, played through the shared `GameMusic` controller. It continues
into New Game or Continue and throughout Eldenmere and the millrace, with live
Music settings. See `assets/music/README.md` for the supplied originals,
compatible runtime exports and rebuild instructions.

The older `eldenmere_theme.wav`, `eldenmere_theme.ogg` and `music_score.json`
here retain the previous sampled piano/cello title score, **A Place to Return
To**, and its historical previews/provenance. They are no longer the default
soundtrack. `tools/build_title_music.py` rebuilds that historical score.

The two bundled DejaVu fonts have their license and attribution in
`assets/ui/fonts/LICENSE-DejaVu.txt`. Only Pygame is required by the game;
Pillow and NumPy are used to build artwork/audio and capture review images;
FFmpeg encodes the runtime Ogg and review video. FluidSynth and the documented
GeneralUser GS 2.0.3 SoundFont are needed to rebuild the sampled music.

Reproduce assets:

```sh
python tools/export_title_art.py
python tools/build_title_water.py
python tools/build_title_music.py --soundfont /path/to/GeneralUser-GS.sf2
```

Gameplay music now uses the shared catalog in `assets/music/tracks.json`; battle
entry and return switch between Eldenmere Theme and Kindled Courage. Victory
uses the one-shot Triumphal Fanfare, followed by silence on Spoils until Continue.
