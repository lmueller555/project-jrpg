# Lithrusk and Veylume combat art

Lithrusk and Veylume have dedicated right-facing combat sprites for the
Sanctuary cave's first enemy roster. The [Bestiary](BESTIARY.md) retains their
approved stats, levels, actions and elemental profiles. This work adds their
visual presentation and supports Veylume's prepared spell sequence. The
[random encounter system](CAVE_RANDOM_ENCOUNTERS.md) now uses these banks in
one-to-four-enemy cave battles. Damage formulas remain unchanged.

## Visual design

**Lithrusk** is a low, heavy crustacean with overlapping pale limestone plates,
dark joints, amber eyes and substantial pincers. Its six-legged gait stays
grounded. Claw Clamp opens and closes the pincers, while Shell Bash lowers the
shell and drives its mass forward. Its hit sequence jolts the plates and its
defeat sequence settles into a flattened stone-like body.

**Veylume** is an Aether-adapted moth with a narrow dark body, ivory/lavender
wings, cyan and gold veins, and sparking antennae. Its wings articulate through
hovering, flight, spell focus and recoil. Static Spark uses a small electrical
release; Gather Charge builds toward Veinflash. A separate charged hover loop
keeps the wings alive while the next ATB turn fills. Its defeat poses descend
and fold the wings.

The original image-generated atlases are retained under
`assets/source/combat/lithrusk/` and `assets/source/combat/veylume/`, with explicit
registration records and source hashes. Exporters select complete authored
bodies, including pincers and wing tips crossing nominal grid boundaries.
Binary alpha removes translucent matte residue. One nearest-neighbor scale
and one shared palette per species preserve native pixel detail and stable
materials. Export never synthesizes poses or redraws parts of a creature.

## Animation banks

| Species | Native canvas | Fixed anchor | Animation states |
| --- | --- | --- | --- |
| Lithrusk | 112 × 96 | 48, 84 | Idle, walk, Claw Clamp, Shell Bash, hurt, defeat |
| Veylume | 112 × 104 | 56, 88 | Idle, fly, Static Spark, Gather Charge, charged hold, Veinflash, hurt, defeat |

The banks contain **256 authored poses** across 14 animations:

| Animation | Lithrusk frames | Veylume frames |
| --- | ---: | ---: |
| Idle | 16 | 16 |
| Walk / fly | 16 | 16 |
| Claw Clamp / Static Spark | 16 | 16 |
| Shell Bash | 16 | — |
| Gather Charge | — | 24 |
| Charged hold | — | 32 |
| Veinflash | — | 24 |
| Hurt | 16 | 12 |
| Defeat | 16 | 20 |
| **Total** | **96** | **160** |

The [animation review](reviews/cave_enemy_combat/README.md) shows each state
with its frame count and actual duration.

Model impact boundaries remain authoritative: Claw Clamp at 400 ms, Shell Bash
at 500 ms, Static Spark at 450 ms, Gather Charge at 400 ms and Veinflash at
550 ms. The action manifests identify the corresponding contact drawings.
Lithrusk walks during approach and retreat; its strike clock is sampled around
the exact impact boundary so the full attack sequence fits between those
phases. Veylume's charge, release and held wingbeat have separate pose clocks.

## Battle integration

The Bestiary entries reference their own sprite banks with direct action-state
names. Concrete presentations must provide an authored state for every action;
an omitted state cannot silently pass Bestiary validation. Explicit pending
presentation remains available for future species without artwork.

Lithrusk uses Claw Clamp and Shell Bash in sequence. Veylume uses
Static Spark → Gather Charge → Veinflash. Preparation locks a living target;
if that character is defeated, the warning and attack retarget a living party
member. At either authored level, two Veinflashes exhaust its usable burst MP.
It then uses the free Static Spark without wasting turns on unaffordable
charges. Outcomes and loss of the MP needed for Veinflash clear the held state.

The renderer gives Lithrusk a grounded shadow and Veylume a smaller hover
shadow. Hit points, contact reach, projectiles and anchors use the same sprite
scale. Complete occupied bounds fit below the enemy HP bar and above the
command panel, including the native-resolution enlarged-text layout.
Existing actors retain their established presentation. Reduced motion holds
the new idle/charge loops steady and suppresses travel and moving charge arcs.

Local cyan/gold projectiles, charge arcs and impact effects distinguish
Veylume's spells. Element tags and defensive affinities remain authoring data;
these visual effects do not activate elemental damage or absorption.

## Reproduction and review

```sh
python tools/build_lithrusk_combat.py --check
python tools/build_veylume_combat.py --check
python tools/capture_cave_enemy_combat.py
python tools/capture_cave_enemy_combat.py --check
```

The [review](reviews/cave_enemy_combat/README.md) contains an animated sprite
showcase, contact sheet, real BattleScene combat reel and source/artifact hash
verification. This retained review records the original sprite rollout before
random encounters and group presentation. Its source-match check applies to
that revision; generating a new review captures the current runtime. The reel
uses disposable encounter fixtures on the existing battlefield and does not
settle rewards or touch a player's journey or settings.
