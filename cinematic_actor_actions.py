"""Small transient entry/hold/recovery clips for scene-owned actor drawings.

Clips are immutable descriptions. Each player owns its own clock and cue history;
selecting a frame never advances playback or changes a source surface.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sys


def _name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a nonempty string')
    return value


def _duration(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError('Action durations must be positive finite milliseconds')
    return float(value)


@dataclass(frozen=True)
class ActionFrame:
    image: object
    duration_ms: float


@dataclass(frozen=True)
class ActionClip:
    entry: tuple[ActionFrame, ...]
    hold_image: object
    hold_duration_ms: float | None
    recovery: tuple[ActionFrame, ...]
    rest_image: object


def load_actions(record, poses, manifest_path, image_loader=None):
    """Validate optional manifest clips using already-loaded static pose images.

File references are local PNGs confined to the actor manifest directory, even
through symlinks. Pose references reuse their existing surfaces without edits.
Manifests without ``actions`` preserve the legacy loading path unchanged.
"""
    if 'actions' not in record:
        return {}
    actions = record['actions']
    if not isinstance(actions, dict):
        raise ValueError('Actor actions must be an object')
    if not actions:
        return {}
    canvas = record.get('canvas')
    if (not isinstance(canvas, (list, tuple)) or len(canvas) != 2
            or any(type(value) is not int or value <= 0 for value in canvas)):
        raise ValueError('Action actor canvas must contain two positive integers')
    canvas = tuple(canvas)
    root = Path(manifest_path).resolve().parent
    files = {}

    def image(reference):
        selector = set(reference) - {'duration_ms'}
        if selector == {'pose'}:
            name = _name(reference['pose'], 'Action pose')
            if name not in poses:
                raise ValueError('Unknown action pose: ' + name)
            result = poses[name]
        elif selector == {'file'}:
            name = _name(reference['file'], 'Action frame filename')
            relative = Path(name)
            if (relative.is_absolute() or '..' in relative.parts
                    or any(character in name for character in ('\\', ':', '\x00'))
                    or relative.suffix.lower() != '.png'):
                raise ValueError('Action frame must be a local relative PNG')
            try:
                path = (root / relative).resolve()
            except (OSError, RuntimeError) as error:
                raise ValueError('Action frame path could not be resolved') from error
            if not path.is_relative_to(root):
                raise ValueError('Action frame leaves its actor folder')
            if path not in files:
                try:
                    if image_loader is None:
                        import pygame
                        files[path] = pygame.image.load(str(path))
                    else:
                        files[path] = image_loader(path)
                except (OSError, ValueError) as error:
                    raise ValueError('Action frame could not be loaded: ' + name) from error
            result = files[path]
        else:
            raise ValueError('Action frame needs exactly one pose or file reference')
        if not hasattr(result, 'get_size') or result.get_size() != canvas:
            raise ValueError('Action frames must match the actor canvas')
        return result

    def sequence(value):
        if not isinstance(value, list) or not value:
            raise ValueError('Action entry and recovery must be nonempty frame lists')
        result = []
        for reference in value:
            if not isinstance(reference, dict) or 'duration_ms' not in reference:
                raise ValueError('Action frame needs a timed reference')
            result.append(ActionFrame(image(reference), _duration(reference['duration_ms'])))
        if not math.isfinite(sum(frame.duration_ms for frame in result)):
            raise ValueError('Action segment duration must be finite')
        return tuple(result)

    loaded = {}
    for name, action in actions.items():
        _name(name, 'Action name')
        if not isinstance(action, dict) or set(action) != {'entry', 'hold', 'recovery', 'rest_pose'}:
            raise ValueError('Action needs entry, hold, recovery and rest_pose')
        entry = sequence(action['entry'])
        recovery = sequence(action['recovery'])
        hold = action['hold']
        if not isinstance(hold, dict) or 'duration_ms' not in hold:
            raise ValueError('Action hold needs one pose/file and duration_ms')
        hold_image = image(hold)
        hold_duration = None if hold['duration_ms'] is None else _duration(hold['duration_ms'])
        rest = _name(action['rest_pose'], 'Action rest pose')
        if rest not in poses:
            raise ValueError('Unknown action rest pose: ' + rest)
        rest_image = image({'pose': rest})
        total = sum(frame.duration_ms for frame in (*entry, *recovery)) + (hold_duration or 0.)
        if not math.isfinite(total):
            raise ValueError('Action duration must be finite')
        loaded[name] = ActionClip(entry, hold_image, hold_duration, recovery, rest_image)
    return loaded


def idle_state():
    return {'stage': 'idle', 'action': None, 'cue_id': None, 'frame_index': None,
            'elapsed_ms': 0., 'release_requested': False, 'active': False}


class ActionPlayer:
    """One actor's local clip clock; no queues, rendering mutations or receipts."""
    def __init__(self, clips):
        self.clips = dict(clips)
        if any(not isinstance(clip, ActionClip) for clip in self.clips.values()):
            raise ValueError('ActionPlayer requires validated action clips')
        self.clear()

    def clear(self):
        self._seen = set()
        self._stage = 'idle'
        self._action = self._cue_id = self._clip = None
        self._index = 0
        self._elapsed = 0.
        self._release = False

    @property
    def stage(self):return self._stage

    @property
    def cue_id(self):return self._cue_id

    @property
    def active(self):return self._stage in ('entry', 'hold', 'recovery')

    @property
    def frame(self):
        if self._stage == 'idle':return None
        if self._stage == 'entry':return self._clip.entry[self._index].image
        if self._stage == 'hold':return self._clip.hold_image
        if self._stage == 'recovery':return self._clip.recovery[self._index].image
        return self._clip.rest_image

    @property
    def state(self):
        if self._stage == 'idle':return idle_state()
        elapsed = self._elapsed
        if self._stage in ('entry', 'recovery'):
            frames = getattr(self._clip, self._stage)
            elapsed += sum(frame.duration_ms for frame in frames[:self._index])
        return {'stage': self._stage, 'action': self._action, 'cue_id': self._cue_id,
                'frame_index': self._index if self._stage in ('entry', 'recovery') else None,
                'elapsed_ms': elapsed, 'release_requested': self._release, 'active': self.active}

    def play(self, name, cue_id):
        _name(name, 'Action name')
        _name(cue_id, 'Action cue ID')
        if name not in self.clips:raise ValueError('Unknown actor action: ' + name)
        if cue_id in self._seen or self.active:return False
        self._seen.add(cue_id)
        self._action, self._cue_id, self._clip = name, cue_id, self.clips[name]
        self._stage, self._index, self._elapsed, self._release = 'entry', 0, 0., False
        return True

    def release(self, cue_id=None):
        if cue_id is not None:_name(cue_id, 'Action cue ID')
        if (self._stage not in ('entry', 'hold') or self._release
                or (cue_id is not None and cue_id != self._cue_id)):
            return False
        self._release = True
        if self._stage == 'hold':
            self._stage, self._index, self._elapsed = 'recovery', 0, 0.
        return True

    def update(self, seconds):
        try:
            valid = type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('Action update needs nonnegative finite seconds')
        remaining = seconds * 1000
        if not math.isfinite(remaining):raise ValueError('Action update milliseconds overflow')
        while self.active and remaining > 0:
            if self._stage == 'hold':
                duration = self._clip.hold_duration_ms
                if duration is None:
                    self._elapsed = min(self._elapsed + remaining, sys.float_info.max)
                    return
            else:
                duration = getattr(self._clip, self._stage)[self._index].duration_ms
            needed = duration - self._elapsed
            # Subtracting adjacent scene timestamps can leave an exact nominal
            # boundary a few floating-point steps short. Scale tolerance only
            # to representation error, so genuinely early samples stay put.
            at_boundary = math.isclose(remaining, needed, rel_tol=0.,
                                       abs_tol=8 * math.ulp(duration))
            if remaining < needed and not at_boundary:
                self._elapsed += remaining
                return
            remaining = max(0., remaining - needed)
            self._elapsed = 0.
            if self._stage == 'hold':
                self._stage, self._index = 'recovery', 0
            else:
                frames = getattr(self._clip, self._stage)
                if self._index + 1 < len(frames):self._index += 1
                elif self._stage == 'entry':
                    self._stage, self._index = ('recovery' if self._release else 'hold'), 0
                else:self._stage, self._index = 'rest', 0
