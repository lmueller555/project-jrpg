"""Foot-driven, nonblocking grass animation for authored game environments.

The field owns vegetation state and independent rear/front scenery records.
It never changes an actor, collision, movement speed, or a world save.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

import pygame


DIRECTIONS = ('north', 'east', 'south', 'west')
_FACING = {'back': 'north', 'right': 'east', 'front': 'south', 'left': 'west'}
_EPSILON = 1e-7


def movement_direction(delta, fallback='south'):
    """Resolve travel direction; standing does not change an existing direction."""
    if abs(delta[0]) > abs(delta[1]):return 'east' if delta[0] > 0 else 'west'
    if abs(delta[1]) > _EPSILON:return 'south' if delta[1] > 0 else 'north'
    return fallback


def _approach(value, target, maximum):
    if value < target:return min(target, value+maximum)
    return max(target, value-maximum)


@dataclass
class GrassClump:
    identifier: str
    position: tuple[float, float]
    variant: str
    phase_ms: float = 0.
    strength: float = 0.
    target_strength: float = 0.
    direction: str = 'south'
    occupants: set = field(default_factory=set)
    activations: int = 0
    release_age: float = 0.
    state: str = 'idle'


class InteractiveGrass:
    """Animate authored clumps from actual actor-foot occupancy and movement.

    ``image`` is the world's cached image loader. The supplied manifest contains
    native frames with the same root anchor; drawing always keeps that anchor
    fixed. Grass remains ordinary depth-sorted scenery, never a blocker.
    """
    PART_SPEED = 12.0
    RECOVER_SPEED = 3.2
    TRANSIT_HOLD_SECONDS = .10

    def __init__(self, manifest, instances, image):
        data = manifest['tall_grass']
        self.anchor = tuple(data['anchor'])
        self.frame_size = tuple(data['frame_size'])
        self.contact_rect = tuple(data['contact_rect'])
        self.variants = {}
        for identifier, variant in data['variants'].items():
            idle = variant['idle']
            if not idle or any(record['duration_ms'] <= 0 for record in idle):
                raise ValueError('Tall grass requires positive idle-frame timing')
            parted = variant['parted']
            if set(parted) != set(DIRECTIONS) or any(len(parted[key]) != 3 for key in DIRECTIONS):
                raise ValueError('Tall grass requires three poses in all four directions')
            def loaded(record):
                surfaces = (image(record['rear']), image(record['front']))
                if any(surface.get_size() != self.frame_size for surface in surfaces):
                    raise ValueError('Tall-grass frames must share the native canvas')
                return surfaces
            self.variants[identifier] = {
                'idle': [(loaded(record), record['duration_ms']) for record in idle],
                'parted': {key: [loaded(record) for record in parted[key]] for key in DIRECTIONS}}
        self.clumps = []
        self.entity_records = []
        self._records = {}
        seen = set()
        for instance in instances:
            identifier = instance['id']
            if identifier in seen:raise ValueError('Duplicate tall-grass instance')
            seen.add(identifier)
            if instance['variant'] not in self.variants:raise ValueError('Unknown tall-grass variant')
            clump = GrassClump(identifier, tuple(instance['position']), instance['variant'],
                               float(instance.get('phase_ms', 0)))
            self.clumps.append(clump)
            position = (round(clump.position[0]-self.anchor[0]),
                        round(clump.position[1]-self.anchor[1]))
            rear, front = self._surfaces(clump)
            records = []
            # Rear stems precede actors on the patch; foreground blade tips
            # overlap boots/legs. An actor well south of a clump draws in front.
            for layer, surface, baseline in (('rear', rear, clump.position[1]-16),
                                              ('front', front, clump.position[1]+6)):
                record = {'id': 'grass.'+identifier+'.'+layer, 'position': position,
                          'sort_y': baseline, 'sort_priority': 4 if layer == 'front' else -1,
                          'surfaces': [surface], 'rect': surface.get_rect(topleft=position),
                          'frame_duration_ms': 1000, 'phase_offset': 0,
                          'animation_stopped': True, 'grass_layer': layer,
                          'grass_instance': identifier}
                records.append(record)
                self.entity_records.append(record)
            self._records[identifier] = records
        self.elapsed_ms = 0.
        self.enabled = True
        self.reduced_motion = False
        self._previous_positions = {}

    def reset(self, *, reduced_motion=False):
        """Discard journey-local contact without rebuilding cached scenery."""
        self.elapsed_ms = 0.
        self.reduced_motion = bool(reduced_motion)
        self._previous_positions.clear()
        for clump in self.clumps:
            clump.strength = clump.target_strength = 0.
            clump.direction = 'south'
            clump.occupants.clear()
            clump.activations = 0
            clump.release_age = 0.
            clump.state = 'idle'
            for record, surface in zip(self._records[clump.identifier], self._surfaces(clump)):
                record['surfaces'] = [surface]

    def _surfaces(self, clump):
        variant = self.variants[clump.variant]
        if clump.strength > _EPSILON:
            pose = min(2, max(0, math.floor(clump.strength+.5)))
            return variant['parted'][clump.direction][pose]
        frames = variant['idle']
        duration = sum(length for _, length in frames)
        clock = (getattr(self, 'elapsed_ms', 0)+clump.phase_ms) % duration
        if getattr(self, 'reduced_motion', False):clock = clump.phase_ms % duration
        for surfaces, length in frames:
            if clock < length:return surfaces
            clock -= length
        return frames[-1][0]

    def _contact(self, clump):
        x, y, width, height = self.contact_rect
        return pygame.Rect(round(clump.position[0]+x), round(clump.position[1]+y), width, height)

    @staticmethod
    def _actor_key(actor):
        # Object identity avoids collisions between NPC aliases or party names.
        return id(actor)

    @staticmethod
    def _feet(actor):
        size = tuple(getattr(actor, 'probe_size', (24, 12)))
        position = pygame.Vector2(getattr(actor, 'story_position', None) or actor.position)
        rect = pygame.Rect(0, 0, *size)
        rect.center = round(position.x), round(position.y)
        return position, rect, size

    def update(self, seconds, actors=(), *, reduced_motion=False):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Grass time must be finite and nonnegative')
        self.reduced_motion = bool(reduced_motion)
        if not self.reduced_motion:self.elapsed_ms += seconds*1000
        actor_records = []
        current_positions = {}
        for actor in actors:
            if not getattr(actor, 'story_visible', True):continue
            key = self._actor_key(actor)
            if key in current_positions:continue
            position, feet, size = self._feet(actor)
            previous = self._previous_positions.get(key, position)
            delta = position-previous
            direction = movement_direction(delta, _FACING.get(getattr(actor, 'facing', 'front'), 'south'))
            current_positions[key] = position.copy()
            actor_records.append((key, position, previous, delta, feet, size, direction,
                                  2. if getattr(actor, 'running', False) else 1.))
        for clump in self.clumps:
            contact = self._contact(clump)
            occupants = set()
            moving_pressure = []
            transient = []
            for key, position, previous, delta, feet, size, direction, strength in actor_records:
                inside = contact.colliderect(feet)
                swept = False
                if delta.length_squared() > _EPSILON:
                    expanded = contact.inflate(size[0], size[1])
                    swept = bool(expanded.clipline(previous, position))
                if inside:
                    occupants.add(key)
                    if delta.length_squared() > _EPSILON or not clump.occupants:
                        moving_pressure.append((strength, direction))
                elif swept:transient.append((strength, direction))
            if occupants and not clump.occupants:clump.activations += 1
            if not occupants and transient and not clump.occupants:clump.activations += 1
            clump.occupants = occupants
            if moving_pressure or transient:
                strength, direction = max(moving_pressure+transient, key=lambda item: item[0])
                clump.direction = direction
                clump.target_strength = max(1., strength) if occupants else strength
                clump.release_age = 0.
            elif occupants:
                clump.target_strength = 1.
                clump.release_age = 0.
            else:
                clump.release_age += seconds
                if clump.release_age >= self.TRANSIT_HOLD_SECONDS:
                    clump.target_strength = 0.
            if self.reduced_motion:
                clump.strength = 1. if occupants or transient else 0.
            else:
                rate = self.PART_SPEED if clump.target_strength > clump.strength else self.RECOVER_SPEED
                clump.strength = _approach(clump.strength, clump.target_strength, rate*seconds)
            if occupants:clump.state = 'occupied'
            elif clump.strength > _EPSILON:clump.state = 'recovering'
            else:clump.state = 'idle'
            surfaces = self._surfaces(clump)
            for record, surface in zip(self._records[clump.identifier], surfaces):
                record['surfaces'] = [surface]
        self._previous_positions = current_positions

    def snapshot(self):
        """Detached JSON-friendly observation for previews and capture checks."""
        return {'elapsed_ms': self.elapsed_ms, 'enabled': self.enabled,
                'reduced_motion': self.reduced_motion,
                'clumps': [{'id': c.identifier, 'position': list(c.position),
                            'variant': c.variant, 'direction': c.direction,
                            'strength': c.strength, 'target_strength': c.target_strength,
                            'occupants': len(c.occupants), 'activations': c.activations,
                            'release_age': c.release_age, 'state': c.state}
                           for c in self.clumps]}
