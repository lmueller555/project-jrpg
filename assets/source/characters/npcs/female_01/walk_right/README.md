# Female NPC 01 — right-walk assembly

Status: draft for review.

Rebuild with `python tools/build_dress_walk.py --direction right`. The appearance comes from the approved `idle_right.png`; stride silhouettes, arm poses, timing and bob come from the shared right template. The character recipe contains explicit skirt rows, leg split columns and ankle-boot tops for each phase.

`parts/` retains head and bodice appearance inputs plus every posed compositing layer. `animation.json` records the exact order and paths from the repository root. Profile arm masks exclude the shared character's neck pixels, and the approved neckline is restored above the arms before compositing the head. The back head has no eye features; profiles retain the blue iris. These appearance sources and shared templates remain unchanged.

Skirt poses resample approved native dress pixels by row without interpolation, fill previously covered hand areas with dress colors and add outline edges. No generated replacement appearance is used. Contact hems are at row 28, passing hems at row 27, with at most one pixel of horizontal skirt sway. Calf and boot colors use the existing named material ramps. The arm and leg masks are read only; costume adjustments live in the character recipe and derived parts.
