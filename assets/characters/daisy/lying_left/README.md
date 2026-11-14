# Daisy — still lying pose, approved

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

`pose.png` is a single 40×36 RGBA sprite with draw anchor `[20,30]`. It preserves
the approved left-facing face, coat colors, black flank patch, floppy gray ear
and native paw pixels. The chest is lowered, legs folded, and fluffy tail laid
beside her. Daisy is awake; this pose has no animation or routine.

`pose.json` links the source idle hash, palette and complete retained layers.
Build with `python tools/build_liam_household_assets.py`. See the
[household preview and rug close-up](../../../../docs/reviews/liam_household/README.md).
