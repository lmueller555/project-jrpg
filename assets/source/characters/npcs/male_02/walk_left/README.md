# Male NPC 02 — left-walk parts

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Status: walking animation approved by the user in chat.

The approved directional palette idle supplies the head, face where visible and clothing appearance. These parts are assembled against the approved base male left recipe and retained shared pose masks. They preserve the exact arm/leg silhouettes, timing and coordinated head-and-shoulder bob while applying the existing shirt and trouser colors. Skin, belt and boots are preserved.

The recipe is `../../../../../characters/npcs/male_02/walk_left/recipe.json`. Rebuild with `python tools/build_npc_walk_variants.py --direction left` or use `--direction all` for all palettes/directions and the combined review grid. The base artwork and approved idles are read-only inputs; no new generative artwork is used for these walking frames.
