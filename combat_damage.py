"""Pure per-hit physical and magical damage, independent of battle state.

Base damage is 20 * potency * offense**2 / (100 + defense). Modifiers remain
exact until a single final floor, followed by the landed-hit minimum and cap.
Callers resolve accuracy and critical eligibility, supply the matching defensive
effect, and explicitly request a variance roll when they need randomness.
"""
from __future__ import annotations

from fractions import Fraction
import math
from typing import Protocol

from character_attributes import ATTRIBUTE_CAPS


NORMAL_DAMAGE_CAP = 9999
BREAK_DAMAGE_CAP = 99999
MIN_VARIANCE_PERCENT = 95
MAX_VARIANCE_PERCENT = 105
MAX_ATTRIBUTE_RATING = ATTRIBUTE_CAPS['str']

Scalar = int | float | Fraction
_AFFINITIES = frozenset((Fraction(0), Fraction(1, 2), Fraction(1), Fraction(2)))


class AttributeValues(Protocol):
    """Effective ratings supplied by a character or future enemy profile."""

    def value(self, identifier: str) -> int: ...


class VarianceRandom(Protocol):
    """An injected random source, such as a seeded random.Random instance."""

    def randint(self, minimum: int, maximum: int) -> int: ...


def _rating(value: int, name: str) -> None:
    if type(value) is not int:
        raise TypeError(name+' must be an integer rating')
    if not 0 <= value <= MAX_ATTRIBUTE_RATING:
        raise ValueError(name+' must be between 0 and '+str(MAX_ATTRIBUTE_RATING))


def _fraction(value: Scalar, name: str) -> Fraction:
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, Fraction):
        return Fraction(value.numerator, value.denominator)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(name+' must be finite')
        # Decimal-facing inputs such as 1.5 keep their intended exact value.
        return Fraction(str(value))
    raise TypeError(name+' must be an integer, float or Fraction')


def calculate_damage(
        offense: int, defense: int, potency: Scalar = 1, *,
        critical: bool = False, affinity: Scalar = 1, protected: bool = False,
        variance_percent: int = 100, hit: bool = True, immune: bool = False,
        break_damage_limit: bool = False) -> int:
    """Calculate one damaging hit without changing any character or resource.

    Ratings are integers from 0 to 255; potency is positive and finite. Affinity
    is 0 (immune), 0.5 (resistant), 1 (neutral), or 2 (weak). Critical hits apply
    x1.5, matching protection applies x0.5, and variance is an integer percent
    from 95 through 105. The deterministic default uses 100% variance.

    All inputs validate before a miss or immunity returns zero. Otherwise the
    result is floored once and has a minimum of one, even at zero offense. Its
    per-hit ceiling is 9,999 or 99,999 when break_damage_limit is enabled.
    Wrong types raise TypeError; invalid numeric ranges raise ValueError.
    """
    _rating(offense, 'offense')
    _rating(defense, 'defense')
    power = _fraction(potency, 'potency')
    if power <= 0:
        raise ValueError('potency must be positive')
    element = _fraction(affinity, 'affinity')
    if element not in _AFFINITIES:
        raise ValueError('affinity must be 0, 0.5, 1 or 2')
    if type(variance_percent) is not int:
        raise TypeError('variance_percent must be an integer')
    if not MIN_VARIANCE_PERCENT <= variance_percent <= MAX_VARIANCE_PERCENT:
        raise ValueError('variance_percent must be between 95 and 105')
    for name, value in (('critical', critical), ('protected', protected),
                        ('hit', hit), ('immune', immune),
                        ('break_damage_limit', break_damage_limit)):
        if type(value) is not bool:
            raise TypeError(name+' must be a bool')
    if not hit or immune or not element:
        return 0

    damage = Fraction(20*offense*offense, 100+defense)*power*element
    if critical:
        damage *= Fraction(3, 2)
    if protected:
        damage *= Fraction(1, 2)
    damage *= Fraction(variance_percent, 100)
    rounded = max(1, damage.numerator//damage.denominator)
    cap = BREAK_DAMAGE_CAP if break_damage_limit else NORMAL_DAMAGE_CAP
    return min(cap, rounded)


def _value(source: AttributeValues, identifier: str) -> int:
    read = getattr(source, 'value', None)
    if not callable(read):
        raise TypeError('attribute providers must expose value(identifier)')
    return read(identifier)


def physical_damage(attacker: AttributeValues, defender: AttributeValues,
                    potency: Scalar = 1, **options) -> int:
    """Calculate Str versus Def; options are those of calculate_damage.

    The caller sets protected for an applicable physical protective effect and
    critical only after that action is eligible for, and resolves, a critical.
    """
    return calculate_damage(_value(attacker, 'str'), _value(defender, 'def'),
                            potency, **options)


def magical_damage(attacker: AttributeValues, defender: AttributeValues,
                   potency: Scalar = 1, **options) -> int:
    """Calculate Mag versus M. Def; options are those of calculate_damage.

    Spirit does not contribute to damaging magicks. The caller sets protected
    for an applicable magical protective effect. This does not calculate healing.
    """
    return calculate_damage(_value(attacker, 'mag'), _value(defender, 'm_def'),
                            potency, **options)


def roll_variance(rng: VarianceRandom) -> int:
    """Roll one 95-105% per-hit variance using an explicit random source.

    No random state is owned by this module. A battle can provide a seeded RNG
    and call this once per hit, passing the result as variance_percent.
    """
    roll = getattr(rng, 'randint', None)
    if not callable(roll):
        raise TypeError('rng must expose randint(minimum, maximum)')
    result = roll(MIN_VARIANCE_PERCENT, MAX_VARIANCE_PERCENT)
    if type(result) is not int:
        raise TypeError('rng must return an integer variance percent')
    if not MIN_VARIANCE_PERCENT <= result <= MAX_VARIANCE_PERCENT:
        raise ValueError('rng returned a variance outside 95-105')
    return result
