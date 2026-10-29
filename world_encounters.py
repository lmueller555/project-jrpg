"""Optional Eldenmere encounters and atomic return to the saved journey."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import random
from uuid import uuid4

import pygame

from aether_lattice import MAX_RP
from battle_model import BattleModel
from battle_scene import BattleScene
from inventory import MAX_QUANTITY


ROOT = Path(__file__).resolve().parent
ENCOUNTER_PATH = ROOT/'assets/combat/encounter.json'


class CombatEncounters:
    """One visible, opt-in test Bat; battle state never leaks into a checkpoint."""

    def __init__(self, game):
        self.game = game
        self.definition = json.loads(ENCOUNTER_PATH.read_text(encoding='utf-8'))
        self.position = pygame.Vector2(self.definition['position'])
        self.radius = self.definition['interaction_radius']
        self.scene = None
        self.receipt_id = None
        self.cooldown = 0.0
        self.world_seconds = 0.0
        self._settled = False
        self._frames = None

    @property
    def active(self):return self.scene is not None

    @property
    def model(self):return self.scene.model if self.scene is not None else None

    def reset(self):
        self.scene = None
        self.receipt_id = None
        self.cooldown = self.world_seconds = 0.0
        self._settled = False

    def _exploration_available(self):
        game = self.game
        return (not self.active and not game.on_title
                and game.world.data['id'] == self.definition['scene']
                and not game.pause.is_open and not game.inventory_ui.is_open
                and not game.quest_ui.journal_open and not game.map_open
                and not game.social.locked and not game.opening.locks_player
                and not game.household_action and not game.transfer_cooldown
                and not game.opening_fade and game.attributes.current_hp > 0)

    def nearby(self):
        return (self._exploration_available() and self.cooldown <= 0
                and self.game.player.position.distance_squared_to(self.position) <= self.radius**2)

    def interaction_hint(self):
        return 'E: Engage Bat' if self.nearby() else ''

    def interact(self, rng=None):
        if not self.nearby():return False
        model = BattleModel(self.game.attributes,
                            self.game.lattice.learned_abilities(),
                            rng=random.Random() if rng is None else rng,
                            enemy_id=self.definition['enemy'])
        model.enemy_definition['rewards'] = self._available_rewards(model.enemy_definition['rewards'])
        self.scene = BattleScene(self.game, model)
        self.receipt_id = 'battle:'+uuid4().hex
        self._settled = False
        self.game.player.moving = self.game.player.running = False
        self.game.player.walk_ms = 0.0
        self.game.social.clear_pointer()
        self.game._mouse_held = False
        return True

    def _available_rewards(self, reward):
        amount = min(reward['rp'], MAX_RP-self.game.lattice.state()['rp'])
        drops = {key: min(quantity, MAX_QUANTITY-self.game.inventory.quantity(key))
                 for key, quantity in reward['drops'].items()
                 if self.game.inventory.quantity(key) < MAX_QUANTITY}
        return {'rp': amount, 'drops': drops}

    def tick_world(self, seconds):
        if self.active:return
        self.world_seconds += seconds
        self.cooldown = max(0.0, self.cooldown-seconds)

    def update(self, seconds):
        if not self.active:return
        self.scene.update(seconds)
        if self.scene.dismissed:self._settle()

    def handle_event(self, event):
        if not self.active:return False
        self.scene.handle_event(event)
        if self.scene.dismissed:self._settle()
        return True

    def _settle(self):
        if not self.active or not self.scene.model.ended or self._settled:return False
        game, scene, model = self.game, self.scene, self.scene.model
        # Defeat is a safe withdrawal in this first encounter: the journey still
        # owns its pre-battle resources, and receives neither drops nor RP.
        if model.phase != 'defeat':
            proposed = deepcopy(game.attributes)
            if not proposed.set_current(hp=model.player.hp, mp=model.player.mp):
                scene.dismissed = False
                scene.result_error = 'Could not return from battle. Try again.'
                return False
        if model.phase == 'victory' and not game.lattice.has_receipt(self.receipt_id):
            reward = self._available_rewards(model.enemy_definition['rewards'])
            # At technical storage limits, keep the room that remains; those
            # limits must never make a completed test encounter impossible to leave.
            awards = {'caelan': reward['rp']} if reward['rp'] else {}
            drops = reward['drops']
            if (awards or drops) and not game.lattice_progression.award_battle_rewards(
                    self.receipt_id, awards, drops):
                scene.dismissed = False
                scene.result_error = 'Rewards could not be collected. Try again.'
                return False
        if model.phase != 'defeat':
            # Rewards only affect RP/inventory; the already validated resource
            # capacities cannot change between the validation and this assignment.
            if not game.attributes.set_current(hp=model.player.hp, mp=model.player.mp):
                raise RuntimeError('Validated battle resources could not be applied')
        self._settled = True
        self.scene = None
        self.cooldown = self.definition['respawn_seconds']
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game._mouse_held = False
        game.social.clear_pointer()
        game.save_progress()
        return True

    def _load_frames(self):
        if self._frames is not None:return
        path = ROOT/'assets/combat/bat/animation.json'
        if not path.exists():return
        record = json.loads(path.read_text(encoding='utf-8'))
        self._anchor = record['anchor']
        self._frames = [(self.game.town.image((path.parent/frame['file']).relative_to(ROOT).as_posix()),
                         frame['duration_ms'])
                        for frame in record['animations']['idle']['frames']]

    def draw_world(self, canvas, camera):
        if (self.active or self.cooldown > 0
                or self.game.world.data['id'] != self.definition['scene']):return
        self._load_frames()
        if not self._frames:return
        time = self.world_seconds*1000 % sum(duration for _, duration in self._frames)
        image = self._frames[-1][0]
        for candidate, duration in self._frames:
            if time < duration:image = candidate;break
            time -= duration
        point = self.position-pygame.Vector2(camera)
        shadow = pygame.Rect(0, 0, 20, 5);shadow.center = point
        pygame.draw.ellipse(canvas, '#304a35', shadow)
        canvas.blit(image, (round(point.x-self._anchor[0]), round(point.y-self._anchor[1])))
