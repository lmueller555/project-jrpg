"""Deterministic wait-ATB battle rules, independent of rendering and saves.

Gauge fill is 0.12 + 0.004 * Speed per charging second. Every gauge pauses at
the exact party-ready boundary and throughout action animations or results.
Only this battle's copied resources change; the owning game settles outcomes.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
import json
import math
from pathlib import Path
import random

from character_attributes import ATTRIBUTE_IDS, ATTRIBUTE_CAPS
from character_abilities import starting_abilities
from battle_choreography import timing_override
from combat_damage import (NORMAL_DAMAGE_CAP, magical_damage, physical_damage,
                           roll_variance)
from gear_state import DEFAULT_GEM, GEM_NAMES, GEM_ORDER, REQUIRED_GEMS, valid_gem
from mira_rig_rules import (CHANNELS as RIG_CHANNELS, CAPACITY as RIG_CAPACITY,
                           DEFAULT_ALLOCATION, SKILLS as RIG_SKILLS,
                           valid_allocation, healing_amount, barrier_amount)


ROOT = Path(__file__).resolve().parent
ACTION_PATH = ROOT/'assets/combat/actions.json'
ENEMY_PATH = ROOT/'assets/combat/bestiary.json'
GUEST_PATH = ROOT/'assets/combat/guests.json'
RESULT_PHASES = frozenset(('victory', 'defeat', 'fled'))
PLAYER_ACTIONS = ('attack', 'guard', 'flee')
SUPPORTED_LEARNED_ACTIONS = ('aether_dart',)
ELEMENTAL_EDGE_ACTIONS = ('aqua_edge', 'flame_edge', 'ice_edge')
SUPPORTED_SKILL_ACTIONS = ('aether_edge', *ELEMENTAL_EDGE_ACTIONS, *RIG_SKILLS)
ELEMENTAL_EDGE_ATTEMPTS = ('aqua_edge',)
EPSILON = 1e-10
MAX_ENEMY_RESOURCE = 999999999
PARTY_IDENTIFIERS = frozenset(('player', 'mira', 'lucan', 'rhea', 'edran'))
MAX_PARTY_MEMBERS = 3
MAX_ENEMIES = 4


def _integer(value, minimum=0, maximum=MAX_ENEMY_RESOURCE):
    return type(value) is int and minimum <= value <= maximum


def _number(value, minimum=0, maximum=1000000):
    return (type(value) in (int, float) and math.isfinite(value)
            and minimum <= value <= maximum)


def load_actions(data=None):
    """Validate and copy the supported action catalog and optional element tags.

    Element tags apply the Bestiary response to elemental damage components.
    """
    if data is None:data = json.loads(ACTION_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'actions'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['actions'], dict) or not data['actions']):
        raise ValueError('Invalid battle action catalog')
    fields = {'name', 'kind', 'potency', 'mp_cost', 'duration', 'impact_at', 'animation', 'target'}
    for identifier, action in data['actions'].items():
        expected_fields = fields.copy()
        if isinstance(action, dict):
            expected_fields = (fields | {'weapon_hits'} if action.get('kind') == 'enchant' else
                               fields | {'magical_potency'} if action.get('kind') == 'spellblade' else fields.copy())
            if 'element' in action:expected_fields = expected_fields | {'element'}
            if 'power_requirements' in action:expected_fields |= {'power_requirements'}
            if 'barrier_percent' in action:expected_fields |= {'barrier_percent', 'barrier_turns'}
            if action.get('kind') == 'heal':expected_fields |= {'heal_percent', 'spirit_multiplier'}
        if (not isinstance(identifier, str) or not identifier
                or not isinstance(action, dict)
                or set(action) != expected_fields
                or any(not isinstance(action[key], str) or not action[key].strip()
                       for key in ('name', 'animation'))
                or action['kind'] not in ('physical', 'magical', 'guard', 'flee', 'prepare', 'recover', 'enchant', 'spellblade', 'failed_edge', 'barrier', 'heal')
                or action['target'] not in ('opponent', 'all_opponents', 'self', 'none', 'ally')
                or not _integer(action['mp_cost'], maximum=999999)
                or not _number(action['duration'], .001, 10)
                or not _number(action['impact_at'], 0, action['duration'])
                or not _number(action['potency'])):
            raise ValueError('Invalid battle action')
        if 'power_requirements' in action:
            requirements = action['power_requirements']
            if (identifier not in RIG_SKILLS or not isinstance(requirements, dict)
                    or set(requirements) != set(RIG_CHANNELS)
                    or any(not _integer(value, 0, RIG_CAPACITY) for value in requirements.values())
                    or sum(requirements.values()) > RIG_CAPACITY):
                raise ValueError('Invalid rig power requirements')
        if identifier in RIG_SKILLS:
            rule = RIG_SKILLS[identifier]
            if (action.get('power_requirements') != rule['requirements']
                    or action['kind'] != rule['kind'] or action['mp_cost'] != rule['mp_cost']
                    or action['potency'] != rule['potency']
                    or action.get('barrier_percent') != rule.get('barrier_percent')
                    or action.get('element') != rule.get('element')):
                raise ValueError('Rig action does not match its canonical rules')
        if 'barrier_percent' in action:
            if (identifier not in RIG_SKILLS or not _integer(action['barrier_percent'], 1, 100)
                    or action['barrier_turns'] != 2 or type(action['barrier_turns']) is not int):
                raise ValueError('Invalid rig barrier')
        if 'element' in action:
            from bestiary import ELEMENT_IDS
            if (action['kind'] not in ('physical', 'magical', 'spellblade')
                    or action['kind'] == 'spellblade' and (identifier not in ELEMENTAL_EDGE_ACTIONS
                        or action['element'] != REQUIRED_GEMS[identifier])
                    or not isinstance(action['element'], str)
                    or action['element'] not in ELEMENT_IDS):
                raise ValueError('Invalid battle action element')
        if action['kind'] in ('physical', 'magical', 'spellblade'):
            if (action['potency'] <= 0 or action['target'] not in ('opponent', 'all_opponents')
                    or action['kind'] == 'spellblade' and action['target'] != 'opponent'):
                raise ValueError('Invalid damaging action')
            if action['kind'] == 'spellblade' and not _number(action['magical_potency'], .001):
                raise ValueError('Invalid spellblade component')
        elif action['kind'] == 'enchant':
            if (action['potency'] <= 0 or action['target'] != 'self'
                    or action['animation'] != 'cast'
                    or not _integer(action['weapon_hits'], 1, 999)):
                raise ValueError('Invalid weapon enchantment')
        elif action['kind'] == 'barrier':
            if action['potency'] != 0 or action['target'] != 'self' or 'barrier_percent' not in action:
                raise ValueError('Invalid barrier action')
        elif action['kind'] == 'heal':
            if (identifier != 'repair_pulse' or action['potency'] != 0 or action['target'] != 'ally'
                    or type(action['heal_percent']) is not int or action['heal_percent'] != 15
                    or type(action['spirit_multiplier']) is not int or action['spirit_multiplier'] != 2):
                raise ValueError('Invalid restorative skill')
        elif (action['potency'] != 0 or action['mp_cost'] != 0
              or action['target'] != ('self' if action['kind'] in ('guard', 'prepare', 'recover', 'failed_edge') else 'none')):
            raise ValueError('Invalid utility action')
    if not set(PLAYER_ACTIONS+SUPPORTED_LEARNED_ACTIONS+SUPPORTED_SKILL_ACTIONS) <= set(data['actions']):
        raise ValueError('Missing player battle action')
    return deepcopy(data['actions'])


def load_enemies(actions, data=None):
    """Validate the Bestiary and compile fixed encounters plus MQ02 at level one.

    Level-derived definitions require ``BattleModel.from_bestiary`` so a caller
    cannot accidentally fight one at an unspecified level. MQ02's Tusker has
    an explicit level-one binding for its established story constructor.
    """
    from bestiary import FIXED_FIELDS, build_enemy, load_bestiary
    catalog = load_bestiary(data, actions=actions)
    enemies = {identifier: deepcopy(enemy)
            for identifier, enemy in catalog['enemies'].items()
            if set(enemy) == FIXED_FIELDS}
    # MQ02 is an explicitly level-one authored encounter. Retain its established
    # constructor API while compiling its stats from the canonical template.
    if 'ridgeback_tusker' in catalog['enemies'] and 'ridgeback_tusker' not in enemies:
        enemies['ridgeback_tusker'] = build_enemy('ridgeback_tusker', 1,
            data=catalog, actions=actions)['combat']
    return enemies


def load_guests(actions, data=None):
    """A guest owns a fixed combat profile, not the player's saved growth."""
    if data is None:data = json.loads(GUEST_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'guests'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['guests'], dict) or not data['guests']):
        raise ValueError('Invalid guest catalog')
    for identifier, guest in data['guests'].items():
        if (not isinstance(identifier, str) or not identifier
                or identifier in ('player', 'enemy') or not isinstance(guest, dict)
                or set(guest) != {'name', 'attributes', 'attack'}
                or not isinstance(guest['name'], str) or not guest['name'].strip()
                or not isinstance(guest['attributes'], dict)
                or set(guest['attributes']) != set(ATTRIBUTE_IDS)
                or any(not _integer(value, 1 if key == 'hp' else 0, ATTRIBUTE_CAPS[key])
                       for key, value in guest['attributes'].items())
                or not isinstance(guest['attack'], str) or guest['attack'] not in actions
                or actions[guest['attack']]['kind'] not in ('physical', 'magical')):
            raise ValueError('Invalid guest definition')
    return deepcopy(data['guests'])




