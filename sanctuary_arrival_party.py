"""Temporary three-person rescue formation acknowledged at Sanctuary arrival.

This helper reconciles only the named MQ03 event. The cinematic owns saving
and rollback of its completion checkpoint. A one-time cave receipt installs
Lucan's authored guest profile without resetting it on ordinary reconciliation.
"""
from __future__ import annotations

from lucan_guest import initialize_lucan_guest


EVENT_ID = 'mq03_sanctuary'
REQUIRED = ('caelan', 'mira', 'lucan')
from regent_resolution import STAGES as RESOLUTION_STAGES
TRIP_STAGES = frozenset(('sanctuary_travel', 'sanctuary_arrival_pending', *(s for s in RESOLUTION_STAGES if s!='resolution_family')))
REASON = 'Caelan, Mira and Lucan are needed for the Sanctuary rescue.'


def sync_arrival_party(game):
    """Return ``None`` for ordinary reconciliation, or a handled success/failure.

    Before the arrival is acknowledged, existing two-person MQ03 and legacy
    journeys retain their rules. After it, the third member and requirements
    are applied atomically. Repeated synchronization preserves formation order
    and resources. Ending this named outing returns a temporary Lucan to Aldric;
    a later permanent Lucan or another event is never removed by this helper.
    """
    arrival = getattr(game, 'sanctuary_arrival', None)
    if not getattr(arrival, 'completed', False):return None
    party = game.party
    departed = bool(getattr(getattr(game, 'sanctuary_cave', None), 'lucan_departed', False))
    required = ('caelan', 'mira') if departed else REQUIRED
    stage = getattr(getattr(game, 'regent_quest', None), 'stage', None)
    if stage not in TRIP_STAGES:
        if party.current_event_id == EVENT_ID:
            before = party.to_dict()
            if not party.end_event(EVENT_ID):return False
            lucan = party.members.get('lucan')
            if lucan is not None and lucan['temporary']:
                if not party.set_available('lucan', False, 'Returned to Aldric.'):
                    party.restore(before)
                    return False
        return None
    if party.current_event_id not in (None, 'mq02', EVENT_ID):return False
    if 'mira' not in party.members:return False

    # A correctly applied event already owns the active trio. Do not reorder
    # the player's supported formation or reset any persistent character owner.
    if (party.current_event_id == EVENT_ID
            and set(required) == set(party.required_ids)
            and all(key in party.active_ids and party.is_available(key) for key in required)
            and (not departed or not party.is_guest('lucan')
                 or not party.is_available('lucan'))):
        initialize_lucan_guest(game)
        return True

    before = party.to_dict()
    previous_event = before['event']
    if party.current_event_id in ('mq02', EVENT_ID):
        if not party.end_event(party.current_event_id):return False
    new_guest = not departed and 'lucan' not in party.members
    if new_guest and not party.recruit('lucan', temporary=True):
        party.restore(before)
        return False
    if (not party.set_available('mira', True)
            or not departed and not party.set_available('lucan', True)
            or not party.begin_event(EVENT_ID, required=required,
                reason='Caelan and Mira are needed at the Sanctuary.' if departed else REASON)):
        party.restore(before)
        return False
    if departed and party.is_guest('lucan'):
        if not party.set_available('lucan', False, 'Returned to Aldric after the cave rescue.'):
            party.restore(before)
            return False
    if previous_event is not None:
        # Keep the formation from before the original outing, rather than
        # treating its enforced Caelan/Mira pair as the player's old choice.
        proposed = party.to_dict()
        proposed['event']['previous'] = list(previous_event['previous'])
        if not party.restore(proposed):
            party.restore(before)
            return False
    initialize_lucan_guest(game, new=new_guest)
    return True


def valid_arrival_party(data, party):
    """Validate the arrival's extra requirement after generic party validation."""
    if not isinstance(data, dict):return False
    arrival = data.get('sanctuary_arrival')
    if not isinstance(arrival, dict) or arrival.get('completed') is not True:return True
    record = data.get('regent_quest')
    stage = record.get('stage') if isinstance(record, dict) else None
    if stage not in TRIP_STAGES:return True
    cave = data.get('sanctuary_cave', {})
    if not isinstance(cave, dict):return False
    departed = cave.get('lucan_departed', False)
    if departed:
        boss = data.get('sanctuary_boss', {})
        return (isinstance(boss, dict) and boss.get('defeated') is True
                and party.current_event_id == EVENT_ID
                and {'caelan', 'mira'} <= set(party.required_ids)
                and {'caelan', 'mira'} <= set(party.active_ids)
                and all(party.is_available(key) for key in ('caelan', 'mira'))
                and (not party.is_guest('lucan') or not party.is_available('lucan')))
    return (party.current_event_id == EVENT_ID
            and set(REQUIRED) <= set(party.required_ids)
            and set(party.active_ids) == set(REQUIRED)
            and all(party.is_available(key) for key in REQUIRED))
