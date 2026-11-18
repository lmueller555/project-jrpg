# Emerald grass terrain

The approved grass palette and variation ship in Eldenmere, the Elden Vale
Sanctuary's outdoor reserve and the upstream mill area. Maintained lawn stays
quiet near buildings, meadow patches add different growth and coverage, and
woodland ground introduces shade, moss and leaf litter. Irregular clumps grow
around selected margins while paths, entrances and quest approaches stay clear.

The base green is `#2c7c50`. Twelve native 24 × 24 ground materials share that
base at their borders. Four rooted grass silhouettes stand 16–17 opaque pixels
tall beside Caelan's 34-pixel visible sprite. Foreground tips cover his legs
while leaving his coat, torso and head visible. Dirt transitions and flower
stems use matching greens.

Walking parts the grass in the direction of movement. Running produces a
stronger bend; standing keeps occupied clumps parted, and they recover after
the last character leaves. Caelan, visible companions and local NPCs use the
same foot-contact logic. Grass is scenery and adds no movement penalty or
collision. Reduced motion keeps a static occupied pose without breeze.

Run the game normally with `python main.py`. No asset-building step is required.
The [production screenshots and walkthrough](reviews/grass_rollout/README.md)
show the rollout. The separate [material study](GRASS_DEMO.md) remains available
for comparing individual ground and grass variants.

## Authoring and reproduction

The shared source recipe lives in `assets/source/terrain/grass/`; its runtime
manifest is `assets/terrain/grass/assets.json`. It promotes the approved study
pixels into the production pack. Legacy grass assets remain as source references
and historical review material. Regional-scale overworld and battle art retain
their own terrain vocabulary.

Map compilers choose coherent groups of lawn, meadow and woodland tiles and
write a `grass` record containing the shared manifest path and authored clump
instances. Each instance has an ID, root position, variant and breeze phase.
`World` loads these optional layers, and the normal game update supplies the
visible actors after movement. Maps without grass use the existing renderer.
Contact and bending state are transient and require no save migration.

Eldenmere retains a native grass-coverage mask for each water-animation phase.
These masks preserve the assembled town's paths, banks and later buildings.
The terrain compiler checks their hashes and the collision fingerprint; review
the coverage sources again when changing the town layout.

Rebuild the shared pack before dependent maps:

```sh
python tools/build_grass_assets.py
python tools/build_playable_eldenmere.py --terrain-only
python tools/build_elden_vale_sanctuary.py
python tools/build_mill_quest.py
```

Use `python tools/build_grass_assets.py --check` to verify the shared pack
without writing files. Eldenmere's `--terrain-only --check` verifies the terrain
rollout while retaining later town additions; a full historical town rebuild
requires its separate follow-up builders. Sanctuary map checks use
`python tools/build_elden_vale_sanctuary.py --check`. The capture tools retain
source and artifact hashes; their `--check` options reject stale reviews.
