"""Local people and optional observations in Elden Vale Sanctuary.

These ambient exchanges never own a quest checkpoint or a durable reward. NPCs
belong to the reserve scene, independently of the town's household actors.
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from social import clear_sight, facing_toward


ROOT = Path(__file__).resolve().parent
STORY = ROOT/'assets/story/sanctuary_reserve'
SCENE_ID = 'elden_vale_sanctuary'
HALL_ID = 'elden_vale_sanctuary_hall'
DIRECTIONS = ('front', 'back', 'left', 'right')


class ReserveVisitor:
    """An ordinary directional sprite with a small, visible ground footprint."""
    def __init__(self, record, world):
        self.data = dict(record)
        self.position = pygame.Vector2(record['position'])
        self.home_facing = record.get('facing', 'front')
        self.facing = self.home_facing
        self.scene_id = SCENE_ID
        self.probe_size = (10, 6)
        self.draw_anchor = (12, 30)
        self.moving = False
        self.conversation_ready = False
        base = 'assets/characters/npcs/'+record['variant']
        self.idles = {direction:world.image(base+'/idle_'+direction+'.png')
                      for direction in DIRECTIONS}

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-5, round(self.position.y)-3, 10, 6)

    def request_conversation(self, facing):
        self.facing = facing
        self.conversation_ready = True

    def end_conversation(self):
        self.facing = self.home_facing
        self.conversation_ready = False

    def sprite(self, elapsed_ms):
        return self.idles[self.facing]


class ReserveCaretaker(ReserveVisitor):
    """Reuse the gardener's drawn poses, grips and bucket registration intact."""
    def __init__(self, record, world):
        super().__init__(record, world)
        base = 'assets/characters/npcs/female_02/gardener/'
        self.animation = json.loads((ROOT/base/'animations.json').read_text())
        self.bodies = {key:world.image(base+pose['body'])
                       for key,pose in self.animation['poses'].items()}
        self.buckets = {key:world.image(base+pose['file'])
                        for key,pose in self.animation['buckets'].items()}
        self.draw_anchor = tuple(self.animation['draw_anchor'])
        self.clock = 0.
        self.root = pygame.Vector2(record['plant_root'])
        self._frames = {}

    def update(self, seconds):
        if not self.conversation_ready:
            self.clock = (self.clock+max(0., seconds)) % 18.

    def _pose(self):
        if self.conversation_ready:
            return 'idle_full.'+self.facing, {}
        # Long pauses keep this a small act of care rather than a frantic loop.
        time = self.clock-6.
        if time < 0 or self.clock >= 10.:
            return 'idle_full.'+self.home_facing, {}
        frames = self.animation['animations']['pour.'+self.home_facing]
        milliseconds = time*1000
        for frame in frames:
            if milliseconds < frame['duration_ms']:
                return frame['pose'], frame
            milliseconds -= frame['duration_ms']
        return 'idle_full.'+self.home_facing, {}

    def sprite(self, elapsed_ms):
        name, frame = self._pose()
        pose = self.animation['poses'][name]
        key = 'bucket_'+str(frame.get('angle', 0))+'_6'
        bucket = self.animation['buckets'][key]
        offset = (pygame.Vector2(self.animation['body_offset'])+
                  pose['grip']-pygame.Vector2(bucket['grip']))
        cache_key = (name, key)
        if cache_key not in self._frames:
            surface = pygame.Surface(self.animation['action_canvas'], pygame.SRCALPHA)
            if pose['order'] == 'before':surface.blit(self.buckets[key], offset)
            surface.blit(self.bodies[name], (0,0))
            if pose['order'] == 'after':surface.blit(self.buckets[key], offset)
            self._frames[cache_key] = surface
        return self._frames[cache_key]

    def draw_foreground(self, target, camera):
        _, frame = self._pose()
        if frame.get('effect') != 'pour':return
        angle = frame.get('angle', 0)
        bucket = self.animation['buckets']['bucket_'+str(angle)+'_6']
        pose = self.animation['poses'][frame['pose']]
        offset = (pygame.Vector2(self.animation['body_offset'])+
                  pose['grip']-pygame.Vector2(bucket['grip']))
        origin = self.position-pygame.Vector2(self.draw_anchor)+offset+bucket['spout']
        middle = origin.lerp(self.root, .5);middle.y -= 2
        points = [tuple(round(value) for value in point-pygame.Vector2(camera))
                  for point in (origin,middle,self.root)]
        pygame.draw.lines(target, '#7ba8ad', False, points, 2)
        pygame.draw.lines(target, '#d4e7dc', False, points, 1)
        # The stream is drawn in world space, so a nearby root never gets
        # clipped at the edge of the gardener's fixed native action canvas.


