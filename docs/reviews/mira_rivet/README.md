# Mira, Rivet, and Overclock production review

[Watch the silent production capture](rivet_combat_silent.mp4) · [Native stills](contact_sheet.png) · [Video frames](video_contact_sheet.png) · [Launcher details](launcher_world_detail.png)

The video shows the carried bolt launcher, authored MQ02 entry, Rivet deployed
with empty ATB, Mira's real Skills → Overclock input, and the five-MP deduction.
Haste applies at impact with eight bot turns and a 1.5× charge rate. Caelan's
unarmed Skills command stays disabled. Rivet attacks autonomously; the charge
target chooses Guard before the Tusker hits. Victory clears bot combat state,
Spoils awards once, and the real walk and intake inspection stow the launcher.

This is a **silent preview**: 1804 direct production frames at 30 FPS,
960×640, lasting 60.13 seconds. Native screenshots are 480×320;
`06_haste_150.png` uses the production 150% text setting at that minimum window.
The game supplies all sprites, effects, status, captions, command bounds, and UI.
The contact sheet only assembles those rendered frames.

Only MQ01 completion and prelude interaction-station placement are fixtures.
MQ02 conversations are acknowledged normally; prelude and aftermath prose is
condensed in the combat-focused edit. Combat and the post-battle walk advance
through ordinary timed `Game.update`, input, and draw calls. The seeded RNG is
7; HP, MP, ATB, phases, and action/animation timers are never overridden.
Journey and settings files live in a temporary directory.
World announcement timers also finish normally; 8.73
seconds of idle waiting is omitted from the video for the two clear world stills.

Observed action starts: {'overclock': 1, 'attack': 2, 'piston_jab': 5, 'tusk_strike': 1, 'bolt_shot': 3, 'prepare_charge': 1, 'guard': 1, 'tusker_charge': 1}. Piston Jab damage:
[65, 71, 69, 67, 69]; guarded charge damage:
[36]. Exact command inputs, start/impact events,
Haste application/ticks, zero-state cleanup, and screenshot text observations
are in [verification.json](verification.json). No per-frame state dump is used.

Runtime and source files were fingerprinted before and after capture and matched.
Full file SHA-256 values are in [fingerprints.json](fingerprints.json).

- renderers: `2ae5cf7a363de6cf7c7706c36db88a8b06c2322ed52d573fd42e1848e2fe5871`
- rules_and_story: `9b7a0a6848cb80dcd82d3a0e6e07b33ec834039985501cbfbd22ed4901e2f3a0`
- runtime_art: `6ab1e76351d071c453a1eb77450e26b44db2b86cf9f0a20fe6fa787383e85928`
- art_sources_and_capture: `935000e3d0bf701c4c353144a5c3f1b5e759cb047776f7f1a2bf3cc8403d372e`

Reproduce from the repository root:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  /workspace/.venvs/project-jrpg/bin/python tools/capture_rivet_combat.py \
  --output docs/reviews/mira_rivet
```

## Regression verification

All 347 selected regression checks pass, followed by five final gameplay/save checks that include pending-victory reload cleanup and once-only Spoils. See the [commands, final fingerprints and media hashes](validation.json) and [test logs](tests.txt). Independent code and visual reviews pass.
