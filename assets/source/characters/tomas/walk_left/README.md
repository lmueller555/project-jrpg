# Left-walk source components

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

`parts/` retains head, upper body/collar, waist and tunic hem from the approved left idle. Eight full-frame layers per phase reconstruct the native exports in the order listed by animation metadata. The knee-patch layers are transparent when the patch is hidden.

The recipe at `assets/characters/tomas/walk_left/recipe.json` records appearance and shared template paths, directional collar/garment regions, arm registration, leg splits, ankle-boot boundaries and patch coordinates. No new appearance concept or edited idle is introduced. The patch follows the near anatomical left knee through the stride and lift; its coordinates remain inside trouser cloth.

Run `python tools/build_tomas_walk.py --direction left` from the repository root. Inputs remain read only; this animation is approved.
