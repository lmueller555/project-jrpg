"""The first household: a temporary companion and three real sack deliveries.

Persistent facts are separate from short gestures. An interrupted lift resumes
at its safe source; stored sacks and the medicine receipt are never replayed.
"""
from collections import deque
import heapq
import itertools
import json
import math
from pathlib import Path

import pygame

from npc_routines import find_path
from npc_following import following_facing, idle_following_facing, reset_following_facing
from quests import OPENING_QUEST
from social import facing_toward, clear_sight

ROOT = Path(__file__).resolve().parent
ART = 'assets/story/halden/'
SOURCES = ((104, 274), (128, 274), (152, 274))
STORAGE = ((112, 112), (136, 112), (160, 112))


def point(value):return tuple(round(v/2)*2 for v in value)


def town_path(world, start, goal, actor, avoid):
    """A coarse long-distance route, checking every edge against solid ground.

    Local 2px navigation handles narrow landings. This bounded 8px search is
    reserved for returning to the sanctuary across the much larger town map.
    """
    start = point(start);goal = point(goal)
    serial = itertools.count();parents = {start: None};costs = {start: 0}
    def h(p):return abs(p[0]-goal[0])+abs(p[1]-goal[1])
    queue = [(h(start), next(serial), start)]
    tail = None;end = None
    while queue and len(costs) < 36000:
        _, _, p = heapq.heappop(queue)
        if h(p) <= 16:
            tail = find_path(world, p, goal, actor.probe_size, actor, avoid)
            if tail is not None:end = p;break
        for dx, dy in ((8, 0), (-8, 0), (0, 8), (0, -8)):
            q = (p[0]+dx, p[1]+dy);cost = costs[p]+8
            if cost >= costs.get(q, math.inf):continue
            if not all(world.can_stand((p[0]+dx*f/4, p[1]+dy*f/4),
                                       actor.probe_size, actor, avoid) for f in (1, 2, 3, 4)):continue
            parents[q] = p;costs[q] = cost
            heapq.heappush(queue, (cost+h(q), next(serial), q))
    if end is None:return None
    path = []
    while end != start:path.append(end);end = parents[end]
    path.reverse();path.extend(tail)
    compact = []
    for p in path:
        if len(compact)>1:
            a, b = compact[-2:]
            if a[0] == b[0] == p[0] or a[1] == b[1] == p[1]:compact[-1] = p;continue
        compact.append(p)
    return deque(compact)


