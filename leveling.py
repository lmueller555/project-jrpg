"""Approved level/XP curves and independent character progression records.

This foundation deliberately owns neither battle-reward distribution nor current
HP/MP. Callers decide eligibility and resource recovery before integrating these
records with a journey. Retired progression currencies are not interpreted as XP.
"""
from bisect import bisect_right
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from character_attributes import ATTRIBUTE_CAPS, ATTRIBUTE_IDS


MIN_LEVEL = 1
MAX_LEVEL = 100
CATALOG_PATH = Path(__file__).resolve().parent/'assets/characters/level_growth.json'
_CHARACTER_IDS = ('caelan', 'mira', 'lucan', 'rhea', 'edran')
_EXPONENTS = {'resources': 1.2, 'ratings': 1.15, 'speed': 1}
_XP_RULES = {'required_scale': 100, 'required_exponent': 0.8,
             'monster_scale': 30, 'monster_exponent': 0.5,
             'multiplier': 2, 'boss_multiplier': 10, 'reward_percent': 70}
_NATURAL_CAPS = {key: 9999 if key == 'hp' else 999 if key == 'mp'
                 else 255 if key == 'speed' else 300 for key in ATTRIBUTE_IDS}


def _integer(value, name, minimum=0, maximum=None):
    if type(value) is not int:
        raise TypeError(name+' must be an integer')
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(name+' is outside its supported range')
    return value


def _level(value):
    return _integer(value, 'level', MIN_LEVEL, MAX_LEVEL)


def _round_half_up(value):
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _validate_catalog(data):
    if (not isinstance(data, dict)
            or set(data) != {'version', 'level_cap', 'exponents', 'xp', 'characters'}
            or type(data['version']) is not int or data['version'] != 1
            or type(data['level_cap']) is not int or data['level_cap'] != MAX_LEVEL):
        raise ValueError('Invalid level growth catalog')
    for field, expected in (('exponents', _EXPONENTS), ('xp', _XP_RULES)):
        record = data[field]
        if (not isinstance(record, dict) or set(record) != set(expected)
                or any(type(record[key]) is not type(value)
                       or record[key] != value or not math.isfinite(record[key])
                       for key, value in expected.items())):
            raise ValueError('Invalid approved '+field+' rules')
    characters = data['characters']
    if not isinstance(characters, dict) or tuple(characters) != _CHARACTER_IDS:
        raise ValueError('Invalid growth reference roster')
    for profile in characters.values():
        if (not isinstance(profile, dict)
                or set(profile) != {'name', 'start', 'target'}
                or not isinstance(profile['name'], str) or not profile['name'].strip()):
            raise ValueError('Invalid character growth profile')
        for endpoint in ('start', 'target'):
            stats = profile[endpoint]
            if (not isinstance(stats, dict) or set(stats) != set(ATTRIBUTE_IDS)
                    or any(type(stats[key]) is not int
                           or not (1 if key == 'hp' else 0) <= stats[key] <= _NATURAL_CAPS[key]
                           for key in ATTRIBUTE_IDS)):
                raise ValueError('Invalid natural '+endpoint+' stats')
        if any(profile['target'][key] < profile['start'][key] for key in ATTRIBUTE_IDS):
            raise ValueError('Natural growth cannot decrease')


def load_growth_catalog(path=CATALOG_PATH):
    """Read and validate authored data; return an independent catalog copy."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    _validate_catalog(data)
    return deepcopy(data)


_CATALOG = load_growth_catalog()


def character_ids():
    """Fixed reference roster; party membership never changes growth curves."""
    return _CHARACTER_IDS


def _profile(character_id):
    if not isinstance(character_id, str):
        raise TypeError('character_id must be a string')
    if character_id not in _CATALOG['characters']:
        raise ValueError('Unknown character growth profile')
    return _CATALOG['characters'][character_id]


def raw_character_stats(character_id, level):
    """Unrounded natural stats, used by the fixed enemy reference baseline."""
    profile = _profile(character_id)
    progress = (_level(level)-MIN_LEVEL)/(MAX_LEVEL-MIN_LEVEL)
    exponents = _CATALOG['exponents']
    return {key: profile['start'][key]+(profile['target'][key]-profile['start'][key])
            *progress**exponents['resources' if key in ('hp', 'mp') else
                                  'speed' if key == 'speed' else 'ratings']
            for key in ATTRIBUTE_IDS}


def character_stats(character_id, level):
    """Natural level stats, with half-up rounding and no equipment or buffs."""
    return {key: _round_half_up(value)
            for key, value in raw_character_stats(character_id, level).items()}


def xp_to_next_level(level):
    """Cost of advancing from this level; the level-100 cost is zero.

    Rounding precedes doubling, preserving the approved even-valued curve.
    """
    level = _level(level)
    if level == MAX_LEVEL:return 0
    rules = _CATALOG['xp']
    return rules['multiplier']*_round_half_up(
        rules['required_scale']*level**rules['required_exponent'])


def monster_xp(level, boss=False):
    """One monster's full reward, before level-cap overflow is considered."""
    level = _level(level)
    if type(boss) is not bool:
        raise TypeError('boss must be a boolean')
    rules = _CATALOG['xp']
    amount = rules['multiplier']*_round_half_up(
        rules['monster_scale']*level**rules['monster_exponent'])
    amount = (amount*rules['reward_percent']+50)//100
    return amount*(rules['boss_multiplier'] if boss else 1)


