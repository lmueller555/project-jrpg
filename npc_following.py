"""Transient direction smoothing for quest companions' actual movement.

Navigation may consume several tiny waypoints in one update. Choose one facing
from that update's net travel, then require a stable turn and a brief hold. This
only changes the rendered direction; paths, positions and walk clocks stay with
the quest controller. Explicit conversation and action poses remain immediate.
"""
from contextlib import contextmanager
from dataclasses import dataclass

import pygame


TURN_INTERVAL = .20
TURN_CONFIRMATION = .07
AXIS_HYSTERESIS = 1.25
MOVEMENT_DEADZONE = .05
RESET_DISTANCE = 24
IDLE_RESET = .35


@dataclass
class _FacingState:
    facing: str
    position: pygame.Vector2
    elapsed: float = 0.0
    candidate: str | None = None
    candidate_elapsed: float = 0.0
    idle_elapsed: float = 0.0


def reset_following_facing(actor):
    """Forget a companion's visual turn history after stopping or relocation."""
    if hasattr(actor, '_following_facing'):
        del actor._following_facing


def _direction(delta, current):
    x, y = delta
    horizontal = abs(x) > abs(y)
    # A near-diagonal path keeps its present axis instead of flickering between
    # the horizontal and vertical sprites as grid waypoints alternate.
    if current in ('left', 'right') and abs(x)*AXIS_HYSTERESIS >= abs(y):
        horizontal = True
    elif current in ('front', 'back') and abs(y)*AXIS_HYSTERESIS >= abs(x):
        horizontal = False
    return ('right' if x > 0 else 'left') if horizontal else ('front' if y > 0 else 'back')


def _apply(actor, before, previous, seconds):
    state = getattr(actor, '_following_facing', None)
    delta = pygame.Vector2(actor.position)-before
    if (state is not None and (state.facing != previous or
                               state.position.distance_to(before) > RESET_DISTANCE)):
        state = None
    # Zero simulation time must not turn a paused actor, even if a caller is
    # aligning a position outside its ordinary navigation loop.
    if seconds <= 0:
        actor.facing = previous
        return
    if delta.length_squared() <= MOVEMENT_DEADZONE**2:
        actor.facing = previous
        if state is not None:
            state.position.update(actor.position)
            state.elapsed += seconds
            state.idle_elapsed += seconds
            if state.idle_elapsed >= IDLE_RESET:
                reset_following_facing(actor)
        return
    desired = _direction(delta, previous if state is not None else None)
    if state is None:
        actor.facing = desired
        actor._following_facing = _FacingState(desired, pygame.Vector2(actor.position))
        return
    state.elapsed += seconds
    state.idle_elapsed = 0.0
    if desired == state.facing:
        state.candidate = None
        state.candidate_elapsed = 0.0
    else:
        if desired != state.candidate:
            state.candidate = desired
            state.candidate_elapsed = 0.0
        state.candidate_elapsed += seconds
        if (state.elapsed+1e-9 >= TURN_INTERVAL and
                state.candidate_elapsed+1e-9 >= TURN_CONFIRMATION):
            state.facing = desired
            state.elapsed = 0.0
            state.candidate = None
            state.candidate_elapsed = 0.0
    state.position.update(actor.position)
    actor._following_facing = state
    actor.facing = state.facing


@contextmanager
def following_facing(actor, seconds):
    """Wrap one movement update, including early navigation returns.

    The controller may keep its ordinary per-waypoint facing assignments. They
    are replaced before drawing with a single stable result for followers.
    Other NPCs retain their existing movement and facing behavior.
    """
    if not getattr(actor, 'story_following', False):
        reset_following_facing(actor)
        yield
        return
    before = pygame.Vector2(actor.position)
    previous = actor.facing
    try:
        yield
    finally:
        if getattr(actor, 'story_following', False):
            _apply(actor, before, previous, max(0.0, seconds))
        else:
            reset_following_facing(actor)


def idle_following_facing(actor, seconds):
    """Advance a stopped follower's turn clock without erasing brief stops."""
    with following_facing(actor, seconds):
        pass
