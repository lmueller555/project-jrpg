# Male NPC 01 — right-walk parts

Status: draft animation awaiting user review.

The approved right idle supplies the head and appearance. The common builder retains its head/face pixels, prepares the torso and waist, materializes the shared posed arms, and recolors the shared leg silhouettes to tan trousers and brown boots. `parts/` contains the appearance layers, limb references, posed arms and recolored legs for all four phases.

The recipe is `../../../../../characters/npcs/male_01/walk_right/recipe.json`. Rebuild with `python tools/build_character_walk.py npcs/male_01 --direction right`. All motion comes from the approved directional pose template; no new generative artwork is used for these walking frames. The upper-body offsets are `[0, 0]`, `[0, -1]`, `[0, 0]`, `[0, -1]`. The original idle and front-walk artwork are unchanged.
