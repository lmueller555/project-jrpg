# Ice Reaper rescue action effects

Eleven short stereo 48 kHz Vorbis effects support twelve one-shot cues in the
20-second Gallery cinematic. Timing and runtime gain are shared through
`ice_reaper_audio.CUES`; `manifest.json` records the same cue list and file hashes.
The music remains Wintermute2 and is not controlled by this package.

The retained source effects come from Kenney's Starter Kit FPS and Starter Kit
3D Platformer repositories, under their MIT licenses. Original files and the
unmodified licenses are in `source/`; repository URLs and exact revision IDs
are recorded in the manifest. These are game-library effects, not claims of
on-location snow, metal or ice recordings.

The build layers pitched source transients, filtered granular textures, damped
metallic resonances, bass impacts, short stereo reflections and broadband magical
swells. Snow and mechanical detail stay short and tactile; the shield and broken
ice have longer decays; the rune has a sustained low/airy release. Effects do not
replace the score. Source code and generated effects are retained for revision.

Rebuild offline from the repository root:

    PYGAME_HIDE_SUPPORT_PROMPT=1 python tools/build_ice_reaper_action_audio.py

Requires numpy and ffmpeg. The deterministic seed reproduces PCM design;
compressed bitstreams may differ with the installed encoder version.

The review capture mixes these same files at their runtime cue offsets/gains.
SDL dummy audio cannot provide hardware loopback; a reconstructed review mix is
identified as such in the capture report.
