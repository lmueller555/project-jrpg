"""The Regent's Road: Caelan welcomes visitors and witnesses adult decisions.

Caelan guides Aldric and Lucan directly to the sanctuary. Durable scene
checkpoints are separate from NPC paths and partially read conversations;
leaving or loading cannot accept unread prose or authorize excavation.
"""
from collections import deque
import json
from pathlib import Path

import pygame

from halden_visit import point, town_path
from npc_routines import find_path
from npc_following import following_facing, idle_following_facing, reset_following_facing
from quests import REGENT_QUEST, MILL_QUEST, LANTERN_QUEST, QuestLog
from regent_actors import StoryActor
from regent_actions import RegentActions
from social import facing_toward

ROOT = Path(__file__).resolve().parent
ART = 'assets/story/regent/'
STAGES = ('idle', 'assigned', 'escorting', 'welcome', 'hosted', 'discussion', 'done')
LEGACY_STAGES = ('idle', 'assigned', 'met', 'dispute', 'releasing', 'escorting',
                 'welcome', 'hosted', 'discussion', 'done')
LEGACY_ESCORT = frozenset(('met', 'dispute', 'releasing', 'escorting'))
OBJECTIVES = ('meet_visitors', 'accompany_visit', 'welcome_party', 'speak_serene')
PREFIX = {'idle': 0, 'assigned': 0, 'escorting': 1, 'welcome': 2,
          'hosted': 3, 'discussion': 3, 'done': 4}


def read(name):return json.loads((ROOT/ART/name).read_text())


