"""Validated enemy action designs whose runtime mechanics are still pending.

These local actions are authoring data, not additions to the live action
catalog. Validation returns detached definitions for Bestiary inspection;
the battle adapter must reject pending designs before constructing a fight.
"""
from copy import deepcopy
import math
import re


_ELEMENTS = frozenset(('non_elemental', 'fire', 'electric', 'water', 'ice',
                       'nature', 'wind', 'holy', 'ground'))
_REQUIREMENTS = frozenset(('party_wide_damage', 'recovery_vulnerability',
                           'guaranteed_target_response'))
_IDENTIFIER = re.compile(r'^[a-zA-Z0-9_.:/-]{1,128}$')
_DAMAGE_KINDS = ('physical', 'magical')


def _identifier(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _number(value, minimum=0, maximum=None, *, exclusive_minimum=False):
    if type(value) not in (int, float):return False
    try:
        finite = math.isfinite(value)
    except OverflowError:
        return False
    return (finite and (value > minimum if exclusive_minimum else value >= minimum)
            and (maximum is None or value <= maximum))


def _validate_action(identifier, action):
    fields = {'name', 'kind', 'target', 'potency', 'mp_cost'}
    if not _identifier(identifier) or not isinstance(action, dict):
        raise ValueError('Invalid pending enemy action')
    damaging = action.get('kind') in _DAMAGE_KINDS
    if (set(action) != fields | ({'element'} if damaging else set())
            or not isinstance(action['name'], str) or not action['name'].strip()
            or len(action['name']) > 120
            or action['kind'] not in (*_DAMAGE_KINDS, 'prepare', 'recover')
            or type(action['mp_cost']) is not int or action['mp_cost'] < 0):
        raise ValueError('Invalid pending enemy action')
    if damaging:
        if (action['target'] not in ('opponent', 'all_opponents')
                or not _number(action['potency'], exclusive_minimum=True)
                or not isinstance(action['element'], str)
                or action['element'] not in _ELEMENTS):
            raise ValueError('Invalid pending enemy damage action')
    elif (action['target'] != 'self' or not _number(action['potency'])
          or action['potency'] != 0 or action['mp_cost'] != 0):
        raise ValueError('Invalid pending enemy utility action')


def validate_combat_design(design, behavior):
    """Validate a pending design and return an independent local action map.

    The windup locks a single physical attack behind a preparation step. Its
    recovery follows immediately and exposes the enemy until the next damage
    action in the looping sequence. No action, rule or caller data is mutated.
    """
    if (not isinstance(design, dict)
            or set(design) != {'status', 'requirements', 'actions', 'windup',
                               'recovery', 'encounter'}
            or design['status'] != 'pending_runtime'):
        raise ValueError('Invalid pending enemy combat design')
    requirements = design['requirements']
    if (not isinstance(requirements, list) or len(requirements) != len(_REQUIREMENTS)
            or any(not isinstance(value, str) for value in requirements)
            or set(requirements) != _REQUIREMENTS):
        raise ValueError('Invalid pending enemy combat requirements')
    if (not isinstance(behavior, dict)
            or set(behavior) != {'sequence', 'fallback', 'targeting'}
            or not isinstance(behavior['sequence'], list) or not behavior['sequence']
            or any(not _identifier(value) for value in behavior['sequence'])
            or not _identifier(behavior['fallback'])
            or behavior['targeting'] != 'cycle_living_party'):
        raise ValueError('Invalid pending enemy combat behavior')
    sequence = behavior['sequence']
    actions = design['actions']
    if not isinstance(actions, dict) or set(actions) != set(sequence):
        raise ValueError('Pending enemy actions must match the complete sequence')
    for identifier, action in actions.items():_validate_action(identifier, action)
    fallback = actions.get(behavior['fallback'])
    if (fallback is None or fallback['kind'] not in _DAMAGE_KINDS
            or fallback['mp_cost'] != 0):
        raise ValueError('Pending enemy behavior needs a free damaging fallback')

    windup = design['windup']
    if (not isinstance(windup, dict)
            or set(windup) != {'prepare_action', 'attack_action', 'minimum_target_actions',
                               'retargeting'}
            or any(not _identifier(windup[key]) or windup[key] not in actions
                   for key in ('prepare_action', 'attack_action'))
            or type(windup['minimum_target_actions']) is not int
            or windup['minimum_target_actions'] < 1
            or windup['retargeting'] != 'repeat_warning'):
        raise ValueError('Invalid pending enemy windup')
    prepare, attack = windup['prepare_action'], windup['attack_action']
    if (actions[prepare]['kind'] != 'prepare'
            or actions[attack]['kind'] != 'physical'
            or actions[attack]['target'] != 'opponent'
            or any(index+1 >= len(sequence) or sequence[index+1] != attack
                   for index, identifier in enumerate(sequence) if identifier == prepare)
            or any(index == 0 or sequence[index-1] != prepare
                   for index, identifier in enumerate(sequence) if identifier == attack)):
        raise ValueError('Pending enemy preparation must precede its physical attack')

    recovery = design['recovery']
    if (not isinstance(recovery, dict)
            or set(recovery) != {'after_action', 'recovery_action',
                                 'damage_taken_multiplier', 'ends_before_action'}
            or any(not _identifier(recovery[key]) or recovery[key] not in actions
                   for key in ('after_action', 'recovery_action', 'ends_before_action'))
            or not _number(recovery['damage_taken_multiplier'], 1, 10,
                           exclusive_minimum=True)):
        raise ValueError('Invalid pending enemy recovery')
    recover, following = recovery['recovery_action'], recovery['ends_before_action']
    if (recovery['after_action'] != attack or actions[recover]['kind'] != 'recover'
            or actions[following]['kind'] not in _DAMAGE_KINDS
            or any(index+1 >= len(sequence) or sequence[index+1] != recover
                   for index, identifier in enumerate(sequence) if identifier == attack)
            or any(sequence[(index+1) % len(sequence)] != following
                   for index, identifier in enumerate(sequence) if identifier == recover)):
        raise ValueError('Pending enemy recovery must follow the attack and end before damage')

    encounter = design['encounter']
    if (not isinstance(encounter, dict)
            or set(encounter) != {'trigger', 'repeatable', 'formation_size'}
            or encounter['trigger'] != 'story' or encounter['repeatable'] is not False
            or type(encounter['formation_size']) is not int or encounter['formation_size'] != 1):
        raise ValueError('Invalid pending enemy story encounter')
    return deepcopy(actions)
