"""The Venn delivery, two inspections and two equivalent, visible gate repairs."""
import json
from pathlib import Path

import pygame

from inventory import Inventory
from quests import OPENING_QUEST, QuestLog
from social import clear_sight, facing_toward

ROOT = Path(__file__).resolve().parent
ART = 'assets/story/venn/'
PIN_APPROACH = (1428, 670)
CHANNEL_APPROACH = (1428, 694)
GATE_POSITION = (1440, 636)
METHODS = ('tools', 'magicks')


def read(path):return json.loads((ROOT/path).read_text())


class VennResident:
    def __init__(self, world, role, position, name):
        self.data = {'id': 'venn_'+role, 'name': name, 'family_role': role, 'household_id': 'venn'}
        self.position = pygame.Vector2(position);self.probe_size = (12, 8)
        self.draw_anchor = (12, 30);self.facing = 'front'
        self.idles = {d: world.image(ART+f'{role}/idle_{d}.png') for d in ('front', 'left', 'right', 'back')}
        self.conversation_ready = False;self.conversation_facing = 'front';self.role = role
        if role == 'child':
            self.heads = [world.image(ART+'child/rest_head.png'), world.image(ART+'child/rest_blink.png')]
            self.story_position = (60, 112);self.story_draw_anchor = (12, 12);self.story_sort_y = 167

    @property
    def blocker(self):
        if self.role == 'child':
            # Nonblocking, but keep the social foot point at the bedside.
            return pygame.Rect(round(self.position.x), round(self.position.y), 0, 0)
        return pygame.Rect(round(self.position.x)-6, round(self.position.y)-4, 12, 8)

    def sprite(self, elapsed_ms):
        if self.role == 'child':return self.heads[int(elapsed_ms%4800>=4640)]
        return self.idles[self.conversation_facing if self.conversation_ready else self.facing]

    def request_conversation(self, facing):
        self.conversation_ready = True;self.conversation_facing = facing

    def end_conversation(self):self.conversation_ready = False


