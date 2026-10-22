# Town NPC — female variant 01

Status: draft front-facing idle awaiting user review.

- Dark hair gathered into a low bun, with a tidy fringe and two visible eyes.
- Simple blue calf-length dress with short sleeves, a defined waist and a gently flared skirt.
- Brown ankle boots, with the hem above the boots so later foot movement can remain visible.
- Relaxed standing pose at 24×36 pixels and the shared `[12, 34]` foot anchor.
- Plain clothing and a rounded hairstyle distinguish her from Mira.

## Files

- `idle_front.png`: native sprite with hard transparency.
- `idle_front.json`: frame, anchor, source, palette and approval status.
- `idle_front_review.png`: 24× nearest-neighbor preview on a light background.
- `scale_comparison.png`: male NPC 01, this NPC and Mira at the same enlarged scale.
- `palette.json`: named hair, skin, dress and leather ramps for later variants.

The source also retains four appearance layers: head, bodice/arms, skirt/hands, and calves/boots. They reconstruct the native idle and are not yet articulated walking components. The dress hem is at row 28, with visible calves at rows 29–31 and ankle boots at rows 32–34.

The generated appearance source and repeatable export are retained under `../../../source/characters/npcs/female_01/`. This proposal covers only the first front idle. Other facing designs, palette variants and walking animations will follow approval. The dress will need dedicated skirt poses when walking is prepared.
