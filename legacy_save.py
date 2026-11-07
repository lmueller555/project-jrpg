"""One-way import of paid rewards from retired progression save records.

Only a compact reward lookup survives for compatibility. This module provides
no graph, traversal, purchase, rank, currency, or interface behavior. Callers
validate the normalized journey before presenting Continue; disk writes belong
to the ordinary successful-Continue checkpoint.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from character_attributes import ATTRIBUTE_CAPS, ATTRIBUTE_IDS


ROOT = Path(__file__).resolve().parent
REWARDS_PATH = ROOT/'assets/compatibility/retired_progression_rewards.json'
MAX_RECEIPTS = 4096
MAX_LEGACY_NUMBER = 999999999
_IDENTIFIER = re.compile(r'^[a-zA-Z0-9_.:/-]{1,128}$')


def _identifier(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _integer(value, minimum=0, maximum=MAX_LEGACY_NUMBER):
    return type(value) is int and minimum <= value <= maximum


def _unique_ids(value, known=None, maximum=MAX_RECEIPTS):
    return (isinstance(value, list) and len(value) <= maximum
            and all(_identifier(item) and (known is None or item in known) for item in value)
            and len(value) == len(set(value)))


def _lookup():
    data = json.loads(REWARDS_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'board_id', 'boards'}
            or type(data['version']) is not int or data['version'] != 1
            or data['board_id'] != 'caelan_starter'
            or not isinstance(data['boards'], dict) or set(data['boards']) != {'1', '2', '3'}):
        raise ValueError('Invalid retired reward lookup')
    for rewards in data['boards'].values():
        if not isinstance(rewards, dict) or not rewards:
            raise ValueError('Invalid retired reward lookup')
        for identifier, reward in rewards.items():
            if (not _identifier(identifier) or not isinstance(reward, list)
                    or reward and (len(reward) != 2 or
                       (reward[0] == 'ability' and not _identifier(reward[1])) or
                       (reward[0] != 'ability' and
                        (not isinstance(reward[0], str) or reward[0] not in ATTRIBUTE_IDS
                         or not _integer(reward[1], 1))))):
                raise ValueError('Invalid retired reward lookup')
    return data


def _ledger_receipts(data):
    if (not isinstance(data, dict) or set(data) != {'version', 'receipts'}
            or type(data['version']) is not int or data['version'] != 1
            or not _unique_ids(data['receipts'])):
        raise ValueError('Invalid battle reward receipts')
    return data['receipts']


def _retired_rewards(record):
    lookup = _lookup()
    if (not isinstance(record, dict)
            or set(record) != {'version', 'board_id', 'board_version', 'characters', 'receipts'}
            or type(record['board_version']) is not int or record['board_version'] not in (1, 2, 3)
            or type(record['version']) is not int
            or record['version'] != (2 if record['board_version'] == 3 else 1)
            or record['board_id'] != lookup['board_id']
            or not isinstance(record['characters'], dict) or set(record['characters']) != {'caelan'}
            or not _unique_ids(record['receipts'])):
        raise ValueError('Invalid retired progression record')
    version = record['board_version']
    rewards = lookup['boards'][str(version)]
    bonuses, learned = {}, {}
    fields = {'rp', 'spent_steps', 'position', 'visited', 'activated'}
    if version == 3:fields.add('legacy_activated')
    for character_id, state in record['characters'].items():
        if (not isinstance(state, dict) or set(state) != fields
                or not _integer(state['rp']) or not _integer(state['spent_steps'])
                or state['spent_steps'] > state['rp']
                or not isinstance(state['position'], str) or state['position'] not in rewards
                or not _unique_ids(state['visited'], rewards, len(rewards))
                or not _unique_ids(state['activated'], rewards, len(rewards))):
            raise ValueError('Invalid retired character rewards')
        visited, activated = set(state['visited']), set(state['activated'])
        if ('origin' not in visited or state['position'] not in visited
                or not activated <= visited or len(visited) > state['spent_steps']+1
                or state['position'] == 'origin' and len(visited) > 1
                   and state['spent_steps'] < len(visited)
                or any(not rewards[identifier] for identifier in activated)):
            raise ValueError('Invalid retired reward provenance')
        legacy = state.get('legacy_activated', [])
        if (not _unique_ids(legacy, activated, len(rewards))
                or any(identifier not in lookup['boards']['2']
                       or not lookup['boards']['2'][identifier] for identifier in legacy)):
            raise ValueError('Invalid retired paid reward provenance')
        amounts = dict.fromkeys(ATTRIBUTE_IDS, 0)
        abilities = set()
        for identifier in activated:
            reward = lookup['boards']['2'][identifier] if identifier in legacy else rewards[identifier]
            if reward[0] == 'ability':abilities.add(reward[1])
            else:amounts[reward[0]] += reward[1]
        bonuses[character_id] = amounts
        learned[character_id] = abilities
    return bonuses, learned, record['receipts']


def _fold_attributes(record, character_id, bonuses):
    if (not isinstance(record, dict)
            or set(record) != {'version', 'character_id', 'attributes', 'current_hp', 'current_mp'}
            or type(record['version']) is not int or record['version'] not in (1, 2, 3)
            or record['character_id'] != character_id
            or not isinstance(record['attributes'], dict)
            or set(record['attributes']) != set(ATTRIBUTE_IDS)
            or any(not _integer(value, 1 if key == 'hp' else 0, ATTRIBUTE_CAPS[key])
                   for key, value in record['attributes'].items())):
        raise ValueError('Invalid saved character attributes')
    result = deepcopy(record)
    # Versions one and two already store aggregate earned growth. Version
    # three stores base attributes with paid bonuses derived by their owner.
    if record['version'] == 3:
        result['attributes'] = {key: min(ATTRIBUTE_CAPS[key], value+bonuses.get(key, 0))
                                for key, value in record['attributes'].items()}
    for resource in ('hp', 'mp'):
        if not _integer(result['current_'+resource], 0, result['attributes'][resource]):
            raise ValueError('Invalid saved character resources')
    return result


def _merge_learned(data, learned):
    earned = {key: set(values) for key, values in learned.items() if values}
    if not earned:return
    registrations = json.loads((ROOT/'assets/abilities/characters.json').read_text())['characters']
    if 'character_abilities' not in data:
        data['character_abilities'] = {'version': 1, 'characters': {
            key: {'equipped_weapon': None, 'first_weapon_acquired': False}
            for key in registrations}}
    record = data['character_abilities']
    if not isinstance(record, dict):raise ValueError('Invalid saved character abilities')
    existing = record.get('learned_abilities', {})
    if (not isinstance(existing, dict)
            or any(not isinstance(key, str) or key not in registrations
                   or not _unique_ids(values) for key, values in existing.items())):
        raise ValueError('Invalid saved learned abilities')
    merged = {key: set(values) for key, values in existing.items()}
    for key, values in earned.items():merged.setdefault(key, set()).update(values)
    for key, values in merged.items():
        registered = set().union(*(registrations[key][group] for group in ('skills', 'spells', 'abilities')))
        if not values <= registered:raise ValueError('Unknown saved learned ability')
    record['learned_abilities'] = {key: sorted(values) for key, values in sorted(merged.items()) if values}


def _normalize_pending(data):
    pending = data.get('post_battle')
    if pending is None:return
    if not isinstance(pending, dict) or not isinstance(pending.get('rewards'), dict):
        raise ValueError('Invalid saved battle rewards')
    rewards = pending['rewards']
    if 'rp' in rewards:
        if set(rewards) != {'rp', 'drops'} or not _integer(rewards['rp']):
            raise ValueError('Invalid retired battle reward')
        pending['rewards'] = {'drops': rewards['drops']}


def migrate_retired_progression(data):
    """Return an independent normalized journey, or reject without mutation.

    Earned effective attributes, skills and reward receipts survive. Obsolete
    progression currencies are discarded rather than reinterpreted as XP. The
    returned copy must still pass the game's complete journey validators.
    """
    if not isinstance(data, dict):raise ValueError('Invalid saved journey')
    try:
        result = deepcopy(data)
    except RecursionError as error:
        raise ValueError('Saved journey nesting exceeds the supported depth') from error
    _normalize_pending(result)
    if 'aether_lattice' not in result:return result
    bonuses, learned, receipts = _retired_rewards(result['aether_lattice'])
    old = result['aether_lattice']['characters']['caelan']
    if 'character_attributes' not in result:
        if old['rp'] or old['spent_steps'] or old['activated']:
            raise ValueError('Paid rewards require saved character attributes')
    else:
        original = result['character_attributes']
        if 'party' in result:
            party = result['party']
            if (not isinstance(party, dict) or not isinstance(party.get('characters'), dict)
                    or party['characters'].get('caelan') != original):
                raise ValueError('Saved party and character attributes disagree')
        result['character_attributes'] = _fold_attributes(original, 'caelan', bonuses['caelan'])
        if 'party' in result:
            result['party']['characters']['caelan'] = deepcopy(result['character_attributes'])
    _merge_learned(result, learned)
    previous = _ledger_receipts(result['battle_rewards']) if 'battle_rewards' in result else []
    combined = sorted(set(previous) | set(receipts))
    if len(combined) > MAX_RECEIPTS:raise ValueError('Too many saved battle rewards')
    result['battle_rewards'] = {'version': 1, 'receipts': combined}
    del result['aether_lattice']
    return result
