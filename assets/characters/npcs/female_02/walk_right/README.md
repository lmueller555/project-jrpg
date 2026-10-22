# Female NPC 02 — right walk

Status: draft for user review. The palette and directional idle designs are approved.

Four native 24×36 frames apply auburn hair, a sage dress and green eyes to the approved blue base's right cycle. Exact named-color replacements preserve every pixel position, alpha, shading role, stride, arm swing, coordinated head/neck/shoulder bob and skirt pose. Skin, outlines and brown ankle boots remain identical. Fronts retain two colored irises, profiles one; back views have none.

Playback follows the base at 140 ms per frame, with a 560 ms loop and foot anchor `[12, 34]`. All offsets are baked into the pixels. Contact hems stay at row 28; passing hems at 27. The recipe retains the approved costume poses and records color replacements and source animation. Animation metadata records eye landmarks after bob offsets and all posed layer paths.

- `frame_01.png`–`frame_04.png`: native transparent frames.
- `spritesheet.png`: native 96×36 playback strip.
- `animation.json`: phases, timing, anchor, eye landmarks, layers and draft status.
- `recipe.json`: base recipe, material map, palette source and rebuild tool.
- `frames_review.png`: all four poses at 12× nearest-neighbor scale.
- `walk_right_preview.gif`: 20× looping preview on a light background.

Rebuild with `python tools/build_female_npc_walk_variants.py --direction right` from the repository root. Use `--direction all` to rebuild all palette cycles, per-character four-direction boards and synchronized three-palette comparisons. The approved blue base remains read only. Existing per-cycle approval statuses survive rebuilding.
