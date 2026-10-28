"""Persistent character attributes, independent of combat and presentation.

HP and MP attributes are maxima; their current resource values are separate.
All other attributes are ratings, not percentages. This foundation supplies no
damage, healing, hit, evasion, critical-hit or turn-timing formulas.
"""
from copy import deepcopy
import json
from pathlib import Path


ATTRIBUTE_IDS = ('hp', 'mp', 'str', 'mag', 'spr', 'def', 'm_def',
                 'speed', 'acc', 'eva', 'lck')
# A bound on stored integers, not an approved combat or progression cap.
MAX_ATTRIBUTE_VALUE = 999999
SNAPSHOT_VERSION = 2
CATALOG_PATH = Path(__file__).parent/'assets/characters/attributes.json'


def _integer(value, minimum=0):
    return type(value) is int and minimum <= value <= MAX_ATTRIBUTE_VALUE


def _valid_attributes(values):
    return (isinstance(values, dict) and set(values) == set(ATTRIBUTE_IDS)
            and all(_integer(value, 1 if identifier == 'hp' else 0)
                    for identifier, value in values.items()))


class CharacterAttributes:
    """One character's independent ratings and current HP/MP resources."""

    def __init__(self, character_id='caelan', catalog=None):
        if catalog is None:
            catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        self.catalog = deepcopy(catalog)
        self._validate_catalog()
        if not isinstance(character_id, str) or character_id not in self.catalog['characters']:
            raise ValueError('Unknown character attribute profile')
        self.character_id = character_id
        self.definitions = self.catalog['attributes']
        profile = self.catalog['characters'][character_id]
        self.name = profile['name']
        self._starting = deepcopy(profile['attributes'])
        self.reset()

    def _validate_catalog(self):
        catalog = self.catalog
        if (not isinstance(catalog, dict)
                or set(catalog) != {'version', 'attributes', 'characters'}
                or type(catalog['version']) is not int or catalog['version'] != 1):
            raise ValueError('Invalid character attribute catalog')
        definitions = catalog['attributes']
        if not isinstance(definitions, dict) or set(definitions) != set(ATTRIBUTE_IDS):
            raise ValueError('Invalid attribute definitions')
        for record in definitions.values():
            if (not isinstance(record, dict)
                    or set(record) != {'label', 'name', 'description'}
                    or any(not isinstance(value, str) or not value.strip()
                           for value in record.values())):
                raise ValueError('Invalid attribute metadata')
        characters = catalog['characters']
        if not isinstance(characters, dict) or not characters:
            raise ValueError('Missing character attribute profiles')
        for identifier, record in characters.items():
            if (not isinstance(identifier, str) or not identifier.strip()
                    or not isinstance(record, dict)
                    or set(record) != {'name', 'attributes'}
                    or not isinstance(record['name'], str) or not record['name'].strip()
                    or not _valid_attributes(record['attributes'])):
                raise ValueError('Invalid character attribute profile')

    @property
    def current_hp(self):
        return self._current_hp

    @property
    def current_mp(self):
        return self._current_mp

    def value(self, identifier):
        """Return a rating, or maximum capacity for HP and MP."""
        return self._attributes[identifier]

    def reset(self):
        """Restore this character's starting profile with full resources."""
        self._attributes = deepcopy(self._starting)
        self._current_hp = self.value('hp')
        self._current_mp = self.value('mp')

    def set_current(self, hp=None, mp=None):
        """Set supplied resources atomically; reject invalid values unchanged."""
        hp = self._current_hp if hp is None else hp
        mp = self._current_mp if mp is None else mp
        if (not _integer(hp) or hp > self.value('hp')
                or not _integer(mp) or mp > self.value('mp')):
            return False
        self._current_hp, self._current_mp = hp, mp
        return True

    def to_dict(self):
        return {'version': SNAPSHOT_VERSION, 'character_id': self.character_id,
                'attributes': dict(self._attributes),
                'current_hp': self._current_hp, 'current_mp': self._current_mp}

    @classmethod
    def valid_snapshot(cls, data, character_id='caelan'):
        """Validate a complete record without constructing or mutating a model."""
        if (not isinstance(data, dict)
                or set(data) != {'version', 'character_id', 'attributes',
                                 'current_hp', 'current_mp'}
                or type(data['version']) is not int or data['version'] not in (1, SNAPSHOT_VERSION)
                or not isinstance(character_id, str) or not character_id
                or data['character_id'] != character_id
                or not _valid_attributes(data['attributes'])):
            return False
        return (all(_integer(data['current_'+resource])
                    and data['current_'+resource] <= data['attributes'][resource]
                    for resource in ('hp', 'mp')))

    def restore(self, data):
        """Restore a valid complete record; malformed records leave all state intact."""
        if not self.valid_snapshot(data, self.character_id):
            return False
        self._attributes = dict(data['attributes'])
        self._current_hp = data['current_hp']
        self._current_mp = data['current_mp']
        # Version one shipped Caelan with 300 starting HP before progression
        # existed. Retune that baseline once; retain other saved growth and MP.
        if data['version'] == 1 and self.character_id == 'caelan' and self.value('hp') == 300:
            maximum = self._starting['hp']
            scaled = (self._current_hp*maximum+150)//300
            self._attributes['hp'] = maximum
            self._current_hp = max(1, scaled) if self._current_hp else 0
        return True
