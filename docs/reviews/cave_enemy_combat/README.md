# Lithrusk and Veylume combat review

[Animated sprite board](sprite_animations.gif) · [Sprite contact sheet](sprite_contact_sheet.png)
· [Silent in-engine reel](combat_reel_silent.mp4) · [Battle contact sheet](battle_contact_sheet.png)

The sprite board displays every production state at two-times native pixel
size. Each tile repeats its state for inspection; frames come directly from the
retained species animation manifests. The PNG selects a representative pose.

The silent reel uses real Game/BattleScene encounters on the existing Eldenmere
review stage. Caelan uses normal Guard and Attack mouse commands, real ATB and
the approved same-level offensive stats. An initial copied profile grants
9,999 HP solely to sustain the review until both Veinflashes and the free
Static Spark fallback are seen. Included action clips run at their actual
timing; charging waits and repeated actions are omitted. Hurt and defeat result
from ordinary attacks. No battle phase, gauge, MP or animation clock is injected.

Temporary settings and in-memory saves isolate the review from player files.
No world encounters are placed, and no rewards or quest progress are settled.
This is a combat presentation review, not a cave walkthrough or encounter
balance demonstration. Elemental relationships remain authoring metadata.

Reproduce with `python tools/capture_cave_enemy_combat.py`; verify current
sources and retained artifacts with `python tools/capture_cave_enemy_combat.py --check`.
