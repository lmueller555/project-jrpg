# Town NPC — female variant 03

Status: base palette and original directional appearances approved. The left/right profile-jaw cleanup is approved by the user.

Blonde hair in the shared low bun, a plum calf-length dress with short sleeves, hazel eyes and brown ankle boots. This is an exact palette variant of `../female_01/idle_front.png`, preserving the silhouette, shading layout, skin, outline and boots.

Both eyes retain a dark upper pupil pixel and have one colored iris pixel beneath it. Eye changes use explicit landmarks, so outlines and other dark pixels remain intact. The frame is 24×36 with the shared `[12, 34]` foot anchor.

- `idle_front.png`: native transparent sprite.
- `idle_front.json`: frame, palette, eye landmarks, layers and review status.
- `idle_front_review.png`: 24× nearest-neighbor preview.
- `palette.json`: full named material ramps, eye colors and region references.

Review all three in `../female_variants_review.png`, with eye close-ups in `../female_eyes_review.png`. Source appearance layers are retained under `../../../source/characters/npcs/female_03/layers/`. Rebuild these variants and the comparison with `python tools/build_female_npc_palette_variants.py`.

The front palette is approved. Left, right and back idles are approved; all four walking cycles are approved.

## Approved directional idles

`idle_left.png`, `idle_right.png` and `idle_back.png` add native 24×36 appearances. Each has metadata and a 24× `_review.png`. The low bun is visible from these angles; the waist remains at row 21, hem at row 28, calves at rows 29–31 and boots at rows 32–34. Side profiles have one dark pupil with a hazel iris pixel beneath it. The back has no eyes or iris pixels.

`idle_directions.png` and its JSON combine front, left, right and back. `idle_directions_review.png` enlarges them 12×; `../female_idle_directions_review.png` compares all three palettes. All four directions are approved by the user in chat. Source appearance layers are retained under `../../../source/characters/npcs/female_03/directions/layers/`. Rebuild using the base directional exporter followed by `python tools/build_female_npc_palette_variants.py --direction all`.

## Approved walking palettes

The front, left, right and back walks use blonde hair, a plum dress and hazel iris accents. They are exact color variants of the approved blue base cycles: stride, arm swing, coordinated bob, neck height, skirt sway, hem lift, boots and 140 ms timing are unchanged. Fronts show two iris accents, profiles one, and backs none.

`walk_directions_review.gif` shows this palette's four directions. `../female_walk_all_variants_review.gif` compares all three palettes with directions as rows and palettes as columns. Each `walk_<direction>/` contains four native frames, a sheet, metadata, a recipe, a static strip and a 20× looping preview. All eight sage and plum palette cycles are approved by the user in chat; all twelve female NPC walking cycles are now approved.

Rebuild with `python tools/build_female_npc_walk_variants.py --direction all`.
