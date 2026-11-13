"""One-time Echo Chamber encounter ownership, separate from MQ03 and random fights."""
from __future__ import annotations

from copy import deepcopy
import math
import random

import pygame

from social import clear_sight


SCENE_ID = 'sanctuary_cave'
BATTLEFIELD = 'cave_echo_chamber'
RECEIPT = 'boss:vespermaw'
APPROACH = (1940, 492)
RETREAT = (1810, 600)
TRIGGER = (1760, 96, 600, 392)
KNOWN_IDS = ('caelan', 'mira', 'lucan', 'rhea', 'edran')
TICKET_FIELDS = {'version', 'enemy_id', 'level', 'receipt', 'scene', 'position',
                 'facing', 'battlefield', 'combat_seed', 'party_active', 'party_resources'}


def _point(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(type(n) in (int, float) and abs(n) < 1e7 and math.isfinite(n) for n in value))


def _near(point):
    return (pygame.Rect(TRIGGER).collidepoint(point)
            or pygame.Vector2(point).distance_squared_to(APPROACH) <= 44**2)


def valid_ticket(ticket):
    if (not isinstance(ticket, dict) or set(ticket) != TICKET_FIELDS
            or type(ticket['version']) is not int or ticket['version'] != 1
            or ticket['enemy_id'] != 'vespermaw'
            or type(ticket['level']) is not int or ticket['level'] != 7
            or ticket['receipt'] != RECEIPT or ticket['scene'] != SCENE_ID
            or ticket['battlefield'] != BATTLEFIELD
            or not isinstance(ticket['position'], list) or not _point(ticket['position'])
            or not _near(ticket['position'])
            or ticket['facing'] not in ('front', 'back', 'left', 'right')
            or type(ticket['combat_seed']) is not int or not 0 <= ticket['combat_seed'] < 2**63
            or not isinstance(ticket['party_active'], list)):
        return False
    active, resources = ticket['party_active'], ticket['party_resources']
    if (not 1 <= len(active) <= 3 or active[0] != 'caelan'
            or any(not isinstance(key, str) or key not in KNOWN_IDS for key in active)
            or len(set(active)) != len(active)
            or not isinstance(resources, dict) or set(resources) != set(active)):
        return False
    for values in resources.values():
        if (not isinstance(values, dict) or set(values) != {'hp', 'mp'}
                or type(values['hp']) is not int or not 0 <= values['hp'] <= 9999
                or type(values['mp']) is not int or not 0 <= values['mp'] <= 999):return False
    return any(values['hp'] for values in resources.values())


