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
footprint, localized water glints, chimney wisps, lantern light and occasional
distant birds. The original scenery remains a single master image.

`eldenmere_theme.wav` is an original 24-second synthesized harp/flute-style
melody in D major, generated without external recordings or sample libraries.
It loops quietly on the title screen, can be muted in Settings, and fades out
when New Game is selected. No audio device is required for play. Headless
verification does not initialize music. The review GIF has no sound.

The two bundled DejaVu fonts have their license and attribution in
`assets/ui/fonts/LICENSE-DejaVu.txt`. Only Pygame is required by the game;
Pillow is used to export artwork and capture review images.

Reproduce assets:

```sh
python tools/export_title_art.py
python tools/build_title_music.py
```

The theme does not change gameplay music, which is not implemented yet.
