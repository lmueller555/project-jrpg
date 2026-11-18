"""A brief, clock-driven curtain between exploration and a battle view."""
from __future__ import annotations

import math

import pygame


SHADE = (7, 18, 17)


def _ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


class BattleTransition:
    """Freeze a real world frame, close a dark curtain, then reveal battle.

    The transition owns no game clocks and never updates the battlefield.
    Reduced Motion replaces the moving curtain with a short plain fade.
    """

    def __init__(self, world_frame, *, reduced_motion=False):
        if not isinstance(world_frame, pygame.Surface):
            raise TypeError('A world frame is required for battle entry')
        self.world_frame = world_frame.copy()
        self.reduced_motion = bool(reduced_motion)
        self.close_seconds = .11 if self.reduced_motion else .34
        self.hold_seconds = .025 if self.reduced_motion else .08
        self.reveal_seconds = .125 if self.reduced_motion else .30
        self.duration = self.close_seconds + self.hold_seconds + self.reveal_seconds
        self.elapsed = 0.0
        self._veil = None

    @property
    def active(self):
        return self.elapsed < self.duration

    @property
    def phase(self):
        if self.elapsed < self.close_seconds:return 'closing'
        if self.elapsed < self.close_seconds + self.hold_seconds:return 'covered'
        return 'revealing' if self.active else 'complete'

    def update(self, seconds, *, paused=False):
        if type(seconds) not in (int, float):
            raise TypeError('Transition time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Transition time must be finite and nonnegative')
        if not paused:self.elapsed = min(self.duration, self.elapsed + seconds)

    def draw(self, target):
        """Apply the curtain over a freshly rendered battle-sized target."""
        if not self.active:return
        width, height = target.get_size()
        if self._veil is None or self._veil.get_size() != target.get_size():
            self._veil = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        veil = self._veil
        if self.phase == 'closing':
            pygame.transform.scale(self.world_frame, target.get_size(), target)
            progress = _ease(self.elapsed / self.close_seconds)
            if progress <= 0:return
            if self.reduced_motion:
                veil.fill((*SHADE, round(255 * progress)))
                target.blit(veil, (0, 0))
            else:
                # x+y = distance sweeps a single solid curtain across the world.
                # There are no flashes, zooms or independent moving fragments.
                distance = (width + height) * progress
                points = [(0, 0), (min(width, distance), max(0, distance-width)),
                          (max(0, distance-height), min(height, distance))]
                if distance > width and distance > height:
                    points = [(0, 0), (width, 0), (width, distance-width),
                              (distance-height, height), (0, height)]
                elif distance > width:
                    points = [(0, 0), (width, 0), (width, distance-width),
                              (0, distance)]
                elif distance > height:
                    points = [(0, 0), (distance, 0), (distance-height, height),
                              (0, height)]
                pygame.draw.polygon(target, SHADE, points)
        elif self.phase == 'covered':
            target.fill(SHADE)
        else:
            progress = _ease((self.elapsed-self.close_seconds-self.hold_seconds)
                             / self.reveal_seconds)
            veil.fill((*SHADE, round(255 * (1-progress))))
            target.blit(veil, (0, 0))
