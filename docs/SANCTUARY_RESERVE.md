# Elden Vale Sanctuary reserve

**Current runtime:** The reserve and cave remain freely explorable. Old MQ03
arrival/rescue actors, markers, conversations and automatic companion recruitment
are removed. The Sanctuary remains a natural confluence; its purpose in the
future [Fire Veinhold opening](narrative/game_01/CHAPTER_01.md) remains open.
The physical regional bridge is still ruined pending a later map/story phase.

The regional miniature opens into a detailed, peaceful woodland reserve built
from the same native pixel asset packs as Eldenmere. The layout follows the
sanctuary reference: southern entrance arch and court,
pale limestone hall and side cloister, a tended memorial grove to the west,
the cave approach on the eastern ridge, and an ordinary path-guide board within the
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
[the faith guide](narrative/world/ELDEN_VALE_FAITH.md) and
[the covenant](narrative/world/SANCTUARY_COVENANT.md).

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
An animated door in its north wall, beside a bed plaque, leads to a small visitor
relief room. Nessa tends the bed, fresh water and care supplies there. The hall's
main exit returns to the sanctuary court. The southern reserve exit returns to
the overworld near the miniature, and the existing Eldenmere entrance still
returns to the village's southern road.

Press **M** to inspect the local reserve map. It shows the sanctuary grounds,
current position and named places, with short descriptions for each landmark.
The same control closes the map and returns to exploration.

## Visitor relief room

Enter the hall from the Sanctuary court, then follow the bed plaque through the
north-wing doorway. The relief room has a proper bed, water table, clean linens,
care supplies, stained glass and a warm memorial lamp, assembled from the same
native pixel packs as the hall. Attendant Nessa welcomes travelers and those
keeping vigil. Both her dialogue and the bedside **E: rest** prompt offer an
explicit **Rest / Not now** choice, with no fee or quest prerequisite.

A short rest fully restores current HP and MP to each available travelling
member's effective maxima, including reserves and KO companions. Characters
unavailable elsewhere retain their resources. Levels, EXP, stats, modifiers,
inventory, equipment, party formation, story progress and the cave encounter
counter stay intact. There is no overnight time skip or quest completion.
The existing story music continues through the room and rest.

Recovery is saved before the completion message. A failed save restores the
previous resources and offers **Retry / Not now**. Walking away or changing
rooms before confirming cannot heal the party remotely. Saving and Continue
inside the room preserve its location; **M** uses the Sanctuary overview and
identifies the relief room. This rest point needs no quest or rescue state.

The independently rebuilt room is `elden_vale_sanctuary_relief`; its entrance
and return use normal reciprocal hall doors. Build it with
`python tools/build_sanctuary_relief_room.py`, and use `--check` to verify the
exports. The hall's doorway and plaque are part of
`tools/build_sanctuary_reserve_hall.py`. See the
[production room captures](reviews/sanctuary_relief/README.md).

Caretakers and visitors are live sprites rather than people painted into the
scenery. Optional conversations and inspections introduce local care,
remembrance, the natural aether currents and a path-guide board. They
grant no items, attributes or quest completion. Subtle moving motes communicate
the natural confluence without establishing a buried control mechanism.

## Story boundaries

At the cave apron, **E** enters the [crystal cave](SANCTUARY_CAVE.md). The cave
retains its layout, treasure, random encounters, Vespermaw, healing pool and Aqua
lesson. Entry grants no quest progress and recruits no companions. Party
availability follows its actual owner; completing MQ02 leaves Mira working at
her workshop rather than automatically enlisting her for exploration.

The reserve is non-combat ground with ordinary caretakers and visitors. It has
no injured workers, missing-crew objective or keeper-rail emergency marker.
Its confluence does not identify an Ancient machine, selected cave bypass or
Veinhold connection. The larger regional checkpoints and broken bridge retain
their physical restrictions pending separate work.