class SanctuaryReserve:
    def __init__(self, game):
        self.game = game
        self.layout = json.loads((STORY/'layout.json').read_text())
        self.dialogue = json.loads((STORY/'scene.json').read_text())
        self._world = None
        self.actors = {}
        self._conversation = None

    @property
    def active(self):
        return self.game.world.data.get('id') in (SCENE_ID, HALL_ID)

    @property
    def targets(self):
        key = 'hall_targets' if self.game.world.data.get('id') == HALL_ID else 'targets'
        geometry = self.game.world.data.get('inspection_points', {})
        approaches = self.game.world.data.get('public_approaches', {})
        result = {}
        for identifier, record in self.layout[key].items():
            point = geometry.get(record.get('geometry_id', identifier), {})
            result[identifier] = {**record, **{field:point[field]
                                  for field in ('position','approach') if field in point}}
            approach = approaches.get(record.get('approach_id', identifier))
            if approach is not None:result[identifier]['approach'] = list(approach)
        arrival=getattr(self.game,'sanctuary_arrival',None)
        if key=='targets' and getattr(arrival,'completed',False) and self.game.regent_quest.stage=='sanctuary_arrival_pending':
            for role in ('caretaker','worker_a','worker_b','runner','sentry'):
                actor=arrival.actors.get(role)
                if actor is not None:
                    result['emergency_'+role]={'position':list(actor.position),'approach':list(actor.position),
                        'radius':38,'actor':'emergency_'+role,'label':{'caretaker':'Speak with the caretaker','worker_a':'Speak with the injured worker','worker_b':'Speak with the injured worker','runner':'Speak with the attendant','sentry':'Speak with the lookout'}[role],'script':'emergency_'+role}
        return result

    def _actor(self,key):
        if key and key.startswith('emergency_'):
            return self.game.sanctuary_arrival.actors.get(key.removeprefix('emergency_'))
        return self.actors.get(key)

    def ensure_world(self):
        world = self.game.world
        if world.data.get('id') != SCENE_ID:return
        if world is self._world:return
        self._release_conversation()
        self._world = world
        self.actors = {}
        for record in self.layout['actors']:
            actor = (ReserveCaretaker if record['id'] == 'reserve_caretaker'
                     else ReserveVisitor)(record, world)
            if not world.can_stand(actor.position, actor.probe_size, actor):
                raise ValueError('Blocked sanctuary resident: '+record['id'])
            self.actors[record['id']] = actor
            world.npcs.append(actor)
        social = self.game.social
        portraits = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())['portraits']
        for record in self.layout['actors']:
            portrait = record['variant']
            social.data['speakers'][record['id']] = {
                'name':record['name'], 'portrait':portrait, 'actor_id':record['id']}
            if portrait not in social.portraits:
                social.portraits[portrait] = world.image(
                    'assets/portraits/eldenmere/'+portraits[portrait]['file'])

    def _release_conversation(self):
        for actor in self.actors.values():actor.end_conversation()
        self._conversation = None

    def reset(self):
        self._release_conversation()
        for record in self.layout['actors']:
            actor = self.actors.get(record['id'])
            if actor is not None:
                actor.position.update(record['position'])
                if isinstance(actor, ReserveCaretaker):actor.clock = 0.

    def update(self, seconds):
        if not self.active:
            self._release_conversation()
            return
        self.game.world.reduced_motion = bool(
            getattr(getattr(self.game, 'audio', None), 'reduced_motion', False))
        self.ensure_world()
        social = self.game.social
        if self._conversation is not None and (
                not social.locked or social.script_identifier != self._conversation):
            self._release_conversation()
        if self.game.world.data.get('id') != SCENE_ID:return
        if (social.locked or self.game.map_open or self.game.quest_ui.journal_open
                or self.game.pause.is_open or self.game.inventory_ui.is_open):return
        for actor in self.actors.values():
            if isinstance(actor, ReserveCaretaker):actor.update(seconds)

    def _available(self):
        game = self.game
        return (self.active and not game.on_title and not game.social.locked
                and not game.pause.is_open and not game.inventory_ui.is_open
                and not game.map_open and not game.quest_ui.journal_open
                and not game.combat.active and not game.transfer_cooldown)

    def _nearby(self):
        if not self._available():return None
        self.ensure_world()
        game = self.game
        forward = pygame.Vector2({'front':(0,1),'back':(0,-1),
                                  'left':(-1,0),'right':(1,0)}[game.player.facing])
        candidates = []
        for key, target in self.targets.items():
            position = pygame.Vector2(target['position'])
            actor = self._actor(target.get('actor')) if game.world.data.get('id') == SCENE_ID else None
            if actor is not None:position = actor.position
            delta = position-game.player.position
            if delta.length_squared() and delta.normalize().dot(forward) < .1:continue
            approach = pygame.Vector2(target['approach'])
            if game.player.position.distance_to(approach) > target.get('radius', 32):continue
            sight = actor.position if actor is not None else approach
            if not clear_sight(game.world, game.player.position, sight):continue
            candidates.append((delta.length_squared(),key,target))
        return min(candidates, key=lambda item:item[:2])[1:] if candidates else None

    def interaction_hint(self):
        nearby = self._nearby()
        return 'E: '+nearby[1]['label'] if nearby else ''

    def interact(self):
        nearby = self._nearby()
        if nearby is None:return False
        key,target = nearby
        identifier = 'sanctuary_reserve_'+key
        script=target.get('script',key)
        arrival=getattr(self.game,'sanctuary_arrival',None)
        if getattr(arrival,'completed',False):
            if script=='cave':script='cave_open'
            elif self.game.regent_quest.stage=='sanctuary_arrival_pending' and script in ('caretaker','visitors'):
                script='emergency_caretaker_gardener' if script=='caretaker' else 'emergency_visitors'
        if not self.game.social.start_script(self.dialogue[script],
                                              on_complete=self._release_conversation,
                                              identifier=identifier):return False
        self._conversation = identifier
        actor = self._actor(target.get('actor'))
        if actor is not None:
            actor.request_conversation(facing_toward(self.game.player.position-actor.position))
        return True
