# Vespermaw source drawings

Eight retained image-generated atlases provide 256 distinct whole-body poses
for the Sanctuary cave miniboss. Each source is an unchanged generated PNG,
with 32 right-facing drawings arranged in eight columns and four rows.
The original locomotion design received an image-generation cutout correction
to provide transparent margins; the other seven atlases use that creature's
anatomy, materials and palette as their reference.

The design is a large pale cave predator: powerful forelimbs, a broad jaw,
small ears, a short tail and mineral crusts along the shoulders and spine.
Tiny blue and violet microcrystals, cyan eyes and a faint throat light connect
it to the Sanctuary's crystal walls. It remains a living quadruped throughout
the action and collapse sequences.

| Atlas | Authored poses |
| --- | --- |
| `locomotion.png` | 16 idle, 16 prowl |
| `raking_claw.png` | 32 claw strike |
| `confluence_roar.png` | 32 inhale, roar and settle |
| `gather_resonance.png` | 32 progressive charge windup |
| `charged_hold.png` | 32 charged breathing loop |
| `ruinous_pounce.png` | 32 crouch, leap, contact and landing |
| `reactions.png` | 16 exhausted breathing, 16 hurt |
| `defeat.png` | 32 stagger, buckle, collapse and settle |

`registration.json` records original source hashes, complete-body bounds,
anatomical ground registration and per-frame attachment points. The exporter
selects connected opaque bodies, removes low-alpha matte residue, registers
one shared 64-color palette and applies one fixed nearest-neighbor scale.
It does not synthesize intermediate drawings or inflate the count with
transformed copies. Airborne poses retain their height above the ground.

Rebuild or verify from the repository root:

```sh
python tools/build_vespermaw_combat.py
python tools/build_vespermaw_combat.py --check
```

See [combat art documentation](../../../../docs/VESPERMAW_COMBAT_ART.md) and
the [animation review](../../../../docs/reviews/vespermaw_combat/README.md).
