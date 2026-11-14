# Daisy's static resting pose source

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

The approved `idle_left.png` supplies the head, floppy ear, body markings, paws
and tail. The builder translates head/torso down, folds the legs with the same
fur palette, and rotates the plume clockwise around its root so it lies beside
her. `parts/` reconstructs the complete one-frame sprite. `recipe.json` records
the native offsets, joints and source hash.

Build with `python tools/build_liam_household_assets.py`; the final pose is in
`assets/characters/daisy/lying_left/`. Existing idles and walks/runs are read-only.
