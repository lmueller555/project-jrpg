"""Persistent owner-bound bot loadouts, separate from party membership.

Starting capability registrations grant ownership. Merely adding another bot
to the catalog grants nothing, and each owner has one autonomous ability slot.
Bot timing and combat resources belong to each battle, never to this record.
"""
from copy import deepcopy
import json
from pathlib import Path

from character_abilities import (CATALOG_PATH as ABILITIES_PATH,
                                 CHARACTERS_PATH, _identifier,
                                 starting_abilities)
from character_attributes import ATTRIBUTE_CAPS, ATTRIBUTE_IDS


CATALOG_PATH = Path(__file__).resolve().parent/'assets/combat/bots.json'
BOT_ATTRIBUTE_IDS = tuple(identifier for identifier in ATTRIBUTE_IDS
                          if identifier not in ('hp', 'mp'))


def load_bot_definitions(data=None):
    """Validate and copy the canonical, versioned bot catalog.

    The battle model adds action-rule validation to these shared definitions.
    Catalog entries describe possible bots, independently of actual ownership.
    """
    if data is None:data = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'bots'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['bots'], dict) or not data['bots']):
        raise ValueError('Invalid bot catalog')
    characters = json.loads(CHARACTERS_PATH.read_text(encoding='utf-8'))['characters']
    abilities = json.loads(ABILITIES_PATH.read_text(encoding='utf-8'))['abilities']
    for identifier, record in data['bots'].items():
        if (not _identifier(identifier) or not isinstance(record, dict)
                or set(record) != {'owner_id', 'name', 'attributes', 'ability_id', 'ability_ids'}
                or not isinstance(record['owner_id'], str) or record['owner_id'] not in characters
                or not isinstance(record['name'], str) or not record['name'].strip()
                or not isinstance(record['attributes'], dict)
                or set(record['attributes']) != set(BOT_ATTRIBUTE_IDS)
                or any(type(value) is not int or not 0 <= value <= ATTRIBUTE_CAPS[key]
                       for key, value in record['attributes'].items())
                or not isinstance(record['ability_ids'], list) or not record['ability_ids']
                or any(not _identifier(ability_id)
                       or abilities.get(ability_id, {}).get('kind') != 'technique'
                       for ability_id in record['ability_ids'])
                or len(set(record['ability_ids'])) != len(record['ability_ids'])
                or not isinstance(record['ability_id'], str)
                or record['ability_id'] not in record['ability_ids']):
            raise ValueError('Invalid bot definition')
    return deepcopy(data['bots'])


def _definitions(definitions):
    if definitions is None:return load_bot_definitions()
    # Callers may reuse the plain definitions returned by the shared loader.
    if isinstance(definitions, dict) and set(definitions) == {'version', 'bots'}:
        return load_bot_definitions(definitions)
    return load_bot_definitions({'version': 1, 'bots': definitions})


def _starting_loadouts(definitions):
    loadouts = {}
    for bot_id, record in definitions.items():
        owner_id = record['owner_id']
        if bot_id not in starting_abilities(owner_id):continue
        if owner_id in loadouts:
            raise ValueError('Starting bot registrations exceed one owner slot')
        loadouts[owner_id] = {'bot_id': bot_id, 'ability_id': record['ability_id']}
    return loadouts


def starting_battle_loadouts(definitions=None):
    """Return owned starting bots using the character unlock registry."""
    return _starting_loadouts(_definitions(definitions))


class BotLoadouts:
    """Save one equipped bot and autonomous ability for each starting owner."""

    def __init__(self, definitions=None):
        self.definitions = _definitions(definitions)
        self._starting = _starting_loadouts(self.definitions)
        self._owned = {owner_id: frozenset(
            bot_id for bot_id, record in self.definitions.items()
            if record['owner_id'] == owner_id and bot_id in starting_abilities(owner_id))
            for owner_id in self._starting}
        self.reset()

    def reset(self):
        """Restore canonical starting loadouts without recruiting any owner."""
        self._loadouts = deepcopy(self._starting)

    def battle_loadouts(self):
        """Return independent battle input; transient combat state is excluded."""
        return deepcopy(self._loadouts)

    def owned_bots(self, owner_id):
        """Return the bot IDs actually granted to this owner."""
        return self._owned.get(owner_id, frozenset()) if isinstance(owner_id, str) else frozenset()

    def to_dict(self):
        return {'version': 1, 'loadouts': self.battle_loadouts()}

    def restore(self, data):
        """Restore a complete loadout atomically, rejecting explicit null data."""
        if (not isinstance(data, dict) or set(data) != {'version', 'loadouts'}
                or type(data['version']) is not int or data['version'] != 1
                or not isinstance(data['loadouts'], dict)
                or set(data['loadouts']) != set(self._owned)):
            return False
        for owner_id, record in data['loadouts'].items():
            if (not isinstance(record, dict) or set(record) != {'bot_id', 'ability_id'}
                    or not isinstance(record['bot_id'], str)
                    or record['bot_id'] not in self._owned[owner_id]):
                return False
            definition = self.definitions[record['bot_id']]
            if (definition['owner_id'] != owner_id or not isinstance(record['ability_id'], str)
                    or record['ability_id'] not in definition['ability_ids']):
                return False
        self._loadouts = deepcopy(data['loadouts'])
        return True

    @classmethod
    def valid_journey(cls, data):
        """Accept a missing legacy key and validate any explicit saved block."""
        if not isinstance(data, dict):return False
        return 'bot_loadouts' not in data or cls().restore(data['bot_loadouts'])
