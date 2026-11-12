# Per-hit damage formula

The approved Project JRPG formula follows the layered approach of Final Fantasy
damage calculations. Physical and magical attacks share the same growth curve.
The pure backend lives in [`combat_damage.py`](../combat_damage.py).

```text
Base damage = (Offense² / 5) × Potency × 100 / (100 + Defense)
            = 20 × Potency × Offense² / (100 + Defense)
```

| Attack | Offense | Defense |
| --- | --- | --- |
| Physical | Attacker Str | Defender Def |
| Damaging magick | Attacker Mag | Defender M. Def |

Offense and Defense are effective ratings between 0 and 999. The character
wrappers read the appropriate `value()` from each participant. They do not read
HP, MP, Spr, Speed, Acc, Eva, Lck or character level, and do not mutate resources
or progression. Enemy HP/MP and encounter budgets are independent design work;
the calculator does not construct or constrain enemy health profiles.

The [traditional leveling foundation](LEVELING.md) now supplies approved natural
character curves and the larger enemy HP baseline. This calculator retains the
existing formula and damage caps. Raising an offensive rating by 50% produces
approximately 2.25 times the damage at equal potency and defense; enemy/profile
and future bot inheritance tuning must account for the squared offense term.

## Potency and modifiers

Potency is a positive action multiplier: 1 for a basic attack, 2 or 3 for a
stronger action, and 12 for the illustrative exceptional attack in the approved
examples. These examples do not assign powers, costs or effects to existing
named abilities.

| Parameter | Effect |
| --- | --- |
| `critical=True` | ×1.5; the caller resolves critical eligibility/chance |
| `affinity=2` | Elemental weakness, ×2 |
| `affinity=0.5` | Elemental resistance, ×0.5 |
| `affinity=1` | Neutral element |
| `affinity=1.5` | Intermediate response, ×1.5; any finite multiplier from 0 through 2 is accepted |
| `affinity=0` or `immune=True` | Zero damage |
| `protected=True` | Appropriate physical/magical protection, ×0.5 |
| `variance_percent` | Integer 95–105, converted to a percentage multiplier |
| `hit=False` | Miss: zero damage |
| `break_damage_limit=True` | Raise the per-hit ceiling from 9,999 to 99,999 |

All modifiers apply before rounding. Exact rational arithmetic preserves the
full intermediate value; floating-point potency values are interpreted by their
decimal representation. Round down once after all multipliers, enforce a minimum
of 1 on a landed nonimmune damaging hit, then apply the permitted cap. A miss or
immunity always deals 0, including at zero Offense.

Cap-breaking changes the ceiling only. It supplies no damage multiplier and
does not change the attribute caps. Hit/evasion and critical-chance rules remain
the future combat controller's responsibility.

## Backend API

```python
from combat_damage import (
    calculate_damage, physical_damage, magical_damage, roll_variance,
)

calculate_damage(50, 40, potency=2)  # 714
calculate_damage(255, 200, potency=3)  # 9999
calculate_damage(255, 200, potency=3, break_damage_limit=True)  # 13005

# Participants need a value(attribute_id) method. CharacterAttributes supports it.
physical_damage(attacker, defender, potency=1)
magical_damage(caster, defender, potency=2)

# A future controller owns the RNG and may roll independently for each hit.
variance = roll_variance(battle_rng)
physical_damage(attacker, defender, variance_percent=variance)
```

`calculate_damage` accepts keyword-only `critical`, `affinity`, `protected`,
`variance_percent`, `hit`, `immune` and `break_damage_limit` options. Its default
variance is 100%, making explicit calculations deterministic. `roll_variance`
uses the supplied object's `randint(95, 105)`; it never accesses global random
state. An actual battle controller will supply its owned RNG.

Ratings and variance require integers, with booleans rejected. Potency accepts
positive finite integers, floats or `fractions.Fraction` values. Affinity accepts
any finite integer, float or Fraction multiplier from 0 through 2; flags must
be booleans. Invalid inputs are rejected before miss/immunity resolution,
leaving participants unchanged.

## Reference results

These are successful neutral hits at exactly 100% variance, with no critical
or protection. The normal per-hit cap is applied to both result columns.

| Offense | Defense | Potency 1 | Potency 3 |
| ---: | ---: | ---: | ---: |
| 10 | 10 | 18 | 54 |
| 25 | 20 | 104 | 312 |
| 50 | 40 | 357 | 1,071 |
| 100 | 80 | 1,111 | 3,333 |
| 150 | 120 | 2,045 | 6,136 |
| 200 | 150 | 3,200 | 9,600 |
| 255 | 200 | 4,335 | 9,999 |
| 255 | 255 | 3,663 | 9,999 |

At Offense 255 against Defense 200:

| Action | Before cap | Normal result | Cap-breaking result |
| --- | ---: | ---: | ---: |
| Potency 3 | 13,005 | 9,999 | 13,005 |
| Potency 12 | 52,020 | 9,999 | 52,020 |
| Potency 12 and weakness ×2 | 104,040 | 9,999 | 99,999 |

Offense 50, Defense 40 and potency 2 produce 714 damage at 100% variance,
678 at 95% and exactly 750 at 105%. Intermediate truncation would change some
results: Offense 43 against Defense 43 at potency 3 must deal 775, rather than
tripling an already rounded basic hit. Protection also precedes capping:
Offense 255 against Defense 200 at potency 3 with protection deals 6,502.

## Multiple hits and future integration

Calculate and cap every hit separately. Four hits of 3,000 total 12,000 without
cap-breaking; no additional 9,999 action-total cap is applied. Action authors
must account for both hit count and potency per hit when balancing overall
power. Potency is supplied per hit rather than automatically divided by the
number of hits.

The module supplies damage mathematics only. It does not start battles, spend
MP, select targets, remove HP, roll accuracy or critical chance, unlock the
damage-limit break, or assign enemy values. The first [ATB battle](COMBAT.md)
now uses this shared calculator for Attack, Aether Dart and the Bat's abilities.
Other combat actions will use the same backend. Healing remains separate
and will use Spirit. Existing opening-quest spell outcomes remain authored scenes.

## Live elemental Spellblade use

Aqua Edge, Flame Edge and Ice Edge apply an enemy’s stored Water, Fire or Ice
percentage respectively to their magical component;
the physical component retains neutral physical behavior. The full 0–200%
range is supported, including intermediate values such as Lithrusk’s 150%
Water response. Vespermaw resolves against its current channeled form: its
weakness takes 200% magical damage, its matching element is absorbed, and
other elements retain 100%. Matching-element absorption restores the neutral-affinity
magical amount up to missing HP and does not revive an enemy. Aether Edge stays
non-elemental. This extends elemental resolution without changing the approved
base offense/defense curve, ordinary variance or damage caps.

The three authored cave bosses expose ×1.50 incoming damage during their
post-heavy-hit recovery. This multiplier applies once to a composed Spellblade
hit before the ordinary cap, rather than once to each component and again to
the sum. Guard, affinity and absorption retain their existing ordering.
