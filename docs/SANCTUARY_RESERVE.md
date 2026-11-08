# Elden Vale Sanctuary reserve

The regional miniature opens into a detailed, peaceful woodland reserve built
from the same native pixel asset packs as Eldenmere. The layout follows the
sanctuary reference: southern entrance arch and court,
pale limestone hall and side cloister, a tended memorial grove to the west,
the cave approach on the eastern ridge, and a surveyed stone face within the
southeastern protected boundary.

The [fantasy expansion](SANCTUARY_FANTASY.md) gives the cave an asymmetric crown
of amethyst, cyan, opal and amber crystals. A silver-green memorial tree,
carved architectural details, buried masonry and reflecting water repeat the
same materials through the grounds. Native pixel assets remain independently
placed, with slow local animation and restrained positional ambience.

The site remains separate from Serene's home in Eldenmere. It was deliberately
constructed near the natural aether confluence to guide the region's dead back
to the planet and remember them. Its living grove and shared keeping serve
that responsibility, as established in
[the faith guide](world/ELDEN_VALE_FAITH.md) and
[the covenant](world/SANCTUARY_COVENANT.md).

## Exploration

Walk onto the sanctuary miniature on the overworld to enter at the southern
woodland approach. The main paths form a continuous circuit around the court,
grove, hillside and cave approach. Gentle paths pass around rock shelves; no
decorative staircase stands across the route. Buildings, trees, walls, benches
and rock faces have solid footprints consistent with the full player probe.
Visible open ground is freely walkable, including grass beyond the paths,
shaded grove clearings, northern shoulders and survey margins. Three open
cloister bays can be entered from the court; their columns, rear wall and the
eastern garden workstation remain solid. The bays are assembled as open floors,
separate columns, arches and roof pieces, with collision at their physical bases.

The hall is a separate, enterable scene with quiet seating and a records table.
Its exit returns to the sanctuary court. The southern reserve exit returns to
the overworld near the miniature, and the existing Eldenmere entrance still
returns to the village's southern road.

Press **M** to inspect the local reserve map. It shows the sanctuary grounds,
current position and named places, with short descriptions for each landmark.
The same control closes the map and returns to exploration.

Caretakers and visitors are live sprites rather than people painted into the
scenery. Optional conversations and inspections introduce local care,
remembrance, the natural aether currents and the proposed stone survey. They
grant no items, attributes or quest completion. Subtle moving motes communicate
the confluence without revealing an ancient mechanism.

## Story boundaries

The cave mouth is an exterior point of interest. A visible keeper rail closes
the inner opening while leaving the public apron and inspection accessible.
Its dungeon, enemy encounters,
miniboss and Caelan's first elemental Edge remain later quest work. It is
distinct from the historically sealed workers' passage beneath the sanctuary.

[Cave Bat](BESTIARY.md#cave-bat) is authored in the Bestiary as a level-2–3
species for the eastern-ridge caves. Its data and isolated combat adapter are
available, while encounter placement and the cave dungeon remain future quest
work. The peaceful reserve and keeper rail retain their current behavior.

During the new MQ03 route, a survivor exposes the Crown crew Aldric secretly
sent ahead to establish authority and prepare mining. Caretakers have heard
growling since the bridge incident; the attack's cause and the creature's
identity remain unresolved. Aldric, Lucan, the page, Caelan and Mira arrive
with MQ03 still active. The arrival cutscene, crew staging and exact extent of
the work completed before the attack remain later scene work. Existing survey
art is not evidence that the emergency has been resolved or permission granted.
The guarded regional gates and destroyed western bridge retain their restrictions.

The reserve and hall use their own scene identities while preserving old save
keys and the town's quest actor
ownership. Continuing a journey saved here resumes in the corresponding scene.

## Review and reproduction

The [current fantasy review](reviews/sanctuary_fantasy/README.md) records the
landmarks, ordinary movement, atmosphere, hall, local map and continued journeys.
The earlier [pixel asset review](reviews/sanctuary_pixel_assets/README.md) records the
reserve and hall at normal character scale, ordinary travel from Eldenmere,
free exploration, the cloister, cave rail, optional inspections, local map and
Save/Continue. Its disposable save and settings files leave player journeys
untouched. Reproduce with `python tools/capture_sanctuary_reserve.py`.

The exterior retains its 48 × 32 tile extent at 24 pixels per tile. Emerald grass
and matching dirt transitions use the shared approved pack. Ordinary foliage,
flowers, benches, paving and masonry reuse Eldenmere modules. Sanctuary-specific
crystals, memorial vegetation, architecture, rock and cave pieces extend those
packs at the same character scale.
The hall uses modular floors, walls and individual furnishings.

Ground layers are compiled for runtime efficiency. Trees, architecture and
furniture remain separately placed, depth-sorted objects. Asset placements own
their solid ground footprints; visible open ground accepts the complete
24 × 12 player probe. Full-foot flood, straight movement, independent occlusion
probes and saved-scene tests check the resulting world. The local map uses an
overview compiled from these same assets.

The previous painted ground, extracted depth silhouettes and localized repair
patches have been removed from the scene pipeline. Source asset references and
deterministic build checks make the replacement reproducible.

Rebuild the checked-in scenes with Pillow available:

```sh
python tools/build_sanctuary_crystals.py
python tools/build_sanctuary_grove.py
python tools/build_elden_vale_sanctuary.py
python tools/build_sanctuary_reserve_hall.py
python tools/build_overworld_sanctuary_art.py
python tools/build_sanctuary_crystals.py --check
python tools/build_sanctuary_grove.py --check
python tools/build_elden_vale_sanctuary.py --check
python tools/build_sanctuary_reserve_hall.py --check
python tools/build_overworld_sanctuary_art.py --check
```

The exterior placement recipe is
[`assets/source/maps/elden_vale_sanctuary/recipe.json`](../assets/source/maps/elden_vale_sanctuary/recipe.json).
The interior recipe is
[`assets/source/terrain/elden_vale_sanctuary_hall/recipe.json`](../assets/source/terrain/elden_vale_sanctuary_hall/recipe.json).
Their exports record the reusable source assets and their hashes. Runtime
exploration uses the checked-in products and requires no asset-building tools.
