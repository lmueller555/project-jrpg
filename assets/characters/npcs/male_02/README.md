# Town NPC — male variant 02

Status: draft awaiting user review.

Black hair, a rust shirt, charcoal trousers and brown boots. This is an exact palette variant of the approved `../male_01/idle_front.png`: the silhouette, pose, skin, eyes and transparency are preserved. Material regions keep hair recoloring separate from brown leather and clothing accents.

- `idle_front.png`: transparent native 24×36 front idle.
- `idle_front_review.png`: 24× nearest-neighbor preview on a light background.
- `idle_front.json`: frame, shared `[12, 34]` anchor, source, recipe and review status.
- `palette.json`: material overrides, regions and shade aliases.

Compare all three in `../male_variants_review.png`. Rebuild with `python tools/build_npc_palette_variants.py` from the repository root. Other directions and walking frames will follow appearance approval.
