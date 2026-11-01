"""One borrowed seat, with the original northern guards always covering duty.

This controller borrows the two existing actors; gates, release flags and the
regional layout remain owned by OverworldWorld. Every acknowledged line and
physical contact is a checkpoint. Explicit snapshots also retain exact feet,
route segment and the bounded animation clock.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
ART = ROOT/'assets/characters/checkpoint_charm'
SCENE_ID = 'checkpoint_borrowed_seat'
BENCH = (377, -2166)
SUPPLIES = (306, -2194)
SACK_CONTACT = (328.8, -2200.8)
WITNESS = (408, -2140)
HOMES = {'owner': (432, -2232), 'borrower': (552, -2208)}
ROUTES = {
    'owner_to_seat': ('owner', [(432, -2160), (377, -2160), BENCH]),
    'owner_out': ('owner', [(377, -2160), (306, -2160), SUPPLIES]),
    'borrower_out': ('borrower', [(552, -2160), (377, -2160), BENCH]),
    'borrower_home': ('borrower', [(377, -2160), (552, -2160), HOMES['borrower']]),
    'owner_home': ('owner', [(306, -2192), (432, -2192), HOMES['owner']]),
}
# Timed stages name their one physical contact. Nothing is emitted twice when
# Continue resumes after that contact but before the action finishes.
ACTIONS = {
    'owner_sit': ('owner', 'sit_down_front', .95, .65, 0),
    'owner_stand': ('owner', 'stand_up_front', .95, .65, 1),
    'check': ('owner', 'check_right', 1.6, .85, 2),
    'borrower_sit': ('borrower', 'sit_down_front', .95, .65, 3),
    'borrower_stand': ('borrower', 'stand_up_front', .95, .65, 4),
}
NEXT = {
    'owner_to_seat': 'owner_sit', 'owner_sit': 'opening',
    'opening': 'owner_stand', 'owner_stand': 'owner_out',
    'owner_out': 'check', 'check': 'borrower_out',
    'borrower_out': 'borrower_sit', 'borrower_sit': 'banter',
    'banter': 'borrower_stand', 'borrower_stand': 'borrower_home',
    'borrower_home': 'owner_home', 'owner_home': 'closing', 'closing': 'done',
}
LINES = {
    'opening': [('owner', "Time to count the stores. Mind the road while I'm up?"),
                ('borrower', 'Both eyes. Off you go.')],
    'banter': [('owner', "That's my seat."),
               ('borrower', 'I know. It was looking underemployed.'),
               ('owner', 'Then keep the road in view while you work it.')],
    'closing': [('owner', 'Same count. Same road.'),
                ('borrower', 'And a very well-rested seat.')],
    'repeat': [('owner', 'All counted. Your watch.'),
               ('borrower', "And your seat. I've had my turn.")],
}
OFFSETS = {'opening': 0, 'banter': 2, 'closing': 5}
READS = {
    'idle': (0,), 'owner_to_seat': (0,), 'owner_sit': (0,),
    'opening': (0, 1), 'owner_stand': (2,), 'owner_out': (2,),
    'check': (2,), 'borrower_out': (2,), 'borrower_sit': (2,),
    'banter': (2, 3, 4), 'borrower_stand': (5,), 'borrower_home': (5,),
    'owner_home': (5,), 'closing': (5, 6), 'done': (7,), 'repeat': (7,),
}
CONTACTS = {
    'idle': 0, 'owner_to_seat': 0, 'opening': 1, 'owner_out': 2,
    'borrower_out': 3, 'banter': 4, 'borrower_home': 5,
    'owner_home': 5, 'closing': 5, 'done': 5, 'repeat': 5,
}


def empty_state():
    return {'version': 1, 'stage': 'idle', 'step': 0, 'elapsed': 0.,
            'read': 0, 'repeat_read': 0, 'contacts': 0, 'clock': 0.,
            'positions': {role: list(point) for role, point in HOMES.items()},
            'moving': False, 'facing': 'front'}


def valid_state(data):
    if not isinstance(data, dict) or set(data) != set(empty_state()):return False
    stage = data.get('stage')
    if not isinstance(stage, str) or stage not in READS or type(data['version']) is not int or data['version'] != 1:return False
    if type(data['read']) is not int or data['read'] not in READS[stage]:return False
    if type(data['repeat_read']) is not int or data['repeat_read'] not in ((0, 1) if stage == 'repeat' else (0,)):return False
    if type(data['contacts']) is not int:return False
    if type(data['step']) is not int or data['step'] < 0:return False
    if stage in ROUTES:
        if data['step'] >= len(ROUTES[stage][1]):return False
    elif data['step'] != 0:return False
    if type(data['moving']) is not bool or (data['moving'] and stage not in ROUTES):return False
    if not isinstance(data['facing'], str) or data['facing'] not in ('front', 'back', 'left', 'right'):return False
    for key, limit in (('elapsed', ACTIONS[stage][2] if stage in ACTIONS else 0), ('clock', 2.1)):
        value = data[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= limit:return False
    contact = CONTACTS.get(stage)
    if stage in ACTIONS:
        _, _, _, time, before = ACTIONS[stage]
        contact = before+int(data['elapsed'] >= time)
    if data['contacts'] != contact:return False
    positions = data['positions']
    if not isinstance(positions, dict) or set(positions) != set(HOMES):return False
    for point in positions.values():
        if (not isinstance(point, list) or len(point) != 2 or any(type(n) not in (int, float)
                or not math.isfinite(n) for n in point)
                or not (300 <= point[0] <= 552 and -2232 <= point[1] <= -2148)):return False
    # Duty is an invariant of the snapshot, not a promise made by animation.
    if stage in ('idle', 'done', 'repeat', 'closing'):
        if any(positions[role] != list(home) for role, home in HOMES.items()):return False
    elif stage in ('owner_to_seat', 'owner_sit', 'opening', 'owner_stand', 'owner_out', 'check'):
        if positions['borrower'] != list(HOMES['borrower']):return False
    elif stage in ('borrower_out', 'borrower_sit', 'banter', 'borrower_stand', 'borrower_home'):
        if positions['owner'] != list(SUPPLIES):return False
    elif stage == 'owner_home' and positions['borrower'] != list(HOMES['borrower']):return False
    stationary = {'owner_sit': ('owner', BENCH), 'opening': ('owner', BENCH),
                  'owner_stand': ('owner', BENCH), 'check': ('owner', SUPPLIES),
                  'borrower_sit': ('borrower', BENCH), 'banter': ('borrower', BENCH),
                  'borrower_stand': ('borrower', BENCH)}
    if stage in stationary:
        role, point = stationary[stage]
        if positions[role] != list(point):return False
    if stage in ROUTES:
        role, route = ROUTES[stage]
        starts = {'owner_to_seat': HOMES['owner'], 'owner_out': BENCH,
                  'borrower_out': HOMES['borrower'], 'borrower_home': BENCH,
                  'owner_home': SUPPLIES}
        before = starts[stage] if data['step'] == 0 else route[data['step']-1]
        after = route[data['step']];point = positions[role]
        # Every authored segment is cardinal. A corrupt snapshot must not
        # teleport a guard into a sack, across the gate, or outside the route.
        if any(not min(a, b)-.000001 <= n <= max(a, b)+.000001
               for n, a, b in zip(point, before, after)):return False
    return True


def progress_state(data):
    """Stable autosave dirtiness; precise explicit snapshots remain available."""
    return {key: copy.deepcopy(value) for key, value in data.items()
            if key not in ('positions', 'elapsed', 'clock', 'moving', 'facing')}


class CheckpointCharm:
    def __init__(self, world):
        self.world = world
        self.actors = {role: actor for index, role in enumerate(HOMES)
                       for actor in world.npcs
                       if actor.data['id'] == f'road_guard:north_checkpoint:{index}'}
        self.enabled = len(self.actors) == 2
        if not self.enabled:self.actors = {}
        self.clips = {}
        if self.enabled:
            metadata = json.loads((ART/'animation.json').read_text())
            for key, clip in metadata['clips'].items():
                self.clips[key] = {**clip, 'frames': [{**frame, 'image': pygame.image.load(
                    str(ART/frame['file'])).convert_alpha()} for frame in clip['frames']]}
        self.restore()

    @property
    def stage(self):return self.state['stage']

    @property
    def duty_guard(self):
        if not self.enabled:return None
        return self.actors['owner' if self.stage in (
            'borrower_out', 'borrower_sit', 'banter', 'borrower_stand', 'borrower_home') else 'borrower']

    def restore(self, data=None):
        candidate = empty_state() if data is None else copy.deepcopy(data)
        if not valid_state(candidate):raise ValueError('Invalid checkpoint scene state')
        if data is None:
            for actor in self.actors.values():actor.end_conversation()
        self.state = candidate
        self._dialogue_running = False
        self._awaiting_resume = self.stage in LINES
        self._apply()

    def to_dict(self):
        result = copy.deepcopy(self.state)
        if self.enabled:result['positions'] = {role: list(actor.position) for role, actor in self.actors.items()}
        return result

    def progress_dict(self):return progress_state(self.to_dict())

    def _image(self, key, time, duration=None):
        clip = self.clips[key];frames = clip['frames']
        total = sum(frame['duration_ms'] for frame in frames)
        clock = time*1000 if duration is None else time/duration*total
        clock = clock % total if clip.get('loop', False) else min(clock, total-.001)
        for frame in frames:
            if clock < frame['duration_ms']:return frame['image']
            clock -= frame['duration_ms']
        return frames[-1]['image']

    def _apply(self):
        if not self.enabled:return
        stage = self.stage
        for role, actor in self.actors.items():
            actor.position.update(self.state['positions'][role])
            actor.moving = False
            actor.on_duty = actor is self.duty_guard
            actor.story_sprite = None;actor.story_draw_anchor = None
        if stage in ('idle', 'done', 'repeat'):return
        # During scene ownership, ordinary guard greetings can end without
        # overwriting the alert supplies stance on the following update.
        owner, borrower = self.actors['owner'], self.actors['borrower']
        owner.facing = 'right' if stage in ('check', 'borrower_out', 'borrower_sit',
            'banter', 'borrower_stand', 'borrower_home') else 'front'
        borrower.facing = 'front'
        for actor in self.actors.values():
            actor.story_sprite = actor._frames['idle_'+actor.facing+'_0.png']
            actor.story_draw_anchor = (20, 38)
        if stage in ROUTES:
            actor = self.actors[ROUTES[stage][0]]
            actor.moving = self.state['moving'];actor.facing = self.state['facing']
            if actor.moving:actor.story_sprite = self._image('walk_'+actor.facing, self.state['clock'])
            else:actor.story_sprite = actor._frames['idle_'+actor.facing+'_0.png']
        if stage in ACTIONS:
            role, key, duration, _, _ = ACTIONS[stage]
            self.actors[role].story_sprite = self._image(key, self.state['elapsed'], duration)
        if stage == 'opening':owner.story_sprite = self._image('sit_front', self.state['clock'])
        if stage == 'banter':borrower.story_sprite = self._image('sit_front', self.state['clock'])

    def _commit(self, game):
        self.state['positions'] = {role: list(actor.position) for role, actor in self.actors.items()}
        self._apply()
        game.save_progress()

    def _stage(self, stage, game):
        self.state.update(stage=stage, step=0, elapsed=0., clock=0., moving=False, facing='front')
        self._awaiting_resume = False
        self._commit(game)

    def _nearby(self, game):
        if not self.enabled or game.world is not self.world:return False
        at_bench = game.player.position.distance_to(BENCH) <= 44
        at_guard = any(game.player.position.distance_to(actor.position) <= 52
                       for actor in self.actors.values())
        # The finite scene owns input around both participants until they have
        # finished changing places. Idle posts retain ordinary road information.
        if self.stage not in ('idle', 'done'):return at_bench or at_guard
        return at_bench and not at_guard

    def interaction_hint(self, game):
        if not self._nearby(game):return ''
        if self.stage == 'idle':return 'E: Watch the checkpoint'
        if self.stage == 'done':return 'E: Share a quiet word'
        if self.stage in LINES:return 'E: Listen to the guards'
        return 'The guards are changing places'

    def _line(self, game):
        stage = self.stage
        index = self.state['repeat_read'] if stage == 'repeat' else self.state['read']-OFFSETS[stage]
        role, text = LINES[stage][index]
        key = 'checkpoint_'+role
        game.social.data['speakers'][key] = {'name': 'Road guard', 'portrait': 'road_guard',
                                            'actor_id': self.actors[role].data['id']}
        def done():
            self._dialogue_running = False
            if self.stage != stage:return
            counter = 'repeat_read' if stage == 'repeat' else 'read'
            self.state[counter] += 1
            if index+1 == len(LINES[stage]):
                if stage == 'repeat':self.state['repeat_read'] = 0
                self._stage('done' if stage == 'repeat' else NEXT[stage], game)
            else:self._commit(game)
        started = game.social.start_script([{'speaker': key, 'text': text}], on_complete=done,
                                           identifier=SCENE_ID+'_'+stage)
        self._dialogue_running = started
        if started:self._awaiting_resume = False
        return started

    def interact(self, game):
        if not self._nearby(game):return False
        if game.social.locked:
            return (self.stage not in ('idle', 'done') and
                    str(game.social.script_identifier).startswith(SCENE_ID+'_'))
        if self.stage == 'idle':self._stage('owner_to_seat', game);return True
        if self.stage == 'done':self._stage('repeat', game)
        # E during movement or a timed contact observes the current beat. It
        # cannot fall through to a travel-info script or restart the program.
        return self._line(game) if self.stage in LINES else True

    def _walk(self, seconds, game):
        role, route = ROUTES[self.stage];actor = self.actors[role]
        target = pygame.Vector2(route[self.state['step']]);delta = target-actor.position
        if delta.length() < .001:
            self.state['step'] += 1
            if self.state['step'] == len(route):self._stage(NEXT[self.stage], game)
            else:self._commit(game)
            return
        from social import facing_toward
        self.state['facing'] = facing_toward(delta)
        remaining = min(delta.length(), 25*seconds)
        player = self.world.probe_rect(game.player.position)
        while remaining > .00001:
            distance = min(1., remaining);point = actor.position+delta.normalize()*distance
            if not self.world.can_stand(point, actor.probe_size, actor, player):break
            actor.position.update(point);remaining -= distance;self.state['moving'] = True

    def update(self, seconds, game):
        if not self.enabled or game.world is not self.world:return
        # Idling for hours must not leak an unbounded clock into the first save.
        if self.stage in ('idle', 'done'):
            self.state['clock'] = 0.;return
        if self._dialogue_running and (not game.social.locked or
                not str(game.social.script_identifier).startswith(SCENE_ID+'_')):
            self._dialogue_running = False
            self._awaiting_resume = True
        if game.social.locked:return
        if game.player.position.distance_to(BENCH) > 280:return
        dt = min(.1, max(0., seconds))
        self.state['clock'] = (self.state['clock']+dt) % 2.1
        self.state['moving'] = False
        if self.stage in LINES:
            # Cancellation leaves this exact unread line available for E. An
            # acknowledged line may continue automatically while witnessing.
            if not self._dialogue_running and not self._awaiting_resume:self._line(game)
        elif self.stage in ROUTES:self._walk(dt, game)
        elif self.stage in ACTIONS:
            _, _, duration, contact, before = ACTIONS[self.stage]
            self.state['elapsed'] = min(duration, self.state['elapsed']+dt)
            if self.state['elapsed'] >= contact and self.state['contacts'] == before:
                self.state['contacts'] += 1
                from regional_audio import Source
                supplies = self.stage == 'check'
                game.regional_audio.play(Source('checkpoint_contact_'+str(before),
                    'rustle' if supplies else 'creak', 'checkpoint_material',
                    SACK_CONTACT if supplies else BENCH, gain=.34,
                    near=28, far=180, priority=2, cooldown=.8))
                self._commit(game)
            if self.state['elapsed'] >= duration:self._stage(NEXT[self.stage], game)
        self.state['positions'] = {role: list(actor.position) for role, actor in self.actors.items()}
        self._apply()
