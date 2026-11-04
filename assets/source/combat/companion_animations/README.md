# Companion combat animation sources — approved

Lucan and Rhea each have an imagegen-authored 4×6 atlas containing 24 poses.
Their `generation.json` files retain prompts and source references. Original
approved combat-ready pixels are preserved as `approved_ready_reference.png`
for comparison. The user approved both complete sets on November 4, 2026.

The shared exporter, `tools/build_companion_combat_animations.py`, mechanically
extracts complete alpha silhouettes, applies binary transparency and one fixed
nearest-neighbor scale per actor, and registers each pose using source-grid
ground points from `recipe.json`. Equipment does not determine the body anchor.
No anatomy is painted, stretched, mirrored or synthesized by the exporter.
Complete connected shapes may extend outside their nominal source cell; Lucan's
contact sword is retained intact rather than cropped to the grid boundary.

| Cells | Animation |
| --- | --- |
| 0–3 | Ready / idle |
| 4–7 | Basic weapon attack |
| 8–11 | Lucan's shield technique / Rhea's casting sequence |
| 12–13 | Guard |
| 14–15 | Hurt / recovery |
| 16–17 | Victory |
| 18–19 | Defeat / kneeling settle |
| 20–23 | Movement cycle, also referenced by the flee alias |

Lucan uses his existing sword-and-shield design. A separate two-handed weapon
set is future work. Rhea retains her purple tanglewood staff, green orb, blonde
hair and emerald dress. Her cast poses are generic animation assets, without
granting a new spell or choosing its element.

Export with `python tools/build_companion_combat_animations.py`. Build review
montages with `python tools/preview_companion_combat_animations.py`. The runtime
uses ordinary PNG frames and version-one animation manifests, not a new rig or
procedural animation controller. Rebuilding the older companion appearance
studies preserves complete combat packs instead of replacing them with one idle.
