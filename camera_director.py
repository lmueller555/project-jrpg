"""Pixel-aligned, eased player tracking throughout live world conversations.

Dialogue never chooses a shot or reserves part of the world for a text panel.
Only the final rendered position is rounded to native pixels.
"""
from __future__ import annotations

import math


VIEW_SIZE = (480, 320)
EASE_RATE = 16.0


class CameraDirector:
    """Track a world while retaining the scene's intended composition.

    Room transfers are intentional cuts. Within a room, exponential easing has
    no overshoot and gives the same result for any partition of a fixed time
    interval. Most focus changes settle in about a third of a second.
    """

    def __init__(self, game):
        self.game = game
        self._world = None
        self._point = None
        self._target_point = None
        self._frame_height = float(VIEW_SIZE[1])
        self._target_height = float(VIEW_SIZE[1])

    @staticmethod
    def _axis(value, world_size, view_size):
        if world_size < view_size:
            return (world_size-view_size)/2
        return max(0.0, min(world_size-view_size, value))

    def _bounded(self, point, height):
        width, world_height = self.game.world.size
        return (self._axis(point[0], width, VIEW_SIZE[0]),
                self._axis(point[1], world_height, height))

    @staticmethod
    def _position_of(actor):
        return getattr(actor, 'story_position', None) or actor.position

    def _desired(self):
        point = self._position_of(self.game.player)
        return self._bounded((point[0]-240, point[1]-160), VIEW_SIZE[1]), VIEW_SIZE[1]

    def reset(self):
        """Establish one shot after a new journey or an intentional room cut."""
        self._world = self.game.world
        self._point = None
        target, height = self._desired()
        self._point = tuple(float(value) for value in target)
        self._target_point = self._point
        self._frame_height = self._target_height = float(height)

    def update(self, seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Camera update seconds must be finite and nonnegative')
        if self._world is not self.game.world or self._point is None:
            self.reset()
            return
        target, height = self._desired()
        self._target_point = tuple(float(value) for value in target)
        self._target_height = float(height)
        blend = -math.expm1(-EASE_RATE*seconds)
        self._point = tuple(current+(goal-current)*blend
                            for current, goal in zip(self._point, self._target_point))
        self._frame_height += (self._target_height-self._frame_height)*blend
        # Keep short rooms centered and larger rooms bounded while tracking.
        self._point = self._bounded(self._point, self._frame_height)

    def position(self):
        if self._world is not self.game.world or self._point is None:
            self.reset()
        return tuple(round(value) for value in self._point)

    @property
    def framing_height(self):
        """World height remains the full viewport, including during dialogue."""
        if self._world is not self.game.world or self._point is None:
            self.reset()
        return round(self._frame_height)

    @property
    def settled(self):
        if self._point is None or self._target_point is None:
            return True
        return (math.dist(self._point, self._target_point) < .25 and
                abs(self._frame_height-self._target_height) < .25)
