"""The mill outing's short return home and physical cup delivery.

MillQuest owns the durable report, dialogue and completion receipts. This
controller stages the existing family and transient movement only: an interrupted
pickup starts again at the clean cups, while a committed placement stays visible.
All bodies are existing approved idle, walking and empty-hand household poses.
"""
from collections import deque

import pygame

from npc_routines import find_path
from social import facing_toward

SOURCE = (120, 96)
TABLE = (252, 200)
SOURCE_CUP = (122, 71)
TABLE_CUP = (266, 190)
FAMILY = {'mother_serene': (288, 116), 'tomas': (108, 200)}
CUP = 'assets/story/sanctuary_opening/poses/cup.png'
EMPTY_HANDS = 'assets/story/elira/give_{}.png'
SPEED = 56.


class SanctuaryReturn:
    def __init__(self, game):
        self.game = game
        self.dining = game._scene_by_id('sanctuary_dining')
        self.serene = next(a for a in game.persistent_npcs if a.data['id'] == 'mother_serene')
        self.tomas = next(a for a in game.persistent_npcs if a.data['id'] == 'tomas')
        self._cup = self.dining.image(CUP)
        self._body_anchor = tuple(self.dining.data['player_draw_anchor'])
        self._household_anchor = (self._body_anchor[0]+8, self._body_anchor[1]+24)
        self._hands = {d: self.dining.image(EMPTY_HANDS.format(d))
                       for d in ('front', 'back', 'left', 'right')}
        # The old household give_left pose extends its far arm backwards.
        # Mirror the existing right-facing pose at draw time to keep a carried
        # cup in front of Caelan when he turns left, without changing a limb.
        self._hands['left'] = pygame.transform.flip(self._hands['right'], True, False)
        self._reaches = [self.dining.image(f'assets/story/elira/reach_{i}.png') for i in range(3)]
        self.surface_props = []
        for kind, origin in (('source', SOURCE_CUP), ('table', TABLE_CUP)):
            for i in range(2):
                self.surface_props.append({'id': f'mill_return_{kind}_cup_{i}',
                    'scene': 'sanctuary_dining', 'surface': self._cup,
                    'position': (origin[0]-i, origin[1]-i*4),
                    'sort_y': 90 if kind == 'source' else 210,
                    'sort_priority': 2, 'kind': kind})
        # Reuse the room's serving pot beside the new cups on the setting table.
        self.surface_props.append({'id': 'mill_return_serving_pot',
            'scene': 'sanctuary_dining',
            'surface': self.dining.image('assets/terrain/eldenmere/sanctuary_interior/props/kettle.png'),
            'position': (278, 178), 'sort_y': 210, 'sort_priority': 1.5,
            'kind': 'pot'})
        self.dining.attach_routine_props(self)
        self._owned = False
        self._player_pose = False
        self._pose_wrist = None
        self.reset()

    @property
    def ready(self):
        return (self._owned and all(self.game._routine_worlds.get(a) is self.dining
                                   for a in (self.serene, self.tomas)))

    @property
    def action_active(self):return self.action is not None

    @property
    def locks_player(self):return self.action_active

    @property
    def holding_cups(self):return self._holding

    def surface_prop_visible(self, prop):
        if prop['kind'] == 'table':return self.placed
        if prop['kind'] == 'pot':return self._reported or self.placed
        return self._reported and not self._holding and not self.placed

    def _clear_player_pose(self):
        if not self._player_pose:return
        for key in ('story_sprite', 'story_draw_anchor', 'story_position', 'story_sort_y'):
            if hasattr(self.game.player, key):delattr(self.game.player, key)
        self._player_pose = False
        self._pose_wrist = None

    def release(self):
        """Release family before RegentQuest claims it; keep placed tableware."""
        self._clear_player_pose()
        if self._owned:
            for actor in (self.serene, self.tomas):
                actor.story_paused = False;actor.story_following = False
                for key in ('story_sprite', 'story_draw_anchor', 'story_position', 'story_sort_y'):
                    if hasattr(actor, key):delattr(actor, key)
                actor.end_conversation()
        self._owned = False;self.action = None;self._holding = False
        self._callback = None;self._route = None

    def reset(self):
        self.release()
        self._reported = False;self.placed = False
        self._holding = False;self.action = None;self.action_time = 0.
        self._callback = None;self._route = None;self._route_goal = None
        self._walk_ms = 0.;self._retry = 0.;self._delivery_origin = None

    def restore(self, reported=False, placed=False, complete=False):
        self.reset()
        if not reported:return self
        self.prepare();self.placed = bool(placed)
        return self

    def _landing(self, actor, preferred):
        avoid = self.dining.probe_rect(self.game.player.position) if self.game.world is self.dining else None
        for radius in (0, 12, 20, 28, 40):
            for offset in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                p = pygame.Vector2(preferred)+offset
                if self.dining.can_stand(p, actor.probe_size, actor, avoid):return p
        return None

    def prepare(self):
        """Stage only the same family members, never the visiting caravan."""
        self._reported = True
        if self._owned:return self.ready
        placements = [(actor, self._landing(actor, FAMILY[actor.data['id']]))
                      for actor in (self.serene, self.tomas)]
        if any(landing is None for _, landing in placements):return False
        for actor, landing in placements:
            for world in self.game.scenes.values():
                while actor in world.npcs:world.npcs.remove(actor)
            self.dining.npcs.append(actor);self.game._routine_worlds[actor] = self.dining
            actor.position.update(landing);actor.scene_id = 'sanctuary_dining'
            actor.story_paused = True;actor.story_following = False;actor.moving = False
            actor.end_conversation();actor.facing = 'front' if actor is self.serene else 'right'
            actor.story_sprite = actor.idles[actor.facing]
            actor.story_draw_anchor = actor.draw_anchor
        self._owned = True
        return self.ready

    def start_cups(self, on_complete=None):
        """Collect and carry the cups, then hold them for the table dialogue."""
        if (not self.ready or self.game.world is not self.dining
                or self.action_active or self._holding or self.placed):return False
        self.action = 'collect';self.action_time = 0.;self._callback = on_complete
        self._route = None;self._walk_ms = 0.;self._retry = 0.
        self.game.player.moving = False
        return True

    def place_cups(self, on_complete=None):
        """After Serene's instruction, return to the table and set them down."""
        if (not self.ready or self.game.world is not self.dining
                or self.action_active or not self._holding or self.placed):return False
        self.action = 'return_table';self.action_time = 0.;self._callback = on_complete
        self._route = None;self._walk_ms = 0.;self._retry = 0.
        return True

    def _arrive(self):
        callback = self._callback;self._callback = None
        self.action = None;self.action_time = 0.;self._route = None
        self.game.player.moving = False
        self._clear_player_pose()
        if self._holding:self._pose(self.game.player.facing)
        if callback is not None:callback()

    def _pose(self, direction):
        player = self.game.player
        player.facing = direction;player.moving = False
        player.story_sprite = self._hands[direction]
        # Household canvases paste the normal 24x36 body at (8,24), so this
        # offset preserves the room's existing foot baseline without a jump.
        player.story_draw_anchor = self._household_anchor
        self._pose_wrist = (11, 48) if direction == 'left' else (28, 48)
        self._player_pose = True

    def _reach(self, index):
        """Existing paired-arm reach, stopping at the sideboard's height."""
        index = max(0, min(2, index))
        player = self.game.player;player.facing = 'back';player.moving = False
        player.story_sprite = self._reaches[index]
        player.story_draw_anchor = self._household_anchor
        fraction = index/3
        self._pose_wrist = (round(20-4*fraction)+8, round(24-21*fraction)+24)
        self._player_pose = True

    def _move(self, goal, seconds):
        player = self.game.player
        player.moving = False
        goal = tuple(goal)
        if player.position.distance_squared_to(goal) < .01:return True
        self._retry = max(0., self._retry-seconds)
        if self._route is None or goal != self._route_goal:
            if self._retry:return False
            route = find_path(self.dining, player.position, goal, self.dining.probe_size, None)
            if route is None:self._retry = .25;return False
            self._route = deque(route);self._route_goal = goal
        budget = max(0., seconds)*SPEED
        while self._route and budget > 1e-7:
            delta = pygame.Vector2(self._route[0])-player.position
            distance = delta.length()
            if distance < 1e-7:self._route.popleft();continue
            travel = min(1., budget, distance)
            candidate = player.position+delta/distance*travel
            if not self.dining.can_stand(candidate):self._route = None;self._retry = .2;return False
            player.position.update(candidate);player.facing = facing_toward(delta)
            player.moving = True;player.running = False
            self._walk_ms += travel/SPEED*1000;player.walk_ms = self._walk_ms;budget -= travel
            if travel >= distance-1e-7:self._route.popleft()
        self._clear_player_pose()
        if player.moving:
            frames = player.walks[player.facing]
            cursor = self._walk_ms % sum(duration for _, duration in frames)
            for image, duration in frames:
                if cursor < duration:break
                cursor -= duration
            player.story_sprite = image;player.story_draw_anchor = self._body_anchor
            self._player_pose = True
        return player.position.distance_squared_to(goal) < .01

    def _cup_origin(self):
        player = self.game.player
        cup_to_hand = pygame.Vector2(3, 5)
        if self._pose_wrist is not None:
            # Existing give pose's authored wrist=(20,24), plus its (8,24)
            # canvas padding. The six-pixel cup rests against that hand.
            return (player.position+pygame.Vector2(self._pose_wrist)
                    -pygame.Vector2(self._household_anchor)-cup_to_hand)
        # Approved normal stride, with the small stack registered to its hand.
        index = int(player.walk_ms//140) % 4 if player.moving else 0
        hands = {'front': ((17, 22), (17, 22), (17, 20), (17, 22)),
                 'back': ((17, 20), (18, 21), (17, 21), (17, 20)),
                 'right': ((16, 21), (16, 21), (16, 22), (16, 21)),
                 'left': ((7, 20), (7, 21), (7, 21), (7, 21))}
        hand = pygame.Vector2(hands[player.facing][index])
        anchor = getattr(player, 'story_draw_anchor', None) or self.game.world.data['player_draw_anchor']
        return player.position+hand-pygame.Vector2(anchor)-cup_to_hand

    def update(self, seconds):
        if not self._owned:return
        if not getattr(self.game, '_music_focused', True):return
        if self.game.map_open or self.game.quest_ui.journal_open:return
        if self.action_active:
            if self.game.world is not self.dining:return
            self.action_time += max(0., seconds)
            if self.action in ('collect', 'carry', 'return_table'):
                goal = SOURCE if self.action == 'collect' else TABLE
                if self._move(goal, seconds):
                    self.action = 'pickup' if self.action == 'collect' else 'hold' if self.action == 'carry' else 'setdown'
                    self.action_time = 0.
                    if self.action == 'setdown':self._delivery_origin = self._cup_origin()
            elif self.action == 'pickup':
                self._reach(min(2, int(self.action_time/.15)))
                if self.action_time >= .45:
                    self._holding = True;self.action = 'lower';self.action_time = 0.;self._route = None
            elif self.action == 'lower':
                self._reach(max(0, 2-int(self.action_time/.12)))
                if self.action_time >= .36:
                    self.action = 'carry';self.action_time = 0.
            elif self.action == 'hold':
                self._pose('right')
                if self.action_time >= .2:self._arrive()
            elif self.action == 'setdown':
                self._pose('right')
                if self.action_time >= .6:
                    self._holding = False;self.placed = True;self._arrive()
        elif self._holding:
            # Cancelling live dialogue leaves normal navigation available.
            # Keep a supported hand pose while standing; walking uses the
            # unmodified directional stride and its registered hand locations.
            if self.game.player.moving:self._clear_player_pose()
            else:self._pose(self.game.player.facing)
        # Live conversations can turn to the actual person holding the floor.
        if self.game.social.active:
            for actor in (self.serene, self.tomas):
                actor.facing = facing_toward(self.game.player.position-actor.position)
                actor.story_sprite = actor.idles[actor.facing]

    def draw_world(self, canvas, camera):
        if not self._holding:return
        origin = self._cup_origin()
        if self.action == 'setdown':
            fraction = min(1., self.action_time/.45)
            fraction = fraction*fraction*(3-2*fraction)
            start = self._delivery_origin if self._delivery_origin is not None else origin
            origin = pygame.Vector2(start).lerp(TABLE_CUP, fraction)
        for i in range(2):
            canvas.blit(self._cup, (round(origin.x-i)-camera[0], round(origin.y-i*4)-camera[1]))