class RegentQuest:
    def __init__(self, game):
        self.game = game;self.town = game.town
        self.dining = game._scene_by_id('sanctuary_dining')
        self.hall = game._scene_by_id('sanctuary_hall')
        self.layout = read('layout.json');self.points = self.layout
        self.lines = read('scene.json');art = read('art.json')
        self.actors = {rec['id']: StoryActor(rec, self.town) for rec in art['actors']}
        self.aldric = self.actors['aldric'];self.lucan = self.actors['lucan']
        self.clerk = self.actors['regent_clerk'];self.driver = self.actors['regent_driver']
        self.party = [self.aldric, self.clerk, self.driver, self.lucan]
        self.serene = next(a for a in game.persistent_npcs if a.data['id'] == 'mother_serene')
        self.tomas = next(a for a in game.persistent_npcs if a.data['id'] == 'tomas')
        self._worlds = {a: self.town for a in self.actors.values()}
        self.stage = 'idle';self.dialogue = None;self.action = None
        self.paths = {};self.retries = {};self._owned = False;self._setup = False
        self._tomas_handed_off = False
        self._serene_handed_off = False
        self._preps_ready = False;self._group_ready = False;self._aside_ready = False
        self._meal_ready = False
        self.trail = deque(maxlen=1024);self.last_scene = None
        self.surface_props = []
        for record in art['props']:
            states = {key: self.town.image(path) for key, path in record['states'].items()}
            self.surface_props.append({**record, 'states': states,
                                       'surface': next(iter(states.values()))})
        self.town.attach_routine_props(self)
        self.dining.attach_routine_props(self)
        self._prior_blockers = getattr(self.town, 'task_blockers', lambda: ())
        self.town.task_blockers = self._task_blockers
        self._prior_dining_blockers = getattr(self.dining, 'task_blockers', lambda: ())
        self.dining.task_blockers = self._dining_blockers
        self.scene_actions = RegentActions(self)

    @property
    def active(self):return self.game.quests.status(REGENT_QUEST) in ('active', 'ready')
    @property
    def eligible(self):
        arrival = getattr(self.game, 'regent_arrival', None)
        return (self.game.quests.status(REGENT_QUEST) != 'locked'
                and (arrival is None or arrival.arrival_complete))
    @property
    def locks_player(self):return False
    def to_dict(self):return {'version': 2, 'stage': self.stage}

    @staticmethod
    def valid_snapshot(data):
        if (not isinstance(data, dict) or set(data) != {'version', 'stage'}
                or type(data['version']) is not int or not isinstance(data['stage'], str)):
            return False
        stages = LEGACY_STAGES if data['version'] == 1 else STAGES if data['version'] == 2 else ()
        return data['stage'] in stages

    @staticmethod
    def migrate_snapshot(data):
        if not RegentQuest.valid_snapshot(data):return data
        return {'version': 2, 'stage': ('escorting' if data['version'] == 1
                and data['stage'] in LEGACY_ESCORT else data['stage'])}

    @staticmethod
    def valid_journey(data):
        record = data['regent_quest']
        if not RegentQuest.valid_snapshot(record):return False
        record = RegentQuest.migrate_snapshot(record)
        quests = QuestLog()
        if not quests.restore(data.get('quests')):return False
        status = quests.status(REGENT_QUEST);stage = record['stage']
        done = quests.states[REGENT_QUEST]['completed_objectives']
        if done != list(OBJECTIVES[:PREFIX[stage]]):return False
        if stage == 'idle':return status in ('locked', 'available')
        if quests.status(MILL_QUEST) != 'completed':return False
        return status == ('completed' if stage == 'done' else 'active')

    def _world(self, actor):
        return self.game._routine_worlds[actor] if actor in (self.serene, self.tomas) else self._worlds[actor]

    def _place(self, actor, world, position):
        for room in self.game.scenes.values():
            if actor in room.npcs:room.npcs.remove(actor)
        world.npcs.append(actor);actor.position.update(position)
        actor.scene_id = world.data['id'];actor.moving = False
        if actor in (self.serene, self.tomas):self.game._routine_worlds[actor] = world
        else:self._worlds[actor] = world
        if actor in self.actors.values():actor.story_visible = True
        self.paths.pop(actor, None)
        reset_following_facing(actor)

    def _hide(self, actor):
        for world in self.game.scenes.values():
            if actor in world.npcs:world.npcs.remove(actor)
        actor.story_visible = False;actor.moving = False;actor.end_conversation()

    def release_pose(self):
        self.scene_actions.release()
        if not self._owned:return
        for actor in (self.serene, self.tomas):
            if self._handed_off(actor):continue
            for key in ('story_sprite', 'story_draw_anchor'):
                if hasattr(actor, key):delattr(actor, key)
            actor.story_following = False
            reset_following_facing(actor)
            if actor in (self.serene, self.tomas):actor.story_paused = False
            actor.end_conversation()
        self._owned = False

    def _handed_off(self, actor):
        return ((actor is self.serene and self._serene_handed_off) or
                (actor is self.tomas and self._tomas_handed_off))

    def _claim(self):
        self._owned = True
        for actor in (self.serene, self.tomas):
            if self._handed_off(actor):continue
            actor.story_paused = True;actor.story_following = False
            actor.end_conversation()
        for actor in self.party:actor.story_following = self.stage != 'idle'

    def restore(self, data=None):
        if data is not None and not self.valid_snapshot(data):return False
        self.release_pose();self.dialogue = None;self.action = None
        self.scene_actions.reset()
        self._tomas_handed_off = False
        self._serene_handed_off = False
        self.paths.clear();self.retries.clear();self.trail.clear();self.last_scene = None
        self._preps_ready = False;self._group_ready = False;self._setup = False
        self._meal_ready = False
        if data:self.stage = self.migrate_snapshot(data)['stage']
        else:
            status = self.game.quests.status(REGENT_QUEST)
            done = len(self.game.quests.states[REGENT_QUEST]['completed_objectives'])
            self.stage = ('done' if status == 'completed' else
                          ('assigned', 'escorting', 'welcome', 'hosted')[min(3, done)] if status == 'active' else 'idle')
        for actor in self.actors.values():self._hide(actor)
        if not self.eligible:return True
        self._claim();self._setup_stage(force=True)
        self._sync_props();self._pose_owned()
        return True

    def _landing(self, actor, desired, world=None):
        world = world or self.town
        avoid = world.probe_rect(self.game.player.position) if world is self.game.world else None
        for radius in (0, 12, 20, 28, 40):
            for dx, dy in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                value = (desired[0]+dx, desired[1]+dy)
                if world.can_stand(value, actor.probe_size, actor, avoid):return value
        return None

    def world_for_station(self, key):
        """Resolve a quest station without confusing room-local coordinates."""
        return self.dining if key in self.points['dining_stations'] else self.town

    def _stage_routine(self, actor, desired, force):
        if force or (self._world(actor) is not self.game.world
                     and self.dining is not self.game.world):
            landing = self._landing(actor, desired, self.dining)
            if landing is not None:self._place(actor, self.dining, landing);return True
        return self._travel(actor, self.dining, .05) and self._move(actor, desired, .05)

    def _setup_stage(self, force=False):
        self._claim()
        serene_point = ('aftermath' if self.stage in ('discussion', 'done') else
                        'serene_meal' if self.stage in ('welcome', 'hosted') else 'serene')
        ready = [True if self._serene_handed_off else self._stage_routine(self.serene, self.points[serene_point], force),
                 True if self._tomas_handed_off else self._stage_routine(self.tomas, self.points['tomas'], force)]
        self._preps_ready = all(ready)
        phase = 'arrival' if self.stage in ('idle', 'assigned', 'escorting') else 'courtyard'
        world = self.game.world if self.stage == 'escorting' else self.dining if phase == 'courtyard' else self.town
        for index, (actor, prefix) in enumerate(self._party_keys()):
            # A legacy roadside checkpoint becomes an ordinary escort beside
            # the saved player, never a completed cart settlement or a jump to lunch.
            target = (self.game.player.position + pygame.Vector2(((-28,28),(28,28),(-42,0),(42,0))[index])
                      if self.stage == 'escorting' else self.points[prefix+'_'+phase])
            if self.stage in ('discussion', 'done') and actor is self.aldric:target = self.points['aldric_aside']
            landing = self._landing(actor, target, world)
            if landing is not None:self._place(actor, world, landing)
        self._setup = self._preps_ready
        self._group_ready = self.stage in ('welcome', 'hosted', 'discussion', 'done')
        self._aside_ready = self.stage in ('discussion', 'done')
        if self.stage in ('welcome', 'hosted'):
            self._meal_ready = all(self._world(actor) is self.dining
                and actor.position.distance_to(seat['approach']) < 1
                for actor in (*self.party, self.serene, self.tomas)
                if (seat := self.points.get('meal_seats', {}).get(actor.data['id'])))

    def _party_keys(self):
        return [(self.aldric, 'aldric'), (self.clerk, 'clerk'),
                (self.driver, 'driver'), (self.lucan, 'lucan')]

    def _save(self):self._sync_props();self.game.save_progress()

    def _transition(self, stage):
        self.stage = stage;self._group_ready = False
        self._meal_ready = self._meal_ready and stage in ('welcome', 'hosted')
        self.paths.clear();self.retries.clear();self.trail.clear();self.last_scene = None
        self._save()

    def _complete(self, objective):return self.game.quests.complete_objective(REGENT_QUEST, objective)

    def _speak(self, kind, callback=None):
        if self.game.social.locked:return False
        actors = tuple(actor for actor in (*self.party, self.serene, self.tomas)
                       if not self._handed_off(actor))
        for actor in actors:
            if self._world(actor) is self.game.world:
                actor.moving = False;actor.facing = facing_toward(self.game.player.position-actor.position)
                actor.end_conversation()
        def finished():
            self.dialogue = None
            for actor in actors:actor.end_conversation()
            if callback is not None:callback()
        source = kind
        if kind == 'arrival':
            if self.game.inventory.quantity('caelan_gearblade') == 0:source = 'arrival_unarmed'
            elif not self.game.mill_quest.cups_placed:source = 'arrival_before_homecoming'
        self._dialogue_lines = self.lines[source]
        result = self.game.social.start_script(self._dialogue_lines, finished, 'regent_'+kind)
        self.dialogue = kind if result else None
        if result:self.game.social.blocked.update(actors)
        return result

    def on_dialogue_cancelled(self, identifier):
        if identifier and identifier.startswith('regent_'):
            self.scene_actions.release()
            self.dialogue = None
            for actor in (*self.party, self.serene, self.tomas):
                if not self._handed_off(actor):actor.end_conversation()

    def can_speak(self, identifier):
        if identifier in self.actors:return self.actors[identifier].story_visible
        return True

    def marker_for(self, identifier):
        if not self.eligible:return NotImplemented
        if identifier == 'mother_serene':
            if self._serene_handed_off:return NotImplemented
            return '!' if self.stage == 'idle' else '?' if self.stage == 'discussion' and self._aside_ready else None
        if identifier == 'aldric':return '?' if self.stage in ('assigned', 'welcome', 'hosted') else None
        if identifier in ('lucan', 'regent_clerk', 'regent_driver'):return None
        return NotImplemented

    def _near(self, where, radius=38):return self.game.player.position.distance_to(where)<=radius

    def try_conversation(self, actor):
        if not self.eligible:return None
        if self._handed_off(actor):return None
        if (actor in (*self.party, self.serene, self.tomas)
                and self._world(actor) is not self.game.world):return False
        if actor is self.serene:
            if self.stage == 'idle':return self._speak('preparations', self._accept) if self._preps_ready else False
            if self.stage == 'discussion':
                return self._speak('aftermath', self._finish) if self._aside_ready else False
            if self.stage == 'escorting':return False
            if self.stage == 'welcome':return self._speak('welcome', self._welcomed) if self._group_ready else False
            if self.stage == 'hosted':return self._speak('discussion', self._discussed) if self._group_ready else False
            return self._speak('serene_after' if self.stage == 'done' else 'preparations_after')
        if actor is self.tomas and self._owned:
            return self._speak('hospitality_after' if self.stage in ('hosted', 'discussion', 'done') else 'tomas_waiting')
        if actor is self.aldric:
            if self.stage == 'idle':return self._speak('arrival_waiting')
            if self.stage == 'assigned':return self._speak('arrival', self._met)
            if self.stage == 'escorting':return False
            if self.stage == 'welcome':return self._speak('welcome', self._welcomed) if self._group_ready else False
            if self.stage == 'hosted':return self._speak('discussion', self._discussed) if self._group_ready else False
            return self._speak('aldric_after' if self.stage in ('discussion', 'done') else 'arrival_reminder')
        if actor is self.driver:return self._speak('driver_after')
        if actor is self.clerk:return self._speak('clerk_after' if self.stage in ('discussion', 'done') else 'clerk_waiting')
        if actor is self.lucan:return self._speak('lucan_after' if self.stage in ('discussion', 'done') else 'lucan_waiting')
        return None

    def _target(self):
        if not self.eligible:return None
        if self.game.world is self.dining:
            if self.stage == 'idle' and self._preps_ready and self._near(self.points['preparations']):return 'preparations'
            if self.stage == 'welcome' and self._group_ready and self._near(self.points['welcome'], 60):return 'welcome'
            if self.stage == 'hosted' and self._group_ready and self._near(self.points['discussion'], 60):return 'discussion'
            if self.stage == 'discussion' and self._aside_ready and self._near(self.points['aftermath']):return 'aftermath'
        elif self.game.world is self.town:
            if self.stage == 'assigned' and self._near(self.points['arrival'], 48):return 'arrival'
        return None

    def interact(self):
        if self.game.social.locked:return False
        target = self._target()
        callbacks = {'preparations': self._accept, 'arrival': self._met,
                     'welcome': self._welcomed, 'discussion': self._discussed, 'aftermath': self._finish}
        return self._speak(target, callbacks[target]) if target is not None else False

    def _accept(self):
        if self.stage != 'idle' or not self._preps_ready:return
        if self.game.world is not self.dining or not self._near(self.serene.position, 52):return
        if not self.game.accept_quest(REGENT_QUEST):return
        self._transition('assigned');self._setup_stage(force=False)

    def _met(self):
        if self.stage != 'assigned':return
        self._complete('meet_visitors');self._transition('escorting')

    def _welcomed(self):
        if self.stage != 'welcome':return
        self._complete('welcome_party');self._transition('hosted')

    def _discussed(self):
        if self.stage != 'hosted':return
        self._aside_ready = False;self._transition('discussion')

    def _finish(self):
        if self.stage != 'discussion':return
        self._complete('speak_serene')
        if not self.game.quests.turn_in(REGENT_QUEST, 'mother_serene'):return
        self.game.social.flags.add('CH01_MQ03_COMPLETE')
        self.game.quests.unlock(LANTERN_QUEST)
        self._transition('done')

    def handoff_tomas(self):
        """MQ04 borrows the actual brother without moving the visit's party."""
        if self._tomas_handed_off:return
        self._tomas_handed_off = True
        self.paths.pop(self.tomas, None);self.tomas.end_conversation()
        for key in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.tomas, key):delattr(self.tomas, key)

    def handoff_serene(self):
        """A later scene borrows Serene without this visit reclaiming her."""
        if self._serene_handed_off:return
        self._serene_handed_off = True
        self.paths.pop(self.serene, None);self.retries.pop(self.serene, None)
        self.serene.end_conversation()
        for key in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.serene, key):delattr(self.serene, key)

    def interaction_hint(self):
        if (self.stage == 'discussion' and not self._aside_ready
                and self.game.world is self.dining and self._near(self.points['aftermath'], 60)):
            return 'Let Aldric step aside before speaking with Serene.'
        target = self._target()
        return {'preparations': 'E: Help welcome the visitors', 'arrival': 'E: Greet Regent Aldric',
                'welcome': 'E: Join the sanctuary welcome', 'discussion': 'E: Listen to Aldric and Serene',
                'aftermath': 'E: Speak with Mother Serene'}.get(target, '')

    def tracker_text(self):
        if not self.eligible:return ''
        return {'idle': 'Meet Mother Serene in the sanctuary dining room.',
                'assigned': 'Meet the visitors by the lower bridge.',
                'escorting': 'Bring Aldric’s party through the sanctuary hall to the dining room.',
                'welcome': 'Join the welcome in the sanctuary dining room.',
                'hosted': 'Listen to Aldric and Serene after the meal.',
                'discussion': 'Speak privately with Mother Serene.',
                'done': ''}.get(self.stage, '')

    def journal_detail(self):return self.tracker_text()

    def _move(self, actor, desired, seconds, speed=74):
        with following_facing(actor, seconds):
            return self._move_impl(actor, desired, seconds, speed)

    def _move_impl(self, actor, desired, seconds, speed=74):
        world = self._world(actor);desired = point(desired);actor.moving = False
        if actor.position.distance_to(desired)<1:self.paths.pop(actor, None);return True
        avoid = world.probe_rect(self.game.player.position) if world is self.game.world else None
        self.retries[actor] = max(0., self.retries.get(actor, 0.)-seconds)
        cached = self.paths.get(actor)
        if cached is None or cached[0] != desired:
            if self.retries[actor]>0:return False
            passing = (avoid is not None and getattr(actor, 'story_following', False) and
                       world.probe_rect(actor.position, actor.probe_size).colliderect(avoid))
            planning_avoid = None if passing else avoid
            route = (town_path(world, actor.position, desired, actor, planning_avoid)
                     if world is self.town and actor.position.distance_to(desired)>180 else
                     find_path(world, actor.position, desired, actor.probe_size, actor, planning_avoid))
            if (route is None and avoid is not None and getattr(actor, 'story_following', False)
                    and actor.position.distance_to(self.game.player.position)<56):
                # Escorted visitors are already nonblocking to the player.
                # Let them use the same courtesy at a single-person threshold;
                # terrain, doors and unrelated NPC feet remain solid.
                route = find_path(world, actor.position, desired, actor.probe_size, actor)
                passing = route is not None
            if route is None:self.retries[actor] = .3;return False
            self.paths[actor] = (desired, deque(route), passing);cached = self.paths[actor]
        if len(cached)>2 and cached[2]:avoid = None
        route = cached[1];budget = max(0., seconds)*speed
        while route and budget>1e-7:
            delta = pygame.Vector2(route[0])-actor.position;distance = delta.length()
            if distance<1e-7:route.popleft();continue
            travel = min(1., budget, distance);candidate = actor.position+delta/distance*travel
            if not world.can_stand(candidate, actor.probe_size, actor, avoid):
                self.paths.pop(actor, None);self.retries[actor] = .2;return False
            actor.position.update(candidate);actor.facing = facing_toward(delta)
            actor.moving = True;actor.walk_ms = getattr(actor, 'walk_ms', 0.)+travel/speed*1000;budget -= travel
            if travel>=distance-1e-7:route.popleft()
        return actor.position.distance_to(desired)<1

    def _destination(self, record):return self.game._load_scene(ROOT/record['destination'])

    def _travel(self, actor, destination, seconds):
        origin = self._world(actor)
        if origin is destination:return True
        queue = deque([(origin, None)]);seen = {origin.path};first = None
        while queue:
            world, first_edge = queue.popleft()
            if world is destination:first = first_edge;break
            for door in world.doors:
                other = self._destination(door.data)
                if other.path not in seen:
                    seen.add(other.path);queue.append((other, first_edge or (door.data['anchor'], door.data, other, door)))
            for link in world.data.get('world_links', []):
                other = self._destination(link)
                if other.path not in seen:
                    seen.add(other.path);queue.append((other, first_edge or (link['position'], link, other, None)))
        if first is None:return False
        anchor, record, other, door = first
        if not self._move(actor, anchor, seconds):return False
        if door is not None and record.get('requires_open') and door.state != 'open':return False
        landing = self._landing(actor, record['spawn'], other)
        if landing is None:return False
        self._place(actor, other, landing)
        arrival = next((d for d in other.doors if d.data['id'] == record.get('arrival_door')), None)
        if arrival is not None:arrival.force_open()
        return other is destination

    def _follow_party(self, seconds):
        player = self.game.player.position
        if self.last_scene is not self.game.world:
            self.last_scene = self.game.world;self.trail.clear()
        if not self.trail or pygame.Vector2(self.trail[-1]).distance_to(player)>=4:self.trail.append(point(player))
        for index, actor in enumerate(self.party):
            if not self._travel(actor, self.game.world, seconds):continue
            if actor.position.distance_to(player)<28+index*12:
                actor.moving = False;self.paths.pop(actor, None)
                idle_following_facing(actor, seconds);continue
            # Different trail distances give the visitors room without granting
            # them a collision wall against the player who is guiding them.
            wanted = 32+index*18;length = 0.;goal = self.trail[-1]
            for old in reversed(self.trail):
                length += pygame.Vector2(goal).distance_to(old);goal = old
                if length>=wanted:break
            if actor.position.distance_to(goal)<6 and actor.position.distance_to(player)>wanted+20:
                goal = point(player+pygame.Vector2(((-28, 28), (28, 28), (-42, 0), (42, 0))[index]))
            landing = self._landing(actor, goal, self.game.world)
            if landing is not None:self._move(actor, landing, seconds, 100)

    def _group_to(self, phase, seconds):
        ready = []
        world = self.dining if phase == 'courtyard' else self.town
        members = self._party_keys()
        if phase == 'courtyard':
            members += [(self.serene, 'serene_meal'), (self.tomas, 'tomas')]
        for actor, prefix in members:
            if self._handed_off(actor):continue
            seat = self.points.get('meal_seats', {}).get(actor.data['id']) if phase == 'courtyard' else None
            desired = (seat['approach'] if seat else self.points[prefix]
                       if actor in (self.serene, self.tomas) else self.points[prefix+'_'+phase])
            ready.append(self._travel(actor, world, seconds) and self._move(actor, desired, seconds))
        if phase == 'courtyard':
            self._meal_ready = all(ready)
        return all(ready)

    def _pose_owned(self):
        for actor in (self.serene, self.tomas):
            if self._handed_off(actor):continue
            if not self._owned or actor not in self._world(actor).npcs:continue
            direction = actor.facing
            frames = actor.walks[direction]
            if actor.moving:
                frame = frames[int(getattr(actor, 'walk_ms', 0.)//140)%len(frames)]
                image = frame[0] if isinstance(frame, tuple) else frame
            else:image = actor.idles[direction]
            actor.story_sprite = image;actor.story_draw_anchor = actor.draw_anchor

    def surface_prop_visible(self, prop):
        if not self.eligible:return False
        if prop['scene'] == self.dining.data['id']:return True
        if prop['id'] == 'regent_wagon':return True
        return self.stage != 'idle'

    def _sync_props(self):
        for prop in self.surface_props:
            prop['surface'] = prop['states'].get('waiting', next(iter(prop['states'].values())))

    def _task_blockers(self):
        blockers = list(self._prior_blockers())
        for prop in self.surface_props:
            if (prop['scene'] == self.town.data['id'] and prop.get('blocker')
                    and self.surface_prop_visible(prop)):
                blockers.append(pygame.Rect(prop['blocker']))
        return blockers

    def _dining_blockers(self):
        blockers = list(self._prior_dining_blockers())
        for prop in self.surface_props:
            if (prop['scene'] == self.dining.data['id'] and prop.get('blocker')
                    and self.surface_prop_visible(prop)):
                blockers.append(pygame.Rect(prop['blocker']))
        return blockers

    def on_enter_scene(self, origin, transition):
        self.trail.clear();self.last_scene = None;self.paths.clear()

    def update(self, seconds):
        if self.game.map_open or self.game.quest_ui.journal_open:return
        if not self.eligible:return
        if not self._setup:
            self._setup_stage(force=False)
        if not self._setup:return
        for actor in (*self.party, self.serene, self.tomas):
            if not self._handed_off(actor):actor.moving = False
        if not self.dialogue:
            if self.stage == 'escorting':
                self._follow_party(seconds)
                if self.game.world is self.dining and self._near(self.points['welcome'], 58) and self._world(self.aldric) is self.dining and self.aldric.position.distance_to(self.points['welcome'])<96:
                    self._complete('accompany_visit');self._transition('welcome')
            elif self.stage in ('welcome', 'hosted'):
                self._group_ready = self._group_to('courtyard', seconds)
            elif self.stage in ('discussion', 'done'):
                aside = self._landing(self.aldric, self.points['aldric_aside'], self.dining)
                aldric_ready = aside is not None and self._move(self.aldric, aside, seconds, 52)
                serene_ready = self._serene_handed_off
                if not serene_ready:
                    station = self._landing(self.serene, self.points['aftermath'], self.dining)
                    serene_ready = station is not None and self._move(self.serene, station, seconds, 48)
                self._aside_ready = aldric_ready and serene_ready
        self._pose_owned();self._sync_props()
        self.scene_actions.update(seconds)

    def draw_world(self, canvas, camera):self.scene_actions.draw_world(canvas, camera)
