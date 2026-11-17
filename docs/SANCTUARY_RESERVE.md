# Elden Vale Sanctuary reserve — Gameplay and Runtime Reference

**Scope:** Current exploration, interactions, scene ownership and reproduction.
The single creative design authority is
[Elden Vale — Regional Design Guidance](world/regions/ELDEN_VALE.md).
The approved Pale Antlers/Rising Rain redesign is awaiting implementation;
this guide describes the playable scenes, not a separate future layout proposal.

The reserve exterior/cave approach, public hall and relief room use native 2×
environment artwork with their established logical footprints. Construction and
rendering follow the [visual standard](VISUAL_ART_STANDARD.md) and
[maintained reserve integration reference](TERRAIN_ART_STANDARD.md#integrated-elden-vale-sanctuary-reserve).
The Sanctuary remains separate from Serene's home in Eldenmere. Its societal
purpose and custodial responsibilities are defined in the
[faith guide](world/ELDEN_VALE_FAITH.md) and
[covenant](world/SANCTUARY_COVENANT.md).

## Exploration

Walk onto the regional Sanctuary miniature to enter at the southern woodland
approach. The current paths form a circuit around the court, grove, hillside and
cave approach. Visible open ground accepts the complete player probe; physical
building bases, roots, walls, benches and rock faces remain solid. Three open
cloister bays can be entered from the court. Their columns, rear wall and garden
workstation retain their physical footprints and separately sorted scenery.

The hall is an enterable scene. Its main exit returns to the court, and an
animated north-wall door beside the bed plaque leads to the visitor relief room.
The southern reserve exit returns to the overworld outside the miniature's
contact area. Eldenmere's entry/return remains independent.

Press **M** for the local reserve map, with current position, named places and
landmark descriptions. The hall and relief room use that same regional context.

Caretakers and visitors are live actors. Optional conversations and inspections
introduce care, remembrance, the confluence and the survey. They do not award
items, attributes or quest completion. Repeatable eligible small inspections and
the visitor bed use the shared discovery cues. Ordinary buildings, characters
and decorative crystals are not blanket highlighted.

## Visitor relief room

Enter the hall, then use its north-wing doorway. Attendant Nessa and the bedside
**E: rest** prompt offer an explicit **Rest / Not now** choice without a fee or
quest prerequisite, subject to ordinary scene/control availability.

Rest restores current HP and MP to effective maxima for every available
travelling member, including reserves and KO companions. Characters unavailable
elsewhere retain their resources. Levels, EXP, stats, modifiers, inventory,
equipment, formation, story progress and the cave encounter counter remain
intact. There is no overnight time skip or quest completion.

Recovery is saved before the completion message. Failed saving restores prior
resources and offers **Retry / Not now**. Moving away or changing scenes before
confirmation cannot heal the party remotely. Continue preserves a save made in
this room. The active story/music owners retain their normal behavior.

The room is available during the MQ03 outing after any mandatory staging releases
control; entering it does not acknowledge or bypass an unfinished arrival scene.
The first post-arrival cave visit also has its existing introductory exchange.
These control owners must finish normally before free travel resumes.

## Story boundaries and cave access

The Sanctuary reserve is non-combat ground. During MQ03, the
[arrival director](SANCTUARY_ARRIVAL.md) stages the wounded Crown crew, caretaker
aid and the rescue decision before returning control at the cave apron. Its
keeper-rail operation remains story-owned; free exploration uses the existing
explicit **E** interaction into the [continuous cave](SANCTUARY_CAVE.md).

The cave, encounters, Vespermaw fight, rescue and healing-pool evacuation are
implemented. The return resolution finishes MQ03 only through its final
acknowledged family exchange. See the
[quest narrative](narrative/game_01/CH01_MQ03.md),
[arrival guide](SANCTUARY_ARRIVAL.md) and
[cave reference](SANCTUARY_CAVE.md) for their respective owners; none grants
excavation permission or changes regional gate/bridge restrictions.

The historical sealed workers' passage is distinct from the playable ridge cave.
The later-game descent below the [Echo Chamber rupture](SANCTUARY_CAVE.md#echo-chamber-rupture)
has no current ladder, transfer or descent action. The established surge/rupture
link does not define the new regional phenomenon's mechanism or the creature's
origin. Follow the regional design and canonical story references for these
boundaries.

## Scene ownership and saved journeys

`elden_vale_sanctuary`, `elden_vale_sanctuary_hall` and
`elden_vale_sanctuary_relief` retain their scene identities. Town quest actors
keep their owners; continuing a save resumes its corresponding scene. Ordinary
regional contact rearming and transfer cooldowns prevent entry/return loops.

The current exterior is 1152×768 logical units (48×32 tiles); the hall is 576×384
and the relief room 336×288. The exterior's current full player probe remains
24×12 logical units. These are live implementation facts, not new pixel-to-world
distance conversions. Revision work must explicitly handle established routes,
scene contracts, saved positions and the design's protected circulation.

Ground uses visible native chunks and bounded scene caches. Scenery and furniture
remain separately placed and depth sorted; their visible silhouette does not
define collision. Pause/focus freezes exploration clocks; reduced motion holds
ambient effects and the caretaker at rest. The local map overview is derived
from the assembled assets.

## Pale Antlers integration

The reserve builder's `pale_antlers` source-recipe record owns the detailed
landmark, independently of ordinary baseline-validated entity IDs. It projects
the coherent 1568×1056 master once at build time to 980×660 artwork pixels, with
logical origin `[726,-41]`. Even native splits at x=0/330/650/980 and y=474
preserve the exact shared arrangement. Runtime consumes native 2× drawings;
there is no frame-by-frame scaling or new save state.

The declared `[948.5,274,45,12.5]` logical contact lies in retained ridge band 4.
Lower earth/root fringe uses an authored uneven embedding contour against
existing solid ridge bands 3–5. Vertical ridge faces stay continuous above their
support rather than being cut at a horizontal row; a conservative authored
polygon preserves jaw/teeth anatomy. Only clipped
contact pixels enter the ground pass. Elevated skull and all beams use authored
coverage masks and immediate local cutaways for players, companions,
story-positioned actors and public approaches. They never contribute collision.
Native limestone ends, exposed strata, earth, roots, ivy and moss provide the
contact dressing; their lower edges remain on existing ridge supports.

Ordinary exploration reveals the skull from the eastern/northern courtyard
circuit, with branches above that route. The central hall forecourt and southern
arrival camera do not show the landmark at this anchored scale; regional views
supply the wider approach silhouette. Some tips extend above/right of the
reserve camera range, intentionally retaining the impression of a larger
landscape. The cave apron shows the embedded jaw, not the whole assembly.
The hall, cave rail, memorial grove, station locations, doors, collision,
public approaches and complete courtyard loop are unchanged. The local overview
includes these layers; this is not the later world-atlas/minimap artwork phase.

Focused contracts in `tests/test_elden_vale_antlers_reserve.py` check exact
protected-anatomy reconstruction, density/masks, ridge-only ground contact,
unchanged gameplay metadata, actual initialized-Game eastern-loop walk/run and
normal/reduced-motion actor cutaways. Those fixtures are not an uninterrupted
story playthrough or user visual approval.

## Review and reproduction

The maintained owner is `tools/build_sanctuary_reserve_hd.py` for all three scenes.
Older exterior/art, hall and relief CLI commands forward to it. Runtime uses
checked-in products and needs no asset-building step.

```sh
python tools/build_sanctuary_reserve_hd.py
python tools/build_sanctuary_reserve_hd.py --check
python tools/capture_sanctuary_reserve_hd.py /tmp/reserve-review
```

Source drawings, registration and geometry controls are under
[`assets/source/maps/sanctuary_reserve_hd/`](../assets/source/maps/sanctuary_reserve_hd/).
The [current native review](reviews/sanctuary_reserve_hd/README.md) records
initialized gameplay fixtures, actual movement/door transfers, caretaker work,
rest offers and the complete arrival preview. The
[terrain integration reference](TERRAIN_ART_STANDARD.md#integrated-elden-vale-sanctuary-reserve)
owns the maintained build workflow.

Earlier [fantasy](reviews/sanctuary_fantasy/README.md),
[pixel-asset](reviews/sanctuary_pixel_assets/README.md) and
[relief-room](reviews/sanctuary_relief/README.md) captures remain historical
implementation evidence. Their source recipes, snapshots and old dimensions do
not supersede the current registry or the regional creative design.
