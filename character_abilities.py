"""Registered character abilities and permanent first-weapon unlock history.

The shared catalog describes abilities; character dictionaries decide who can
learn them and how. Explicit learned history belongs to this owner. Equipment
references inventory ownership without consuming the equipped item, and does
not recruit a character or grant any starting equipment.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from gear_state import DEFAULT_GEM, valid_gem
from inventory import Inventory


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT/'assets/abilities/catalog.json'
CHARACTERS_PATH = ROOT/'assets/abilities/characters.json'
_IDENTIFIER = re.compile(r'^[a-zA-Z0-9_.:/-]{1,128}$')
_GROUP_KINDS = {'skills': 'technique', 'spells': 'spell', 'abilities': 'capability'}
_UNLOCKS = ('starting', 'first_weapon', 'learned')


def _identifier(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def starting_abilities(character_id, characters=None):
    """Read a character's starting registrations without creating game state.

    Bot ownership and direct battle construction use the same authored unlocks
    as the persistent character ability owner.
    """
    if characters is None:
        characters = json.loads(CHARACTERS_PATH.read_text(encoding='utf-8'))
    if (not isinstance(characters, dict) or set(characters) != {'version', 'characters'}
            or type(characters['version']) is not int or characters['version'] != 1
            or not isinstance(characters['characters'], dict)):
        raise ValueError('Invalid character ability catalog')
    if not isinstance(character_id, str):return frozenset()
    profile = characters['characters'].get(character_id)
    if profile is None:return frozenset()
    if (not isinstance(profile, dict)
            or any(not isinstance(profile.get(group), dict) for group in _GROUP_KINDS)):
        raise ValueError('Invalid character ability profile')
    known = set()
    for group in _GROUP_KINDS:
        for identifier, record in profile[group].items():
            if (not _identifier(identifier) or not isinstance(record, dict)
                    or set(record) != {'unlock'} or record['unlock'] not in _UNLOCKS):
                raise ValueError('Invalid character ability unlock')
            if record['unlock'] == 'starting':known.add(identifier)
    return frozenset(known)


class CharacterAbilities:
    """Independent character unlock history backed by shared item ownership."""

    def __init__(self, inventory, catalog=None, characters=None):
        if not isinstance(inventory, Inventory):
            raise ValueError('Character abilities require an inventory owner')
        if catalog is None:catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        if characters is None:characters = json.loads(CHARACTERS_PATH.read_text(encoding='utf-8'))
        self.catalog = deepcopy(catalog)
        self.character_catalog = deepcopy(characters)
        self._validate_catalogs()
        self.inventory = inventory
        self.definitions = self.catalog['abilities']
        self.characters = self.character_catalog['characters']
        self.character_ids = tuple(self.characters)
        self.reset()

    def _validate_catalogs(self):
        catalog = self.catalog
        if (not isinstance(catalog, dict) or set(catalog) != {'version', 'abilities'}
                or type(catalog['version']) is not int or catalog['version'] != 1
                or not isinstance(catalog['abilities'], dict) or not catalog['abilities']):
            raise ValueError('Invalid ability catalog')
        for identifier, record in catalog['abilities'].items():
            if (not _identifier(identifier) or not isinstance(record, dict)
                    or set(record) != {'name', 'description', 'kind'}
                    or record['kind'] not in tuple(_GROUP_KINDS.values())
                    or any(not isinstance(record[key], str) or not record[key].strip()
                           for key in ('name', 'description'))):
                raise ValueError('Invalid ability definition')
        characters = self.character_catalog
        if (not isinstance(characters, dict) or set(characters) != {'version', 'characters'}
                or type(characters['version']) is not int or characters['version'] != 1
                or not isinstance(characters['characters'], dict) or not characters['characters']):
            raise ValueError('Invalid character ability catalog')
        for identifier, record in characters['characters'].items():
            if (not _identifier(identifier) or not isinstance(record, dict)
                    or set(record) != {'name', 'job', *_GROUP_KINDS}
                    or any(not isinstance(record[key], str) or not record[key].strip()
                           for key in ('name', 'job'))):
                raise ValueError('Invalid character ability profile')
            for group, kind in _GROUP_KINDS.items():
                if not isinstance(record[group], dict):
                    raise ValueError('Character abilities must be dictionaries')
                for ability_id, unlock in record[group].items():
                    if (not _identifier(ability_id) or ability_id not in catalog['abilities']
                            or catalog['abilities'][ability_id]['kind'] != kind
                            or not isinstance(unlock, dict) or set(unlock) != {'unlock'}
                            or unlock['unlock'] not in _UNLOCKS):
                        raise ValueError('Invalid character ability unlock')

    def reset(self):
        """Clear equipment and unlock history without changing inventory."""
        self._characters = {identifier: {'equipped_weapon': None,
                                        'first_weapon_acquired': False}
                            for identifier in self.characters}
        self._deferred_weapon_training = set()
        self._learned_abilities = {}
        self._gear_focus = ({'caelan': DEFAULT_GEM}
                            if 'caelan' in self.characters else {})

    def _known_character(self, character_id):
        return isinstance(character_id, str) and character_id in self.characters

    def active_gem(self, character_id='caelan'):
        """Return the settled gearblade focus, independent of learned skills."""
        if not isinstance(character_id, str):return None
        return self._gear_focus.get(character_id)

    def set_active_gem(self, gem, character_id='caelan'):
        """Keep a valid settled focus without granting elemental knowledge."""
        if (not isinstance(character_id, str) or character_id not in self._gear_focus
                or not valid_gem(gem)):
            return False
        self._gear_focus[character_id] = gem
        return True

    def known_abilities(self, character_id='caelan'):
        """Derive known IDs from registration and permanent learned history."""
        if not self._known_character(character_id):return frozenset()
        learned = self._learned_abilities.get(character_id, set())
        first_weapon = (self._characters[character_id]['first_weapon_acquired']
                        and character_id not in self._deferred_weapon_training)
        known = set()
        for group in _GROUP_KINDS:
            for identifier, record in self.characters[character_id][group].items():
                unlock = record['unlock']
                if (unlock == 'starting' or unlock == 'first_weapon' and first_weapon
                        or unlock == 'learned' and identifier in learned):
                    known.add(identifier)
        return frozenset(known)

    def _learnable(self, character_id, ability_id):
        return (self._known_character(character_id) and isinstance(ability_id, str)
                and any(self.characters[character_id][group].get(ability_id, {}).get('unlock')
                        == 'learned' for group in _GROUP_KINDS))

    def learn_ability(self, character_id, ability_id):
        """Record an explicitly granted, registered ability once.

        Story or future progression code owns acquisition conditions. Registering
        an ability does not grant it, spend inventory, or supply free equipment.
        """
        if not self._learnable(character_id, ability_id):return False
        known = self._learned_abilities.setdefault(character_id, set())
        if ability_id in known:return False
        known.add(ability_id)
        return True

    def skill_ids(self, character_id='caelan'):
        """Return known techniques in the shared catalog's authored order."""
        known = self.known_abilities(character_id)
        return tuple(identifier for identifier, record in self.definitions.items()
                     if record['kind'] == 'technique' and identifier in known)

    def _weapon(self, item_id):
        return (isinstance(item_id, str)
                and self.inventory.definitions.get(item_id, {}).get('category') == 'weapons')

    def _owned_weapon(self, item_id):
        return self._weapon(item_id) and self.inventory.quantity(item_id) > 0

    def reconcile_equipment(self):
        """Reserve one owned copy per wielder, preserving permanent knowledge.

        When quantity shrinks, characters keep their copies in catalog order.
        Later owners become unarmed until another copy is explicitly equipped.
        """
        changed = False
        reserved = {}
        for identifier in self.character_ids:
            record = self._characters[identifier]
            weapon = record['equipped_weapon']
            if weapon is None:continue
            if not self._owned_weapon(weapon) or reserved.get(weapon, 0) >= self.inventory.quantity(weapon):
                record['equipped_weapon'] = None
                changed = True
            else:reserved[weapon] = reserved.get(weapon, 0)+1
        return changed

    def has_weapon(self, character_id='caelan'):
        """Check equipment against current ownership, including removal since equip."""
        self.reconcile_equipment()
        return (self._known_character(character_id)
                and self._owned_weapon(self._characters[character_id]['equipped_weapon']))

    def _available_weapon(self, character_id, item_id, additional_copies=0):
        if not self._known_character(character_id) or not self._weapon(item_id):return False
        self.reconcile_equipment()
        reserved = sum(owner != character_id and record['equipped_weapon'] == item_id
                       for owner, record in self._characters.items())
        return reserved < self.inventory.quantity(item_id)+additional_copies

    def acquire_weapon(self, character_id, item_id, *, learn_starter=True):
        """Add and equip a catalogued weapon, granting first-weapon unlocks once.

        Validate character, category and a free copy after the addition before
        touching inventory. After its atomic add succeeds, committing the
        prepared state cannot reject or partially grant unlock history.
        A story gift can defer its starter technique until an authored lesson
        succeeds. That deferral never removes a skill already earned.
        """
        if type(learn_starter) is not bool:return False
        if not self._available_weapon(character_id, item_id, additional_copies=1):return False
        if not self.inventory.add(item_id):return False
        learned = (self._characters[character_id]['first_weapon_acquired']
                   and character_id not in self._deferred_weapon_training)
        self._characters[character_id] = {'equipped_weapon': item_id,
                                          'first_weapon_acquired': True}
        if not learn_starter and not learned:
            self._deferred_weapon_training.add(character_id)
        elif learn_starter:
            self._deferred_weapon_training.discard(character_id)
        return True

    def starter_skills_pending(self, character_id='caelan'):
        """Whether this character still needs their first-weapon lesson."""
        return self._known_character(character_id) and character_id in self._deferred_weapon_training

    def learn_first_weapon_skills(self, character_id='caelan'):
        """Commit a successful weapon lesson once, retaining earned knowledge.

        Discovery needs the owned, equipped weapon used in the lesson. Repeated
        settlement calls are harmless; unequipping later keeps the technique.
        """
        if not self.has_weapon(character_id):return False
        if not self._characters[character_id]['first_weapon_acquired']:return False
        self._deferred_weapon_training.discard(character_id)
        return True

    def equip_weapon(self, character_id, item_id):
        """Equip one owned weapon or unequip, retaining permanent unlock history."""
        if not self._known_character(character_id):return False
        if item_id is None:
            self._characters[character_id]['equipped_weapon'] = None
            return True
        if (not self._available_weapon(character_id, item_id)
                or not self._owned_weapon(item_id)):
            return False
        self._characters[character_id] = {'equipped_weapon': item_id,
                                          'first_weapon_acquired': True}
        return True

    def to_dict(self):
        """Save history and only equipment whose inventory ownership is intact."""
        self.reconcile_equipment()
        result = {'version': 1, 'characters': {
            identifier: {'equipped_weapon': record['equipped_weapon'],
                         'first_weapon_acquired': record['first_weapon_acquired']}
            for identifier, record in sorted(self._characters.items())}}
        # Omit the extension when no lesson is pending. Existing version-one
        # journeys retain their exact representation and already-earned skills.
        if self._deferred_weapon_training:
            result['deferred_weapon_training'] = sorted(self._deferred_weapon_training)
        focus = {identifier: gem for identifier, gem in sorted(self._gear_focus.items())
                 if gem != DEFAULT_GEM}
        if focus:result['gear_focus'] = focus
        if self._learned_abilities:
            result['learned_abilities'] = {
                identifier: sorted(abilities)
                for identifier, abilities in sorted(self._learned_abilities.items())}
        return result

    def restore(self, data):
        """Restore a complete record atomically; missing legacy data starts unarmed."""
        if data is None:
            self.reset()
            return True
        if (not isinstance(data, dict)
                or not {'version', 'characters'} <= set(data)
                or set(data) - {'version', 'characters', 'deferred_weapon_training', 'gear_focus',
                               'learned_abilities'}
                or type(data['version']) is not int or data['version'] != 1
                or not isinstance(data['characters'], dict)
                or set(data['characters']) != set(self.characters)):
            return False
        equipped = {}
        for record in data['characters'].values():
            if (not isinstance(record, dict)
                    or set(record) != {'equipped_weapon', 'first_weapon_acquired'}
                    or type(record['first_weapon_acquired']) is not bool):
                return False
            weapon = record['equipped_weapon']
            if weapon is not None:
                if (not self._owned_weapon(weapon)
                        or not record['first_weapon_acquired']):
                    return False
                equipped[weapon] = equipped.get(weapon, 0)+1
                if equipped[weapon] > self.inventory.quantity(weapon):return False
        deferred = data.get('deferred_weapon_training', [])
        if (not isinstance(deferred, list)
                or any(not self._known_character(identifier) for identifier in deferred)
                or len(deferred) != len(set(deferred))
                or any(not data['characters'][identifier]['first_weapon_acquired']
                       for identifier in deferred)):
            return False
        focus = data.get('gear_focus', {})
        if (not isinstance(focus, dict)
                or any(identifier != 'caelan' or identifier not in self.characters
                       or not valid_gem(gem) for identifier, gem in focus.items())):
            return False
        learned = data.get('learned_abilities', {})
        if (not isinstance(learned, dict)
                or any(not self._known_character(identifier)
                       or not isinstance(abilities, list) or not abilities
                       or any(not self._learnable(identifier, ability) for ability in abilities)
                       or len(abilities) != len(set(abilities))
                       for identifier, abilities in learned.items())):
            return False
        self._characters = deepcopy(data['characters'])
        self._deferred_weapon_training = set(deferred)
        self._gear_focus = ({'caelan': focus.get('caelan', DEFAULT_GEM)}
                            if 'caelan' in self.characters else {})
        self._learned_abilities = {identifier: set(abilities)
                                   for identifier, abilities in learned.items()}
        return True

    @classmethod
    def valid_journey(cls, data):
        """Check saved equipment against saved ownership without mutating a journey."""
        if not isinstance(data, dict):return False
        if 'character_abilities' in data and data['character_abilities'] is None:return False
        inventory = Inventory()
        if 'inventory' in data and not inventory.restore(data['inventory']):return False
        return cls(inventory).restore(data.get('character_abilities'))
