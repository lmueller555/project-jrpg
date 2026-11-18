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
from mira_rig_state import MiraRigState
from quests import MILL_QUEST
from post_battle import battle_reward_definition, valid_pending_snapshot
from spoils_scene import SpoilsScene
from ui_style import GOLD


ROOT = Path(__file__).resolve().parent
ENCOUNTER_PATH = ROOT/'assets/combat/encounter.json'


class CombatEncounters:
    """Story bosses, cave formations and the optional Bat share battle ownership."""

    def __init__(self, game):
        self.game = game
        self.definition = json.loads(ENCOUNTER_PATH.read_text(encoding='utf-8'))
        self.position = pygame.Vector2(self.definition['position'])
        self.radius = self.definition['interaction_radius']
        self.scene = None
        self.receipt_id = None
        self._defeat_elapsed = 0.
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
        self._rig_entry = None
        self._rig_stats = None
        self._party_active = None
        self.entry = None
        self._cave_ticket = None
        self._boss_ticket = None
        self._cave_checkpointed = False

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
        if self._boss_ticket is not None:return tuple(self._boss_ticket['position'])
        if self.active and self.kind == 'mill':return tuple(self.game.mill_quest.upstream.data['spawn'])
        return tuple(self.game.player.position)

    @staticmethod
    def valid_pending_snapshot(record, data=None):return valid_pending_snapshot(record, data)

    def snapshot(self):return deepcopy(self._pending)

    @property
    def transitioning(self):
        return bool(self.transition is not None and self.transition.active)

    def _begin_battle_music(self):
        self._defeat_elapsed = 0.
        music = getattr(self.game, 'music', None)
        if music is not None:music.begin_battle()

    def _end_battle_music(self):
        music = getattr(self.game, 'music', None)
        if music is not None:
            music.set_ducked(False)
            music.end_battle()

    def reset(self):
        self.stop_audio()
        self._end_battle_music()
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
        self._rig_entry = None
        self._rig_stats = None
        self._party_active = None
        self.entry = None
        self._cave_ticket = None
        self._boss_ticket = None
        self._cave_checkpointed = False

    def stop_audio(self):
        """Stop disposable intro/reward effects without changing durable facts."""
        if self.spoils is not None:self.spoils.stop_audio()
        if self.entry is not None and hasattr(self.entry, 'stop_audio'):
            self.entry.stop_audio()
        if self.scene is not None:
            for name in ('action_audio', 'channel_audio'):
                audio = getattr(self.scene, name, None)
                if audio is not None:audio.stop()

    def _party_options(self):
        party = getattr(self.game, 'party', None)
        if party is None:return {}
        return {'party_members': party.battle_members(),
                'guest_abilities': {identifier: self.game.character_abilities.known_abilities(identifier)
                                    for identifier in party.active_ids if identifier != 'caelan'}}

    def _rig_snapshot(self):
        owner = getattr(self.game, 'mira_rig', None)
        return owner.to_dict() if owner is not None else MiraRigState().to_dict()

    def _rig_allocation(self):
        return self._rig_snapshot()['allocation']

    def _restore_rig(self, record):
        owner = getattr(self.game, 'mira_rig', None)
        return owner.restore(record) if owner is not None else record == MiraRigState().to_dict()

    def _capture_party_entry(self):
        self._rig_entry = self._rig_snapshot()
        party = getattr(self.game, 'party', None)
        self._party_active = tuple(party.active_ids) if party is not None else None
        self._party_entry = self._party_resources() if party is not None else None
        self._rig_stats = ({key: {stat: party.characters[key].value(stat) for stat in ('hp', 'spr')}
                            for key in self._party_active} if party is not None else {})

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
        elementals = getattr(game, 'elemental_bosses', None)
        if elementals is not None:elementals.draw_world(frame, camera)
        self.draw_world(frame, camera)
        game.opening.draw_world(frame, camera)
        for visit in game.household_visits:visit.draw_world(frame, camera)
        return frame

    def _begin_transition(self, frame):
        self.transition = BattleTransition(
            frame, reduced_motion=getattr(self.game.audio, 'reduced_motion', False))
        self._entry_keys.clear()
        self._begin_battle_music()

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
                            owned_gems=self.game.character_abilities.owned_gems(),
                            rig_allocation=self._rig_allocation(),
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
                            owned_gems=game.character_abilities.owned_gems(),
                            rig_allocation=self._rig_allocation(),
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
        lesson = getattr(game, 'cave_lesson', None)
        if lesson is not None and lesson.is_intro(ticket) and lesson.ready_reason():return False
        if lesson is not None and lesson.is_intro(ticket):
            # The confluence lesson is specifically the Blue focus. Selecting
            # another installed gem before arrival cannot strand its loading.
            if not game.character_abilities.set_active_gem('water'):return False
        self.kind = 'cave'
        self._cave_ticket = deepcopy(ticket)
        self.receipt_id = ticket['receipt']
        self._settled = False
        self._capture_party_entry()
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.
        game.social.clear_pointer();game._mouse_held = False
        frame = self._capture_world()
        focus = game.player.position-pygame.Vector2(game.camera.position())
        location = game.world.location(game.player.position) or game.world.data['name']
        self.entry = CaveBattleEntry(frame, focus, location,
                                    reduced_motion=game.audio.reduced_motion)
        self._entry_keys.clear()
        self._begin_battle_music()
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
            owned_gems=game.character_abilities.owned_gems(),
            rig_allocation=self._rig_allocation(),
            rng=random.Random(ticket['combat_seed']), initial_atb=True,
            initial_atb_seed=ticket['combat_seed'],
            aqua_edge_tutorial=(getattr(game, 'cave_lesson', None) is not None
                and game.cave_lesson.is_intro(ticket)),
            **self._party_options())
        model.encounter_rewards = self._available_rewards(model.encounter_rewards)
        scene = BattleScene(game, model, battlefield=ticket['battlefield'],
                            tutorial=model.aqua_edge_guided)
        old = self.entry
        self.scene = scene
        self._begin_transition(old.world_frame)
        # The cave entry already closed the world view and displayed loading.
        # Reveal the prepared battlefield without another approach curtain.
        self.transition.elapsed = self.transition.close_seconds+self.transition.hold_seconds
        scene.paused, scene.focused = old.paused, old.focused
        scene._held = old._held
        if hasattr(old, 'stop_audio'):old.stop_audio()
        self.entry = None

    def start_boss(self, ticket, *, restoring=False):
        """Checkpoint an acknowledged one-time story fight before its intro.

        The boss controller owns the durable ticket. Its saved formation,
        resources and seed are the battle entry checkpoint, independent of the
        cave's random encounter countdown.
        """
        return self._start_authored_boss(ticket, 'cave_boss', restoring=restoring)

    def start_elemental_boss(self, ticket, *, restoring=False):
        """Start either independently owned elemental teaching encounter."""
        return self._start_authored_boss(ticket, 'elemental_boss', restoring=restoring)

    def _boss_controller(self):
        return (self.game.elemental_bosses if self.kind == 'elemental_boss'
                else self.game.sanctuary_boss)

    def _start_authored_boss(self, ticket, kind, *, restoring=False):
        if kind == 'elemental_boss':
            from elemental_bosses import SCENE_ID, valid_ticket
        else:
            from sanctuary_boss import SCENE_ID, valid_ticket
        game = self.game
        controller = getattr(game, 'elemental_bosses' if kind == 'elemental_boss' else 'sanctuary_boss', None)
        if (self.active or game.world.data.get('id') != SCENE_ID
                or not valid_ticket(ticket) or controller is None
                or controller.pending != ticket
                or not game.world.can_stand(ticket['position'])
                or list(game.party.active_ids) != ticket['party_active']
                or game.party.battle_reason()):return False
        if kind == 'elemental_boss':
            if (controller.to_dict()['bosses'][ticket['enemy_id']]['defeated']
                    or game.cave_lesson.needs_intro or game.sanctuary_boss.pending is not None):return False
        elif (controller.defeated
              or getattr(getattr(game, 'elemental_bosses', None), 'pending', None) is not None):return False
        current = {identifier: {'hp': game.party.characters[identifier].current_hp,
                                'mp': game.party.characters[identifier].current_mp}
                   for identifier in ticket['party_active']}
        if current != ticket['party_resources']:return False
        if getattr(game.cave_random_encounters, 'pending', None) is not None:return False
        self.kind = kind
        self._boss_ticket = deepcopy(ticket)
        self.receipt_id = ticket['receipt']
        self._settled = False
        self._capture_party_entry()
        game.player.position.update(ticket['position'])
        game.player.facing = ticket['facing']
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.
        game.social.clear_pointer();game._mouse_held = False
        frame = self._capture_world()
        focus = game.player.position-pygame.Vector2(game.camera.position())
        self.entry = controller.make_entry(frame, focus, restoring=restoring)
        self._entry_keys.clear()
        self._begin_battle_music()
        self._cave_checkpointed = self._checkpoint()
        if not self._cave_checkpointed:
            self.entry.set_error('Progress could not be saved. Retry to enter battle.')
        return True

    def _boss_model(self):
        game, ticket = self.game, self._boss_ticket
        return BattleModel.from_bestiary_group(
            game.attributes, [{'enemy_id': ticket['enemy_id'], 'level': ticket['level']}],
            learned_abilities=game.character_abilities.known_abilities(),
            weapon_equipped=game.character_abilities.has_weapon(),
            active_gem=game.character_abilities.active_gem(),
            owned_gems=game.character_abilities.owned_gems(),
            rig_allocation=self._rig_allocation(),
            rng=random.Random(ticket['combat_seed']), initial_atb=True,
            initial_atb_seed=ticket['combat_seed'],
            elemental_tutorial=self.kind == 'elemental_boss', **self._party_options())

    def _load_boss_battle(self):
        game, ticket = self.game, self._boss_ticket
        model = self._boss_model()
        model.encounter_rewards = self._available_rewards(model.encounter_rewards)
        scene = BattleScene(game, model, battlefield=ticket['battlefield'])
        controller = self._boss_controller()
        before = controller.to_dict()
        if not controller.entry_loaded():
            raise ValueError('The boss introduction could not be acknowledged')
        if controller.to_dict() != before and not self._checkpoint():
            controller.restore(before)
            self.entry.set_error('Progress could not be saved. Retry to enter battle.')
            return
        old = self.entry
        self.scene = scene
        self._begin_transition(old.world_frame)
        self.transition.elapsed = self.transition.close_seconds+self.transition.hold_seconds
        scene.paused, scene.focused = old.paused, old.focused
        scene._held = old._held
        if hasattr(old, 'stop_audio'):old.stop_audio()
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
            try:
                if self.kind in ('cave_boss', 'elemental_boss'):self._load_boss_battle()
                else:self._load_cave_battle()
            except (OSError, ValueError, pygame.error):
                self.scene = None;self.transition = None
                entry.set_error('The battle could not be prepared. Please retry.')

    def _finish_cave_counter(self):
        owner = getattr(self.game, 'cave_random_encounters', None)
        if owner is None or self._cave_ticket is None:return None
        before = owner.to_dict()
        if not owner.finish(self.receipt_id):return None
        return before

    def _available_rewards(self, reward, spent=None):
        spent = spent or {}
        drops = {key: min(quantity, MAX_QUANTITY-self.game.inventory.quantity(key)+spent.get(key, 0))
                 for key, quantity in reward['drops'].items()
                 if self.game.inventory.quantity(key)-spent.get(key, 0) < MAX_QUANTITY}
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
        if (self.model.phase == 'defeat' and not getattr(self.game,'_is_gallery_preview',False)):
            if not self.scene.paused and self.scene.focused:self._defeat_elapsed += seconds
            if self._defeat_elapsed >= 1.5:
                self.game.show_game_over()
                return
        if self.model.ended:self._end_battle_music()
        if self.model.phase != 'defeat' and not self._checkpoint_spellblade_discovery():return
        if self.model.phase == 'victory':
            self._begin_victory()
            return
        if self.scene.dismissed:self._settle()

    def _checkpoint_spellblade_discovery(self):
        """Commit a discovery and the cast's resources together, retrying errors."""
        if self.model is None:return True
        game, owner = self.game, self.game.character_abilities
        aether = (self.kind == 'mill' and self.model.aether_edge_discovered
                  and owner.starter_skills_pending('caelan'))
        aqua = (self.kind == 'cave' and self.model.aqua_edge_discovered
                and 'aqua_edge' not in owner.known_abilities())
        if not (aether or aqua):return True
        before = (owner.to_dict(), game.party.to_dict() if hasattr(game, 'party') else None,
                  game.attributes.to_dict(), set(game.social.flags))
        learned = (owner.learn_first_weapon_skills('caelan') if aether
                   else owner.learn_ability('caelan', 'aqua_edge'))
        if not learned:return False
        resources = {'hp': self.model.player.hp, 'mp': self.model.player.mp}
        party_resources = self._model_resources(self.model) if self._party_active else None
        if not self._apply_resources(resources, party_resources):
            owner.restore(before[0])
            raise RuntimeError('Discovered skill produced invalid battle resources')
        game.social.flags.add('CH01_MQ02_AETHER_EDGE_DISCOVERED' if aether else
                              'CH01_MQ03_AQUA_EDGE_DISCOVERED')
        if self._checkpoint():
            self.scene.result_error = ''
            return True
        owner.restore(before[0]);game.social.flags = before[3]
        if before[1] is not None:game.party.restore(before[1])
        else:game.attributes.restore(before[2])
        self.scene.result_error = 'The learned technique could not be saved. Retrying…'
        return False

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
        if self.model.ended:self._end_battle_music()
        if self.model.phase != 'defeat' and not self._checkpoint_spellblade_discovery():return True
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
        if not self._checkpoint_spellblade_discovery():return False
        game, model = self.game, self.model
        hp, mp = model.player.hp, model.player.mp
        incapacitated = hp == 0
        cave_battle = self.kind in ('cave', 'cave_boss', 'elemental_boss')
        ticket = self._boss_ticket if self.kind in ('cave_boss', 'elemental_boss') else self._cave_ticket
        if incapacitated and not cave_battle:hp = max(1, game.attributes.value('hp')//4)
        position = (ticket['position'] if cave_battle else
                    self._mill_origin if self.kind == 'mill' and self._mill_origin is not None
                    else game.player.position)
        rewards = (model.encounter_rewards if cave_battle
                   else model.enemy_definition['rewards'])
        self._pending = {
            'version': 1, 'kind': self.kind, 'receipt': self.receipt_id, 'stage': 'pending',
            'rewards': self._available_rewards(rewards),
            'before': {'hp': game.attributes.current_hp, 'mp': game.attributes.current_mp},
            'resources': {'hp': hp, 'mp': mp}, 'scene': game.world.data['id'],
            'position': list(position), 'facing': game.player.facing,
            'incapacitated': incapacitated}
        if cave_battle:self._pending['encounter'] = deepcopy(ticket)
        if self._party_active is not None:
            resources = self._model_resources(model)
            resources['caelan'] = {'hp': hp, 'mp': mp}
            self._pending.update(party_before=self._party_resources(),
                                 party_resources=resources, party_active=list(self._party_active))
            offered = battle_reward_definition(self.kind, ticket)
            from enemy_loot import encounter_drops
            offered['drops'] = encounter_drops(self.kind, ticket, self.receipt_id, offered['drops'])
            costs = dict(getattr(model, 'item_spent', {}))
            self._pending['rewards'] = self._available_rewards({'drops': offered['drops']}, costs)
            end_hp = {'caelan' if member.identifier == 'player' else member.identifier: member.hp
                      for member in model.party}
            self._pending.update(version=4,
                                 rig_before=deepcopy(self._rig_entry or self._rig_snapshot()),
                                 rig_after={'version': 1, 'allocation': dict(model.rig_allocation)},
                                 rig_stats=deepcopy(self._rig_stats),
                                 rig_skill_uses=dict(model.rig_skill_uses),
                                 rig_healing={'caelan' if key == 'player' else key: value
                                              for key, value in model.rig_healing.items()},
                                 offered_drops=offered['drops'],
                                 item_costs=costs,
                                 item_before={key: game.inventory.quantity(key) for key in costs},
                                 progression=game.character_progression.preview(
                                     offered['xp'], list(self._party_active), end_hp))
        if not valid_pending_snapshot(self._pending):
            self._pending = None
            raise RuntimeError('A completed battle produced an invalid victory record')
        self.post_phase = 'banner'
        self._post_elapsed = 0.0
        self.scene.dismissed = False
        self.scene._tutorial_queue.clear()
        self._entry_keys.clear()
        self._victory_checkpointed = self._checkpoint()
        self._end_battle_music()
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
        plan = record.get('progression')
        if plan is not None and not game.character_progression.matches_plan(plan):
            return self._post_error('Character progress could not be collected. Try again.')
        before = (game.battle_rewards.to_dict(), game.inventory.to_dict(), game.quests.to_dict(),
                  quest.to_dict(), set(game.social.flags),
                  game.party.to_dict() if hasattr(game, 'party') else None,
                  game.character_progression.to_dict() if plan is not None else None,
                  game.attributes.to_dict(), self._rig_snapshot())
        boss_controller = self._boss_controller() if self.kind in ('cave_boss', 'elemental_boss') else None
        boss_before = boss_controller.to_dict() if boss_controller is not None else None
        abilities_before = game.character_abilities.to_dict() if self.kind == 'elemental_boss' else None
        lesson = getattr(game, 'cave_lesson', None)
        lesson_before = (lesson.to_dict() if self.kind == 'cave' and lesson is not None
                         and lesson.is_intro(self._cave_ticket) else None)

        def rollback(message):
            game.battle_rewards.restore(before[0]);game.inventory.restore(before[1])
            game.quests.restore(before[2]);quest.restore(before[3]);game.social.flags = before[4]
            if before[5] is not None:game.party.restore(before[5])
            else:game.attributes.restore(before[7])
            if before[6] is not None:game.character_progression.restore(before[6])
            self._restore_rig(before[8])
            if boss_before is not None:boss_controller.restore(boss_before)
            if abilities_before is not None:game.character_abilities.restore(abilities_before)
            if lesson_before is not None:lesson.restore(lesson_before)
            return self._post_error(message)

        reward = record['rewards']
        if game.battle_rewards.has_receipt(record['receipt']):
            return self._post_error('The victory receipt is inconsistent. Try again.')
        if record.get('item_costs') and not game.inventory.consume_bundle(record['item_costs']):
            return rollback('Used items could not be settled. Try again.')
        granted = game.battle_rewards.award_battle_rewards(record['receipt'], reward['drops'])
        if not granted:return rollback('Rewards could not be collected. Try again.')
        if plan is not None and not game.character_progression.apply(plan):
            return rollback('Character progress could not be collected. Try again.')
        if self.kind == 'mill' and not quest.battle_won():
            return rollback('The encounter could not be completed. Try again.')
        if not self._apply_resources(resources, party_resources):
            return rollback('Battle resources could not be collected. Try again.')
        if 'rig_after' in record and not self._restore_rig(record['rig_after']):
            return rollback('Rig configuration could not be collected. Try again.')
        if self.kind == 'elemental_boss':
            from elemental_bosses import definition
            unlock = definition(record['encounter']['enemy_id'])
            owner = game.character_abilities
            if unlock['gem'] not in owner.owned_gems() and not owner.grant_gem(unlock['gem']):
                return rollback('The focus gem could not be installed. Try again.')
            if (unlock['skill'] not in owner.known_abilities()
                    and not owner.learn_ability('caelan', unlock['skill'])):
                return rollback('The elemental technique could not be learned. Try again.')
            if not owner.set_active_gem(unlock['gem']):
                return rollback('The focus gem could not be selected. Try again.')
        if boss_controller is not None and not boss_controller.mark_defeated(record['receipt']):
            return rollback('The boss encounter could not be completed. Try again.')
        if lesson_before is not None and not lesson.mark_cleared(self._cave_ticket):
            return rollback('The cave lesson could not be completed. Try again.')
        record['stage'] = 'awarded'
        if not self._checkpoint():
            if boss_before is not None or lesson_before is not None or record['version'] >= 4:
                record['stage'] = 'pending'
                return rollback('Progress could not be saved. Try again.')
            return self._post_error('Progress could not be saved. Try again.')
        self.scene.result_error = ''
        self.spoils.set_awarded(reward)
        return True

    def _make_spoils(self):
        record = self._pending
        received = record['rewards']['drops']
        offered = record.get('offered_drops', received)
        loot = {'offered': dict(offered), 'received': dict(received),
                'lost': {item: amount-received.get(item, 0) for item, amount in offered.items()
                         if amount > received.get(item, 0)}}
        return SpoilsScene(self.game, record['rewards'], party=self.model.party, model=self.model,
                           progression=record.get('progression'), background=self.scene, loot=loot)

    def _update_post_battle(self, seconds):
        if self.paused or not self.focused:return
        if self.post_phase == 'banner':
            self.scene.update(seconds)
            self._post_elapsed += seconds
            if self._post_elapsed >= 1.6:
                self.spoils = self._make_spoils()
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
        if not self.spoils.presentation_complete:
            self.spoils.dismissed = False
            return False
        game, record = self.game, self._pending
        game.player.position.update(record['position'])
        game.player.facing = record['facing']
        self._pending = None
        self._exiting_spoils = True
        cave_before = self._finish_cave_counter() if self.kind == 'cave' else None
        boss_controller = self._boss_controller() if self.kind in ('cave_boss', 'elemental_boss') else None
        boss_before = boss_controller.to_dict() if boss_controller is not None else None
        if self.kind == 'cave' and cave_before is None:
            self._pending = record;self._exiting_spoils = False
            self.spoils.dismissed = False
            return self._post_error('The cave encounter could not be completed. Try again.')
        if boss_controller is not None and not boss_controller.finish(record['receipt']):
            self._pending = record;self._exiting_spoils = False
            self.spoils.dismissed = False
            return self._post_error('The boss encounter could not be completed. Try again.')
        if not self._checkpoint():
            if cave_before is not None:game.cave_random_encounters.restore(cave_before)
            if boss_before is not None:boss_controller.restore(boss_before)
            self._pending = record
            self._exiting_spoils = False
            self.spoils.dismissed = False
            return self._post_error('Progress could not be saved. Try again.')
        kind = self.kind
        self._settled = True
        self.stop_audio()
        self.scene = None;self.spoils = None;self.transition = None
        self.post_phase = None;self._exiting_spoils = False
        self._entry_keys.clear();self.kind = None;self._mill_intro_started = False
        if kind == 'bat':self.cooldown = self.definition['respawn_seconds']
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.0;game._mouse_held = False
        game.social.clear_pointer();game.camera.reset()
        self._end_battle_music()
        if kind == 'cave':self._cave_ticket = None
        if kind in ('cave_boss', 'elemental_boss'):self._boss_ticket = None
        if kind == 'mill':game.mill_quest.battle_returned('victory', recovered=record['incapacitated'])
        if hasattr(game,'saves'):game.saves.request_battle(record['receipt'])
        return True

    def restore_pending(self, record):
        if record is None:return True
        if not valid_pending_snapshot(record):return False
        game = self.game
        validation = {'player': {'scene': game.world.data['id'], 'position': record['position'],
                                  'facing': record['facing']},
                      'battle_rewards': game.battle_rewards.to_dict(),
                      'inventory': game.inventory.to_dict(),
                      'mira_rig': self._rig_snapshot(),
                      'character_attributes': game.attributes.to_dict(),
                      'quests': game.quests.to_dict(), 'mill_quest': game.mill_quest.to_dict()}
        if hasattr(game, 'party'):validation['party'] = game.party.to_dict()
        if 'progression' in record:validation['character_levels'] = game.character_progression.to_dict()
        if record['kind'] == 'cave':
            validation['cave_random_encounters'] = game.cave_random_encounters.to_dict()
        elif record['kind'] == 'cave_boss':
            validation['sanctuary_boss'] = game.sanctuary_boss.to_dict()
        elif record['kind'] == 'elemental_boss':
            validation['elemental_bosses'] = game.elemental_bosses.to_dict()
            validation['character_abilities'] = game.character_abilities.to_dict()
            validation['inventory'] = game.inventory.to_dict()
        if not valid_pending_snapshot(record, validation):return False
        self._pending = deepcopy(record)
        # begin_journey has already chosen a clear standing spot if an NPC now
        # occupies the old return position; keep that safe landing on exit.
        if record['kind'] in ('cave', 'cave_boss', 'elemental_boss'):
            if not game.world.can_stand(record['position']):
                self._pending = None
                return False
            game.player.position.update(record['position'])
        self._pending['position'] = list(game.player.position)
        self._pending['facing'] = game.player.facing
        self.kind, self.receipt_id = record['kind'], record['receipt']
        if self.kind == 'cave':
            self._cave_ticket = deepcopy(record['encounter'])
        elif self.kind in ('cave_boss', 'elemental_boss'):
            self._boss_ticket = deepcopy(record['encounter'])
        if self.kind == 'bat':self._bat_contact_armed = False
        self._mill_origin = tuple(self._pending['position']) if self.kind == 'mill' else None
        options = self._party_options() if 'party_active' in record else {
            'guest_abilities': ({'mira': game.character_abilities.known_abilities('mira')}
                                if self.kind == 'mill' else {}),
            'guest_id': 'mira' if self.kind == 'mill' else None}
        common = dict(weapon_equipped=game.character_abilities.has_weapon(),
                      active_gem=game.character_abilities.active_gem(),
                      owned_gems=game.character_abilities.owned_gems(),
                      rig_allocation=self._rig_allocation(), **options)
        if self.kind == 'cave':
            model = BattleModel.from_bestiary_group(
                game.attributes, self._cave_ticket['members'],
                learned_abilities=game.character_abilities.known_abilities(),
                rng=random.Random(self._cave_ticket['combat_seed']), initial_atb=True,
                **common)
        elif self.kind in ('cave_boss', 'elemental_boss'):
            model = self._boss_model()
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
        model.player.hp = (record['resources']['hp'] if self.kind in ('cave', 'cave_boss', 'elemental_boss') else
                           0 if record['incapacitated'] else record['resources']['hp'])
        model.player.mp = record['resources']['mp']
        for enemy in getattr(model, 'enemies', (model.enemy,)):
            enemy.hp = 0;enemy.atb = 0.
        model._result('victory')
        model.drain_events()
        model.enemy_definition['rewards'] = deepcopy(record['rewards'])
        if self.kind in ('cave', 'cave_boss', 'elemental_boss'):model.encounter_rewards = deepcopy(record['rewards'])
        battlefield = (self._boss_ticket['battlefield'] if self.kind in ('cave_boss', 'elemental_boss') else
                       self._cave_ticket['battlefield'] if self.kind == 'cave' else
                       'millrace' if self.kind == 'mill' else 'eldenmere')
        self.scene = BattleScene(game, model, battlefield=battlefield)
        self.spoils = self._make_spoils()
        self.post_phase = 'spoils';self._post_elapsed = 0.;self.transition = None
        self._settled = False;self._victory_checkpointed = True;self._entry_keys.clear()
        # Continue reconstructs the current world/story score before Spoils.
        # There is no live battle stream to override or resume after a reload.
        self._award_spoils()
        return True

    def _settle(self):
        """Commit used supplies with a withdrawal; defeat restores entry supplies."""
        if not self.active or self.model is None or not self.model.ended or self._settled:return False
        if self.model.phase != 'fled':return self._settle_outcome()
        before = self.game.inventory.to_dict()
        rig_before = self._rig_snapshot()
        costs = dict(getattr(self.model, 'item_spent', {}))
        if costs and not self.game.inventory.consume_bundle(costs):
            self.scene.dismissed = False
            self.scene.result_error = 'Used items could not be settled. Try again.'
            return False
        if not self._restore_rig({'version': 1, 'allocation': dict(self.model.rig_allocation)}):
            self.game.inventory.restore(before)
            return False
        if not self._settle_outcome():
            self.game.inventory.restore(before)
            self._restore_rig(rig_before)
            return False
        if hasattr(self.game,'saves'):self.game.saves.request_battle(self.receipt_id+':fled:'+uuid4().hex)
        return True

    def _settle_outcome(self):
        if not self.active or not self.scene.model.ended or self._settled:return False
        if self.model.phase == 'defeat' and not getattr(self.game,'_is_gallery_preview',False):
            self.game.show_game_over()
            return True
        if self.model.phase == 'victory':
            if self._pending is None:self._begin_victory()
            return False
        if self.kind == 'cave':return self._settle_cave()
        if self.kind in ('cave_boss', 'elemental_boss'):return self._settle_boss()
        if self.kind == 'mill':return self._settle_mill()
        game, scene, model = self.game, self.scene, self.scene.model
        party_before = game.party.to_dict() if self._party_active else None
        attributes_before = game.attributes.to_dict()
        # Defeat is a safe withdrawal: every member retains the resources saved
        # before this optional fight, and receives no item drops.
        if model.phase != 'defeat':
            resources = {'hp': model.player.hp, 'mp': model.player.mp}
            party_resources = self._model_resources(model) if self._party_active else None
            if not self._apply_resources(resources, party_resources):
                scene.dismissed = False
                scene.result_error = 'Could not return from battle. Try again.'
                return False
        if not self._checkpoint():
            if party_before is not None:game.party.restore(party_before)
            else:game.attributes.restore(attributes_before)
            scene.dismissed = False
            scene.result_error = 'Progress could not be saved. Try again.'
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
        self._end_battle_music()
        return True

    def _settle_cave(self):
        """Withdraw once, retaining spent resources on flee and entry on defeat."""
        game, scene, model = self.game, self.scene, self.model
        party_before = game.party.to_dict()
        lesson = getattr(game, 'cave_lesson', None)
        intro = lesson is not None and lesson.is_intro(self._cave_ticket)
        lesson_before = lesson.to_dict() if intro else None
        if model.phase != 'defeat':
            resources = {'hp': model.player.hp, 'mp': model.player.mp}
            if not self._apply_resources(resources, self._model_resources(model)):
                scene.dismissed = False
                scene.result_error = 'Could not return from battle. Try again.'
                return False
        # An unfinished lesson retains its formation/seed while the player is
        # free to prepare, visit the bed and return to this exact encounter.
        ticket = self._cave_ticket
        if intro:
            counter_before = game.cave_random_encounters.to_dict()
            if not lesson.defer(ticket):
                game.party.restore(party_before)
                scene.dismissed = False
                return False
            self._cave_ticket = None
        else:counter_before = self._finish_cave_counter()
        if counter_before is None:
            game.party.restore(party_before)
            scene.dismissed = False
            scene.result_error = 'The cave encounter could not be completed. Try again.'
            return False
        if not self._checkpoint():
            game.party.restore(party_before)
            game.cave_random_encounters.restore(counter_before)
            if lesson_before is not None:lesson.restore(lesson_before)
            self._cave_ticket = ticket
            scene.dismissed = False
            scene.result_error = 'Progress could not be saved. Try again.'
            return False
        self._settled = True
        self.scene = None;self.entry = None;self.transition = None
        self._entry_keys.clear();self.kind = None
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.;game._mouse_held = False
        game.social.clear_pointer();game.camera.reset()
        self._end_battle_music()
        self._cave_ticket = None
        return True

    def _settle_boss(self):
        """Return an unbeaten boss to its captured entry resources and choices."""
        game, scene = self.game, self.scene
        ticket = deepcopy(self._boss_ticket)
        controller = self._boss_controller()
        if self.kind == 'elemental_boss' and self.model.phase == 'fled':
            return self._flee_elemental_boss(ticket, controller)
        if ticket is None or not self._apply_resources(
                ticket['party_resources']['caelan'], ticket['party_resources']):
            scene.dismissed = False
            scene.result_error = 'Could not return from battle. Try again.'
            return False
        game.player.position.update(ticket['position'])
        game.player.facing = ticket['facing']
        self._settled = True
        self.scene = None;self.entry = None;self.transition = None
        self._entry_keys.clear();self.kind = None;self._boss_ticket = None
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.;game._mouse_held = False
        game.social.clear_pointer();game.camera.reset()
        self._end_battle_music()
        # The ticket remains durable until the controller commits Retry or
        # Return. Quitting before that choice can safely restart the encounter.
        controller.battle_defeated(ticket)
        return True

    def _flee_elemental_boss(self, ticket, controller):
        """Withdraw to this chamber's foyer, retaining spent party resources."""
        game, scene = self.game, self.scene
        if ticket is None:return False
        before = (game.party.to_dict(), controller.to_dict(),
                  tuple(game.player.position), game.player.facing)
        resources = self._model_resources(self.model)
        if not self._apply_resources(resources['caelan'], resources):
            scene.dismissed = False
            scene.result_error = 'Could not return from battle. Try again.'
            return False
        if not controller.finish_flee(ticket):
            game.party.restore(before[0]);controller.restore(before[1])
            scene.dismissed = False
            scene.result_error = 'The chamber could not be left. Try again.'
            return False
        self._boss_ticket = None
        if not self._checkpoint():
            game.party.restore(before[0]);controller.restore(before[1])
            game.player.position.update(before[2]);game.player.facing = before[3]
            self._boss_ticket = ticket
            game.party_travel.reset();game.camera.reset()
            scene.dismissed = False
            scene.result_error = 'Progress could not be saved. Try again.'
            return False
        self._settled = True
        self.scene = None;self.entry = None;self.transition = None
        self._entry_keys.clear();self.kind = None
        game.player.moving = game.player.running = False
        game.player.walk_ms = 0.;game._mouse_held = False
        game.social.clear_pointer();game.party_travel.reset();game.camera.reset()
        self._end_battle_music()
        return True

    def _settle_mill(self):
        game, scene = self.game, self.scene
        model, quest = scene.model, game.mill_quest
        party_before = game.party.to_dict() if self._party_active else None
        attributes_before = game.attributes.to_dict()
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
        if not self._checkpoint():
            if party_before is not None:game.party.restore(party_before)
            else:game.attributes.restore(attributes_before)
            scene.dismissed = False
            scene.result_error = 'Progress could not be saved. Try again.'
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
        self._end_battle_music()
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
