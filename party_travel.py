"""Passive exploration companions following the player's traversed route.

These render actors never enter a world's NPC list. Authored quest companions
keep their own movement, props and staging; the party supplies followers only
when that character is not already represented by an authored actor.
"""
from __future__ import annotations

from bisect import bisect_right
import json
import math
from pathlib import Path

import pygame

from npc_following import following_facing, reset_following_facing


ROOT = Path(__file__).resolve().parent
COMPANIONS = frozenset(('mira', 'lucan', 'rhea', 'edran'))
SPACING = 22.0
WALK_SPEED = 72.0
RUN_SPEED = 108.0
TRAIL_LENGTH = 640.0
TELEPORT_DISTANCE = 64.0


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


class _TravelActor:
    """The small actor interface consumed by World.draw's existing NPC path."""

    def __init__(self, identifier):
        self.identifier = identifier
        self.position = pygame.Vector2()
        self.facing = 'front'
        self.moving = False
        self.walk_ms = 0.0
        self.visible = False
        self.story_following = True  # Existing companion direction smoothing.
        self.trail_distance = 0.0
        directory = ROOT/'assets/characters'/identifier
        front = _json(directory/'idle_front.json')
        self.draw_anchor = tuple(front.get('foot_anchor') or front['anchor'])
        self.idles = {}
        self.walks = {}
        for facing in ('front', 'back', 'left', 'right'):
            self.idles[facing] = pygame.image.load(str(directory/f'idle_{facing}.png')).convert_alpha()
            manifest = _json(directory/f'walk_{facing}'/'animation.json')
            self.walks[facing] = tuple(
                (pygame.image.load(str(directory/f'walk_{facing}'/frame['file'])).convert_alpha(),
                 frame.get('duration_ms', manifest.get('frame_duration_ms', 140)))
                for frame in manifest['frames'])

    def sprite(self, elapsed_ms):
        # Simulation time owns gait, so paused menus/dialogue freeze this pose.
        if not self.moving:return self.idles[self.facing]
        frames = self.walks[self.facing]
        remaining = self.walk_ms % sum(duration for _, duration in frames)
        for surface, duration in frames:
            if remaining < duration:return surface
            remaining -= duration
        return frames[-1][0]


