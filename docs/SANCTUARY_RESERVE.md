# Elden Vale Sanctuary reserve

The regional miniature opens into a detailed, peaceful woodland reserve. The
scene follows the approved sanctuary preview: southern entrance arch and court,
pale limestone hall and side cloister, a tended memorial grove to the west,
the cave approach on the eastern ridge, and a surveyed stone face within the
southeastern protected boundary.

The site remains separate from Serene's home in Eldenmere. Its living grove,
natural aether confluence and shared keeping retain the meaning established in
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
eastern garden workstation remain solid.
Localized floor patches open the three former low masonry panels so the
painting and the walkable space agree.

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

The survey marks remain beside intact limestone. Excavation has not begun, and
visiting the site does not resolve Aldric and Serene's disagreement or grant
permission to disturb the ground. The guarded regional gates and destroyed
western bridge retain their existing restrictions.

The Eldenmere music continues during this visit. The reserve and hall use their
own scene identities while preserving old save keys and the town's quest actor
ownership. Continuing a journey saved here resumes in the corresponding scene.

## Review and reproduction

The [scenery-depth review](reviews/sanctuary_depth/README.md) shows the corrected
overlap between Caelan and the trees, props, buildings and hall furniture.
Individual silhouettes use their own ground anchors; canopy gaps remain
transparent, and wall/cliff sections follow their sloping ground edges. Tree
collision follows the visible roots, allowing movement behind projecting
trunks and crowns. That depth correction retains the source painting; the
three open cloister bays use their own localized floor patches.

The [in-game review](reviews/sanctuary_reserve/README.md) records ordinary travel
from Eldenmere, the reserve circuit, hall entry and return, optional inspections,
and save/continue checks using disposable save and settings files. Reproduce
with `python tools/capture_sanctuary_reserve.py`.

The [free exploration review](reviews/sanctuary_free_roam/README.md) records
ordinary movement off the paths and into the three open cloister bays, the visible cave
rail, hall entry/exit, and Save/Continue on formerly blocked grass. Its
independent full-foot flood and direct movement regressions check broad open
ground as well as the remaining physical barriers. Reproduce with
`python tools/capture_reserve_free_roam.py`.
