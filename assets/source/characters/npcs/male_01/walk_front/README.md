# Male NPC 01 — front-walk parts

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Status: front-walk animation approved by the user in chat.

The shared walk builder prepares these parts from the approved front idle and Caelan's retained pose templates. It preserves the head/face, crops the original waist and buckle, separates the shirt, materializes posed arms in the NPC palette and applies an explicit tan-trouser/brown-boot mapping to the shared leg poses.

`parts/` contains the head, shirt, waist, empty pouch layer, idle limb references, four pairs of posed arms and four recolored leg layers. The recipe is `../../../../../characters/npcs/male_01/walk_front/recipe.json`.

Rebuild with `python tools/build_character_walk.py npcs/male_01`. No new generative artwork is used for the walking frames. The head and shoulders share the template's `[0, 0]`, `[0, -1]`, `[0, 0]`, `[0, -1]` offsets; feet follow the approved shared stride.
