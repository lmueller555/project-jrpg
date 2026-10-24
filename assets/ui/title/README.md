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

`eldenmere_theme.wav` and `eldenmere_theme.ogg` now contain the replacement
93.33-second sampled piano/cello score, **A Place to Return To**. The former
flute/harp track is discarded. The new piece uses 4/4 at a fixed 72 BPM, with
quarter-grid entrances/releases and calibrated sample attacks. Its G-major
melody receives a cello answer and restrained strings before a quiet return.
`music_score.json` records note events, sample-clock timing and attack offsets.
See `assets/source/audio/title_piano_cello/` for the GeneralUser GS sample
license/provenance, and `docs/reviews/title_piano_cello/` for clean and metronome
excerpts. Music still loops, mutes in Settings and fades out on New Game.

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

The theme does not change gameplay music, which is not implemented yet.
