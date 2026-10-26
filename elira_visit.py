"""Elira's delivery and a single, physically registered memorial lantern."""
import json
from pathlib import Path

import pygame

from inventory import Inventory
from quests import OPENING_QUEST, QuestLog
from social import clear_sight, facing_toward

ROOT = Path(__file__).resolve().parent
ART = 'assets/story/elira/'
PACK = 'assets/terrain/eldenmere/elira_interior/sprites/'
STOOL_APPROACH = (154, 118)
STOOL_FEET = (154, 76)
TABLE_APPROACH = (180, 238)
TABLE_LANTERN = (178, 216)
POSE_ANCHOR = (20, 54)


class Elira:
    def __init__(self, world):
        self.data = {'id': 'elira', 'name': 'Elira'}
        self.position = pygame.Vector2(210, 202)
        self.probe_size = (12, 8);self.draw_anchor = (12, 30)
        self.idles = {d: world.image(ART+f'idle_{d}.png') for d in ('front', 'left', 'right', 'back')}
        self.facing = 'front';self.conversation_ready = False;self.conversation_facing = 'front'

    @property
    def blocker(self):return pygame.Rect(round(self.position.x)-6, round(self.position.y)-4, 12, 8)

    def sprite(self, elapsed_ms):return self.idles[self.conversation_facing if self.conversation_ready else self.facing]

    def request_conversation(self, facing):
        self.conversation_ready = True;self.conversation_facing = facing

    def end_conversation(self):self.conversation_ready = False


