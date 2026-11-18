# Eldenmere well replacement — PR 1 asset pack

**Status: staged artwork, pending user visual review, not integrated.**
The ordinary game still selects its existing well, drawing mechanism, gardener
animations and pail. Merging this pack does not change that selection or certify
the later mechanism and character performance.

PR 1 establishes the replacement's static artwork and shared geometry: a compact
stone well with a broad visible upper opening, low front masonry, grounded timber
supports, a rear slate canopy, a static windlass reference and a separate pail.
The retained new masters are under
`assets/source/terrain/eldenmere/well_hd/`; their normalization and authored
partitions are defined in its recipe. The staged bank is
`assets/terrain/eldenmere/well_hd/manifest.json`, exported by
`tools/build_eldenmere_well_pack.py`. Construction follows the existing
[visual art standard](../../VISUAL_ART_STANDARD.md) and
[terrain standard](../../TERRAIN_ART_STANDARD.md).

## Review views

- [Proposed well beside Eldenmere's buildings and Caelan](town_proposed_review.png).
- [Current live well beside the proposed static composition](town_before_after.png).
- [Authored structural layers](layer_breakdown.png).
- [Well coverage masks](mask_breakdown.png).
- [Empty-to-full pail variants](pail_fill_variants.png).
- [Registration and future-station diagnostic](geometry_diagnostic.png).

The proposed town views are **offline static asset composites**, not integrated
gameplay captures. An initialized production Game renders the ordinary town,
ground, buildings, residents and Caelan at native **960×640**. It uses disposable
saves/settings, a disabled opening, no seeded quests and no simulation updates.
Only the well's drawing and draw origin are replaced in that disposable Game's
memory. The original live source files and map data are never rewritten.

The labelled review boards retain the complete native scene unscaled, with
captions outside it. The [raw current view](town_live_baseline_native.png) and
[raw proposed view](town_proposed_native.png) each preserve 960×640 pixels.
Caelan's fixture is `[576,914]`, the camera focus is `[528,850]`, and the resulting
camera origin is `[288,690]`, all in logical world units.

The composite keeps the existing overall well sort baseline for this scale and
projection study. It does not establish the final per-layer sorting around a
moving operator, attachment/retrieval contact, animation or interaction behavior.
The coloured geometry and mask boards are diagnostics, not game surfaces.

## Geometry and export contract

| Registration | Logical units | Artwork pixels |
| --- | --- | --- |
| Well canvas | 72×88 | 144×176 |
| Proposed world draw origin | `[492,800]` | Converted once by the renderer |
| Local draw anchor | `[0,0]` | `[0,0]` |
| Local ground registration anchor | `[36,64]` | `[72,128]` |
| Canonical physical support | `[504,840,48,48]` in world coordinates | Existing logical collision remains unchanged |
| Pail canvas | 12×18 | 24×36 |
| Pail grip | `[6,2.5]` | `[12,5]` |

The well master is uniformly fitted as one drawing. Its roof and masonry are
not stretched independently around the former mechanism's coordinates. The
structural layers use authored masks and share one native canvas; the contact
shadow has a separately declared whole-layer opacity. Water has an explicit mask
inside the shaft aperture, and the near masonry, supports and canopy have their
own coverage definitions.

The pail bank contains seven **static** neutral-orientation states, zero through
six water units. Water changes are confined to the authored interior mask;
exterior wood, metal bands, handle and silhouette retain their source pixels.
The pail sheet shows 4× nearest-neighbour inspection examples and native-size
examples. It is not an animation or a live gardener replacement.

Mechanism anchors and future standing stations are preparation targets. They
require motion and character-pose review in the following PRs; a clear collision
probe alone does not establish a believable hand contact. The canonical ground
support remains the live layout's 48×48 logical rectangle, and image alpha does
not create new collision or navigation.

## Preservation evidence

[The clean pre-pack snapshot](production_before.json) records base commit
`665b81702468bb1f177b1c758aa866dc92cf0a69`, all **969 active town files**, map-field
hashes and **207 protected legacy well/gardener/runtime/build files**.
[The observation record](observations.json) checks that exact snapshot before
and after capture. Collision, navigation, live well selection, routines and
existing artwork remain byte-identical.

Every changed pixel in the proposed native town view lies inside the union of
the old and new well drawing canvases. The record retains the actual changed
pixel count and confirms **zero changes outside that union**. The in-memory map
metadata and quest, party, inventory and flag state also remain unchanged.
All eight PNG witnesses have recorded SHA-256 hashes.

Validation passes all **14 focused pack checks**, including the regression that
keeps the two confirmed masonry-boundary samples outside the water layer. The
pack's read-only check verifies **28 exports**; the unchanged live town producer
also verifies all **997 existing exports**. The current live well's older
rendering/animation issues remain for the later mechanism and integration PRs.

The capture revision records the checkout base and explicitly discloses an
uncommitted pack/helper when present. Exact staged-manifest, helper and PNG hashes
identify the reviewed bytes; a base commit is not presented as an already
committed new asset revision.

Regenerate these static reviews from a checkout with the retained production
snapshot using:

```sh
python tools/build_eldenmere_well_pack.py --check
python -m unittest discover -s tests -p test_eldenmere_well_pack.py -v
python tools/capture_eldenmere_well_pack.py
```

## Later work

- PR 2 supplies moving mechanism parts, continuous rope/bucket motion, water
  effects, timing and the independent controller.
- PR 3 supplies the gardener's matching work poses and carrying/pouring bindings.
- PR 4 activates the coordinated replacement in the live town and validates
  movement, depth, obstruction, offscreen work and reset/Continue behavior.
- PR 5 supplies player examination and sound feedback.
- PR 6 removes remaining obsolete paths and completes final acceptance.

None of those later features is established by this static pack or its previews.
