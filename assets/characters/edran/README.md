# Edran Hale — first sprite studies

**Status:** All three sprite designs approved by the user. The approved character foundations are in the
[companion guide](../../../docs/narrative/game_01/COMPANIONS.md).

Salt-and-pepper hair and a short beard, a sky-blue long robe with a high collar and capelet, silver trim and sash, slate-gray boots and healer pouch, and an ashwood crook with silver fittings.

- Front overworld idle: [idle_front.png](idle_front.png), 24×36 pixels.
- Combat-ready pose: [idle_01.png](../../combat/edran/idle_01.png), 64×64 pixels, facing left.
- Cinematic standing pose: [stand_front.png](../../cinematics/companions/edran/stand_front.png), 96×112 pixels.

The front idle uses foot anchor [12, 34]. Combat uses [32, 54] and cinematic
uses [48, 104]. Read the adjacent metadata when positioning each image.

These are authored static base poses for further animation and scene work.
Generated sources, prompts and extraction recipes are retained under
[the source directory](../../source/companions/edran/source.json).
The [comparison and scene-scale boards](../../../docs/reviews/companion_sprites/README.md)
show their actual native pixels with whole-number enlargements.

Rebuild with the repository's asset environment:

    python tools/build_companion_sprite_studies.py --actor edran

## Front walking animation

The [four-frame front walk](walk_front/README.md) is approved, with a
[loop preview](../../../docs/reviews/companion_front_walks/edran_front_walk.gif).

## Remaining directional idles

The proposed [left, right and rear poses](../../../docs/reviews/companion_directional_idles/edran_directional_idles.png)
are ready for user review beside the approved front idle. See the
[directional review guide](../../../docs/reviews/companion_directional_idles/README.md)
for the source and export workflow.
