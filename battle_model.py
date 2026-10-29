"""Deterministic wait-ATB battle rules, independent of rendering and saves.

Gauge fill is 0.12 + 0.004 * Speed per charging second. Every gauge pauses at
the exact party-ready boundary and throughout action animations or results.
Only this battle's copied resources change; the owning game settles outcomes.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random

from character_attributes import ATTRIBUTE_IDS, ATTRIBUTE_CAPS
from combat_damage import magical_damage, physical_damage, roll_variance


ROOT = Path(__file__).resolve().parent
ACTION_PATH = ROOT/'assets/combat/actions.json'
ENEMY_PATH = ROOT/'assets/combat/enemies.json'
GUEST_PATH = ROOT/'assets/combat/guests.json'
RESULT_PHASES = frozenset(('victory', 'defeat', 'fled'))
PLAYER_ACTIONS = ('attack', 'guard', 'flee')
SUPPORTED_LEARNED_ACTIONS = ('aether_dart',)
EPSILON = 1e-10
MAX_ENEMY_RESOURCE = 999999999


def _integer(value, minimum=0, maximum=MAX_ENEMY_RESOURCE):
    return type(value) is int and minimum <= value <= maximum


def _number(value, minimum=0, maximum=1000000):
    return (type(value) in (int, float) and math.isfinite(value)
            and minimum <= value <= maximum)


def load_actions(data=None):
    """Validate and copy the initial battle's supported action catalog."""
    if data is None:data = json.loads(ACTION_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'actions'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['actions'], dict) or not data['actions']):
        raise ValueError('Invalid battle action catalog')
    fields = {'name', 'kind', 'potency', 'mp_cost', 'duration', 'impact_at', 'animation', 'target'}
    for identifier, action in data['actions'].items():
        if (not isinstance(identifier, str) or not identifier
                or not isinstance(action, dict) or set(action) != fields
                or any(not isinstance(action[key], str) or not action[key].strip()
                       for key in ('name', 'animation'))
                or action['kind'] not in ('physical', 'magical', 'guard', 'flee', 'prepare')
                or action['target'] not in ('opponent', 'self', 'none')
                or not _integer(action['mp_cost'], maximum=999999)
                or not _number(action['duration'], .001, 10)
                or not _number(action['impact_at'], 0, action['duration'])
                or not _number(action['potency'])):
            raise ValueError('Invalid battle action')
        if action['kind'] in ('physical', 'magical'):
            if action['potency'] <= 0 or action['target'] != 'opponent':
                raise ValueError('Invalid damaging action')
        elif (action['potency'] != 0 or action['mp_cost'] != 0
              or action['target'] != ('self' if action['kind'] in ('guard', 'prepare') else 'none')):
            raise ValueError('Invalid utility action')
    if not set(PLAYER_ACTIONS+SUPPORTED_LEARNED_ACTIONS) <= set(data['actions']):
        raise ValueError('Missing player battle action')
    return deepcopy(data['actions'])


def load_enemies(actions, data=None):
    """Enemy HP/MP use structural bounds, independently of party resource caps."""
    if data is None:data = json.loads(ENEMY_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'version', 'enemies'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['enemies'], dict) or not data['enemies']):
        raise ValueError('Invalid enemy catalog')
    for identifier, enemy in data['enemies'].items():
        if (not isinstance(identifier, str) or not identifier or not isinstance(enemy, dict)
                or set(enemy) != {'name', 'attributes', 'abilities', 'rewards'}
                or not isinstance(enemy['name'], str) or not enemy['name'].strip()
                or not isinstance(enemy['attributes'], dict)
                or set(enemy['attributes']) != set(ATTRIBUTE_IDS)
                or any(not _integer(value, 1 if key == 'hp' else 0,
                                    MAX_ENEMY_RESOURCE if key in ('hp', 'mp') else 255)
                       for key, value in enemy['attributes'].items())
                or not isinstance(enemy['abilities'], list) or not enemy['abilities']
                or any(not isinstance(key, str) or key not in actions
                       or actions[key]['kind'] not in ('physical', 'magical', 'prepare')
                       for key in enemy['abilities'])
                or len(enemy['abilities']) != len(set(enemy['abilities']))):
            raise ValueError('Invalid enemy definition')
        if not any(actions[key]['mp_cost'] == 0 and
                   actions[key]['kind'] in ('physical', 'magical')
                   for key in enemy['abilities']):
            raise ValueError('Enemy requires a free fallback action')
        rewards = enemy['rewards']
        if (not isinstance(rewards, dict) or set(rewards) != {'rp', 'drops'}
                or not _integer(rewards['rp']) or not isinstance(rewards['drops'], dict)
                or any(not isinstance(key, str) or not key or not _integer(value, 1, 999999)
                       for key, value in rewards['drops'].items())):
            raise ValueError('Invalid enemy reward')
    return deepcopy(data['enemies'])


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


