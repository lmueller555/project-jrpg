"""Read-only combat announcements and truthful, persistent wind-up warnings.

The scene feeds model events and advances this presentation clock only while
unpaused. No timers here pause ATB, settle actions, or change combat resources.
"""
from __future__ import annotations

from collections import deque
import math


RESULTS = ('victory', 'defeat', 'fled')


def _text(value):
    return ' '.join(value.split()) if isinstance(value, str) else ''


def _name(model, identifier, display_name=None):
    member = model.combatant(identifier)
    if member is None:return ''
    if display_name is not None and model.is_enemy(identifier):
        return _text(display_name(identifier)) or member.name
    return member.name


def _sequence(model, actor):
    record = model.enemy_record(actor)
    behavior = record.get('behavior') if record is not None else None
    if behavior is not None:return tuple(behavior['sequence'])
    return tuple(model.enemy_definitions[actor]['abilities'])


def basic_attack(model, actor):
    """Resolve each actor's ordinary attack, including guest aliases."""
    if actor == 'player':return 'attack'
    member = model.combatant(actor)
    if member is None:return None
    if actor in model.guest_definitions:return model.guest_definitions[actor]['attack']
    if model.is_enemy(actor):
        record = model.enemy_record(actor)
        behavior = record.get('behavior') if record is not None else None
        if behavior is not None:return behavior['fallback']
        return next((identifier for identifier in _sequence(model, actor)
                     if model.actions[identifier]['kind'] in ('physical', 'magical')
                     and model.actions[identifier]['mp_cost'] == 0), None)
    return 'attack'


def _prepared_after(model, actor, preparation=None):
    prepared = model.enemy_prepared_actions.get(actor)
    if prepared is not None:return prepared
    sequence = _sequence(model, actor)
    for index, identifier in enumerate(sequence):
        if (model.actions[identifier]['kind'] == 'prepare'
                and (preparation is None or identifier == preparation)
                and index + 1 < len(sequence)):
            following = sequence[index+1]
            if model.actions[following]['kind'] in ('physical', 'magical'):
                return following
    return None


def _duration(text):
    # Long emotes remain available in full; the renderer can page wrapped text
    # using age/duration instead of truncating the announcement's content.
    return max(2.5, min(12., len(text) * .07))


def _authored_windup(model, actor):
    record = model.enemy_record(actor) if model.is_enemy(actor) else None
    design = record.get('metadata', {}).get('combat_design') if record is not None else None
    return design['windup']['attack_action'] if design is not None else None


def enemy_charge_warnings(model, display_name=None):
    """Describe actual preparation, held attacks and unresolved releases.

    A preparation is visible from its action start, before the telegraph's
    impact commits its target. Held warnings survive other actors' turns and
    disappear when released, canceled, defeated or the encounter ends.
    """
    if model.phase in RESULTS or not any(member.hp for member in model.party):return ()
    current = model.current_action
    telegraphs = model.enemy_telegraphs
    warnings = []
    for enemy in model.enemies:
        actor = enemy.identifier
        if not enemy.hp:continue
        own = current if current is not None and current.actor == actor else None
        preparing = own is not None and own.kind == 'prepare'
        target = telegraphs.get(actor)
        if not preparing and actor not in model.enemy_prepared_actions and target is None:
            continue
        attack = _prepared_after(model, actor, own.action if preparing else None)
        releasing = own is not None and own.action == attack and not own.resolved
        if own is not None and own.action == attack and own.resolved:continue
        if (attack is not None and not releasing
                and enemy.mp < model.actions[attack]['mp_cost']):continue
        stage = 'prepare' if preparing else 'release' if releasing else 'ready'
        if releasing:target = own.target
        member = model.combatant(target)
        if member is None or not getattr(member, 'hp', 0):target = None
        action_name = model.actions[attack]['name'] if attack is not None else 'Powerful attack'
        source = _name(model, actor, display_name)
        suffix = ' → '+_name(model, target, display_name) if target is not None else ''
        text = source+(' unleashes ' if releasing else ' readies ')+action_name+suffix
        if attack is not None and attack == _authored_windup(model, actor):
            # A solo boss's name is already on its field header. Keep the marked
            # character on the first page even with minimum-size enlarged text.
            text = action_name+suffix
        warnings.append({'text': text, 'kind': 'warning', 'actor': actor,
                         'action': attack, 'action_name': action_name, 'target': target,
                         'stage': stage, 'age': 0., 'duration': _duration(text)})
    return tuple(warnings)