class VennVisit:
    def __init__(self, game):
        self.game = game;self.home = game._scene_by_id('venn');self.town = game.town
        self.family = {}
        for role, position, name in [('mother', (104, 178), 'Mrs. Venn'),
                                      ('father', (300, 202), 'Mr. Venn'), ('child', (88, 138), 'Venn child')]:
            actor = VennResident(self.home, role, position, name)
            if role != 'child' and not self.home.can_stand(actor.position, actor.probe_size):
                raise ValueError(f'Blocked Venn {role} station')
            self.home.npcs.append(actor);self.family[role] = actor
        self.lines = read(ART+'scene.json');self.art = read(ART+'art.json')
        self.inspected = set();self.method = None;self.repaired = False
        self.action = None;self.phase = None;self.phase_time = 0.;self.contact = False
        self.walk_ms = 0.;self.blocked_seconds = 0.;self.dialogue = None;self.partner = None
        self.debris_cleared = False;self.flow_seconds = 0.;self._pose_owned = False
        self._last_art = None;self._water_cache = {}
        self.gates = {name: [self.town.image(path) for path in frames] for name, frames in self.art['animations'].items()}
        self.backgrounds = [self.town.image(path, False) for path in self.art['backgrounds']]
        self.surface_props = [
            {'id': 'venn_supplies', 'scene': 'venn', 'surface': self.home.image(ART+'provisions.png'),
             'position': [338, 128], 'sort_y': 175},
            {'id': 'venn_tools', 'scene': self.town.data['id'], 'surface': self.town.image(ART+'toolbox.png'),
             'position': [1400, 686], 'sort_y': 698},
            {'id': 'venn_gate', 'scene': self.town.data['id'], 'surface': self.backgrounds[0].copy(),
             'position': list(GATE_POSITION), 'sort_y': 672},
            {'id': 'venn_debris', 'scene': self.town.data['id'], 'surface': self.town.image(ART+'debris.png'),
             'position': [1446, 680], 'sort_y': -9998},
            {'id': 'venn_magicks', 'scene': self.town.data['id'], 'surface': pygame.Surface((8, 12), pygame.SRCALPHA),
             'position': [1448, 644], 'sort_y': -9997}]
        meta = read('assets/terrain/eldenmere/irrigation/tileset.json')
        routes = {r['id']: r for r in meta['routes']}
        atlases = [self.town.image('assets/terrain/eldenmere/irrigation/'+f['image']) for f in meta['frames']]
        terrain = read('assets/maps/eldenmere/terrain_foundation/scene.json')
        downstream = [c for c in terrain['channels'] if c['branch']=='irrigation' and c['mode']=='trickle' and c['cell'][1]>=28]
        self.water_props = []
        for i, cell in enumerate(downstream):
            x, y = cell['cell'];images = [a.subsurface(routes[cell['route']]['rect']).copy() for a in atlases]
            prop = {'id': f'venn_flow_{i}', 'scene': self.town.data['id'], 'position': [x*24, y*24],
                    'sort_y': -10000, 'surface': images[0], 'images': images, 'delay': (i+1)*.16}
            self.water_props.append(prop)
        for fall in terrain['spillways']:
            if fall['branch'] != 'irrigation' or fall['mode'] != 'trickle':continue
            images = [self.town.image(f'assets/terrain/eldenmere/terraces/spillway/frame_{i+1:02}.png') for i in range(6)]
            self.water_props.append({'id': 'venn_spillway', 'scene': self.town.data['id'],
                'position': fall['position'], 'sort_y': -9999, 'surface': images[0], 'images': images,
                'delay': 9*.16})
        self.surface_props.extend(self.water_props)
        self.home.attach_routine_props(self);self.town.attach_routine_props(self)
        self._update_art(force=True)

    @property
    def active(self):return self.game.quests.objective_status(OPENING_QUEST, 'venn') == 'active'

    @property
    def completed(self):return self.game.quests.objective_status(OPENING_QUEST, 'venn') == 'completed'

    @property
    def delivered(self):return self.game.inventory.was_delivered(OPENING_QUEST, 'venn')

    @property
    def locks_player(self):return self.action is not None

    @property
    def hands_full(self):return getattr(getattr(self.game, 'elira_visit', None), 'lantern', None)=='carried'

    def to_dict(self):
        if self.completed:
            return {'version': 1, 'inspected': ['pin', 'channel'], 'method': self.method, 'repaired': True}
        if not self.active:return {'version': 1, 'inspected': [], 'method': None, 'repaired': False}
        return {'version': 1, 'inspected': [k for k in ('pin', 'channel') if k in self.inspected],
                'method': self.method, 'repaired': self.repaired}

    @staticmethod
    def valid_snapshot(data):
        if not isinstance(data, dict) or set(data) != {'version', 'inspected', 'method', 'repaired'}:return False
        inspected = data['inspected'];method = data['method']
        return (type(data['version']) is int and data['version']==1 and isinstance(inspected, list) and
                all(isinstance(v, str) and v in ('pin', 'channel') for v in inspected) and
                len(set(inspected))==len(inspected) and type(data['repaired']) is bool and
                (method is None or isinstance(method, str) and method in METHODS) and
                (method is None and not data['repaired'] or set(inspected)=={'pin', 'channel'}))

    @staticmethod
    def valid_journey(data):
        record = data['venn_visit']
        if not VennVisit.valid_snapshot(record):return False
        quests = QuestLog()
        if not quests.restore(data['quests']):return False
        status = quests.objective_status(OPENING_QUEST, 'venn')
        progress = bool(record['inspected'] or record['method'] or record['repaired'])
        if progress:
            if status not in ('active', 'completed'):return False
            if 'inventory' in data:
                inventory = Inventory()
                if not inventory.restore(data['inventory']) or not inventory.was_delivered(OPENING_QUEST, 'venn'):return False
            elif status != 'completed':return False
        if record['repaired'] and record['method'] is None and status != 'completed':return False
        return status != 'completed' or record['repaired']

    def restore(self, data=None):
        if data is not None and not self.valid_snapshot(data):return False
        self.release_pose();self.action = None;self.phase = None;self.phase_time = 0.
        self.contact = False;self.dialogue = None;self.partner = None
        self.inspected = set(data['inspected']) if data else {'pin', 'channel'} if self.completed else set()
        self.method = data['method'] if data else None
        self.repaired = data['repaired'] if data else self.completed
        self.debris_cleared = self.repaired;self.flow_seconds = 100. if self.repaired else 0.
        for actor in self.family.values():actor.end_conversation();actor.facing = 'front'
        self._last_art = None;self._update_art(force=True)
        return True

    def surface_prop_visible(self, prop):
        name = prop['id']
        if name == 'venn_supplies':return self.delivered and self.action != 'supplies'
        if name == 'venn_tools':return True
        if name == 'venn_gate':return True
        if name == 'venn_debris':return not self.repaired and not self.debris_cleared
        if name == 'venn_magicks':return self.action=='repair' and self.method=='magicks' and self.phase in ('ease_water', 'work_pin')
        return self.repaired and self.flow_seconds>=prop['delay']

    def can_speak(self, identifier):return not (identifier.startswith('venn_') and self.action)

    def try_conversation(self, actor):
        if actor not in self.family.values() or actor.role=='child':return None
        self.partner = actor
        if self.completed:return self._speak('after')
        if not self.active:return None
        if not self.delivered and self.hands_full:return self._speak('hands_full')
        if not self.delivered:return self._speak('arrival', self._begin_supplies)
        if self.repaired:return self._speak('resolution', self._complete)
        return self._speak('reminder')

    def _speak(self, kind, callback=None):
        if self.game.social.locked or self.action:return False
        for actor in self.family.values():actor.facing = facing_toward(self.game.player.position-actor.position)
        self.dialogue = kind
        def finished():
            self.dialogue = None
            if callback is not None:callback()
        result = self.game.social.start_script(self.lines[kind], finished, 'venn_'+kind)
        if result:
            for actor in self.family.values():self.game.social.blocked.add(actor)
        else:self.dialogue = None
        return result

    def on_dialogue_cancelled(self, identifier):
        if identifier and identifier.startswith('venn_'):self.dialogue = None

    def _begin_supplies(self):
        if not self.hands_full and self.game.world is self.home and self.partner is not None and self.game.player.position.distance_to(self.partner.position)<=36:
            self.action = 'supplies';self.phase_time = 0.;self.contact = False

    def _near(self, point):
        p = self.game.player.position
        return p.distance_to(point)<=16 and clear_sight(self.town, p, pygame.Vector2(point))

    def _target(self):
        if not self.active or not self.delivered or self.repaired or self.action or self.game.world is not self.town:return None
        if self._near(PIN_APPROACH):
            if 'pin' not in self.inspected:return 'pin', 'E: Inspect the gate pin'
            if self.inspected=={'pin', 'channel'}:return 'choice', 'E: Choose how to repair the gate'
        if self._near(CHANNEL_APPROACH) and 'channel' not in self.inspected:
            return 'channel', 'E: Inspect the blocked water channel'
        return None

    def interact(self):
        if self.game.social.locked:return False
        target = self._target()
        if target is None:return False
        if target[0] in ('pin', 'channel'):
            key = target[0]
            return self._speak(key, lambda: self._record_inspection(key))
        if self.hands_full:return self._speak('hands_full')
        self.dialogue = 'choice'
        return self.game.social.start_choice(self.lines['choice'], [
            {'text': 'Use borrowed tools', 'action': 'tools'},
            {'text': 'Use modest magicks', 'action': 'magicks'}], self._select_method,
            identifier='venn_choice', prompt='How will you free the gate?')

    def _record_inspection(self, key):
        if self.active and self.delivered:self.inspected.add(key);self._save()

    def _select_method(self, method):
        self.dialogue = None
        if (method not in METHODS or self.hands_full or not self.active or not self.delivered or self.repaired or
                self.inspected!={'pin', 'channel'} or self.game.world is not self.town or not self._near(PIN_APPROACH)):
            return False
        self.method = method;self.action = 'repair';self.debris_cleared = False
        self._phase('align_pin');self._save();return True

    def _phase(self, name):
        self.release_pose();self.phase = name;self.phase_time = 0.;self.walk_ms = 0.;self.blocked_seconds = 0.

    def _save(self):self.game.save_progress()

    def _complete(self):
        if self.active and self.delivered and self.repaired:
            self.game.quests.complete_objective(OPENING_QUEST, 'venn')
            self.game.social.flags.add('CH01_MQ01_VENN_DONE')
            if self.method:self.game.social.flags.add('CH01_MQ01_VENN_METHOD_'+self.method.upper())
            self._save()

    def interaction_hint(self):
        if not self.active or self.game.social.locked:return ''
        if self.action:return 'Passing the recovery supplies…' if self.action=='supplies' else 'Freeing the irrigation gate…'
        target = self._target()
        if target:return target[1]
        if self.game.world is self.home:
            return 'Approach either parent with the recovery supplies.' if not self.delivered else 'Speak with the family.' if self.repaired else 'The irrigation gate is east of the cottage. E: inspect.'
        if self.game.world is self.town and self.delivered:
            if self.repaired:return 'Return to the Venn family.'
            if self.inspected=={'pin', 'channel'}:return 'Return to the gate pin to choose a repair.'
            return 'Inspect the gate pin and the channel just downstream.'
        return ''

    def tracker_text(self):
        if not self.active:return ''
        if self.hands_full and not self.repaired:return 'Set Elira’s lantern safely on her table first.'
        if self.action=='repair':return 'Freeing the irrigation gate…'
        if self.game.world is self.home and not self.delivered:return 'Give the Venn family their supplies.'
        if not self.delivered:return ''
        if self.repaired:return 'Return to the Venn family.'
        return f'Inspect the gate and channel: {len(self.inspected)}/2.' if len(self.inspected)<2 else 'Choose a repair at the gate. E: interact.'

    def journal_detail(self):
        if not self.active:return ''
        if not self.delivered:return 'Recovery supplies are in the satchel.'
        return 'Recovery supplies delivered. '+('Water is flowing again; speak with the family.' if self.repaired else f'Gate/channel inspections: {len(self.inspected)}/2.')

    def release_pose(self):
        if not self._pose_owned:return
        for name in ('story_sprite', 'story_draw_anchor'):
            if hasattr(self.game.player, name):delattr(self.game.player, name)
        self._pose_owned = False

    def _pose(self, name):
        self.game.player.story_sprite = self.town.image(ART+'caelan/'+name+'.png')
        self.game.player.story_draw_anchor = (20, 38);self._pose_owned = True

    def _walk(self, goal, seconds):
        self.release_pose();p = self.game.player;delta = pygame.Vector2(goal)-p.position
        if delta.length()<.05:p.position.update(goal);p.moving = False;p.facing = 'right';return True
        before = p.position.copy();p.update(delta, min(seconds, delta.length()/72), self.town)
        self.walk_ms += seconds*1000;p.walk_ms = self.walk_ms
        self.blocked_seconds = self.blocked_seconds+seconds if before==p.position else 0.
        if self.blocked_seconds>=1:
            self.action = None;self.phase = None;self._last_art = None
        return False

    def update(self, seconds):
        if self.repaired:self.flow_seconds = min(100., self.flow_seconds+seconds)
        if self.action=='supplies':
            self.phase_time += seconds
            self.game.player.facing = facing_toward(self.partner.position-self.game.player.position)
            self._pose('give_'+self.game.player.facing)
            if self.phase_time>=.4 and not self.contact:
                self.contact = True;self.game.deliver_quest_item(OPENING_QUEST, 'venn', 'venn')
            if self.phase_time>=.85:self.action = None;self.release_pose();self._save()
        elif self.action=='repair':self._repair(seconds)
        self._update_art()

    def _repair(self, seconds):
        phase = self.phase
        if phase in ('align_pin', 'align_channel', 'return_pin'):
            goal = CHANNEL_APPROACH if phase=='align_channel' else PIN_APPROACH
            if self._walk(goal, seconds):
                self._phase('ease_water' if phase=='align_pin' and self.method=='magicks' else
                            'work_pin' if phase=='align_pin' else 'clear_channel' if phase=='align_channel' else 'open')
            return
        self.phase_time += seconds;t = self.phase_time
        if phase=='ease_water':
            self._pose('magicks_'+str(min(3, int(t/.3))))
            if t>=1.2:self._phase('work_pin')
        elif phase=='work_pin':
            self._pose(('tools_' if self.method=='tools' else 'hands_')+str(int(t/.2)%4))
            if t>=1.2:self._phase('align_channel' if self.method=='tools' else 'open')
        elif phase=='clear_channel':
            self._pose('hands_'+str(min(3, int(t/.25))))
            if t>=.8:self.debris_cleared = True
            if t>=1.:self._phase('return_pin')
        elif phase=='open':
            self._pose('hands_'+str(min(3, int(t/.3))))
            if self.method=='magicks' and t>=.6:self.debris_cleared = True
            if t>=1.2:
                self.repaired = True;self.debris_cleared = True;self.flow_seconds = 0.
                self._phase('finish');self._save()
        elif phase=='finish':
            if t>=.4:self.action = None;self.phase = None;self.release_pose();self._save()

    def _gate_frame(self, phase):
        if self.action=='repair':
            if self.phase=='work_pin':return 'repair', min(5, int(self.phase_time/.2))
            if self.phase=='open':return 'opening', min(5, int(self.phase_time/.2))
            if self.phase in ('align_channel', 'clear_channel', 'return_pin'):return 'idle_closed', phase
        return ('idle_open' if self.repaired else 'idle_jammed'), phase

    def _update_art(self, force=False):
        if not force and self.game.world is not self.town:return
        phase = int(self.game.elapsed_ms//200)%6;animation, frame = self._gate_frame(phase)
        magic = self.action=='repair' and self.method=='magicks' and self.phase in ('ease_water', 'work_pin')
        signature = (phase, animation, frame, magic, self.debris_cleared, int(self.flow_seconds/.16) if self.repaired and self.flow_seconds<12 else 100)
        if signature==self._last_art and not force:return
        self._last_art = signature
        gate = self.backgrounds[phase].copy();gate.blit(self.gates[animation][frame], (0, 0))
        self.surface_props[2]['surface'] = gate
        debris = self.surface_props[3]
        debris['position'] = [1446, 680]
        if self.action=='repair' and not self.debris_cleared:
            if self.phase=='clear_channel':
                fraction = min(1., self.phase_time/.8)
                debris['position'] = [1446-round(6*fraction), 680-round(fraction)]
            elif self.phase=='open' and self.method=='magicks':
                debris['position'] = [1446, 680+round(16*min(1., self.phase_time/.6))]
        effect = self.surface_props[4]['surface'];effect.fill((0, 0, 0, 0))
        if magic:
            # Ripples stay strictly inside the existing upstream water pixels.
            for y in (phase, phase+6):
                if y<12:pygame.draw.lines(effect, '#c1d6cc', False, [(1, y+1), (3, y), (6, y+1)], 1)
        for i, prop in enumerate(self.water_props):
            if not self.surface_prop_visible(prop):continue
            key = (i, phase)
            if key not in self._water_cache:
                image = prop['images'][phase];rect = image.get_rect(topleft=prop['position'])
                background = self.town.ground[phase].subsurface(rect).copy()
                background.blit(image, (0, 0));self._water_cache[key] = background
            prop['surface'] = self._water_cache[key]

    def draw_world(self, canvas, camera):
        if self.action!='supplies' or self.game.world is not self.home:return
        actor = self.partner if self.contact else self.game.player
        canvas.blit(self.home.image(ART+'provisions.png'),
                    (round(actor.position.x)+3-camera[0], round(actor.position.y)-12-camera[1]))
