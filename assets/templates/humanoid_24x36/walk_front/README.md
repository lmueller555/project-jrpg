# Shared front-walk pose template

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

This template extracts the limb poses from Caelan's approved front walk. It contains four phases at 140 ms each and the shared `[12, 34]` foot anchor on a 24×36 canvas.

Each `frame_01`–`frame_04` directory contains:

- `left_arm_mask.png` and `right_arm_mask.png`: screen-left/right arm silhouettes with semantic material codes defined in `poses.json`. These include the approved shoulder/arm motion; the passing-phase shoulder rise is already baked in.
- `legs.png`: the exact approved lower-leg/boot pixels from rows 26–35, as a paired pose component. The existing consumers reuse those exact trousers/boots pixels.

The masks separate pose geometry from costume colors. Mira uses pink sleeve materials and bare forearms in place of the source costume's sleeve/cuff colors. Her own head, shirt, waist and pouch are assembled around the posed limbs. The extraction excludes Caelan's hanging tabard from the forearm masks.

This retained template separates pose pixels from material colors and is not
a runtime skeletal rig. Its masks support reproducing the existing packs.
New costumes and body types follow the global standard's complete-drawing
workflow rather than extending this legacy limb-mask construction method.

## Rebuild

Install `tools/requirements-assets.txt`, then run from the repository root:

```sh
python tools/build_character_walk.py mira --refresh-template
```

This refreshes the shared masks from the approved references and assembles Mira. For subsequent appearance changes, `python tools/build_character_walk.py mira` uses the retained masks. Reference sprites are read-only inputs.
