"""Liam's first lantern: committed scenes, one child, one unfinished object.

The first release ends at frame_ready. The complete objective chain already
exists, so subsequent releases continue this quest without replaying its start.
"""
from collections import deque
import json
from pathlib import Path

import pygame

from halden_visit import point, town_path
from lantern_actors import ResidentPose
from lantern_village import LanternVillage, VILLAGE_STAGES, VILLAGE_PREFIX
from lantern_rest import LanternRest, REST_STAGES, REST_PREFIX
from npc_routines import find_path
from quests import LANTERN_QUEST, REGENT_QUEST, QuestLog
from social import facing_toward

ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/story/lantern'
STAGES = ('idle', 'invited', 'classroom', 'designed', 'permitted', 'workshop',
          'tested', 'assembled', 'lifted', 'frame_ready') + VILLAGE_STAGES + REST_STAGES
OBJECTIVES = ('join_preparations', 'build_frame', 'visit_neighbours', 'visit_elira',
              'take_break', 'speak_serene', 'finish_lantern', 'show_mother')
PREFIX = {s: (2 if s == 'frame_ready' else 1 if STAGES.index(s) >= 4 else 0) for s in STAGES}
PREFIX.update(VILLAGE_PREFIX)
PREFIX.update(REST_PREFIX)


class LanternQuest:
    def __init__(self, game):
        self.game = game;self.town = game.town
        self.school = game._scene_by_id('school')
        self.layout = json.loads((ART/'layout.json').read_text());self.points = self.layout
        self.lines = json.loads((ART/'scene.json').read_text())
        self.art = json.loads((ART/'art.json').read_text())
        self.shared = game.play_routines[0];self.liam = self.shared.liam
        self.tomas = next(a for a in game.persistent_npcs if a.data['id'] == 'tomas')
        self.serene = next(a for a in game.persistent_npcs if a.data['id'] == 'mother_serene')
        self.mira = game.mill_quest.mira
        self.residents = {};self._homes = {};self._worlds = {};self.resident_poses = {}
        for scene_id, identifiers in (('liam_house', ('liam_mother',)),
                                      ('home_a', ('tessa', 'finn')),
                                      ('home_b', ('rowan', 'ada')), ('home_c', ('pippa',))):
            world = game._scene_by_id(scene_id)
            for identifier in identifiers:
                actor = next(a for a in world.npcs if a.data['id'] == identifier)
                self.residents[identifier] = actor;self._worlds[actor] = world
                self._homes[actor] = (world, tuple(actor.position))
        self.mother = self.residents['liam_mother']
        self.children = {k: a for k, a in self.residents.items() if k != 'liam_mother'}
        self.stage = 'idle';self.dialogue = None;self.action = None;self.action_time = 0.
        self._player_route = None;self._player_goal = None
        self.align_time = 0.
        self._approach_walk_ms = 0.
        self.paths = {};self.retries = {};self._owned = False;self._liam_claimed = False
        self._ready = False;self._class_ready = False;self._gathering = False;self._mira_owned = False
        self._pose_actors = set();self.poses = {}
        self._quest_profiles = set()
        for identifier, path in self.art.get('poses', {}).items():
            meta = json.loads((ROOT/path).read_text());sheet = self.town.image(meta['sheet'])
            self.poses[identifier] = (meta, {kind: [(sheet.subsurface(f['rect']).copy(), f['duration_ms'])
                                        for f in frames] for kind, frames in meta['actions'].items()})
        self.surface_props = []
        for spec in self.art['props']:
            states = {k: self.town.image(p) for k, p in spec['states'].items()}
            prop = {**spec, 'states': states, 'surface': next(iter(states.values()))}
            self.surface_props.append(prop)
            game._scene_by_id(spec['scene']).attach_routine_props(self)
        self._prior_blockers = getattr(self.town, 'task_blockers', lambda: ())
        self.town.task_blockers = self._task_blockers
        self.village = LanternVillage(self)
        self.village_points = self.village.points;self.village_lines = self.village.lines
        self.lines.update(self.village.lines)
        self.halden = self.village.halden;self.venn_family = self.village.family
        self.venn_home = self.village.venn_home;self.elira_home = self.village.elira_home;self.elira = self.village.elira
        self.rest = LanternRest(self)
        self.rest_points = self.rest.points;self.rest_lines = self.rest.lines;self.lines.update(self.rest.lines)
        self.liam_home = self.rest.home;self.father = self.rest.father;self.sanctuary = self.rest.sanctuary

    @property
    def eligible(self):return self.game.quests.status(LANTERN_QUEST) != 'locked'
    @property
    def active(self):return self.game.quests.status(LANTERN_QUEST) == 'active'
    @property
    def locks_player(self):return self.action is not None

    def to_dict(self):return {'version': 1, 'stage': self.stage}

    @staticmethod
    def valid_snapshot(data):
        return (isinstance(data, dict) and set(data) == {'version', 'stage'} and
                type(data['version']) is int and data['version'] == 1 and
                isinstance(data['stage'], str) and data['stage'] in STAGES)

    @staticmethod
    def valid_journey(data):
        record = data['lantern_quest']
        if not LanternQuest.valid_snapshot(record):return False
        quests = QuestLog()
        if not quests.restore(data.get('quests')):return False
        stage = record['stage'];status = quests.status(LANTERN_QUEST)
        if quests.states[LANTERN_QUEST]['completed_objectives'] != list(OBJECTIVES[:PREFIX[stage]]):return False
        if stage == 'idle':return status in ('locked', 'available')
        return status == 'active' and quests.status(REGENT_QUEST) == 'completed'

    def _world(self, actor):
        if actor in (self.tomas, self.serene):return self.game._routine_worlds[actor]
        if actor is self.liam:return self.shared.worlds[actor]
        if actor is self.mira:return self.game.mill_quest._mira_world
        if actor in self._worlds:return self._worlds[actor]
        return next((world for world in self.game.scenes.values() if actor in world.npcs), None)

    def _place(self, actor, world, position):
        for scene in self.game.scenes.values():
            if actor in scene.npcs:scene.npcs.remove(actor)
        world.npcs.append(actor);actor.position.update(position)
        actor.scene_id = world.data['id'];actor.moving = False
        if actor in (self.tomas, self.serene):self.game._routine_worlds[actor] = world
        elif actor is self.liam:self.shared.worlds[actor] = world
        elif actor is self.mira:self.game.mill_quest._mira_world = world
        else:self._worlds[actor] = world
        self.paths.pop(actor, None)
        if actor in self.resident_poses:self.resident_poses[actor].sync()

    def _landing(self, actor, desired, world=None):
        world = world or self.town
        avoid = world.probe_rect(self.game.player.position) if world is self.game.world else None
        for radius in (0, 12, 20, 28, 40, 56):
            for dx, dy in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                p = (desired[0]+dx, desired[1]+dy)
                if world.can_stand(p, actor.probe_size, actor, avoid):return p
        return None

    def _clear_action_pose(self):
        for actor in self._pose_actors:
            for key in ('story_sprite', 'story_draw_anchor'):
                if hasattr(actor, key):delattr(actor, key)
        self._pose_actors.clear()

    def release_pose(self):
        if hasattr(self, 'rest'):self.rest.release()
        self._clear_action_pose()
        if not self._owned:return
        self.shared.release_liam(self, reset=True)
        self._liam_claimed = False
        for actor, pose in self.resident_poses.items():
            world, position = self._homes[actor];self._place(actor, world, position);pose.release()
        self.resident_poses.clear()
        for identifier in self._quest_profiles:self.game.social.profiles.pop(identifier, None)
        self._quest_profiles.clear()
        self.tomas.story_following = False;self.tomas.story_paused = False
        for key in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.tomas, key):delattr(self.tomas, key)
        if self._mira_owned:
            self.mira.quest_mode = False;self.mira.story_following = False
            self.mira.end_conversation();self._mira_owned = False
        self._owned = False

    def _claim(self):
        if not self._owned:
            self.game.regent_quest.handoff_tomas()
            self.tomas.story_paused = True;self.tomas.story_following = True
            self.tomas.end_conversation()
            for actor in self.residents.values():self.resident_poses[actor] = ResidentPose(actor, self._homes[actor][0])
            for identifier in ('liam', *self.residents):
                if identifier not in self.game.social.profiles:
                    self.game.social.profiles[identifier] = {'conversations': []}
                    self._quest_profiles.add(identifier)
            self._owned = True
        if not self._liam_claimed:self._liam_claimed = self.shared.request_liam(self)
        if self._liam_claimed:
            self.liam.action = None;self.liam.sort_y = None;self.liam.story_following = True

    def _claim_mira(self):
        if self._mira_owned:return
        self.game.mill_quest._returning = False
        self.mira.quest_mode = True;self.mira.story_following = True
        self.mira.end_conversation();self._mira_owned = True

    def restore(self, data=None):
        if data is not None and not self.valid_snapshot(data):return False
        self.release_pose();self.dialogue = None;self.action = None;self.action_time = 0.
        self._player_route = None;self._player_goal = None
        self.paths.clear();self.retries.clear()
        self.village.reset()
        self.rest.reset()
        self._ready = False;self._class_ready = False;self._gathering = False
        self.stage = data['stage'] if data else ('serene_heard' if self.game.quests.objective_status(LANTERN_QUEST, 'speak_serene') == 'completed'
                                              else 'home_break_done' if self.game.quests.objective_status(LANTERN_QUEST, 'take_break') == 'completed'
                                              else 'elira_visited' if self.game.quests.objective_status(LANTERN_QUEST, 'visit_elira') == 'completed'
                                              else 'neighbours_visited' if self.game.quests.objective_status(LANTERN_QUEST, 'visit_neighbours') == 'completed'
                                              else 'frame_ready' if self.game.quests.objective_status(LANTERN_QUEST, 'build_frame') == 'completed'
                                              else 'permitted' if self.game.quests.objective_status(LANTERN_QUEST, 'join_preparations') == 'completed'
                                              else 'invited' if self.active else 'idle')
        if not self.eligible:self._sync_props();return True
        self._claim()
        # Reconstruct committed stations on launch, never a partly read page or
        # a half-held craft prop. Live transitions use collision-aware walking.
        for identifier, actor in self.residents.items():
            desired = self.points['school_teacher'] if actor is self.mother else self.points['school_children'][identifier]
            landing = self._landing(actor, desired, self.school)
            if landing is not None:self._place(actor, self.school, landing)
            actor.facing = 'front'
        if self.stage == 'idle':
            self._restore_station(self.tomas, self.town, self.points['tomas_invitation'])
            if self._liam_claimed:self._restore_station(self.liam, self.school, self.points['school_liam'])
        elif self.stage in ('invited', 'classroom', 'designed'):
            self._restore_station(self.tomas, self.school, self.points['school_tomas'])
            if self._liam_claimed:self._restore_station(self.liam, self.school, self.points['school_liam'])
        elif self.stage == 'permitted':
            for actor, offset in ((self.liam, (-28, 18)), (self.tomas, (28, 18))):
                if actor is not self.liam or self._liam_claimed:
                    self._restore_station(actor, self.game.world, self.game.player.position+offset)
        elif self.stage in REST_STAGES or self.stage == 'elira_visited':
            self.rest.restore()
        elif self.stage in VILLAGE_STAGES:
            self.village.restore()
        else:
            self._claim_mira();self._gathering = True
            for actor, key in self._workshop_stations():self._restore_station(actor, self.town, self.points[key])
        if self.stage == 'lifted':self._set_action_pose(self.liam, 'liam', 'lift', 99.)
        self._sync_residents();self._sync_props();return True

    def _restore_station(self, actor, world, desired):
        landing = self._landing(actor, desired, world)
        if landing is None:return False
        self._place(actor, world, landing);return True

    def _save(self):self._sync_props();self.village.sync_props();self.rest.sync_props();self.game.save_progress()

    def _transition(self, stage, objective=None):
        if stage == 'frame_ready':self._clear_action_pose()
        if objective:self.game.quests.complete_objective(LANTERN_QUEST, objective)
        self.stage = stage;self.paths.clear();self.retries.clear();self._ready = False;self._save()

    def _speak(self, kind, callback=None):
        if self.game.social.locked:return False
        actors = (self.tomas, self.liam, self.mira, self.serene, self.father, *self.residents.values(), *self.village.actors)
        for actor in actors:
            if self._world(actor) is self.game.world:
                actor.moving = False
                getattr(actor, 'end_conversation', lambda: None)()
        def finished():
            self.dialogue = None
            for actor in actors:getattr(actor, 'end_conversation', lambda: None)()
            if callback:callback()
        result = self.game.social.start_script(self.lines[kind], finished, 'lantern_'+kind)
        self.dialogue = kind if result else None
        if result:self.game.social.blocked.update(actors)
        return result

    def on_dialogue_cancelled(self, identifier):
        if identifier and identifier.startswith('lantern_'):
            self.dialogue = None
            for actor in (self.tomas, self.mira, *self.residents.values()):getattr(actor, 'end_conversation', lambda: None)()

    def can_speak(self, identifier):return True

    def _near(self, desired, radius=60):return self.game.player.position.distance_to(desired) <= radius

    def _target(self):
        if not self.eligible or self.action or not self._ready:return None
        if self.rest.active:return self.rest.target()
        if self.stage == 'frame_ready' or self.stage in VILLAGE_STAGES:return self.village.target()
        if self.stage == 'idle':
            return 'invitation' if self.game.world is self.town and self._near(self.points['invitation'], 62) else None
        if self.stage in ('invited', 'classroom', 'designed'):
            if self.game.world is self.school and self._near(self.points['school'], 86):
                return {'invited': 'classroom', 'classroom': 'design', 'designed': 'permission'}[self.stage]
        if self.game.world is self.town and self._near(self.points['workshop'], 72):
            return {'permitted': 'workshop', 'workshop': 'test_shape', 'tested': 'assemble',
                    'assembled': 'lift', 'lifted': 'frame_ready'}.get(self.stage)
        return None

    def interact(self):
        if self.game.social.locked:return False
        target = self._target()
        if target is None:return False
        return self._speak(target, lambda: self._finished(target))

    def _finished(self, kind):
        if self.rest.finish(kind):return
        if self.village.finish(kind):return
        if kind == 'invitation':
            if self.stage != 'idle' or not self.game.accept_quest(LANTERN_QUEST):return
            self._transition('invited')
        elif kind == 'classroom':self._transition('classroom')
        elif kind == 'design':self._transition('designed')
        elif kind == 'permission':self._transition('permitted', 'join_preparations')
        elif kind == 'workshop':self._transition('workshop')
        elif kind == 'test_shape':self._transition('tested')
        elif kind in ('assemble', 'lift'):
            self.action = kind;self.action_time = 0.;self._ready = False
            self.align_time = 0.
            self._approach_walk_ms = 0.
            self._player_goal = self.points['assemble_player' if kind == 'assemble' else 'lift_player']
            self._player_route = None
        elif kind == 'frame_ready':self._transition('frame_ready', 'build_frame')

    def try_conversation(self, actor):
        if not self.eligible:return None
        result = self.rest.try_conversation(actor)
        if result is not None:return result
        result = self.village.try_conversation(actor)
        if result is not None:return result
        target = self._target()
        if actor is self.tomas and self.stage == 'idle':return self.interact() if target else False
        if actor is self.mother:
            if target in ('classroom', 'permission'):return self.interact()
            if STAGES.index(self.stage) >= 4:return self._speak('mother_after_permission')
            return self._speak('classroom_waiting' if self.stage == 'invited' else 'permission_waiting')
        if actor is self.liam and self._liam_claimed:
            if target in ('classroom', 'design', 'permission'):return self.interact()
            return self._speak('frame_after' if self.stage == 'frame_ready' else
                               'workshop_waiting' if self._mira_owned and self._world(self.mira) is self.game.world else
                               'liam_outing_waiting' if self.stage == 'permitted' else 'design_waiting')
        if actor is self.mira and STAGES.index(self.stage) >= 4:
            if target:return self.interact()
            return self._speak('mira_after' if self.stage == 'frame_ready' else
                               'workshop_waiting' if self._liam_claimed and self._world(self.liam) is self.game.world else 'mira_waiting')
        if actor is self.tomas and self._owned:
            if target:return self.interact()
            if self.stage == 'permitted' and not self._gathering:return self._speak('walk_chat')
            return self._speak('tomas_after' if self.stage == 'frame_ready' else 'invitation_waiting')
        if actor.data['id'] in self.children and self._owned:return self._speak('child_'+actor.data['id'])
        return None

    def marker_for(self, identifier):
        if not self.eligible:return NotImplemented
        result = self.rest.marker_for(identifier)
        if result is not NotImplemented:return result
        result = self.village.marker_for(identifier)
        if result is not NotImplemented:return result
        if identifier == 'tomas':return '!' if self.stage == 'idle' else None
        if identifier == 'liam_mother':return '?' if self.stage in ('invited', 'designed') else None
        if identifier == 'liam':return '?' if self.stage == 'classroom' else None
        if identifier == 'mira_worker':return '?' if self.stage in ('permitted', 'workshop', 'tested', 'assembled', 'lifted') else None
        return NotImplemented

    def tracker_text(self):
        if not self.eligible:return ''
        if self.rest.active:return self.rest.tracker_text()
        if self.stage in VILLAGE_STAGES:return self.village.tracker_text()
        return {'idle': 'Meet Tomas by the sanctuary lantern supplies.',
                'invited': 'Join the lantern preparations at the village school.',
                'classroom': 'Look at Liam’s lantern drawing with him.',
                'designed': 'Agree on the outing with Liam’s mother.',
                'permitted': 'Accompany Liam and Tomas to Mira’s workshop.',
                'workshop': 'Try Liam’s tower design with Mira.',
                'tested': 'Help assemble the lantern frame.',
                'assembled': 'Let Liam try lifting his lantern frame.',
                'lifted': 'See what Liam thinks of his frame.',
                'frame_ready': 'Speak with Mira before seeing the village preparations.'}[self.stage]

    def journal_detail(self):return self.tracker_text()

    def journal_objectives(self):
        return OBJECTIVES[:6] if self.stage in REST_STAGES else OBJECTIVES[:4] if self.stage in VILLAGE_STAGES else OBJECTIVES[:2]

    def interaction_hint(self):
        if self.rest.active:return self.rest.interaction_hint(self._target())
        if self.action:return 'Assembling the frame…' if self.action == 'assemble' else 'Trying the lantern’s balance…'
        if self.stage == 'frame_ready' or self.stage in VILLAGE_STAGES:return self.village.interaction_hint(self._target())
        return {'invitation': 'E: Help Tomas with the lantern preparations',
                'classroom': 'E: Join the school preparation table', 'design': 'E: Look at Liam’s drawing',
                'permission': 'E: Speak with Liam’s mother', 'workshop': 'E: Show Mira the lantern design',
                'test_shape': 'E: Try the tower frame', 'assemble': 'E: Help assemble the frame',
                'lift': 'E: Let Liam try the handle', 'frame_ready': 'E: Look at the finished frame'}.get(self._target(), '')

    def _move(self, actor, desired, seconds, speed=68):
        world = self._world(actor);desired = point(desired);actor.moving = False
        if actor.position.distance_to(desired)<1:self.paths.pop(actor, None);return True
        avoid = world.probe_rect(self.game.player.position) if world is self.game.world else None
        self.retries[actor] = max(0., self.retries.get(actor, 0.)-seconds)
        cached = self.paths.get(actor)
        if cached is None or cached[0] != desired:
            if self.retries[actor]>0:return False
            passing = avoid is not None and getattr(actor, 'story_following', False) and actor.position.distance_to(self.game.player.position)<56
            planning = None if passing else avoid
            route = (town_path(world, actor.position, desired, actor, planning)
                     if world is self.town and actor.position.distance_to(desired)>180 else
                     find_path(world, actor.position, desired, actor.probe_size, actor, planning))
            if route is None and avoid is not None and getattr(actor, 'story_following', False):
                route = find_path(world, actor.position, desired, actor.probe_size, actor)
                passing = route is not None
            if route is None:self.retries[actor] = .3;return False
            cached = self.paths[actor] = (desired, deque(route), passing)
        if cached[2]:avoid = None
        route = cached[1];budget = max(0., seconds)*speed
        while route and budget>1e-7:
            delta = pygame.Vector2(route[0])-actor.position;distance = delta.length()
            if distance<1e-7:route.popleft();continue
            step = min(1., budget, distance);candidate = actor.position+delta/distance*step
            if not world.can_stand(candidate, actor.probe_size, actor, avoid):
                self.paths.pop(actor, None);self.retries[actor] = .2;return False
            actor.position.update(candidate);actor.facing = facing_toward(delta);actor.moving = True
            actor.walk_ms = getattr(actor, 'walk_ms', 0.)+step/speed*1000;budget -= step
            if step>=distance-1e-7:route.popleft()
        return actor.position.distance_to(desired)<1

    def _travel(self, actor, destination, seconds):
        origin = self._world(actor)
        if origin is destination:return True
        queue = deque([(origin, None)]);seen = {origin.path};first = None
        while queue:
            world, edge = queue.popleft()
            if world is destination:first = edge;break
            for door in world.doors:
                other = self.game._load_scene(ROOT/door.data['destination'])
                if other.path not in seen:
                    seen.add(other.path);queue.append((other, edge or (door, other)))
        if first is None:return False
        door, other = first;record = door.data
        if not self._move(actor, record['anchor'], seconds):return False
        if record.get('requires_open') and door.state != 'open':return False
        landing = self._landing(actor, record['spawn'], other)
        if landing is None:return False
        self._place(actor, other, landing)
        arrival = next((d for d in other.doors if d.data['id'] == record.get('arrival_door')), None)
        if arrival:arrival.force_open()
        return other is destination

    def _station(self, actor, world, desired, seconds):
        # Offscreen attendance starts at its agreed station. Visible participants
        # always use the actual room doors and collision-aware walking.
        if self._world(actor) is not self.game.world and world is not self.game.world:
            return self._restore_station(actor, world, desired)
        return self._travel(actor, world, seconds) and self._move(actor, desired, seconds)

    def _workshop_stations(self):
        return ((self.liam, 'workshop_liam'), (self.mira, 'workshop_mira'), (self.tomas, 'workshop_tomas'))

    def _follow(self, seconds):
        for actor, offset in ((self.liam, (-26, 20)), (self.tomas, (26, 30))):
            if actor is self.liam and not self._liam_claimed:continue
            if not self._travel(actor, self.game.world, seconds):continue
            if actor.position.distance_to(self.game.player.position)<32:
                actor.moving = False;continue
            desired = self._landing(actor, self.game.player.position+offset, self.game.world)
            if desired is not None:self._move(actor, desired, seconds, 80)

    def _sync_residents(self):
        for actor, pose in self.resident_poses.items():pose.sync()
        if self._owned:
            direction = self.tomas.facing
            frames = self.tomas.walks[direction]
            frame = frames[int(self.tomas.walk_ms//140)%len(frames)] if self.tomas.moving else self.tomas.idles[direction]
            self.tomas.story_sprite = frame[0] if isinstance(frame, tuple) else frame
            self.tomas.story_draw_anchor = self.tomas.draw_anchor

    def _set_action_pose(self, actor, identifier, kind, time):
        if identifier not in self.poses:return
        meta, actions = self.poses[identifier];frames = actions.get(kind, actions.get('work'))
        if not frames:return
        elapsed = min(time*1000, sum(d for _, d in frames)-1)
        for surface, duration in frames:
            if elapsed<duration:break
            elapsed -= duration
        actor.story_sprite = surface;actor.story_draw_anchor = tuple(meta['draw_anchor'])
        self._pose_actors.add(actor)

    def _action_update(self, seconds):
        player = self.game.player
        if player.position.distance_to(self._player_goal) >= .3:
            self.align_time += seconds
            if self.align_time > 12:
                self.action = None;self._clear_action_pose();self._ready = False;return
            if self._player_route is None:
                route = find_path(self.town, player.position, self._player_goal, self.town.probe_size, None)
                if route is None:
                    self.action = None;self._clear_action_pose();self._ready = False;return
                self._player_route = deque(route)
            budget = seconds
            while self._player_route and budget > 1e-7:
                delta = pygame.Vector2(self._player_route[0])-player.position
                if delta.length() < .04:self._player_route.popleft();continue
                duration = min(budget, delta.length()/72)
                player.walk_ms = self._approach_walk_ms
                before = player.position.copy();player.update(delta, duration, self.town)
                self._approach_walk_ms = player.walk_ms
                if player.position == before:self._player_route = None;break
                budget -= duration
            return
        player.moving = False;player.facing = 'right'
        self.action_time += seconds
        self._set_action_pose(self.liam, 'liam', 'work' if self.action == 'assemble' else 'lift', self.action_time)
        if self.action == 'assemble':self._set_action_pose(self.mira, 'mira', 'work', self.action_time)
        if self.action == 'assemble' or self.action_time < 1.2:
            self._set_action_pose(player, 'caelan', 'work' if self.action == 'assemble' else 'support', self.action_time)
        elif player in self._pose_actors:
            for key in ('story_sprite', 'story_draw_anchor'):
                if hasattr(player, key):delattr(player, key)
            self._pose_actors.discard(player)
        duration = 2.4 if self.action == 'assemble' else 2.1
        if self.action_time>=duration:
            stage = 'assembled' if self.action == 'assemble' else 'lifted'
            self.action = None;self._clear_action_pose();self._transition(stage)

    def surface_prop_visible(self, prop):
        if not self.eligible:return False
        if prop['scene'] == self.school.data['id']:return STAGES.index(self.stage)<4
        return self._gathering or STAGES.index(self.stage)>=5

    def _sync_props(self):
        state = ('ready' if self.stage == 'frame_ready' or self.stage in VILLAGE_STAGES or self.stage in REST_STAGES else
                 'lifted' if self.stage == 'lifted' else
                 'lifted' if self.action == 'lift' and self.action_time > 0 else
                 'partial' if self.action == 'assemble' and self.action_time > 0 else
                 'frame' if STAGES.index(self.stage)>=7 else 'test' if self.stage == 'tested' else
                 'materials' if self.stage == 'workshop' else 'drawing')
        for prop in self.surface_props:
            if prop['id'] == 'craft_surface' and hasattr(self, 'rest') and self.rest.frame_location != 'workshop':
                prop['surface'] = self.rest.workshop_empty
            else:prop['surface'] = prop['states'].get(state, next(iter(prop['states'].values())))

    def _task_blockers(self):
        result = list(self._prior_blockers())
        for prop in self.surface_props:
            if prop['scene'] != self.town.data['id'] or not self.surface_prop_visible(prop) or 'footprint' not in prop:continue
            result.append(pygame.Rect(prop['footprint']))
        if hasattr(self, 'village'):
            for prop in self.village.surface_props:
                if prop['scene'] == self.town.data['id'] and self.village.surface_prop_visible(prop) and 'footprint' in prop:
                    result.append(pygame.Rect(prop['footprint']))
        return tuple(result)

    def on_enter_scene(self, origin, transition):
        self.paths.clear();self.retries.clear();self.village.reset();self.rest.reset()

    def update(self, seconds):
        if self.game.map_open or self.game.quest_ui.journal_open:return
        if not self.eligible:return
        self._claim()
        for actor in (self.tomas, self.liam, *self.residents.values()):actor.moving = False
        if self._mira_owned:self.mira.moving = False
        if self.rest.active:
            self.rest.update(seconds);self._sync_residents();self._sync_props();return
        if self.stage in VILLAGE_STAGES:
            self.village.update(seconds);self._sync_residents();self._sync_props();return
        if self.action:self._action_update(seconds)
        elif not self.game.social.locked:
            attendance = []
            for identifier, actor in self.residents.items():
                desired = self.points['school_teacher'] if actor is self.mother else self.points['school_children'][identifier]
                attendance.append(self._station(actor, self.school, desired, seconds))
            if self.stage in ('idle', 'invited', 'classroom', 'designed'):
                if self._liam_claimed:attendance.append(self._station(self.liam, self.school, self.points['school_liam'], seconds))
                else:attendance.append(False)
                self._class_ready = all(attendance)
                if self.stage == 'idle':
                    self._ready = self._station(self.tomas, self.town, self.points['tomas_invitation'], seconds)
                else:self._ready = self._station(self.tomas, self.school, self.points['school_tomas'], seconds) and self._class_ready
            else:
                if self.stage == 'permitted' and not self._gathering:
                    self._follow(seconds)
                    if self.game.world is self.town and self._near(self.points['workshop'], 90):
                        self._gathering = True;self._claim_mira();self.paths.clear()
                if self._gathering:
                    self._claim_mira()
                    ready = []
                    for actor, key in self._workshop_stations():
                        if actor is self.liam and not self._liam_claimed:continue
                        arrived = self._travel(actor, self.town, seconds) and self._move(actor, self.points[key], seconds)
                        ready.append(arrived)
                        if arrived:
                            actor.facing = ('right' if actor is self.liam else 'left')
                    self._ready = self._liam_claimed and len(ready) == 3 and all(ready)
        if self.stage == 'lifted':self._set_action_pose(self.liam, 'liam', 'lift', 99.)
        self._sync_residents();self._sync_props()

    def draw_world(self, canvas, camera):pass
