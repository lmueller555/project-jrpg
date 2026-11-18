# Mira Bolt Shot clack

`bolt_clack.wav` is the first 65 ms of the retained Kenney Starter Kit FPS
`fps_weapon_change.ogg`, converted from 96000 Hz to 44100 Hz stereo PCM16.
The original recording, provenance manifest and MIT license remain unchanged in
`../ice_reaper_rescue/`. `bolt_clack.json` records source/output hashes and license.

This scoped conversion avoids SDL_mixer returning an empty decoded sound for
that 96 kHz Vorbis file at the battle's ordinary 44100/48000 Hz output rates.
It changes no global mixer setting and no other cue. The existing audio player
applies its usual short fade and effects-volume/cue gain. It is a dry mechanism
clack, with no blaster tail or explosion.

Rebuild: `python tools/build_mira_bolt_clack.py` (ffmpeg required).
