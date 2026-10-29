"""Story and optional encounters, with atomic return to the saved journey."""
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
from quests import MILL_QUEST


ROOT = Path(__file__).resolve().parent
ENCOUNTER_PATH = ROOT/'assets/combat/encounter.json'


class CombatEncounters:
    """MQ02's first fight and the later repeatable Bat share battle ownership."""

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
        self.kind = None
        self._mill_intro_started = False
        self._mill_origin = None
        self._world_art = {}

    @property
    def active(self):return self.scene is not None

    @property
    def model(self):return self.scene.model if self.scene is not None else None

    def reset(self):
        self.scene = None
        self.receipt_id = None
        self.cooldown = self.world_seconds = 0.0
        self._settled = False
        self.kind = None
        self._mill_intro_started = False
        self._mill_origin = None

    @property
    def bat_unlocked(self):
        return self.game.mill_quest.combat_unlocked

    def _world_available(self):
        game = self.game
        return (not self.active and not game.on_title
                and not game.pause.is_open and not game.inventory_ui.is_open
                and not game.quest_ui.journal_open and not game.map_open
                and not game.social.locked and not game.opening.locks_player
                and not game.household_action and not game.transfer_cooldown
                and not game.opening_fade and game.attributes.current_hp > 0)

    def _exploration_available(self):
        return (self.bat_unlocked and self._world_available()
                and self.game.world.data['id'] == self.definition['scene'])

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
        self.kind = 'bat'
        self.receipt_id = 'battle:'+uuid4().hex
        self._settled = False
        self.game.player.moving = self.game.player.running = False
        self.game.player.walk_ms = 0.0
        self.game.social.clear_pointer()
        self.game._mouse_held = False
        return True

    def start_mill(self, rng=None):
        """Called after Mira's acknowledged approach, never on town arrival."""
        game, quest = self.game, self.game.mill_quest
        if (not self._world_available() or not quest.encounter_pending
                or game.world is not quest.upstream):
            self._mill_intro_started = False
            return False
        model = BattleModel(game.attributes, game.lattice.learned_abilities(),
                            rng=random.Random() if rng is None else rng,
                            enemy_id='ridgeback_tusker', guest_id='mira')
        model.enemy_definition['rewards'] = self._available_rewards(model.enemy_definition['rewards'])
        self._mill_origin = tuple(game.player.position)
        # A quit/reload resumes on the safe approach with the fight unfinished.
        # The live position remains at the encounter for its eventual aftermath.
        game.player.position.update(quest.upstream.data['spawn'])
        try:
            game.save_progress()
        finally:
            game.player.position.update(self._mill_origin)
        self.scene = BattleScene(game, model, battlefield='millrace', tutorial=True)
        self.kind = 'mill'
        self.receipt_id = 'mq02:ridgeback_tusker'
        self._settled = False
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game.social.clear_pointer()
        game._mouse_held = False
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
        quest = self.game.mill_quest
        approach = self.game.world is quest.upstream and quest._at_encounter_approach()
        if not quest.encounter_pending or not approach:
            self._mill_intro_started = False
        elif quest.encounter_ready and self._world_available() and not self._mill_intro_started:
            self._mill_intro_started = bool(quest.begin_encounter(self.start_mill))

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
        if self.kind == 'mill':return self._settle_mill()
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
        self.kind = None
        self.cooldown = self.definition['respawn_seconds']
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game._mouse_held = False
        game.social.clear_pointer()
        game.save_progress()
        return True

    def _settle_mill(self):
        game, scene = self.game, self.scene
        model, quest = scene.model, game.mill_quest
        outcome = model.phase
        hp, mp = model.player.hp, model.player.mp
        if outcome == 'defeat':
            # Retry the introductory encounter with viable resources. No quest
            # milestone, reward or partial party fight is committed on defeat.
            hp, mp = game.attributes.value('hp'), game.attributes.current_mp
        elif hp == 0:
            # Incapacitation is followed by first aid before exploration resumes.
            hp = max(1, game.attributes.value('hp')//4)
        proposed = deepcopy(game.attributes)
        if not proposed.set_current(hp=hp, mp=mp):
            scene.dismissed = False
            scene.result_error = 'Could not return from battle. Try again.'
            return False
        if outcome == 'victory':
            proposed_quests = deepcopy(game.quests)
            if not quest.encounter_pending or not proposed_quests.complete_objective(MILL_QUEST, 'secure_trail'):
                scene.dismissed = False
                scene.result_error = 'Could not finish the encounter. Try again.'
                return False
            before = (game.lattice.to_dict(), game.inventory.to_dict(),
                      game.quests.to_dict(), quest.to_dict(), set(game.social.flags))
            reward = self._available_rewards(model.enemy_definition['rewards'])
            awards = {'caelan': reward['rp']} if reward['rp'] else {}
            if ((awards or reward['drops']) and not game.lattice.has_receipt(self.receipt_id)
                    and not game.lattice_progression.award_battle_rewards(
                        self.receipt_id, awards, reward['drops'])):
                scene.dismissed = False
                scene.result_error = 'Rewards could not be collected. Try again.'
                return False
            if not quest.battle_won():
                game.lattice.restore(before[0]);game.inventory.restore(before[1])
                game.quests.restore(before[2]);quest.restore(before[3])
                game.social.flags = before[4]
                scene.dismissed = False
                scene.result_error = 'Could not finish the encounter. Try again.'
                return False
        if not game.attributes.set_current(hp=hp, mp=mp):
            raise RuntimeError('Validated battle resources could not be applied')
        if outcome != 'victory':
            game.player.position.update(quest.upstream.data['spawn'])
        elif self._mill_origin is not None:
            game.player.position.update(self._mill_origin)
        self._settled = True
        self.scene = None
        self.kind = None
        self._mill_intro_started = False
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game._mouse_held = False
        game.social.clear_pointer()
        game.camera.reset()
        # Commit resources, once-only rewards and the cleared path together.
        game.save_progress()
        quest.battle_returned(outcome, recovered=model.player.hp <= 0)
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
        self._draw_mira_spear(canvas, camera)
        self._draw_mill_world(canvas, camera)
        if (self.active or self.cooldown > 0
                or not self.bat_unlocked
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

    def _draw_mira_spear(self, canvas, camera):
        quest = self.game.mill_quest
        carried = (quest.mira_armed and quest._mira_world is self.game.world
                   and not quest.action and not quest._mira_pose)
        stowed = (getattr(quest, 'mira_spear_stowed', False)
                  and self.game.world is quest.upstream)
        if not carried and not stowed:return
        if 'spear' not in self._world_art:
            folder = ROOT/'assets/combat/mira'
            if not (folder/'world_spear.json').exists():return
            record = json.loads((folder/'world_spear.json').read_text())
            image = pygame.image.load(str(folder/'world_spear.png')).convert_alpha()
            self._world_art['spear'] = image, record['hand_anchor']
        source, anchor = self._world_art['spear']
        if carried:
            facing = quest.mira.facing
            angle = {'front': -8, 'back': 8, 'left': 20, 'right': -20}.get(facing, 0)
            hand = quest.mira.position+pygame.Vector2(-8 if facing == 'left' else 8, -13)
        else:
            angle, hand = 18, pygame.Vector2(430, 252)
        image = pygame.transform.rotate(source, angle)
        grip = (pygame.Vector2(anchor)-pygame.Vector2(source.get_size())/2).rotate(-angle)
        point = hand-pygame.Vector2(camera)-pygame.Vector2(image.get_size())/2-grip
        canvas.blit(image, (round(point.x), round(point.y)))

    def _draw_mill_world(self, canvas, camera):
        quest = self.game.mill_quest
        if self.game.world is not quest.upstream:return
        folder = ROOT/'assets/story/mill/encounter'
        if 'tree' not in self._world_art and (folder/'scene.json').exists():
            record = json.loads((folder/'scene.json').read_text())
            path = folder/record['image']
            self._world_art['tree'] = (pygame.image.load(str(path)).convert_alpha(), record['position'])
        if 'tree' in self._world_art:
            image, point = self._world_art['tree']
            canvas.blit(image, (round(point[0]-camera[0]), round(point[1]-camera[1])))
        if not quest.encounter_pending:return
        if 'tusker' not in self._world_art:
            path = ROOT/'assets/combat/ridgeback_tusker/animation.json'
            if not path.exists():return
            record = json.loads(path.read_text())
            frames = [(pygame.image.load(str(path.parent/frame['file'])).convert_alpha(), frame['duration_ms'])
                      for frame in record['animations']['idle']['frames']]
            self._world_art['tusker'] = frames, record['anchor']
        frames, anchor = self._world_art['tusker']
        time = self.world_seconds*1000 % sum(duration for _, duration in frames)
        image = frames[-1][0]
        for candidate, duration in frames:
            if time < duration:image = candidate;break
            time -= duration
        point = pygame.Vector2(quest.points.get('combat_position', (360, 312)))-camera
        shadow = pygame.Rect(0, 0, 64, 12);shadow.center = (round(point.x), round(point.y))
        pygame.draw.ellipse(canvas, '#304a35', shadow)
        canvas.blit(image, (round(point.x-anchor[0]), round(point.y-anchor[1])))
