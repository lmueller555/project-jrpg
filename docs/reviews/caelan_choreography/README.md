# Caelan choreography review

[Choreography reel](caelan_choreography_reel_silent.mp4) · [Real MQ02 journey](mq02_choreography_silent.mp4) · [Phase contact sheet](contact_sheet.png) · [Decoded video frames](decoded_video_contact_sheet.png)

Silent production rendering at 960×640 and 30 FPS. The reel shows unarmed and
armed Attack, all four non-elemental Aether Edge focus colors, Aether Dart,
Guard, and guarded versus unguarded reactions to the Bat and Boar. Each action
uses production choreography, authored sprites, damage and impact timing.
Isolated reel fixtures are declared in [verification.json](verification.json).
Initial gauge charging is simulated normally and omitted from this short reel.

The full MQ02 video reuses the earlier capture driver, receives the weapon
through real dialogue, selects opening Guard, fails the first matching focus,
discovers Aether Edge on the next attempt, uses Mira's Overclock and Rivet,
then reaches victory and settled Spoils. Combat resources, gauges and animation
clocks are never overridden. Earlier quest progress, prelude placement and
RNG 7 are the only full-journey fixtures. The earlier capture script is unedited.

[Verification](verification.json) includes inputs, events, action counts and
phase timestamps. [Fingerprints](fingerprints.json) prove source and art stayed
unchanged throughout capture. Contact sheets only assemble rendered frames.

Reproduce: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_caelan_choreography.py`.

[QA results](qa.json): 62 scene tests pass, including 11 new choreography checks, the existing MQ02 lesson sequence and Rivet’s eight completed bot turns. Independent visual review found no blocking issues.
