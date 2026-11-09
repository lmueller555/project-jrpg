"""Saved character EXP and atomic, deterministic victory growth plans.

Character attributes remain owned by the party. Existing journeys acquire zero
EXP without replacing their saved stats; future levels add the approved growth
deltas to that preserved baseline. Encounter receipts and checkpointing belong
to the combat owner, not the presentation or this module.
"""
from __future__ import annotations

from copy import deepcopy

from character_attributes import (ATTRIBUTE_CAPS, ATTRIBUTE_IDS, MAX_ATTRIBUTE_VALUE,
                                  CharacterAttributes)
from leveling import CharacterLevel, character_ids, character_stats, combat_xp_allocations


_IDS = character_ids()
_PLAN_FIELDS = {'version', 'amount', 'active_ids', 'end_hp', 'characters'}
_AWARD_FIELDS = {'character_id', 'requested_xp', 'accepted_xp', 'discarded_xp',
                 'old_total_xp', 'new_total_xp', 'old_level', 'new_level',
                 'stat_gains', 'stats_before', 'stats_after'}


def _base_stats(attributes):
    return {key: attributes.base_value(key) for key in ATTRIBUTE_IDS}


def _valid_stats(values):
    return (isinstance(values, dict) and set(values) == set(ATTRIBUTE_IDS)
            and all(type(value) is int
                    and (1 if key == 'hp' else 0) <= value <= MAX_ATTRIBUTE_VALUE
                    for key, value in values.items()))


def _snapshot_records(data):
    if (not isinstance(data, dict) or set(data) != {'version', 'characters'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['characters'], dict)
            or set(data['characters']) != set(_IDS)):
        raise ValueError('Invalid character EXP snapshot')
    records = {}
    for identifier in _IDS:
        record = CharacterLevel.from_dict(data['characters'][identifier])
        if record.character_id != identifier:
            raise ValueError('Character EXP identity does not match its slot')
        records[identifier] = record
    return records


