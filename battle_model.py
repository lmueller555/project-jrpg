"""Deterministic wait-ATB battle rules, independent of rendering and saves.

Gauge fill is 0.12 + 0.004 * Speed per charging second. Every gauge pauses at
the exact player-ready boundary and throughout action animations or results.
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
                or action['kind'] not in ('physical', 'magical', 'guard', 'flee')
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
              or action['target'] != ('self' if action['kind'] == 'guard' else 'none')):
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
                       or actions[key]['kind'] not in ('physical', 'magical')
                       for key in enemy['abilities'])
                or len(enemy['abilities']) != len(set(enemy['abilities']))):
            raise ValueError('Invalid enemy definition')
        if not any(actions[key]['mp_cost'] == 0 for key in enemy['abilities']):
            raise ValueError('Enemy requires a free fallback action')
        rewards = enemy['rewards']
        if (not isinstance(rewards, dict) or set(rewards) != {'rp', 'drops'}
                or not _integer(rewards['rp']) or not isinstance(rewards['drops'], dict)
                or any(not isinstance(key, str) or not key or not _integer(value, 1, 999999)
                       for key, value in rewards['drops'].items())):
            raise ValueError('Invalid enemy reward')
    return deepcopy(data['enemies'])


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
    """One player against one test enemy, with player-first simultaneous readiness."""

    def __init__(self, player_attributes, learned_abilities=(), rng=None, enemy_id='bat',
                 *, action_data=None, enemy_data=None):
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
        self.enemy_id = enemy_id
        self.enemy_definition = deepcopy(enemies[enemy_id])
        enemy = self.enemy_definition
        self.enemy = Combatant('enemy', enemy['name'], dict(enemy['attributes']),
                               enemy['attributes']['hp'], enemy['attributes']['mp'])
        self.learned_abilities = frozenset(learned_abilities)
        self.rng = random.Random() if rng is None else rng
        if not callable(getattr(self.rng, 'randint', None)):
            raise TypeError('Battle RNG must expose randint')
        self.phase = 'charging' if self.player.hp else 'defeat'
        self.current_action = self.last_action = None
        self.events = []
        self.message = 'A Bat approaches!' if enemy_id == 'bat' else self.enemy.name+' approaches!'
        self._pending_outcome = None
        self._enemy_action_index = 0
        if self.phase == 'defeat':self._result('defeat')

    @property
    def waiting_for_player(self):return self.phase == 'ready'

    @property
    def ended(self):return self.phase in RESULT_PHASES

    @staticmethod
    def atb_rate(combatant):return .12+.004*combatant.value('speed')

    def available_actions(self):
        return list(PLAYER_ACTIONS)+[key for key in SUPPORTED_LEARNED_ACTIONS
                                    if key in self.learned_abilities]

    def action_reason(self, identifier):
        if not isinstance(identifier, str) or identifier not in self.available_actions():
            return 'This action is not available.'
        if self.phase != 'ready':return 'Caelan is not ready.'
        if self.player.mp < self.actions[identifier]['mp_cost']:return 'Not enough MP.'
        return ''

    def choose_action(self, identifier):
        if self.action_reason(identifier):return False
        self._start_action('player', identifier)
        return True

    def drain_events(self):
        result, self.events = self.events, []
        return result

    def _start_action(self, actor_id, identifier):
        actor = self.player if actor_id == 'player' else self.enemy
        record = self.actions[identifier]
        actor.mp -= record['mp_cost']
        actor.atb = 0.0
        target = ('enemy' if actor_id == 'player' else 'player')
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
            identifier = next(key for key in choices if self.actions[key]['mp_cost'] == 0)
        self._start_action('enemy', identifier)

    def _resolve_action(self):
        action = self.current_action
        actor = self.player if action.actor == 'player' else self.enemy
        if action.kind == 'guard':
            actor.guarded = True
            self.message = actor.name+' braces for the next attack.'
            self.events.append({'type': 'guard', 'actor': action.actor})
        elif action.kind == 'flee':
            self._pending_outcome = 'fled'
            self.message = actor.name+' gets away safely.'
        else:
            target = self.player if action.target == 'player' else self.enemy
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
            if not target.hp:
                self._pending_outcome = 'defeat' if action.target == 'player' else 'victory'
        action.resolved = True

    def _result(self, outcome):
        self.phase = outcome
        self.message = {'victory': 'Victory!', 'defeat': 'Caelan has fallen.',
                        'fled': 'Escaped safely.'}[outcome]
        self.events.append({'type': 'result', 'outcome': outcome})

    def _advance_gauges(self, seconds):
        for combatant in (self.player, self.enemy):
            combatant.atb = min(1.0, combatant.atb+self.atb_rate(combatant)*seconds)

    def update(self, seconds):
        """Consume time through exact gauge/impact boundaries; choice time is free."""
        if type(seconds) not in (int, float):raise TypeError('Battle time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid battle time')
        remaining = float(seconds)
        while True:
            if self.ended or self.waiting_for_player:return
            if self.phase == 'charging':
                player_time = max(0.0, (1-self.player.atb)/self.atb_rate(self.player))
                enemy_time = max(0.0, (1-self.enemy.atb)/self.atb_rate(self.enemy))
                player_first = player_time <= enemy_time+EPSILON
                boundary = player_time if player_first else enemy_time
                if remaining+EPSILON < boundary:
                    self._advance_gauges(remaining)
                    return
                self._advance_gauges(boundary)
                remaining = max(0.0, remaining-boundary)
                if player_first:
                    self.player.atb = 1.0
                    self.phase = 'ready'
                    self.message = 'Choose an action.'
                    self.events.append({'type': 'player_ready'})
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
