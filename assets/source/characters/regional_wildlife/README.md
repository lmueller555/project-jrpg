# Regional wildlife native art

These are hand-authored native pixel sprites for the fixed Elden Vale wildlife
roster. The complete editable drawing recipes are
`tools/build_regional_wildlife.py`; `palette.json` records their color ramps.
The script paints directly at final resolution, with no reduction, interpolation,
whole-body deformation or generated imagery. It preserves all six original
wildlife props and records their SHA256 hashes in the exported provenance file.

The existing cream fleece, dark warm legs, brown sparrows and amber butterflies
supply the palette and scale reference. The new farm cat is a small taupe tabby
with cream paws and muzzle. Fleece is shaded in small scalloped clusters. Sheep
legs, grazing necks and nuzzling heads are separately drawn; walking never shifts
the whole image. The cat has a connected hook tail, a curled sleeping silhouette,
a planted bow stretch and a tall seated silhouette. Birds fold their wings on
landing and lower their beaks to the same ground plane as the seed spill.
Butterflies close their wings against their body when settled.

## Export API

`assets/characters/regional_wildlife/animation.json` has version 1:

- `families[family]`: native `size` and fixed foot `anchor`, in pixels.
- `clips[family_pose_direction]`: `family`, relative PNG `frames`, parallel
  `durations` in seconds, `loop`, and parallel per-frame `landmarks`.
- `landmarks`: canvas coordinates for `ground_contacts`, plus sheep `muzzle`,
  bird `beak`, and `airborne` for birds and butterflies.
- `props.seeds`: relative filename, native size and anchor for the sparse grain
  spill. It is a static scene decoration, not a collectible or new produce.

Both left and right are exported for every action. Left poses mirror pixels and
landmarks around the canvas midline. Anchor registration is constant through a
clip, with near paws on the anchor row. The controller owns position and flight
elevation. No baked shadow, basket, grain reward or duplicate held prop is present
in animal frames. The empty basket remains the original
`assets/characters/garden_workers/basket.png`.

| Family | Size | Anchor | Poses |
| --- | --- | --- | --- |
| Sheep | 24 × 20 | 12,18 | graze, walk, look, nuzzle |
| Cat | 24 × 18 | 12,16 | sleep, stretch, walk, sit |
| Bird | 12 × 12 | 6,10 | land, peck, fly |
| Butterfly | 12 × 12 | 6,10 | flutter, settle |

Nuzzle, cat stretch and bird land are finite clips. Their final frames can be
held by the controller. Other poses loop at deliberately unhurried timings,
with a short blink, grazing contact or peck inside each longer rest.

## Inspection and reproducibility

`contacts_native.png` shows all right-facing frames at 1× alongside the six
unaltered original animals. `contacts_3x.png` is a nearest-neighbor enlargement.
`poses_preview.gif` plays each action at its manifest timing at 3×. It is an
art-only board, not gameplay evidence; finite actions hold for 800 ms and replay
for comparison. Runtime capture evidence is maintained by the scene owner.

Build and check with:

```sh
python tools/build_regional_wildlife.py
python tools/build_regional_wildlife.py --check
python -m unittest discover -s tests -p test_regional_wildlife_art.py -v
```
