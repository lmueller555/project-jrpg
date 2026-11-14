# Iselin — registered overworld actor

The portrait, four directional idles and four 16-frame walks are approved and
merged. `actor.json` is the reusable runtime actor definition;
`animation.json` registers its idles and approved walk manifests.

Authoring follows the
[global sprite and animation standard](../../../docs/SPRITE_ANIMATION_STANDARD.md).
These integration details describe the current exports and renderer.

## Runtime size and playback

- Artwork is 42×72 at two artwork pixels per world pixel, representing a
  21×36 logical frame. Draw anchor is [21,60] in artwork / [10.5,30] in world
  coordinates; the collision probe remains 8×4 world pixels.
- Each direction uses its existing `walk_DIRECTION/animation.json`: sixteen
  complete frames at 35 ms each, for a 560 ms two-step loop.
- `StoryActor` loads those unchanged images and creates 21×36 fallbacks in
  memory. Logical and detailed frames select from the same authored durations
  and movement clock. Navigation owns movement speed and advances that clock.
- `WorldCanvas` preserves the 42×72 detail at normal party scale, including
  foreground foliage and later depth-ordered blits. Ordinary surfaces use the
  logical fallback. No additional bob or frame interpolation is applied.
- Stopping selects the facing idle. Conversation uses the conversation-facing
  idle; authored scene poses and external sprite overrides retain ownership.

The actor is ready for scene use. Replacing Aldric's existing quest actors,
cinematic/meal poses, dialogue and story identifiers remains a separate task.
The review capture stages Iselin transiently; it does not replace the regent or
change quest progress.

## Reproduction and review

```sh
python tools/register_iselin_walks.py --check
python tools/export_iselin_first_assets.py --check
python tools/capture_iselin_walks.py
PYTHONPATH=.:tests python -m unittest test_iselin_walk_integration test_iselin_idles test_dense_art
```

Run `python tools/register_iselin_walks.py` to re-register the four manifests
without changing artwork. The idle/first-assets exporters also retain this
registration when rebuilt.

[Production travel and occlusion review](../../../docs/reviews/iselin_walk_integration/README.md)
shows four directions, stopping, turns and tree occlusion. Native PNG captures
are the color/detail references; GIFs are motion previews.

The initial 24×36 idle and resolution study are retained as historical evidence.
They are superseded by the approved detailed sprite. Sources and provenance live
under `assets/source/characters/iselin/` and
`assets/source/portraits/eldenmere/`. See the
[first detailed-idle implementation](../../../docs/reviews/iselin_first_assets/IMPLEMENTED.md)
and [directional-idle review](../../../docs/reviews/iselin_first_assets/DIRECTIONAL_IDLES.md)
for that milestone's original rendering evidence.
