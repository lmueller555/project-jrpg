# Mira combat sprite redraw

[Before / updated / Caelan comparison](before_after.png) · [All 42 drawings](sprite_sheet.png) · [Animated sprite board](sprite_animations.gif) · [Silent battle reel](mira_combat_reel_silent.mp4) · [Current battlefield](normal_battle.png)

Mira now uses 42 whole-body drawings with her ponytail, left-side flower,
rolled pink shirt, utility pouch, consistent launcher and articulated two-handed
grip. Eight shot drawings cover raising, aim, release, recoil and recovery.
Guard entry, held guard and guarded impact are separate from ordinary hurt.
Overclock secures the launcher and handles the controller. Victory and
incapacity finish on held poses. Four walk drawings preserve alternating feet.
The comparison assembles actual pre-redraw and updated exported sprite pixels
at the same scale and floor, with Caelan's unchanged idle for scale.

The 19.30-second silent reel renders the actual BattleModel and BattleScene at
960×640, 60 FPS. Its seven isolated cases show Bolt Shot, Overclock, guarded and
unguarded incoming hits, Reduced Motion Bolt Shot, actual victory, and Mira's
incapacity with Rivet suspended. No sprite pixels or presentation poses are
substituted during the production rendering. The animated sprite board only
assembles exported PNGs; it repeats one-shot states after a readable hold for
review.

The isolated fixtures are a durable passive Tusker (1,000,000 HP, Speed 0), RNG
seed 7, Mira's gauge set ready before ordinary command clicks, and explicitly
selected incoming tusk strikes. The victory case starts its enemy at 1 HP;
the incapacity case starts Mira at 1 HP. Damage formulas, action definitions,
impact events and animation clocks run normally. No journey or settings file
is read or written.

Bolt Shot remains 0.80 seconds with damage at 0.40; the bolt now leaves the
registered muzzle at 0.28 seconds and travels to the target silhouette.
Overclock remains 0.90 seconds, applying eight bot turns at 0.50 and costing
5 MP. Observed shots deal 50 damage; incoming hits deal 24 unguarded or 12
guarded. `minimum_large_text.png` renders the minimum 480×320 window at 150%
text; `normal_battle.png` and `reduced_motion.png` use the normal window.

[Verification](verification.json) lists all declared fixtures, action/event
observations and screenshots. [Fingerprints](fingerprints.json) show that
production rules, sprite sources and exported art stayed unchanged throughout
the capture.

Reproduce from the repository root:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  /workspace/.venvs/project-jrpg/bin/python tools/capture_mira_redraw.py
```

Asset validation: five Mira redraw checks plus eight MQ02 asset checks pass.
They verify anatomical floor registration, sprite/attachment clock agreement,
weapon release placement, action durations, distinct brace/hurt drawings,
unclipped binary-alpha exports, source provenance, and the unchanged overworld
launcher.

## Complete MQ02 playthrough

[Full MQ02 production capture](mq02/mq02_gear_combat_silent.mp4) · [Verification](mq02/verification.json) · [Victory](mq02/victory.png) · [Settled Spoils](mq02/spoils.png)

The unchanged `tools/capture_gear_combat.py` driver also completed a fresh
90.97-second production MQ02 recording with the final Mira artwork. It receives
the sword through dialogue, completes the Guard lesson, fails the first matching
elemental attempt, discovers Aether Edge on the next attempt, uses Overclock and
three Bolt Shots, and reaches victory and settled Spoils. Actual combat clocks,
HP, MP, ATB and damage are not overridden; only the prior MQ01 public-API handoff,
prelude station placement, and RNG seed 7 are fixtures. Source fingerprints
remain unchanged throughout. Selected stills and the full production movie are
retained here; the driver's auxiliary four-gem reel is outside this review.

Reproduce the complete original driver output in a scratch directory with:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  /workspace/.venvs/project-jrpg/bin/python tools/capture_gear_combat.py \
  --output /workspace/work/mira_mq02
```

## Final regression verification

All **375 targeted tests and 854 subtests pass** across 37 combat, gear, bot,
Mira and cinematic modules. See [validation](validation.json) and [test output](tests.txt).
Two stale test helpers were corrected: the battlefield fixture now supplies its
UI surface, and the Rivet tutorial helper selects the Edge matching the settled
gem. The original main reproduced all six affected failures; correcting only
those fixtures also passes on that baseline. No combat rules were changed.
