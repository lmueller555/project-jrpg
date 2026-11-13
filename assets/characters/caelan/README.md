# Caelan — current overworld artwork

The overworld quality refresh replaces the four directional idles, sixteen walk
frames and sixteen run frames with registered authored drawings. Status is
**review**, pending the user's visual review after merge. Earlier approvals
remain historical records; they do not approve this new appearance.

Caelan retains chestnut hair, ivory sleeves/tunic, teal tabard with ochre edging,
brown leather belt/boots, wrist bracers, dark trousers and the anatomical-left
hip pouch. Profiles have distinct authored faces, sleeves and near/far limbs.
The one-pixel warm near-black contour matches Mira's overworld line weight.
It sits inside the existing alpha silhouette, retaining bright skin highlights
and interior material shading rather than expanding the character.

All individual runtime frames stay **24×36**, with metadata foot anchor
`[12,34]`. The map's existing draw anchor `[12,30]`, player collision, movement
speed and gait timing are preserved. Walks remain four phases at 140 ms each;
runs remain four phases at 100 ms with compact raised flight poses. Registration
moves whole drawings; it never stretches anatomy or changes planted feet within
a drawing. Ordinary travel depicts no separate sword or tool.

Rebuild with:

```sh
python tools/build_caelan_overworld.py
python tools/build_caelan_overworld.py --check
```

Sources, exact rectangles, scales and hashes are in
`../../source/characters/caelan/overworld_refresh/`. The main builder refreshes
individual runtime PNGs, current combined sheets, manifests and scoped world
pose derivatives. Historical procedural walk/run builders describe older art;
the authored builder is the current source of truth.

Current preview and validation evidence:
[outline revision](../../../docs/reviews/caelan_outline/README.md) and
[earlier overworld quality review](../../../docs/reviews/caelan_overworld_refresh/README.md).
The earlier review GIFs and approval manifests remain unchanged as history.