class Halden:
    """A named miller with an independent portrait and directional work costume."""
    def __init__(self, world):
        self.data = {'id': 'halden', 'name': 'Master Halden'}
        self.position = pygame.Vector2(192, 176)
        self.probe_size = (12, 8);self.draw_anchor = (12, 30)
        self.idles = {d: world.image(ART+f'idle_{d}.png') for d in ('front', 'back', 'left', 'right')}
        self.moving = False;self.walk_ms = 0.;self.opens_doors = True
        self.facing = 'front';self.conversation_ready = False
        self.conversation_facing = 'front'

    @property
    def blocker(self):return pygame.Rect(round(self.position.x)-6, round(self.position.y)-4, 12, 8)

    def sprite(self, elapsed_ms):
        if self.moving and not self.conversation_ready and hasattr(self, 'walks'):
            return self.walks[self.facing][int(self.walk_ms//140)%4]
        return self.idles[self.conversation_facing if self.conversation_ready else self.facing]

    def request_conversation(self, facing):
        self.conversation_ready = True;self.conversation_facing = facing

    def end_conversation(self):self.conversation_ready = False


class HaldenVisit:
    def __init__(self, game):
        self.game = game;self.home = game._scene_by_id('halden')
        self.halden = Halden(self.home);self.home.npcs.append(self.halden)
        self.tomas = next(a for a in game.persistent_npcs if a.data['id'] == 'tomas')
        self.lines = json.loads((ROOT/'assets/story/halden/scene.json').read_text())
        self.stored = set();self.carried = None;self.concluded = False
        self.departed = False;self.returning = False;self.owns_tomas = False
        self.action = None;self.action_time = 0.;self.contact = False
        self.tomas_job = None;self.tomas_time = 0.;self.tomas_held = None
        self.paths = {};self.retry = {};self.trail = deque(maxlen=1024)
        self.last_scene = None;self.dialogue = None
        self._player_pose = False;self._tomas_pose = False
        self.surface_props = []
        for i in range(3):
            self.surface_props.append({'id': f'sack_{i}', 'scene': 'halden',
                'surface': self.home.image(ART+'sack.png'), 'position': [0, 0], 'sort_y': 0})
        self.surface_props.append({'id': 'grain_pallet', 'scene': 'halden',
            'surface': self.home.image(ART+'pallet.png'), 'position': [98, 94], 'sort_y': 96})
        self.surface_props.append({'id': 'halden_medicine', 'scene': 'halden',
            'surface': self.home.image(ART+'medicine.png'), 'position': [278, 145], 'sort_y': 175})
        self.home.attach_routine_props(self)
        self.home.task_blockers = self.blockers
        self._sync_props()

    @property
    def active(self):return self.game.quests.objective_status(OPENING_QUEST, 'halden') == 'active'

    @property
    def medicine(self):return self.game.inventory.was_delivered(OPENING_QUEST, 'halden')

    @property
    def locks_player(self):return self.action is not None

    def to_dict(self):
        if self.game.quests.objective_status(OPENING_QUEST, 'halden') == 'completed':
            return {'version': 1, 'stored_sacks': [0, 1, 2], 'carried_sack': None,
                    'concluded': True, 'departed': True}
        return {'version': 1, 'stored_sacks': sorted(self.stored), 'carried_sack': self.carried,
                'concluded': self.concluded, 'departed': self.departed}

    @staticmethod
    def valid_snapshot(data):
        if not isinstance(data, dict) or set(data) != {'version', 'stored_sacks', 'carried_sack', 'concluded', 'departed'}:return False
        stored = data['stored_sacks'];carried = data['carried_sack']
        return (type(data['version']) is int and data['version'] == 1 and
                isinstance(stored, list) and all(type(i) is int and 0 <= i < 3 for i in stored) and
                len(set(stored)) == len(stored) and
                (carried is None or type(carried) is int and 0 <= carried < 3 and carried not in stored and carried != 1) and
                type(data['concluded']) is bool and type(data['departed']) is bool and
                (not data['concluded'] or len(stored) == 3) and
                (not data['departed'] or data['concluded']))

    def restore(self, data=None):
        if data is not None and not self.valid_snapshot(data):return False
        self._clear_player_pose();self._clear_tomas_pose()
        self.action = None;self.action_time = 0;self.tomas_job = None;self.tomas_held = None
        self.paths.clear();self.retry.clear();self.trail.clear();self.last_scene = None
        self.dialogue = None;self.returning = False;self.owns_tomas = False
        self.tomas.story_following = False;reset_following_facing(self.tomas)
        self.halden.end_conversation()
        completed = self.game.quests.objective_status(OPENING_QUEST, 'halden') == 'completed'
        self.stored = set(data['stored_sacks']) if data else set(range(3)) if completed else set()
        self.carried = data['carried_sack'] if data else None
        self.concluded = data['concluded'] if data else completed
        self.departed = data['departed'] if data else completed
        self._sync_props()
        if self.active and self.game.opening.stage in ('disabled', 'done'):
            # Continue resumes the escort beside Caelan, with one actor instance.
            landing = self._near_player()
            if landing is not None:self._place_tomas(self.game.world, landing)
            self._join()
        elif completed:
            self._resume_schedule()
        return True

    def surface_prop_visible(self, prop):
        identifier = prop['id']
        if identifier == 'halden_medicine':return self.medicine and self.action != 'medicine'
        if identifier == 'grain_pallet':return True
        i = int(identifier.rsplit('_', 1)[1])
        return i != self.carried and i != self.tomas_held

    def _sync_props(self):
        for prop in self.surface_props[:3]:
            i = int(prop['id'].rsplit('_', 1)[1]);x, y = STORAGE[i] if i in self.stored else SOURCES[i]
            prop['position'] = [x-8, y-18];prop['sort_y'] = y

    def blockers(self):
        return [pygame.Rect(x-8, y-5, 16, 8) for i in range(3)
                if i != self.carried and i != self.tomas_held
                for x, y in [STORAGE[i] if i in self.stored else SOURCES[i]]]

    def _near_player(self):
        player = self.game.player.position;world = self.game.world
        avoid = world.probe_rect(player).inflate(4, 4)
        for radius in (26, 34, 42, 18, 50):
            for dx, dy in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                p = point(player+pygame.Vector2(dx, dy))
                if world.can_stand(p, self.tomas.probe_size, self.tomas, avoid):return p
        return None

    def _place_tomas(self, world, position):
        reset_following_facing(self.tomas)
        old = self.game._routine_worlds[self.tomas]
        if self.tomas in old.npcs:old.npcs.remove(self.tomas)
        if self.tomas not in world.npcs:world.npcs.append(self.tomas)
        self.tomas.position.update(position);self.tomas.scene_id = world.data['id']
        self.game._routine_worlds[self.tomas] = world
        self.paths.pop(self.tomas, None)

    def _join(self):
        if self.owns_tomas:return
        reset_following_facing(self.tomas)
        self.owns_tomas = True;self.tomas.story_paused = True;self.tomas.story_following = True
        self.tomas.end_conversation();self.game.opening._clear_pose(self.tomas)
        self.tomas.moving = False;self.tomas.walk_ms = 0

    def _resume_schedule(self, arrived=False):
        # The physical return walks into the hall before releasing his schedule.
        hall = self.game._scene_by_id('sanctuary_hall')
        if not arrived:
            avoid = hall.probe_rect(self.game.player.position) if self.game.world is hall else None
            landing = next((p for p in ((208, 282), (232, 282), (184, 282))
                            if hall.can_stand(p, self.tomas.probe_size, self.tomas, avoid)), None)
            if landing is None:return
            self._place_tomas(hall, landing)
        self.tomas.select_step('return_through_hall', position=tuple(self.tomas.position), scene_id='sanctuary_hall', facing='back')
        self._clear_tomas_pose();self.tomas.story_following = False;self.tomas.story_paused = False
        reset_following_facing(self.tomas)
        self.owns_tomas = False;self.returning = False

    def can_speak(self, identifier):
        if identifier == 'tomas' and (self.owns_tomas or self.active):return False
        if identifier == 'halden' and (self.action or self.carried is not None or self.tomas_job):return False
        return True

    def try_conversation(self, actor):
        if actor is not self.halden or not self.active:return None
        if not self.owns_tomas or self.tomas.scene_id != 'halden':return False
        if self.tomas.position.distance_to(self.halden.position)>96:return False
        if not self.medicine:
            return self._speak('arrival', self._begin_medicine)
        if len(self.stored) == 3 and not self.concluded:
            return self._speak('conclusion', self._finish_conclusion)
        return self._speak('reminder', None)

    def _speak(self, kind, callback):
        if self.game.social.locked:return False
        self.halden.facing = facing_toward(self.game.player.position-self.halden.position)
        self.tomas.moving = False
        self.dialogue = kind
        def finished():
            self.dialogue = None
            if callback is not None:callback()
        result = self.game.social.start_script(self.lines[kind], finished, 'halden_'+kind)
        if result:self.game.social.blocked.add(self.halden)
        else:self.dialogue = None
        return result

    def on_dialogue_cancelled(self, identifier):
        if identifier and identifier.startswith('halden_'):self.dialogue = None

    def _begin_medicine(self):
        if self.game.world is not self.home or self.game.player.position.distance_to(self.halden.position)>36:return
        self.action = 'medicine';self.action_time = 0;self.contact = False
        self.game.player.facing = facing_toward(self.halden.position-self.game.player.position)

    def _finish_conclusion(self):
        self.concluded = True;self._save()

    def _save(self):
        self._sync_props();self.game.save_progress()

    def _target(self):
        if not self.active or not self.medicine or self.action or self.game.world is not self.home:return None
        p = self.game.player.position
        if self.carried is not None:
            i = self.carried;goal = (STORAGE[i][0], STORAGE[i][1]+22)
            if p.distance_to(goal)<=18 and clear_sight(self.home, p, pygame.Vector2(goal)):
                return ('store', i, 'E: Set sack on the dry pallet')
            return None
        for i, source in enumerate(SOURCES):
            if i in self.stored or i == self.tomas_held or (i == 1 and self.tomas_job):continue
            goal = (source[0], source[1]+18)
            if p.distance_to(goal)<=16 and clear_sight(self.home, p, pygame.Vector2(goal)):
                if i == 1:
                    return ('tomas', i, 'E: Ask Tomas to carry this sack') if self.tomas.scene_id == 'halden' else None
                return ('lift', i, 'E: Pick up grain sack')
        return None

    def interaction_hint(self):
        if self.game.social.locked or not self.active:return ''
        if self.action:return 'Passing the medicine…' if self.action == 'medicine' else 'Moving the grain sack…'
        target = self._target()
        if target:return target[2]
        if self.game.world is self.home:
            if self.concluded:return 'Walk up to Tomas to say goodbye.'
            if self.medicine and len(self.stored) == 3:return 'Speak with Halden.'
            if not self.medicine:return 'Approach Halden to give him Serene’s medicine.'
        return ''

    def tracker_text(self):
        if not self.active:return ''
        if self.concluded:return 'Say goodbye to Tomas.'
        if self.medicine:
            if len(self.stored) == 3:return 'Speak with Halden.'
            return f'Store the grain sacks: {len(self.stored)}/3. E: lift / set down.'
        return 'Visit Halden with Tomas.'

    def journal_detail(self):
        if not self.active:return ''
        return ('Medicine delivered. ' if self.medicine else 'Medicine is in the satchel. ')+f'Grain sacks stored: {len(self.stored)}/3.'

    def interact(self):
        if self.game.social.locked or self.action:return False
        target = self._target()
        if target is None:return False
        kind, i, _ = target
        if kind == 'tomas':
            self.tomas_job = 'approach';self.tomas_time = 0;self.paths.pop(self.tomas, None)
            return True
        self.action = (kind, i);self.action_time = 0;self.contact = False
        self.game.player.facing = 'back'
        return True

    def _pose(self, actor, character, kind, direction, index=None):
        suffix = '' if index is None else '_'+str(index)
        actor.story_sprite = self.home.image(ART+f'{character}/{kind}_{direction}{suffix}.png')
        actor.story_draw_anchor = (16, 34)
        if actor is self.game.player:self._player_pose = True
        else:self._tomas_pose = True

    def _clear_player_pose(self):
        if not self._player_pose:return
        for name in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.game.player, name):delattr(self.game.player, name)
        self._player_pose = False

    def _clear_tomas_pose(self):
        if not self._tomas_pose:return
        for name in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.tomas, name):delattr(self.tomas, name)
        self._tomas_pose = False

    def _update_player(self, dt):
        player = self.game.player
        if self.action:
            self.action_time += dt
            if self.action == 'medicine':
                if self.action_time >= .4 and not self.contact:
                    self.contact = True
                    self.game.deliver_quest_item(OPENING_QUEST, 'halden', 'halden')
                if self.action_time >= .85:
                    self.action = None;self._save()
                return
            kind, i = self.action
            frame = min(3, int(self.action_time/.18))
            # Loose prop remains at its source until the contact pose owns it.
            if self.action_time >= .36 and not self.contact:
                self.contact = True
                if kind == 'lift':self.carried = i
                else:self.stored.add(i);self.carried = None
                self._save()
            if kind == 'lift' and self.contact or kind == 'store' and not self.contact:
                self._pose(player, 'caelan', 'lift', 'back', frame if kind == 'lift' else 3-frame)
            elif kind == 'store':self._clear_player_pose()
            if self.action_time >= .72:
                self.action = None;self._clear_player_pose();self._save()
        if self.carried is not None and self.action is None:
            frame = int(player.walk_ms//140)%4
            self._pose(player, 'caelan', 'carry' if player.moving else 'hold', player.facing,
                       frame if player.moving else None)
        elif not self.action:self._clear_player_pose()

    def _move(self, actor, world, goal, dt, speed=76):
        with following_facing(actor, dt):
            return self._move_path(actor, world, goal, dt, speed)

    def _move_path(self, actor, world, goal, dt, speed=76):
        goal = point(goal);actor.moving = False
        avoid = world.probe_rect(self.game.player.position) if self.game.world is world else None
        if actor.position.distance_to(goal)<.1:
            self.paths.pop(actor, None);return True
        cached = self.paths.get(actor)
        self.retry[actor] = max(0., self.retry.get(actor, 0.)-dt)
        if cached is None or cached[0] != goal:
            if self.retry[actor]>0:return False
            route = (town_path(world, actor.position, goal, actor, avoid)
                     if world is self.game.town and actor.position.distance_to(goal)>200
                     else find_path(world, actor.position, goal, actor.probe_size, actor, avoid))
            if route is None:self.retry[actor] = .35;return False
            self.paths[actor] = (goal, route);cached = (goal, route)
        route = cached[1];budget = max(0., dt)*speed
        while route and budget>1e-7:
            delta = pygame.Vector2(route[0])-actor.position;distance = delta.length()
            if distance<1e-7:route.popleft();continue
            direction = delta/distance;travel = min(1., budget, distance)
            next_point = actor.position+direction*travel
            if not world.can_stand(next_point, actor.probe_size, actor, avoid):
                self.paths.pop(actor, None);self.retry[actor] = .15;return False
            actor.position.update(next_point);actor.facing = facing_toward(direction)
            actor.moving = True;actor.walk_ms += travel/speed*1000;budget -= travel
            if travel>=distance-1e-7:route.popleft()
        return actor.position.distance_to(goal)<.1

    def _door_toward(self, world, destination):
        queue = deque([(world, None)]);seen = {world.path}
        while queue:
            room, first = queue.popleft()
            if room is destination:return first
            for door in room.doors:
                path = (ROOT/door.data['destination']).resolve()
                if path in seen:continue
                seen.add(path);queue.append((self.game._load_scene(path), first or door))
        return None

    def _travel_room(self, destination, dt):
        world = self.game._routine_worlds[self.tomas]
        if world is destination:return True
        door = self._door_toward(world, destination)
        if door is None:return False
        if not self._move(self.tomas, world, door.data['anchor'], dt):return False
        step = {'scene': self.game._load_scene(ROOT/door.data['destination']).data['id'],
                'position': door.data['spawn'], 'departure_door': door.data['id'],
                'arrival_door': door.data['arrival_door']}
        result = self.game._transfer_routine_npc(self.tomas, step)
        if result is not None:
            self.paths.pop(self.tomas, None);reset_following_facing(self.tomas)
        return result is destination

    def _follow(self, dt):
        actor = self.tomas;world = self.game.world;player = self.game.player
        if not self._travel_room(world, dt):return
        if self.last_scene is not world:
            self.trail.clear();self.last_scene = world
        if not self.trail or pygame.Vector2(self.trail[-1]).distance_to(player.position)>=4:
            if self.trail and pygame.Vector2(self.trail[-1]).distance_to(player.position)>128:self.trail.clear()
            self.trail.append(point(player.position))
        distance = actor.position.distance_to(player.position)
        if distance<20:
            # Yield to the player's feet. The escort never becomes a door wall.
            landing = self._near_player()
            if landing:self._move(actor, world, landing, dt)
            return
        if distance<=34:
            actor.moving = False;self.paths.pop(actor, None);idle_following_facing(actor, dt);return
        length = 0;goal = self.trail[-1]
        for previous in reversed(self.trail):
            length += pygame.Vector2(goal).distance_to(previous);goal = previous
            if length>=28:break
        avoid = world.probe_rect(player.position).inflate(2, 2)
        if not world.can_stand(goal, actor.probe_size, actor, avoid):goal = self._near_player()
        if goal is not None:self._move(actor, world, goal, dt, 116 if distance>64 else 78)

    def _update_tomas_job(self, dt):
        actor = self.tomas;self.tomas_time += dt
        if actor.scene_id != 'halden':return
        if self.tomas_job == 'approach':
            if self._move(actor, self.home, (128, 256), dt, 52):
                actor.facing = 'front';self.tomas_job = 'lift';self.tomas_time = 0
        elif self.tomas_job == 'lift':
            if self.tomas_time>=.36:self.tomas_held = 1
            if self.tomas_held is not None:self._pose(actor, 'tomas', 'lift', 'front', min(3, int(self.tomas_time/.18)))
            if self.tomas_time>=.72:
                self.tomas_job = 'carry';self.tomas_time = 0
        elif self.tomas_job == 'carry':
            arrived = self._move(actor, self.home, (136, 134), dt, 48)
            self._pose(actor, 'tomas', 'carry', actor.facing, int(actor.walk_ms//140)%4)
            if arrived:actor.facing = 'back';self.tomas_job = 'store';self.tomas_time = 0
        elif self.tomas_job == 'store':
            if self.tomas_time<.36:self._pose(actor, 'tomas', 'lift', 'back', max(0, 3-int(self.tomas_time/.18)))
            elif self.tomas_held is not None:
                self.stored.add(1);self.tomas_held = None;self._clear_tomas_pose();self._save()
            if self.tomas_time>=.72:
                self.tomas_job = None;self.tomas_time = 0;self._clear_tomas_pose()

    def update(self, seconds):
        self._update(seconds)
        if self.owns_tomas and not self._tomas_pose:
            frames = self.tomas.walks[self.tomas.facing]
            self.tomas.story_sprite = (frames[self.tomas._frame_index(frames, self.tomas.walk_ms)][0]
                                       if self.tomas.moving else self.tomas.idles[self.tomas.facing])
            self.tomas.story_draw_anchor = self.tomas.draw_anchor;self._tomas_pose = True

    def _update(self, seconds):
        eligible = self.active and self.game.opening.stage in ('disabled', 'done')
        if eligible and not self.owns_tomas:self._join()
        self._update_player(seconds)
        if not self.owns_tomas:return
        self.tomas.story_paused = True;self.tomas.story_following = True
        if self.returning:
            self._clear_tomas_pose()
            hall = self.game._scene_by_id('sanctuary_hall')
            if self._travel_room(hall, seconds):self._resume_schedule(arrived=True)
            return
        if self.concluded:
            self._clear_tomas_pose();self.tomas.moving = False
            if self.departed:
                if self._travel_room(self.game.town, seconds):
                    self.returning = True
                    self.game.quests.complete_objective(OPENING_QUEST, 'halden')
                    self.game.social.flags.update({'CH01_MQ01_HALDEN_DONE', 'CH01_MQ01_TOMAS_DEPARTED'})
                    self._save()
                return
            if self.game.world is self.home and self.tomas.scene_id == 'halden' and not self.game.social.locked:
                gap = self.tomas.position.distance_to(self.game.player.position)
                if gap<=34:self._speak('goodbye', self._depart)
            elif self.tomas.scene_id != 'halden':
                self._travel_room(self.home, seconds)
            return
        if self.tomas_job:
            self._update_tomas_job(seconds);return
        self._clear_tomas_pose()
        if self.dialogue or self.action or self.game.social.resolve_speaker() is self.tomas:
            self.tomas.moving = False
            self.tomas.story_sprite = self.tomas.idles[facing_toward(self.game.player.position-self.tomas.position)]
            self.tomas.story_draw_anchor = self.tomas.draw_anchor;self._tomas_pose = True
        else:
            self._follow(seconds)
            frames = self.tomas.walks[self.tomas.facing]
            image = frames[self.tomas._frame_index(frames, self.tomas.walk_ms)][0] if self.tomas.moving else self.tomas.idles[self.tomas.facing]
            self.tomas.story_sprite = image;self.tomas.story_draw_anchor = self.tomas.draw_anchor;self._tomas_pose = True

    def _depart(self):
        self.departed = True;self.paths.pop(self.tomas, None);self._save()

    def draw_world(self, canvas, camera):
        if self.action != 'medicine' or self.game.world is not self.home:return
        # One bottle, snapped at the actual handoff beat between close hands.
        owner = self.halden if self.contact else self.game.player
        pos = owner.position
        canvas.blit(self.home.image(ART+'medicine.png'), (round(pos.x)+4-camera[0], round(pos.y)-14-camera[1]))
