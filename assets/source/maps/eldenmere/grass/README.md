# Eldenmere emerald terrain rollout

The approved shared grass pack supplies every ground motif and interactive
blade frame. `recipe.json` authors maintained lawn, meadow and woodland regions
and seven irregular grass patches. Exact native coverage masks derive from the
assembled town before rollout, preserving the school, Liam's home, dirt edges,
water animation, masonry and paving from that completed composition. Each
animated frame has its own mask because water/bank silhouettes vary over time.
The recorded old-frame hashes identify that derivation; mask hashes validate
the retained authoring input.

Run `python tools/build_playable_eldenmere.py --terrain-only` after the town and
its later building/story additions have been assembled. Add `--check` to verify
the exported terrain without writing. This path preserves the assembled map's
doors, NPCs, interiors, quest links, collision and route metadata. The original
full-town compiler remains available for rebuilding its earlier base stage;
apply the later building/story builders before the terrain rollout.

The compiler paints canonical grass only through the retained native masks,
then remaps exact archived grass/stem colours in composed art. It never edits
the archived terrain source packs. Legacy static tall plants are replaced by
walkable interactive clumps. Full grass coverage, collision, route masks,
entity footprints and protected approach radii constrain every placement.
