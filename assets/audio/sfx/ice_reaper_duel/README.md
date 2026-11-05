# Ice Reaper duel effects

Nine finite 48 kHz stereo effects accompany Rhea's staff sweep and wind blast,
the two snow landings, the Reaper's ice sword, six rune-point fireball ignitions,
the fire presence during the orbit, and the final windup and charge.

The fourteen new cues span 24.00–30.30 seconds on the uninterrupted cinematic
clock. Their finite tails resolve by 31.95 seconds, before the 32-second fade
finishes. The six flame ignitions use restrained gains to retain headroom when
their transients overlap. The fire bed remains quiet beneath Wintermute 2.

Sources are the retained MIT Kenney foley and the game's previously designed
rescue effects. `manifest.json` records exact source hashes, upstream commits,
license locations, output hashes and cue positions. Filtered, seeded noise and
sparse stereo reflections add wind, flame and ice texture. Music and all thirteen
earlier cues remain unchanged.

Rebuild offline from the repository root:

```sh
python3 tools/build_ice_duel_audio.py
```

The build requires NumPy and FFmpeg. Vorbis outputs use bit-exact muxing flags;
no music file or earlier sound file is modified.
