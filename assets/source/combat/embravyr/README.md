# Embravyr authored combat sources

Embravyr is a pure Fire-Aether elemental coalesced around one exposed red
crystal. Its asymmetric dark limestone shell, loose mineral limbs and flowing
fire ribbons contain no organic head, eyes, mouth or humanoid body.

These four original image_gen PNGs are preserved unchanged from their chosen
generation outputs. They contain 184 distinct authored drawings in an 8×6
organizational grid; the final sheet uses 40 cells and leaves its last row blank.
The source art follows the established Lithrusk / Vespermaw pixel-art shading.
Later sheets reference the chosen Embravyr design to preserve its core and shell.

| Source atlas | Authored cells |
| --- | --- |
| `emerge_idle_lash.png` | Emerge 16, idle 16, Cinder Lash 16 |
| `emberwash_gather.png` | Emberwash 24, Gather Embers 24 |
| `charged_lunge_hurt.png` | Charged Hold 16, Furnace Lunge 24, hurt 8 |
| `cooling_defeat.png` | Cooling 16, defeat 24; final 8 cells unused |

`registration.json` records each retained source hash, exact pose rectangle,
anatomical floor, exposed core, casting origin and contact point. Source cells
are organizational indices rather than cutting masks: the first cooling pose
extends slightly across its nominal cell boundary, so its explicit rectangle
retains the complete drawing through the transparent gap before its neighbour.
Disconnected mineral fragments and fire ribbons belong to their authored pose
and are retained. No connected-body filter erases them.

The deterministic exporter applies only explicit extraction, binary alpha at
128, a shared 64-color opaque palette, fixed 0.72 nearest-neighbor scale and
floor/core registration onto a 160×144 canvas anchored at `(80, 128)`.
It does not mirror, rotate, deform or synthesize animation poses. Every exported
native drawing has a distinct pixel hash and is used once.

```sh
python tools/build_embravyr_combat.py
python tools/build_embravyr_combat.py --check
```
