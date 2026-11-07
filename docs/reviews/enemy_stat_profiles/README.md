# Approved enemy stat profile checkpoint

The ten approved numerical profiles are executable through
`profile_enemy_stats(profile_id, level)`. All eleven weights are explicit in
the [catalogue](../../../assets/combat/enemy_archetypes.json), with the full
table and API described in [Enemy archetypes](../../ENEMY_ARCHETYPES.md).

The profile, optional species factors and optional tier factors multiply the
unrounded baseline before one final half-up rounding and cap operation. No
individual monster levels, species adjustments, boss multipliers or AI changes
are assigned in this checkpoint.

## Review artifacts

- [Growth CSV](growth.csv): all 100 levels for five characters, the enemy
  baseline and ten enemy profiles, totaling 1,600 rows. XP columns describe
  the player/reward curves at that level; enemies do not earn XP.
- [Checkpoints](checkpoints.md): levels 1, 25, 50, 75 and 100.
- [Validation record](validation.json) and [test output](tests.txt).

Reproduce the numeric preview without opening the game or reading a journey:

```sh
python tools/preview_leveling.py --enemy-profiles --levels 1 25 50 75 100
python tools/preview_leveling.py --enemy-profiles --all-levels --format csv
```

The original preview remains unchanged when `--enemy-profiles` is omitted.

## Settled player policies

`combat_xp_allocations(amount, active_ids, current_hp)` gives the full encounter
amount to each living active combatant, zero to KO members, and no entries for
reserves. Eligibility uses the combat HP snapshot before post-battle recovery.
`CharacterAttributes.apply_growth(gains)` increases permanent stats while
leaving current HP and MP unchanged, including zero. Named modifiers retain
their own ownership, and invalid growth is rejected atomically.

These helpers encode the approved policies. Live battle XP and saved character
levels still await encounter/recruitment levels and the remaining integration
rules; existing item receipts, encounters and saves retain their current flow.

## Validation

The regression passed **302 tests and 2,894 subtests across 25 modules**,
covering growth, profiles, attributes, real battle resolution, party state,
bot ownership, item rewards, legacy conversion and save/Continue behavior.
Independent review found no blocking issues and matched all 1,000 enemy
profile/level combinations against a 60-digit reference calculation.

Tests verify exact weights and endpoints, composition before rounding/caps,
malformed inputs and detached exports. Real battle fixtures demonstrate the
Armored/Warded physical and magical tradeoffs. Growth fixtures preserve depleted
resources across all five characters, including no revival of a KO character.
