"""Persistent recruited characters, available companions and active formation.

Membership and resources outlive individual battles. A named story event can
overlay availability and formation requirements without rewriting the underlying
story availability. This module owns no progression rules or encounter clocks.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from character_attributes import ATTRIBUTE_IDS, CharacterAttributes


ROOT = Path(__file__).resolve().parent
MAX_PARTY = 3
CATALOG_PATH = ROOT/'assets/characters/party.json'


def _ids(value, known, *, empty=True):
    return (isinstance(value, (list, tuple)) and (empty or bool(value))
            and all(isinstance(identifier, str) and identifier in known for identifier in value)
            and len(value) == len(set(value)))


def _text(value, *, empty=True):
    return isinstance(value, str) and len(value) <= 240 and (empty or bool(value.strip()))


class PartyState:
    """One to three active members, with Caelan normally required as leader.

    ``characters['caelan']`` aliases the game's existing attribute object.
    Other registered characters begin unrecruited; defining a profile does not
    add it to the visible roster or grant any skill, equipment, or story flag.
    Future companions currently use the established starter ratings until an
    authored recruitment supplies their tuned profile. Mira retains MQ02's
    existing guest ratings exactly.
    """

    def __init__(self, caelan_attributes):
        if (not isinstance(caelan_attributes, CharacterAttributes)
                or caelan_attributes.character_id != 'caelan'):
            raise ValueError('Party requires Caelan’s persistent attributes')
        catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        self.definitions = deepcopy(catalog['characters'])
        self.known_ids = tuple(self.definitions)
        base = deepcopy(caelan_attributes.catalog)
        starter = deepcopy(base['characters']['caelan']['attributes'])
        mira = json.loads((ROOT/'assets/combat/guests.json').read_text())['guests']['mira']['attributes']
        for identifier, definition in self.definitions.items():
            if identifier == 'caelan':continue
            base['characters'][identifier] = {'name': definition['name'],
                'attributes': deepcopy(mira if definition['profile'] == 'mill_guest' else starter)}
        self.characters = {'caelan': caelan_attributes}
        self.characters.update({identifier: CharacterAttributes(identifier, base)
                                for identifier in self.known_ids if identifier != 'caelan'})
        self._members = {'caelan': {'available': True, 'reason': '', 'temporary': False}}
        self._active = ('caelan',)
        self._event = None

    @property
    def members(self):
        """An inspectable effective roster; mutate it through the public methods."""
        members = deepcopy(self._members)
        if self._event is not None:
            for identifier in self._event['unavailable']:
                members[identifier]['available'] = False
                members[identifier]['reason'] = self._event['reason'] or 'Unavailable for this event.'
        return members

    @property
    def active_ids(self):return self._active

    @property
    def required_ids(self):
        return tuple(dict.fromkeys(('caelan', *(self._event['required'] if self._event else ()))))

    @property
    def locked(self):return bool(self._event and self._event['locked'])

    @property
    def lock_reason(self):return self._event['reason'] if self._event else ''

    @property
    def event_id(self):return self._event['id'] if self._event else None

    @property
    def current_event_id(self):return self.event_id

    @property
    def pending_selection(self):
        if not self._event or not self._event['selection_pending']:return None
        return {'event_id': self._event['id'], 'title': self._event['selection_title'],
                'lock_after': self._event['lock_after']}

    @property
    def available_ids(self):
        return tuple(identifier for identifier, record in self.members.items() if record['available'])

    @property
    def reserve_ids(self):return tuple(identifier for identifier in self.available_ids if identifier not in self._active)

    def attributes(self, identifier):return self.characters[identifier]

    def is_available(self, identifier):return identifier in self.available_ids

    def selection_change_reason(self):
        return (self.lock_reason or 'The party is fixed for this event.') if self.locked else ''

    def selection_reason(self, identifiers):
        if not _ids(identifiers, self.known_ids, empty=False):
            return 'Choose distinct recruited characters.'
        if len(identifiers) > MAX_PARTY:return 'Combat supports up to three party members.'
        if any(identifier not in self._members for identifier in identifiers):return 'That character has not joined the party.'
        for identifier in identifiers:
            member = self.members[identifier]
            if not member['available']:
                return member['reason'] or self.definitions[identifier]['name']+' is unavailable.'
        if any(identifier not in identifiers for identifier in self.required_ids):
            names = ', '.join(self.definitions[identifier]['name'] for identifier in self.required_ids
                              if identifier not in identifiers)
            return names+' must be in the active party.'
        if identifiers[0] != 'caelan':return 'Caelan leads the travelling party.'
        if self.locked and tuple(identifiers) != self._active:return self.selection_change_reason()
        return ''

    def battle_reason(self):
        reason = self.selection_reason(self._active)
        if reason:return reason
        if not any(self.characters[identifier].current_hp for identifier in self._active):
            return 'At least one active party member must be able to fight.'
        return ''

    def select(self, identifiers):
        if self.selection_reason(identifiers):return False
        self._active = tuple(identifiers)
        return True

    def recruit(self, identifier, temporary=False):
        if not isinstance(identifier, str) or identifier not in self.definitions or type(temporary) is not bool:return False
        if identifier in self._members:return False
        self._members[identifier] = {'available': True, 'reason': '', 'temporary': temporary}
        if len(self._active) < MAX_PARTY and not self.locked:
            self._active += (identifier,)
        return True

    def set_available(self, identifier, available, reason=''):
        if (not isinstance(identifier, str) or identifier not in self._members or type(available) is not bool
                or not _text(reason) or (not available and not reason.strip())
                or (not available and identifier in self.required_ids)):
            return False
        self._members[identifier]['available'] = available
        self._members[identifier]['reason'] = '' if available else reason
        if not available:self._active = tuple(value for value in self._active if value != identifier)
        return True

    def begin_event(self, event_id, required=(), unavailable=(), reason='', locked=False,
                    selection_pending=False, selection_title='', lock_after=False):
        """Apply one named event atomically, retaining the previous formation."""
        if (not _text(event_id, empty=False) or not _text(reason)
                or type(locked) is not bool or type(selection_pending) is not bool
                or type(lock_after) is not bool or not _text(selection_title)
                or (locked and selection_pending)
                or not _ids(required, self.known_ids) or not _ids(unavailable, self.known_ids)):
            return False
        if self._event is not None:return self._event['id'] == event_id
        needed = tuple(dict.fromkeys(('caelan', *required)))
        if (len(needed) > MAX_PARTY or set(needed) & set(unavailable)
                or any(identifier not in self._members for identifier in (*needed, *unavailable))
                or any(not self._members[identifier]['available'] for identifier in needed)):
            return False
        previous = self._active
        candidates = [identifier for identifier in previous if identifier not in unavailable]
        for identifier in needed:
            if identifier not in candidates:candidates.append(identifier)
        # Keep every required character and retain as many previous choices as fit.
        active = ['caelan']
        active.extend(identifier for identifier in needed if identifier != 'caelan')
        active.extend(identifier for identifier in candidates if identifier not in active)
        self._event = {'id': event_id, 'required': list(required), 'unavailable': list(unavailable),
                       'reason': reason, 'locked': locked, 'previous': list(previous),
                       'selection_pending': selection_pending, 'selection_title': selection_title,
                       'lock_after': lock_after}
        self._active = tuple(active[:MAX_PARTY])
        return True

    def set_event_locked(self, event_id, locked=True):
        if not self._event or self._event['id'] != event_id or type(locked) is not bool:return False
        if locked and self._event['selection_pending']:return False
        self._event['locked'] = locked
        return True

    def lock_event(self, event_id, reason=''):
        if not _text(reason) or not self.set_event_locked(event_id):return False
        if reason:self._event['reason'] = reason
        return True

    def set_event_pending(self, event_id, pending, lock_after=False, title=''):
        if (not self._event or self._event['id'] != event_id or type(pending) is not bool
                or type(lock_after) is not bool or not _text(title)
                or (pending and self.locked)):
            return False
        self._event['selection_pending'] = pending
        self._event['lock_after'] = lock_after
        self._event['selection_title'] = title
        return True

    def confirm_event(self, event_id):
        if not self._event or self._event['id'] != event_id:return False
        if self.selection_reason(self._active):return False
        self._event['selection_pending'] = False
        self._event['locked'] = self._event['locked'] or self._event['lock_after']
        return True

    def previous_formation(self):
        return tuple(self._event['previous']) if self._event else ()

    def end_event(self, event_id, restore=False):
        if (self._event is None or self._event['id'] != event_id
                or type(restore) is not bool):return False
        previous = tuple(self._event['previous'])
        self._event = None
        # Story availability may have changed during the event. Respect it.
        self._active = tuple(identifier for identifier in self._active if self._members[identifier]['available'])
        if restore and not self.selection_reason(previous):self._active = previous
        return True

    def battle_members(self):
        """Copy the canonical ordered party into encounter input records."""
        result = []
        for identifier in self._active:
            attributes = self.characters[identifier]
            result.append({'identifier': 'player' if identifier == 'caelan' else identifier,
                           'name': attributes.name,
                           'attributes': {key: attributes.value(key) for key in ATTRIBUTE_IDS},
                           'hp': attributes.current_hp, 'mp': attributes.current_mp,
                           'attack': self.definitions[identifier]['attack']})
        return result

    def apply_battle(self, model):
        """Settle all participating resources atomically, without resetting reserves."""
        updates = {}
        for member in model.party:
            identifier = 'caelan' if member.identifier == 'player' else member.identifier
            if identifier not in self._members or identifier in updates:return False
            candidate = deepcopy(self.characters[identifier])
            if not candidate.set_current(hp=member.hp, mp=member.mp):return False
            updates[identifier] = (member.hp, member.mp)
        if tuple(updates) != self._active:return False
        for identifier, (hp, mp) in updates.items():
            self.characters[identifier].set_current(hp=hp, mp=mp)
        return True

    def to_dict(self):
        return {'version': 1, 'members': deepcopy(self._members), 'active': list(self._active),
                'characters': {identifier: attributes.to_dict() for identifier, attributes in self.characters.items()},
                'event': deepcopy(self._event)}

    def restore(self, data):
        """Validate the complete state before changing any live object or alias."""
        if (not isinstance(data, dict) or set(data) != {'version', 'members', 'active', 'characters', 'event'}
                or type(data['version']) is not int or data['version'] != 1
                or not isinstance(data['members'], dict) or not data['members']
                or 'caelan' not in data['members'] or not set(data['members']) <= set(self.known_ids)
                or not isinstance(data['characters'], dict) or set(data['characters']) != set(self.known_ids)):
            return False
        proposed = PartyState(deepcopy(self.characters['caelan']))
        for identifier, snapshot in data['characters'].items():
            attributes = proposed.characters[identifier]
            existing_modifiers = deepcopy(self.characters[identifier]._modifiers)
            bonuses = {key: sum(source.get(key, 0) for source in existing_modifiers.values())
                       for key in ATTRIBUTE_IDS}
            if not attributes.restore(snapshot, modifier_bonuses=bonuses):return False
            attributes._modifiers = existing_modifiers
        for identifier, record in data['members'].items():
            if (not isinstance(record, dict) or set(record) != {'available','reason','temporary'}
                    or type(record['available']) is not bool or type(record['temporary']) is not bool
                    or not _text(record['reason'])
                    or (not record['available'] and not record['reason'].strip())
                    or (record['available'] and record['reason'])):
                return False
        if not data['members']['caelan']['available'] or data['members']['caelan']['temporary']:return False
        proposed._members = deepcopy(data['members'])
        event = data['event']
        if event is not None:
            if (not isinstance(event, dict)
                    or set(event) != {'id','required','unavailable','reason','locked','previous',
                                      'selection_pending','selection_title','lock_after'}
                    or not _text(event['id'], empty=False) or not _text(event['reason'])
                    or type(event['locked']) is not bool
                    or type(event['selection_pending']) is not bool
                    or type(event['lock_after']) is not bool or not _text(event['selection_title'])
                    or (event['locked'] and event['selection_pending'])
                    or not _ids(event['required'], self.known_ids)
                    or not _ids(event['unavailable'], self.known_ids)
                    or not _ids(event['previous'], self.known_ids, empty=False)
                    or len(event['previous']) > MAX_PARTY or event['previous'][0] != 'caelan'
                    or any(identifier not in proposed._members for identifier in event['previous'])):
                return False
            if not proposed.begin_event(event['id'],event['required'],event['unavailable'],event['reason'],False):return False
            proposed._event = deepcopy(event)
            # Validate independently of its locked-current-formation check.
            proposed._event['locked'] = False
        if proposed.selection_reason(data['active']):return False
        proposed._active = tuple(data['active'])
        if event is not None:proposed._event['locked'] = event['locked']
        # Preserve all exposed CharacterAttributes object identities.
        for identifier, source in proposed.characters.items():
            target = self.characters[identifier]
            target._attributes = dict(source._attributes)
            target._current_hp, target._current_mp = source.current_hp, source.current_mp
            target._modifiers = deepcopy(source._modifiers)
        self._members, self._active, self._event = proposed._members, proposed._active, proposed._event
        return True
