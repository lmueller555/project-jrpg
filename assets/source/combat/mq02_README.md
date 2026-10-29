# MQ02 combat artwork sources

These original transparent PNGs were generated with the image-generation tool.
The exporter mechanically extracts their authored sprites; it does not paint
anatomy, weapons, poses or scenery.

- `mq02_mira_generated_sheet.png`: sixteen left-facing Mira combat/walking
  key poses. References were her approved left-walk review, neutral portrait
  and Caelan's existing combat atlas. Her rose work blouse, brown trousers,
  toolbelt, boots, brown tied hair and cream clip are preserved. The short
  steel-headed spear uses two-handed contact and braced defensive poses.
- `mq02_tusker_generated_sheet.png`: sixteen right-facing Ridgeback Tusker
  poses, including grounded idle breathing, ordinary strike, head-lowered
  preparation, running charge, hurt and collapse. Its thick brown bristles,
  heavy shoulders, gray-ivory tusks and four-legged silhouette remain uniform.
- `mq02_spear_generated.png`: one isolated vertical travel spear, referenced
  from Mira's authored combat atlas, for a matching overworld prop.

Run `python tools/build_mill_combat_assets.py` to reproduce the runtime assets.
Source hashes are retained in each animation manifest and spear metadata.

The generated atlases have small cross-cell weapon and motion overhangs.
The exporter uses binary-alpha connected silhouettes to recover each complete
authored sprite instead of cutting it at an arbitrary grid boundary. It then
applies one fixed nearest-neighbor scale per actor and registers each cutout
at its ground anchor. No limb, tusk or spear tip is redrawn. Runtime alpha is
binary, and every combat frame keeps transparent padding on all four sides.

Mira's runtime canvas is 64×64 with ground anchor (32,54); her body remains
approximately 24×36 pixels. The Tusker uses 96×72 with anchor (48,62) and an
idle body approximately 70×48 pixels. Both are rendered at the same 2× scale
as Caelan, preserving their relative character/monster sizes. The separate
16×48 world spear has hand anchor (8,28), with its point facing upward.

The spear thrust covers the model's 800ms action with its contact frame at
400ms. Tusker strike, preparation and charge align with 900/450ms, 800/400ms
and 1000/500ms duration/impact respectively. The preparation state loops while
the creature is holding its visible charge tell between turns.
