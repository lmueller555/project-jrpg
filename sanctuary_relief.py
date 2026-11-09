"""A local visitor-care attendant, independent of Sanctuary quest ownership."""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from sanctuary_reserve import ReserveVisitor
from social import clear_sight, facing_toward


ROOT = Path(__file__).resolve().parent
SCENE_ID = 'elden_vale_sanctuary_relief'


class SanctuaryRelief:
    def __init__(self, game):
        self.game = game
        self.data = json.loads((ROOT/'assets/story/sanctuary_relief.json').read_text())
        self._world = None
        self.attendant = None

    @property
    def active(self):return self.game.world.data.get('id') == SCENE_ID

    def ensure_world(self):
        if not self.active:return
        world = self.game.world
        if world is self._world and self.attendant in world.npcs:return
        self._release()
        record = dict(self.data['attendant'])
        record.update(world.data.get('relief_room', {}).get('attendant', {}))
        if 'position' not in record:
            raise ValueError('The relief attendant needs an authored station')
        actor = ReserveVisitor(record, world)
        actor.scene_id = SCENE_ID
        if not world.can_stand(actor.position, actor.probe_size, actor):
            raise ValueError('The relief attendant station is blocked')
        old = next((npc for npc in world.npcs if npc.data.get('id') == record['id']), None)
        if old is not None:world.npcs.remove(old)
        world.npcs.append(actor)
        self._world, self.attendant = world, actor
        portraits = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())['portraits']
        variant = record['variant']
        social = self.game.social
        social.data['speakers'][record['id']] = {
            'name': record['name'], 'portrait': variant, 'actor_id': record['id']}
        if variant not in social.portraits:
            social.portraits[variant] = world.image('assets/portraits/eldenmere/'+portraits[variant]['file'])

    def _release(self):
        if self.attendant is not None:self.attendant.end_conversation()

    def reset(self):
        self._release()
        if self._world is not None and self.attendant is not None:
            if self.attendant in self._world.npcs:self._world.npcs.remove(self.attendant)
        self._world = None
        self.attendant = None

    def update(self, seconds):
        if not self.active:
            self._release()
            return
        self.ensure_world()
        social = self.game.social
        if not social.locked or not str(social.script_identifier or '').startswith('sanctuary_relief_'):
            self._release()

    def _nearby(self):
        if not self.active or not self.game.bed_rest.available(self.data['bed']):return False
        self.ensure_world()
        game, actor = self.game, self.attendant
        if game.player.position.distance_to(actor.position) > self.data['attendant']['radius']:return False
        if not clear_sight(game.world, game.player.position, actor.position):return False
        forward = pygame.Vector2({'front':(0,1), 'back':(0,-1),
                                  'left':(-1,0), 'right':(1,0)}[game.player.facing])
        delta = actor.position-game.player.position
        return not delta.length_squared() or delta.normalize().dot(forward) >= .1

    def interaction_hint(self):return 'E: speak to Attendant Nessa' if self._nearby() else ''

    def interact(self):
        if not self._nearby():return False
        if not self.game.bed_rest.offer_relief(self._nearby, attendant=True):return False
        self.attendant.request_conversation(facing_toward(self.game.player.position-self.attendant.position))
        return True
