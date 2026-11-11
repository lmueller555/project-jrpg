"""Durable Mira arm-rig allocation and bounded retired-loadout import.

Only the applied allocation is saved. Draft UI edits, barriers, animation and
live combat state belong to their own transient controllers. The starting rig
does not recruit Mira, change stats or grant earned progression.
"""
from copy import deepcopy

from mira_rig_rules import DEFAULT_ALLOCATION, valid_allocation


class MiraRigState:
    def __init__(self):
        self._allocation = dict(DEFAULT_ALLOCATION)

    @property
    def allocation(self):
        return dict(self._allocation)

    def set_allocation(self, allocation):
        if not valid_allocation(allocation):return False
        self._allocation = dict(allocation)
        return True

    def to_dict(self):
        return {'version': 1, 'allocation': self.allocation}

    def restore(self, data):
        """Accept an exact modern record atomically; explicit null is invalid."""
        if (not isinstance(data, dict) or set(data) != {'version', 'allocation'}
                or type(data['version']) is not int or data['version'] != 1):
            return False
        return self.set_allocation(data['allocation'])

    @classmethod
    def valid_journey(cls, data):
        return (isinstance(data, dict)
                and ('mira_rig' not in data or cls().restore(data['mira_rig'])))


def _retired_loadout(data):
    """Recognize only the two historical wire records, without live bot data."""
    if (not isinstance(data, dict) or set(data) != {'version', 'loadouts'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['loadouts'], dict)):
        return False
    loadouts = data['loadouts']
    return (not loadouts or loadouts == {
        'mira': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}})


def migrate_mira_rig(data):
    """Normalize a copied journey before modern validation; never write disk.

    Retired starting registrations were not learned-history records, so no
    character ability IDs are removed here. Exact old bot loadouts can be
    dropped safely without touching pending rewards, inventory or resources.
    """
    if not isinstance(data, dict):raise ValueError('Invalid saved journey')
    if 'bot_loadouts' in data and not _retired_loadout(data['bot_loadouts']):
        raise ValueError('Invalid retired bot loadout')
    result = deepcopy(data)
    result.pop('bot_loadouts', None)
    if 'mira_rig' not in result:result['mira_rig'] = MiraRigState().to_dict()
    return result