@dataclass
class Combatant:
    identifier: str
    name: str
    attributes: dict
    hp: int
    mp: int
    atb: float = 0.0
    guarded: bool = False

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


class BattleModel:
    """Player-commanded party against one enemy, with party-first readiness ties.

    ``player`` remains Caelan for save settlement and existing callers. Commands
    default to ``active_player``; any living, full-gauge member can be selected
    while the model waits. Guest resources belong only to this encounter.
    """

    def __init__(self, player_attributes, learned_abilities=(), rng=None, enemy_id='bat',
                 *, guest_id=None, action_data=None, enemy_data=None, guest_data=None):
        self.actions = load_actions(action_data)
        enemies = load_enemies(self.actions, enemy_data)
        if not isinstance(enemy_id, str) or enemy_id not in enemies:
            raise ValueError('Unknown battle enemy')
        if (not isinstance(learned_abilities, (tuple, list, set, frozenset))
                or any(not isinstance(identifier, str) for identifier in learned_abilities)):
            raise ValueError('Invalid learned abilities')
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
        if guest_id is not None:
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
        self._active_actor = 'player'
        self.enemy_id = enemy_id
        self.enemy_definition = deepcopy(enemies[enemy_id])
        enemy = self.enemy_definition
        self.enemy = Combatant('enemy', enemy['name'], dict(enemy['attributes']),
                               enemy['attributes']['hp'], enemy['attributes']['mp'])
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
        if self.phase == 'defeat':self._result('defeat')

    @property
    def waiting_for_player(self):return self.phase == 'ready'

    @property
    def ended(self):return self.phase in RESULT_PHASES

    @staticmethod
    def atb_rate(combatant):return .12+.004*combatant.value('speed')

    def combatant(self, identifier):
        if identifier == 'enemy':return self.enemy
        return next((member for member in self.party if member.identifier == identifier), None)

    @property
    def active_player(self):
        return self.combatant(self._active_actor)

    @property
    def ready_actor(self):
        return self._active_actor if self.waiting_for_player else None

    @property
    def ready_members(self):
        return tuple(member.identifier for member in self.party
                     if member.hp and member.atb+EPSILON >= 1)

    def select_ready(self, identifier):
        if (not self.waiting_for_player or not isinstance(identifier, str)
                or identifier not in self.ready_members):return False
        self._active_actor = identifier
        return True

    def _party_actor(self, actor_id=None):
        if actor_id is None:actor_id = self._active_actor
        return next((member for member in self.party if member.identifier == actor_id), None)

    def available_actions(self, actor_id=None):
        actor = self._party_actor(actor_id)
        if actor is None:return []
        if actor.identifier != 'player':return list(PLAYER_ACTIONS)
        return list(PLAYER_ACTIONS)+[key for key in SUPPORTED_LEARNED_ACTIONS
                                    if key in self.learned_abilities]

    def _action_id(self, command, actor):
        if command == 'attack' and actor.identifier in self.guest_definitions:
            return self.guest_definitions[actor.identifier]['attack']
        return command

    def action_reason(self, identifier, actor_id=None):
        actor = self._party_actor(actor_id)
        if (actor is None or not isinstance(identifier, str)
                or identifier not in self.available_actions(actor.identifier)):
            return 'This action is not available.'
        if (self.phase != 'ready' or not actor.hp
                or actor.atb+EPSILON < 1):return actor.name+' is not ready.'
        if actor.mp < self.actions[self._action_id(identifier, actor)]['mp_cost']:
            return 'Not enough MP.'
        return ''

    def choose_action(self, identifier, actor_id=None):
        if self.action_reason(identifier, actor_id):return False
        actor = self._party_actor(actor_id)
        self._active_actor = actor.identifier
        self._start_action(actor.identifier, self._action_id(identifier, actor))
        return True

    def drain_events(self):
        result, self.events = self.events, []
        return result

    def _enemy_target(self, identifier):
        living = [member for member in self.party if member.hp]
        if not living:return None
        if identifier == 'tusker_charge' and self.telegraphed_target:
            target = self.combatant(self.telegraphed_target)
            if target is not None and target.hp:return target.identifier
        if self.enemy_id == 'ridgeback_tusker' and identifier == 'tusk_strike':
            mira = self.combatant('mira')
            if mira is not None and mira.hp:return 'mira'
        return living[0].identifier

    def _start_action(self, actor_id, identifier):
        actor = self.combatant(actor_id)
        record = self.actions[identifier]
        actor.mp -= record['mp_cost']
        actor.atb = 0.0
        target = 'enemy' if actor_id != 'enemy' else self._enemy_target(identifier)
        if record['target'] == 'self':target = actor_id
        elif record['target'] == 'none':target = None
        self.current_action = BattleAction(actor_id, identifier, target, record['name'],
                                          record['kind'], record['animation'],
                                          record['duration'], record['impact_at'])
        self.phase = 'acting'
        self.message = actor.name+' uses '+record['name']+'.'
        self.events.append({'type': 'action_started', 'actor': actor_id,
                            'action': identifier, 'target': target, 'name': record['name']})

    def _start_enemy_action(self):
        choices = self.enemy_definition['abilities']
        identifier = choices[self._enemy_action_index % len(choices)]
        self._enemy_action_index += 1
        if self.enemy.mp < self.actions[identifier]['mp_cost']:
            identifier = next(key for key in choices if self.actions[key]['mp_cost'] == 0
                              and self.actions[key]['kind'] in ('physical', 'magical'))
        self._start_action('enemy', identifier)

    def _resolve_action(self):
        action = self.current_action
        actor = self.combatant(action.actor)
        if action.kind == 'guard':
            actor.guarded = True
            self.message = actor.name+' braces for the next attack.'
            self.events.append({'type': 'guard', 'actor': action.actor})
        elif action.kind == 'flee':
            self._pending_outcome = 'fled'
            self.message = actor.name+' gets away safely.'
        elif action.kind == 'prepare':
            target = self._enemy_target('tusker_charge')
            self.telegraphed_target = target
            member = self.combatant(target)
            self.message = actor.name+' lowers its head toward '+member.name+'.'
            self.events.append({'type': 'telegraph', 'actor': action.actor,
                                'action': action.action, 'target': target})
        else:
            target = self.combatant(action.target)
            protected = target.guarded
            calculator = physical_damage if action.kind == 'physical' else magical_damage
            action.damage = calculator(actor, target, self.actions[action.action]['potency'],
                                       protected=protected, variance_percent=roll_variance(self.rng))
            target.hp = max(0, target.hp-action.damage)
            target.guarded = False
            self.message = target.name+' takes '+str(action.damage)+' damage.'
            self.events.append({'type': 'impact', 'actor': action.actor, 'action': action.action,
                                'target': action.target, 'damage': action.damage,
                                'remaining_hp': target.hp, 'guarded': protected})
            if action.action == 'tusker_charge':self.telegraphed_target = None
            if not target.hp:
                target.atb = 0.0
                if action.target == 'enemy':self._pending_outcome = 'victory'
                elif not any(member.hp for member in self.party):self._pending_outcome = 'defeat'
        action.resolved = True

    def _result(self, outcome):
        self.phase = outcome
        defeat = ('The party has fallen.' if len(self.party) > 1
                  else self.player.name+' has fallen.')
        self.message = {'victory': 'Victory!', 'defeat': defeat,
                        'fled': 'Escaped safely.'}[outcome]
        self.events.append({'type': 'result', 'outcome': outcome})

    def _advance_gauges(self, seconds):
        for combatant in (*self.party, self.enemy):
            if combatant.hp:
                combatant.atb = min(1.0, combatant.atb+self.atb_rate(combatant)*seconds)

    def update(self, seconds):
        """Consume time through exact gauge/impact boundaries; choice time is free."""
        if type(seconds) not in (int, float):raise TypeError('Battle time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid battle time')
        remaining = float(seconds)
        while True:
            if self.ended or self.waiting_for_player:return
            if self.phase == 'charging':
                living = [member for member in self.party if member.hp]
                if not living:
                    self._result('defeat')
                    return
                member = min(living, key=lambda actor: max(0.0, (1-actor.atb)/self.atb_rate(actor)))
                player_time = max(0.0, (1-member.atb)/self.atb_rate(member))
                enemy_time = max(0.0, (1-self.enemy.atb)/self.atb_rate(self.enemy))
                player_first = player_time <= enemy_time+EPSILON
                boundary = player_time if player_first else enemy_time
                if remaining+EPSILON < boundary:
                    self._advance_gauges(remaining)
                    return
                self._advance_gauges(boundary)
                remaining = max(0.0, remaining-boundary)
                if player_first:
                    member.atb = 1.0
                    self._active_actor = member.identifier
                    self.phase = 'ready'
                    self.message = 'Choose an action.'
                    self.events.append({'type': 'player_ready', 'actor': member.identifier})
                    return
                self.enemy.atb = 1.0
                self._start_enemy_action()
            elif self.phase == 'acting':
                action = self.current_action
                if not action.resolved and action.elapsed+EPSILON >= action.impact_at:
                    self._resolve_action()
                if action.elapsed+EPSILON >= action.duration:
                    action.elapsed = action.duration
                    self.last_action, self.current_action = action, None
                    if self._pending_outcome is not None:
                        self._result(self._pending_outcome)
                        return
                    self.phase = 'charging'
                    continue
                boundary = action.duration if action.resolved else action.impact_at
                wait = max(0.0, boundary-action.elapsed)
                if remaining+EPSILON < wait:
                    action.elapsed += remaining
                    return
                action.elapsed = boundary
                remaining = max(0.0, remaining-wait)
