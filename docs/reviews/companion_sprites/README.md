# Companion sprite review

**Status:** All nine base sprite designs are approved, including Edran’s
sky-blue and silver revision. Character biographies are approved
in the [companion guide](../../narrative/game_01/COMPANIONS.md).

[Review Edran’s updated design](edran_sky_blue_review.png).
[Open the nine-pose comparison](sprite_comparison.png).
[Compare their scene scale with Caelan](scale_comparison.png).

Rows are Lucan Rooke, Rhea Sorel and Edran Hale. Columns show the front-facing
overworld idle, left-facing combat-ready pose and larger cinematic standing
pose. Each enlarged image uses nearest-neighbor sampling, with its actual
native texture shown below. The scale board places Caelan and the companions
on the same ground baseline at the same display scale for each scene type.

| Format | Native canvas | Intended use |
| --- | --- | --- |
| Overworld | 24×36 | Front idle matching the existing 24-pixel tile world |
| Combat | 64×64 | Static left-facing battle stance with room for equipment |
| Cinematic | 96×112 | Detailed standing pose matching the opening's actor canvas |

Rhea follows the requested blonde hair, blue eyes, fitted green dress and
purple tanglewood staff topped by a glowing green orb. Lucan's approved visual
identity uses steel, oxblood and gold; Edran's revised outfit uses sky blue,
silver and cool gray.

All three are adults: Lucan 24, Rhea 22 and Edran 46. Each format retains the
character's costume and equipment. Their metadata records the individual
artwork approval status;
this asset work does not insert them into existing quests or alter party rules.
Combat manifests describe a single static idle frame, rather than a finished
animation set.

[Verification](verification.json) records the nine PNGs, source hashes, crops,
foot registration, palette counts and uniform export scales. Every native
texture uses binary transparency. Rhea's front idle anchor is [10, 34], giving
her staff room inside its 24-pixel frame while preserving her body scale;
Lucan and Edran use [12, 34]. Combat and cinematic anchors are shared.

Rebuild all assets and both boards with:

    python tools/build_companion_sprite_studies.py
