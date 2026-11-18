# Playtime source layers

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Rebuild with `python tools/build_liam_daisy_play.py`. Each action retains four
sets of transparent source layers. The runtime animation manifest records the
ordered composition paths and the approved character source hashes. Bed quilt
and frame overlays reuse the approved furniture image without changing it.
