# Town NPC — female variant 02

Status: front-facing idle and this palette approved by the user in chat.

Auburn hair in the shared low bun, a sage calf-length dress with short sleeves, green eyes and brown ankle boots. This is an exact palette variant of `../female_01/idle_front.png`, preserving the silhouette, shading layout, skin, outline and boots.

Both eyes retain a dark upper pupil pixel and have one colored iris pixel beneath it. Eye changes use explicit landmarks, so outlines and other dark pixels remain intact. The frame is 24×36 with the shared `[12, 34]` foot anchor.

- `idle_front.png`: native transparent sprite.
- `idle_front.json`: frame, palette, eye landmarks, layers and review status.
- `idle_front_review.png`: 24× nearest-neighbor preview.
- `palette.json`: full named material ramps, eye colors and region references.

Review all three in `../female_variants_review.png`, with eye close-ups in `../female_eyes_review.png`. Source appearance layers are retained under `../../../source/characters/npcs/female_02/layers/`. Rebuild these variants and the comparison with `python tools/build_female_npc_palette_variants.py`.

This work covers front-facing palette variants only. Other facing designs and walking animations are the next planned assets.
