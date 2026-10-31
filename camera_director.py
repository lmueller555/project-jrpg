"""Pixel-aligned player tracking and explicitly authored cutscene pans.

Ordinary live dialogue keeps player tracking. A scene may explicitly focus a
world point, hold that composition, and release back to the player. Only final
rendered positions are rounded; every shot retains the complete world viewport.
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
        self._shot_mode = None
        self._pan_origin = None
        self._pan_target = None
        self._pan_duration = self._pan_elapsed = 0.0

    @staticmethod
    def _axis(value, world_size, view_size):
        if world_size < view_size:
            return (world_size-view_size)/2
        return max(0.0, min(world_size-view_size, value))

    def _bounded(self, point, height):
        world = self.game.world
        bounds = getattr(world, 'bounds', None)
        if bounds is None:
            left = top = 0
            width, world_height = world.size
        else:
            left, top, width, world_height = bounds
        return (left+self._axis(point[0]-left, width, VIEW_SIZE[0]),
                top+self._axis(point[1]-top, world_height, height))

    @staticmethod
    def _position_of(actor):
        return getattr(actor, 'story_position', None) or actor.position

    def _desired(self):
        point = self._position_of(self.game.player)
        return self._bounded((point[0]-240, point[1]-160), VIEW_SIZE[1]), VIEW_SIZE[1]

    def reset(self):
        """Establish one shot after a new journey or an intentional room cut."""
        self._shot_mode = None
        self._pan_origin = self._pan_target = None
        self._pan_duration = self._pan_elapsed = 0.0
        self._world = self.game.world
        self._point = None
        target, height = self._desired()
        self._point = tuple(float(value) for value in target)
        self._target_point = self._point
        self._frame_height = self._target_height = float(height)

    def _ensure_world(self):
        if self._world is not self.game.world or self._point is None:
            self.reset()
            return False
        return True

    @staticmethod
    def _pair(value, name, *, normalized=False):
        try:
            result = tuple(value)
        except TypeError:
            raise ValueError(f'{name} must contain two finite coordinates') from None
        if (len(result) != 2 or any(type(v) not in (int, float) or not math.isfinite(v)
                                    for v in result)
                or normalized and any(not 0 <= v <= 1 for v in result)):
            raise ValueError(f'{name} must contain two finite coordinates')
        return tuple(float(v) for v in result)

    @staticmethod
    def _duration(duration):
        if (type(duration) not in (int, float) or not math.isfinite(duration)
                or duration < 0):
            raise ValueError('Pan duration must be finite and nonnegative')
        return float(duration)

    def _begin_pan(self, target, duration, mode):
        duration = self._duration(duration)
        self._ensure_world()
        self._shot_mode = mode
        self._pan_origin = self._point
        self._pan_target = tuple(float(v) for v in self._bounded(target, VIEW_SIZE[1]))
        self._target_point = self._pan_target
        self._frame_height = self._target_height = float(VIEW_SIZE[1])
        self._pan_duration = float(duration)
        self._pan_elapsed = 0.0
        # A request already at its composition is settled immediately. A
        # zero-duration request is an explicit static cut, e.g. Reduced Motion.
        if duration == 0 or math.dist(self._pan_origin, self._pan_target) < 1e-9:
            self._point = self._pan_target
            self._pan_elapsed = self._pan_duration
            if mode == 'return':self._shot_mode = None

    def focus(self, point, duration=.75, *, anchor=(.5, .5)):
        """Pan a world point to a viewport anchor, then hold until released.

        ``anchor`` is a pair of fractions: (.5, .5) centers the point; (.5, .33)
        leaves room below it for a cutscene's dialogue. Scene bounds always win.
        Repeating an unchanged focus request preserves its current progress.
        """
        point = self._pair(point, 'Focus point')
        anchor = self._pair(anchor, 'Viewport anchor', normalized=True)
        duration = self._duration(duration)
        target = self._bounded((point[0]-VIEW_SIZE[0]*anchor[0],
                                point[1]-VIEW_SIZE[1]*anchor[1]), VIEW_SIZE[1])
        self._ensure_world()
        if duration > 0 and self._shot_mode == 'focus' and self._pan_target == target:return
        self._begin_pan(target, duration, 'focus')

    def return_to_player(self, duration=.65):
        """Pan to the player's current composition, then resume normal tracking."""
        duration = self._duration(duration)
        self._ensure_world()
        target, _ = self._desired()
        if duration > 0 and self._shot_mode == 'return' and self._pan_target == target:return
        self._begin_pan(target, duration, 'return')

    def release(self, duration=.65):
        """Release an authored shot back to ordinary player tracking."""
        self.return_to_player(duration)

    @property
    def scripted(self):
        self._ensure_world()
        return self._shot_mode is not None

    def _track(self, seconds):
        target, height = self._desired()
        self._target_point = tuple(float(value) for value in target)
        self._target_height = float(height)
        blend = -math.expm1(-EASE_RATE*seconds)
        self._point = tuple(current+(goal-current)*blend
                            for current, goal in zip(self._point, self._target_point))
        self._frame_height += (self._target_height-self._frame_height)*blend
        self._point = self._bounded(self._point, self._frame_height)

    def update(self, seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Camera update seconds must be finite and nonnegative')
        if not self._ensure_world():return
        if self._shot_mode is None:
            self._track(seconds)
            return
        if self._pan_elapsed < self._pan_duration:
            portion = min(seconds, self._pan_duration-self._pan_elapsed)
            self._pan_elapsed += portion
            seconds -= portion
            complete = self._pan_duration-self._pan_elapsed < 1e-9
            progress = 1.0 if complete else self._pan_elapsed/self._pan_duration
            blend = progress*progress*(3.0-2.0*progress)
            self._point = self._bounded(tuple(start+(goal-start)*blend
                                              for start, goal in zip(self._pan_origin,
                                                                     self._pan_target)), VIEW_SIZE[1])
            if complete:
                self._pan_elapsed = self._pan_duration
                self._point = self._pan_target
                if self._shot_mode == 'return':self._shot_mode = None
        if self._shot_mode is None and seconds > 0:self._track(seconds)

    def position(self):
        self._ensure_world()
        return tuple(round(value) for value in self._point)

    @property
    def framing_height(self):
        """World height remains the full viewport, including during dialogue."""
        self._ensure_world()
        return round(self._frame_height)

    @property
    def settled(self):
        self._ensure_world()
        if self._shot_mode is not None and self._pan_elapsed < self._pan_duration:return False
        return (math.dist(self._point, self._target_point) < .25 and
                abs(self._frame_height-self._target_height) < .25)
