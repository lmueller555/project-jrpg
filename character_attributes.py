"""Persistent character attributes, independent of combat and presentation.

HP and MP attributes are maxima; their current resource values are separate.
Saved attributes are preserved base values. Effective values add named modifier
sources rebuilt from their canonical owners, such as activated lattice nodes,
then stop at each attribute's gameplay cap. Earned modifiers remain canonical.
All other attributes are ratings, not percentages. This supplies no combat
damage, healing, hit, evasion, critical-hit or turn-timing formulas.
"""
from copy import deepcopy
import json
from pathlib import Path


ATTRIBUTE_IDS = ('hp', 'mp', 'str', 'mag', 'spr', 'def', 'm_def',
                 'speed', 'acc', 'eva', 'lck')
# Storage bounds also validate raw growth; gameplay caps bound effective values.
MAX_ATTRIBUTE_VALUE = 999999
ATTRIBUTE_CAPS = {identifier: 9999 if identifier == 'hp' else
                  999 if identifier == 'mp' else 255
                  for identifier in ATTRIBUTE_IDS}
SNAPSHOT_VERSION = 3
CATALOG_PATH = Path(__file__).parent/'assets/characters/attributes.json'


def _integer(value, minimum=0):
    return type(value) is int and minimum <= value <= MAX_ATTRIBUTE_VALUE


def _valid_attributes(values, capped=True):
    return (isinstance(values, dict) and set(values) == set(ATTRIBUTE_IDS)
            and all(_integer(value, 1 if identifier == 'hp' else 0)
                    and (not capped or value <= ATTRIBUTE_CAPS[identifier])
                    for identifier, value in values.items()))


def _valid_bonuses(values):
    return (isinstance(values, dict) and set(values) <= set(ATTRIBUTE_IDS)
            and all(_integer(value) for value in values.values()))


def _attribute_totals(base, sources):
    return {identifier: base[identifier]+sum(values.get(identifier, 0)
                                           for values in sources.values())
            for identifier in ATTRIBUTE_IDS}


def _capped_values(totals):
    return {identifier: min(value, ATTRIBUTE_CAPS[identifier])
            for identifier, value in totals.items()}


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

    @staticmethod
    def cap(identifier):
        """Return the shared gameplay maximum for an attribute."""
        return ATTRIBUTE_CAPS[identifier]

    def value(self, identifier):
        """Return a capped effective rating, or maximum capacity for HP and MP."""
        total = self._attributes[identifier]+sum(values.get(identifier, 0)
                                                for values in self._modifiers.values())
        return min(total, self.cap(identifier))

    def base_value(self, identifier):
        """Return preserved growth before lattice or other named modifiers."""
        return self._attributes[identifier]

    def set_modifiers(self, source, bonuses):
        """Replace one source atomically without changing base or current resources.

        An empty mapping removes that source. Recomputing the same lattice
        bonuses therefore never stacks them. Raw earned growth is preserved
        when its effective value reaches a gameplay cap. A replacement that
        would leave a current resource above its new maximum is rejected.
        """
        if (not isinstance(source, str) or not source.strip() or len(source) > 64
                or not _valid_bonuses(bonuses)):
            return False
        sources = {name: dict(values) for name, values in self._modifiers.items()
                   if name != source}
        if bonuses:sources[source] = dict(bonuses)
        totals = _attribute_totals(self._attributes, sources)
        effective = _capped_values(totals)
        if (not _valid_attributes(totals, capped=False)
                or self.current_hp > effective['hp'] or self.current_mp > effective['mp']):
            return False
        self._modifiers = sources
        return True

    def reset(self):
        """Restore this character's starting profile with full resources."""
        self._attributes = deepcopy(self._starting)
        self._modifiers = {}
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
        # Bonuses are stored by their owner, not copied into the base record.
        return {'version': SNAPSHOT_VERSION, 'character_id': self.character_id,
                'attributes': dict(self._attributes),
                'current_hp': self._current_hp, 'current_mp': self._current_mp}

    @classmethod
    def valid_snapshot(cls, data, character_id='caelan', lattice_bonuses=None):
        """Validate base and current resources against externally derived bonuses.

        Versions one and two contain pre-lattice aggregate growth. Their values
        become the preserved base, so supplying nonzero lattice growth for an
        older record is rejected instead of counting its growth twice.
        """
        if (not isinstance(data, dict)
                or set(data) != {'version', 'character_id', 'attributes',
                                 'current_hp', 'current_mp'}
                or type(data['version']) is not int or data['version'] not in (1, 2, SNAPSHOT_VERSION)
                or not isinstance(character_id, str) or not character_id
                or data['character_id'] != character_id
                or not _valid_attributes(data['attributes'])):
            return False
        bonuses = {} if lattice_bonuses is None else lattice_bonuses
        if not _valid_bonuses(bonuses):return False
        if data['version'] < SNAPSHOT_VERSION and any(bonuses.values()):return False
        totals = _attribute_totals(data['attributes'], {'lattice': bonuses})
        if not _valid_attributes(totals, capped=False):return False
        effective = _capped_values(totals)
        return (all(_integer(data['current_'+resource])
                    and data['current_'+resource] <= effective[resource]
                    for resource in ('hp', 'mp')))

    def restore(self, data, lattice_bonuses=None):
        """Restore a valid complete record; malformed records leave all state intact."""
        if not self.valid_snapshot(data, self.character_id, lattice_bonuses):
            return False
        attributes = dict(data['attributes'])
        current_hp = data['current_hp']
        # Version one shipped Caelan with 300 starting HP before progression
        # existed. Retune that baseline once; retain other saved growth and MP.
        if data['version'] == 1 and self.character_id == 'caelan' and attributes['hp'] == 300:
            maximum = self._starting['hp']
            scaled = (current_hp*maximum+150)//300
            attributes['hp'] = maximum
            current_hp = max(1, scaled) if current_hp else 0
        bonuses = {} if lattice_bonuses is None else dict(lattice_bonuses)
        self._attributes = attributes
        self._current_hp = current_hp
        self._current_mp = data['current_mp']
        self._modifiers = {'lattice': bonuses} if bonuses else {}
        return True
