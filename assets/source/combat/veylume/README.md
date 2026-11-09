# Veylume combat artwork

Five original imagegen atlases retain 160 distinct authored drawings of the
same right-facing Electric cave moth. The design uses a segmented indigo body,
amber eyes, four ivory/lavender wings and fine cyan/gold electrical venation.
These PNGs are unmodified generation outputs, including their low-alpha matte.

| Original atlas | Authored cells, in reading order |
| --- | --- |
| `base_hover_flight.png` | Idle 0–15; active flight 16–31 |
| `actions_spark_charge.png` | Static Spark 0–15; first Gather Charge poses 16–31 |
| `actions_charge_flash.png` | Last Gather Charge poses 0–7; Veinflash 8–31 |
| `reactions_hurt_defeat.png` | Hurt/recovery 0–11; defeat/collapse 12–31 |
| `charged_hold.png` | Sustained charged hover 0–31 |

Each atlas uses eight columns and four rows. A few complete wing tips cross a
nominal cell edge, so the exporter selects whole-atlas connected silhouettes
and records their explicit source rectangles. It removes detached alpha
fringe, uses one fixed 0.33 nearest-neighbor scale and one shared 96-color
opaque-only palette, then registers the drawings on a 112 × 104 canvas at
floor anchor (56, 88). It never redraws, warps or synthesizes poses. The final
four collapsed drawings use their authored supporting pixels as floor contact.

`registration.json` owns animation selection and exact integer timing. Static
Spark contacts at 450 ms of 850 ms, Gather Charge signals at 400 ms of 800 ms,
and Veinflash contacts on its authored release pose at 550 ms of 1,000 ms.
Charged hover supplies a full 32-pose loop while the next ATB turn fills.

Rebuild or verify all native exports without changing the originals:

```sh
python tools/build_veylume_combat.py
python tools/build_veylume_combat.py --check
```

The runtime manifest retains every source SHA-256, source cell and rectangle,
registration hash, fixed scale and pose timing. The complete native contact
sheet is `assets/combat/veylume/spritesheet.png`.
