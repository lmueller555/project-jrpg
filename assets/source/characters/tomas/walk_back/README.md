# Back-walk source components

`parts/` retains head, upper body/collar, waist and tunic hem from the approved back idle. Eight full-frame layers per phase reconstruct the native exports in the order listed by animation metadata. The knee-patch layers are transparent when the patch is hidden.

The recipe at `assets/characters/tomas/walk_back/recipe.json` records appearance and shared template paths, directional collar/garment regions, arm registration, leg splits, ankle-boot boundaries and patch coordinates. No new appearance concept or edited idle is introduced. The patch is on the front of the left knee and faces away from the back view; no eyes are visible.

Run `python tools/build_tomas_walk.py --direction back` from the repository root. Inputs remain read only; this animation awaits review.
