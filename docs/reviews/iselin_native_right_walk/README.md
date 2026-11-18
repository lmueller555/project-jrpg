# Iselin native right-walk review

**Status: approved and integrated.** The images below retain the original
native-art approval snapshot, captured before campaign activation. Its
`capture.json` preserves the reviewed commit and original input hashes; current
manifest metadata and helper code may differ after integration. Do not repin
those historical hashes to imply the original fixture was captured again.
Current production verification is in the
[native integration review](../iselin_native_integration/README.md).

The [sprite and animation standard](../../SPRITE_ANIMATION_STANDARD.md) remains
the authoring reference. The right-facing appearance keeps the anatomical-right
mantle on the near side and anatomical-left braid on the far side. Motion review
tracks the anatomical limbs through their sleeve/leg depth, rather than assuming
a hand that occupies a similar screen position is always the same hand.

The retained source is a single 1086×1448 sheet containing 16 complete
right-specific drawings. Cells are padded to the same 272×362 source grid,
sampled to 27×36 with nearest-neighbor pixels and registered at `[-2,-1]`
on each 24×36 export. The density and origin are shared across the cycle;
individual boot positions and silhouette heights do not change registration.

After whole-drawing export, the approved right idle's stationary head/face
region (source rows 0–11) is preserved at destination row 1. This one-pixel
walking settle stays constant throughout the cycle. The mantle, torso, near/far
arms, coat and legs from row 13 downward remain authored pose pixels. Native
sampling, the protected head/neck boundary and the loop joins were inspected
in the exported frames and renderer captures.

## Animated in-game evidence

![Actual rightward travel and start/stop transitions](in_game_travel.gif)

This is **production movement and world rendering**: `RegentQuest._move` moves
a review `StoryActor` rightward on a clear Eldenmere road at 74 world pixels per
second. `World.draw` and `WorldCanvas.present_detail` render the actual town at
the game's 960×640 presentation scale and normal depth order. The fixed-camera
GIF includes an idle hold, four walking cycles and a stopped hold. It crops
rendered world frames and adds inspection captions. Scenery time is held at
zero to isolate the gait; HUD, input and story updates do not run in this
world-render fixture. Caelan and Mira retain their current artwork.

Separate inspection loops use the same actor and renderer with an explicitly
pinned position:

- [Normal in-place loop](in_game_loop.gif): 16×35 ms, 560 ms total.
- [Slow in-place loop](in_game_loop_slow.gif): 3× slower, 1680 ms total.
- [Full rendered world viewport](in_game_right_walk.png): lossless 960×640 PNG.
- [Enlarged rendered closeup](in_game_closeup.png).

The inspection loops enlarge real game-frame crops 3× with nearest-neighbor
sampling. GIF timings alternate 30/40 ms normally and 100/110 ms when slowed,
preserving complete-cycle durations despite GIF's 10 ms timing units. A common
palette keeps static scenery from changing color between exposures. The PNGs
retain lossless rendered pixels. The pinned loops supply phase inspection;
the separate travel GIF supplies actual movement and stopping evidence.

## Scope, reproduction and checks

The review manifest is `assets/characters/iselin/native_walk_right/review_actor.json`.
It uses the ordinary sheet-based loader, approved native idles and explicit
right-walk timings. The actor has no HD idle or walk overrides, uses draw anchor
`[12,30]` and keeps the existing 8×4 collision probe.

After exporting the staged artwork, run from the repository root:

```sh
python tools/export_iselin_native_right_walk.py --check
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=. \
python tools/capture_iselin_native_right_walk.py --out /tmp/iselin-native-right_walk-review
```

The helper checks all 167 integer positions on its horizontal route, sampled
travel clearance, right facing, idle/walk/stop transitions, 16-frame timings,
native frame sizes, absence of HD overrides, unchanged quest facts and saved
GIF duration totals. `capture.json` records positions, clocks, camera, source
and output hashes and clearance evidence. Shared rendering/GIF routines come
from the front-walk capture helper, whose source hash is also recorded.

All save/settings paths are temporary. This focused art/controller fixture does
not claim full campaign traversal, save migration or gameplay activation.
These isolated fixtures do not modify campaign bindings; current activation is covered by the integration review.