class EliraVisit:
    def __init__(self, game):
        self.game = game;self.home = game._scene_by_id('elira')
        self.elira = Elira(self.home)
        if not self.home.can_stand(self.elira.position, self.elira.probe_size):
            raise ValueError('Elira must stand on a clear floor position')
        self.home.npcs.append(self.elira)
        self.lines = json.loads((ROOT/ART/'scene.json').read_text())
        self.lantern = 'shelf';self.action = None;self.action_time = 0.
        self.contact = False;self.aligning = False;self.align_ms = 0.;self.blocked_seconds = 0.
        self.dialogue = None;self._pose_owned = False
        shelf = next(e for e in self.home.entities if e['id'] == 'lantern_shelf')
        shelf['state_images'] = {'full': PACK+'shelf_with_lantern.png', 'empty': PACK+'shelf_empty.png'}
        self.surface_props = [
            {'id': 'elira_lantern_table', 'scene': 'elira', 'surface': self.home.image(PACK+'lantern_unlit.png'),
             'position': list(TABLE_LANTERN), 'sort_y': 271},
            {'id': 'elira_provisions', 'scene': 'elira', 'surface': self.home.image(ART+'provisions.png'),
             'position': [194, 119], 'sort_y': 163}]
        self.home.attach_routine_props(self)
        self._sync_shelf()

    @property
    def active(self):return self.game.quests.objective_status(OPENING_QUEST, 'elira') == 'active'

    @property
    def delivered(self):return self.game.inventory.was_delivered(OPENING_QUEST, 'elira')

    @property
    def completed(self):return self.game.quests.objective_status(OPENING_QUEST, 'elira') == 'completed'

    @property
    def locks_player(self):return self.action is not None

    def to_dict(self):
        state = 'table' if self.completed else self.lantern if self.active else 'shelf'
        return {'version': 1, 'lantern': state}

    @staticmethod
    def valid_snapshot(data):
        return (isinstance(data, dict) and set(data) == {'version', 'lantern'} and
                type(data['version']) is int and data['version'] == 1 and
                isinstance(data['lantern'], str) and data['lantern'] in ('shelf', 'carried', 'table'))

    @staticmethod
    def valid_journey(data):
        record = data['elira_visit']
        if not EliraVisit.valid_snapshot(record):return False
        quests = QuestLog()
        if not quests.restore(data['quests']):return False
        status = quests.objective_status(OPENING_QUEST, 'elira')
        if record['lantern'] != 'shelf':
            if status not in ('active', 'completed'):return False
            if 'inventory' in data:
                inventory = Inventory()
                if not inventory.restore(data['inventory']) or not inventory.was_delivered(OPENING_QUEST, 'elira'):return False
            elif status != 'completed':return False
        return status != 'completed' or record['lantern'] == 'table'

    def restore(self, data=None):
        if data is not None and not self.valid_snapshot(data):return False
        self.release_pose();self.action = None;self.action_time = 0.;self.contact = False
        self.aligning = False;self.align_ms = 0.;self.blocked_seconds = 0.;self.dialogue = None
        self.elira.end_conversation();self.elira.facing = 'front'
        self.lantern = data['lantern'] if data else 'table' if self.completed else 'shelf'
        self._sync_shelf()
        if self.lantern == 'carried':self._carry_pose()
        return True

    def _sync_shelf(self):
        state = 'full' if self.lantern == 'shelf' else 'empty'
        shelf = next(e for e in self.home.entities if e['id'] == 'lantern_shelf')
        if shelf.get('state') != state:self.home.set_entity_state('lantern_shelf', state)

    def surface_prop_visible(self, prop):
        if prop['id'] == 'elira_lantern_table':return self.lantern == 'table'
        return self.delivered and self.action != 'supplies'

    def can_speak(self, identifier):
        return not (self.action is not None and identifier == 'elira')

    def try_conversation(self, actor):
        if actor is not self.elira:return None
        if self.completed:return self._speak('after')
        if not self.active:return None
        if not self.delivered:return self._speak('arrival', self._begin_supplies)
        if self.lantern == 'table':return self._speak('resolution', self._complete)
        return self._speak('carrying' if self.lantern == 'carried' else 'reminder')

    def _speak(self, kind, callback=None):
        if self.game.social.locked or self.action:return False
        self.elira.facing = facing_toward(self.game.player.position-self.elira.position)
        self.dialogue = kind
        def finished():
            self.dialogue = None
            if callback is not None:callback()
        result = self.game.social.start_script(self.lines[kind], finished, 'elira_'+kind)
        if result:self.game.social.blocked.add(self.elira)
        else:self.dialogue = None
        return result

    def on_dialogue_cancelled(self, identifier):
        if identifier and identifier.startswith('elira_'):self.dialogue = None

    def _begin_supplies(self):
        if self.game.world is self.home and self.game.player.position.distance_to(self.elira.position)<=36:
            self._start('supplies')

    def _start(self, name):
        self.action = name;self.action_time = 0.;self.contact = False
        self.aligning = name in ('retrieve', 'place');self.align_ms = 0.;self.blocked_seconds = 0.

    def _target(self):
        if not self.active or not self.delivered or self.game.world is not self.home or self.action:return None
        goal = STOOL_APPROACH if self.lantern == 'shelf' else TABLE_APPROACH if self.lantern == 'carried' else None
        if goal is None:return None
        p = self.game.player.position
        if p.distance_to(goal)>16 or not clear_sight(self.home, p, pygame.Vector2(goal)):return None
        return ('retrieve', 'E: Use stool to retrieve the lantern') if self.lantern == 'shelf' else ('place', 'E: Set the lantern on Elira’s table')

    def interact(self):
        if self.game.social.locked:return False
        target = self._target()
        if target is None:return False
        self._start(target[0]);return True

    def interaction_hint(self):
        if not self.active or self.game.social.locked:return ''
        if self.action:
            return {'supplies': 'Passing Elira her supplies…', 'retrieve': 'Retrieving the memorial lantern…',
                    'place': 'Setting the lantern down carefully…'}[self.action]
        target = self._target()
        if target:return target[1]
        if self.game.world is not self.home:return ''
        if not self.delivered:return 'Approach Elira to deliver her food and lamp oil.'
        return {'shelf': 'Use the stool beneath the high shelf. E: retrieve lantern.',
                'carried': 'Carry the lantern to the north side of Elira’s table.',
                'table': 'Approach Elira to talk about the lantern.'}[self.lantern]

    def tracker_text(self):
        if not self.active or self.game.world is not self.home:return ''
        if not self.delivered:return 'Give Elira the food and lamp oil.'
        return {'shelf': 'Retrieve Elira’s memorial lantern. E: use stool.',
                'carried': 'Set the lantern on Elira’s table.', 'table': 'Speak with Elira.'}[self.lantern]

    def journal_detail(self):
        if not self.active:return ''
        if not self.delivered:return 'Food and lamp oil are in the satchel.'
        return 'Food and lamp oil delivered. '+{'shelf': 'The lantern is still on the high shelf.',
            'carried': 'I am carrying the lantern to her table.',
            'table': 'The lantern is on her table; speak with Elira.'}[self.lantern]

    def _save(self):self._sync_shelf();self.game.save_progress()

    def _complete(self):
        if self.active and self.delivered and self.lantern == 'table':
            self.game.quests.complete_objective(OPENING_QUEST, 'elira')
            self.game.social.flags.add('CH01_MQ01_ELIRA_DONE');self._save()

    def _pose(self, name, position=None, sort_y=None):
        p = self.game.player;p.story_sprite = self.home.image(ART+name+'.png')
        p.story_draw_anchor = POSE_ANCHOR
        if position is not None:p.story_position = tuple(position)
        if sort_y is not None:p.story_sort_y = sort_y
        self._pose_owned = True

    def release_pose(self):
        if not self._pose_owned:return
        for name in ('story_sprite', 'story_draw_anchor', 'story_position', 'story_sort_y'):
            if hasattr(self.game.player, name):delattr(self.game.player, name)
        self._pose_owned = False

    def _carry_pose(self):
        p = self.game.player
        self.release_pose()
        self._pose(f'carry_{p.facing}_{int(p.walk_ms//140)%4}' if p.moving else f'hold_{p.facing}')

    def _align(self, seconds):
        player = self.game.player;goal = pygame.Vector2(STOOL_APPROACH if self.action == 'retrieve' else TABLE_APPROACH)
        delta = goal-player.position
        if delta.length()<.05:
            player.position.update(goal);player.moving = False;self.aligning = False
            player.facing = 'back' if self.action == 'retrieve' else 'front'
            self.release_pose();return True
        previous = player.position.copy()
        player.update(delta, min(seconds, delta.length()/72), self.home)
        self.align_ms += seconds*1000;player.walk_ms = self.align_ms
        self.blocked_seconds = self.blocked_seconds+seconds if previous == player.position else 0.
        if self.action == 'place':self._carry_pose()
        if self.blocked_seconds>=1:
            self.action = None;self.aligning = False;self.release_pose()
        return False

    def update(self, seconds):
        if self.action:
            if self.aligning and not self._align(seconds):return
            self.action_time += seconds;time = self.action_time
            if self.action == 'supplies':
                self.game.player.facing = facing_toward(self.elira.position-self.game.player.position)
                self._pose('give_'+self.game.player.facing)
                if time>=.4 and not self.contact:
                    self.contact = True;self.game.deliver_quest_item(OPENING_QUEST, 'elira', 'elira')
                if time>=.85:self._finish_action()
            elif self.action == 'retrieve':self._retrieve(time)
            elif self.action == 'place':self._place(time)
        elif self.lantern == 'carried':self._carry_pose()
        else:self.release_pose()

    def _retrieve(self, time):
        if time<.55:
            pos = pygame.Vector2(STOOL_APPROACH).lerp(STOOL_FEET, min(1., time/.55))
            self._pose(f'step_{min(3, int(time/.55*4))}', pos, 120)
        elif time<1.15:
            self._pose(f'reach_{min(3, int((time-.55)/.6*4))}', STOOL_FEET, 120)
        elif time<1.85:
            if not self.contact:
                self.contact = True;self.lantern = 'carried';self._save()
            self._pose(f'take_{min(3, int((time-1.15)/.7*4))}', STOOL_FEET, 120)
        elif time<2.45:
            # A large frame delta still crosses the handoff exactly once.
            if not self.contact:
                self.contact = True;self.lantern = 'carried';self._save()
            pos = pygame.Vector2(STOOL_FEET).lerp(STOOL_APPROACH, min(1., (time-1.85)/.6))
            self._pose(f'down_{min(3, int((time-1.85)/.6*4))}', pos, 120)
        else:
            if not self.contact:self.contact = True;self.lantern = 'carried'
            self._finish_action()

    def _place(self, time):
        frame = min(3, int(min(time, .4)/.4*4))
        if time>=.4 and not self.contact:
            self.contact = True;self.lantern = 'table';self._save()
        self._pose(('place_empty_' if self.contact else 'place_')+str(frame))
        if time>=.8:self._finish_action()

    def _finish_action(self):
        self.action = None;self.aligning = False;self.release_pose()
        if self.lantern == 'carried':self._carry_pose()
        self._save()

    def draw_world(self, canvas, camera):
        if self.action != 'supplies' or self.game.world is not self.home:return
        owner = self.elira if self.contact else self.game.player
        canvas.blit(self.home.image(ART+'provisions.png'),
                    (round(owner.position.x)+3-camera[0], round(owner.position.y)-12-camera[1]))
