"""The sanctuary's opening morning, with resumable scene checkpoints.

Opening scenes borrow the existing persistent actors rather than spawning
copies. Logical feet stay on clear floor while seated/sleeping presentations
use explicit display positions; releasing control restores normal rendering.
"""
from __future__ import annotations

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
        self._sleeping = False
        self._push_ms = None
        self._meal_remaining = None
        self._seen_cue_pages = set()
        self._chairs = []
        self._arriving = False
        self._arrival_path = None
        self._arrival_retry = 0.0

    @property
    def active(self):
        return self.stage not in ('disabled', 'done')

    @property
    def locks_player(self):
        return self.stage in ('wake', 'breakfast', 'acceptance')

    @property
    def player_visible(self):
        return not self._sleeping

    @property
    def controls_player(self):
        return self.stage == 'breakfast' and self._arriving

    def can_speak(self, npc_id):
        if npc_id not in ('mother_serene', 'tomas'):
            return True
        return self.stage in ('disabled', 'done') or (self.stage == 'assignment' and npc_id == 'mother_serene')

    def hint_text(self):
        if self.stage == 'wake':
            return 'Morning bells. A knock at the door.'
        if self.stage == 'explore':
            if self.game.world.data['id'] == 'sanctuary_hall':
                return 'Breakfast is through the northeast doorway.'
            return 'Join Tomas and Mother Serene for breakfast.'
        if self.stage == 'assignment':
            return 'Speak to Mother Serene about today\'s visits.'
        return ''

    def _inspect_target(self):
        if (self.stage not in ('explore', 'assignment', 'done') or
                self.game.world.data['id'] != 'sanctuary_bedroom' or
                self.game.social.locked or self.game.map_open or
                self.game.quest_ui.journal_open):
            return None
        destinations = self.game.world.data.get('destinations', {})
        candidates = [(self.game.player.position.distance_squared_to(destinations[key]), key)
                      for key in self.data['inspections'] if key in destinations]
        nearby = [item for item in candidates if item[0] <= 22*22]
        return min(nearby)[1] if nearby else None

    def interaction_hint(self):
        key = self._inspect_target()
        return f"E: inspect {self.data['inspections'][key]['label']}" if key else ''

    def inspect_nearby(self):
        key = self._inspect_target()
        if key is None:
            return False
        return self.game.social.start_script(
            [{'speaker': 'caelan', 'text': self.data['inspections'][key]['text']}],
            identifier='bedroom_inspect_'+key)

    def to_dict(self):
        return {'version': 1, 'stage': self.stage}

    @staticmethod
    def valid_snapshot(data):
        return (isinstance(data, dict) and set(data) == {'version', 'stage'} and
                type(data['version']) is int and data['version'] == 1 and
                isinstance(data['stage'], str) and data['stage'] in STAGES)

    def _actor(self, identifier):
        return next(actor for actor in self.game.persistent_npcs
                    if actor.data['id'] == identifier)

    def _image(self, name):
        return self.game.town.image(POSES+name)

    @staticmethod
    def _clear_pose(actor):
        for attribute in ('story_sprite', 'story_position', 'story_sort_y',
                          'story_draw_anchor', 'story_visible'):
            if hasattr(actor, attribute):
                delattr(actor, attribute)

    def _clear(self):
        self.game.social.cancel_script()
        self._clear_pose(self.game.player)
        for actor in self.game.persistent_npcs:
            if actor.data['id'] in ('mother_serene', 'tomas'):
                actor.story_paused = False
                self._clear_pose(actor)
        self._sleeping = False
        self._push_ms = None
        self._meal_remaining = None
        self._seen_cue_pages.clear()
        self._arriving = False
        self._arrival_path = None
        self._arrival_retry = 0.0
        self._restore_chairs()

    def _seat_chairs(self):
        self._restore_chairs()
        room = self.game._scene_by_id('sanctuary_dining')
        positions = {'chair_west': (120, 174), 'chair_east': (192, 174)}
        for entity in room.entities:
            if entity['id'] in positions:
                self._chairs.append((entity, list(entity['position'])))
                entity['position'] = list(positions[entity['id']])
                entity['rect'].topleft = entity['position']

    def _restore_chairs(self):
        for entity, position in self._chairs:
            entity['position'] = position
            entity['rect'].topleft = position
        self._chairs = []

    def _place_actor(self, identifier, scene_id, point, step, facing):
        actor = self._actor(identifier)
        destination = self.game._scene_by_id(scene_id)
        for scene in self.game.scenes.values():
            while actor in scene.npcs:
                scene.npcs.remove(actor)
        actor.end_conversation()
        actor.select_step(step, position=point, scene_id=scene_id, facing=facing)
        destination.npcs.append(actor)
        self.game._routine_worlds[actor] = destination
        actor.story_paused = True
        self._clear_pose(actor)
        return actor

    def _prepare_serene(self):
        return self._place_actor('mother_serene', 'sanctuary_dining',
                                 (288, 214), 'sort_provisions', 'back')

    def _prepare_dining(self):
        self._prepare_serene()
        actor = self._place_actor('tomas', 'sanctuary_dining',
                                 self.data['tomas_breakfast_floor'], 'walk_to_model', 'left')
        actor.story_sprite = self._image('tomas_seated.png')
        actor.story_position = self.data['tomas_seated_position']
        actor.story_sort_y = 206
        actor.story_draw_anchor = (12, 30)

    def _save(self):
        save = getattr(self.game, 'save_progress', None)
        if save is not None:
            save()

    def start_new_game(self):
        self._clear()
        self.stage = 'wake'
        self.game.world = self.game._scene_by_id('sanctuary_bedroom')
        self.game.player.position.update(self.data['bedroom_position'])
        self.game.player.facing = 'front'
        self.game.player.moving = False
        self.game.player.walk_ms = 0
        self.game.player.story_visible = False
        self._sleeping = True
        self._prepare_serene()
        self._place_actor('tomas', 'sanctuary_hall', (84, 102), 'cross_hall', 'back')
        self.game.social.start_script(self.data['wake'], self._finish_wake, 'opening_wake')

    def _finish_wake(self):
        self.stage = 'explore'
        self._sleeping = False
        self._clear_pose(self.game.player)
        self._prepare_dining()
        self._save()

    def _start_breakfast(self):
        if self.game.social.locked:
            return False
        self.stage = 'breakfast'
        self._prepare_dining()
        self._seat_chairs()
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self._push_ms = None
        self._meal_remaining = None
        self._seen_cue_pages.clear()
        self._arriving = True
        self._arrival_path = None
        self._arrival_retry = 0.0
        return True

    def _seat_player(self):
        self._arriving = False
        player = self.game.player
        # The mover already reached this point; remove subpixel round-off
        # before registering a repeatable seated presentation/checkpoint.
        player.position.update(self.data['caelan_breakfast_floor'])
        player.facing = 'right'
        player.moving = False
        player.walk_ms = 0
        player.story_sprite = self._image('caelan_seated.png')
        player.story_position = self.data['caelan_seated_position']
        player.story_sort_y = 206
        player.story_draw_anchor = (12, 30)
        self.game.social.start_script(self.data['breakfast'],
                                       self._begin_meal, 'opening_breakfast')

    def _walk_to_breakfast(self, seconds):
        player = self.game.player
        world = self.game.world
        goal = self.data['caelan_breakfast_floor']
        if player.position.distance_squared_to(goal) < 1e-8:
            self._seat_player()
            return
        self._arrival_retry = max(0.0, self._arrival_retry-seconds)
        if self._arrival_path is None:
            if self._arrival_retry:
                return
            self._arrival_path = find_path(world, player.position, goal,
                                           world.probe_size, player)
            if self._arrival_path is None:
                self._arrival_retry = .5
                return
        remaining = max(0, seconds)
        while remaining > 1e-8 and self._arrival_path:
            target = pygame.Vector2(self._arrival_path[0])
            delta = target-player.position
            distance = delta.length()
            if distance < 1e-7:
                self._arrival_path.popleft()
                continue
            # Use the production player mover/collision tests for each small
            # part of the route, retaining its normal speed and walk frames.
            step_seconds = min(remaining, 1/60, distance/72)
            before = player.position.copy()
            player.update(delta, step_seconds, world, False)
            remaining -= step_seconds
            if player.position.distance_squared_to(before) < 1e-10:
                self._arrival_path = None
                self._arrival_retry = .5
                return
        if not self._arrival_path:
            self._arrival_path = None
            if player.position.distance_squared_to(goal) < 1e-8:
                self._seat_player()

    def _begin_meal(self):
        # A brief shared breakfast beat follows the exchange, with no new page
        # to click. It never holds the player for a long unskippable sequence.
        self._meal_remaining = 0.8
        if self._push_ms is None:
            self._push_ms = 0.0

    def _finish_breakfast(self):
        self.stage = 'assignment'
        self._clear_pose(self.game.player)
        self._restore_chairs()
        self.game.player.facing = 'right'
        tomas = self._actor('tomas')
        self._clear_pose(tomas)
        tomas.select_step('walk_to_model', position=self.data['tomas_breakfast_floor'],
                          scene_id='sanctuary_dining', facing='front')
        tomas.story_paused = True
        serene = self._actor('mother_serene')
        serene.select_step('sort_provisions', position=(288, 214),
                           scene_id='sanctuary_dining', facing='back')
        serene.story_paused = True
        self._meal_remaining = None
        self._save()

    def _start_acceptance(self):
        if self.game.social.locked:
            return False
        self.stage = 'acceptance'
        for identifier in ('mother_serene', 'tomas'):
            actor = self._actor(identifier)
            actor.story_paused = True
            if getattr(actor, 'idles', None):
                facing = facing_toward(self.game.player.position-actor.position)
                actor.story_sprite = actor.idles[facing]
                actor.story_draw_anchor = actor.draw_anchor
        self.game.social.start_script(self.data['acceptance'],
                                       self._finish_acceptance, 'opening_acceptance')
        self._save()
        return True

    def on_quest_accepted(self, quest_id):
        """Start the follow-up before the accepting click is checkpointed."""
        if (quest_id != OPENING_QUEST or self.stage != 'assignment' or
                self.game.quests.status(quest_id) != 'active'):
            return False
        return self._start_acceptance()

    def _finish_acceptance(self):
        self.stage = 'done'
        for identifier in ('mother_serene', 'tomas'):
            actor = self._actor(identifier)
            self._clear_pose(actor)
            actor.story_paused = False
        self._save()

    def _update_serene_station(self, seconds):
        """Loop preparation work, still honoring safe conversation handoffs."""
        serene = self._actor('mother_serene')
        duration = serene._duration()
        if not duration or getattr(serene, 'conversation_ready', False):
            return
        remaining = max(0, seconds)
        while remaining > 1e-9:
            if (getattr(serene, 'conversation_requested', False) and
                    serene._conversation_safe()):
                serene.conversation_ready = True
                return
            step = min(remaining, 1/60)
            serene.state_ms = (serene.state_ms+step*1000) % duration
            remaining -= step
        if (getattr(serene, 'conversation_requested', False) and
                serene._conversation_safe()):
            serene.conversation_ready = True

    def on_enter_scene(self):
        if self.stage == 'explore' and self.game.world.data['id'] == 'sanctuary_dining':
            self._start_breakfast()

    def update(self, seconds):
        if self.stage in ('wake', 'explore', 'breakfast', 'assignment'):
            # Serene keeps doing visible provision work while her story station
            # is reserved. Its loop owns the same surface props as her routine.
            self._update_serene_station(seconds)
        page = self.game.social.page
        if self.game.social.scripted and page is not None:
            key = (self.game.social.script_identifier, self.game.social.page_index)
            if key not in self._seen_cue_pages:
                self._seen_cue_pages.add(key)
                if page.get('cue') == 'wake_up':
                    self._sleeping = False
                    self.game.player.story_visible = True
                elif page.get('cue') == 'push_plate':
                    self._push_ms = 0.0
        if self.stage == 'breakfast':
            if self._arriving:
                self._walk_to_breakfast(seconds)
            if self._push_ms is not None:
                self._push_ms += max(0, seconds)*1000
                index = min(3, int(self._push_ms//self.data['pose_duration_ms']))
                actor = self._actor('tomas')
                if self._push_ms < self.data['pose_duration_ms']*4:
                    actor.story_sprite = self._image(f'tomas_plate_push/frame_{index+1:02}.png')
                else:
                    actor.story_sprite = self._image('tomas_seated.png')
            if self._meal_remaining is not None:
                self._meal_remaining -= max(0, seconds)
                if self._meal_remaining <= 0:
                    self._finish_breakfast()
        elif self.stage == 'assignment':
            status = self.game.quests.status(OPENING_QUEST)
            if status == 'active':
                self._start_acceptance()
            elif status in ('ready', 'completed'):
                self._finish_acceptance()

    def draw_world(self, canvas, camera):
        scene_id = self.game.world.data['id']
        if self._sleeping and scene_id == 'sanctuary_bedroom':
            x, y = self.data['sleep_head_origin']
            canvas.blit(self._image('caelan_sleep_head.png'), (x-camera[0], y-camera[1]))
        if scene_id == 'sanctuary_dining' and self.stage in ('breakfast', 'assignment', 'acceptance', 'done'):
            index = (min(3, int(self._push_ms//self.data['pose_duration_ms']))
                     if self._push_ms is not None else 0)
            if self.stage != 'breakfast':
                index = 3
            x, y = self.data['plate_origin']
            canvas.blit(self._image('plate.png'),
                        (x+self.data['plate_push_offsets'][index]-camera[0], y-camera[1]))

    def restore(self, data):
        """Resume at a complete scene checkpoint, never half an input prompt."""
        if not self.valid_snapshot(data):
            return False
        self._clear()
        stage = data['stage']
        status = self.game.quests.status(OPENING_QUEST)
        if (stage in ('wake', 'explore', 'breakfast') and
                status in ('active', 'ready', 'completed')):
            stage = 'done'
        elif stage == 'assignment' and status == 'active':
            # Acceptance checkpoints before the next update. If the player
            # quits on that click, resume the promised follow-up exchange.
            stage = 'acceptance'
        elif stage in ('assignment', 'acceptance') and status in ('ready', 'completed'):
            stage = 'done'
        if stage == 'wake':
            self.start_new_game()
        elif stage == 'breakfast':
            self.stage = 'explore'
            self.game.world = self.game._scene_by_id('sanctuary_dining')
            self.game.player.position.update(self.game.world.data['spawn'])
            self._start_breakfast()
        elif stage == 'acceptance':
            if self.game.quests.status(OPENING_QUEST) == 'available':
                self.stage = 'assignment'
                self._prepare_dining()
                self._clear_pose(self._actor('tomas'))
            else:
                self._prepare_dining()
                self._clear_pose(self._actor('tomas'))
                self.game.world = self.game._scene_by_id('sanctuary_dining')
                self.game.player.position.update(288, 231)
                self.game.player.facing = 'back'
                self._start_acceptance()
        else:
            self.stage = stage
            if stage == 'explore':
                self._prepare_dining()
            elif stage == 'assignment':
                self._prepare_dining()
                self._clear_pose(self._actor('tomas'))
        return True
