# Vespermaw combat art review

[Animated sprite board](sprite_animations.gif) · [Sprite contact sheet](sprite_contact_sheet.png)
· [Silent cave art reel](cave_art_reel_silent.mp4) · [Cave contact sheet](battle_contact_sheet.png)

The sprite board displays every retained state at twice its native pixel size.
It samples the actual animation manifest clock at 50 FPS; non-looping actions
repeat for inspection after a short final-pose hold. Each individual exported
pose appears in the board, and verification records frame counts and durations.

The cave reel renders the same poses through the production BattleScene at
their manifest clocks. This is an explicitly visual-only fixture: it uses
ordinary Bat rules with Vespermaw's name and art, a copied level-seven party,
and a directly sampled enemy pose clock. It does not run Vespermaw's pending
party-wide damage, marked-target response rules or recovery vulnerability.
Its HP/ATB bars are fixture UI, not a boss balance demonstration.

Separate native 480×320 captures use 150% text. No Game instance or user save,
settings, inventory, quest or reward settlement is involved. The boss remains
excluded from random encounters and its canonical combat implementation gate
remains in place.

Reproduce with `python tools/capture_vespermaw_combat.py`; verify with
`python tools/capture_vespermaw_combat.py --check`. Use `--output /tmp/vespermaw-review`
for disposable alternative captures.