def _party_snapshot(members, actions):
    """Copy a saved active lineup without refilling anyone's resources."""
    if (not isinstance(members, (tuple, list))
            or not 1 <= len(members) <= MAX_PARTY_MEMBERS):
        raise ValueError('A battle requires one to three party members')
    copied = []
    used = set()
    fields = {'identifier', 'name', 'attributes', 'hp', 'mp', 'attack'}
    for member in members:
        if (not isinstance(member, dict) or set(member) != fields
                or not isinstance(member['identifier'], str)
                or member['identifier'] not in PARTY_IDENTIFIERS
                or member['identifier'] in used
                or not isinstance(member['name'], str) or not member['name'].strip()
                or not isinstance(member['attributes'], dict)
                or set(member['attributes']) != set(ATTRIBUTE_IDS)
                or any(not _integer(value, 1 if key == 'hp' else 0, ATTRIBUTE_CAPS[key])
                       for key, value in member['attributes'].items())
                or not _integer(member['hp'], 0, member['attributes']['hp'])
                or not _integer(member['mp'], 0, member['attributes']['mp'])
                or member['attack'] not in ('attack', 'bolt_shot')
                or member['attack'] not in actions):
            raise ValueError('Invalid battle party member')
        used.add(member['identifier'])
        copied.append(deepcopy(member))
    if 'player' not in used:raise ValueError('The battle party requires Caelan')
    return copied


@dataclass
class Combatant:
    identifier: str
    name: str
    attributes: dict
    hp: int
    mp: int
    atb: float = 0.0
    guarded: bool = False
    aether_edge_hits: int = 0
    barrier: int = 0
    barrier_turns: int = 0

    def value(self, identifier):return self.attributes[identifier]

    @property
    def max_hp(self):return self.value('hp')

    @property
    def max_mp(self):return self.value('mp')




@dataclass
class BattleAction:
    actor: str
    action: str
    target: str | None
    name: str
    kind: str
    animation: str
    duration: float
    impact_at: float
    elapsed: float = 0.0
    damage: int = 0
    resolved: bool = False
    active_gem: str | None = None
    choreography: str | None = None
    weapon_equipped: bool = False
    targets: tuple[str, ...] = ()
    rig_allocation: dict | None = None
    barrier_granted: bool = False


@dataclass
class EnemyState:
    """Independent action selection and prepared spell state for one opponent."""
    behavior: dict | None = None
    style: str | None = None
    preparations: dict | None = None
    prepared_action: str | None = None
    target_index: int = 0
    action_index: int = 0
    telegraphed_target: str | None = None
    design: dict | None = None
    response_actions: int = 0
    vulnerable: bool = False


def _primary_enemy_state(field):
    """Keep the established single-opponent attributes as first-enemy aliases."""
    return property(lambda self: getattr(self._enemy_states['enemy'], field),
                    lambda self, value: setattr(self._enemy_states['enemy'], field, value))


