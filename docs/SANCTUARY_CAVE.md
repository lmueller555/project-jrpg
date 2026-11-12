# Sanctuary crystal cave

For nearby recovery, return to the Sanctuary hall and take the bed-marked
north-wing door to the visitor relief room. Attendant Nessa and the bed both
offer a free, confirmed short rest that restores travelling party HP/MP and
revives KO companions. There is no need to return to Eldenmere. See
[visitor care](SANCTUARY_RESERVE.md#visitor-relief-room).

The Sanctuary's first dungeon is one continuous scrolling cave, assembled from
the approved limestone dungeon asset pack. The player walks from the rooted,
daylit entrance through crystal-bearing galleries and reflecting water to the
broad Echo Chamber. Rooms, branches and return paths share the same world;
there are no internal scene transfers or passage interactions.

## Layout and travel

The direct route is **Cave Entrance → Vein Gallery → Splitstone Hollow →
Deep Gallery → Quiet Shelf → Echo Chamber**.

| Branch | Connection | Exploration reward |
| --- | --- | --- |
| Reflecting Grotto | Leaves Vein Gallery and rejoins the Upper Passage before Splitstone Hollow | A dropped pack and a chest across the reflecting pool |
| Keeper's Recess | Takes the lower damp route from Splitstone Hollow and rejoins Deep Passage | A keeper's chest and traces of maintained stonework |
| High shelf | A ramp-accessed spur overlooking Splitstone Hollow | A cache and a view over the junction |
| Quiet Shelf alcove | A short spur before the final chamber | The last cache and room to prepare |
| Embervein Chamber | Optional continuous branch from the lower Vein Gallery route | Level-four Embravyr, Red focus and Flame Edge |
| Stillfrost Chamber | Optional continuous branch from the upper/deeper junction | Level-four Nivareth, White focus and Ice Edge |

The first Vein Gallery cache introduces the containers on the direct route.
Both longer detours reconnect, so exploration does not require retracing a
long dead end. A split pillar, natural arch, contrasting dry and wet routes,
wall contours and local lighting distinguish the junctions. The Echo Chamber
has a clear foreground framed by stone and embedded microcrystals, with a
fresh rupture in its rear floor.

Main passages allow at least three 24-pixel tiles of clearance. Shelves, ramps
and optional routes are authored for the full 24 × 12 pixel player footprint
and the following story party. Physical scenery sorts at its base.

Press **E** at the Sanctuary cave approach to lift the rail and enter. Inside,
walking crosses every room boundary. **E** opens containers, reads inspections
or returns through the entrance to the Sanctuary apron. **M** shows the whole
cave, its room landmarks, the exterior exit and the player's actual position.
Selection and mouse hover label rooms; select a room with the keyboard or mouse
to read its description.
Treasure and encounter staging data are not map markers.

## Persistent discoveries and journeys

The six existing discovery IDs and their inventory rewards are retained:

| Receipt | Placement |
| --- | --- |
| `cave_vein_cache` | Vein Gallery, on the direct route |
| `cave_grotto_pack` | Reflecting Grotto loop |
| `cave_grotto_chest` | Across the grotto pool, reached around its shore |
| `cave_keeper_chest` | Keeper's Recess |
| `cave_overlook_cache` | High shelf above Splitstone Hollow |
| `cave_quiet_cache` | Quiet Shelf alcove |

Opening a discovery grants its existing Aether material bundle through the
inventory foundation and changes the visible container state. Its independent
receipt prevents duplicate rewards after reopening, revisiting or continuing
a journey. Material uses and equipment customization remain future systems.

Journeys saved inside the continuous cave restore the same location and opened
containers. Older journeys from the three-section cave migrate to safe
landings in the corresponding part of the new map, preserving receipts,
inventory, party and quest progress.

## Assets and lighting

The live map is `assets/maps/sanctuary_cave/map.json`, authored by
`assets/source/maps/sanctuary_cave/recipe.json`. The builder composes the reusable
modules documented in [the dungeon asset pack](DUNGEON_ASSET_PACK.md): dry and
damp limestone, gravel, silt, rooted earth transitions, walls and overhangs,
ledges and ramps, fixed water banks, animated water, seepage, debris and
restrained keeper paving. Containers reuse the original cave's open and closed
sprites. Authored room polygons and navigation routes describe the full level.

Red, blue, green, white, orange and purple microcrystals follow the cave walls
in varied seams, corners and narrow fissures. Individual facets are mostly
2 × 3 native pixels and never exceed 4 × 5. They remain embedded scenery when
the player collects a container.

`SanctuaryCaveWorld` draws ordinary ground, scenery, party and foreground before
applying the colored light field. Sources follow a six-second breathing cycle;
the crystal frames and local illumination share that pulse. Ambient light
keeps the paths readable at the trough. Cached falloff is clipped at walls and
culled to the viewport. The HUD, dialogue and menus remain outside the lighting
pass. Reduced motion holds crystals and illumination at a readable static
state while preserving the same terrain and collision.

The optional elemental rooms add sparse floor-clipped embers or frost motes
and an Effects-volume crystal hum through `elemental_room_fx.py`. Their original
wall microcrystal light roots remain shared with the cave lighting pass.
Reduced Motion holds the motes, and menus, dialogue, focus loss and combat
release the ambience audio without changing story music ownership.

## Story and encounters

The [MQ03 arrival scene](SANCTUARY_ARRIVAL.md) returns control at the cave
apron with Caelan, Mira and temporary companion Lucan ready for the rescue.
Lucan joins as a level-five guest, receives no combat EXP, and has Inspire,
Bolster and Provoke alongside the ordinary Attack, Items, Guard and permitted
Flee commands. He has no interactable minigame in this appearance; see
[guest combat rules](COMBAT.md#lucans-cave-guest-combat). He remains for early
rest trips, and leaves only after Vespermaw's defeat and the subsequent actual
cave exit. Save/Continue and later cave re-entry retain that departure.
MQ03 remains active; cave exploration does not complete its remaining story. **Elden Vale
Sanctuary Cave** replaces the emergency score during non-battle cave exploration,
including the optional elemental chambers, dialogue and menus. The cue repeats
without restarting as the player walks between rooms. Battles retain
**Kindled Courage**, then resume the cave track at its interrupted position
through results and rewards. Continue selects the cave cue even when restoring
pending rewards. First entry permanently releases MQ03's emergency override;
exiting returns to normal area music, including after Continue and later visits.
Cave entry, treasure and the Echo Chamber inspection preserve the pending story
state. See [music exports and playback](../assets/music/README.md).

The first entrance with Mira’s Blade presents a short Blue-gem resonance
scene. Caelan notices concentrated ambient aether and wonders whether he can
focus Aqua Edge here. His first distance-triggered encounter is fixed to two
level-two Cave Bats. A player-selected Aqua Edge succeeds, teaches the ability
and releases ordinary ATB combat. Aqua Edge costs 0 MP throughout this battle
and its retries. Afterward it costs 4 MP and remains usable outside the cave. The Blue gem is the only installed
gem at this point. Optional [elemental chambers](ELEMENTAL_CAVE_ENCOUNTERS.md)
then add the Red/Fire and White/Ice focuses in either order. See
[Caelan’s progression](CAELAN_AQUA_PROGRESSION.md).

The cave now uses [distance-based random encounters](CAVE_RANDOM_ENCOUNTERS.md)
with Cave Bats, Lithrusks and Veylumes. A hidden 16–36-tile countdown, weighted
toward 26, selects one of 14 authored formations from the outer, middle or deep
pool after the introductory bat pair clears. Battles contain at most four
enemies; groups of three or four are rarer.
The six original encounter spaces remain layout references. Random selection
uses the player's actual location throughout the continuous cave.

The entrance apron, High Overlook, Quiet Shelf, Echo Chamber and the new
guardian chambers and their final approaches are protected from random battles.
Earlier stretches of the optional branches keep their existing area pools.
Embravyr and Nivareth are pure elemental Aether formations, each fixed at level four. Their
independent Approach / Party / Leave choices and animated battlefields lead
to guaranteed Red/Flame Edge and White/Ice Edge rewards respectively. Either
order works; neither is required for Vespermaw. Elemental Edges cost 0 MP
throughout these two teaching encounters, then 4 MP in normal combat.

The Echo Chamber contains the level-seven miniboss,
[Vespermaw](BESTIARY.md#vespermaw), as a one-time solo story encounter. The
approach offers **Enter / Party / Step back**, with a short crystal-and-growl
introduction before the dedicated animated Echo Chamber battlefield. Its
[combat art](VESPERMAW_COMBAT_ART.md), party-wide Roar, marked Pounce response
and +50% exhaustion vulnerability are active. It starts in Fire and channels
Ice, then Water, changing freely before every third, fifth, seventh and later
alternate boss turn. Three large embedded red, white and blue crystals line the
rear wall in the exploration chamber and matching battlefield. The active
crystal brightens and pulses with the boss's fur and elemental effects; no
counter-element hints are displayed. Physical and non-elemental damage remain
viable, so neither optional gem is required. It remains excluded from random pools.
The Quiet Shelf provides a preparation pause without restoring HP or MP.

Boss entry checkpoints the formation, current party resources, safe approach
and opening combat seed. Continue restarts an unfinished fight from that entry
checkpoint. Flee is disabled during the boss battle; defeat offers **Retry /
Return to the Quiet Shelf** with pre-fight HP/MP restored and no rewards.
Victory awards 520 EXP to each living active member plus one Aether Amethyst
and one Aether Sapphire through the standard spoils transaction. The saved
defeated flag prevents the encounter and rewards from repeating after Continue
or revisiting. Boss completion leaves MQ03's remaining rescue and resolution open;
the previous music resumes through the existing battle music owner.

Random battle entry focuses the party, presents a loading screen and reveals
one of four regional animated cave battlefields. Victory/flee return to the
same cave position and reset the random distance budget. The introductory
bat pair instead retains its exact ticket after defeat or withdrawal until
victory; a deferred retry permits preparation without starting another battle. Each authored boss owns its own
entry and completion records instead of consuming a random-encounter ticket.
The two elemental encounters permit Flee; Vespermaw retains its no-Flee rule.
Focus rewards, learned skills and EXP share an atomic victory transaction,
while KO Caelan defers only the post-Spoils installation dialogue. See the
[elemental encounter guide](ELEMENTAL_CAVE_ENCOUNTERS.md).
See the [live encounter review](reviews/mira_rig_continuity/README.md).

The [arrival cutscene](SANCTUARY_ARRIVAL.md) is implemented. Further combat
tuning, the missing worker's rescue payoff and post-boss resolution remain
later work. The cave does not establish the
confluence's detailed workings, identify the original sacrificial temple or
merge this location with the historically sealed workers' passage.

## Reproduction and retained reviews

```sh
python tools/build_continuous_sanctuary_cave.py
python tools/build_continuous_sanctuary_cave.py --check
```

The retained [original cave review](reviews/sanctuary_cave/README.md) documents
the earlier three-section implementation. Its images and walkthrough are
historical evidence, not a preview of the current layout. The
[limestone chamber](LIMESTONE_CAVE_REVIEW.md) and
[expanded pack review](reviews/dungeon_pack/README.md) show the approved reusable
materials. No new walkthrough was generated for the continuous level; review
the merged dungeon in-game.

## Echo Chamber rupture

A large fresh chasm occupies the rear-central Echo Chamber. The foreground and
both side routes remain walkable. Broken rim slabs, exposed older strata and
climbing scratches show a route by which subterranean monsters emerged.
The footprint and its unstable lip are solid; there is no ladder, transfer,
descent option or lower-level encounter. The rupture remains after Vespermaw.
When Mira is travelling with the party, a safe inspection has her recognize
climbing marks and the equipment needed for descent; Caelan feels rising aether
without claiming the full explanation. Otherwise Caelan inspects it alone.

**Established cause:** the aether surge that caused the lightning storm and
bridge destruction also disturbed this natural confluence. The floor ruptured,
opening onto the deeper subterranean region before the Crown crew was attacked.
That region is later-game content. This does not add a new explanation for the
planet's aether cycle or resolve the Sanctuary's other story scenes.

Eleven restrained aether threads rise, bend outward and dissolve over a
12-second cycle, with blue-white dominant and faint other mineral colors.
A soft below-rim glow preserves a dark centre. The ordinary crystal cycle
remains six seconds. The Effects-volume regional audio owner adds quiet air
and low resonance near the opening; it releases the bed for menus, dialogue,
focus loss, combat and leaving the cave. Cave music remains unchanged.
World VFX freeze with pause/focus conditions; Reduced Motion holds them steady.
The boss introduction pans to the rupture and the dedicated Echo battlefield
shows matching scenery and a cached 48-frame cycle behind its clear actor stage.

Old cave saves covered by the new collision relocate to an intact foreground
landing. Matching pending boss and spoils coordinates move together before
normal save validation. Seeds, receipts, resources, rewards and story flags
are preserved; loading alone does not write the migration to disk.
