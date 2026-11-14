# Female NPC 01 — left-walk assembly

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Status: approved by the user in chat.

Rebuild with `python tools/build_dress_walk.py --direction left`. The appearance comes from the approved `idle_left.png`; stride silhouettes, arm poses, timing and bob come from the shared left template. The character recipe contains explicit skirt rows, leg split columns and ankle-boot tops for each phase.

`parts/` retains head and bodice appearance inputs plus every posed compositing layer. `animation.json` records the exact order and paths from the repository root. Profile arm masks exclude the shared character's neck pixels, and the approved neckline is restored above the arms before compositing the head. The back head has no eye features; profiles retain the blue iris. These appearance sources and shared templates remain unchanged.

Skirt poses resample approved native dress pixels by row without interpolation, fill previously covered hand areas with dress colors and add outline edges. No generated replacement appearance is used. Contact hems are at row 28, passing hems at row 27, with at most one pixel of horizontal skirt sway. Calf and boot colors use the existing named material ramps. The arm and leg masks are read only; costume adjustments live in the character recipe and derived parts.

The profile head now includes the three-pixel closed-mouth jaw cleanup from the directional appearance exporter; this appearance revision is approved by the user.
