# Sanctuary crystal cave

The Sanctuary's first dungeon is a connected set of native pixel cave scenes.
The route moves from daylight at the entrance through crystal-bearing galleries
and reflecting pools to the broad Echo Chamber. Six persistent discoveries
reward exploration along the route and its optional branches.

The cave extends the Sanctuary's amethyst, cyan, opal and restrained amber
materials. Slow crystal pulses illuminate surrounding stone and characters.
The crystals remain scenery; collecting a cache never removes wall formations
or disturbs memorial offerings.

## Layout and travel

| Scene | Main route | Optional exploration |
| --- | --- | --- |
| Entrance | Cave Entrance → Vein Gallery → upper passage | Reflecting Grotto loop around the pool; three discoveries |
| Hollow | Splitstone Hollow → Deep Gallery | Keeper's Recess loop and a high shelf; two discoveries |
| Depths | Deep Gallery → Quiet Shelf → Echo Chamber | Quiet Shelf cache; final chamber and its inspection |

The lower grotto and keeper routes reconnect with the main passages. Broad
landmarks, wall contours and local lighting distinguish junctions. Walkable
shelves remain consistent with the full 24 × 12 pixel player footprint, and
scenery sorts against characters at its physical base.

Press **E** at the Sanctuary cave approach to lift the rail and enter. Inside,
press **E** at passage mouths to move between the three scrolling scenes, or
at containers to collect a discovery. These explicit passage interactions avoid
automatic transfers while inspecting a tunnel. The entrance passage returns to
the existing Sanctuary apron. **M** opens the current cave section's local map,
with room names, passage locations and the player's position.

Each discovery has an independent stable receipt. Opening it grants a modest
bundle of existing Aether materials through the inventory foundation and changes
its visible state. Reopening, revisiting or continuing a journey cannot grant
the bundle twice. Material uses and equipment customization remain separate
future systems.

## Assets and lighting

The reusable cave source recipe is in
`assets/source/terrain/sanctuary_cave/`. The builder exports the terrain kit,
assembled scenes, collision, overviews, asset board and placement metadata to
`assets/terrain/sanctuary_cave/` and `assets/maps/sanctuary_cave/`.

Floor and wall modules use the existing 24 pixel scale. Crystal formations
reuse the Sanctuary material language with independent light sources and fixed
physical silhouettes. Cave scenery remains modular rather than a painted
background. Source data records the intended paths, room landmarks, treasure
approaches, future encounter spaces and scene connections.

`SanctuaryCaveWorld` draws the ordinary ground, scenery, party and foreground
before applying a separate colored light field. Sources follow a six-second
breathing cycle; their visible crystal frames and local illumination share the
same pulse. The ambient level preserves readable floors at the trough. Light
falloff and visibility are cached, clipped at walls and culled to the viewport.
The HUD, dialogue and menus remain outside the lighting pass.

Reduced motion holds crystals and their illumination at a readable static
state. It does not remove light or make navigation depend on animation.

## Story boundary

The cave is explorable without resolving the pending MQ03 Sanctuary arrival.
The existing party ownership and Kindled Courage music continue while that
checkpoint remains active. Cave entry, treasure and the Echo Chamber inspection
do not complete a quest, recruit Lucan or trigger an invented encounter.

The arrival cutscene, enemy populations, miniboss identity, combat balance and
post-boss resolution remain later work. The Echo Chamber provides a clear staging
space for that encounter. The cave does not establish the confluence's detailed
workings, identify the original sacrificial temple or merge this location with
the historically sealed workers' passage.

## Reproduction and review

```sh
python tools/build_sanctuary_cave.py
python tools/build_sanctuary_cave.py --check
python tools/capture_sanctuary_cave.py
python tools/capture_sanctuary_cave.py --check
```

The [production review](reviews/sanctuary_cave/README.md) contains gameplay views,
light trough and crest captures, local maps, reduced motion and a walkthrough.
It uses disposable settings and saves, production movement and **E** input.
Its fixture initializes only completed earlier quests; the MQ03 emergency and
journey to the Sanctuary are played normally before entering the cave.
