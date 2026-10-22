# Town NPC — female variant 01

Status: all four directional idles and this palette approved by the user in chat.

- Dark hair gathered into a low bun, with a tidy fringe and two visible blue eyes.
- Simple blue calf-length dress with short sleeves, a defined waist and a gently flared skirt.
- Brown ankle boots, with the hem above the boots so later foot movement can remain visible.
- Relaxed standing pose at 24×36 pixels and the shared `[12, 34]` foot anchor.
- Plain clothing and a rounded hairstyle distinguish her from Mira.

## Files

- `idle_front.png`: native sprite with hard transparency.
- `idle_front.json`: frame, anchor, source, palette and approval status.
- `idle_front_review.png`: 24× nearest-neighbor preview on a light background.
- `scale_comparison.png`: male NPC 01, this NPC and Mira at the same enlarged scale.
- `palette.json`: named hair, skin, dress, leather and eye colors.

The source also retains four appearance layers: head, bodice/arms, skirt/hands, and calves/boots. They reconstruct the native idle and are not yet articulated walking components. The dress hem is at row 28, with visible calves at rows 29–31 and ankle boots at rows 32–34.

The generated appearance source and repeatable export are retained under `../../../source/characters/npcs/female_01/`. All three front-facing palettes are approved. Left, right and back idles are approved; the front walk is approved, and left, right and back walks are drafts for review. Each walking direction uses dedicated skirt poses.

Compare all three front palettes in `../female_variants_review.png`: dark hair/blue dress/blue eyes, auburn hair/sage dress/green eyes, and blonde hair/plum dress/hazel eyes. The close-up `../female_eyes_review.png` shows both pupils and iris accents at 32× scale. The base design is unchanged apart from the two requested colored iris pixels.

## Approved directional idles

`idle_left.png`, `idle_right.png` and `idle_back.png` add native 24×36 appearances. Each has metadata and a 24× `_review.png`. The low bun is visible from these angles; the waist remains at row 21, hem at row 28, calves at rows 29–31 and boots at rows 32–34. Side profiles have one dark pupil with a blue iris pixel beneath it. The back has no eyes or iris pixels.

`idle_directions.png` and its JSON combine front, left, right and back. `idle_directions_review.png` enlarges them 12×; `../female_idle_directions_review.png` compares all three palettes. All four directions are approved by the user in chat. Source appearance layers are retained under `../../../source/characters/npcs/female_01/directions/layers/`. Rebuild using the base directional exporter followed by `python tools/build_female_npc_palette_variants.py --direction all`.

The [approved front walk](walk_front/README.md) uses shared stride poses, coordinated head-and-shoulder bob, and dedicated skirt/calf/ankle-boot parts. Review the enlarged loop in `walk_front/walk_front_preview.gif`.

The [left](walk_left/README.md), [right](walk_right/README.md) and [back](walk_back/README.md) walks are drafts. `walk_directions_review.gif` compares all four base directions, with the approved front walk unchanged. Build them and the combined sheets with `python tools/build_dress_walk.py --direction all`.
