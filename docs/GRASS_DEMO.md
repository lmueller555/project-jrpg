# Playable grass demonstration

Run the isolated art study from the repository root:

```sh
python tools/preview_grass.py
```

This preview uses Caelan's existing 24 × 36 sprites, walking and running rules,
the normal 24 × 12 foot probe, and the shared world renderer. Its own small map
contains maintained lawn, meadow and woodland patches, irregular tall-grass
edges and adjacent current/proposed grass samples. It opens no journey or
settings file. The town and Sanctuary retain their existing terrain.

| Control | Action |
| --- | --- |
| WASD / arrow keys | Walk |
| Shift while moving | Run |
| Release movement keys | Stand among the grass |
| R | Reset the demonstration |
| M | Switch normal/reduced motion |
| H | Show/hide the guide |
| Escape | Close |

The deeper emerald palette and different blade arrangements are a prototype for
visual review. Ground materials stay quiet enough for Caelan to remain clear.
Grass reaches about half Caelan's visible height. Its foreground blades cover
his legs while leaving his coat, torso and head visible. The clumps have several
distinct shapes, independent breeze phases and directional parting poses.
Feet trigger the reaction; running displaces it more
strongly. Occupied grass stays parted, then recovers after the last actor leaves.
Its roots remain fixed, and separate rear/front blades overlap the lower body.
Grass does not block movement or change travel speed. Reduced motion retains a
static occupied pose with no continuous breeze animation.

The [screenshots and movement review](reviews/grass_demo/README.md) show the
actual playable preview, including walking, running, standing and recovery.
The native world image is enlarged at integer scale; guide text is drawn at
display resolution with the game's shared font and panels.

## Source and reproduction

The prototype pack and map are separate from the currently approved terrain:

- `assets/source/terrain/grass_demo/`: palette and source recipe.
- `assets/terrain/grass_demo/`: new ground and rooted vegetation frames.
- `assets/source/maps/grass_demo/`: authored demonstration layout.
- `assets/maps/grass_demo/`: compiled terrain, collision, placements and overview.
- [`interactive_grass.py`](../interactive_grass.py): foot occupancy and reaction state.
- [`grass_demo.py`](../grass_demo.py): the preview world using the shared renderer.

The checked-in preview needs only the game's existing Pygame dependency.
Rebuilding assets requires the Pillow asset environment:

```sh
python tools/build_grass_demo_assets.py
python tools/build_grass_demo_scene.py
python tools/build_grass_demo_assets.py --check
python tools/build_grass_demo_scene.py --check
```

For a disposable headless still:

```sh
python tools/preview_grass.py --headless --frames 120 --screenshot /tmp/grass-demo.png
```

Source and artifact fingerprint checks accompany the review capture. This
milestone supplies a playable comparison before wider terrain changes.