class CharacterProgression:
    """One saved level record per character, independent of recruitment.

    ``preview`` does not mutate levels, stats, current resources, or modifiers.
    ``apply`` accepts only a recomputable plan whose complete participating
    before-state still matches. The combat receipt prevents duplicate rewards
    after saving or Continue; repeated nonzero plans also fail the before check.
    """

    def __init__(self, party):
        if (not hasattr(party, 'characters') or set(party.characters) != set(_IDS)
                or any(not isinstance(party.characters[key], CharacterAttributes)
                       or party.characters[key].character_id != key for key in _IDS)):
            raise ValueError('Character progression requires the canonical party')
        self.party = party
        self.records = {identifier: CharacterLevel(identifier) for identifier in _IDS}

    def __getitem__(self, identifier):
        return self.records[identifier]

    def level(self, identifier):
        return self.records[identifier].level

    def to_dict(self):
        return {'version': 1,
                'characters': {identifier: self.records[identifier].to_dict()
                               for identifier in _IDS}}

    def initialize_new_game(self):
        """Use approved level-one baselines only for a genuinely new journey.

        Ordinary construction and migration deliberately do not call this:
        saved placeholder ratings, earned stats and current resources must
        survive Continue. The game invokes it while setting up a fresh party.
        """
        for identifier in _IDS:
            attributes = self.party.characters[identifier]
            attributes._attributes = character_stats(identifier, 1)
            attributes._modifiers = {}
            attributes._current_hp = attributes.value('hp')
            attributes._current_mp = attributes.value('mp')
        self.restore()
        return True

    def restore(self, data=None):
        """Restore EXP only; old journeys start at zero with all stats intact."""
        try:
            records = ({identifier: CharacterLevel(identifier) for identifier in _IDS}
                       if data is None else _snapshot_records(data))
        except (TypeError, ValueError, KeyError, OverflowError):
            return False
        self.records = records
        return True

    @staticmethod
    def valid_snapshot(data):
        try:
            _snapshot_records(data)
            return True
        except (TypeError, ValueError, KeyError, OverflowError):
            return False

    @classmethod
    def valid_journey(cls, data):
        return (isinstance(data, dict)
                and ('character_levels' not in data
                     or cls.valid_snapshot(data['character_levels'])))

    def preview(self, amount, active_ids, end_hp):
        """Build every combatant's outcome from actual HP before first aid.

        Each living active character receives the full battle EXP. KO entries
        are retained with zero requested EXP so the view can explain exclusion;
        reserves and summoned bots never enter this plan. Stats are unbuffed
        persistent base values, with the existing per-attribute caps applied.
        """
        allocations = combat_xp_allocations(amount, active_ids, end_hp)
        result = {'version': 1, 'amount': amount, 'active_ids': list(active_ids),
                  'end_hp': {identifier: end_hp[identifier] for identifier in active_ids},
                  'characters': {}}
        for identifier in active_ids:
            record = CharacterLevel.from_dict(self.records[identifier].to_dict())
            award = record.award_xp(allocations[identifier]).to_dict()
            before = _base_stats(self.party.characters[identifier])
            after = {key: max(before[key], min(ATTRIBUTE_CAPS[key],
                                              before[key]+award['stat_gains'][key]))
                     for key in ATTRIBUTE_IDS}
            result['characters'][identifier] = {
                **award, 'stats_before': before, 'stats_after': after}
        return result

    @staticmethod
    def valid_plan(plan):
        """Recompute the complete saved award without trusting its gains."""
        try:
            if (not isinstance(plan, dict) or set(plan) != _PLAN_FIELDS
                    or type(plan['version']) is not int or plan['version'] != 1
                    or not isinstance(plan['active_ids'], list)
                    or not isinstance(plan['end_hp'], dict)
                    or not isinstance(plan['characters'], dict)):
                return False
            active = plan['active_ids']
            allocations = combat_xp_allocations(plan['amount'], active, plan['end_hp'])
            if (set(plan['end_hp']) != set(active)
                    or set(plan['characters']) != set(active)):
                return False
            for identifier in active:
                entry = plan['characters'][identifier]
                if (not isinstance(entry, dict) or set(entry) != _AWARD_FIELDS
                        or entry['character_id'] != identifier
                        or not _valid_stats(entry['stats_before'])
                        or not _valid_stats(entry['stats_after'])):
                    return False
                # Constructor validation rejects bools and out-of-range totals.
                record = CharacterLevel(identifier, entry['old_total_xp'])
                expected = record.award_xp(allocations[identifier]).to_dict()
                # Equality alone would accept True as 1 in numeric receipt fields.
                if any(type(entry[field]) is not int for field in (
                        'requested_xp', 'accepted_xp', 'discarded_xp', 'old_total_xp',
                        'new_total_xp', 'old_level', 'new_level')):
                    return False
                if (not isinstance(entry['stat_gains'], dict)
                        or set(entry['stat_gains']) != set(ATTRIBUTE_IDS)
                        or any(type(value) is not int for value in entry['stat_gains'].values())
                        or any(entry[field] != value for field, value in expected.items())):
                    return False
                after = {key: max(entry['stats_before'][key],
                                  min(ATTRIBUTE_CAPS[key], entry['stats_before'][key]
                                      +expected['stat_gains'][key])) for key in ATTRIBUTE_IDS}
                if entry['stats_after'] != after:
                    return False
            return True
        except (TypeError, ValueError, KeyError, OverflowError):
            return False

    def matches_plan(self, plan, after=False):
        """Match participating EXP and base stats, leaving resources separate."""
        if type(after) is not bool or not self.valid_plan(plan):
            return False
        state = 'new' if after else 'old'
        stats = 'stats_after' if after else 'stats_before'
        return all(self.records[identifier].total_xp == entry[state+'_total_xp']
                   and _base_stats(self.party.characters[identifier]) == entry[stats]
                   for identifier, entry in plan['characters'].items())

    def apply(self, plan):
        """Commit a valid before-state once without healing or losing modifiers."""
        if not self.matches_plan(plan):
            return False
        proposed = {}
        for identifier, entry in plan['characters'].items():
            attributes = deepcopy(self.party.characters[identifier])
            if not attributes.apply_growth(entry['stat_gains']):
                return False
            if _base_stats(attributes) != entry['stats_after']:
                return False
            proposed[identifier] = attributes
        # Every mutation has been validated on independent copies. Preserve
        # exposed attribute identities, HP/MP and modifier owners on commit.
        for identifier, attributes in proposed.items():
            self.party.characters[identifier]._attributes = dict(attributes._attributes)
            self.records[identifier] = CharacterLevel(
                identifier, plan['characters'][identifier]['new_total_xp'])
        return True
