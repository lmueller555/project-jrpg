"""Canonical wearable-rig requirements and restorative calculations.

Allocation is a configuration rather than ammunition or a stat multiplier.
These pure rules are shared by combat, saved state and presentation.
"""
CHANNELS = ('weapons', 'protection', 'support')
CAPACITY = 6
DEFAULT_ALLOCATION = dict.fromkeys(CHANNELS, 2)
SKILLS = {
    'charged_bolt': {'requirements': {'weapons': 3, 'protection': 0, 'support': 0},
                     'mp_cost': 3, 'kind': 'physical', 'potency': 1.75},
    'bulwark': {'requirements': {'weapons': 0, 'protection': 3, 'support': 0},
                'mp_cost': 3, 'kind': 'barrier', 'potency': 0, 'barrier_percent': 25},
    'repair_pulse': {'requirements': {'weapons': 0, 'protection': 0, 'support': 3},
                     'mp_cost': 4, 'kind': 'heal', 'potency': 0},
    'impact_bolt': {'requirements': {'weapons': 2, 'protection': 2, 'support': 0},
                    'mp_cost': 4, 'kind': 'physical', 'potency': 1,
                    'barrier_percent': 10},
    'arc_discharge': {'requirements': {'weapons': 3, 'protection': 0, 'support': 2},
                      'mp_cost': 5, 'kind': 'magical', 'potency': 1.5,
                      'element': 'electric'},
}


def valid_allocation(value):
    return (isinstance(value, dict) and set(value) == set(CHANNELS)
            and all(type(value[key]) is int and 0 <= value[key] <= CAPACITY for key in CHANNELS)
            and sum(value.values()) == CAPACITY)


def healing_amount(spirit, target_max_hp):
    """Nominal restorative output, before missing-HP clamping."""
    if type(spirit) is not int or not 0 <= spirit <= 999:
        raise ValueError('Invalid repair Spirit')
    if type(target_max_hp) is not int or not 1 <= target_max_hp <= 9999:
        raise ValueError('Invalid repair target HP')
    return min(9999, target_max_hp*15//100+2*spirit)


def barrier_amount(maximum_hp, percent):
    if type(maximum_hp) is not int or not 1 <= maximum_hp <= 9999:
        raise ValueError('Invalid barrier HP')
    if type(percent) is not int or not 1 <= percent <= 100:
        raise ValueError('Invalid barrier percentage')
    return max(1, maximum_hp*percent//100)
