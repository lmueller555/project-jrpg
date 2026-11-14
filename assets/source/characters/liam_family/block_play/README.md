# Wooden-block action source layers

**Existing asset / legacy construction reference.** New or revised artwork
follows the [global sprite and animation standard](../../../../../docs/SPRITE_ANIMATION_STANDARD.md).
Part, mask, layer and registration recipes below document this pack's existing
implementation and reproduction, not the authoring method for new animations.
Approval records and original review evidence are retained.

Rebuild with `python tools/build_liam_blocks.py`. Action folders retain four
sets of transparent body/head/legs/hand layers. The runtime manifest records
composition order, hand/nose landmarks, contacts and original character hashes.
Daisy's curious sniff retains the original body/paws/tail and moves head/ear
layers only. Do not edit only the flattened runtime exports.
