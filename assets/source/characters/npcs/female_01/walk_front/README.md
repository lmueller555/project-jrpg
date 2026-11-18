# Female NPC 01 — front-walk assembly

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Status: approved by the user in chat. Source idle and shared reference animations remain unchanged.

`python tools/build_dress_walk.py` reads the approved female front idle and palette, the shared `humanoid_24x36/walk_front/poses.json`, and the character's `walk_front/recipe.json`. It retains appearance parts and writes per-phase legs, skirt, bodice, left arm, right arm and head layers to `parts/`. Their recorded compositing order reconstructs each native frame.

The existing shared builder supplies appearance extraction, semantic arm recoloring, translation and nearest-neighbor previews. Shared leg masks supply the stride silhouette; the dress builder assigns calf/ankle-boot materials using per-leg boot tops. The recipe supplies explicit skirt rows as `[source_y, left_inclusive, right_exclusive, sway_x]`, starting at native row 21. These fill previously covered hand areas without carrying idle hands into the skirt.

The head, neckline and upper bodice share the template's 0/-1/0/-1 pixel bob. Shared arm masks already contain shoulder motion. The lower bodice joins the fixed waist while contact skirts sway one pixel and passing hems rise one pixel. No interpolation, smoothing or new colors are introduced. Animation approval comes from the recipe and survives rebuilds.