class PartyTravel:
    """Draw up to two active companions along collision-checked breadcrumbs.

    On a doorway transfer or teleport, companions wait off screen until the
    player has cleared enough traversable space to place them behind the leader.
    No guessed entry coordinates, navigation shortcuts, or world NPC mutations
    are needed. Their HP does not restrict exploration representation.
    """

    def __init__(self, game, *, actor_factory=None):
        self.game = game
        self._actor_factory = actor_factory or _TravelActor
        self._actors = {}
        self._world = None
        self._points = []
        self._distances = []

    def reset(self):
        self._sync_authored(())
        self._world = None
        self._points.clear()
        self._distances.clear()
        for actor in self._actors.values():
            actor.visible = False
            actor.moving = False
            reset_following_facing(actor)

    def _normal_scale(self):
        return not getattr(self.game.world, 'is_overworld', False)

    def _paused(self):
        game = self.game
        if (getattr(game, 'on_title', False) or getattr(game, 'household_action', None)
                or getattr(game, 'map_open', False)
                or getattr(getattr(game, 'quest_ui', None), 'journal_open', False)):return True
        for name in ('pause', 'inventory_ui', 'world_map_viewer', 'party_ui',
                     'status_ui', 'lattice_ui', 'journal', 'map_ui'):
            if getattr(getattr(game, name, None), 'is_open', False):return True
        social = getattr(game, 'social', None)
        return bool(getattr(social, 'active', False) or getattr(social, 'locked', False)
                    or getattr(getattr(game, 'combat', None), 'active', False)
                    or getattr(getattr(game, 'opening', None), 'locks_player', False))

    def _owned_by_story(self, identifier):
        actor = getattr(getattr(self.game, 'mill_quest', None), 'mira', None) if identifier == 'mira' else None
        if actor is not None and any(getattr(actor, field, False)
                                     for field in ('story_following', 'quest_mode', 'story_sprite',
                                                   'story_position', 'story_draw_anchor')):
            return True
        return False

    def _sync_authored(self, active):
        # World/social integration temporarily suspends the routine actor while
        # her passive party representation travels. Her position is untouched.
        mira = getattr(getattr(self.game, 'mill_quest', None), 'mira', None)
        if mira is not None:mira.party_travelling = 'mira' in active

    def _active(self):
        party = getattr(self.game, 'party', None)
        members = getattr(party, 'members', {})
        return tuple(identifier for identifier in getattr(party, 'active_ids', ())
                     if identifier in COMPANIONS
                     and members.get(identifier, {}).get('available', False)
                     and not self._owned_by_story(identifier))

    def actors(self):
        """Read-only current-scene render list; never register collision actors."""
        if self._world is not self.game.world or not self._normal_scale():return ()
        return tuple(self._actors[identifier] for identifier in self._active()
                     if identifier in self._actors and self._actors[identifier].visible)

    def _start_trail(self, position):
        self._world = self.game.world
        self._points = [pygame.Vector2(position)]
        self._distances = [0.0]
        for actor in self._actors.values():
            actor.visible = False
            actor.moving = False
            reset_following_facing(actor)

    def _segment(self, start, end):
        """Check every pixel before publishing a recorded route segment."""
        delta = end-start
        steps = max(1, math.ceil(delta.length()))
        points = [start+delta*(index/steps) for index in range(1, steps+1)]
        return points if all(self.game.world.can_stand(point) for point in points) else None

    def _record(self, position):
        start = self._points[-1]
        if start.distance_squared_to(position) < 1e-10:return
        if start.distance_to(position) > TELEPORT_DISTANCE:
            self._start_trail(position)
            return
        points = self._segment(start, position)
        if points is None:
            # Player movement resolves x/y independently. Reconstruct a valid
            # axis route if a collision slide made the endpoint chord unsafe.
            for corner in (pygame.Vector2(position.x, start.y), pygame.Vector2(start.x, position.y)):
                first = self._segment(start, corner)
                second = self._segment(corner, position)
                if first is not None and second is not None:
                    points = first+second
                    break
        if points is None:
            self._start_trail(position)
            return
        for point in points:
            distance = self._points[-1].distance_to(point)
            if distance > 1e-9:
                self._points.append(point)
                self._distances.append(self._distances[-1]+distance)

    def _point_at(self, distance):
        index = max(0, bisect_right(self._distances, distance)-1)
        if index >= len(self._points)-1:return pygame.Vector2(self._points[-1])
        span = self._distances[index+1]-self._distances[index]
        return self._points[index].lerp(self._points[index+1], (distance-self._distances[index])/span)

    def _clear_spawn(self, point, placed):
        return (self.game.world.can_stand(point)
                and point.distance_to(self.game.player.position) >= 12
                and all(point.distance_to(actor.position) >= 12 for actor in placed))

    def _advance(self, actor, goal, seconds, speed):
        # Visit every original breadcrumb, rather than taking a straight chord
        # from last frame to this frame's target around a corner.
        distance = min(goal, actor.trail_distance+speed*seconds)
        indices = range(bisect_right(self._distances, actor.trail_distance),
                        bisect_right(self._distances, distance))
        candidates = [(self._distances[index], self._points[index]) for index in indices]
        candidates.append((distance, self._point_at(distance)))
        travelled = 0.0
        with following_facing(actor, seconds):
            for next_distance, point in candidates:
                if next_distance <= actor.trail_distance+1e-9:continue
                if not self.game.world.can_stand(point):break
                travelled += point.distance_to(actor.position)
                actor.position.update(point)
                actor.trail_distance = next_distance
        actor.moving = travelled > .001
        if actor.moving:actor.walk_ms += travelled/speed*1000

    def update(self, seconds):
        # Story staging may take ownership on the same frame it opens dialogue.
        # Release the routine suspension even when motion now has to freeze.
        active = self._active() if self._normal_scale() else ()
        self._sync_authored(active)
        if seconds <= 0 or self._paused():return
        if not self._normal_scale():
            self.reset()
            return
        position = pygame.Vector2(self.game.player.position)
        if self._world is not self.game.world or not self._points:
            self._start_trail(position)
        else:
            self._record(position)
        for identifier, actor in self._actors.items():
            if identifier not in active:
                actor.visible = False
                actor.moving = False
        placed = []
        speed = RUN_SPEED if getattr(self.game.player, 'running', False) else WALK_SPEED
        slots = {identifier: slot for slot, identifier in enumerate(self.game.party.active_ids)}
        for identifier in active:
            actor = self._actors.get(identifier)
            if actor is None:
                actor = self._actors[identifier] = self._actor_factory(identifier)
            # A story-owned Mira still occupies her formation slot. Another
            # companion must not collapse into her existing follow distance.
            goal = self._distances[-1]-SPACING*slots[identifier]
            if goal < self._distances[0]:continue
            if not actor.visible:
                point = self._point_at(goal)
                if not self._clear_spawn(point, placed):continue
                actor.position.update(point)
                actor.trail_distance = goal
                actor.facing = getattr(self.game.player, 'facing', 'front')
                actor.visible = True
                actor.moving = False
                actor.walk_ms = 0.0
                reset_following_facing(actor)
            else:
                self._advance(actor, goal, seconds, speed)
            placed.append(actor)
        # Keep the occupied tail when a temporary NPC obstruction holds a
        # follower back, then bound ordinary history to a few screen widths.
        oldest = min((actor.trail_distance for actor in placed), default=self._distances[-1])
        cutoff = min(oldest, self._distances[-1]-TRAIL_LENGTH)
        keep = max(0, bisect_right(self._distances, cutoff)-1)
        if keep:
            del self._points[:keep]
            del self._distances[:keep]
