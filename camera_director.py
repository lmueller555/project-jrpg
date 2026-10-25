"""Pixel-aligned, eased camera direction for story scenes and exploration.

Dialogue boxes do not choose a new camera height for authored scenes. The
opening controller supplies one focus for the whole beat, including any action
between pages. Only the final rendered position is rounded to native pixels.
"""
from __future__ import annotations

import math


VIEW_SIZE = (480, 320)
DIALOGUE_HEIGHT = 204
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
        self._inspection_anchor = None
        self._inspection_height = None

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

    def _authored_focus(self):
        opening = getattr(self.game, 'opening', None)
        focus = getattr(opening, 'camera_focus', None)
        if focus is None:
            return None
        # The player may leave the breakfast room after the exchange. A quest
        # giver's reserved station must not keep free exploration framed there.
        social = getattr(self.game, 'social', None)
        if (getattr(opening, 'stage', None) == 'assignment' and
                not getattr(social, 'locked', False)):
            return None
        return focus()

    def _inspection_target(self):
        """Hold an already useful shot, moving only enough to expose a speaker."""
        current = self._point
        if current is None:
            point = self._position_of(self.game.player)
            current = self._bounded((point[0]-240, point[1]-160), 320)
        point = self._position_of(self.game.player)
        # Keep the feet clear of the textbox and the head below the top HUD.
        if 62 <= point[1]-current[1] <= 190:
            return current, self._frame_height
        y = max(point[1]-190, min(current[1], point[1]-62))
        return self._bounded((current[0], y), DIALOGUE_HEIGHT), DIALOGUE_HEIGHT

    def _desired(self):
        social = getattr(self.game, 'social', None)
        focus = self._authored_focus()
        if focus is not None:
            self._inspection_anchor = None
            self._inspection_height = None
            return self._bounded((focus[0]-240, focus[1]-102), DIALOGUE_HEIGHT), DIALOGUE_HEIGHT

        identifier = getattr(social, 'script_identifier', None) or ''
        inspecting = getattr(social, 'locked', False) and identifier.startswith('bedroom_inspect_')
        if inspecting:
            if self._inspection_anchor is None:
                self._inspection_anchor, self._inspection_height = self._inspection_target()
            return self._inspection_anchor, self._inspection_height
        self._inspection_anchor = None
        self._inspection_height = None

        point = self._position_of(self.game.player)
        if getattr(social, 'locked', False):
            actor = getattr(social, 'actor', None)
            if actor is not None:
                other = self._position_of(actor)
                focus = ((point[0]+other[0])/2, (point[1]+other[1])/2-12)
                return self._bounded((focus[0]-240, focus[1]-102), DIALOGUE_HEIGHT), DIALOGUE_HEIGHT
            # An actorless line outside an authored scene can use the existing
            # composition when the player is already clear of the text panel.
            return self._inspection_target()
        return self._bounded((point[0]-240, point[1]-160), VIEW_SIZE[1]), VIEW_SIZE[1]

    def reset(self):
        """Establish one shot after a new journey or an intentional room cut."""
        self._world = self.game.world
        self._point = None
        self._inspection_anchor = None
        self._inspection_height = None
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
        # The intermediate safe area grows/shrinks along with the composition.
        # It keeps short rooms bounded without snapping to a new textbox size.
        self._point = self._bounded(self._point, self._frame_height)

    def position(self):
        if self._world is not self.game.world or self._point is None:
            self.reset()
        return tuple(round(value) for value in self._point)

    @property
    def framing_height(self):
        """Current usable world height, for an optional receding scene matte."""
        if self._world is not self.game.world or self._point is None:
            self.reset()
        return round(self._frame_height)

    @property
    def settled(self):
        if self._point is None or self._target_point is None:
            return True
        return (math.dist(self._point, self._target_point) < .25 and
                abs(self._frame_height-self._target_height) < .25)
