# Sanctuary fantasy assets

Elden Vale Sanctuary combines emerald woodland, luminous mineral growth and
weathered pale stone around its natural aether confluence. The eastern crystal
ridge and western memorial tree are its principal landmarks. The hall, spring,
buried masonry and signs of ongoing care repeat their colors and carved forms.

The cave formations use amethyst and cyan with opal and smaller amber accents.
Their facets shimmer slowly while their roots and silhouettes stay fixed. The
grove's intertwined tree has a silver-green crown, related saplings and sparse
blossoms. The courtyard water and architectural inlays carry these materials
into quieter public spaces. The regional miniature and hall details follow the
same visual language.

These are native pixel modules at the existing terrain and character scale.
Independent ground, roots, trunks, canopy, architecture and atmospheric layers
are composed by the Sanctuary map builder. The source recipes retain palettes,
anchors, animation timings and asset provenance. The compiled overview uses
the same placed objects as gameplay.

## Exploration and meaning

The reserve retains its existing entrance, hall doorway, open cloister bays,
woodland circuit, inspections, survey site and closed cave rail. The approved
emerald grass continues to part around characters. Decorative floor fragments
do not introduce movement barriers; large scenery uses visible physical bases.
The scene identities and travel links remain compatible with existing journeys.

Both the reserve and hall retain their previous collision masks byte-for-byte.
Public approaches, the woodland circuit, doors and inspection geometry are
unchanged. All 96 interactive grass placements are retained.

The Sanctuary was deliberately built near this natural confluence to guide
the region's dead back to the planet and remember them. Mining would disrupt
that duty. The visual effects do not define the guidance mechanism, establish
an Aethersphere link, identify the original sacrificial temple or assign souls
to memorial trees. Crystal colors do not establish elemental affinities or
mining rewards.

The new MQ03 emergency journey reaches an arrival checkpoint after exposing
Aldric's secret crew and its attack. The existing survey art does not stage
that crew or resolve the new event; the arrival cutscene and cave dungeon
remain future story work. Growling heard since the bridge incident foreshadows
the coming encounter without identifying the creature or establishing a cause.

Local sound respects effects volume, focus, menus and scene changes. Reduced
motion retains the finished composition while holding optional atmospheric
animation still. The existing music remains in use.

## Review and reproduction

The crystal and grove recipes live in
`assets/source/terrain/sanctuary_fantasy/`. Their corresponding
`assets/terrain/sanctuary_fantasy/` manifests export reusable frames and material
boards comparing the assets directly with Caelan. Use
`tools/build_sanctuary_crystals.py` and `tools/build_sanctuary_grove.py` to rebuild
them; each supports `--check` without writing files.

The [production review](reviews/sanctuary_fantasy/README.md) records actual
travel, movement, landmark depth, the hall, reduced motion and Save/Continue.
It uses disposable journey and settings files.

Reproduce with `python tools/capture_sanctuary_fantasy.py`; use `--check` to
verify the retained source and artifact fingerprints. The annotated placement
sheet is a diagram; the gameplay screenshots and video use the production
renderer and ordinary movement.

See the [reserve guide](SANCTUARY_RESERVE.md) for exploration and scene build
commands, the [faith guide](world/ELDEN_VALE_FAITH.md) for the established
spiritual foundations, and the [covenant](world/SANCTUARY_COVENANT.md) for the
reserve's public responsibilities and unresolved history.
