# Leveling foundation review

This checkpoint implements the approved character/monster curves as standalone
code and validated design data. The shared effective rating caps are active:
ordinary ratings 999, Speed 255, player HP 9,999 and MP 999. The approved growth curves and authored encounter ratings remain available
independently of the live item-reward flow.

The [canonical leveling specification](../../LEVELING.md) records all five
character profiles, XP rules, caps, enemy growth and unresolved policies. The
[enemy catalogue](../../ENEMY_ARCHETYPES.md) records ten qualitative stat
profiles, twenty approved concepts and fourteen reusable behavior descriptions.
Numerical profile/species weights remain explicitly unauthored.

## Reproducible curve artifacts

- [Growth CSV](growth.csv): all 100 levels for the five characters and the fixed
  enemy reference, totaling 600 rows. XP columns describe the player progression
  and monster reward curves at that row's level; enemies do not earn XP.
- [Checkpoints](checkpoints.md): readable comparisons at levels 1, 10, 25, 50,
  75, 90 and 100.
- [Validation record](validation.json) and [regression output](tests.txt).

Reproduce from the repository root with an environment containing the project's
Python dependencies:

```sh
python tools/preview_leveling.py --levels 1 10 25 50 75 90 100
python tools/preview_leveling.py --all-levels --format csv
```

The preview only prints results. It does not load Pygame or read/write a journey,
settings or inventory state. Output is deterministic and can be generated
from another working directory using the script's absolute path.

## Verification scope

The final regression passed **647 tests and 2,633 subtests across 58 modules**.
Independent review found no blocking issues. The validation record includes
source and artifact hashes from that checkpoint, plus its authored encounter
comparison. Those hashes are historical references, not current source checks.

Tests cover XP thresholds, rounding before doubling, multi-level awards, the
level-100 cap, malformed records, every character curve across levels 1–100,
enemy HP anchors and monotonicity, raw fixed-reference averaging, multiplier
validation, catalog references and the enlarged effective caps. Independent
review also checked the full curves against high-precision calculations.

Integration tests feed generated profiles through real `CharacterAttributes`
snapshots and three-member `BattleModel` formations. An endgame spell resolves
against a 50,000-HP enemy; an explicitly modified 999-Magick fixture reaches the
existing 9,999 damage cap. These are isolated test fixtures, not live encounter
balance changes.

Existing save, party, bot and victory/Spoils regressions covered the earlier
foundation checkpoint. Its validation record is historical; current removal
and migration validation belongs to the latest regression suite. Combat XP distribution, resource recovery, old-save
conversion, numerical enemy profile weights and future Stagger remain separate
design work.
