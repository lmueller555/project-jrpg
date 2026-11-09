"""Story and optional encounters, with atomic return to the saved journey."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import random
from uuid import uuid4

import pygame

from battle_model import BattleModel
from battle_scene import BattleScene
from battle_transition import BattleTransition
from cave_battle_entry import CaveBattleEntry
from inventory import MAX_QUANTITY
from quests import MILL_QUEST
from post_battle import valid_pending_snapshot
from spoils_scene import SpoilsScene
from ui_style import GOLD


ROOT = Path(__file__).resolve().parent
ENCOUNTER_PATH = ROOT/'assets/combat/encounter.json'


class CombatEncounters:
    """MQ02's story fight and the repeatable test Bat share battle ownership."""

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
        self._bat_contact_armed = True
        self._party_entry = None
        self._party_active = None
        self.entry = None
        self._cave_ticket = None
        self._cave_checkpointed = False
        self._cave_return_track = None

    @property
    def active(self):return self.scene is not None or self.entry is not None

    @property
    def model(self):return self.scene.model if self.scene is not None else None

    @property
    def view(self):return self.entry or (self.spoils if self.post_phase == 'spoils' else self.scene)

    @property
    def entry_phase(self):return self.entry.phase if self.entry is not None else None

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
        if self._cave_ticket is not None:return tuple(self._cave_ticket['position'])
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
        self._bat_contact_armed = True
        self._party_entry = None
        self._party_active = None
        self.entry = None
        self._cave_ticket = None
        self._cave_checkpointed = False
        self._cave_return_track = None
        self._music('eldenmere')

    def _party_options(self):
        party = getattr(self.game, 'party', None)
        if party is None:return {}
        return {'party_members': party.battle_members(),
                'guest_abilities': {identifier: self.game.character_abilities.known_abilities(identifier)
                                    for identifier in party.active_ids if identifier != 'caelan'}}

    def _capture_party_entry(self):
        party = getattr(self.game, 'party', None)
        self._party_active = tuple(party.active_ids) if party is not None else None
        self._party_entry = self._party_resources() if party is not None else None

    def _party_resources(self):
        party = self.game.party
        return {identifier: {'hp': party.characters[identifier].current_hp,
                             'mp': party.characters[identifier].current_mp}
                for identifier in self._party_active}

    @staticmethod
    def _model_resources(model):
        return {'caelan' if member.identifier == 'player' else member.identifier:
                {'hp': member.hp, 'mp': member.mp} for member in model.party}

    def _apply_resources(self, resources, party_resources=None):
        """Validate every participant before changing any persistent resource."""
        game = self.game
        updates = {'caelan': resources} if party_resources is None else party_resources
        party = getattr(game, 'party', None)
        characters = party.characters if party is not None else {'caelan': game.attributes}
        for identifier, values in updates.items():
            if identifier not in characters:return False
            proposed = deepcopy(characters[identifier])
            if not proposed.set_current(hp=values['hp'], mp=values['mp']):return False
        for identifier, values in updates.items():
            characters[identifier].set_current(hp=values['hp'], mp=values['mp'])
        return True

    def _capture_world(self):
        """Render the actual approach, including story props, without a frame flip."""
        game = self.game
        frame = pygame.Surface(game.canvas.get_size())
        camera = game.camera.position()
        travel = getattr(game, 'party_travel', None)
        options = ({'party_actors': travel.actors()}
                   if travel is not None and not getattr(game.world, 'is_overworld', False) else {})
        game.world.draw(frame, camera, game.player, game.elapsed_ms, include_ui=False, **options)
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
        # The optional test encounter is available independently of story progress.
        return True

    def _world_available(self):
        game = self.game
        party = getattr(game, 'party', None)
        can_fight = not party.battle_reason() if party is not None else game.attributes.current_hp > 0
        return (not self.active and not game.on_title
                and not game.pause.is_open and not game.inventory_ui.is_open
                and not getattr(getattr(game, 'party_ui', None), 'is_open', False)
                and not game.quest_ui.journal_open and not game.map_open
                and not game.social.locked and not game.opening.locks_player
                and not game.household_action and not game.transfer_cooldown
                and not game.opening_fade and can_fight)

    def _exploration_available(self):
        return (self.bat_unlocked and self._world_available()
                and self.game.world.data['id'] == self.definition['scene'])

    def nearby(self):
        return (self._exploration_available() and self.cooldown <= 0
                and self.game.player.position.distance_squared_to(self.position) <= self.radius**2)

    def interaction_hint(self):
        if not self.nearby():return ''
        return ('Approach the Bat to test combat' if self._bat_contact_armed else
                'Move away, then approach the Bat to test again')

    def _inside_bat_radius(self):
        return (self.game.world.data['id'] == self.definition['scene'] and
                self.game.player.position.distance_squared_to(self.position) <= self.radius**2)

    def prepare_world_resume(self):
        """Loading onto the Bat's spot is not a new approach to the encounter."""
        self._bat_contact_armed = not self._inside_bat_radius()

    def interact(self, rng=None):
        if not self.nearby():return False
        party = getattr(self.game, 'party', None)
        if party is not None and party.battle_reason():return False
        self._bat_contact_armed = False
        model = BattleModel(self.game.attributes,
                            self.game.character_abilities.known_abilities(),
                            weapon_equipped=self.game.character_abilities.has_weapon(),
                            active_gem=self.game.character_abilities.active_gem(),
                            bot_loadouts=self.game.bot_loadouts.battle_loadouts(),
                            rng=random.Random() if rng is None else rng,
                            enemy_id=self.definition['enemy'], initial_atb=True,
                            **self._party_options())
        self._capture_party_entry()
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
        owner=game.character_abilities
        if owner.starter_skills_pending('caelan') and quest.uses_gearblade:
            # The authored first lesson draws the gift he is carrying, even if
            # a loadout edit put it away between the workshop and river path.
            if not owner.equip_weapon('caelan','caelan_gearblade'):return False
        training = owner.has_weapon() and owner.starter_skills_pending('caelan')
        if training and (game.attributes.current_hp < min(80,game.attributes.value('hp'))
                         or game.attributes.current_mp < 4):
            # Optional test battles can exhaust a new journey before its first
            # authored lesson. A brief preparation pause prevents an unwinnable
            # first Guard or an MP-gated mandatory discovery.
            def prepared():
                game.attributes.set_current(hp=max(game.attributes.current_hp,min(80,game.attributes.value('hp'))),
                                            mp=max(game.attributes.current_mp,4))
                game.save_progress()
                self.start_mill(rng)
            return quest._speak('tutorial_preparation', prepared)
        party = getattr(game, 'party', None)
        if party is not None and party.battle_reason():return False
        options = self._party_options() if party is not None else {
            'guest_id': 'mira',
            'guest_abilities': {'mira': game.character_abilities.known_abilities('mira')}}
        model = BattleModel(game.attributes, game.character_abilities.known_abilities(),
                            weapon_equipped=game.character_abilities.has_weapon(),
                            active_gem=game.character_abilities.active_gem(),
                            bot_loadouts=game.bot_loadouts.battle_loadouts(),
                            rng=random.Random() if rng is None else rng,
                            enemy_id='ridgeback_tusker', spellblade_tutorial=training,
                            initial_atb=not training, **options)
        self._capture_party_entry()
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

    def start_cave(self, ticket, *, restoring=False):
        """Checkpoint one selected formation before its approach and load.

        The random encounter owner retains the ticket until settlement. Continue
        can therefore replay the same formation and opening ATB rolls without
        saving animation clocks or settling incomplete battle resources.
        """
        if self.active or self.game.world.data.get('id') != 'sanctuary_cave':return False
        from cave_random_encounters import valid_ticket
        if not valid_ticket(ticket):return False
        game = self.game
        if getattr(game, 'party', None) is None or game.party.battle_reason():return False
        controller = getattr(game, 'cave_random_encounters', None)
        if controller is None or controller.pending != ticket:return False
        self.kind = 'cave'
        self._cave_ticket = deepcopy(ticket)
        self.receipt_id = ticket['receipt']
        self._settled = False
        self._capture_party_entry()
        self._cave_return_track = getattr(getattr(game, 'music', None), 'desired_track', None)
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.
        game.social.clear_pointer();game._mouse_held = False
        frame = self._capture_world()
        focus = game.player.position-pygame.Vector2(game.camera.position())
        location = game.world.location(game.player.position) or game.world.data['name']
        self.entry = CaveBattleEntry(frame, focus, location,
                                    reduced_motion=game.audio.reduced_motion)
        self._entry_keys.clear()
        self._cave_checkpointed = self._checkpoint()
        if not self._cave_checkpointed:
            self.entry.set_error('Progress could not be saved. Retry to enter battle.')
        return True

    def _load_cave_battle(self):
        game, ticket = self.game, self._cave_ticket
        model = BattleModel.from_bestiary_group(
            game.attributes, ticket['members'],
            learned_abilities=game.character_abilities.known_abilities(),
            weapon_equipped=game.character_abilities.has_weapon(),
            active_gem=game.character_abilities.active_gem(),
            bot_loadouts=game.bot_loadouts.battle_loadouts(),
            rng=random.Random(ticket['combat_seed']), initial_atb=True,
            **self._party_options())
        model.encounter_rewards = self._available_rewards(model.encounter_rewards)
        scene = BattleScene(game, model, battlefield=ticket['battlefield'])
        old = self.entry
        self.scene = scene
        self._begin_transition(old.world_frame)
        # The cave entry already closed the world view and displayed loading.
        # Reveal the prepared battlefield without another approach curtain.
        self.transition.elapsed = self.transition.close_seconds+self.transition.hold_seconds
        scene.paused, scene.focused = old.paused, old.focused
        scene._held = old._held
        self.entry = None

    def _update_cave_entry(self, seconds):
        entry = self.entry
        if entry.retry_requested:
            entry.retry_requested = False
            if not self._cave_checkpointed:
                self._cave_checkpointed = self._checkpoint()
                if self._cave_checkpointed:entry.clear_error()
            else:entry.clear_error()
        entry.update(seconds)
        if entry.ready_to_load:
            try:self._load_cave_battle()
            except (OSError, ValueError, pygame.error):
                self.scene = None;self.transition = None
                entry.set_error('The battle could not be prepared. Please retry.')

    def _restore_cave_music(self):
        emergency = getattr(getattr(self.game, 'regent_quest', None), 'emergency', None)
        if emergency is not None:emergency.sync_music(restoring=True)
        # The Sanctuary emergency owns Kindled Courage while its arrival is
        # pending. A free exploration visit retains its own previous track.
        quest = getattr(self.game, 'regent_quest', None)
        if quest is None or getattr(quest, 'stage', None) not in (
                'sanctuary_travel', 'sanctuary_arrival_pending'):
            self._music(self._cave_return_track or 'eldenmere')

    def _cave_courage_owned(self):
        return (self.kind == 'cave' and
                getattr(getattr(self.game, 'regent_quest', None), 'stage', None)
                in ('sanctuary_travel', 'sanctuary_arrival_pending'))

    def _finish_cave_counter(self):
        owner = getattr(self.game, 'cave_random_encounters', None)
        if owner is None or self._cave_ticket is None:return None
        before = owner.to_dict()
        if not owner.finish(self.receipt_id):return None
        return before

    def _available_rewards(self, reward):
        drops = {key: min(quantity, MAX_QUANTITY-self.game.inventory.quantity(key))
                 for key, quantity in reward['drops'].items()
                 if self.game.inventory.quantity(key) < MAX_QUANTITY}
        return {'drops': drops}

    def tick_world(self, seconds):
        if self.active:return
        self.world_seconds += seconds
        self.cooldown = max(0.0, self.cooldown-seconds)
        if not self._inside_bat_radius():self._bat_contact_armed = True
        if self._bat_contact_armed and self.nearby():
            self.interact()
            return
        quest = self.game.mill_quest
        approach = self.game.world is quest.upstream and quest._at_encounter_approach()
        if not quest.encounter_pending or not approach:
            self._mill_intro_started = False
        elif quest.encounter_ready and not self._mill_intro_started:
            self._mill_intro_started = bool(quest.begin_encounter(self.start_mill))

    def update(self, seconds):
        if not self.active:return
        if self.entry is not None:
            self._update_cave_entry(seconds)
            return
        if self.post_phase:
            self._update_post_battle(seconds)
            return
        if self.transitioning:
            self.transition.update(seconds, paused=self.scene.paused or not self.scene.focused)
            if not self.transition.active:self.transition = None
            return
        self.scene.update(seconds)
        self._checkpoint_spellblade_discovery()
        if self.model.phase == 'victory':
            self._begin_victory()
            return
        if self.scene.dismissed:self._settle()

    def _checkpoint_spellblade_discovery(self):
        if (self.kind != 'mill' or self.model is None
                or not getattr(self.model,'aether_edge_discovered',False)):
            return
        owner=self.game.character_abilities
        if not owner.starter_skills_pending('caelan'):return
        if owner.learn_first_weapon_skills('caelan'):
            # Persist the earned action's resources with the learned technique;
            # quitting here must not refund its MP while keeping the discovery.
            resources = {'hp': self.model.player.hp, 'mp': self.model.player.mp}
            party_resources = self._model_resources(self.model) if self._party_active else None
            if not self._apply_resources(resources, party_resources):
                raise RuntimeError('Discovered skill produced invalid battle resources')
            self.game.social.flags.add('CH01_MQ02_AETHER_EDGE_DISCOVERED')
            # No battle clock is saved. A retry retains the skill actually
            # discovered, and still owes the encounter's victory/reward receipt.
            self.game.save_progress()

    def handle_event(self, event):
        if not self.active:return False
        if event.type == pygame.KEYUP:
            self._entry_keys.discard(event.key)
        elif event.type == pygame.KEYDOWN and event.key in self._entry_keys:
            return True
        if self.entry is not None:
            if event.type == pygame.KEYDOWN and event.key != pygame.K_ESCAPE:
                self._entry_keys.add(event.key)
            return self.entry.handle_event(self.game, event)
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
        if self.entry is not None:
            self.entry.draw(self.game, canvas, ui_surface)
            return
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
        if incapacitated and self.kind != 'cave':hp = max(1, game.attributes.value('hp')//4)
        position = (self._cave_ticket['position'] if self.kind == 'cave' else
                    self._mill_origin if self.kind == 'mill' and self._mill_origin is not None
                    else game.player.position)
        rewards = (model.encounter_rewards if self.kind == 'cave'
                   else model.enemy_definition['rewards'])
        self._pending = {
            'version': 1, 'kind': self.kind, 'receipt': self.receipt_id, 'stage': 'pending',
            'rewards': self._available_rewards(rewards),
            'before': {'hp': game.attributes.current_hp, 'mp': game.attributes.current_mp},
            'resources': {'hp': hp, 'mp': mp}, 'scene': game.world.data['id'],
            'position': list(position), 'facing': game.player.facing,
            'incapacitated': incapacitated}
        if self.kind == 'cave':self._pending['encounter'] = deepcopy(self._cave_ticket)
        if self._party_active is not None:
            resources = self._model_resources(model)
            resources['caelan'] = {'hp': hp, 'mp': mp}
            self._pending.update(party_before=self._party_resources(),
                                 party_resources=resources, party_active=list(self._party_active))
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
            music.play('battle' if self._cave_courage_owned() else 'victory', fade_ms=0)
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
        party_resources = record.get('party_resources')
        if party_resources is not None:
            party = getattr(game, 'party', None)
            if party is None or tuple(record['party_active']) != party.active_ids:
                return self._post_error('The battle party could not be restored. Try again.')
            for identifier, values in party_resources.items():
                proposed = deepcopy(party.characters[identifier])
                if not proposed.set_current(hp=values['hp'], mp=values['mp']):
                    return self._post_error('Battle resources could not be collected. Try again.')
        quest = game.mill_quest
        if self.kind == 'mill':
            proposed_quests = deepcopy(game.quests)
            if not quest.encounter_pending or not proposed_quests.complete_objective(MILL_QUEST, 'secure_trail'):
                return self._post_error('The encounter could not be completed. Try again.')
        before = (game.battle_rewards.to_dict(), game.inventory.to_dict(), game.quests.to_dict(),
                  quest.to_dict(), set(game.social.flags),
                  game.party.to_dict() if hasattr(game, 'party') else None)
        reward = record['rewards']
        if game.battle_rewards.has_receipt(record['receipt']):
            return self._post_error('The victory receipt is inconsistent. Try again.')
        granted = game.battle_rewards.award_battle_rewards(record['receipt'], reward['drops'])
        if not granted:return self._post_error('Rewards could not be collected. Try again.')
        if self.kind == 'mill' and not quest.battle_won():
            game.battle_rewards.restore(before[0]);game.inventory.restore(before[1])
            game.quests.restore(before[2]);quest.restore(before[3]);game.social.flags = before[4]
            if before[5] is not None:game.party.restore(before[5])
            return self._post_error('The encounter could not be completed. Try again.')
        if not self._apply_resources(resources, party_resources):
            game.battle_rewards.restore(before[0]);game.inventory.restore(before[1])
            game.quests.restore(before[2]);quest.restore(before[3]);game.social.flags = before[4]
            if before[5] is not None:game.party.restore(before[5])
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
        cave_before = self._finish_cave_counter() if self.kind == 'cave' else None
        if self.kind == 'cave' and cave_before is None:
            self._pending = record;self._exiting_spoils = False
            self.spoils.dismissed = False
            return self._post_error('The cave encounter could not be completed. Try again.')
        if not self._checkpoint():
            if cave_before is not None:game.cave_random_encounters.restore(cave_before)
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
        if kind == 'cave':
            self._restore_cave_music()
            self._cave_ticket = None
        else:self._music('eldenmere')
        if kind == 'mill':game.mill_quest.battle_returned('victory', recovered=record['incapacitated'])
        return True

    def restore_pending(self, record):
        if record is None:return True
        if not valid_pending_snapshot(record):return False
        game = self.game
        validation = {'player': {'scene': game.world.data['id'], 'position': record['position'],
                                  'facing': record['facing']},
                      'battle_rewards': game.battle_rewards.to_dict(),
                      'character_attributes': game.attributes.to_dict(),
                      'quests': game.quests.to_dict(), 'mill_quest': game.mill_quest.to_dict()}
        if hasattr(game, 'party'):validation['party'] = game.party.to_dict()
        if record['kind'] == 'cave':
            validation['cave_random_encounters'] = game.cave_random_encounters.to_dict()
        if not valid_pending_snapshot(record, validation):return False
        self._pending = deepcopy(record)
        # begin_journey has already chosen a clear standing spot if an NPC now
        # occupies the old return position; keep that safe landing on exit.
        if record['kind'] == 'cave':
            if not game.world.can_stand(record['position']):
                self._pending = None
                return False
            game.player.position.update(record['position'])
        self._pending['position'] = list(game.player.position)
        self._pending['facing'] = game.player.facing
        self.kind, self.receipt_id = record['kind'], record['receipt']
        if self.kind == 'cave':
            self._cave_ticket = deepcopy(record['encounter'])
            self._cave_return_track = getattr(getattr(game, 'music', None), 'desired_track', None)
        if self.kind == 'bat':self._bat_contact_armed = False
        self._mill_origin = tuple(self._pending['position']) if self.kind == 'mill' else None
        options = self._party_options() if 'party_active' in record else {
            'guest_abilities': ({'mira': game.character_abilities.known_abilities('mira')}
                                if self.kind == 'mill' else {}),
            'guest_id': 'mira' if self.kind == 'mill' else None}
        common = dict(weapon_equipped=game.character_abilities.has_weapon(),
                      active_gem=game.character_abilities.active_gem(),
                      bot_loadouts=game.bot_loadouts.battle_loadouts(), **options)
        if self.kind == 'cave':
            model = BattleModel.from_bestiary_group(
                game.attributes, self._cave_ticket['members'],
                learned_abilities=game.character_abilities.known_abilities(),
                rng=random.Random(self._cave_ticket['combat_seed']), initial_atb=True,
                **common)
        else:
            model = BattleModel(game.attributes, game.character_abilities.known_abilities(),
                                enemy_id='ridgeback_tusker' if self.kind == 'mill' else 'bat',
                                **common)
        self._capture_party_entry()
        if 'party_resources' in record:
            for member in model.party:
                identifier = 'caelan' if member.identifier == 'player' else member.identifier
                member.hp = record['party_resources'][identifier]['hp']
                member.mp = record['party_resources'][identifier]['mp']
        model.player.hp = (record['resources']['hp'] if self.kind == 'cave' else
                           0 if record['incapacitated'] else record['resources']['hp'])
        model.player.mp = record['resources']['mp']
        for enemy in getattr(model, 'enemies', (model.enemy,)):
            enemy.hp = 0;enemy.atb = 0.
        model._result('victory')
        model.drain_events()
        model.enemy_definition['rewards'] = deepcopy(record['rewards'])
        if self.kind == 'cave':model.encounter_rewards = deepcopy(record['rewards'])
        battlefield = (self._cave_ticket['battlefield'] if self.kind == 'cave' else
                       'millrace' if self.kind == 'mill' else 'eldenmere')
        self.scene = BattleScene(game, model, battlefield=battlefield)
        self.spoils = SpoilsScene(game, record['rewards'], party=model.party, model=model)
        self.post_phase = 'spoils';self._post_elapsed = 0.;self.transition = None
        self._settled = False;self._victory_checkpointed = True;self._entry_keys.clear()
        music = getattr(game, 'music', None)
        if music is not None:
            if self._cave_courage_owned():music.play('battle', fade_ms=0)
            else:music.stop()
        self._award_spoils()
        return True

    def _settle(self):
        if not self.active or not self.scene.model.ended or self._settled:return False
        if self.model.phase == 'victory':
            if self._pending is None:self._begin_victory()
            return False
        if self.kind == 'cave':return self._settle_cave()
        if self.kind == 'mill':return self._settle_mill()
        game, scene, model = self.game, self.scene, self.scene.model
        # Defeat is a safe withdrawal: every member retains the resources saved
        # before this optional fight, and receives no item drops.
        if model.phase != 'defeat':
            resources = {'hp': model.player.hp, 'mp': model.player.mp}
            party_resources = self._model_resources(model) if self._party_active else None
            if not self._apply_resources(resources, party_resources):
                scene.dismissed = False
                scene.result_error = 'Could not return from battle. Try again.'
                return False
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

    def _settle_cave(self):
        """Withdraw once, retaining spent resources on flee and entry on defeat."""
        game, scene, model = self.game, self.scene, self.model
        party_before = game.party.to_dict()
        if model.phase != 'defeat':
            resources = {'hp': model.player.hp, 'mp': model.player.mp}
            if not self._apply_resources(resources, self._model_resources(model)):
                scene.dismissed = False
                scene.result_error = 'Could not return from battle. Try again.'
                return False
        counter_before = self._finish_cave_counter()
        if counter_before is None:
            game.party.restore(party_before)
            scene.dismissed = False
            scene.result_error = 'The cave encounter could not be completed. Try again.'
            return False
        if not self._checkpoint():
            game.party.restore(party_before)
            game.cave_random_encounters.restore(counter_before)
            scene.dismissed = False
            scene.result_error = 'Progress could not be saved. Try again.'
            return False
        self._settled = True
        self.scene = None;self.entry = None;self.transition = None
        self._entry_keys.clear();self.kind = None
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.;game._mouse_held = False
        game.social.clear_pointer();game.camera.reset()
        self._restore_cave_music()
        self._cave_ticket = None
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
        party_resources = self._model_resources(model) if self._party_active else None
        if party_resources is not None:
            if outcome == 'defeat':
                # The authored first fight must remain retryable even when a
                # companion entered injured. Restore HP and preserve entry MP.
                party_resources = {identifier: {
                    'hp': game.party.characters[identifier].value('hp'),
                    'mp': self._party_entry[identifier]['mp']}
                    for identifier in self._party_active}
            party_resources['caelan'] = {'hp': hp, 'mp': mp}
        if not self._apply_resources({'hp': hp, 'mp': mp}, party_resources):
            scene.dismissed = False
            scene.result_error = 'Could not return from battle. Try again.'
            return False
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
        self._draw_mira_weapon(canvas, camera)
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

    def _draw_mira_weapon(self, canvas, camera):
        quest = self.game.mill_quest
        carried = (quest.mira_armed and quest._mira_world is self.game.world
                   and not quest.action and not quest._mira_pose)
        stowed = (getattr(quest, 'mira_weapon_stowed', False)
                  and self.game.world is quest.upstream)
        if not carried and not stowed:return
        if 'bolt_launcher' not in self._world_art:
            folder = ROOT/'assets/combat/mira'
            if not (folder/'world_bolt_launcher.json').exists():return
            record = json.loads((folder/'world_bolt_launcher.json').read_text())
            image = pygame.image.load(str(folder/'world_bolt_launcher.png')).convert_alpha()
            self._world_art['bolt_launcher'] = image, record['hand_anchor']
        source, anchor = self._world_art['bolt_launcher']
        if carried:
            facing = quest.mira.facing
            if facing == 'right':
                source = pygame.transform.flip(source, True, False)
                anchor = (source.get_width()-1-anchor[0], anchor[1])
            angle = {'front': 65, 'back': -65, 'left': -10, 'right': 10}.get(facing, 0)
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
