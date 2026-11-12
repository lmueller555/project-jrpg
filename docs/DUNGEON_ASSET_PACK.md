# Sanctuary dungeon asset pack

The expanded pack continues the Sanctuary's warm limestone, pale calcite,
damp teal and tiny red, blue, green, white, orange and purple microcrystals.
The approved additions are merged and used by the
[continuous Sanctuary cave](SANCTUARY_CAVE.md). The full catalogue also retains
the base limestone and microcrystal modules.

## Review the complete library

The [full catalogue](../assets/terrain/limestone_cave/catalog/README.md) shows
every floor variant and module at a consistent pixel scale. Its labelled pages
cover the existing base pack together with all four new families. Animated
pages show the water and crystal cycles; the catalogue manifest links every
frame, placement anchor and physical footprint.

- [Complete PDF](../assets/terrain/limestone_cave/catalog/full_catalog.pdf)
- [Native asset archive](../assets/terrain/limestone_cave/catalog/native_assets.zip)
- [Catalogue overview](../assets/terrain/limestone_cave/catalog/overview.png)
- [Playable scene and animation review](reviews/dungeon_pack/README.md)

| Family | Contents |
| --- | --- |
| Base limestone | Dry and damp floors, gravel, silt, transitions, original walls and formations |
| Structure and passages | Directional walls and caps, low and tall faces, shelves, ledges, ramps, worn steps, narrow/wide tunnel mouths and alcoves |
| Water and seepage | Shallow/deep water, fixed pool banks and corners, stream connections, trickles, wall seepage, drips and ripples |
| Loose geology and entrance | Pebbles, rubble, talus fans, fallen slabs, fractures, erosion, roots, moss, leaves and earth-to-stone transitions |
| Microcrystals | Existing branching seams plus vertical, diagonal, inside/outside corner, sparse and dense adapters in all six colors |

The microcrystals retain their tiny native scale: individual facets are mostly
2 × 3 pixels and never exceed 4 × 5. Their surroundings are transparent so the
mineral follows existing geology rather than replacing the wall with a panel.
Water banks and collision remain fixed while water and droplets animate.

## Play the assembled review scene

```sh
python tools/preview_dungeon_pack.py
```

WASD or arrows move Caelan, Shift runs, Space holds low/high light reference
frames, L shows underlying material colors, R toggles reduced motion, H hides
the guide, Home resets the viewer and Escape closes it.

The route moves from a rooted earth threshold through dry limestone galleries,
an alcove and raised shelf to a wet grotto. It uses the production Player,
World, depth sorting and crystal lighting, without constructing the normal
Game, loading a journey or writing saves/settings. The viewer is an isolated
asset study; the live continuous dungeon, quests, party and music are handled
by the normal game.

## Rebuild and verify

The existing base builders remain unchanged. Additional authoritative recipes
live in `assets/source/terrain/limestone_cave/` and the scene recipe is in
`assets/source/maps/dungeon_pack_review/`.

```sh
python tools/build_dungeon_structure.py
python tools/build_dungeon_water.py
python tools/build_dungeon_geology.py
python tools/build_microcrystal_adapters.py
python tools/build_dungeon_review_scene.py
python tools/build_dungeon_pack_catalog.py
python tools/capture_dungeon_pack.py
```

Each builder supports `--check` without writing. The retained gameplay review
records the source and artifact fingerprints from asset approval. Its original
capture guards compare against that baseline; subsequent live-level changes
are intentionally outside the archived review. Current live-layout generation
is documented in [Sanctuary cave](SANCTUARY_CAVE.md).

Pygame and NumPy are runtime dependencies. Building and capturing require Pillow;
the walkthrough recording additionally requires ffmpeg.

## Rupture and subterranean depth

The [chasm module pack](../assets/terrain/limestone_cave/chasm/assets.json)
adds separately authored north/south rims, side rims, deep stratified rock,
fresh rubble, fissures and climbing scratches. The retained
[source atlas](../assets/source/terrain/limestone_cave/chasm/README.md) and
`tools/build_cave_chasm_assets.py` reproduce its registered exports. The Echo
Chamber composes these into a blocked opening; there is no descent transition.
