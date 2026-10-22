# Town NPC — male variant 02

Status: all four directional idles and this palette are approved by the user in chat.

Black hair, a rust shirt, charcoal trousers and brown boots. This is an exact palette variant of the approved `../male_01/idle_front.png`: the silhouette, pose, skin, eyes and transparency are preserved. Material regions keep hair recoloring separate from brown leather and clothing accents.

- `idle_front.png`: transparent native 24×36 front idle.
- `idle_front_review.png`: 24× nearest-neighbor preview on a light background.
- `idle_front.json`: frame, shared `[12, 34]` anchor, source, recipe and review status.
- `palette.json`: material overrides, regions and shade aliases.

Compare all three in `../male_variants_review.png`. Rebuild with `python tools/build_npc_palette_variants.py` from the repository root. The approved front walk is linked below.

## Approved directional idles

New `idle_left.png`, `idle_right.png` and `idle_back.png` frames apply this palette to the corresponding base views, preserving their exact silhouettes. Each has matching JSON metadata and a 24× `_review.png` preview. All directional appearances are approved.

`idle_directions.png` is the native 96×36 strip ordered front, left, right, back; `idle_directions.json` records rectangles and frame statuses. `idle_directions_review.png` shows all four at 12× scale. Compare every variant in `../male_idle_directions_review.png`. Rebuild all directions with `python tools/build_npc_palette_variants.py --direction all`.

## Approved front walk

The [four-frame front walk](walk_front/README.md) applies this approved palette to the approved base cycle. Its stride and coordinated head-and-shoulder bob match the base exactly. Review all three palettes together in `../male_walk_front_variants_review.gif`. This front-walking animation is approved.
