"""Authored sanctuary morning with short, resumable physical scene beats.

The public checkpoint is a whole scene. Timed poses and dialogue are joined by
completion barriers, so reading quickly cannot omit a necessary movement.
"""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path

import pygame

from npc_routines import find_path
from quests import OPENING_QUEST
from social import facing_toward

ROOT = Path(__file__).resolve().parent
POSES = 'assets/story/sanctuary_opening/poses/'
STAGES = frozenset(('disabled', 'wake', 'explore', 'breakfast', 'assignment', 'acceptance', 'done'))


class OpeningSequence:
    def __init__(self, game):
        self.game = game
        self.data = json.loads((ROOT/'assets/story/opening.json').read_text(encoding='utf-8'))
        self.stage = 'disabled'
        self._animations = {}
        self._walk_frames = {}
        self._actions = deque()
        self._action = None
        self._action_time = 0.0
        self._phase = None
        self._sound_events = []
        self._sleeping = False
        self._bed_occlusion = None
        self._arriving = False
        self._arrival_path = None
        self._arrival_retry = 0.0
        self._footstep_distance = 0.0
        self._seen_cue_pages = set()
        self._wake_started = self._wake_finished = self._wake_dialogue_done = False
        self._meal_finished = self._meal_dialogue_done = False
        self._cup_finished = self._cup_dialogue_done = False
        self._leaving_breakfast = False
        self._plate_index = 0
        self._cup_position = None
        self._cup_placed = False
        self._serene_glance = False

    @property
    def active(self):return self.stage not in ('disabled', 'done')

    @property
    def locks_player(self):
        # Physical bed/chair poses constrain the body; merely displaying speech
        # does not. In particular the invitation and accepted quest follow-up
        # remain ordinary live conversations.
        return ((self.stage == 'wake' and (self._sleeping or self.in_action)) or
                (self.stage == 'breakfast' and self._phase != 'greeting'))

    @property
    def player_visible(self):return not self._sleeping

    @property
    def controls_player(self):return self.stage == 'breakfast' and self._arriving

    @property
    def in_action(self):return self._action is not None or bool(self._actions) or self._arriving

    @property
    def action_name(self):
        if self._arriving:return 'walk_to_breakfast'
        if self._action is not None:return self._action['name']
        return self._actions[0]['name'] if self._actions else None

    def request_movement(self, direction):
        """A steering gesture asks a seated player to finish up and stand.

        Required prop and chair motions finish before movement resumes, even
        after a short tap. Unread prose cannot keep the player seated forever.
        """
        if (self.stage == 'breakfast' and self._phase in ('meal', 'cup') and
                pygame.Vector2(direction).length_squared()):
            self._leaving_breakfast = True
            self._check_progress()

    def drain_sound_events(self):
        result, self._sound_events = self._sound_events, []
        return result

    def record_footsteps(self, travel):
        """Two contacts per 560 ms walk cycle, shared by guided and free steps."""
        if travel <= 0:
            self._footstep_distance = 0.0
            return
        self._footstep_distance += travel
        while self._footstep_distance+1e-8 >= 20.16:
            self._sound_events.append('footstep')
            self._footstep_distance -= 20.16

    def camera_focus(self):
        """Retain the scene hook without taking over live player tracking."""
        return None

    def on_dialogue_cancelled(self, identifier):
        """Settle a live exchange without treating unread prose as completed."""
        if identifier == 'opening_wake' and self.stage == 'wake':
            self._wake_dialogue_done = True
            self._queue_wake();self._check_progress()
        elif identifier == 'opening_greeting' and self.stage == 'breakfast':
            # The invitation can be heard again on the next dining-room visit;
            # walking away must not start a guided walk from another room.
            self.stage = 'explore';self._phase = None
            self._save()
        elif identifier == 'opening_acceptance' and self.stage == 'acceptance':
            # Acceptance was already explicit and saved. The remaining banter
            # can be left freely without leaving either actor story-paused.
            self._finish_acceptance()

    def can_speak(self, npc_id):
        if npc_id not in ('mother_serene', 'tomas'):return True
        return self.stage in ('disabled', 'done') or (self.stage == 'assignment' and npc_id == 'mother_serene')

    def hint_text(self):
        if self.stage == 'wake':return 'Morning bells. A knock at the door.'
        if self.stage == 'explore':
            if self.game.world.data['id'] == 'sanctuary_hall':return 'Breakfast is through the northeast doorway.'
            return 'Join Tomas and Mother Serene for breakfast.'
        if self.stage == 'assignment':return "Speak to Mother Serene about today's visits."
        return ''

    def _inspect_target(self):
        if (self.stage not in ('explore', 'assignment', 'done') or
                self.game.world.data['id'] != 'sanctuary_bedroom' or
                self.game.social.locked or self.game.map_open or self.game.quest_ui.journal_open):return None
        destinations = self.game.world.data.get('destinations', {})
        nearby = [(self.game.player.position.distance_squared_to(destinations[key]), key)
                  for key in self.data['inspections'] if key in destinations
                  and self.game.player.position.distance_squared_to(destinations[key]) <= 22*22]
        return min(nearby)[1] if nearby else None

    def _can_join_breakfast(self):
        return (self.stage == 'explore' and
                self.game.world.data['id'] == 'sanctuary_dining' and
                not self.game.social.locked and not self.game.map_open and
                not self.game.quest_ui.journal_open and
                min(self.game.player.position.distance_squared_to(self.data[key])
                    for key in ('caelan_breakfast_floor', 'tomas_breakfast_floor')) <= 40*40)

    def interaction_hint(self):
        if self._can_join_breakfast():return 'E: join breakfast'
        key = self._inspect_target()
        return f"E: inspect {self.data['inspections'][key]['label']}" if key else ''

    def inspect_nearby(self):
        if self._can_join_breakfast():return self._start_breakfast()
        key = self._inspect_target()
        if key is None:return False
        return self.game.social.start_script(
            [{'speaker': 'caelan', 'text': self.data['inspections'][key]['text']}],
            identifier='bedroom_inspect_'+key)

    def to_dict(self):return {'version': 1, 'stage': self.stage}

    @staticmethod
    def valid_snapshot(data):
        return (isinstance(data, dict) and set(data) == {'version', 'stage'} and
                type(data['version']) is int and data['version'] == 1 and
                isinstance(data['stage'], str) and data['stage'] in STAGES)

    def _actor(self, identifier):
        return next(actor for actor in self.game.persistent_npcs if actor.data['id'] == identifier)

    def _image(self, name):return self.game.town.image(POSES+name)

    def _animation(self, name):
        if name not in self._animations:
            path = ROOT/POSES/name/'animation.json'
            metadata = json.loads(path.read_text(encoding='utf-8'))
            self._animations[name] = metadata['frames']
        return self._animations[name]

    def _duration(self, name):return sum(frame['duration_ms'] for frame in self._animation(name))/1000

    def _frame(self, name, elapsed, repeat=False):
        frames = self._animation(name)
        duration = self._duration(name)
        cursor = (elapsed % duration if repeat else min(elapsed, duration-1e-8))*1000
        for index, record in enumerate(frames):
            if cursor < record['duration_ms']:return index, record
            cursor -= record['duration_ms']
        return len(frames)-1, frames[-1]

    def _pose(self, actor, name, elapsed, position, repeat=False, sort_y=206):
        _, record = self._frame(name, elapsed, repeat)
        self._body(actor, self._image(name+'/'+record['file']), position, record.get('draw_anchor', (12, 30)), sort_y)
        return record

    def _walking_pose(self, actor, identity, direction, elapsed, position):
        key = (identity, direction)
        if key not in self._walk_frames:
            folder = f'assets/characters/{identity}/walk_{direction}'
            metadata = json.loads((ROOT/folder/'animation.json').read_text(encoding='utf-8'))
            self._walk_frames[key] = [(self.game.town.image(folder+'/'+frame['file']), frame['duration_ms'])
                                      for frame in metadata['frames']]
        frames = self._walk_frames[key]
        cursor = (elapsed*1000) % sum(duration for _, duration in frames)
        image = frames[-1][0]
        for candidate, duration in frames:
            if cursor < duration:
                image = candidate;break
            cursor -= duration
        self._body(actor, image, position)

    @staticmethod
    def _body(actor, image, position, anchor=(12, 30), sort_y=206):
        actor.story_visible = True
        actor.story_sprite = image
        actor.story_position = tuple(position)
        actor.story_draw_anchor = tuple(anchor)
        actor.story_sort_y = sort_y

    @staticmethod
    def _clear_pose(actor):
        for attribute in ('story_sprite', 'story_position', 'story_sort_y', 'story_draw_anchor', 'story_visible'):
            if hasattr(actor, attribute):delattr(actor, attribute)

    def _clear(self):
        self.game.social.cancel_script()
        self._clear_pose(self.game.player)
        for actor in self.game.persistent_npcs:
            if actor.data['id'] in ('mother_serene', 'tomas'):
                actor.story_paused = False
                self._clear_pose(actor)
        self._actions.clear();self._action = None;self._action_time = 0.0
        self._sound_events.clear();self._seen_cue_pages.clear()
        self._phase = None;self._sleeping = False;self._bed_occlusion = None
        self._arriving = False;self._arrival_path = None;self._arrival_retry = 0.0
        self._footstep_distance = 0.0
        self._wake_started = self._wake_finished = self._wake_dialogue_done = False
        self._meal_finished = self._meal_dialogue_done = False
        self._cup_finished = self._cup_dialogue_done = False
        self._leaving_breakfast = False
        self._plate_index = 0;self._cup_position = None;self._cup_placed = False
        self._serene_glance = False

    def _place_actor(self, identifier, scene_id, point, step, facing):
        actor = self._actor(identifier)
        destination = self.game._scene_by_id(scene_id)
        for scene in self.game.scenes.values():
            while actor in scene.npcs:scene.npcs.remove(actor)
        actor.end_conversation()
        actor.select_step(step, position=point, scene_id=scene_id, facing=facing)
        destination.npcs.append(actor)
        self.game._routine_worlds[actor] = destination
        actor.story_paused = True
        self._clear_pose(actor)
        return actor

    def _prepare_serene(self):
        return self._place_actor('mother_serene', 'sanctuary_dining', (288, 214), 'sort_provisions', 'back')

    def _prepare_dining(self):
        self._prepare_serene()
        actor = self._place_actor('tomas', 'sanctuary_dining', self.data['tomas_breakfast_floor'], 'walk_to_model', 'left')
        self._body(actor, self._image('tomas_seated.png'), self.data['tomas_seated_position'])

    def _save(self):
        save = getattr(self.game, 'save_progress', None)
        if save is not None:save()

    def _queue(self, name, duration, update, finish=None, sounds=()):
        self._actions.append({'name': name, 'duration': duration, 'update': update,
                              'finish': finish, 'sounds': list(sounds), 'emitted': set()})

    def _update_actions(self, seconds):
        budget = max(0.0, seconds)
        while self._action is not None or self._actions:
            if self._action is None:
                self._action = self._actions.popleft();self._action_time = 0.0
            action = self._action
            consumed = min(budget, action['duration']-self._action_time)
            self._action_time += consumed
            action['update'](self._action_time)
            for index, (when, kind) in enumerate(action['sounds']):
                if self._action_time+1e-8 >= when and index not in action['emitted']:
                    self._sound_events.append(kind);action['emitted'].add(index)
            if self._action_time+1e-8 < action['duration']:break
            budget = max(0.0, budget-consumed)
            self._action = None;self._action_time = 0.0
            if action['finish'] is not None:action['finish']()
            if budget <= 1e-9:break

    @staticmethod
    def _lerp(a, b, fraction):
        fraction = max(0.0, min(1.0, fraction))
        smooth = fraction*fraction*(3-2*fraction)
        return pygame.Vector2(a).lerp(b, smooth)

    def start_new_game(self):
        self._clear();self.stage = 'wake';self._phase = 'wake_dialogue'
        self.game.world = self.game._scene_by_id('sanctuary_bedroom')
        player = self.game.player
        player.position.update(self.data['bedroom_position']);player.facing = 'front'
        player.moving = False;player.walk_ms = 0;player.story_visible = False
        self._sleeping = True
        self._prepare_serene()
        self._place_actor('tomas', 'sanctuary_hall', (84, 102), 'cross_hall', 'back')
        self.game.social.start_script(self.data['wake'], self._finish_wake_dialogue, 'opening_wake')

    def _queue_wake(self):
        if self._wake_started:return
        self._wake_started = True
        duration = self._duration('wake_up')
        def animate(elapsed):
            frames = self._animation('wake_up')
            index, record = self._frame('wake_up', elapsed)
            times = [0.0]
            for frame in frames[:-1]:times.append(times[-1]+frame['duration_ms']/1000)
            a = record['display_position']
            b = frames[min(index+1, len(frames)-1)]['display_position']
            span = max(.001, record['duration_ms']/1000)
            # A head-only pose remains registered to the pillow. The next
            # full-body pose supplies the hidden torso before moving outward.
            position = (pygame.Vector2(a) if record.get('kind') == 'pillow_head'
                        else self._lerp(a, b, (elapsed-times[index])/span))
            self._sleeping = False
            self._pose(self.game.player, 'wake_up', elapsed, position, sort_y=180)
            self._bed_occlusion = None
            if record.get('bed_occlusion'):
                bed = next((entity for entity in self.game.world.entities if entity['id'] == 'bed'), None)
                if bed is not None:
                    x, y = bed['position']
                    image = bed.get('surfaces', [None])[0]
                    width, height = image.get_size() if image is not None else (48, 72)
                    chin = position.y-record.get('draw_anchor', (12, 30))[1]+record.get('head_bottom', 15)
                    top = max(y, round(chin+2))
                    if top < y+height:self._bed_occlusion = (x, top, width, y+height-top)
        def finished():
            self._wake_finished = True;self._sleeping = False;self._bed_occlusion = None
            self._clear_pose(self.game.player)
        self._queue('wake_up', duration, animate, finished, ((.18, 'bedsheet'),))

    def _finish_wake_dialogue(self):
        self._wake_dialogue_done = True
        self._queue_wake()
        self._check_progress()

    def _finish_wake(self):
        self.stage = 'explore';self._phase = None
        self._prepare_dining();self._save()

    def _start_breakfast(self):
        if self.game.social.locked:return False
        self.stage = 'breakfast';self._phase = 'greeting'
        self._prepare_dining()
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.moving = False
        return self.game.social.start_script(self.data['breakfast_greeting'], self._start_arrival, 'opening_greeting')

    def _start_arrival(self):
        self._phase = 'arrival';self._arriving = True
        self._arrival_path = None;self._arrival_retry = 0.0
        self.game.player.moving = False

    def _walk_to_breakfast(self, seconds):
        player = self.game.player;world = self.game.world
        player.moving = False
        goal = self.data['caelan_breakfast_floor']
        if player.position.distance_squared_to(goal) < 1e-8:
            self._start_sitting();return
        self._arrival_retry = max(0.0, self._arrival_retry-seconds)
        if self._arrival_path is None:
            if self._arrival_retry:return
            self._arrival_path = find_path(world, player.position, goal, world.probe_size, player)
            if self._arrival_path is None:self._arrival_retry = .5;return
        remaining = max(0, seconds)
        while remaining > 1e-8 and self._arrival_path:
            target = pygame.Vector2(self._arrival_path[0]);delta = target-player.position;distance = delta.length()
            if distance < 1e-7:self._arrival_path.popleft();continue
            step_seconds = min(remaining, 1/60, distance/72)
            before = player.position.copy()
            player.update(delta, step_seconds, world, False)
            remaining -= step_seconds
            travel = player.position.distance_to(before)
            self.record_footsteps(travel)
            if travel < 1e-5:self._arrival_path = None;self._arrival_retry = .5;return
        if not self._arrival_path:
            self._arrival_path = None
            if player.position.distance_squared_to(goal) < 1e-8:self._start_sitting()

    def _start_sitting(self):
        self._arriving = False;self._phase = 'sitting'
        self.game.player.position.update(self.data['caelan_breakfast_floor'])
        self.game.player.moving = False;self.game.player.facing = 'right'
        walk_duration = .25
        pose_duration = self._duration('caelan_sit')
        duration = walk_duration+pose_duration
        approach = (self.data['caelan_seated_position'][0]-12, self.data['caelan_seated_position'][1])
        def animate(elapsed):
            if elapsed < walk_duration:
                position = pygame.Vector2(self.data['caelan_breakfast_floor']).lerp(approach, elapsed/walk_duration)
                self._walking_pose(self.game.player, 'caelan', 'right', elapsed, position)
            else:
                local = elapsed-walk_duration
                position = self._lerp(approach, self.data['caelan_seated_position'], local/pose_duration)
                self._pose(self.game.player, 'caelan_sit', local, position)
        self._queue('sit', duration, animate, self._start_meal,
                    ((walk_duration-.02, 'footstep'), (walk_duration+.08, 'chair')))

    def _start_meal(self):
        self._phase = 'meal'
        self._body(self.game.player, self._image('caelan_seated.png'), self.data['caelan_seated_position'])
        self._meal_finished = self._meal_dialogue_done = False
        plate_duration = .72
        def plate(elapsed):
            self._plate_index = min(3, int(elapsed/.18))
            actor = self._actor('tomas')
            self._body(actor, self._image(f'tomas_plate_push/frame_{self._plate_index+1:02}.png'), self.data['tomas_seated_position'])
        def eat(elapsed):
            self._pose(self.game.player, 'caelan_eat', min(elapsed, self._duration('caelan_eat')-1e-6), self.data['caelan_seated_position'])
            self._pose(self._actor('tomas'), 'tomas_eat', elapsed, self.data['tomas_seated_position'], repeat=True)
        def finished():
            self._meal_finished = True
            self._body(self.game.player, self._image('caelan_seated_glance.png'), self.data['caelan_seated_position'])
            self._body(self._actor('tomas'), self._image('tomas_seated_glance.png'), self.data['tomas_seated_position'])
        self._queue('plate', plate_duration, plate, sounds=((.25, 'plate'),))
        self._queue('eat', 1.45, eat, finished, ((.28, 'bite'), (.95, 'bite')))
        self.game.social.start_script(self.data['breakfast'], self._finish_meal_dialogue, 'opening_breakfast')

    def _finish_meal_dialogue(self):self._meal_dialogue_done = True;self._check_progress()

    def _start_cup(self):
        self._phase = 'cup';self._cup_finished = self._cup_dialogue_done = False
        duration = self._duration('caelan_seated_cup')
        def animate(elapsed):
            record = self._pose(self.game.player, 'caelan_seated_cup', elapsed, self.data['caelan_seated_position'])
            index, _ = self._frame('caelan_seated_cup', elapsed)
            if index < 2:
                hand = record.get('hand_landmark', record.get('wrist', (16, 23)))
                origin = pygame.Vector2(self.data['caelan_seated_position'])-pygame.Vector2(12, 30)
                self._cup_position = origin+pygame.Vector2(hand)+pygame.Vector2(-2, -4)
            else:
                self._cup_position = pygame.Vector2(self.data['cup_position']);self._cup_placed = True
        def finished():
            self._cup_finished = True;self._cup_placed = True
            self._cup_position = pygame.Vector2(self.data['cup_position'])
            self._body(self.game.player, self._image('caelan_seated.png'), self.data['caelan_seated_position'])
        self._queue('cup', duration, animate, finished, ((duration*.52, 'cup'),))
        self.game.social.start_script(self.data['kindness'], self._finish_cup_dialogue, 'opening_kindness')

    def _finish_cup_dialogue(self):self._cup_dialogue_done = True;self._check_progress()

    def _start_standing(self):
        self._phase = 'standing'
        pose_duration = max(self._duration('caelan_stand'), self._duration('tomas_stand'))
        walk_duration = .25
        duration = pose_duration+walk_duration
        caelan_approach = (self.data['caelan_seated_position'][0]-12, self.data['caelan_seated_position'][1])
        tomas_approach = (self.data['tomas_seated_position'][0]+12, self.data['tomas_seated_position'][1])
        def animate(elapsed):
            actor = self._actor('tomas')
            if elapsed < pose_duration:
                self._pose(self.game.player, 'caelan_stand', elapsed,
                           self._lerp(self.data['caelan_seated_position'], caelan_approach, elapsed/pose_duration))
                self._pose(actor, 'tomas_stand', elapsed,
                           self._lerp(self.data['tomas_seated_position'], tomas_approach, elapsed/pose_duration))
            else:
                local = elapsed-pose_duration
                self._walking_pose(self.game.player, 'caelan', 'left', local,
                                   pygame.Vector2(caelan_approach).lerp(self.data['caelan_breakfast_floor'], local/walk_duration))
                self._walking_pose(actor, 'tomas', 'right', local,
                                   pygame.Vector2(tomas_approach).lerp(self.data['tomas_breakfast_floor'], local/walk_duration))
        self._queue('stand', duration, animate, self._finish_breakfast,
                    ((.12, 'chair'), (pose_duration+walk_duration-.02, 'footstep')))

    def _finish_breakfast(self):
        self.stage = 'assignment';self._phase = None
        self._clear_pose(self.game.player);self.game.player.facing = 'left'
        tomas = self._actor('tomas');self._clear_pose(tomas)
        tomas.select_step('walk_to_model', position=self.data['tomas_breakfast_floor'], scene_id='sanctuary_dining', facing='right')
        tomas.story_paused = True
        serene = self._actor('mother_serene')
        self._clear_pose(serene);self._serene_glance = False
        serene.select_step('sort_provisions', position=(288, 214), scene_id='sanctuary_dining', facing='back')
        serene.story_paused = True
        self._save()

    def _check_progress(self):
        if self.stage == 'breakfast' and self._leaving_breakfast and not self.in_action:
            social = self.game.social
            if self._phase == 'meal' and self._meal_finished:
                if social.script_identifier == 'opening_breakfast':social.cancel_script()
                self._meal_dialogue_done = True
            elif self._phase == 'cup' and self._cup_finished:
                if social.script_identifier == 'opening_kindness':social.cancel_script()
                self._cup_dialogue_done = True
        if self.stage == 'wake' and self._wake_dialogue_done and self._wake_finished and not self.in_action:self._finish_wake()
        elif self.stage == 'breakfast' and self._phase == 'meal' and self._meal_dialogue_done and self._meal_finished and not self.in_action:self._start_cup()
        elif self.stage == 'breakfast' and self._phase == 'cup' and self._cup_dialogue_done and self._cup_finished and not self.in_action:self._start_standing()

    def _start_acceptance(self):
        if self.game.social.locked:return False
        self.stage = 'acceptance'
        for identifier in ('mother_serene', 'tomas'):
            actor = self._actor(identifier);actor.story_paused = True
            if getattr(actor, 'idles', None):
                actor.story_sprite = actor.idles[facing_toward(self.game.player.position-actor.position)]
                actor.story_draw_anchor = actor.draw_anchor
        self.game.social.start_script(self.data['acceptance'], self._finish_acceptance, 'opening_acceptance')
        self._save();return True

    def on_quest_accepted(self, quest_id):
        if quest_id != OPENING_QUEST or self.stage != 'assignment' or self.game.quests.status(quest_id) != 'active':return False
        return self._start_acceptance()

    def _finish_acceptance(self):
        self.stage = 'done'
        for identifier in ('mother_serene', 'tomas'):
            actor = self._actor(identifier);self._clear_pose(actor);actor.story_paused = False
        self._save()

    def _update_serene_station(self, seconds):
        serene = self._actor('mother_serene');duration = serene._duration()
        if not duration or self._serene_glance or getattr(serene, 'conversation_ready', False):return
        remaining = max(0, seconds)
        while remaining > 1e-9:
            if getattr(serene, 'conversation_requested', False) and serene._conversation_safe():serene.conversation_ready = True;return
            step = min(remaining, 1/60);serene.state_ms = (serene.state_ms+step*1000) % duration;remaining -= step
        if getattr(serene, 'conversation_requested', False) and serene._conversation_safe():serene.conversation_ready = True

    def on_enter_scene(self):
        if self.stage == 'explore' and self.game.world.data['id'] == 'sanctuary_dining':self._start_breakfast()

    def update(self, seconds):
        if self.stage in ('wake', 'explore', 'breakfast', 'assignment'):self._update_serene_station(seconds)
        if self.stage == 'breakfast' and self._phase == 'cup' and not self._serene_glance:
            serene = self._actor('mother_serene')
            if getattr(serene, 'idles', None) and getattr(serene, '_conversation_safe', lambda: True)():
                serene.story_sprite = serene.idles[facing_toward(self.game.player.position-serene.position)]
                serene.story_draw_anchor = serene.draw_anchor
                self._serene_glance = True
        page = self.game.social.page
        if self.stage == 'wake' and self.game.social.scripted and page is not None:
            key = (self.game.social.script_identifier, self.game.social.page_index)
            if key not in self._seen_cue_pages:
                self._seen_cue_pages.add(key)
                if page.get('cue') == 'wake_up':self._queue_wake()
        if self.stage == 'breakfast' and self._arriving:self._walk_to_breakfast(seconds)
        self._update_actions(seconds)
        self._check_progress()
        if self.stage == 'assignment':
            status = self.game.quests.status(OPENING_QUEST)
            if status == 'active':self._start_acceptance()
            elif status in ('ready', 'completed'):self._finish_acceptance()

    def draw_world(self, canvas, camera):
        scene_id = self.game.world.data['id']
        if self._sleeping and scene_id == 'sanctuary_bedroom':
            x, y = self.data['sleep_head_origin'];canvas.blit(self._image('caelan_sleep_head.png'), (x-camera[0], y-camera[1]))
        if self._bed_occlusion and scene_id == 'sanctuary_bedroom':
            bed = next((entity for entity in self.game.world.entities if entity['id'] == 'bed'), None)
            if bed and 'surfaces' in bed:
                patch = pygame.Rect(self._bed_occlusion)
                source = patch.move(-bed['position'][0], -bed['position'][1])
                canvas.blit(bed['surfaces'][0], (patch.x-camera[0], patch.y-camera[1]), source)
        if scene_id == 'sanctuary_dining' and self.stage in ('breakfast', 'assignment', 'acceptance', 'done'):
            x, y = self.data['plate_origin']
            canvas.blit(self._image('plate.png'), (x+self.data['plate_push_offsets'][self._plate_index]-camera[0], y-camera[1]))
            if self._cup_position is not None or self._cup_placed:
                point = self._cup_position if self._cup_position is not None else self.data['cup_position']
                canvas.blit(self._image('cup.png'), (round(point[0])-camera[0], round(point[1])-camera[1]))

    def restore(self, data):
        if not self.valid_snapshot(data):return False
        self._clear();stage = data['stage'];status = self.game.quests.status(OPENING_QUEST)
        if stage in ('wake', 'explore', 'breakfast') and status in ('active', 'ready', 'completed'):stage = 'done'
        elif stage == 'assignment' and status == 'active':stage = 'acceptance'
        elif stage in ('assignment', 'acceptance') and status in ('ready', 'completed'):stage = 'done'
        if stage == 'wake':self.start_new_game()
        elif stage == 'breakfast':
            self.stage = 'explore';self.game.world = self.game._scene_by_id('sanctuary_dining')
            self.game.player.position.update(self.game.world.data['spawn']);self._start_breakfast()
        elif stage == 'acceptance':
            self._prepare_dining();self._clear_pose(self._actor('tomas'))
            if status == 'available':self.stage = 'assignment'
            else:
                self.game.world = self.game._scene_by_id('sanctuary_dining')
                self.game.player.position.update(288, 231);self.game.player.facing = 'back';self._start_acceptance()
        else:
            self.stage = stage
            if stage in ('explore', 'assignment'):
                self._prepare_dining()
                if stage == 'assignment':self._clear_pose(self._actor('tomas'))
            if stage in ('assignment', 'done'):
                self._plate_index = 3;self._cup_placed = True
                self._cup_position = pygame.Vector2(self.data['cup_position'])
        return True
