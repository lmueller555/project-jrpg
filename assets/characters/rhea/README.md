# Rhea Sorel — first sprite studies

**Status:** All three sprite designs approved by the user. The approved character foundations are in the
[companion guide](../../../docs/narrative/game_01/COMPANIONS.md).

Blonde hair, blue eyes, fitted emerald green dress with a thigh slit, brown boots and a field-notebook pouch. Her purple tanglewood staff cradles a glowing green orb. The same appearance is retained across all three poses.

- Front overworld idle: [idle_front.png](idle_front.png), 24×36 pixels.
- Combat-ready pose: [idle_01.png](../../combat/rhea/idle_01.png), 64×64 pixels, facing left.
- Cinematic standing pose: [stand_front.png](../../cinematics/companions/rhea/stand_front.png), 96×112 pixels.

The front idle uses foot anchor [10, 34]. Combat uses [32, 54] and cinematic
uses [48, 104]. Read the adjacent metadata when positioning each image.

These are authored static base poses for further animation and scene work.
Generated sources, prompts and extraction recipes are retained under
[the source directory](../../source/companions/rhea/source.json).
The [comparison and scene-scale boards](../../../docs/reviews/companion_sprites/README.md)
show their actual native pixels with whole-number enlargements.

Rebuild with the repository's asset environment:

    python tools/build_companion_sprite_studies.py --actor rhea

## Front walking animation

The [four-frame front walk](walk_front/README.md) is approved, with a
[loop preview](../../../docs/reviews/companion_front_walks/rhea_front_walk.gif).
