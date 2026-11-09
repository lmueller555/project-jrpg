# Lithrusk combat source art

These three PNGs are unchanged imagegen-authored atlases of the same
right-facing limestone crustacean. Each contains 32 whole-body poses arranged
in an eight-column, four-row grid, for 96 distinct drawings in total.

| Atlas | First 16 poses | Last 16 poses |
| --- | --- | --- |
| `locomotion.png` | Idle breathing and claw/antenna movement | Six-leg crawl cycle |
| `attacks.png` | Claw Clamp: brace, extension, closure, recovery | Shell Bash: crouch, shoulder rotation, impact, recovery |
| `reactions.png` | Hurt compression, flinch and recovery | Buckling, collapse and final shell settling |

`registration.json` records complete connected-body bounds rather than cutting
at nominal cell boundaries. This preserves the extended pincer in the contact
pose. Its floor points register each body on the fixed native anchor `[48,84]`.
The exporter uses one 0.37 nearest-neighbor scale for all three atlases and one
48-color palette, with alpha threshold 128. Low-alpha generated matte residue
does not enter the native frames. No artwork is redrawn, warped or interpolated.

Rebuild or verify the checked-in native frames with:

```sh
python tools/build_lithrusk_combat.py
python tools/build_lithrusk_combat.py --check
```

The exported canvas is 112×96. Every state has 16 genuine authored poses.
Claw Clamp contacts on frame 9 at 400 ms; Shell Bash contacts on frame 9 at
500 ms. Supporting feet and the final collapsed body share the same ground
baseline. The sprite bank contains no detached projectiles or battle effects.