class BattleAnnouncements:
    """Bounded event messages with a persistent authoritative warning fallback."""

    def __init__(self, model, display_name=None):
        self.model, self.display_name = model, display_name
        self._elapsed = 0.
        self._current = None
        self._queue = deque(maxlen=6)
        self._action_token = None
        self._warning_key = None
        self._warning_origin = 0.
        self._showing_warning = False
        self._recovery_key = None
        self._recovery_origin = 0.

    @property
    def warnings(self):return enemy_charge_warnings(self.model, self.display_name)

    def _recovery_notice(self, actor, action=None):
        multiplier = getattr(self.model, 'enemy_recovery_states', {}).get(actor)
        if multiplier is None:return None
        increase = round((multiplier-1)*100)
        return {'text': _name(self.model, actor, self.display_name)
                +' is exhausted — takes '+str(increase)+'% more damage.',
                'kind': 'event', 'actor': actor, 'action': action, 'recovery': True}

    def _prune_recovery(self):
        states = getattr(self.model, 'enemy_recovery_states', {})
        key = tuple(states.items())
        if key != self._recovery_key:
            self._recovery_key, self._recovery_origin = key, self._elapsed
        def valid(message):return not message.get('recovery') or message.get('actor') in states
        if self._current is not None and not valid(self._current):self._current = None
        self._queue = deque((message for message in self._queue if valid(message)), maxlen=6)

    def clear(self):
        self._current = None
        self._queue.clear()
        self._action_token = None
        self._warning_key = None
        self._showing_warning = False
        self._recovery_key = None

    def _ability(self, actor, identifier, name=None):
        if not isinstance(identifier, str) or not isinstance(actor, str):return None
        record = self.model.actions.get(identifier)
        if (record is None or identifier == basic_attack(self.model, actor)
                or record['kind'] in ('guard', 'flee')):return None
        if record['kind'] == 'recover':return self._recovery_notice(actor, identifier)
        label = _text(name) or record['name']
        source = _name(self.model, actor, self.display_name)
        return {'text': source+' — '+label if source else label,
                'kind': 'ability', 'actor': actor, 'action': identifier}

    def _show(self, message, *, replace=False, priority=1, only_empty=False):
        if message is None:return
        message = dict(message)
        message['text'] = _text(message.get('text'))
        if not message['text']:return
        message.update(age=0., duration=_duration(message['text']), priority=priority,
                       created=self._elapsed)
        key = (message['text'], message.get('actor'), message.get('action'), message['kind'])
        if not replace and any((item['text'], item.get('actor'), item.get('action'), item['kind']) == key
                               for item in ([self._current] if self._current is not None else []) + list(self._queue)):
            return
        if priority < 2 and self.warnings:
            if not only_empty:self._queue.append(message)
            return
        if self._current is None or replace:
            self._current = message
        elif not only_empty:
            if priority > self._current['priority']:
                self._current = message
            else:self._queue.append(message)

    def _sync_action(self):
        """Immediate draws after a click precede the scene's next event drain."""
        action = self.model.current_action
        if action is None or self.model.phase != 'acting':return
        if action is self._action_token:return
        self._action_token = action
        self._show(self._ability(action.actor, action.action, action.name), replace=True, priority=2)
        if (self._current is not None and self._current['kind'] == 'ability'
                and self._current.get('actor') == action.actor
                and self._current.get('action') == action.action):
            self._current['duration'] = max(self._current['duration'], action.duration)

    def _next_notice(self):
        self._queue = deque((candidate for candidate in self._queue
                             if self._elapsed-candidate['created'] <= 8.), maxlen=6)
        if self.warnings:return
        while self._queue:
            candidate = self._queue.popleft()
            if self._elapsed-candidate['created'] <= 8.:
                self._current = candidate
                break

    def _defer_for_warning(self):
        if (self._current is not None and self._current['priority'] < 2
                and self.warnings):
            self._queue.appendleft(self._current)
            self._current = None

    def _sync_warning_cycle(self):
        warnings = self.warnings
        key = tuple((item['actor'], item['action'], item['target'], item['stage'])
                    for item in warnings) if warnings else None
        if key != self._warning_key:
            self._warning_key, self._warning_origin = key, self._elapsed
        self._showing_warning = bool(warnings)
        return warnings

    @property
    def current(self):
        if self.model.phase in RESULTS:
            self.clear()
            return None
        self._prune_recovery()
        self._sync_action()
        warnings = self._sync_warning_cycle()
        self._defer_for_warning()
        if self._current is not None:
            source = self.model.combatant(self._current.get('actor'))
            if (source is not None and self.model.is_enemy(source.identifier) and not source.hp):
                self._current = None
            else:return dict(self._current)
        self._next_notice()
        if self._current is not None:
            return dict(self._current)
        if not warnings:
            for enemy in self.model.enemies:
                notice = self._recovery_notice(enemy.identifier)
                if enemy.hp and notice is not None:
                    duration = _duration(notice['text'])
                    return dict(notice, age=(self._elapsed-self._recovery_origin) % duration,
                                duration=duration)
            return None
        period = sum(item['duration'] for item in warnings)
        age = (self._elapsed-self._warning_origin) % period
        for warning in warnings:
            if age < warning['duration']:
                return dict(warning, age=age)
            age -= warning['duration']
        return dict(warnings[-1], age=0.)

    def consume(self, event):
        if not isinstance(event, dict):return
        kind = event.get('type')
        actor = event.get('actor')
        if kind == 'result':
            self.clear()
            return
        if self.model.phase in RESULTS:return
        if kind == 'action_started':
            action = self.model.current_action
            if (action is not None and action.actor == actor and action.action == event.get('action')):
                self._sync_action()
            else:self._show(self._ability(actor, event.get('action'), event.get('name')),
                            replace=True, priority=2)
            return
        if (kind == 'telegraph' and event.get('prepared_action') is not None
                and event.get('prepared_action') == _authored_windup(self.model, actor)):
            # The marked character must be visible as soon as the model commits
            # or changes the warning, including during Gather's follow-through.
            self._current = None
            self._action_token = self.model.current_action
            return
        name = _name(self.model, actor, self.display_name)
        message = None
        if kind == 'recovery_started':
            message = self._recovery_notice(actor, event.get('action'))
            # The hit has landed: make its opening visible during followthrough
            # rather than leaving the completed strike's title over the window.
            self._show(message, replace=True, priority=2)
            return
        elif kind == 'recovery_ended':
            self._prune_recovery()
            return
        elif kind in ('event', 'emote', 'narration', 'special_event'):
            text = _text(event.get('text'))
            if text:
                message = {'text': (name+' — ' if kind == 'emote' and name else '')+text,
                           'kind': 'event', 'actor': actor}
        elif kind == 'spellblade_failed':
            record = self.model.actions.get(event.get('action'), {})
            message = {'text': name+"'s "+record.get('name', 'elemental focus')+' fails!',
                       'kind': 'event', 'actor': actor}
        elif kind == 'spellblade_discovered':
            message = {'text': name+' discovers Aether Edge!', 'kind': 'event', 'actor': actor}
        elif kind == 'aqua_edge_discovered':
            message = {'text': name+' learns Aqua Edge!', 'kind': 'event', 'actor': actor}
        elif kind == 'barrier_applied':
            target = _name(self.model, event.get('target'), self.display_name)
            message = {'text': target+' gains a barrier ('+str(event.get('amount', 0))+' HP).',
                       'kind': 'event', 'actor': actor}
        elif kind == 'barrier_expired':
            if event.get('reason') in ('ko', 'result', 'battle_end'):return
            target = _name(self.model, event.get('target', actor), self.display_name)
            message = {'text': target+"'s barrier "+('breaks.' if event.get('reason') in ('broken', 'depleted') else 'ends.'),
                       'kind': 'event', 'actor': actor}
        elif kind == 'guard':
            self._show({'text': name+' uses Guard.', 'kind': 'event', 'actor': actor}, only_empty=True)
            return
        if message is not None:self._show(message, priority=1)

    def update(self, seconds):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Announcement time must be finite and nonnegative')
        if self.model.phase in RESULTS:
            self.clear()
            return
        self._elapsed += seconds
        self._prune_recovery()
        self._sync_action()
        self._sync_warning_cycle()
        self._defer_for_warning()
        if self._current is None:self._next_notice()
        remaining = seconds
        while self._current is not None:
            portion = min(remaining, self._current['duration']-self._current['age'])
            self._current['age'] += portion
            remaining -= portion
            if self._current['age'] < self._current['duration']-1e-9:break
            self._current = None
            self._next_notice()
            if remaining <= 0:break
