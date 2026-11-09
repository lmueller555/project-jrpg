# Caelan gear combat review

**Historical capture:** This review predates Blue-only gem ownership and the
current automatic Aether discovery. It retains the earlier four-focus,
two-attempt sequence. See [current Caelan progression](../../CAELAN_AQUA_PROGRESSION.md).

[Production MQ02 combat](mq02_gear_combat_silent.mp4) · [Four-focus FX reel](four_gem_fx_silent.mp4) · [Contact sheet](contact_sheet.png) · [Decoded video frames](video_contact_sheet.png)

Both silent previews render the production battle scene at 960×640, 30 FPS.
The MQ02 capture begins from the public prior-quest handoff fixture, receives
Mira’s gift through the real scene, then shows the required Guard, matching-gem
first failure, next-turn Aether Edge discovery, global 25% hover charging,
ordinary party combat, victory and Spoils settlement. Selector changes use real
captured pointer gestures. No combat resources, gauges, phases or action timers
are overwritten. Only prior work, prelude station placement and RNG 7 are fixtures.

The separate four-focus reel uses an explicitly durable harmless Bat fixture,
and compares learned non-elemental Aether Edge with Nature, Water, Fire and Ice
selected. It creates no elemental unlocks and changes no damage definition.
The screenshot names `fx_*.png` mark the same action age in every focus.

[Verification](verification.json) records inputs, lesson events, normal action
counts, settlement and reel observations. [Fingerprints](fingerprints.json)
confirm production rules, rendered art and art source files stayed byte-identical
during capture. The contact sheet only assembles rendered frames.

Reproduce with:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  /workspace/.venvs/project-jrpg/bin/python tools/capture_gear_combat.py
```
