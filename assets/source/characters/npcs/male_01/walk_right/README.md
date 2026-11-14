# Male NPC 01 — right-walk parts

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Status: walking animation approved by the user in chat.

The approved right idle supplies the head and appearance. The common builder retains its head/face pixels, prepares the torso and waist, materializes the shared posed arms, and recolors the shared leg silhouettes to tan trousers and brown boots. `parts/` contains the appearance layers, limb references, posed arms and recolored legs for all four phases.

The recipe is `../../../../../characters/npcs/male_01/walk_right/recipe.json`. Rebuild with `python tools/build_character_walk.py npcs/male_01 --direction right`. All motion comes from the approved directional pose template; no new generative artwork is used for these walking frames. The upper-body offsets are `[0, 0]`, `[0, -1]`, `[0, 0]`, `[0, -1]`. The original idle and front-walk artwork are unchanged.