def combat_xp_allocations(amount, active_ids, current_hp):
    """Allocate the full encounter XP to each living active party member.

    IDs use canonical character names, including ``caelan`` rather than the
    battle model's ``player`` alias. The HP mapping may include reserves; only
    the ordered active formation receives entries, with zero for KO members.
    The caller supplies the end-of-battle HP snapshot and determines whether
    the encounter outcome awards XP. No character, resource or save is mutated.
    """
    _integer(amount, 'amount')
    if (not isinstance(active_ids, (list, tuple)) or not 1 <= len(active_ids) <= 3
            or any(not isinstance(identifier, str) or identifier not in _CHARACTER_IDS
                   for identifier in active_ids)
            or len(active_ids) != len(set(active_ids))):
        raise ValueError('Combat XP requires one to three distinct active characters')
    if not isinstance(current_hp, dict):
        raise TypeError('current_hp must map character IDs to current HP')
    if (any(not isinstance(identifier, str) or identifier not in _CHARACTER_IDS
            for identifier in current_hp)
            or any(identifier not in current_hp for identifier in active_ids)):
        raise ValueError('Combat XP requires valid HP for every active character')
    for hp in current_hp.values():
        _integer(hp, 'current_hp', maximum=ATTRIBUTE_CAPS['hp'])
    return {identifier: amount if current_hp[identifier] > 0 else 0
            for identifier in active_ids}


# Index zero is level one, which requires no accumulated XP.
_THRESHOLDS = (0,)
for _starting_level in range(MIN_LEVEL, MAX_LEVEL):
    _THRESHOLDS += (_THRESHOLDS[-1]+xp_to_next_level(_starting_level),)
MAX_TOTAL_XP = _THRESHOLDS[-1]


def total_xp_for_level(level):
    """Cumulative XP required to reach the requested level."""
    return _THRESHOLDS[_level(level)-1]


def level_for_total_xp(total_xp):
    """Derive a level without exceeding 100, including oversized input totals."""
    _integer(total_xp, 'total_xp')
    return min(MAX_LEVEL, bisect_right(_THRESHOLDS, total_xp))


@dataclass(frozen=True)
class XpAward:
    """One explicit XP mutation; current HP/MP are intentionally absent."""

    character_id: str
    requested_xp: int
    accepted_xp: int
    discarded_xp: int
    old_total_xp: int
    new_total_xp: int
    old_level: int
    new_level: int
    stat_gains: Mapping[str, int]

    @property
    def levels_gained(self):return self.new_level-self.old_level

    def to_dict(self):
        return {'character_id': self.character_id, 'requested_xp': self.requested_xp,
                'accepted_xp': self.accepted_xp, 'discarded_xp': self.discarded_xp,
                'old_total_xp': self.old_total_xp, 'new_total_xp': self.new_total_xp,
                'old_level': self.old_level, 'new_level': self.new_level,
                'stat_gains': dict(self.stat_gains)}


class CharacterLevel:
    """Standalone XP state, separate from party resources and legacy journeys.

    Stored XP stops at the level-100 threshold. Awards report any discarded
    excess so a future reward UI can show the actual accepted amount.
    """

    def __init__(self, character_id='caelan', total_xp=0):
        _profile(character_id)
        _integer(total_xp, 'total_xp', maximum=MAX_TOTAL_XP)
        self._character_id = character_id
        self._total_xp = total_xp

    @property
    def character_id(self):return self._character_id

    @property
    def total_xp(self):return self._total_xp

    @property
    def level(self):return level_for_total_xp(self._total_xp)

    @property
    def stats(self):return character_stats(self.character_id, self.level)

    @property
    def xp_into_level(self):return self.total_xp-total_xp_for_level(self.level)

    @property
    def xp_remaining(self):
        return 0 if self.level == MAX_LEVEL else xp_to_next_level(self.level)-self.xp_into_level

    def award_xp(self, amount):
        """Apply XP atomically, carrying excess through multiple level-ups."""
        _integer(amount, 'amount')
        old_total, old_level, old_stats = self.total_xp, self.level, self.stats
        accepted = min(amount, MAX_TOTAL_XP-old_total)
        new_total = old_total+accepted
        new_level = level_for_total_xp(new_total)
        new_stats = character_stats(self.character_id, new_level)
        receipt = XpAward(self.character_id, amount, accepted, amount-accepted,
                          old_total, new_total, old_level, new_level,
                          MappingProxyType({key: new_stats[key]-old_stats[key]
                                            for key in ATTRIBUTE_IDS}))
        self._total_xp = new_total
        return receipt

    def to_dict(self):
        return {'version': 1, 'character_id': self.character_id, 'total_xp': self.total_xp}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise TypeError('Level record must be a mapping')
        if (set(data) != {'version', 'character_id', 'total_xp'}
                or type(data['version']) is not int or data['version'] != 1):
            raise ValueError('Invalid level record')
        return cls(data['character_id'], data['total_xp'])
