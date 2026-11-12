"""Optional cave Aether guardians and their once-only focus acquisitions.

The registry gives each guardian its own arena, receipt and focus. Battle
settlement owns rewards and resources; this owner retains encounter choices,
entry checkpoints and the acknowledged acquisition presentation.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import random

import pygame

from social import clear_sight


SCENE_ID = 'sanctuary_cave'
SAVE_KEY = 'elemental_bosses'
KNOWN_IDS = ('caelan', 'mira', 'lucan', 'rhea', 'edran')
REGISTRY = {
    'embravyr': {
        'name': 'Embravyr', 'element': 'fire', 'level': 4,
        'receipt': 'boss:embravyr', 'battlefield': 'cave_embervein',
        'room': 'embervein_chamber', 'location': 'Embervein Chamber',
        'gem': 'fire', 'skill': 'flame_edge', 'item': 'red_focus_gem',
        'gem_name': 'Red Focus Gem', 'skill_name': 'Flame Edge',
    },
    'nivareth': {
        'name': 'Nivareth', 'element': 'ice', 'level': 4,
        'receipt': 'boss:nivareth', 'battlefield': 'cave_stillfrost',
        'room': 'stillfrost_chamber', 'location': 'Stillfrost Chamber',
        'gem': 'ice', 'skill': 'ice_edge', 'item': 'white_focus_gem',
        'gem_name': 'White Focus Gem', 'skill_name': 'Ice Edge',
    },
}
# Geometry belongs to the level builder. The encounter registry contributes
# rewards/presentation without maintaining a second set of chamber coordinates.
_MAP = Path(__file__).parent/'assets/maps/sanctuary_cave/map.json'
_ARENAS = json.loads(_MAP.read_text(encoding='utf-8'))['cave']['elemental_arenas']
if ({entry['enemy_id'] for entry in _ARENAS} != set(REGISTRY)
        or len(_ARENAS) != len(REGISTRY)):
    raise ValueError('The elemental guardian arenas must match their registry')
for _arena in _ARENAS:
    _entry = REGISTRY[_arena['enemy_id']]
    if any(_arena[key] != _entry[key] for key in ('level', 'room', 'battlefield')):
        raise ValueError('The elemental guardian arena definition is inconsistent')
    for _key in ('center', 'approach', 'retreat', 'trigger'):
        _entry[_key] = tuple(_arena[_key])
TICKET_FIELDS = {'version', 'enemy_id', 'level', 'receipt', 'scene', 'position',
                 'facing', 'battlefield', 'combat_seed', 'party_active', 'party_resources'}
STATE_FIELDS = {'discovered', 'intro_seen', 'defeated', 'pending_acquisition'}


def definition(enemy_id):
    """Return detached authored data; unknown IDs never fall back to a boss."""
    return deepcopy(REGISTRY.get(enemy_id)) if isinstance(enemy_id, str) else None


def enemy_for_receipt(receipt):
    return next((key for key, value in REGISTRY.items()
                 if value['receipt'] == receipt), None)


def is_receipt(receipt):return enemy_for_receipt(receipt) is not None


def _point(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(type(n) in (int, float) and abs(n) < 1e7 and math.isfinite(n)
                    for n in value))


def _near(enemy_id, point):
    entry = REGISTRY[enemy_id]
    return (pygame.Rect(entry['trigger']).collidepoint(point)
            or pygame.Vector2(point).distance_squared_to(entry['approach']) <= 48**2)


def valid_ticket(ticket):
    if (not isinstance(ticket, dict) or set(ticket) != TICKET_FIELDS
            or type(ticket['version']) is not int or ticket['version'] != 1
            or not isinstance(ticket['enemy_id'], str) or ticket['enemy_id'] not in REGISTRY
            or type(ticket['level']) is not int or ticket['level'] != 4
            or ticket['scene'] != SCENE_ID
            or not isinstance(ticket['position'], list) or not _point(ticket['position'])
            or ticket['facing'] not in ('front', 'back', 'left', 'right')
            or type(ticket['combat_seed']) is not int or not 0 <= ticket['combat_seed'] < 2**63
            or not isinstance(ticket['party_active'], list)):
        return False
    entry = REGISTRY[ticket['enemy_id']]
    if (ticket['receipt'] != entry['receipt'] or ticket['battlefield'] != entry['battlefield']
            or not _near(ticket['enemy_id'], ticket['position'])):return False
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


def _fresh():
    return {key: {field: False for field in STATE_FIELDS} for key in REGISTRY}


class ElementalBosses:
    def __init__(self, game):
        self.game = game
        self.bosses = _fresh()
        self.victory_order = []
        self._pending = None
        self._armed = {key: True for key in REGISTRY}
        self._defeat_choice = False
        self._presenting = None
        self._acquisition_elapsed = 0.
        self._acquisition_acknowledged = False
        self._seat_started = self._gear_clicked = False
        self._prior_gems = ()
        self._click_sound = self._click_channel = None
        self._sprites = None
        self.presentation_error = ''
        from elemental_room_fx import ElementalRoomEffects
        self._ambience = ElementalRoomEffects(game) if getattr(game, 'audio', None) is not None else None

    @property
    def pending(self):return deepcopy(self._pending)

    @property
    def active(self):return self.game.world.data.get('id') == SCENE_ID

    @property
    def locks_player(self):
        return ((self._pending is not None and not self.game.combat.active)
                or self.acquisition_active)

    @property
    def acquisition_active(self):return self._presenting is not None

    @staticmethod
    def valid_snapshot(record):
        if (not isinstance(record, dict)
                or set(record) != {'version', 'bosses', 'victory_order', 'pending'}
                or type(record['version']) is not int or record['version'] != 1
                or not isinstance(record['bosses'], dict) or set(record['bosses']) != set(REGISTRY)
                or not isinstance(record['victory_order'], list)
                or any(not isinstance(key, str) or key not in REGISTRY for key in record['victory_order'])
                or len(record['victory_order']) != len(set(record['victory_order']))
                or (record['pending'] is not None and not valid_ticket(record['pending']))):return False
        defeated = set()
        for key, state in record['bosses'].items():
            if (not isinstance(state, dict) or set(state) != STATE_FIELDS
                    or any(type(value) is not bool for value in state.values())
                    or state['intro_seen'] and not state['discovered']
                    or state['defeated'] and not state['intro_seen']
                    or state['pending_acquisition'] and not state['defeated']):return False
            if state['defeated']:defeated.add(key)
        if set(record['victory_order']) != defeated:return False
        pending = record['pending']
        return pending is None or record['bosses'][pending['enemy_id']]['discovered']

    @classmethod
    def valid_journey(cls, data):
        try:return cls._valid_journey(data)
        except (KeyError, TypeError, ValueError, AttributeError):return False

    @classmethod
    def _valid_journey(cls, data):
        if not isinstance(data, dict):return False
        state = data.get(SAVE_KEY)
        post = data.get('post_battle')
        elemental_post = isinstance(post, dict) and post.get('kind') == 'elemental_boss'
        receipts = data.get('battle_rewards', {}).get('receipts', [])
        items = data.get('inventory', {}).get('items', {})
        if state is None:
            return (not elemental_post and not any(entry['receipt'] in receipts for entry in REGISTRY.values())
                    and all(type(items.get(entry['item'], 0)) is int
                            and items.get(entry['item'], 0) == 0 for entry in REGISTRY.values()))
        if not cls.valid_snapshot(state):return False
        if (any(values['discovered'] for values in state['bosses'].values())
                and not (data.get('cave_lesson') or {}).get('battle_cleared')):return False
        abilities = data.get('character_abilities') or {}
        owned = abilities.get('gear_gems', {}).get('caelan', [])
        learned = abilities.get('learned_abilities', {}).get('caelan', [])
        for key, entry in REGISTRY.items():
            defeated = state['bosses'][key]['defeated']
            if (entry['receipt'] in receipts) != defeated:return False
            quantity = items.get(entry['item'], 0)
            if type(quantity) is not int or quantity != int(defeated):return False
            if defeated and (entry['gem'] not in owned or entry['skill'] not in learned):return False
        ticket = state['pending']
        if ticket is None:return not elemental_post
        if data.get('sanctuary_boss', {}).get('pending') is not None:return False
        if data.get('cave_random_encounters', {}).get('pending') is not None:return False
        if not (data.get('cave_lesson') or {}).get('battle_cleared'):return False
        enemy_id = ticket['enemy_id']
        defeated = state['bosses'][enemy_id]['defeated']
        if defeated and not (elemental_post and post.get('stage') == 'awarded'):return False
        if post is not None and not elemental_post:return False
        player, party = data.get('player', {}), data.get('party', {})
        if (player.get('scene') != SCENE_ID or player.get('position') != ticket['position']
                or player.get('facing') != ticket['facing']
                or party.get('active') != ticket['party_active']):return False
        if elemental_post:
            return (post.get('encounter') == ticket
                    and post.get('party_before') == ticket['party_resources']
                    and defeated == (post.get('stage') == 'awarded'))
        for key, values in ticket['party_resources'].items():
            saved = party.get('characters', {}).get(key, {})
            if (saved.get('current_hp'), saved.get('current_mp')) != (values['hp'], values['mp']):return False
        return True

    def to_dict(self):
        return {'version': 1, 'bosses': deepcopy(self.bosses),
                'victory_order': list(self.victory_order), 'pending': self.pending}

    def restore(self, record=None):
        if record is not None and not self.valid_snapshot(record):return False
        self.stop_audio()
        if self._ambience is not None:self._ambience.elapsed = 0.
        self.bosses = deepcopy(record['bosses']) if record is not None else _fresh()
        self.victory_order = list(record['victory_order']) if record is not None else []
        self._pending = deepcopy(record['pending']) if record is not None else None
        self._armed = {key: True for key in REGISTRY}
        self._defeat_choice = False
        self._presenting = None
        self._acquisition_elapsed = 0.
        self._acquisition_acknowledged = self._seat_started = self._gear_clicked = False
        return True

    def entry_loaded(self):
        if self._pending is None:return False
        self.bosses[self._pending['enemy_id']]['intro_seen'] = True
        return True

    def mark_defeated(self, receipt):
        key = enemy_for_receipt(receipt)
        if (key is None or self._pending is None or self._pending['enemy_id'] != key
                or self.bosses[key]['defeated']):return False
        self.bosses[key].update(discovered=True, intro_seen=True, defeated=True, pending_acquisition=True)
        self.victory_order.append(key)
        return True

    def finish(self, receipt):
        key = enemy_for_receipt(receipt)
        if (key is None or self._pending is None or self._pending['enemy_id'] != key
                or not self.bosses[key]['defeated']):return False
        self._pending = None
        self._defeat_choice = False
        self._armed[key] = False
        return True

    def _available(self, *, require_cave=True):
        g = self.game
        return ((self.active or not require_cave) and not g.on_title and not g.combat.active
                and not g.opening_cinematic.active and not g.social.active and not g.social.locked
                and not g.household_action and not g.opening.locks_player
                and not g.transfer_cooldown and not g.opening_fade
                and not g.map_open and not g.quest_ui.journal_open
                and getattr(g, '_music_focused', True)
                and not any(getattr(getattr(g, key, None), 'is_open', False)
                            for key in ('pause', 'inventory_ui', 'world_map_viewer', 'party_ui', 'status_ui')))

    def nearby(self, enemy_id=None):
        if enemy_id is not None and (not isinstance(enemy_id, str) or enemy_id not in REGISTRY):return None
        if (not self._available() or self._pending is not None or self.game.cave_lesson.needs_intro
                or self.game.sanctuary_boss.pending is not None
                or self.game.cave_random_encounters.pending is not None):return None
        for key in ((enemy_id,) if enemy_id is not None else REGISTRY):
            entry = REGISTRY[key]
            if (not self.bosses[key]['defeated'] and _near(key, self.game.player.position)
                    and self.game.world.can_stand(self.game.player.position)
                    and clear_sight(self.game.world, self.game.player.position, entry['center'])):
                return key
        return None

    def interaction_hint(self):
        key = self.nearby()
        return 'E: approach '+REGISTRY[key]['name'] if key is not None else ''

    def interact(self):
        key = self.nearby()
        return self.offer(key) if key is not None else False

    def offer(self, enemy_id, error=None):
        if not isinstance(enemy_id, str) or enemy_id not in REGISTRY or self.nearby(enemy_id) != enemy_id:return False
        g, entry = self.game, REGISTRY[enemy_id]
        before = self.to_dict()
        self.bosses[enemy_id]['discovered'] = True
        if not self._checkpoint():
            self.restore(before)
            error = 'Progress could not be saved. Try again before entering.'
        g.player.moving = g.player.running = False
        line = ("Look, the Aether is condensing into that monster. It's drawing in fire-aspected Aether from the cave."
                if entry['element'] == 'fire' else
                "Look, the Aether is condensing into that monster. It's drawing in ice-aspected Aether from its surroundings.")
        opened = g.social.start_choice(
            [{'speaker': 'caelan', 'text': line}],
            [{'text': 'Approach', 'action': 'enter'}, {'text': 'Party', 'action': 'party'},
             {'text': 'Leave', 'action': 'leave'}],
            lambda action: self._choose(enemy_id, action),
            identifier='elemental_boss_offer_'+enemy_id, prompt=error or 'Approach '+entry['name']+'?')
        if opened:self._armed[enemy_id] = False
        return opened

    def _choose(self, enemy_id, action):
        if self.nearby(enemy_id) != enemy_id:return
        g, entry = self.game, REGISTRY[enemy_id]
        self.bosses[enemy_id]['discovered'] = True
        if action == 'party':
            g.party_ui.open(prompt='Prepare for '+entry['name'],
                            on_confirm=lambda: self.offer(enemy_id), on_cancel=lambda: self.offer(enemy_id))
        elif action == 'leave':
            self._move(entry['approach'])
            self._checkpoint()
        elif action == 'enter':
            reason = g.party.battle_reason()
            if reason:
                self.offer(enemy_id, reason)
                return
            if g.sanctuary_boss.pending is not None or g.cave_random_encounters.pending is not None:
                self.offer(enemy_id, 'Finish the current encounter first.')
                return
            ticket = {'version': 1, 'enemy_id': enemy_id, 'level': entry['level'],
                      'receipt': entry['receipt'], 'scene': SCENE_ID,
                      'position': list(g.player.position), 'facing': g.player.facing,
                      'battlefield': entry['battlefield'], 'combat_seed': random.SystemRandom().randrange(2**63),
                      'party_active': list(g.party.active_ids),
                      'party_resources': {key: {'hp': g.party.characters[key].current_hp,
                                                'mp': g.party.characters[key].current_mp}
                                          for key in g.party.active_ids}}
            if not valid_ticket(ticket):return
            self.bosses[enemy_id]['discovered'] = True
            self._pending = ticket
            if not g.combat.start_elemental_boss(ticket):
                self._pending = None
                self.offer(enemy_id, 'The battle could not be started. Try again.')

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

    def finish_flee(self, ticket):
        """Root checkpoints this mutation with the battle's spent resources."""
        if not valid_ticket(ticket) or self._pending != ticket or self.bosses[ticket['enemy_id']]['defeated']:return False
        key = ticket['enemy_id']
        if not self._move(REGISTRY[key]['retreat']):return False
        self._pending = None
        self._defeat_choice = False
        self._armed[key] = False
        return True

    def battle_fled(self, ticket):return self.finish_flee(ticket)

    def battle_defeated(self, ticket):
        if not valid_ticket(ticket) or self._pending != ticket or self.bosses[ticket['enemy_id']]['defeated']:return False
        self._defeat_choice = True
        self._show_defeat()
        return True

    def _show_defeat(self, error=None):
        if not self._available() or self._pending is None:return False
        name = REGISTRY[self._pending['enemy_id']]['name']
        return self.game.social.start_choice(
            [{'speaker': 'caelan', 'text': 'We need to regroup before trying that again.'}],
            [{'text': 'Retry', 'action': 'retry'}, {'text': 'Leave', 'action': 'leave'}],
            self._choose_defeat, identifier='elemental_boss_defeat',
            prompt=error or 'Try '+name+' again or leave?')

    def _choose_defeat(self, action):
        if not self._available() or self._pending is None:return
        if self.bosses[self._pending['enemy_id']]['defeated']:return
        if action == 'retry':
            if not self.game.combat.start_elemental_boss(self.pending, restoring=True):
                self._show_defeat('The battle could not be restarted. Try again.')
            else:self._defeat_choice = False
        elif action == 'leave':
            g, before = self.game, self.to_dict()
            position, facing = tuple(g.player.position), g.player.facing
            if not self.finish_flee(self.pending) or not self._checkpoint():
                self.restore(before)
                g.player.position.update(position);g.player.facing = facing
                g.party_travel.reset();g.camera.reset()
                self._defeat_choice = True
                self._show_defeat('Progress could not be saved. Try again.')

    def make_entry(self, world_frame, focus, *, restoring=False):
        from elemental_boss_entry import ElementalBossEntry
        key = self._pending['enemy_id']
        return ElementalBossEntry(world_frame, focus, key,
                                  intro_seen=self.bosses[key]['intro_seen'],
                                  reduced_motion=self.game.audio.reduced_motion)

    def _acquisition_lines(self, key):
        entry = REGISTRY[key]
        first = self.victory_order.index(key) == 0
        color = 'red' if key == 'embravyr' else 'white'
        if first:
            return [
                {'speaker': 'caelan', 'text': 'The Aether has settled into a gem like I have in my sword.'},
                {'speaker': 'mira', 'text': 'Look...it fits one of the empty sockets. Let me seat it in the ring.'},
                {'speaker': 'caelan', 'text': 'Wow, I can channel Aether through it.'},
                {'speaker': 'mira', 'text': 'Can you form it around your blade like with the water gem?'},
                {'speaker': 'caelan', 'text': 'Yeah...I am getting the hang of it while we are in this cave.'},
                {'speaker': 'caelan', 'text': 'The '+color+' focus is part of the blade now.'},
            ]
        return [
            {'speaker': 'mira', 'text': 'Another focus. There is still room in the ring for it, here.'},
            {'speaker': 'caelan', 'text': 'This one has different flow… but I know how to follow it now.'},
            {'speaker': 'caelan', 'text': 'The '+color+' focus is part of the blade now.'},
        ]

    def _finish_acquisition(self, key):
        if self._acquisition_elapsed < 1.1:
            self._acquisition_acknowledged = self._seat_started = True
            return
        before = self.bosses[key]['pending_acquisition']
        self.bosses[key]['pending_acquisition'] = False
        self._presenting = None
        if not self._checkpoint():self.bosses[key]['pending_acquisition'] = before

    def _present_acquisition(self):
        if (self._presenting is not None or self._pending is not None or not self._available(require_cave=False)
                or not self.game.party.characters['caelan'].current_hp):return False
        for key in self.victory_order:
            if not self.bosses[key]['pending_acquisition']:continue
            opened = self.game.social.start_script(
                self._acquisition_lines(key), on_complete=lambda key=key: self._finish_acquisition(key),
                identifier='elemental_focus_acquisition_'+key)
            if opened:
                self._presenting = key
                self._acquisition_elapsed = 0.
                self._acquisition_acknowledged = self._seat_started = self._gear_clicked = False
                hidden = {REGISTRY[other]['gem'] for other in self.victory_order
                          if self.bosses[other]['pending_acquisition']}
                self._prior_gems = tuple(gem for gem in self.game.character_abilities.owned_gems()
                                         if gem not in hidden)
            return opened
        return False

    def update(self, seconds=0):
        self.sync_audio()
        if self._ambience is not None:self._ambience.update(seconds)
        if self._presenting is not None:
            if not getattr(self.game, '_music_focused', True):return False
            social = self.game.social
            if social.script_identifier == 'elemental_focus_acquisition_'+self._presenting:
                if social.page and social.page.get('source_line', 0) >= (1 if self.victory_order.index(self._presenting) == 0 else 0):
                    self._seat_started = True
            elif not self._acquisition_acknowledged:
                self._presenting = None
                return False
            if self._seat_started:self._acquisition_elapsed += max(0., seconds)
            if self._acquisition_elapsed >= .72 and not self._gear_clicked:
                self._gear_clicked = True
                self._play_click()
            if self._acquisition_acknowledged and self._acquisition_elapsed >= 1.1:
                self._finish_acquisition(self._presenting)
            return False
        if self._present_acquisition():return True
        if not self.active:return False
        if self._defeat_choice and self._pending is not None:return self._show_defeat()
        if not self._available() or self._pending is not None:return False
        for key, entry in REGISTRY.items():
            inside = pygame.Rect(entry['trigger']).collidepoint(self.game.player.position)
            if not inside:self._armed[key] = True
            if inside and self._armed[key] and self.nearby(key) == key:return self.offer(key)
        return False

    def _play_click(self):
        try:
            if not pygame.mixer.get_init() or self.game.audio.effects_volume <= 0:return
            if self._click_sound is None:
                self._click_sound = pygame.mixer.Sound(str(Path(__file__).parent/'assets/story/mill_gift/gear_click.ogg'))
            self._click_channel = self._click_sound.play()
            self.sync_audio()
        except (OSError, pygame.error):self._click_channel = None

    def sync_audio(self):
        if self._ambience is not None:self._ambience.sync_audio()
        if self._click_channel is None:return
        try:
            if self._click_channel.get_sound() is not self._click_sound:
                self._click_channel = None
                return
            self._click_channel.set_volume(.14*self.game.audio.effects_volume)
            if not getattr(self.game, '_music_focused', True) or self.game.pause.is_open:
                self._click_channel.pause()
            else:self._click_channel.unpause()
        except pygame.error:self._click_channel = None

    def stop_audio(self):
        if self._ambience is not None:self._ambience.stop_audio()
        try:
            if self._click_channel is not None and self._click_channel.get_sound() is self._click_sound:
                self._click_channel.stop()
        except pygame.error:pass
        self._click_channel = None

    def draw_ui(self, target):
        """A native mechanism close-up seats the earned gem outside the prose."""
        if self._presenting is None:return
        from gear_state import GEM_ORDER
        from gear_widget import _housing, _mechanism, _gem, _point
        from ui_style import GOLD, IVORY
        painter = self.game.ui.painter(target)
        entry = REGISTRY[self._presenting]
        layout = self.game.social.bubble.layout(painter=painter)
        above = max(0, layout.panel.top-12) if layout is not None else 160
        below = max(0, 304-layout.panel.bottom-6) if layout is not None else 0
        height = min(88, max(above, below))
        # Three short display-resolution labels fit beside a native wheel even
        # with 150% text. Ordinary portrait prose keeps its measured rectangle.
        height = max(66, height)
        y = 6 if above >= below else 310-height
        panel = pygame.Rect(90, y, 300, height)
        painter.panel(panel)
        side = min(72, height-12)
        wheel = pygame.Rect(panel.left+6, panel.top+6, side, side)
        progress = min(1., self._acquisition_elapsed/.72)
        seated = self.game.audio.reduced_motion or progress >= 1
        owned = tuple(gem for gem in GEM_ORDER
                      if gem in self._prior_gems or seated and gem == entry['gem'])
        active = GEM_ORDER.index('water')
        angle = -active*math.pi/2
        layer = _housing().copy()
        layer.blit(_mechanism(round((angle % math.tau)/math.tau*240)%240, active, owned), (0, 0))
        painter.image(layer, wheel)
        local = _point(12, angle+GEM_ORDER.index(entry['gem'])*math.pi/2)
        destination = pygame.Vector2(wheel.left+local[0]*side/48, wheel.top+local[1]*side/48)
        if not seated:
            icon = pygame.Surface((16, 16), pygame.SRCALPHA)
            _gem(icon, entry['gem'], (8, 8), True)
            # Keep the short seating path within the mechanism column, away
            # from the display-resolution focus and learned-skill labels.
            origin = pygame.Vector2(wheel.centerx, panel.bottom-10)
            blend = progress*progress*(3-2*progress)
            point = origin.lerp(destination, blend)
            painter.image(icon, (round(point.x-8), round(point.y-8), 16, 16))
        elif not self.game.audio.reduced_motion and self._acquisition_elapsed < 1.1:
            fade = max(0, 1-(self._acquisition_elapsed-.72)/.38)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                a = destination+pygame.Vector2(dx, dy)*(5+fade*2)
                b = destination+pygame.Vector2(dx, dy)*(8+fade*3)
                painter.line(GOLD, a, b)
        text_x = wheel.right+10
        line_height = painter.font('small').get_linesize()+2
        painter.text('Focus installed' if seated else 'New focus', (text_x, panel.top+8),
                     role='small', color=GOLD, bold=True)
        painter.text(entry['gem_name'], (text_x, panel.top+8+line_height), role='small', color=IVORY)
        painter.text(entry['skill_name']+' learned', (text_x, panel.top+8+line_height*2),
                     role='small', color=GOLD)
        return panel

    def draw_world(self, target, camera, *, elapsed_ms=None):
        """Draw chamber ambience followed by each guardian's authored idle bank."""
        if not self.active:return
        if self._ambience is not None:self._ambience.draw(target, camera)
        if self.game.cave_lesson.needs_intro:return
        for key, entry in REGISTRY.items():
            if self.bosses[key]['defeated']:continue
            point = pygame.Vector2(entry['center'])-pygame.Vector2(camera)
            if not target.get_rect().inflate(160, 160).collidepoint(point):continue
            manifest = Path(__file__).parent/'assets/combat'/key/'animation.json'
            if not manifest.exists():
                self.presentation_error = entry['name']+' combat artwork is not available.'
                continue
            try:
                if self._sprites is None:
                    from battle_scene import CombatSprites
                    self._sprites = CombatSprites()
                clock = self.game.elapsed_ms if elapsed_ms is None else elapsed_ms
                image, anchor = self._sprites.frame(key, 'idle', 0 if self.game.audio.reduced_motion else clock)
                scale = .5
                image = pygame.transform.scale(image, tuple(max(1, round(n*scale)) for n in image.get_size()))
                floor = (round(point.x-anchor[0]*scale), round(point.y-anchor[1]*scale))
                target.blit(image, floor)
                self.presentation_error = ''
            except (OSError, ValueError, KeyError, pygame.error) as error:
                self.presentation_error = entry['name']+' could not be drawn: '+str(error)
