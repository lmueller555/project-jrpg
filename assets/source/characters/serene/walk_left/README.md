# Left-walk source components

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

`parts/` retains head, shoulder mantle and bodice appearance from the approved left idle, plus seven ordered full-frame compositing layers per phase. `assets/characters/serene/walk_left/recipe.json` records source paths, mantle/bodice bounds, eye landmarks, costume row poses and calf/boot boundaries. Animation metadata lists the layer order for exact reconstruction.

The approved directional stride masks and timing remain unchanged. Both head and the complete short mantle share the passing bob. Directional costume rows retain apron details where visible and fill sage cloth beneath the idle hands; no new appearance concept or changed idle is introduced. This animation is approved.

Run `python tools/build_serene_walk.py --direction left` from the repository root.
