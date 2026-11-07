"""Render-independent Caelan action choreography in logical battlefield units.

The catalog owns action boundaries as well as motion, so contact, damage and
the return to formation share one clock. Sampling is pure and works with large
frames, replay scrubbing, and both armed and unarmed sprite banks.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path


CHOREOGRAPHY_PATH = Path(__file__).resolve().parent/'assets/combat/caelan_choreography.json'
ACTION_IDS = frozenset(('attack', 'aether_edge', 'aether_dart', 'guard'))


def _number(value, low=0, high=10000):
    return (type(value) in (int, float) and math.isfinite(value)
            and low <= value <= high)


def load_choreography(data=None):
    """Validate and copy the timeline, including continuous phase boundaries."""
    if data is None:data = json.loads(CHOREOGRAPHY_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'actions'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['actions'], dict)
            or set(data['actions']) != ACTION_IDS):
        raise ValueError('Invalid Caelan choreography catalog')
    fields = {'duration', 'impact_at', 'catalog_timing', 'reaction_duration',
              'release_at', 'phases'}
    phase_fields = {'name', 'start', 'end', 'pose', 'approach', 'elevation', 'camera'}
    for action in data['actions'].values():
        if (not isinstance(action, dict) or set(action) != fields
                or not _number(action['duration'], .001, 10)
                or not _number(action['impact_at'], .001, action['duration'])
                or not _number(action['reaction_duration'], 0, action['duration'])
                or (action['release_at'] is not None
                    and (not _number(action['release_at'], 0, action['impact_at'])
                         or action['release_at'] >= action['impact_at']))
                or not isinstance(action['catalog_timing'], dict)
                or set(action['catalog_timing']) != {'duration', 'impact_at'}
                or not _number(action['catalog_timing']['duration'], .001, 10)
                or not _number(action['catalog_timing']['impact_at'], 0,
                               action['catalog_timing']['duration'])
                or not isinstance(action['phases'], list) or not action['phases']):
            raise ValueError('Invalid Caelan action choreography')
        previous_end = 0
        previous_approach = previous_camera = 0
        names = set()
        for phase in action['phases']:
            if (not isinstance(phase, dict)
                    or not phase_fields <= set(phase) <= phase_fields | {'pose_start_ms', 'pose_duration_ms'}
                    or any(not isinstance(phase[key], str) or not phase[key].strip()
                           for key in ('name', 'pose'))
                    or phase['name'] in names
                    or not _number(phase['start'], 0, action['duration'])
                    or not _number(phase['end'], 0, action['duration'])
                    or phase['end'] <= phase['start']
                    or not math.isclose(phase['start'], previous_end, abs_tol=1e-9)
                    or not _number(phase.get('pose_start_ms', 0))
                    or not _number(phase.get('pose_duration_ms', 1), .001)
                    or not _number(phase['elevation'], 0, 100)
                    or any(not isinstance(phase[key], list) or len(phase[key]) != 2
                           or any(not _number(value, 0, 1) for value in phase[key])
                           for key in ('approach', 'camera'))):
                raise ValueError('Invalid Caelan choreography phase')
            if (phase['approach'][0] != previous_approach
                    or phase['camera'][0] != previous_camera):
                raise ValueError('Discontinuous Caelan choreography motion')
            previous_end = phase['end']
            previous_approach = phase['approach'][1]
            previous_camera = phase['camera'][1]
            names.add(phase['name'])
        if (not math.isclose(previous_end, action['duration'], abs_tol=1e-9)
                or previous_approach != 0 or previous_camera != 0):
            raise ValueError('Caelan choreography must return to formation')
    return deepcopy(data['actions'])


_ACTIONS = load_choreography()


def action_timing(action_id):
    """Return the choreography's (duration, impact_at), in seconds."""
    action = _action(action_id)
    return action['duration'], action['impact_at']


def timing_override(action_id, duration, impact_at):
    """Use profiles for canonical Caelan timings; honor custom action fixtures."""
    if action_id not in _ACTIONS:return None
    action = _ACTIONS[action_id]
    original = action['catalog_timing']
    if (duration, impact_at) != (original['duration'], original['impact_at']):return None
    return action['duration'], action['impact_at']


def _action(action_id):
    if not isinstance(action_id, str) or action_id not in _ACTIONS:
        raise ValueError('Unknown Caelan choreography')
    return _ACTIONS[action_id]


def _clamp(value):return max(0., min(1., value))


def _mix(pair, progress):return pair[0]+(pair[1]-pair[0])*progress


@dataclass(frozen=True)
class ChoreographySample:
    action_id: str
    phase: str
    pose: str
    pose_ms: float
    armed: bool
    elapsed: float
    duration: float
    impact_at: float
    progress: float
    phase_progress: float
    impact_progress: float
    approach: float
    elevation: float
    target_reaction: float
    camera_weight: float
    projectile_progress: float | None


def sample(action_id, elapsed, armed=True):
    """Sample one absolute action time without retaining or mutating state.

    ``approach`` interpolates home (0) to the scene's contact anchor (1).
    ``elevation`` is a positive height above the ground in logical pixels.
    ``pose_ms`` addresses the sprite bank's clock, including Aether Edge's
    original contact frame at 500 ms. ``projectile_progress`` is absent before
    Dart release, then travels from 0 to 1 at the exact model impact boundary.
    Times outside the action are clamped to its first and final samples.
    """
    action = _action(action_id)
    if type(elapsed) not in (int, float):raise TypeError('Choreography time must be numeric')
    if not math.isfinite(elapsed):raise ValueError('Invalid choreography time')
    if type(armed) is not bool:raise TypeError('Choreography armed state must be boolean')
    elapsed = max(0., min(action['duration'], float(elapsed)))
    phase = next((phase for phase in action['phases'] if elapsed < phase['end']),
                 action['phases'][-1])
    local = elapsed-phase['start']
    progress = _clamp(local/(phase['end']-phase['start']))
    # Ease position and framing at each authored foot plant. Elevation follows
    # a separate shallow arc; it never changes the logical ground anchor.
    eased = progress*progress*(3-2*progress)
    reaction = 0.
    if action['impact_at'] <= elapsed and action['reaction_duration']:
        reaction = _clamp(1-(elapsed-action['impact_at'])/action['reaction_duration'])
    release = action['release_at']
    projectile = (None if release is None or elapsed < release else
                  _clamp((elapsed-release)/(action['impact_at']-release)))
    return ChoreographySample(
        action_id=action_id, phase=phase['name'], pose=phase['pose'],
        pose_ms=phase.get('pose_start_ms', 0)+(progress*phase['pose_duration_ms']
                 if 'pose_duration_ms' in phase else local*1000), armed=armed,
        elapsed=elapsed, duration=action['duration'], impact_at=action['impact_at'],
        progress=elapsed/action['duration'], phase_progress=progress,
        impact_progress=_clamp(elapsed/action['impact_at']),
        approach=_mix(phase['approach'], eased),
        elevation=phase['elevation']*math.sin(progress*math.pi),
        target_reaction=reaction, camera_weight=_mix(phase['camera'], eased),
        projectile_progress=projectile)
