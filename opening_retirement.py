"""Copy-only compatibility for journeys from the retired opening storyline.

Ordinary household/mill and independent cave rewards remain earned. Only the
removed scene owners, quest records and their temporary party obligation are
retired. A battle/reward transaction cannot be moved out of its saved scene.
"""
from __future__ import annotations

from copy import deepcopy


STORY_REVISION = 2
RETIRED_QUESTS = frozenset(('CH01_MQ03', 'CH01_MQ04'))
RETIRED_OWNERS = ('regent_arrival', 'regent_quest', 'sanctuary_arrival',
                  'sanctuary_rescue', 'lantern_quest')
RETIRED_FLAGS = frozenset(('CH01_MQ03_COMPLETE', 'CH01_MQ04_COMPLETE'))
RETIRED_PARTY_EVENT = 'mq03_sanctuary'
SAFE_HOME = {'scene': 'sanctuary_dining', 'position': [288, 238], 'facing': 'front'}


class OpeningCompatibilityError(ValueError):
    """A legacy checkpoint needs a settled save rather than guessed progress."""


def _quests(data):
    quests = data.get('quests')
    return quests.get('quests', {}) if isinstance(quests, dict) else {}


def _affected(data):
    quests = _quests(data)
    if isinstance(quests, dict):
        mill = quests.get('CH01_MQ02')
        if isinstance(mill, dict) and mill.get('status') == 'completed':return True
        for identifier in RETIRED_QUESTS:
            record = quests.get(identifier)
            if isinstance(record, dict) and record.get('status') in ('active', 'ready', 'completed'):
                return True
    for owner, initial in (('regent_quest', 'idle'), ('lantern_quest', 'idle'),
                           ('sanctuary_rescue', 'undiscovered')):
        record = data.get(owner)
        if isinstance(record, dict) and record.get('stage', initial) != initial:return True
    arrival = data.get('regent_arrival')
    if isinstance(arrival, dict) and arrival.get('state') in ('pending', 'seen'):return True
    arrival = data.get('sanctuary_arrival')
    if isinstance(arrival, dict) and (arrival.get('completed') or arrival.get('beat', 0)):
        return True
    party = data.get('party')
    event = party.get('event') if isinstance(party, dict) else None
    return isinstance(event, dict) and event.get('id') == RETIRED_PARTY_EVENT


def _pending_transaction(data):
    if data.get('post_battle') is not None:return True
    for owner in ('sanctuary_boss', 'elemental_bosses', 'cave_random_encounters'):
        record = data.get(owner)
        if isinstance(record, dict) and record.get('pending') is not None:return True
    elemental = data.get('elemental_bosses')
    bosses = elemental.get('bosses') if isinstance(elemental, dict) else None
    return isinstance(bosses, dict) and any(
        isinstance(record, dict) and record.get('pending_acquisition')
        for record in bosses.values())


def _retire_party(data):
    party = data.get('party')
    if not isinstance(party, dict):return
    members, active = party.get('members'), party.get('active')
    if not isinstance(members, dict) or not isinstance(active, list):return
    event = party.get('event')
    retired_event = isinstance(event, dict) and event.get('id') == RETIRED_PARTY_EVENT
    if retired_event:
        # End only the retired named obligation; the character snapshots and
        # every earned level/resource stay in the persistent party owner.
        party['event'] = None
    unrelated_event = isinstance(event, dict) and event.get('id') not in (RETIRED_PARTY_EVENT, 'mq02')
    if not unrelated_event:
        returned = {'lucan': 'The previous temporary outing has ended.'}
        mill = _quests(data).get('CH01_MQ02')
        if isinstance(mill, dict) and mill.get('status') == 'completed':
            returned['mira'] = 'Working in Eldenmere.'
        for identifier, reason in returned.items():
            record = members.get(identifier)
            if isinstance(record, dict) and record.get('temporary') is True:
                record['available'] = False
                record['reason'] = reason
                active = [key for key in active if key != identifier]
        party['active'] = active


def migrate_retired_opening(data):
    """Normalize a legacy journey without changing it or writing its save file.

    Revision-two checkpoints are already in the neutral exploration timeline.
    Completed legacy MQ02 or actual retired scene progress returns to the safe
    household; early MQ01/MQ02 keeps its saved feet and exact retained progress.
    """
    result = deepcopy(data)
    if not isinstance(result, dict):return result
    revision = result.get('story_revision', 1)
    if type(revision) is not int or revision not in (1, STORY_REVISION):
        raise OpeningCompatibilityError('This saved journey uses an unsupported story revision.')
    if revision == STORY_REVISION:return result
    affected = _affected(result)
    if affected and _pending_transaction(result):
        raise OpeningCompatibilityError(
            'This older save is inside a battle or unfinished reward transaction from the retired '
            'opening. Load a settled exploration save; its rewards cannot be safely migrated.')

    if affected:
        player = result.get('player')
        if isinstance(player, dict):player.update(deepcopy(SAFE_HOME))
        _retire_party(result)

    quests = _quests(result)
    if isinstance(quests, dict):
        for identifier in RETIRED_QUESTS:quests.pop(identifier, None)
    for owner in RETIRED_OWNERS:result.pop(owner, None)
    flags = result.get('dialogue_flags')
    if isinstance(flags, list):
        result['dialogue_flags'] = [flag for flag in flags if flag not in RETIRED_FLAGS]
    inventory = result.get('inventory')
    if isinstance(inventory, dict):
        # Shipped MQ03/MQ04 have no exclusive inventory items: their lanterns,
        # papers and tools belonged to the removed scene owners, not this ledger.
        # Keep all consumables, equipment, focus gems and delivery receipts.
        grants = inventory.get('granted_quests')
        if isinstance(grants, list):
            inventory['granted_quests'] = [identifier for identifier in grants if identifier not in RETIRED_QUESTS]
        deliveries = inventory.get('deliveries')
        if isinstance(deliveries, list):
            inventory['deliveries'] = [identifier for identifier in deliveries
                if not isinstance(identifier, str) or identifier.split('/', 1)[0] not in RETIRED_QUESTS]
    cave = result.get('sanctuary_cave')
    if isinstance(cave, dict):
        cave.pop('lucan_guest_initialized', None)
        cave.pop('lucan_departed', None)
    result['story_revision'] = STORY_REVISION
    return result
