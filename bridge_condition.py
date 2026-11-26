"""Pure bridge condition shared by world state, saves and presentation readers.

The legacy layout is a migration origin, not evidence that a scripted attack
has happened. Explicit conditions take precedence over older repair flags.
"""
from __future__ import annotations

from dataclasses import dataclass


DEFAULT_REPAIR_FLAG = 'ELDEN_VALE_WEST_BRIDGE_REPAIRED'
_PHASES = frozenset(('intact', 'destroyed', 'restored'))
_ORIGINS = frozenset(('explicit', 'legacy_layout', 'legacy_repair'))


def _valid_state(phase, origin):
    if type(phase) is not str or type(origin) is not str:
        return False
    if phase not in _PHASES or origin not in _ORIGINS:
        return False
    return (origin == 'explicit'
            or origin == 'legacy_layout' and phase == 'destroyed'
            or origin == 'legacy_repair' and phase == 'restored')


@dataclass(frozen=True)
class BridgeCondition:
    phase: str = 'destroyed'
    origin: str = 'explicit'

    def __post_init__(self):
        if not _valid_state(self.phase, self.origin):
            raise ValueError('Invalid bridge phase or origin')

    @property
    def passable(self):
        return self.phase in ('intact', 'restored')

    @property
    def destroyed(self):
        return self.phase == 'destroyed'

    def to_dict(self):
        return {'version': 1, 'phase': self.phase, 'origin': self.origin}


def valid_snapshot(value):
    """Accept only a complete version-one condition with a legal provenance."""
    return (type(value) is dict
            and set(value) == {'version', 'phase', 'origin'}
            and type(value['version']) is int and value['version'] == 1
            and _valid_state(value['phase'], value['origin']))


def _has_flag(flags, repair_flag):
    if flags is None:
        return False
    if isinstance(flags, str):
        return flags == repair_flag
    try:
        return repair_flag in flags
    except TypeError:
        return False


def resolve_condition(value=None, *, flags=(), repair_flag=DEFAULT_REPAIR_FLAG):
    """Resolve an authoritative condition or infer only the legacy placeholder."""
    if isinstance(value, BridgeCondition):
        return value
    if value is not None:
        if not valid_snapshot(value):
            raise ValueError('Invalid bridge condition snapshot')
        return BridgeCondition(value['phase'], value['origin'])
    if _has_flag(flags, repair_flag):
        return BridgeCondition('restored', 'legacy_repair')
    return BridgeCondition('destroyed', 'legacy_layout')


def opening_condition(value=None, *, flags=(), repair_flag=DEFAULT_REPAIR_FLAG):
    """Roll the superseded scenery placeholder into the intact opening.

    Explicit damage and legacy repair facts retain their physical condition.
    No attack, reconstruction, reward or checkpoint permission is inferred.
    """
    condition = resolve_condition(value, flags=flags, repair_flag=repair_flag)
    if condition.origin == 'legacy_layout':return BridgeCondition('intact')
    return condition


def condition_for_game(game, region=None):
    """Read existing owners and flags without allocating a region or a world."""
    for owner_name in ('overworld_travel', 'world'):
        owner = getattr(game, owner_name, None)
        value = getattr(owner, 'bridge_condition', None)
        if value is not None:
            return resolve_condition(value)
    repair_flag = DEFAULT_REPAIR_FLAG
    if isinstance(region, dict):
        bridge = region.get('bridge')
        if isinstance(bridge, dict) and isinstance(bridge.get('repair_flag'), str):
            repair_flag = bridge['repair_flag']
    flags = getattr(getattr(game, 'social', None), 'flags', ())
    return resolve_condition(flags=flags, repair_flag=repair_flag)
