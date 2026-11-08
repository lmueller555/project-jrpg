# Cave water and seepage modules

Approval status: pending visual review.

Native 24-pixel water tiles, fixed limestone banks, 48-pixel stream prefabs,
wet cracks, seepage, trickles, falling drops, ripples and mineral crusts.
Water highlights animate in six 140 ms frames; bank pixels and fixed
water masks never change. Reduced motion holds frame 2.

`water_regions` is an exact set of nonoverlapping [x,y,w,h] rectangles;
`water_mask` is the matching white-water/black-ground bitmap.
Water uses the existing blocked-water rule; shallow is a material
appearance, not a new movement mechanic. Decorative effects add no
floor collision. Anchors are bottom center; stream connections name
the open ports. Native terrain remains independent of crystal light.

Build with `python tools/build_dungeon_water.py`; use `--check` for
deterministic read-only verification. Source: assets/source/terrain/
limestone_cave/water.json. The live cave and runtime are untouched.