class BattleModel:
    """Player-commanded party against up to four independently acting enemies.

    ``player`` remains Caelan for save settlement and existing callers. Commands
    default to ``active_player``; any living, full-gauge member can be selected
    while the model waits. Supplied party profiles and resources are copied;
    the caller settles their persistent state when the encounter ends.
    """

    _enemy_behavior = _primary_enemy_state('behavior')
    _enemy_style = _primary_enemy_state('style')
    _enemy_preparations = _primary_enemy_state('preparations')
    _enemy_prepared_action = _primary_enemy_state('prepared_action')
    _enemy_target_index = _primary_enemy_state('target_index')
    _enemy_action_index = _primary_enemy_state('action_index')
    telegraphed_target = _primary_enemy_state('telegraphed_target')

    @staticmethod
    def _prepared_spells(record, actions):
        if record['metadata'].get('combat_pending'):
            raise ValueError('Bestiary enemy combat implementation is pending')
        if record['metadata']['presentation_pending']:
            raise ValueError('Bestiary enemy presentation is pending')
        design = record['metadata'].get('combat_design')
        designed = design is not None and design['status'] == 'ready'
        if (record['fighting_style'] not in (None, 'standard_attacks',
                                            'physical_magical_alternation', 'magical_offense')
                and not ((designed or record['id'] == 'ridgeback_tusker')
                         and record['fighting_style'] == 'telegraphed_windup')):
            raise ValueError('Unsupported Bestiary fighting style')
        behavior = record['behavior']
        if behavior is not None and behavior['targeting'] != 'cycle_living_party':
            raise ValueError('Unsupported Bestiary targeting')
        preparations = {}
        if designed:
            preparations[design['windup']['prepare_action']] = design['windup']['attack_action']
        if record['fighting_style'] == 'magical_offense':
            for index, identifier in enumerate(behavior['sequence']):
                action = actions[identifier]
                if action['kind'] == 'prepare':
                    if index+1 >= len(behavior['sequence']):
                        raise ValueError('Magical preparation requires a following spell')
                    spell = behavior['sequence'][index+1]
                    if (actions[spell]['kind'] != 'magical' or not actions[spell]['mp_cost']
                            or preparations.get(identifier, spell) != spell):
                        raise ValueError('Magical preparation requires one paid spell')
                    preparations[identifier] = spell
                elif action['kind'] != 'magical' and identifier != behavior['fallback']:
                    raise ValueError('Magical offense requires damaging spells')
        return preparations

    @classmethod
    def from_bestiary(cls, player_attributes, enemy_id, level, *,
                      bestiary_data=None, **options):
        """Create a level-specific encounter without settling XP or saved state.

        Bestiary planning metadata stays inert. Only supported behavior and the
        compiled combat profile are installed in this battle's private copies.
        """
        from bestiary import build_enemy
        if 'enemy_data' in options:
            raise ValueError('Use bestiary_data for Bestiary encounters')
        actions = load_actions(options.get('action_data'))
        record = build_enemy(enemy_id, level, data=bestiary_data, actions=actions)
        preparations = cls._prepared_spells(record, actions)
        # The Tusker retains MQ02's authored targeting and forced Guard lesson.
        behavior = None if enemy_id == 'ridgeback_tusker' else record['behavior']
        model = cls(player_attributes, enemy_id=enemy_id,
                    enemy_data={'version': 1, 'enemies': {enemy_id: record['combat']}},
                    **options)
        model.enemy_bestiary_record = deepcopy(record)
        model.enemy_bestiary_id = record['id']
        model.enemy_level = record['level']
        model.enemy_xp_reward = record['xp_reward']
        model.enemy_sprite_id = record['presentation']['sprite_id']
        model.enemy_action_aliases = deepcopy(record['presentation']['action_aliases'])
        model._enemy_behavior = deepcopy(behavior)
        model._enemy_style = record['fighting_style']
        model._enemy_preparations = preparations
        model._enemy_states['enemy'].design = deepcopy(record['metadata'].get('combat_design'))
        model.enemy_records['enemy'] = model.enemy_bestiary_record
        return model

    @classmethod
    def from_bestiary_group(cls, player_attributes, members, *, bestiary_data=None,
                            initial_atb=True, initial_atb_seed=None, **options):
        """Build a fixed one-to-four-opponent formation at explicit levels.

        The formation is copied before battle. Initial ATB rolls are independent
        per participant; a dedicated seed can preserve the encounter handoff
        without coupling opening readiness to later damage variance.
        """
        from bestiary import build_enemy
        if (not isinstance(members, (tuple, list)) or not 1 <= len(members) <= MAX_ENEMIES
                or type(initial_atb) is not bool
                or initial_atb_seed is not None and not _integer(initial_atb_seed, maximum=2**63-1)
                or any(key in options for key in ('enemy_id', 'enemy_data'))
                or options.get('spellblade_tutorial', False)):
            raise ValueError('Invalid Bestiary formation')
        if options.get('aqua_edge_tutorial', False) and list(members) != [
                {'enemy_id': 'cave_bat', 'level': 2}, {'enemy_id': 'cave_bat', 'level': 2}]:
            raise ValueError('Aqua Edge lesson requires its two level-two Cave Bats')
        actions = load_actions(options.get('action_data'))
        records = []
        for member in members:
            if not isinstance(member, dict) or set(member) != {'enemy_id', 'level'}:
                raise ValueError('Invalid Bestiary formation member')
            record = build_enemy(member['enemy_id'], member['level'], data=bestiary_data,
                                 actions=actions)
            cls._prepared_spells(record, actions)
            records.append(record)
        if any(record['metadata'].get('combat_design', {}).get('status') == 'ready'
               and record['metadata']['combat_design']['encounter']['formation_size'] != len(records)
               for record in records):
            raise ValueError('Story boss requires its authored solo formation')
        first = records[0]
        model = cls.from_bestiary(player_attributes, first['id'], first['level'],
                                  bestiary_data=bestiary_data, **options)
        enemies = [model.enemy]
        for index, record in enumerate(records[1:], 2):
            identifier = 'enemy_'+str(index)
            definition = deepcopy(record['combat'])
            attributes = definition['attributes']
            enemies.append(Combatant(identifier, definition['name'], dict(attributes),
                                     attributes['hp'], attributes['mp']))
            model.enemy_definitions[identifier] = definition
            model.enemy_records[identifier] = deepcopy(record)
            model._enemy_states[identifier] = EnemyState(
                behavior=None if record['id'] == 'ridgeback_tusker' else deepcopy(record['behavior']),
                style=record['fighting_style'],
                preparations=cls._prepared_spells(record, actions),
                design=deepcopy(record['metadata'].get('combat_design')),
                target_index=(index-1) % len(model.party))
        model.enemies = tuple(enemies)
        model.enemy_xp_reward = sum(record['xp_reward'] or 0 for record in records)
        drops = {}
        for record in records:
            for item, quantity in record['combat']['rewards']['drops'].items():
                drops[item] = drops.get(item, 0)+quantity
        model.encounter_rewards = {'drops': drops}
        if initial_atb:
            generator = model.randomize_initial_atb(initial_atb_seed)
            offset = generator.randint(0, len(model.party)-1)
            for index, enemy in enumerate(model.enemies):
                model._enemy_states[enemy.identifier].target_index = (offset+index) % len(model.party)
        model.message = ('Enemies approach!' if len(model.enemies) > 1
                         else model.enemy.name+' approaches!')
        return model

    def __init__(self, player_attributes, learned_abilities=(), rng=None, enemy_id='bat',
                 *, guest_id=None, weapon_equipped=False, action_data=None,
                 enemy_data=None, guest_data=None,
                 guest_abilities=None, spellblade_tutorial=False, aqua_edge_tutorial=False,
                 elemental_tutorial=False,
                 active_gem=DEFAULT_GEM, owned_gems=GEM_ORDER, party_members=None, initial_atb=False,
                 initial_atb_seed=None, rig_allocation=None):
        if (type(initial_atb) is not bool or initial_atb_seed is not None
                and not _integer(initial_atb_seed, maximum=2**63-1)):
            raise ValueError('Invalid initial ATB configuration')
        if (type(elemental_tutorial) is not bool
                or elemental_tutorial and enemy_id not in ('embravyr', 'nivareth')):
            raise ValueError('Invalid elemental teaching encounter')
        self.elemental_tutorial = elemental_tutorial
        self.actions = load_actions(action_data)
        self.item_counts = None
        self.item_spent = {}
        self.item_definitions = {}
        rig_allocation = DEFAULT_ALLOCATION if rig_allocation is None else rig_allocation
        if not valid_allocation(rig_allocation):raise ValueError('Invalid rig allocation')
        self._rig_allocation = dict(rig_allocation)
        self.rig_skill_uses = {}
        self.rig_healing = {}
        self.restorative_skills = {}
        enemies = load_enemies(self.actions, enemy_data)
        if not isinstance(enemy_id, str) or enemy_id not in enemies:
            raise ValueError('Unknown battle enemy')
        if (not isinstance(learned_abilities, (tuple, list, set, frozenset))
                or any(not isinstance(identifier, str) for identifier in learned_abilities)):
            raise ValueError('Invalid learned abilities')
        if type(weapon_equipped) is not bool:raise ValueError('Invalid weapon equipment state')
        self.weapon_equipped = weapon_equipped
        if not valid_gem(active_gem):raise ValueError('Invalid active gem')
        if owned_gems is None:owned_gems = GEM_ORDER
        if (not isinstance(owned_gems, (tuple, list))
                or any(not valid_gem(gem) for gem in owned_gems)
                or len(set(owned_gems)) != len(owned_gems)
                or owned_gems and active_gem not in owned_gems):
            raise ValueError('Invalid owned gems')
        self.owned_gems = tuple(gem for gem in GEM_ORDER if gem in owned_gems)
        self.active_gem = active_gem
        # The presentation owns selector motion. It holds this flag while a
        # focus settles, preventing a command from using an intermediate pose.
        self.gear_settling = False
        values = {key: player_attributes.value(key) for key in ATTRIBUTE_IDS}
        if any(not _integer(value, 1 if key == 'hp' else 0, ATTRIBUTE_CAPS[key])
               for key, value in values.items()):
            raise ValueError('Invalid player battle attributes')
        hp, mp = player_attributes.current_hp, player_attributes.current_mp
        if not _integer(hp, 0, values['hp']) or not _integer(mp, 0, values['mp']):
            raise ValueError('Invalid player battle resources')
        name = getattr(player_attributes, 'name', 'Caelan')
        if not isinstance(name, str) or not name.strip():raise ValueError('Invalid player name')
        self.player = Combatant('player', name, dict(values), hp, mp)
        self.guest_definitions = {}
        members = [self.player]
        if party_members is not None:
            if guest_id is not None:raise ValueError('Supply a party or a legacy guest, not both')
            profiles = _party_snapshot(party_members, self.actions)
            members = []
            for profile in profiles:
                identifier = profile['identifier']
                member = Combatant(identifier, profile['name'], profile['attributes'],
                                   profile['hp'], profile['mp'])
                members.append(member)
                if identifier == 'player':self.player = member
                else:
                    self.guest_definitions[identifier] = {
                        key: profile[key] for key in ('name', 'attributes', 'attack')}
            if guest_data is not None:load_guests(self.actions, guest_data)
        elif guest_id is not None:
            guests = load_guests(self.actions, guest_data)
            if not isinstance(guest_id, str) or guest_id not in guests:
                raise ValueError('Unknown battle guest')
            guest = guests[guest_id]
            members.append(Combatant(guest_id, guest['name'], dict(guest['attributes']),
                                     guest['attributes']['hp'], guest['attributes']['mp']))
            self.guest_definitions[guest_id] = guest
        elif guest_data is not None:
            # An explicitly supplied catalog must be valid even without a guest.
            load_guests(self.actions, guest_data)
        self.party = tuple(members)
        self.guest_abilities = self._guest_ability_map(guest_abilities)
        self._active_actor = 'player'
        self._enemy_states = {'enemy': EnemyState(preparations={})}
        self.enemy_id = enemy_id
        self.enemy_bestiary_id = None
        self.enemy_bestiary_record = None
        self.enemy_level = self.enemy_xp_reward = None
        self.enemy_sprite_id = enemy_id
        self.enemy_action_aliases = {}
        self._enemy_behavior = None
        self._enemy_style = None
        self._enemy_preparations = {}
        self._enemy_prepared_action = None
        self._enemy_target_index = 0
        self.enemy_definition = deepcopy(enemies[enemy_id])
        enemy = self.enemy_definition
        self.enemy = Combatant('enemy', enemy['name'], dict(enemy['attributes']),
                               enemy['attributes']['hp'], enemy['attributes']['mp'])
        self.enemies = (self.enemy,)
        self.enemy_definitions = {'enemy': self.enemy_definition}
        self.enemy_records = {'enemy': None}
        if enemy_id == 'ridgeback_tusker' and enemy_data is None:
            from bestiary import build_enemy
            record = build_enemy(enemy_id, 1, actions=self.actions)
            self.enemy_bestiary_id = enemy_id
            self.enemy_bestiary_record = self.enemy_records['enemy'] = record
            self.enemy_level, self.enemy_xp_reward = record['level'], record['xp_reward']
            self._enemy_style = record['fighting_style']
        self.encounter_rewards = deepcopy(enemy['rewards'])
        self.initial_atb_values = {}
        self.selected_target = 'enemy'
        self.learned_abilities = frozenset(learned_abilities)
        self.rng = random.Random() if rng is None else rng
        if not callable(getattr(self.rng, 'randint', None)):
            raise TypeError('Battle RNG must expose randint')
        self.phase = 'charging' if any(member.hp for member in self.party) else 'defeat'
        self.current_action = self.last_action = None
        self.events = []
        self.message = 'A Bat approaches!' if enemy_id == 'bat' else self.enemy.name+' approaches!'
        self._pending_outcome = None
        self._enemy_action_index = 0
        self.telegraphed_target = None
        if type(spellblade_tutorial) is not bool:raise ValueError('Invalid spellblade tutorial state')
        if type(aqua_edge_tutorial) is not bool:raise ValueError('Invalid Aqua Edge tutorial state')
        if aqua_edge_tutorial and (spellblade_tutorial or enemy_id != 'cave_bat'
                                   or not weapon_equipped or not self.player.hp
                                   or 'water' not in self.owned_gems or active_gem != 'water'):
            raise ValueError('Aqua Edge lesson requires conscious armed Caelan and Blue gem')
        if spellblade_tutorial and (enemy_id != 'ridgeback_tusker'
                                   or self.combatant('mira') is None or not weapon_equipped
                                   or 'water' not in self.owned_gems):
            raise ValueError('Spellblade lesson requires the armed mill party')
        self.spellblade_stage = ('opening' if spellblade_tutorial and
                                'aether_edge' not in self.learned_abilities else None)
        if self.spellblade_guided and self.player.mp < self.actions['aether_edge']['mp_cost']:
            raise ValueError('The mill lesson requires preparation for Aether Edge')
        self.aether_edge_discovered = False
        self.aqua_edge_stage = (('complete' if 'aqua_edge' in self.learned_abilities else 'attempt')
                                if aqua_edge_tutorial else None)
        self.aqua_edge_discovered = False
        if initial_atb and not self.spellblade_guided:self.randomize_initial_atb(initial_atb_seed)
        if self.spellblade_guided:self.enemy.atb = 1.
        if self.phase == 'defeat':self._result('defeat')

    def randomize_initial_atb(self, seed=None):
        """Roll each living participant once, independently, in [0, 0.5]."""
        if seed is not None and not _integer(seed, maximum=2**63-1):
            raise ValueError('Invalid initial ATB seed')
        generator = random.Random(seed) if seed is not None else self.rng
        self.initial_atb_values = {}
        for actor in (*self.party, *self.enemies):
            value = (generator.random()*.5 if callable(getattr(generator, 'random', None))
                     else generator.randint(0, 500000)/1000000)
            alive = bool(actor.hp)
            actor.atb = value if alive else 0.
            self.initial_atb_values[actor.identifier] = actor.atb
        return generator

    @property
    def spellblade_guided(self):
        return self.spellblade_stage not in (None, 'complete')

    @property
    def aqua_edge_guided(self):
        return self.aqua_edge_stage not in (None, 'complete')

    @property
    def lesson_guided(self):
        return self.spellblade_guided or self.aqua_edge_guided

    @property
    def waiting_for_player(self):return self.phase == 'ready'

    @property
    def ended(self):return self.phase in RESULT_PHASES

    @property
    def gear_available(self):
        """The selector stays usable through other actors' actions and menus."""
        return bool(self.weapon_equipped and self.player.hp and not self.ended
                    and not (self.current_action is not None
                             and self.current_action.actor == 'player'))

    @property
    def gear_busy(self):
        return bool(self.gear_settling or not self.gear_available)

    def set_active_gem(self, gem):
        """Commit a settled focus without spending MP, ATB, or teaching skills.

        ``gear_settling`` blocks commands, not this completion callback. The
        presentation clears its settling flag after committing the final gem.
        """
        if (not valid_gem(gem) or gem not in self.owned_gems or not self.gear_available
                or self.lesson_guided and gem != 'water'):return False
        self.active_gem = gem
        return True

    @staticmethod
    def atb_rate(combatant):
        rate = .12+.004*combatant.value('speed')
        return rate

    def combatant(self, identifier):
        return next((member for member in (*self.party,
                                           *getattr(self, 'enemies', ()))
                     if member.identifier == identifier), None)

    def is_enemy(self, identifier):
        return any(enemy.identifier == identifier for enemy in self.enemies)

    @property
    def living_enemies(self):return tuple(enemy for enemy in self.enemies if enemy.hp)

    @property
    def enemy_telegraphs(self):
        return {identifier: state.telegraphed_target
                for identifier, state in self._enemy_states.items()
                if state.telegraphed_target is not None}

    @property
    def enemy_prepared_actions(self):
        return {identifier: state.prepared_action
                for identifier, state in self._enemy_states.items()
                if state.prepared_action is not None}

    @property
    def enemy_recovery_states(self):
        return {identifier: state.design['recovery']['damage_taken_multiplier']
                for identifier, state in self._enemy_states.items()
                if state.design is not None and state.vulnerable}

    @property
    def flee_allowed(self):
        return not any(state.design is not None
                       and not state.design['encounter'].get('flee_allowed', False)
                       for state in self._enemy_states.values())

    def enemy_record(self, identifier='enemy'):
        return self.enemy_records.get(identifier)

    def enemy_definition_for(self, identifier='enemy'):
        return self.enemy_definitions.get(identifier)

    def enemy_sprite_id_for(self, identifier='enemy'):
        if identifier == 'enemy':return self.enemy_sprite_id
        record = self.enemy_records.get(identifier)
        return record['presentation']['sprite_id'] if record is not None else None

    def enemy_action_aliases_for(self, identifier='enemy'):
        if identifier == 'enemy':return self.enemy_action_aliases
        record = self.enemy_records.get(identifier)
        return record['presentation']['action_aliases'] if record is not None else {}

    def enemy_sprite(self, identifier='enemy'):
        return self.enemy_sprite_id_for(identifier)

    def select_target(self, identifier):
        target = self.combatant(identifier)
        if not self.is_enemy(identifier) or target is None or not target.hp:return False
        self.selected_target = identifier
        return True

    def _living_target(self, preferred=None):
        target = self.combatant(preferred or self.selected_target)
        if target is not None and self.is_enemy(target.identifier) and target.hp:
            return target.identifier
        return self.living_enemies[0].identifier if self.living_enemies else None



    def _guest_ability_map(self, supplied):
        if supplied is None:
            return {member.identifier: starting_abilities(member.identifier)
                    for member in self.party if member.identifier != 'player'}
        if (not isinstance(supplied, dict)
                or any(not isinstance(owner, str) or not owner
                       or not isinstance(known, (tuple, list, set, frozenset))
                       or any(not isinstance(key, str) or not key for key in known)
                       for owner, known in supplied.items())):
            raise ValueError('Invalid guest abilities')
        return {owner: frozenset(known) for owner, known in supplied.items()}


    @property
    def active_player(self):
        return self.combatant(self._active_actor)

    @property
    def ready_actor(self):
        return self._active_actor if self.waiting_for_player else None

    @property
    def ready_members(self):
        return tuple(member.identifier for member in self.party
                     if member.hp and member.atb+EPSILON >= 1
                     and (not self.lesson_guided or member.identifier == 'player'))

    def select_ready(self, identifier):
        if (not self.waiting_for_player or not isinstance(identifier, str)
                or identifier not in self.ready_members):return False
        self._active_actor = identifier
        return True

    def _party_actor(self, actor_id=None):
        if actor_id is None:actor_id = self._active_actor
        return next((member for member in self.party if member.identifier == actor_id), None)

    @property
    def rig_allocation(self):return dict(self._rig_allocation)

    def rig_reason(self):
        mira = self._party_actor('mira')
        if mira is None:return 'Mira is not in the combat party.'
        if not mira.hp:return 'Mira is incapacitated.'
        if self.ended:return 'The battle has ended.'
        if self.lesson_guided:return 'Finish the guided action first.'
        if self.phase == 'acting':return 'Wait for the current action to finish.'
        if self.phase != 'charging' and not (self.phase == 'ready' and self.ready_actor == 'mira'):
            return 'Select Mira when she is ready.'
        return ''

    def set_rig_allocation(self, allocation):
        if not valid_allocation(allocation) or self.rig_reason():return False
        self._rig_allocation = dict(allocation)
        return True

    def _repair_reason(self, target_id):
        if target_id is None:
            return '' if any(member.hp and member.hp < member.max_hp for member in self.party) else 'No injured living ally.'
        target = self._party_actor(target_id)
        if target is None:return 'Choose an active party member.'
        if not target.hp:return 'Repair Pulse cannot revive a KO character.'
        if target.hp >= target.max_hp:return 'HP is already full.'
        return ''

    def available_actions(self, actor_id=None):
        actor = self._party_actor(actor_id)
        if actor is None:return []
        if actor.identifier != 'player':return list(PLAYER_ACTIONS)+self.skill_actions(actor.identifier)
        return list(PLAYER_ACTIONS)+[key for key in SUPPORTED_LEARNED_ACTIONS
                                    if key in self.learned_abilities]+self.skill_actions(actor.identifier)

    def skill_actions(self, actor_id=None):
        """Implemented skills owned by this party member."""
        actor = self._party_actor(actor_id)
        if actor is None:return []
        if actor.identifier == 'player':
            if self.spellblade_stage == 'first_edge' or self.aqua_edge_guided:
                return ['aqua_edge']
            # Focus ownership never grants the corresponding technique.
            return [key for key in ('aether_edge', *REQUIRED_GEMS)
                    if key in self.learned_abilities and key in self.actions
                    and self.actions[key]['kind'] != 'failed_edge']
        if actor.identifier == 'mira':
            return [key for key in RIG_SKILLS if key in self.guest_abilities.get('mira', ())]
        return []

    def command_actions(self, actor_id=None):
        """Root commands include the Skills submenu, never a synthetic action."""
        actor = self._party_actor(actor_id)
        if actor is None:return []
        spells = [key for key in SUPPORTED_LEARNED_ACTIONS
                  if actor.identifier == 'player' and key in self.learned_abilities]
        return ['attack', 'skills']+(['items'] if self.item_counts is not None else [])+['guard', 'flee']+spells

    def command_reason(self, identifier, actor_id=None):
        if identifier == 'items':
            if self.item_counts is None:return 'Items are unavailable.'
            if self.lesson_guided:return 'Finish the guided action first.'
            if not self.waiting_for_player:return 'Wait until a character is ready.'
            if not any(self.item_counts.get(key, 0) for key in self.item_definitions):return 'No items carried.'
            return ''
        if identifier != 'skills':return self.action_reason(identifier, actor_id)
        actor = self._party_actor(actor_id)
        if actor is None:return 'This action is not available.'
        if self.spellblade_guided:
            if actor.identifier != 'player':return 'Mira is covering Caelan.'
            if self.spellblade_stage != 'first_edge':
                return 'Guard against the charge first.'
        if self.aqua_edge_guided and actor.identifier != 'player':return 'Mira is covering Caelan.'
        if (self.phase != 'ready' or not actor.hp
                or actor.atb+EPSILON < 1):return actor.name+' is not ready.'
        if actor.identifier == 'player' and self.gear_settling:
            return 'The gear is settling.'
        if actor.identifier == 'player' and not self.weapon_equipped:
            return 'Requires a weapon.'
        if not self.skill_actions(actor.identifier):return 'No skills learned.'
        return ''

    def _action_id(self, command, actor):
        if command == 'attack' and actor.identifier in self.guest_definitions:
            return self.guest_definitions[actor.identifier]['attack']
        return command

    def action_reason(self, identifier, actor_id=None, target_id=None):
        actor = self._party_actor(actor_id)
        if (actor is None or not isinstance(identifier, str)
                or identifier not in self.available_actions(actor.identifier)):
            return 'This action is not available.'
        if identifier == 'flee' and not self.flee_allowed:
            return 'Cannot flee this boss battle.'
        if self.aqua_edge_guided and actor.identifier != 'player':return 'Mira is covering Caelan.'
        if (self.phase != 'ready' or not actor.hp
                or actor.atb+EPSILON < 1):return actor.name+' is not ready.'
        if actor.identifier == 'player' and self.gear_settling:
            return 'The gear is settling.'
        if self.spellblade_guided:
            if actor.identifier != 'player':return 'Mira is covering Caelan.'
            expected = ('guard',) if self.spellblade_stage == 'guard' else ELEMENTAL_EDGE_ATTEMPTS
            if identifier not in expected:
                return ('Guard against the charge first.' if self.spellblade_stage == 'guard'
                        else 'Choose a focus from Skills.')
        if (actor.identifier == 'player' and identifier in ('aether_edge', *REQUIRED_GEMS)
                and not self.weapon_equipped):
            return 'Requires a weapon.'
        if actor.identifier == 'player' and identifier in REQUIRED_GEMS:
            gem = REQUIRED_GEMS[identifier]
            if gem not in self.owned_gems:return 'Requires the '+GEM_NAMES[gem]+' gem.'
            if self.active_gem != gem:return 'Requires the '+GEM_NAMES[gem]+' gem.'
        if identifier in RIG_SKILLS:
            requirements = self.actions[identifier]['power_requirements']
            missing = [key.title()+' '+str(amount)+' (currently '+str(self._rig_allocation[key])+')'
                       for key, amount in requirements.items() if self._rig_allocation[key] < amount]
            if missing:return 'Requires '+', '.join(missing)+'.'
            if identifier == 'repair_pulse':
                reason = self._repair_reason(target_id)
                if reason:return reason
        if self.aqua_edge_guided and identifier != 'aqua_edge':
            return 'Try Aqua Edge from Skills.'
        if actor.mp < self.action_mp_cost(identifier, actor.identifier):
            return 'Not enough MP.'
        return ''

    def action_mp_cost(self, identifier, actor_id=None):
        """Teaching encounters waive elemental Edge costs, never other actions."""
        actor = self._party_actor(actor_id)
        if actor is not None and actor.identifier == 'player':
            if self.elemental_tutorial and identifier in ELEMENTAL_EDGE_ACTIONS:return 0
            if identifier == 'aqua_edge' and (self.aqua_edge_stage is not None
                                             or self.spellblade_stage == 'first_edge'):return 0
        action_id = self._action_id(identifier, actor) if actor is not None else identifier
        return self.actions[action_id]['mp_cost']

    def choose_action(self, identifier, actor_id=None, target_id=None, *, target=None):
        if target is not None:
            if target_id is not None and target_id != target:return False
            target_id = target
        if self.action_reason(identifier, actor_id, target_id):return False
        actor = self._party_actor(actor_id)
        self._active_actor = actor.identifier
        action = ('aqua_edge_attempt' if actor.identifier == 'player' and
                  self.spellblade_stage == 'first_edge' and identifier == 'aqua_edge'
                  else self._action_id(identifier, actor))
        if self.actions[action]['target'] == 'opponent':
            if target_id is not None and not self.select_target(target_id):return False
            target_id = self._living_target(target_id)
            if target_id is None:return False
        elif self.actions[action]['target'] == 'ally' and target_id is None:return False
        self._start_action(actor.identifier, action, target_id=target_id)
        return True

    def set_item_inventory(self, inventory):
        """Copy shared supplies for this attempt; settlement owns durable costs."""
        from inventory import Inventory
        if not isinstance(inventory, Inventory) or self.item_counts is not None:return
        self.item_definitions = {key: deepcopy(value) for key, value in inventory.definitions.items()
                                 if value.get('use_context') in ('consumable', 'rest_policy_pending')}
        self.item_counts = {key: inventory.quantity(key) for key in self.item_definitions}
        for key, item in self.item_definitions.items():
            self.actions['item:'+key] = {'name': item['name'], 'kind': 'item',
                'potency': 0, 'mp_cost': 0, 'duration': 1., 'impact_at': .5,
                'animation': 'idle', 'target': 'none' if item.get('effect', {}).get('kind') == 'escape' else 'ally'}

    def item_reason(self, item_id, target_id=None, actor_id=None):
        from consumables import target_reason
        actor = self._party_actor(actor_id)
        if not isinstance(item_id, str):return 'Choose an item.'
        if self.item_counts is None or item_id not in self.item_definitions:return 'This item is unavailable.'
        item = self.item_definitions[item_id]
        if not item.get('effect'):return 'Rest Kit use is not available yet.'
        if not self.item_counts[item_id]:return 'None remaining.'
        if self.lesson_guided:return 'Finish the guided action first.'
        if self.phase != 'ready' or actor is None or not actor.hp or actor.atb+EPSILON < 1:
            return 'This character is not ready.'
        if actor.identifier == 'player' and self.gear_settling:return 'The gear is settling.'
        if item['effect']['kind'] == 'escape':return '' if self.flee_allowed else 'Cannot flee this boss battle.'
        if target_id is None:
            return '' if any(not self.item_reason(item_id, member.identifier, actor.identifier)
                             for member in self.party) else 'No valid target.'
        target = self._party_actor(target_id)
        if target is None:return 'Choose a party member.'
        return target_reason(self.item_definitions[item_id]['effect'], target.hp, target.mp,
                             target.max_hp, target.max_mp)

    def choose_item(self, item_id, target_id=None, actor_id=None):
        if self.item_reason(item_id, target_id, actor_id):return False
        if self.item_definitions[item_id]['effect']['kind'] != 'escape' and target_id is None:return False
        actor = self._party_actor(actor_id)
        self._active_actor = actor.identifier
        self.item_counts[item_id] -= 1
        self.item_spent[item_id] = self.item_spent.get(item_id, 0)+1
        self._start_action(actor.identifier, 'item:'+item_id, target_id=target_id)
        return True

    def drain_events(self):
        result, self.events = self.events, []
        return result

    def _sync_enemy_preparation(self):
        """Keep each held spell's visible target and MP reservation truthful."""
        living = [member for member in self.party if member.hp]
        for enemy in self.enemies:
            state = self._enemy_states[enemy.identifier]
            spell = state.prepared_action
            if spell is None:continue
            casting = (self.current_action is not None
                       and self.current_action.actor == enemy.identifier
                       and self.current_action.action == spell)
            if (not enemy.hp or not living or self.ended
                    or not casting and enemy.mp < self.actions[spell]['mp_cost']):
                state.prepared_action = state.telegraphed_target = None
                continue
            if not any(member.identifier == state.telegraphed_target for member in living):
                state.telegraphed_target = self._enemy_target(spell, enemy.identifier)
                if state.design is not None:
                    state.response_actions = 0
                    self._warn_target(enemy.identifier, state.telegraphed_target, retargeted=True)
                if casting and state.design is not None and not self.current_action.resolved:
                    # A target lost during the leap cannot turn its replacement
                    # into an unannounced hit. Restart the held strike only
                    # after the replacement has had its own command opportunity.
                    enemy.mp = min(enemy.max_mp, enemy.mp+self.actions[spell]['mp_cost'])
                    enemy.atb = 1.0
                    state.action_index = state.behavior['sequence'].index(spell)
                    self.last_action, self.current_action = self.current_action, None
                    self.phase = 'charging'
                elif casting and not self.current_action.resolved:
                    self.current_action.target = state.telegraphed_target

    def _warn_target(self, enemy_actor, target, *, retargeted=False):
        state = self._enemy_states[enemy_actor]
        member = self.combatant(target)
        if member is None:return
        prepare = state.design['windup']['prepare_action']
        self.message = self.combatant(enemy_actor).name+' gathers resonance toward '+member.name+'.'
        self.events.append({'type': 'telegraph', 'actor': enemy_actor,
                            'action': prepare, 'target': target,
                            'prepared_action': state.prepared_action,
                            'hold_after': 0 if retargeted else
                                self.actions[prepare]['duration']-self.actions[prepare]['impact_at'],
                            'retargeted': retargeted})

    def _enemy_response_pending(self, enemy_actor):
        state = self._enemy_states[enemy_actor]
        if state.design is None:return False
        windup = state.design['windup']
        next_action = state.behavior['sequence'][state.action_index % len(state.behavior['sequence'])]
        return (next_action == windup['attack_action']
                and state.prepared_action == next_action
                and state.response_actions < windup['minimum_target_actions'])

    def _enemy_target(self, identifier, enemy_actor='enemy'):
        living = [member for member in self.party if member.hp]
        if not living:return None
        state = self._enemy_states[enemy_actor]
        if identifier == state.prepared_action and state.telegraphed_target:
            target = next((member for member in living
                           if member.identifier == state.telegraphed_target), None)
            if target is not None:return target.identifier
        if state.behavior is not None:
            for offset in range(len(self.party)):
                member = self.party[(state.target_index+offset) % len(self.party)]
                if member.hp:return member.identifier
        if self.spellblade_guided and identifier == 'tusker_charge':return 'player'
        if identifier == 'tusker_charge' and state.telegraphed_target:
            target = next((member for member in living
                           if member.identifier == state.telegraphed_target), None)
            if target is not None:return target.identifier
        record = self.enemy_records.get(enemy_actor)
        species = self.enemy_id if enemy_actor == 'enemy' else record['id'] if record else None
        if species == 'ridgeback_tusker' and identifier == 'tusk_strike':
            mira = self.combatant('mira')
            if mira is not None and mira.hp:return 'mira'
        return living[0].identifier

    def _start_action(self, actor_id, identifier, target_id=None):
        actor = self.combatant(actor_id)
        record = self.actions[identifier]
        enemy_actor = self.is_enemy(actor_id)
        if not enemy_actor and self._party_actor(actor_id) is not None:
            for state in self._enemy_states.values():
                if state.design is not None and state.telegraphed_target == actor_id:
                    state.response_actions += 1
        if enemy_actor:
            state = self._enemy_states[actor_id]
            if (state.design is not None and state.vulnerable
                    and identifier == state.design['recovery']['ends_before_action']):
                state.vulnerable = False
                self.events.append({'type': 'recovery_ended', 'actor': actor_id, 'action': identifier})
        actor.mp -= self.action_mp_cost(identifier, actor_id)
        actor.atb = 0.0
        target = (self._enemy_target(identifier, actor_id) if enemy_actor
                  else self._living_target(target_id))
        if record['target'] == 'self':target = actor_id
        elif record['target'] == 'ally':target = target_id
        elif record['target'] == 'all_opponents':target = 'all_opponents'
        elif record['target'] == 'none':target = None
        if enemy_actor and record['target'] == 'opponent' and target is not None:
            state = self._enemy_states[actor_id]
            if state.behavior is not None:
                if identifier == state.prepared_action:state.telegraphed_target = target
                state.target_index = (next(index for index, member in enumerate(self.party)
                                          if member.identifier == target)+1) % len(self.party)
        choreography = 'aether_edge' if identifier in ELEMENTAL_EDGE_ACTIONS else identifier
        timing = (timing_override(choreography, record['duration'], record['impact_at'])
                  if actor_id == 'player' else None)
        duration, impact_at = timing or (record['duration'], record['impact_at'])
        self.current_action = BattleAction(actor_id, identifier, target, record['name'],
                                          record['kind'], record['animation'],
                                          duration, impact_at,
                                          active_gem=self.active_gem if actor_id == 'player' else None,
                                          choreography=choreography if timing else None,
                                          weapon_equipped=self.weapon_equipped if actor_id == 'player' else False)
        if actor_id == 'mira' and identifier in RIG_SKILLS:
            self.current_action.rig_allocation = self.rig_allocation
            self.rig_skill_uses[identifier] = self.rig_skill_uses.get(identifier, 0)+1
            if identifier == 'repair_pulse':
                self.restorative_skills[identifier] = self.restorative_skills.get(identifier, 0)+1
        if target == 'all_opponents':
            opponents = self.party if enemy_actor else self.enemies
            self.current_action.targets = tuple(member.identifier for member in opponents if member.hp)
        self.phase = 'acting'
        self.message = actor.name+' uses '+record['name']+'.'
        self.events.append({'type': 'action_started', 'actor': actor_id,
                            'action': identifier, 'target': target, 'name': record['name']})

    def _start_enemy_action(self, enemy_actor='enemy'):
        enemy = self.combatant(enemy_actor)
        if enemy is None or not enemy.hp:return
        state = self._enemy_states[enemy_actor]
        if self._enemy_response_pending(enemy_actor):return False
        choices = (state.behavior['sequence'] if state.behavior is not None
                   else self.enemy_definitions[enemy_actor]['abilities'])
        if self.spellblade_guided:
            identifier = ('prepare_charge' if self.spellblade_stage == 'opening' else
                          'tusker_charge' if self.spellblade_stage == 'charge' else 'tusk_strike')
        else:
            identifier = choices[state.action_index % len(choices)]
            if (state.design is not None and identifier == state.design['windup']['attack_action']
                    and state.prepared_action != identifier):
                state.action_index = choices.index(state.design['windup']['prepare_action'])
                identifier = choices[state.action_index]
            state.action_index += 1
        prepared_spell = state.preparations.get(identifier)
        if (prepared_spell is not None
                and enemy.mp < self.actions[prepared_spell]['mp_cost']):
            identifier = state.behavior['fallback']
            state.action_index = 0
            state.prepared_action = state.telegraphed_target = None
        if enemy.mp < self.actions[identifier]['mp_cost']:
            identifier = (state.behavior['fallback'] if state.behavior is not None
                          else next(key for key in choices if self.actions[key]['mp_cost'] == 0
                                    and self.actions[key]['kind'] in ('physical', 'magical')))
            if state.style == 'magical_offense':
                state.action_index = 0
                state.prepared_action = state.telegraphed_target = None
        self._start_action(enemy_actor, identifier)

    def _resolve_action(self):
        action = self.current_action
        actor = self.combatant(action.actor)
        if action.kind == 'guard':
            actor.guarded = True
            self.message = actor.name+' braces for the next attack.'
            self.events.append({'type': 'guard', 'actor': action.actor})
            if self.spellblade_stage == 'guard' and action.actor == 'player':
                self.spellblade_stage = 'charge';self.enemy.atb = 1.
        elif action.kind == 'barrier':
            self._grant_barrier(actor, self.actions[action.action]['barrier_percent'], action)
            self.message = actor.name+' activates Bulwark.'
        elif action.kind == 'heal':
            target = self._party_actor(action.target)
            if target is not None and target.hp:
                amount = min(target.max_hp-target.hp, healing_amount(actor.value('spr'), target.max_hp))
                target.hp += amount
                if amount:self.rig_healing[target.identifier] = self.rig_healing.get(target.identifier, 0)+amount
                self.events.append({'type': 'skill_heal', 'actor': actor.identifier,
                    'target': target.identifier, 'action': action.action, 'amount': amount, 'resource': 'hp'})
                self.message = target.name+' recovers '+str(amount)+' HP.'
        elif action.kind == 'item':
            from consumables import restore, target_reason
            item_id = action.action.split(':', 1)[1]
            effect = self.item_definitions[item_id]['effect']
            if effect['kind'] == 'escape':
                self._pending_outcome = 'fled'
                self.message = 'The party escapes under cover of smoke.'
                self.events.append({'type': 'item_effect', 'actor': action.actor,
                    'target': action.actor, 'item': item_id, 'action': action.action, 'amount': 0})
            else:
                target = self._party_actor(action.target)
                if target is not None and not target_reason(effect, target.hp, target.mp, target.max_hp, target.max_mp):
                    before_hp, before_mp = target.hp, target.mp
                    target.hp, target.mp = restore(effect, target.hp, target.mp, target.max_hp, target.max_mp)
                    if before_hp == 0:target.atb = 0.;target.guarded = False
                    amount = target.mp-before_mp if effect['kind'] == 'restore_mp' else target.hp-before_hp
                    self.events.append({'type': 'item_effect', 'actor': action.actor,
                        'target': target.identifier, 'item': item_id, 'action': action.action,
                        'amount': amount, 'revived': before_hp == 0,
                        'resource': 'mp' if effect['kind'] == 'restore_mp' else 'hp'})
                    self.message = target.name+' recovers '+str(amount)+(' MP.' if effect['kind'] == 'restore_mp' else ' HP.')
                    self._sync_party_activity()
        elif action.kind == 'flee':
            self._pending_outcome = 'fled'
            self.message = actor.name+' gets away safely.'
        elif action.kind == 'prepare':
            state = self._enemy_states[action.actor]
            prepared_spell = state.preparations.get(action.action)
            target = self._enemy_target(prepared_spell or 'tusker_charge', action.actor)
            state.telegraphed_target = target
            member = self.combatant(target)
            if prepared_spell is not None:
                state.prepared_action = prepared_spell
                state.response_actions = 0
                self.message = actor.name+' gathers charge toward '+member.name+'.'
            else:self.message = actor.name+' lowers its head toward '+member.name+'.'
            self.events.append({'type': 'telegraph', 'actor': action.actor,
                                'action': action.action, 'target': target,
                                **({'prepared_action': prepared_spell,
                                    'hold_after': action.duration-action.impact_at}
                                   if prepared_spell else {})})
            if self.spellblade_stage == 'opening':self.spellblade_stage = 'guard'
        elif action.kind == 'recover':
            self.message = actor.name+' is exhausted.'
            self.events.append({'type': 'recover', 'actor': action.actor, 'action': action.action})
        elif action.kind == 'failed_edge':
            self.message = 'The Blue gem flickers; Aqua Edge fails. Raw aether floods the blade.'
            self.spellblade_stage = 'second_edge'
            self.events.append({'type': 'spellblade_failed', 'actor': action.actor,
                                'action': action.action})
        elif action.kind == 'enchant':
            actor.aether_edge_hits = self.actions[action.action]['weapon_hits']
            self.message = actor.name+' enchants their weapon with Aether Edge.'
            self.events.append({'type': 'enchant', 'actor': action.actor,
                                'action': action.action,
                                'remaining_hits': actor.aether_edge_hits})
        else:
            if self.actions[action.action]['target'] == 'all_opponents':
                opponents = self.party if self.is_enemy(action.actor) else self.enemies
                targets = tuple(member for member in opponents if member.hp)
                action.targets = tuple(member.identifier for member in targets)
                action.damage = sum(self._damage_target(action, actor, target) for target in targets)
                side = 'the party' if self.is_enemy(action.actor) else 'the enemies'
                self.message = actor.name+' strikes '+side+' with '+action.name+'.'
            else:
                target = self.combatant(action.target)
                if target is None or not target.hp:
                    action.target = (self._enemy_target(action.action, action.actor)
                                     if self.is_enemy(action.actor) else self._living_target())
                    target = self.combatant(action.target)
                if target is None:
                    self._pending_outcome = 'defeat' if self.is_enemy(action.actor) else 'victory'
                    action.resolved = True
                    return
                action.damage = self._damage_target(action, actor, target)
            if action.action == 'impact_bolt' and actor.hp:
                self._grant_barrier(actor, self.actions[action.action]['barrier_percent'], action)
            if self.is_enemy(action.actor):
                state = self._enemy_states[action.actor]
                if action.action == state.prepared_action:
                    state.prepared_action = state.telegraphed_target = None
                    state.response_actions = 0
                if state.design is not None and action.action == state.design['recovery']['after_action']:
                    state.vulnerable = True
                    self.events.append({'type': 'recovery_started', 'actor': action.actor,
                        'action': action.action,
                        'damage_taken_multiplier': state.design['recovery']['damage_taken_multiplier']})
            if action.action == 'tusker_charge':
                self._enemy_states[action.actor].telegraphed_target = None
                if self.spellblade_stage == 'charge':self.spellblade_stage = 'first_edge'
            if action.action == 'aqua_edge' and self.aqua_edge_guided:
                self.aqua_edge_stage = 'complete'
                self.learned_abilities = self.learned_abilities | {'aqua_edge'}
                self.aqua_edge_discovered = True
                self.events.append({'type': 'aqua_edge_discovered', 'actor': 'player',
                                    'action': 'aqua_edge'})
            if action.action == 'aether_edge' and self.spellblade_stage == 'second_edge':
                self.spellblade_stage = 'complete'
                self.learned_abilities = self.learned_abilities | {'aether_edge'}
                self.aether_edge_discovered = True
                self.events.append({'type': 'spellblade_discovered', 'actor': 'player',
                                    'action': 'aether_edge'})
            if not any(member.hp for member in self.party):self._pending_outcome = 'defeat'
            self._sync_party_activity()
        self._sync_enemy_preparation()
        action.resolved = True

    def _elemental_response(self, target, element):
        """Shared Bestiary response for a tagged damage component.

        Unaligned and fixed legacy actors are neutral. Same-element absorption
        supersedes the percentage and restores the neutral component's damage.
        """
        record = self.enemy_records.get(target.identifier)
        profile = record['metadata'].get('elemental_profile') if record else None
        if profile is None or element in (None, 'non_elemental'):return Fraction(1), False
        if element in profile['absorption']['elements']:return Fraction(1), True
        return Fraction(str(profile['damage_percentages'][element]))/100, False

    def _grant_barrier(self, target, percent, action):
        previous = target.barrier
        target.barrier = max(previous, barrier_amount(target.max_hp, percent))
        target.barrier_turns = 2
        action.barrier_granted = True
        self.events.append({'type': 'barrier_applied', 'actor': action.actor,
            'target': target.identifier, 'action': action.action, 'amount': target.barrier,
            'previous': previous, 'turns': target.barrier_turns})

    def _clear_barrier(self, target, reason):
        if target.barrier or target.barrier_turns:
            target.barrier = target.barrier_turns = 0
            self.events.append({'type': 'barrier_expired', 'actor': target.identifier,
                                'target': target.identifier, 'reason': reason})

    def _complete_rig_turn(self, action):
        target = self._party_actor(action.actor)
        if target is None or target.identifier != 'mira' or not target.hp:return
        if target.barrier_turns and not action.barrier_granted:
            target.barrier_turns -= 1
            if not target.barrier_turns:self._clear_barrier(target, 'duration')

    def _damage_target(self, action, actor, target):
        """Resolve one hit; vulnerability modifies the complete hit once."""
        protected = target.guarded
        calculator = physical_damage if action.kind in ('physical', 'spellblade') else magical_damage
        variance = roll_variance(self.rng)
        source = actor
        record = self.actions[action.action]
        affinity, absorbed = self._elemental_response(target, record.get('element'))
        # A spellblade's element belongs only to its magical component.
        damage = calculator(source, target, record['potency'],
                            affinity=1 if action.kind == 'spellblade' else affinity,
                            protected=protected, variance_percent=variance)
        healing = damage if absorbed and action.kind != 'spellblade' else 0
        if healing:damage = 0
        if action.kind == 'spellblade':
            bonus = magical_damage(source, target, record['magical_potency'],
                                   affinity=affinity, protected=protected, variance_percent=variance)
            if absorbed:healing = bonus
            else:damage = min(NORMAL_DAMAGE_CAP, damage+bonus)
        enchanted = (action.actor == 'player' and self.weapon_equipped
                     and action.kind == 'physical' and actor.aether_edge_hits > 0)
        if enchanted:
            bonus = magical_damage(actor, target, self.actions['aether_edge']['potency'],
                                   protected=protected, variance_percent=variance)
            damage = min(NORMAL_DAMAGE_CAP, damage+bonus)
            actor.aether_edge_hits -= 1
        if self.is_enemy(target.identifier):
            state = self._enemy_states[target.identifier]
            if state.design is not None and state.vulnerable:
                factor = Fraction(str(state.design['recovery']['damage_taken_multiplier']))
                damage = min(NORMAL_DAMAGE_CAP, damage*factor.numerator//factor.denominator)
        blocked = min(target.barrier, damage)
        if blocked:
            target.barrier -= blocked
            damage -= blocked
            self.events.append({'type': 'barrier_absorbed', 'actor': action.actor,
                'target': target.identifier, 'action': action.action,
                'amount': blocked, 'remaining': target.barrier})
            if not target.barrier:self._clear_barrier(target, 'depleted')
        before_hp = target.hp
        target.hp = max(0, min(target.max_hp, target.hp-damage+healing))
        restored = max(0, target.hp-max(0, before_hp-damage))
        target.guarded = False
        self.message = target.name+' takes '+str(damage)+' damage.'
        if restored:self.message += ' The element restores '+str(restored)+' HP.'
        event = {'type': 'impact', 'actor': action.actor, 'action': action.action,
                 'target': target.identifier, 'damage': damage,
                 'remaining_hp': target.hp, 'guarded': protected}
        if absorbed:event.update(healing=restored, element=record.get('element'), absorbed=True)
        if blocked:event['barrier_absorbed'] = blocked
        if enchanted:event.update(aether_edge=True, remaining_hits=actor.aether_edge_hits)
        self.events.append(event)
        if not target.hp:
            target.atb = 0.0
            self._clear_barrier(target, 'ko')
            if self.is_enemy(target.identifier):
                state = self._enemy_states[target.identifier]
                state.prepared_action = state.telegraphed_target = None
                state.response_actions = 0
                state.vulnerable = False
                self.selected_target = self._living_target()
                if not self.living_enemies:self._pending_outcome = 'victory'
        return damage

    def _result(self, outcome):
        for state in self._enemy_states.values():
            if state.style == 'magical_offense' or state.design is not None:
                state.prepared_action = state.telegraphed_target = None
                state.response_actions = 0
                state.vulnerable = False
        for actor in (*self.party, *self.enemies):
            actor.aether_edge_hits = 0
            self._clear_barrier(actor, 'battle_end')
        self.phase = outcome
        defeat = ('The party has fallen.' if len(self.party) > 1
                  else self.player.name+' has fallen.')
        self.message = {'victory': 'Victory!', 'defeat': defeat,
                        'fled': 'Escaped safely.'}[outcome]
        self.events.append({'type': 'result', 'outcome': outcome})

    def _advance_gauges(self, seconds, atb_multiplier=1.0):
        scaled_seconds = seconds*atb_multiplier
        for combatant in (*self.party, *self.enemies):
            if combatant.hp and (not self.aqua_edge_guided or combatant.identifier == 'player'):
                combatant.atb = min(1.0, combatant.atb+self.atb_rate(combatant)*scaled_seconds)
    def _sync_party_activity(self):
        # A lesson cannot keep ordering an incapacitated character to act.
        # Release the companions without treating survival as a skill discovery.
        for member in self.party:
            if not member.hp:self._clear_barrier(member, 'ko')
        if self.lesson_guided and not self.player.hp:
            was_aqua = self.aqua_edge_guided
            self.spellblade_stage = self.aqua_edge_stage = None
            self.telegraphed_target = None
            if self.current_action is not None and self.current_action.actor == 'player':
                self.last_action, self.current_action = self.current_action, None
                self.phase = 'charging'
            elif self.waiting_for_player and self._active_actor == 'player':
                self.phase = 'charging'
            self.events.append({'type': 'aqua_edge_interrupted' if was_aqua else 'spellblade_interrupted',
                                'actor': 'player'})
    def update(self, seconds, *, atb_multiplier=1.0):
        """Consume wall time through exact boundaries; choice time is free.

        The global multiplier affects every charging gauge, but never action animations. Zero freezes charging while still
        allowing an already full gauge to act. Ready menus always pause gauges.
        """
        if type(seconds) not in (int, float):raise TypeError('Battle time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid battle time')
        if type(atb_multiplier) not in (int, float):raise TypeError('ATB multiplier must be numeric')
        if not math.isfinite(atb_multiplier) or atb_multiplier < 0:
            raise ValueError('Invalid ATB multiplier')
        self._sync_party_activity()
        self._sync_enemy_preparation()
        remaining = float(seconds)
        while True:
            if self.ended or self.waiting_for_player:return
            if self.phase == 'charging':
                living = [member for member in self.party if member.hp]
                if not living:
                    self._result('defeat')
                    return
                if not self.living_enemies:
                    self._result('victory')
                    return
                candidates = [*(member for member in living
                                if not self.aqua_edge_guided or member.identifier == 'player'),
                              *(enemy for enemy in self.living_enemies
                                if not self.aqua_edge_guided and not self._enemy_response_pending(enemy.identifier))]
                times = [(actor, max(0.0, ((1-actor.atb)/self.atb_rate(actor))/atb_multiplier)
                          if atb_multiplier else 0.0 if actor.atb+EPSILON >= 1 else math.inf)
                         for actor in candidates]
                earliest = min(time for actor, time in times)
                if math.isinf(earliest):
                    self._advance_gauges(remaining, atb_multiplier)
                    return
                member, boundary = next((actor, time) for actor, time in times
                                        if time <= earliest+EPSILON)
                if remaining+EPSILON < boundary:
                    self._advance_gauges(remaining, atb_multiplier)
                    return
                self._advance_gauges(boundary, atb_multiplier)
                remaining = max(0.0, remaining-boundary)
                if member in living:
                    member.atb = 1.0
                    if self.spellblade_guided and member.identifier != 'player':
                        self._start_action(member.identifier, 'guard')
                        continue
                    self._active_actor = member.identifier
                    self.phase = 'ready'
                    self.message = 'Choose an action.'
                    self.events.append({'type': 'player_ready', 'actor': member.identifier})
                    return
                member.atb = 1.0
                self._start_enemy_action(member.identifier)
            elif self.phase == 'acting':
                action = self.current_action
                actor = self.combatant(action.actor)
                if not action.resolved and action.elapsed+EPSILON >= action.impact_at:
                    event_start = len(self.events)
                    self._resolve_action()
                    # Presentation clocks advance by the caller's full frame,
                    # including time left unused at a ready/result boundary.
                    for event in self.events[event_start:]:
                        if (event['type'] in ('impact', 'skill_heal', 'barrier_applied', 'barrier_absorbed')
                                or event['type'] == 'telegraph'
                                and event.get('prepared_action')):
                            event['frame_age'] = remaining
                if action.elapsed+EPSILON >= action.duration:
                    action.elapsed = action.duration
                    self._complete_rig_turn(action)
                    self.last_action, self.current_action = action, None
                    if self._pending_outcome is not None:
                        self._result(self._pending_outcome)
                        return
                    if (action.action == 'aqua_edge_attempt' and self.spellblade_stage == 'second_edge'
                            and self.player.hp):
                        self._start_action('player', 'aether_edge')
                    else:self.phase = 'charging'
                    continue
                boundary = action.duration if action.resolved else action.impact_at
                wait = max(0.0, boundary-action.elapsed)
                if remaining+EPSILON < wait:
                    action.elapsed += remaining
                    return
                action.elapsed = boundary
                remaining = max(0.0, remaining-wait)
