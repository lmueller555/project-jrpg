# Companion sprite study sources

The lucan, rhea and edran folders each preserve an imagegen-authored transparent
design sheet and a source.json provenance/extraction recipe. Each source has
three isolated poses: front overworld idle, left-facing combat-ready stance
and detailed cinematic standing. Prompts are retained with the sources.

The production textures are derived by uniform nearest-neighbor scaling,
binary-alpha export, palette reduction and foot registration. The exporter
never redraws limbs or stretches separate axes. Explicit panel crops preserve
weapons and hands that extend beyond an evenly divided source column.

Rebuild with:

    python tools/build_companion_sprite_studies.py

The [review boards](../../../docs/reviews/companion_sprites/README.md) show all
native outputs and a comparison with Caelan. All three characters’ base sprite
designs are approved, including Edran’s sky-blue and silver revision. Source
recipes record the individual approvals. Approved biography facts live in the
[companion guide](../../../docs/narrative/game_01/COMPANIONS.md).
