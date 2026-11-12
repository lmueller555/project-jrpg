"""Authored, finite movement tracks for the Sanctuary emergency arrival.

The scene deliberately reserves walking lanes and departure gaps. A pixel-sized
sweep prevents transient overlap if a frame spans a corner; a stuck track raises
an authoring error instead of silently holding an unread scene forever.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from npc_routines import find_path
from social import facing_toward


SPEED = 76.0
PRINCIPALS = ('caelan', 'mira', 'lucan', 'aldric', 'page')


def feet(actor, position=None):
    position = actor.position if position is None else position
    width, height = actor.probe_size
    return pygame.Rect(round(position[0])-width//2,
                       round(position[1])-height//2, width, height)


@dataclass
class _Track:
    delay: float = 0.
    after: tuple = ()
    started: bool = False
    finished: bool = False
    blocked: float = 0.


class SanctuaryBlocking:
    def __init__(self, world, actors, manifest):
        self.world = world
        self.actors = actors
        self.manifest = manifest
        self.beat = 0
        self.elapsed = 0.
        self.tracks = {}

    def _route(self, key, points):
        actor = self.actors[key]
        origin = pygame.Vector2(actor.position)
        route = []
        if len(points) == 2 and all(isinstance(v, (int, float)) for v in points):
            points = [points]
        for point in points:
            if origin.distance_to(point) < .01:continue
            path = find_path(self.world, origin, point, actor.probe_size, None)
            if path is None:
                raise ValueError(f'Blocked Sanctuary track: {key}: {tuple(origin)} -> {point}')
            route.extend(path)
            origin.update(point)
        actor.route = route
        return bool(route)

    def begin(self, beat, initial=False):
        """Rebuild one acknowledged beat from its authored start stations."""
        self.beat = beat
        self.elapsed = 0.
        self.tracks = {}
        for actor in self.actors.values():
            actor.route = []
            actor.moving = False
        movements = self.manifest['beats'][beat].get('movement', {})
        for key, record in movements.items():
            after = record.get('start_after', ())
            if isinstance(after, str):after = (after,)
            active = self._route(key, record['waypoints'])
            self.tracks[key] = _Track(float(record.get('delay', 0.)), tuple(after), finished=not active)
        self._validate_stations()

    # An explicit alias is convenient for callers using the scene's beat name.
    setbeat = begin

    def _validate_stations(self):
        values = list(self.actors.items())
        for index, (key, actor) in enumerate(values):
            if not self.world.can_stand(actor.position, actor.probe_size):
                raise ValueError(f'Blocked Sanctuary station: {key}: {tuple(actor.position)}')
            for other_key, other in values[index+1:]:
                if feet(actor).colliderect(feet(other)):
                    raise ValueError(f'Overlapping Sanctuary stations: {key} / {other_key}')

    def move_actor(self, key, points, *, delay=0., start_after=()):
        """Use the same checked lanes for a late rope-operation step."""
        if isinstance(start_after, str):start_after = (start_after,)
        active = self._route(key, points)
        self.tracks[key] = _Track(self.elapsed+float(delay), tuple(start_after), finished=not active)
        return active

    def started(self, key):
        record = self.tracks.get(key)
        return record is None or record.started

    def busy(self, key):
        record = self.tracks.get(key)
        return record is not None and not record.finished

    @property
    def settled(self):
        # The runner completes one finite delivery while the principal scene
        # proceeds; she never gates the first conversation or begins a loop.
        return all(record.finished for key, record in self.tracks.items() if key != 'runner')

    def initial_camera(self):
        """A focus for anchor (.5,.35), keeping the moving column on screen."""
        if self.beat or all(not self.busy(key) for key in PRINCIPALS):return None
        positions = [self.actors[key].position for key in PRINCIPALS]
        return ((min(p.x for p in positions)+max(p.x for p in positions))/2,
                min(p.y for p in positions)+64)

    def update(self, seconds):
        seconds = max(0., float(seconds))
        if not math.isfinite(seconds):raise ValueError('Invalid Sanctuary movement delta')
        for actor in self.actors.values():actor.moving = False
        remaining = seconds
        # At most one world pixel per step, independent of rendered framerate.
        while remaining > 1e-9:
            step = min(remaining, 1/SPEED)
            remaining -= step
            self.elapsed += step
            for key, record in self.tracks.items():
                if record.finished or self.elapsed+1e-9 < record.delay:continue
                if any(self.busy(other) for other in record.after):continue
                record.started = True
                actor = self.actors[key]
                budget = step*SPEED
                while actor.route and budget > 1e-9:
                    delta = pygame.Vector2(actor.route[0])-actor.position
                    distance = delta.length()
                    if distance < 1e-7:
                        actor.position.update(actor.route.pop(0))
                        continue
                    travel = min(budget, distance, 1.)
                    candidate = actor.position+delta*(travel/distance)
                    if not self.world.can_stand(candidate, actor.probe_size):
                        raise ValueError(f'Sanctuary track crossed terrain: {key}: {tuple(candidate)}')
                    occupied = next((other_key for other_key, other in self.actors.items()
                                     if other_key != key and feet(actor, candidate).colliderect(feet(other))), None)
                    if occupied is not None:
                        record.blocked += step
                        if record.blocked > 2.:
                            raise ValueError(f'Stalled Sanctuary track: {key} behind {occupied} at {tuple(actor.position)}')
                        break
                    actor.position.update(candidate)
                    actor.facing = facing_toward(delta)
                    actor.walk_ms += travel/SPEED*1000
                    actor.moving = True
                    budget -= travel
                    record.blocked = 0.
                if not actor.route:record.finished = True
