# Front-walk source components

`parts/` retains head, upper body, waist and tunic hem from Tomas's approved front idle. Eight full-frame RGBA layers per phase retain the legs, left-knee patch, waist, hem, two arms, upper body and head, in the compositing order listed by animation metadata.

The approved shared front template supplies four stride/arm phases and 140 ms timing. The recipe at `assets/characters/tomas/walk_front/recipe.json` registers shared arms to Tomas's narrower, shorter proportions, maps upper legs to trousers and positions the existing knee-patch color inside each left-leg pose. No new appearance concept or edited idle is introduced. The patch changes apparent size with foreshortening and stays on screen right. Both green eyes and the original neck/chest remain intact; head and shoulders share the passing bob.

Run `python tools/build_tomas_walk.py` from the repository root. All approved appearance/template inputs remain read only. This front walk awaits review.
