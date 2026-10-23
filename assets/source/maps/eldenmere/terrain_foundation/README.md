# Eldenmere terrain foundation — retained composition recipe

This pass assembles the user-approved 64×56 overhead design from existing approved native assets. It creates a scene for layout review. It introduces no new painted environment art, game engine, doors, quests or character animations. The sanctuary and Mira's workshop remain measured design placeholders.

The approved design is retained at `docs/world/eldenmere/blockout/recipe.json`. Its exported status predates the user's subsequent approval in chat; the terrain recipe records that approval and reads the blockout without modifying it.

## Native assets and registration

- Grass and path tiles use the approved 24px grass/dirt pack and all 47 normalized blob masks. Grass variants use a fixed random seed. Plot and garden reserves are bare earth at this stage.
- Brook cells use the approved stationary bank/water-mask atlas, two surface variants and six synchronized phases.
- Directed eight-pixel channels reuse the irrigation pack. The existing west-return compatibility module reconnects each branch at the brook's first receiving bank cell. The brook keeps its own water; a restricted field drain does not dry a stripe through the river.
- Terrace masonry repeats approved modules. Two stacked rows show the larger northern drop. All four staircases reuse the complete unrotated 48×48 south-facing prefab, with a 34px central tread.
- Two-tier headwater weirs repeat existing 24×48 spillways at x=34,35,36 and x=43. The upper field supply and southern field drop also use existing spillways. These are assemblies, not newly painted waterfalls or stretched sprites.
- Bridge spans assemble west + repeated middle sections + east, retaining the two-tile walking deck and separate foreground rail. Wakes are clipped to actual water colors.
- Cottage origins derive from each pack's `ground_rect`. Approved door leaves stay closed; original lantern and chimney-smoke layers play with retained 200ms timing. The wide Venn cottage's doorway is aligned to its exported centre.
- Mill origin derives from `building_ground_rect`; its native landing lies at [936,336,48,24]. The race's eight-pixel water band at row 14 reaches the approved wheel's lowest paddles and splash layer. The clockwise wheel therefore retains westward underside flow.
- Caelan remains an unmodified 24×36 sprite. The main scene has one Caelan at the commons; the eight detail panels are separate scale snapshots of the same character.

## Changes needed to fit the native art

1. The eastern steps move from the conceptual east/west opening [45,33,2,2] to [48,35,2,2] on the terrace's southern edge. The lower lane approaches at row 38, then climbs north. Existing south-facing stair artwork is used directly.
2. The mill race returns at row 14 rather than row 15, and its landing rectangle becomes [39,14,2,1]. The upper race bend follows the headwater cascade and runs behind the roof before reaching the exposed eastern channel. Building footprints remain fixed.
3. The headwater brook stays at x=35 through row 10, giving the repeated spillways straight inputs and outputs before its first bend.
4. Cottage door approaches follow the native centres. Venn's front path uses x=52, and all six actual threshold approaches are checked with the actor probe.

All changes are recorded in `recipe.json` and in the exported scene metadata for this review. The original approved blockout is preserved as the design reference.

## Animation and checks

The loop is 18 × 200ms = 3.6 seconds. Water, wheel, gate, splash, spillway and bridge phases repeat every six ticks; cottage smoke/lantern layers repeat every eighteen. Smoke drifts east as in the approved art. No foliage has been added in this terrain pass.

The mill is running, matching the beginning of MQ01. The Venn gate holds its approved jammed pose. The controlled downstream channel and field spillway carry a restricted trickle; the brook, mill supply and upstream irrigation remain independently full. At each return, the river's receiving water stays wet.

The 24×12 foot probe uses anchor [12,30]. A two-pixel lattice flood starts in the sanctuary courtyard, respects walls, water, building ground footprints, bridge decks and 34px stair treads, and reaches every door, quest approach, exit and scale-snapshot placement. These are composition checks, not installed game collision or finalized traversal rules. Roof overhangs are visual occlusion, not enlarged building ground blockers.

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/build_eldenmere_town.py
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/project-jrpg/bin/python tools/test_eldenmere_town.py
```

Only the source/map composition directories are written. Previous environment art, character art, narrative and blockout exports are read-only. GIFs use an explicit exact RGB palette lookup, retaining close source shades that Pillow's approximate palette lookup can merge. Text labels and measured placeholder graphics are review aids.
