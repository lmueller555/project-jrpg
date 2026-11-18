"""Independent, deterministic controller for the Eldenmere well.

This module does not import Game, Pygame or a resident. The live gardener
adapter signals real station arrivals and consumes operation events. Artwork
and actor adapters only read frozen snapshots; drawing cannot advance work or
transfer a pail. DrawingWell owns the live reservation and depth passes.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from hashlib import sha256
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent
CONTRACT_FILE = 'assets/source/terrain/eldenmere/well_hd/mechanism/contract.json'
CONTRACT_PATH = ROOT / CONTRACT_FILE
SCHEMA_VERSION = 1


def _serializable(value):
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_serializable(item) for item in value]
    return value


class _Record:
    def to_dict(self):
        return _serializable(asdict(self))


@dataclass(frozen=True)
class OperationToken:
    """Opaque authority valid only for its issuing controller and operation."""
    operation_id: int
    generation: int
    _controller_key: object = field(repr=False)


@dataclass(frozen=True)
class WellSnapshot(_Record):
    schema_version: int
    operation_id: int | None
    operator_id: str | None
    pail_id: str | None
    phase_id: str
    phase_elapsed_ms: float
    phase_progress: float
    total_elapsed_ms: float
    required_station: str | None
    ready: bool
    crank_turns: float
    crank_phase: float
    crank_direction: int
    crank_sample: int
    bucket_grip_local: tuple[float, float]
    rope_origin_local: tuple[float, float]
    rope_end_local: tuple[float, float]
    rope_length: float
    rope_deployed: bool
    hook_visible: bool
    pail_owner: str
    water_units: int
    bucket_region: str
    water_contact: bool
    bucket_submerged: bool
    mouth_submerged: bool
    completed: bool
    cancelled: bool


@dataclass(frozen=True)
class WellEvent(_Record):
    event_id: tuple[int, str]
    operation_id: int
    cue_id: str
    phase_id: str
    operation_elapsed_ms: float
    bucket_grip_local: tuple[float, float]
    water_units: int
    pail_owner: str


@dataclass(frozen=True)
class RecoveryState(_Record):
    """A recovery description, not a new object or an inventory reward.

    Its stable recovery_id lets an adapter handle an abort/reset description
    once. Resetting the complete ambient task must restore the actor and this
    well atomically; this controller never teleports a suspended pail to a hand.
    """
    recovery_id: tuple[int, str]
    operation_id: int
    operator_id: str
    pail_id: str
    pail_owner: str
    water_units: int
    bucket_grip_local: tuple[float, float]
    bucket_region: str
    crank_turns: float


def load_contract(path: str | Path | None = None) -> dict[str, Any]:
    return json.loads((CONTRACT_PATH if path is None else Path(path)).read_text())


def _point(value):
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(isinstance(item, bool) or not isinstance(item, Real)
                   or not math.isfinite(item) for item in value)):
        raise ValueError('Mechanism positions must be finite logical point pairs')
    return tuple(float(item) for item in value)


class WellMechanism:
    """A gated one-pail operation with one authoritative functional clock.

    reserve() starts an operation but performs no work. signal_ready() opens
    the current loading/operator/retrieval gate. update() consumes only timed
    work and stops at the next gate, discarding unused time. Fractions retain
    ordinary frame intervals such as 1/60 exactly across different partitions.

    abort() releases the operator but retains an attached pail in its real
    recovery location. A new operation cannot replace that unresolved pail;
    coordinated reset is required. A completed, actor-owned pail has already
    left controller ownership and is not handed out again by reset().
    """

    def __init__(self, contract: Mapping[str, Any] | str | Path | None = None):
        if contract is None or isinstance(contract, (str, Path)):
            source = CONTRACT_PATH if contract is None else Path(contract)
            raw = source.read_bytes()
            value = json.loads(raw)
            self._contract_digest = sha256(raw).hexdigest()
        else:
            value = deepcopy(dict(contract))
            raw = (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()
            self._contract_digest = sha256(raw).hexdigest()
        self._validate(value)
        self._contract = value
        self._geometry = value['geometry']
        self._pail = value['pail']
        self._durations = {name: Fraction(duration)
                           for name, duration in value['phase_durations_ms'].items()}
        self._namespace = object()
        self._generation = 0
        self._operation_counter = 0
        self._events: list[WellEvent] = []
        self._clear()

    @staticmethod
    def _validate(value):
        if (value.get('schema_version') != SCHEMA_VERSION
                or value.get('integration_status') != 'staged'
                or value.get('runtime_activation') is not False):
            raise ValueError('Unsupported staged well mechanism contract')
        recipe = ROOT / value['geometry_recipe']
        if sha256(recipe.read_bytes()).hexdigest() != value['geometry_recipe_sha256']:
            raise ValueError('Shared PR1 geometry changed; coordinate both adapters')
        geometry, pail = value['geometry'], value['pail']
        for key in ('rope_origin_local', 'loading_grip_local', 'guided_grip_local',
                    'lowered_grip_local', 'water_plane_local', 'crank_pivot_local',
                    'crank_radii_local', 'hook_rope_offset_logical'):
            _point(geometry[key])
        for key in ('grip_anchor_local', 'support_anchor_local', 'mouth_anchor_local',
                    'base_offset_from_grip', 'mouth_offset_from_grip'):
            _point(pail[key])
        for feature, offset in (('support_anchor_local', 'base_offset_from_grip'),
                                ('mouth_anchor_local', 'mouth_offset_from_grip')):
            derived = tuple(pail[feature][i]-pail['grip_anchor_local'][i] for i in (0, 1))
            if derived != tuple(pail[offset]):
                raise ValueError('Pail contact offsets must derive from named feature anchors')
        if (type(pail['capacity_units']) is not int or pail['capacity_units'] <= 0
                or geometry['rope_units_per_crank_turn'] <= 0
                or geometry['crank_samples'] != 16):
            raise ValueError('Invalid well capacity or winding registration')
        guide = geometry['guided_grip_local'][1]
        low = geometry['lowered_grip_local'][1]
        water = geometry['water_plane_local'][1]
        if guide+pail['base_offset_from_grip'][1] >= water:
            raise ValueError('Guided pail must fully clear the water before shaft entry')
        if low+pail['mouth_offset_from_grip'][1] < water:
            raise ValueError('Filling position must submerge the pail mouth')
        if guide+geometry['hook_rope_offset_logical'][1] < geometry['rope_origin_local'][1]:
            raise ValueError('Hook rope anchor cannot wind through the spindle')
        for name, duration in value['phase_durations_ms'].items():
            if type(duration) is not int or duration <= 0:
                raise ValueError('Timed phases require positive integer milliseconds: '+name)
        order = value['phase_order']
        if len(set(order)) != len(order) or order[-1] != 'complete':
            raise ValueError('Operation phases must be unique and finish at complete')
        for phase, gate in value['readiness_gates'].items():
            if phase not in order or gate['next_phase'] != order[order.index(phase)+1]:
                raise ValueError('Readiness gate must open the following phase')
        if set(order)-set(value['phase_durations_ms'])-set(value['readiness_gates']) != {'complete'}:
            raise ValueError('Every operation phase needs a duration or explicit gate')
        for phase, cues in value['cue_progress'].items():
            if phase not in value['phase_durations_ms']:
                raise ValueError('Cues require a timed phase')
            if any(not 0 < progress <= 1 for progress in cues.values()):
                raise ValueError('Action cues must occur after the gesture begins')

    @property
    def contract(self):
        return deepcopy(self._contract)

    @property
    def contract_sha256(self):
        """Loaded-file digest, or canonical-data digest for an injected mapping."""
        return self._contract_digest

    def _clear(self):
        self._active_token: OperationToken | None = None
        self._operation_id: int | None = None
        self._operator_id: str | None = None
        self._pail_id: str | None = None
        self._phase = 'idle'
        self._elapsed = Fraction(0)
        self._total = Fraction(0)
        self._turns_base = 0.0
        self._water_units = 0
        self._attached = False
        self._contact_recorded = False
        self._mouth_recorded = False
        self._seen_cues: set[str] = set()
        self._recovery: RecoveryState | None = None

    def _current(self, token):
        return (isinstance(token, OperationToken) and self._active_token is not None
                and token._controller_key is self._namespace
                and token == self._active_token)

    def reserve(self, operator_id: str, pail_id: str, *, water_units: int = 0):
        for name, identifier in (('operator', operator_id), ('pail', pail_id)):
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError('A nonempty '+name+' identity is required')
        if type(water_units) is not int or not 0 <= water_units <= self._pail['capacity_units']:
            raise ValueError('Initial water units leave the pail capacity')
        if self._active_token is not None:
            return None
        if self._recovery is not None and self._recovery.pail_owner == 'well':
            return None
        self._clear()
        self._operation_counter += 1
        self._operation_id = self._operation_counter
        self._operator_id, self._pail_id = operator_id, pail_id
        self._water_units = water_units
        token = OperationToken(self._operation_id, self._generation, self._namespace)
        self._active_token = token
        self._phase = self._contract['phase_order'][0]
        return token

    def signal_ready(self, token: OperationToken, station: str):
        if not self._current(token):
            return False
        gate = self._contract['readiness_gates'].get(self._phase)
        if gate is None or gate['station'] != station:
            return False
        self._enter(gate['next_phase'])
        return True

    def _progress(self):
        duration = self._durations.get(self._phase)
        return float(self._elapsed/duration) if duration else (1.0 if self._phase == 'complete' else 0.0)

    def _grip(self):
        if self._phase == 'cancelled' and self._recovery is not None:
            return self._recovery.bucket_grip_local
        motion = self._contract['phase_motion'].get(self._phase)
        if motion:
            first, last = (_point(self._geometry[motion[key]]) for key in ('start', 'end'))
            progress = self._progress()
            return tuple(first[i]+(last[i]-first[i])*progress for i in (0, 1))
        if self._phase == 'fill':
            return _point(self._geometry['lowered_grip_local'])
        return _point(self._geometry['loading_grip_local'])

    def _turns(self):
        if self._phase == 'cancelled' and self._recovery is not None:
            return self._recovery.crank_turns
        motion = self._contract['phase_motion'].get(self._phase)
        turns = self._turns_base
        if motion:
            start = self._geometry[motion['start']][1]
            turns += (self._grip()[1]-start)/self._geometry['rope_units_per_crank_turn']
        return float(round(turns)) if abs(turns-round(turns)) < 1e-12 else turns

    def _region(self):
        if self._phase == 'cancelled' and self._recovery is not None:
            return self._recovery.bucket_region
        if not self._attached:
            return 'actor_held'
        if self._phase in ('lower', 'fill', 'raise'):
            return 'shaft'
        return 'loading_foreground'

    def snapshot(self):
        grip, region, turns = self._grip(), self._region(), self._turns()
        origin = _point(self._geometry['rope_origin_local'])
        offset = _point(self._geometry['hook_rope_offset_logical'])
        endpoint = tuple(grip[i]+offset[i] for i in (0, 1))
        water_y = self._geometry['water_plane_local'][1]
        base_y = grip[1]+self._pail['base_offset_from_grip'][1]
        mouth_y = grip[1]+self._pail['mouth_offset_from_grip'][1]
        in_shaft = region == 'shaft' and self._attached
        water_units = self._water_units
        if self._phase == 'fill':
            water_units += math.floor((self._pail['capacity_units']-water_units)*self._progress()+1e-12)
        if self._recovery is not None and self._phase == 'cancelled':
            water_units = self._recovery.water_units
        direction = 0
        if self._phase in self._contract['phase_motion'] and self._active_token is not None:
            motion = self._contract['phase_motion'][self._phase]
            delta = self._geometry[motion['end']][1]-self._geometry[motion['start']][1]
            direction = 1 if delta > 0 else -1 if delta < 0 else 0
        phase = turns % 1.0
        if phase > 1-1e-12:
            phase = 0.0
        gate = self._contract['readiness_gates'].get(self._phase)
        return WellSnapshot(
            SCHEMA_VERSION, self._operation_id, self._operator_id, self._pail_id,
            self._phase, float(self._elapsed), self._progress(), float(self._total),
            gate['station'] if gate else None,
            self._active_token is not None and gate is None,
            turns, phase, direction, int(math.floor(phase*self._geometry['crank_samples']+1e-10)) % self._geometry['crank_samples'],
            grip, origin, endpoint, math.dist(origin, endpoint), True, True,
            'well' if self._attached else 'actor', water_units, region,
            in_shaft and base_y >= water_y-1e-10,
            in_shaft and base_y > water_y+1e-10,
            in_shaft and mouth_y >= water_y-1e-10,
            self._phase == 'complete', self._phase == 'cancelled')

    def _emit(self, cue_id):
        if cue_id in self._seen_cues or self._operation_id is None:
            return
        self._seen_cues.add(cue_id)
        current = self.snapshot()
        self._events.append(WellEvent(
            (self._operation_id, cue_id), self._operation_id, cue_id,
            self._phase, float(self._total), current.bucket_grip_local,
            current.water_units, current.pail_owner))

    def _enter(self, phase):
        self._turns_base = self._turns()
        self._phase, self._elapsed = phase, Fraction(0)
        if phase == 'complete':
            self._active_token = None
            self._emit('completed')

    def _cues(self):
        duration = self._durations[self._phase]
        result = [(duration*Fraction(str(progress)), name)
                  for name, progress in self._contract['cue_progress'].get(self._phase, {}).items()]
        if self._phase in ('lower', 'raise'):
            motion = self._contract['phase_motion'][self._phase]
            start = Fraction(str(self._geometry[motion['start']][1]))
            finish = Fraction(str(self._geometry[motion['end']][1]))
            water = Fraction(str(self._geometry['water_plane_local'][1]))
            names = (('water_contact', 'base_offset_from_grip'),
                     ('mouth_submerged', 'mouth_offset_from_grip')) if self._phase == 'lower' else (('water_exit', 'base_offset_from_grip'),)
            for name, offset in names:
                target = water-Fraction(str(self._pail[offset][1]))
                progress = (target-start)/(finish-start)
                if not 0 <= progress <= 1:
                    raise ValueError('Contact feature never reaches its declared water plane')
                result.append((duration*progress, name))
        if self._phase == 'fill':
            result.append((duration, 'fill_complete'))
        return sorted(result)

    def _perform_cue(self, name):
        if name == 'attached':
            self._attached = True
        elif name == 'detached':
            self._attached = False
        elif name == 'water_contact':
            self._contact_recorded = True
        elif name == 'mouth_submerged':
            self._mouth_recorded = True
        elif name == 'fill_complete':
            if not self._contact_recorded or not self._mouth_recorded or not self.snapshot().mouth_submerged:
                raise RuntimeError('Water cannot fill without the mouth reaching the water surface')
            self._water_units = self._pail['capacity_units']
        self._emit(name)

    def update(self, seconds: float):
        try:
            valid = (not isinstance(seconds, bool) and isinstance(seconds, Real)
                     and math.isfinite(seconds) and seconds >= 0)
        except (OverflowError, TypeError):
            valid = False
        if not valid:
            raise ValueError('Well time must be a finite nonnegative number')
        remaining = Fraction(str(seconds)).limit_denominator(1_000_000_000)*1000
        while remaining > 0 and self._active_token is not None and self._phase in self._durations:
            duration = self._durations[self._phase]
            cues = [(time, name) for time, name in self._cues()
                    if name not in self._seen_cues and time >= self._elapsed]
            target = min(self._elapsed+remaining, duration, *(time for time, _ in cues))
            consumed = target-self._elapsed
            self._elapsed = target
            self._total += consumed
            remaining -= consumed
            for time, name in cues:
                if time == self._elapsed:
                    self._perform_cue(name)
            if self._elapsed == duration:
                phases = self._contract['phase_order']
                self._enter(phases[phases.index(self._phase)+1])
        return self.snapshot()

    def drain_events(self):
        result = tuple(self._events)
        self._events.clear()
        return result

    def _recovery_state(self):
        if self._operation_id is None or self._phase == 'complete':
            return None
        current = self.snapshot()
        return RecoveryState(
            (self._operation_id, 'recovery'), self._operation_id,
            self._operator_id, self._pail_id, current.pail_owner,
            current.water_units, current.bucket_grip_local,
            current.bucket_region, current.crank_turns)

    def abort(self, token):
        if not self._current(token):
            return None
        recovery = self._recovery_state()
        self._recovery = recovery
        self._water_units = recovery.water_units
        self._active_token = None
        self._phase, self._elapsed = 'cancelled', Fraction(0)
        self._emit('cancelled')
        return recovery

    def reset(self):
        recovery = self._recovery if self._phase == 'cancelled' else self._recovery_state()
        self._generation += 1
        self._events.clear()
        self._clear()
        return recovery