class SanctuaryBoss:
    def __init__(self, game):
        self.game = game
        self.defeated = self.intro_seen = False
        self._pending = None
        self._armed = True
        self._defeat_choice = False

    @property
    def pending(self):return deepcopy(self._pending)

    @property
    def active(self):return self.game.world.data.get('id') == SCENE_ID

    @property
    def locks_player(self):
        return self._pending is not None and not self.game.combat.active

    @staticmethod
    def valid_snapshot(record):
        return (isinstance(record, dict)
                and set(record) == {'version', 'defeated', 'intro_seen', 'pending'}
                and type(record['version']) is int and record['version'] == 1
                and type(record['defeated']) is bool and type(record['intro_seen']) is bool
                and (not record['defeated'] or record['intro_seen'])
                and (record['pending'] is None or valid_ticket(record['pending'])))

    @classmethod
    def valid_journey(cls, data):
        try:return cls._valid_journey(data)
        except (KeyError, TypeError, AttributeError, ValueError):return False

    @classmethod
    def _valid_journey(cls, data):
        if not isinstance(data, dict):return False
        state = data.get('sanctuary_boss')
        post = data.get('post_battle')
        boss_post = isinstance(post, dict) and post.get('kind') == 'cave_boss'
        receipts = data.get('battle_rewards', {}).get('receipts', [])
        if state is None:return not boss_post and RECEIPT not in receipts
        if not cls.valid_snapshot(state):return False
        if (RECEIPT in receipts) != state['defeated']:return False
        ticket = state['pending']
        if ticket is None:return not boss_post
        if state['defeated'] and not (boss_post and post.get('stage') == 'awarded'):return False
        if post is not None and not boss_post:return False
        if data.get('cave_random_encounters', {}).get('pending') is not None:return False
        player = data.get('player', {})
        if (player.get('scene') != SCENE_ID or player.get('position') != ticket['position']
                or player.get('facing') != ticket['facing']):return False
        party = data.get('party', {})
        if party.get('active') != ticket['party_active']:return False
        if boss_post:
            return (post.get('encounter') == ticket
                    and post.get('party_before') == ticket['party_resources']
                    and state['defeated'] == (post.get('stage') == 'awarded'))
        for key, values in ticket['party_resources'].items():
            saved = party.get('characters', {}).get(key, {})
            if (saved.get('current_hp'), saved.get('current_mp')) != (values['hp'], values['mp']):return False
        return True

    def to_dict(self):
        return {'version': 1, 'defeated': self.defeated,
                'intro_seen': self.intro_seen, 'pending': self.pending}

    def restore(self, record=None):
        if record is not None and not self.valid_snapshot(record):return False
        record = record or {'defeated': False, 'intro_seen': False, 'pending': None}
        self.defeated, self.intro_seen = record['defeated'], record['intro_seen']
        self._pending = deepcopy(record['pending'])
        self._armed = True
        self._defeat_choice = False
        return True

    def mark_defeated(self, receipt):
        if receipt != RECEIPT or self._pending is None or self.defeated:return False
        self.defeated = self.intro_seen = True
        return True

    def finish(self, receipt):
        if receipt != RECEIPT or self._pending is None or not self.defeated:return False
        self._pending = None
        self._defeat_choice = False
        self._armed = False
        return True

    def _available(self):
        g = self.game
        return (self.active and not g.on_title and not g.combat.active
                and not g.opening_cinematic.active and not g.social.active
                and not g.social.locked and not g.household_action
                and not g.opening.locks_player and not g.transfer_cooldown and not g.opening_fade
                and not g.map_open and not g.quest_ui.journal_open
                and getattr(g, '_music_focused', True)
                and not any(getattr(getattr(g, key, None), 'is_open', False)
                            for key in ('pause', 'inventory_ui', 'world_map_viewer', 'party_ui', 'status_ui')))

    def nearby(self):
        if not self._available() or self.defeated or self._pending is not None:return False
        g = self.game
        return (_near(g.player.position) and g.world.can_stand(g.player.position)
                and clear_sight(g.world, g.player.position, (2000, 420)))

    def interaction_hint(self):return 'E: approach the Echo Chamber' if self.nearby() else ''

    def interact(self):return self.offer()

    def offer(self, error=None):
        if not self.nearby():return False
        self.game.player.moving = self.game.player.running = False
        opened = self.game.social.start_choice(
            [{'speaker': 'caelan', 'text': 'That growl… It is coming from the chamber.'}],
            [{'text': 'Enter', 'action': 'enter'}, {'text': 'Party', 'action': 'party'},
             {'text': 'Step back', 'action': 'leave'}], self._choose,
            identifier='sanctuary_boss_offer', prompt=error or 'Enter the Echo Chamber?')
        if opened:self._armed = False
        return opened

    def _choose(self, action):
        if not self.nearby():return
        g = self.game
        if action == 'party':
            g.party_ui.open(prompt='Prepare for the Echo Chamber',
                            on_confirm=self.offer, on_cancel=self.offer)
        elif action == 'leave':
            self._move(APPROACH)
            self._checkpoint()
        elif action == 'enter':
            reason = g.party.battle_reason()
            if reason:
                self.offer(reason)
                return
            if g.cave_random_encounters.pending is not None:
                self.offer('Finish the current encounter first.')
                return
            rescue = getattr(g, 'sanctuary_rescue', None)
            if rescue is not None:
                rescue.start_before(self._begin_battle)
            else:
                self._begin_battle()

    def _begin_battle(self):
        """Commit the ticket only after the acknowledged rescue confrontation."""
        g = self.game
        if (self.defeated or self._pending is not None or g.combat.active
                or g.party.battle_reason() or g.cave_random_encounters.pending is not None):
            return False
        ticket = {'version': 1, 'enemy_id': 'vespermaw', 'level': 7,
                  'receipt': RECEIPT, 'scene': SCENE_ID,
                  'position': list(g.player.position), 'facing': g.player.facing,
                  'battlefield': BATTLEFIELD, 'combat_seed': random.SystemRandom().randrange(2**63),
                  'party_active': list(g.party.active_ids),
                  'party_resources': {key: {'hp': g.party.characters[key].current_hp,
                                            'mp': g.party.characters[key].current_mp}
                                      for key in g.party.active_ids}}
        if not valid_ticket(ticket):return
        self._pending = ticket
        if not g.combat.start_boss(ticket):
            self._pending = None
            self.offer('The battle could not be started. Try again.')
            return False
        return True

    def _checkpoint(self):
        return not self.game.save_store.enabled or self.game.save_progress()

    def _move(self, point):
        g = self.game
        landing = g.overworld_travel._landing(g.world, point)
        if landing is None:return False
        g.player.position.update(landing)
        g.player.moving = g.player.running = False
        g.player.walk_ms = 0.
        g.party_travel.reset()
        g.camera.reset()
        return True

    def battle_defeated(self, ticket):
        if self._pending != ticket or self.defeated:return False
        self._defeat_choice = True
        self._show_defeat()
        return True

    def _show_defeat(self, error=None):
        if not self._available() or self._pending is None:return False
        return self.game.social.start_choice(
            [{'speaker': 'caelan', 'text': 'We need to regroup.'}],
            [{'text': 'Retry', 'action': 'retry'}, {'text': 'Return to the Quiet Shelf', 'action': 'return'}],
            self._choose_defeat, identifier='sanctuary_boss_defeat',
            prompt=error or 'Try again or return to the passage?')

    def _choose_defeat(self, action):
        if not self._available() or self._pending is None or self.defeated:return
        if action == 'retry':
            if not self.game.combat.start_boss(self.pending, restoring=True):
                self._show_defeat('The battle could not be restarted. Try again.')
            else:self._defeat_choice = False
        elif action == 'return':
            g = self.game
            before = self.to_dict()
            position, facing = tuple(g.player.position), g.player.facing
            self._pending = None
            self._defeat_choice = False
            if not self._move(RETREAT) or not self._checkpoint():
                self.restore(before)
                g.player.position.update(position)
                g.player.facing = facing
                g.party_travel.reset()
                g.camera.reset()
                self._defeat_choice = True
                self._show_defeat('Progress could not be saved. Try again.')
            else:self._armed = False

    def make_entry(self, world_frame, focus, *, restoring=False):
        from sanctuary_boss_entry import SanctuaryBossEntry
        return SanctuaryBossEntry(world_frame, focus, intro_seen=self.intro_seen,
                                  reduced_motion=self.game.audio.reduced_motion,
                                  audio_settings=self.game.audio)

    def entry_loaded(self):
        self.intro_seen = True
        return True

    def update(self, seconds=0):
        if not self.active:return
        if self._defeat_choice and self._pending is not None:
            return self._show_defeat()
        if not self._available() or self._pending is not None or self.defeated:return
        inside = pygame.Rect(TRIGGER).collidepoint(self.game.player.position)
        if not inside:self._armed = True
        if inside and self._armed:return self.offer()
        return False
