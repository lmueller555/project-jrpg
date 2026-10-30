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
from battle_transition import BattleTransition
from inventory import MAX_QUANTITY
from quests import MILL_QUEST
from post_battle import valid_pending_snapshot
from spoils_scene import SpoilsScene
from ui_style import GOLD


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
        self.transition = None
        self._entry_keys = set()
        self.spoils = None
        self.post_phase = None
        self._post_elapsed = 0.0
        self._pending = None
        self._victory_checkpointed = False
        self._exiting_spoils = False

    @property
    def active(self):return self.scene is not None

    @property
    def model(self):return self.scene.model if self.scene is not None else None

    @property
    def view(self):return self.spoils if self.post_phase == 'spoils' else self.scene

    @property
    def paused(self):return bool(self.view and self.view.paused)

    @property
    def focused(self):return self.view.focused if self.view is not None else True

    @property
    def tutorial_active(self):return bool(not self.post_phase and self.scene and self.scene.tutorial_active)

    @property
    def checkpoint_position(self):
        if self._pending is not None:return tuple(self._pending['position'])
        if self._exiting_spoils:return tuple(self.game.player.position)
        if self.active and self.kind == 'mill':return tuple(self.game.mill_quest.upstream.data['spawn'])
        return tuple(self.game.player.position)

    @staticmethod
    def valid_pending_snapshot(record, data=None):return valid_pending_snapshot(record, data)

    def snapshot(self):return deepcopy(self._pending)

    @property
    def transitioning(self):
        return bool(self.transition is not None and self.transition.active)

    def _music(self, track):
        music = getattr(self.game, 'music', None)
        if music is not None:music.play(track)

    def reset(self):
        self.scene = None
        self.receipt_id = None
        self.cooldown = self.world_seconds = 0.0
        self._settled = False
        self.kind = None
        self._mill_intro_started = False
        self._mill_origin = None
        self.transition = None
        self._entry_keys.clear()
        self.spoils = None
        self.post_phase = None
        self._post_elapsed = 0.0
        self._pending = None
        self._victory_checkpointed = False
        self._exiting_spoils = False
        self._music('eldenmere')

    def _capture_world(self):
        """Render the actual approach, including story props, without a frame flip."""
        game = self.game
        frame = pygame.Surface(game.canvas.get_size())
        camera = game.camera.position()
        game.world.draw(frame, camera, game.player, game.elapsed_ms, include_ui=False)
        self.draw_world(frame, camera)
        game.opening.draw_world(frame, camera)
        for visit in game.household_visits:visit.draw_world(frame, camera)
        return frame

    def _begin_transition(self, frame):
        self.transition = BattleTransition(
            frame, reduced_motion=getattr(self.game.audio, 'reduced_motion', False))
        self._entry_keys.clear()
        self._music('battle')

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
        frame = self._capture_world()
        self.scene = BattleScene(self.game, model)
        self.kind = 'bat'
        self.receipt_id = 'battle:'+uuid4().hex
        self._settled = False
        self.game.player.moving = self.game.player.running = False
        self.game.player.walk_ms = 0.0
        self.game.social.clear_pointer()
        self.game._mouse_held = False
        self._begin_transition(frame)
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
        frame = self._capture_world()
        self.scene = BattleScene(game, model, battlefield='millrace', tutorial=True)
        self.kind = 'mill'
        self.receipt_id = 'mq02:ridgeback_tusker'
        self._settled = False
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game.social.clear_pointer()
        game._mouse_held = False
        self._begin_transition(frame)
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
        if self.post_phase:
            self._update_post_battle(seconds)
            return
        if self.transitioning:
            self.transition.update(seconds, paused=self.scene.paused or not self.scene.focused)
            if not self.transition.active:self.transition = None
            return
        self.scene.update(seconds)
        if self.model.phase == 'victory':
            self._begin_victory()
            return
        if self.scene.dismissed:self._settle()

    def handle_event(self, event):
        if not self.active:return False
        if event.type == pygame.KEYUP:
            self._entry_keys.discard(event.key)
        elif event.type == pygame.KEYDOWN and event.key in self._entry_keys:
            return True
        if self.post_phase:
            return self._handle_post_event(event)
        if self.transitioning:
            if event.type == pygame.KEYDOWN:self._entry_keys.add(event.key)
            if event.type == pygame.WINDOWFOCUSLOST:self._entry_keys.clear()
            if (event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED,
                               pygame.MOUSEBUTTONUP)
                    or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)
                    or (self.scene.paused and event.type == pygame.MOUSEBUTTONDOWN)):
                self.scene.handle_event(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Holding a click through the reveal cannot spend a turn.
                self.scene._held = True
            return True
        self.scene.handle_event(event)
        if self.model.phase == 'victory':
            self._begin_victory()
            return True
        if self.scene.dismissed:self._settle()
        return True

    def draw(self, canvas, ui_surface):
        if not self.active:return
        if self.post_phase:
            self._draw_post_battle(canvas, ui_surface)
            return
        self.scene.draw(canvas, ui_surface)
        if self.transitioning:
            self.transition.draw(ui_surface)
            if self.scene.paused:
                # Keep the ordinary pause controls visible over a frozen curtain.
                painter = self.game.ui.painter(ui_surface)
                painter.veil(150)
                painter.panel((124, 111, 232, 100))
                painter.text('Battle paused', (240, 126), color=GOLD,
                             anchor='midtop', bold=True)
                painter.button(self.scene.resume_rect, 'Resume', disabled=not self.scene.focused)
                painter.clip()

    def _checkpoint(self):
        store = getattr(self.game, 'save_store', None)
        if store is not None and not store.enabled:return True
        return bool(self.game.save_progress())

    def _begin_victory(self):
        if self._pending is not None or self.model is None or self.model.phase != 'victory':return False
        game, model = self.game, self.model
        hp, mp = model.player.hp, model.player.mp
        incapacitated = hp == 0
        if incapacitated:hp = max(1, game.attributes.value('hp')//4)
        position = self._mill_origin if self.kind == 'mill' and self._mill_origin is not None else game.player.position
        self._pending = {
            'version': 1, 'kind': self.kind, 'receipt': self.receipt_id, 'stage': 'pending',
            'rewards': self._available_rewards(model.enemy_definition['rewards']),
            'before': {'hp': game.attributes.current_hp, 'mp': game.attributes.current_mp},
            'resources': {'hp': hp, 'mp': mp}, 'scene': game.world.data['id'],
            'position': list(position), 'facing': game.player.facing,
            'incapacitated': incapacitated}
        if not valid_pending_snapshot(self._pending):
            self._pending = None
            raise RuntimeError('A completed battle produced an invalid victory record')
        self.post_phase = 'banner'
        self._post_elapsed = 0.0
        self.scene.dismissed = False
        self.scene._tutorial_queue.clear()
        self._entry_keys.clear()
        self._victory_checkpointed = self._checkpoint()
        music = getattr(game, 'music', None)
        if music is not None:
            music.set_ducked(False)
            music.play('victory', fade_ms=0)
        return True

    def _post_error(self, message):
        self.scene.result_error = message
        self.spoils.set_error(message)
        return False

    def _award_spoils(self):
        if self._pending is None or self.spoils is None:return False
        game, record = self.game, self._pending
        if record['stage'] == 'awarded':
            # A failed save retries only the complete checkpoint, never a grant.
            if not self._checkpoint():return self._post_error('Progress could not be saved. Try again.')
            self.scene.result_error = ''
            self.spoils.set_awarded(record['rewards'])
            return True
        if not self._victory_checkpointed:
            self._victory_checkpointed = self._checkpoint()
            if not self._victory_checkpointed:
                return self._post_error('The victory could not be saved. Try again.')
        resources = record['resources']
        proposed = deepcopy(game.attributes)
        if not proposed.set_current(hp=resources['hp'], mp=resources['mp']):
            return self._post_error('Battle resources could not be collected. Try again.')
        quest = game.mill_quest
        if self.kind == 'mill':
            proposed_quests = deepcopy(game.quests)
            if not quest.encounter_pending or not proposed_quests.complete_objective(MILL_QUEST, 'secure_trail'):
                return self._post_error('The encounter could not be completed. Try again.')
        before = (game.lattice.to_dict(), game.inventory.to_dict(), game.quests.to_dict(),
                  quest.to_dict(), set(game.social.flags))
        reward = record['rewards']
        if game.lattice.has_receipt(record['receipt']):
            return self._post_error('The victory receipt is inconsistent. Try again.')
        awards = {'caelan': reward['rp']} if reward['rp'] else {}
        if awards or reward['drops']:
            granted = game.lattice_progression.award_battle_rewards(record['receipt'], awards, reward['drops'])
        else:
            # Empty capped spoils still need a receipt. The lattice's canonical
            # reward operation supports an empty award; progression requires a
            # nonempty bundle because it normally also owns inventory changes.
            proposed_lattice = deepcopy(game.lattice)
            granted = (proposed_lattice.award_rewards(record['receipt'], {})
                       and game.lattice.restore(proposed_lattice.to_dict()))
        if not granted:return self._post_error('Rewards could not be collected. Try again.')
        if self.kind == 'mill' and not quest.battle_won():
            game.lattice.restore(before[0]);game.inventory.restore(before[1])
            game.quests.restore(before[2]);quest.restore(before[3]);game.social.flags = before[4]
            return self._post_error('The encounter could not be completed. Try again.')
        if not game.attributes.set_current(hp=resources['hp'], mp=resources['mp']):
            game.lattice.restore(before[0]);game.inventory.restore(before[1])
            game.quests.restore(before[2]);quest.restore(before[3]);game.social.flags = before[4]
            return self._post_error('Battle resources could not be collected. Try again.')
        record['stage'] = 'awarded'
        if not self._checkpoint():return self._post_error('Progress could not be saved. Try again.')
        self.scene.result_error = ''
        self.spoils.set_awarded(reward)
        return True

    def _update_post_battle(self, seconds):
        if self.paused or not self.focused:return
        if self.post_phase == 'banner':
            self.scene.update(seconds)
            self._post_elapsed += seconds
            if self._post_elapsed >= 1.6:
                self.spoils = SpoilsScene(self.game, self._pending['rewards'],
                                          party=self.model.party, model=self.model)
                self.post_phase = 'spoils_transition'
                self._post_elapsed = 0.0
            return
        if self.post_phase == 'spoils_transition':
            self._post_elapsed += seconds
            duration = .22 if self.game.audio.reduced_motion else .36
            if self._post_elapsed >= duration:
                self.spoils.paused, self.spoils.focused = self.scene.paused, self.scene.focused
                self.spoils._held = self.scene._held
                self.post_phase = 'spoils'
                self._post_elapsed = 0.0
                self._award_spoils()
            return
        self.spoils.update(seconds)
        if self.spoils.retry_requested:
            self.spoils.retry_requested = False
            self._award_spoils()
        if self.spoils.dismissed:self._finish_spoils()

    def _handle_post_event(self, event):
        if self.post_phase != 'spoils':
            if event.type == pygame.KEYDOWN:self._entry_keys.add(event.key)
            if event.type == pygame.WINDOWFOCUSLOST:self._entry_keys.clear()
            if (event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED, pygame.MOUSEBUTTONUP)
                    or event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                    or self.scene.paused and event.type == pygame.MOUSEBUTTONDOWN):
                self.scene.handle_event(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.scene._held = True
            return True
        self.spoils.handle_event(event)
        if self.spoils.retry_requested:
            self.spoils.retry_requested = False
            self._award_spoils()
        if self.spoils.dismissed:self._finish_spoils()
        return True

    def _draw_post_battle(self, canvas, ui_surface):
        if self.post_phase == 'spoils':
            self.spoils.draw(canvas, ui_surface)
            return
        if self.post_phase == 'banner':
            self.scene.draw(canvas, ui_surface)
            return
        duration = .22 if self.game.audio.reduced_motion else .36
        progress = min(1., self._post_elapsed/duration)
        if progress < .5:self.scene.draw(canvas, ui_surface)
        else:self.spoils.draw(canvas, ui_surface)
        opacity = round(255*(1-abs(2*progress-1)))
        self.game.ui.painter(ui_surface).veil(opacity)
        if self.scene.paused:
            painter = self.game.ui.painter(ui_surface)
            painter.veil(150)
            painter.panel((124, 111, 232, 100))
            painter.text('Battle paused', (240, 126), color=GOLD, anchor='midtop', bold=True)
            painter.button(self.scene.resume_rect, 'Resume', disabled=not self.scene.focused)
            painter.clip()

    def _finish_spoils(self):
        if self._pending is None or self._pending['stage'] != 'awarded' or not self.spoils.ready:return False
        game, record = self.game, self._pending
        game.player.position.update(record['position'])
        game.player.facing = record['facing']
        self._pending = None
        self._exiting_spoils = True
        if not self._checkpoint():
            self._pending = record
            self._exiting_spoils = False
            self.spoils.dismissed = False
            return self._post_error('Progress could not be saved. Try again.')
        kind = self.kind
        self._settled = True
        self.scene = None;self.spoils = None;self.transition = None
        self.post_phase = None;self._exiting_spoils = False
        self._entry_keys.clear();self.kind = None;self._mill_intro_started = False
        if kind == 'bat':self.cooldown = self.definition['respawn_seconds']
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0;game._mouse_held = False
        game.social.clear_pointer();game.camera.reset()
        self._music('eldenmere')
        if kind == 'mill':game.mill_quest.battle_returned('victory', recovered=record['incapacitated'])
        return True

    def restore_pending(self, record):
        if record is None:return True
        if not valid_pending_snapshot(record):return False
        game = self.game
        validation = {'player': {'scene': game.world.data['id'], 'position': record['position'],
                                  'facing': record['facing']},
                      'aether_lattice': game.lattice.to_dict(),
                      'character_attributes': game.attributes.to_dict(),
                      'quests': game.quests.to_dict(), 'mill_quest': game.mill_quest.to_dict()}
        if not valid_pending_snapshot(record, validation):return False
        self._pending = deepcopy(record)
        # begin_journey has already chosen a clear standing spot if an NPC now
        # occupies the old return position; keep that safe landing on exit.
        self._pending['position'] = list(game.player.position)
        self._pending['facing'] = game.player.facing
        self.kind, self.receipt_id = record['kind'], record['receipt']
        self._mill_origin = tuple(self._pending['position']) if self.kind == 'mill' else None
        model = BattleModel(game.attributes, game.lattice.learned_abilities(),
                            enemy_id='ridgeback_tusker' if self.kind == 'mill' else 'bat',
                            guest_id='mira' if self.kind == 'mill' else None)
        model.player.hp = 0 if record['incapacitated'] else record['resources']['hp']
        model.player.mp = record['resources']['mp']
        model.enemy.hp = 0;model.phase = 'victory'
        model.enemy_definition['rewards'] = deepcopy(record['rewards'])
        self.scene = BattleScene(game, model, battlefield='millrace' if self.kind == 'mill' else 'eldenmere')
        self.spoils = SpoilsScene(game, record['rewards'], party=model.party, model=model)
        self.post_phase = 'spoils';self._post_elapsed = 0.;self.transition = None
        self._settled = False;self._victory_checkpointed = True;self._entry_keys.clear()
        music = getattr(game, 'music', None)
        if music is not None:music.stop()
        self._award_spoils()
        return True

    def _settle(self):
        if not self.active or not self.scene.model.ended or self._settled:return False
        if self.model.phase == 'victory':
            if self._pending is None:self._begin_victory()
            return False
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
        if model.phase != 'defeat':
            # Rewards only affect RP/inventory; the already validated resource
            # capacities cannot change between the validation and this assignment.
            if not game.attributes.set_current(hp=model.player.hp, mp=model.player.mp):
                raise RuntimeError('Validated battle resources could not be applied')
        self._settled = True
        self.scene = None
        self.transition = None
        self._entry_keys.clear()
        self.kind = None
        self.cooldown = self.definition['respawn_seconds']
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game._mouse_held = False
        game.social.clear_pointer()
        game.save_progress()
        self._music('eldenmere')
        return True

    def _settle_mill(self):
        game, scene = self.game, self.scene
        model, quest = scene.model, game.mill_quest
        outcome = model.phase
        if outcome == 'victory':
            if self._pending is None:self._begin_victory()
            return False
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
        if not game.attributes.set_current(hp=hp, mp=mp):
            raise RuntimeError('Validated battle resources could not be applied')
        game.player.position.update(quest.upstream.data['spawn'])
        self._settled = True
        self.scene = None
        self.transition = None
        self._entry_keys.clear()
        self.kind = None
        self._mill_intro_started = False
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0
        game._mouse_held = False
        game.social.clear_pointer()
        game.camera.reset()
        # Defeat/withdrawal checkpoints retain the existing safe retry policy.
        game.save_progress()
        self._music('eldenmere')
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
