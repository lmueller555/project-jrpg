# Iselin — native overworld actor

The four native directional idles and all four 16-frame walking cycles are
approved and integrated. `actor.json` is the reusable actor definition;
`animation.json` and `native_overworld.png` register the approved cells through
the ordinary sheet-based actor loader.

- Frame: 24×36 RGBA at one artwork pixel per world pixel.
- Draw anchor: `[12,30]`; foot anchor: `[12,34]`; collision probe: 8×4.
- Walk timing: 16×35 ms = 560 ms per full two-step cycle, in every direction.
- Stopping and conversation choose the approved facing idle. The existing
  movement clock, routes, world positions and collision remain authoritative.
- Campaign, Sanctuary cast and return escorts use the same native actor.
  Seated, arrival and aerial views use the corresponding native design exports.
- Dialogue keeps the approved 72×72 portrait and its separate retained master.

The approved source PNGs in `native_idles/` and `native_walk_*` are preserved
byte for byte. Their individual review sheets remain useful inspection assets;
`native_overworld.png` is the combined live registration. Superseded detailed
sprite banks, trial exports and their dedicated builders were removed.

```sh
python tools/build_iselin_native_actor.py --check
python tools/export_iselin_native_idles.py --check
python tools/export_iselin_native_front_walk.py --check
python tools/export_iselin_native_left_walk.py --check
python tools/export_iselin_native_right_walk.py --check
python tools/export_iselin_native_back_walk.py --check
python tools/build_regent_iselin.py --check
python tools/export_iselin_portrait.py --check
```

Authoring stays centralized in the
[sprite and animation standard](../../../docs/SPRITE_ANIMATION_STANDARD.md).
Current production evidence and fixture limits are in the
[native integration review](../../../docs/reviews/iselin_native_integration/README.md).
The separate directional approval reviews retain the original reviewed captures.
