"""Encounter battle views, compact party status and contextual guidance."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

from gear_widget import GearWidget
from gear_state import GEM_NAMES, GEM_COLORS
from gearblade_fx import GearbladeEffects
from battle_choreography import sample as sample_choreography
from battle_action_fx import BattleActionEffects, target_reaction
from battle_action_audio import BattleActionAudio
from combat_motion_art import MOTION_STATES, frame as motion_frame, anchors as motion_anchors
from mira_combat_art import MiraCombatArt
from mira_rig_ui import MiraRigUI
from cave_battlefield import CaveBattlefield, CAVE_BATTLEFIELDS
from battle_target_marker import (FINGER_SIZE, FINGER_GAP, target_marker_geometry,
                                  draw_target_ring, draw_target_finger)
from battle_announcements import BattleAnnouncements, enemy_charge_warnings
from enemy_charge_aura import EnemyChargeAura
from vespermaw_confluence_fx import (VespermawConfluenceEffects,
                                     VespermawChannelAudio, COLORS as CONFLUENCE_COLORS)

from ui_style import FOREST, FOREST_DARK, FOREST_LIGHT, IVORY, GOLD, BRASS, MUTED


ROOT = Path(__file__).resolve().parent
COMBAT_ART = ROOT/'assets/combat'
RESULTS = ('victory', 'defeat', 'fled')
ACTION_LABELS = {'attack': 'Attack', 'guard': 'Guard', 'flee': 'Flee',
                 'skills': 'Skills', 'back': 'Back',
                 'aether_edge': 'Aether Edge', 'aether_dart': 'Dart · 4 MP',
                 'nature_edge': 'Nature Edge', 'aqua_edge': 'Aqua Edge',
                 'flame_edge': 'Flame Edge', 'ice_edge': 'Ice Edge',
                 'charged_bolt': 'Charged Bolt', 'bulwark': 'Bulwark',
                 'repair_pulse': 'Repair Pulse', 'impact_bolt': 'Impact Bolt',
                 'arc_discharge': 'Arc Discharge'}
RIG_SKILLS = frozenset(('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'))
HP_GREEN = '#6fc878'
HP_YELLOW = GOLD
HP_RED = '#df6b62'
MP_BLUE = '#5da9e9'
ATB_YELLOW = GOLD
ELEMENTALS = frozenset(('embravyr', 'nivareth'))
CAVE_ENEMIES = frozenset(('lithrusk', 'veylume', 'vespermaw', *ELEMENTALS))


class CombatSprites:
    """Native combat frames loaded once, including optional guest/enemy art."""

    def __init__(self, root=COMBAT_ART):
        self.root = Path(root)
        self.actors = {}
        for actor in ('caelan', 'bat'):
            self._load_actor(actor)

    def _load_actor(self, actor):
        if actor not in ('caelan', 'bat', 'mira', 'ridgeback_tusker', 'lucan', 'rhea', 'edran',
                         'lithrusk', 'veylume', 'vespermaw', *ELEMENTALS):
            raise ValueError('Unknown combat actor')
        folder = self.root/actor
        data = json.loads((folder/'animation.json').read_text(encoding='utf-8'))
        canvas, anchor = data['canvas'], data['anchor']
        if (len(canvas) != 2 or len(anchor) != 2
                or any(type(n) is not int or n <= 0 for n in canvas)
                or any(type(n) is not int or not 0 <= n <= canvas[i]
                       for i, n in enumerate(anchor))):
            raise ValueError('Invalid combat sprite canvas or anchor')
        animations = {}
        points = {}
        for state, animation in data['animations'].items():
            frames = []
            frame_points = []
            for record in animation['frames']:
                filename = Path(record['file'])
                duration = record['duration_ms']
                if (filename.is_absolute() or '..' in filename.parts
                        or type(duration) is not int or duration <= 0):
                    raise ValueError('Invalid combat animation frame')
                surface = pygame.image.load(str(folder/filename)).convert_alpha()
                if surface.get_size() != tuple(canvas):
                    raise ValueError('Combat animation frames must share their canvas')
                frames.append((surface, duration))
                anchors = record.get('anchors', {})
                if (not isinstance(anchors, dict)
                        or any(not isinstance(name, str) or not isinstance(point, (list, tuple))
                               or len(point) != 2 or any(type(value) not in (int, float)
                                   or not math.isfinite(value) for value in point)
                               for name, point in anchors.items())):
                    raise ValueError('Invalid combat animation anchors')
                frame_points.append({name: tuple(point) for name, point in anchors.items()})
            if not frames or type(animation['loop']) is not bool:
                raise ValueError('Invalid combat animation')
            animations[state] = (frames, animation['loop'])
            points[state] = frame_points
        if 'idle' not in animations:raise ValueError('Combat sprites require an idle')
        occupied = [frame.get_bounding_rect() for sequence, _ in animations.values()
                    for frame, _ in sequence if frame.get_bounding_rect().width]
        bounds = occupied[0].unionall(occupied[1:]) if occupied else pygame.Rect(0, 0, *canvas)
        idle = [frame.get_bounding_rect() for frame, _ in animations['idle'][0]
                if frame.get_bounding_rect().width]
        idle_bounds = idle[0].unionall(idle[1:]) if idle else bounds
        self.actors[actor] = {'anchor': tuple(anchor), 'animations': animations,
                             'bounds': bounds, 'idle_bounds': idle_bounds,
                             'frame_anchors': points,
                             'timing': {state: {'contact_ms': entry.get('contact_ms')}
                                        for state, entry in data['animations'].items()}}

    def _selection(self, actor, state, elapsed_ms):
        if actor not in self.actors:self._load_actor(actor)
        data = self.actors[actor]
        if state not in data['animations']:state = 'idle'
        frames, loop = data['animations'][state]
        duration = sum(frame[1] for frame in frames)
        time = max(0, elapsed_ms)
        time = time % duration if loop else min(time, duration-1)
        for index, (_, length) in enumerate(frames):
            if time < length:return data, state, index
            time -= length
        return data, state, len(frames)-1

    def frame(self, actor, state, elapsed_ms):
        data, state, index = self._selection(actor, state, elapsed_ms)
        return data['animations'][state][0][index][0], data['anchor']

    def anchors(self, actor, state, elapsed_ms):
        """Read retained pose points using the exact same clock as its drawing."""
        data, state, index = self._selection(actor, state, elapsed_ms)
        result = dict(data['frame_anchors'][state][index])
        result.setdefault('floor', data['anchor'])
        return result


class BattleScene:
    """Render and operate a BattleModel without settling its persistent outcome.

    Game owns transition, checkpoint and rewards. A confirmed result sets
    dismissed, which lets Game return safely to the original world position.
    """

    def __init__(self, game, model, sprites=None, *, battlefield='eldenmere', tutorial=False):
        if battlefield not in ('eldenmere', 'millrace', *CAVE_BATTLEFIELDS):
            raise ValueError('Unknown battlefield')
        self.game, self.model = game, model
        model.set_item_inventory(getattr(game, 'inventory', None))
        self.battlefield = battlefield
        self._cave_field = CaveBattlefield(battlefield) if battlefield in CAVE_BATTLEFIELDS else None
        self.location_name = (self._cave_field.name if self._cave_field is not None else
                              'Upper Millrace' if battlefield == 'millrace' else 'Eldenmere')
        self.tutorial = bool(tutorial)
        self._tutorial_queue = []
        self._tutorial_seen = set()
        self.tutorial_continue_rect = pygame.Rect(354, 61, 90, 20)
        self.sprites = sprites if sprites is not None else CombatSprites()
        self.mira_art = MiraCombatArt() if model.combatant('mira') is not None else None
        self.rig = (MiraRigUI(getattr(model, 'rig_allocation', None), on_apply=self._apply_rig)
                    if self.mira_art is not None else None)
        if model.weapon_equipped:
            from gearblade_art import prepare_combat_art
            prepare_combat_art()
        self.dismissed = False
        self.result_error = ''
        self.paused = False
        self.focused = True
        self.selected = 0
        self.command_menu = 'root'
        self._selected_item = None
        self._selected_skill = None
        self._target_command = None
        self.enemy_rows = {}
        self.enemy_rects = {}
        self.target_marker_rects = {}
        self._command_context = (model.phase, model.ready_actor)
        self._held = False
        self._elapsed = 0.0
        self._phase_elapsed = 0.0
        self._defeat_times = {member.identifier: 0.0 for member in
                              (*model.party, *self._enemy_members()) if not member.hp}
        self._popups = []
        self._reactions = {}
        self.action_fx = BattleActionEffects()
        self._elemental_layer = pygame.Surface((480, 320), pygame.SRCALPHA)
        self._rig_layer = pygame.Surface((480, 320), pygame.SRCALPHA)
        motion_frame('plant', 0, armed=model.weapon_equipped)
        self.action_audio = BattleActionAudio(game)
        self.channel_art = None
        if any(self._sprite(enemy.identifier)=='vespermaw' for enemy in self._enemy_members()):
            from vespermaw_channel_art import VespermawChannelArt
            self.channel_art = VespermawChannelArt()
        self.channel_fx = VespermawConfluenceEffects()
        self.channel_audio = VespermawChannelAudio(game)
        if self.channel_art is not None:self.channel_audio.prepare()
        self._cue_action = None
        self._cue_phases = set()
        self._enemy_charge_time = None
        self._enemy_charge_times = {}
        self._enemy_recovery_times = {}
        self._last_phase = model.phase
        self._notice = ''
        self.panel_rect = pygame.Rect(8, 232, 464, 80)
        self.command_rects = {}
        self.continue_rect = pygame.Rect(20, 286, 110, 20)
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self._target_confirm_rect = pygame.Rect(0, 0, 0, 0)
        self._target_cancel_rect = pygame.Rect(0, 0, 0, 0)
        self.name_rect = pygame.Rect(220, 252, 40, 15)
        self.atb_rect = pygame.Rect(156, 256, 50, 6)
        self.hp_rect = pygame.Rect(294, 266, 86, 5)
        self.mp_rect = pygame.Rect(390, 266, 70, 5)
        self.party_row_rect = pygame.Rect(152, 250, 308, 24)
        self.party_rows = {}
        self.header_rects = {}
        self._detail_lines = []
        self.gear = GearWidget(getattr(model, 'active_gem', 'water'),
                               owned_gems=getattr(model, 'owned_gems', None))
        self.gear_fx = GearbladeEffects()
        self._slot_time = None
        self._gear_adjust_time = None
        self._command_scroll = 0
        self._pointer = None
        self._pointer_window = None
        self._hovered_enemy = None
        self._viewport = (self.game.ui_surface.get_size(), getattr(self.game.audio, 'text_scale', 1))
        self._command_lines = {}
        self._background = (self._cave_field.frames[0] if self._cave_field is not None else
                            self._make_background(COMBAT_ART/battlefield/'background.png'))
        self._grass = self._make_grass() if battlefield == 'eldenmere' else ()
        self._shadows = self._make_shadows()
        self.announcements = BattleAnnouncements(model, display_name=self._feedback_name)
        self.announcement_rect = pygame.Rect(8, 3, 464, 29)
        self.announcement_text_rects = []
        self.charge_aura = EnemyChargeAura()
        self.charge_aura_rects = {}

    def _feedback_name(self, identifier):
        if self._is_enemy(identifier):return self._enemy_name(identifier)
        member = self.model.combatant(identifier)
        return member.name if member is not None else str(identifier or '')

    def announce(self, text, *, actor=None, kind='event'):
        """Present an authored battle emote without changing combat state."""
        self.announcements.consume({'type': kind, 'actor': actor, 'text': text})

    @property
    def charging_enemies(self):
        return tuple(warning['actor'] for warning in enemy_charge_warnings(
            self.model, display_name=self._feedback_name))

    def _enemy_members(self):
        return tuple(getattr(self.model, 'enemies', (self.model.enemy,)))

    def _is_enemy(self, identifier):
        return any(member.identifier == identifier for member in self._enemy_members())

    def _sprite(self, identifier):
        if identifier == 'player':return 'caelan'
        if self._is_enemy(identifier):
            helper = getattr(self.model, 'enemy_sprite_id_for', None)
            return helper(identifier) if helper is not None else self.model.enemy_sprite_id
        return identifier

    def _telegraphs(self):
        values = getattr(self.model, 'enemy_telegraphs', None)
        if values is not None:return values
        return {'enemy': self.model.telegraphed_target} if self.model.telegraphed_target else {}

    @property
    def _group(self):return len(self._enemy_members()) > 1

    def _enemy_name(self, identifier):
        members = self._enemy_members()
        member = next(member for member in members if member.identifier == identifier)
        duplicates = [enemy for enemy in members if enemy.name == member.name]
        name = 'Bat' if self._group and member.name == 'Cave Bat' else member.name
        return name+(' '+chr(65+duplicates.index(member)) if len(duplicates) > 1 else '')

    def _enemy_header_columns(self):
        count = len(self._enemy_members())
        height = getattr(self, '_enemy_label_height', 21)
        space = self.panel_rect.top-5-(35+math.ceil(count/2)*height+4)
        # Large text keeps all HP/ATB cards, using one row so bodies and the
        # pointing glove still have room below the header.
        return count if count > 2 and space < FINGER_SIZE[1]+FINGER_GAP+40 else min(2, count)

    def _group_slots(self):
        members = self._enemy_members()
        height = getattr(self, '_enemy_label_height', 21)
        columns = self._enemy_header_columns()
        return {enemy.identifier: pygame.Rect(10+round(index % columns*260/columns),
                    35+index//columns*height,
                    round((index % columns+1)*260/columns)-round(index % columns*260/columns)-4, height-2)
                for index, enemy in enumerate(members)}

    @staticmethod
    def _make_background(path=COMBAT_ART/'eldenmere/background.png'):
        """Load the authored well-side clearing once at its native pixel size."""
        image = pygame.image.load(str(path))
        if image.get_size() != (480, 320):
            raise ValueError('Eldenmere battlefield must be 480 by 320 pixels')
        return image.convert()

    @staticmethod
    def _make_grass(path=COMBAT_ART/'eldenmere/grass.png'):
        """Cache a few native-pixel breeze poses of the authored foreground tuft."""
        image = pygame.image.load(str(path)).convert_alpha()
        if image.get_size() != (24, 12):
            raise ValueError('Eldenmere foreground grass must be 24 by 12 pixels')
        return tuple(pygame.transform.rotate(image, angle) for angle in (-4, 0, 4))

    def _draw_foreground(self, canvas):
        if not self._grass:return
        for x, y, phase in ((32, 198, 0), (456, 197, 1.8)):
            sway = 0 if self.reduced_motion else math.sin(self._elapsed*1.4+phase)
            image = self._grass[0 if sway < -.4 else 2 if sway > .4 else 1]
            canvas.blit(image, image.get_rect(midbottom=(x, y)))

    @staticmethod
    def _make_shadows():
        """Small translucent ground projections keep the painted grass visible."""
        shadows = {}
        for key, size, opacity in (('player', (34, 7), 65),
                                   ('enemy_low', (30, 7), 48),
                                   ('enemy_high', (24, 5), 34),
                                   ('tusker', (114, 14), 62),
                                   ('lithrusk', (84, 11), 62),
                                   ('veylume', (32, 6), 30),
                                   ('embravyr', (68, 10), 42),
                                   ('nivareth', (54, 8), 34),
                                   ('vespermaw', (126, 17), 65)):
            image = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.ellipse(image, (31, 43, 29, opacity//2), image.get_rect())
            pygame.draw.ellipse(image, (31, 43, 29, opacity), image.get_rect().inflate(-8, -2))
            shadows[key] = image
        return shadows

    def _draw_shadow(self, canvas, actor, point):
        if not self._is_enemy(actor):
            image, ground_y = self._shadows['player'], round(point.y)
        elif self._sprite(actor) == 'ridgeback_tusker':
            image, ground_y = self._shadows['tusker'], round(point.y)
            factor = self._actor_scale(actor)/2
            if factor != 1:
                image = pygame.transform.scale(image, (max(1, round(image.get_width()*factor)),
                                                       max(1, round(image.get_height()*factor))))
        elif self._sprite(actor) in CAVE_ENEMIES:
            image = self._shadows[self._sprite(actor)]
            factor = self._actor_scale(actor)/2
            image = pygame.transform.scale(image, (max(1, round(image.get_width()*factor)),
                                                   max(1, round(image.get_height()*factor))))
            ground_y = round(point.y)
        else:
            # The Bat moves above the same ground plane, including its idle bob.
            ground_y = round(self._home_positions()[actor].y+(0 if self._group or self._cave_field is not None else 14))
            image = self._shadows['enemy_low' if point.y > 177 else 'enemy_high']
            if self._group or self._actor_scale(actor) != 2:
                image = pygame.transform.scale(image, (max(1, round(image.get_width()*self._actor_scale(actor)/2)),
                                                       max(1, round(image.get_height()*self._actor_scale(actor)/2))))
        canvas.blit(image, (round(point.x)-image.get_width()//2,
                            ground_y-image.get_height()//2))

    def _layout(self, painter):
        """One geometry map for character columns and the shared right menu."""
        self._sync_commands()
        small = painter.font('small').get_linesize()
        name_font = painter.font('small', bold=True)
        name = name_font.get_linesize()
        count = len(self.model.party)
        # Name/ATB, HP and MP each occupy one text row. The remaining two
        # thirds keep the gear's native size while exposing more battlefield.
        self._status_height = name+2*small+4
        interactable_height = 2*self._status_height
        height = 3*self._status_height
        self.panel_rect = pygame.Rect(8, 312-height, 464, height)
        top = self.panel_rect.top
        command_width = max(80, painter.font('small', bold=True).size('COMMANDS')[0]+12)
        self.commands_panel = pygame.Rect(self.panel_rect.right-command_width, top, command_width, height)
        party_width = self.commands_panel.left-self.panel_rect.left
        self.party_rows = {}
        for index, member in enumerate(self.model.party):
            left = 8+round(party_width*index/count)
            right = 8+round(party_width*(index+1)/count)
            column = pygame.Rect(left, top, right-left, height)
            center = column.centerx
            name_width, name_height = name_font.size(member.name)
            inner_width = column.width-8
            header_gap = 4 if column.width-name_width >= 32 else 2
            atb_width = min(44 if count == 3 else 56, column.width-4-name_width-header_gap)
            header_left = center-(name_width+header_gap+atb_width)//2
            name_rect = pygame.Rect(header_left, top+2, name_width, name_height)
            atb_rect = pygame.Rect(name_rect.right+header_gap, 0, atb_width, 4)
            atb_rect.centery = name_rect.centery
            resource_width = max(painter.font('small').size(label+' '+str(maximum)+'/'+str(maximum))[0]
                                 for label, maximum in (
                                     ('HP', member.max_hp), ('MP', member.max_mp)))
            bar_width = min(112, inner_width-resource_width-4)
            bar_left = center-(bar_width+4+resource_width)//2
            hp_top = top+2+name
            mp_top = hp_top+small
            hp_text = pygame.Rect(bar_left+bar_width+4, hp_top, resource_width, small)
            mp_text = pygame.Rect(hp_text.left, mp_top, resource_width, small)
            hp_bar = pygame.Rect(bar_left, 0, bar_width, 3)
            mp_bar = pygame.Rect(bar_left, 0, bar_width, 3)
            hp_bar.centery, mp_bar.centery = hp_text.centery, mp_text.centery
            self.party_rows[member.identifier] = {
                'column': column,
                'row': pygame.Rect(left+2, top+2, column.width-4, self._status_height-3),
                'name': name_rect,
                'atb': atb_rect,
                'hp_text': hp_text,
                'mp_text': mp_text,
                'hp': hp_bar,
                'mp': mp_bar,
                'interactable': pygame.Rect(left+4, top+self._status_height+2,
                                            column.width-8, interactable_height-6)}
        player_row = self.party_rows['player']
        self.name_rect, self.atb_rect = player_row['name'], player_row['atb']
        self.hp_rect, self.mp_rect = player_row['hp'], player_row['mp']
        self.party_row_rect = player_row['row']
        self._party_bottom = top+self._status_height
        self._detail_top = self._party_bottom+5
        space = player_row['interactable']
        side = min(48, space.height, space.width)
        wheel = pygame.Rect(0, 0, side, side)
        wheel.center = (space.centerx-18 if space.width >= 140 else space.centerx, space.centery)
        self.gear.layout(wheel)
        if self.rig is not None and 'mira' in self.party_rows:
            self.rig.sync(self.model.rig_allocation)
            self.rig.layout(self.party_rows['mira']['interactable'], painter)
        self.continue_rect = pygame.Rect(self.commands_panel.left+6, self.panel_rect.bottom-25, self.commands_panel.width-12, 20)
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self._target_confirm_rect = pygame.Rect(self.commands_panel.left+6, self.panel_rect.bottom-47,
                                               self.commands_panel.width-12, 18)
        self._target_cancel_rect = pygame.Rect(self.commands_panel.left+6, self.panel_rect.bottom-25,
                                              self.commands_panel.width-12, 18)
        self.header_rects = {}
        actions = self._command_actions()
        self._command_lines = {identifier: painter.wrap(self._command_label(identifier),
                                                        self.commands_panel.width-16, role='small')
                               for identifier in actions}
        row_heights = [max(16, len(self._command_lines[item])*small+5) for item in actions]
        available = height-small-15
        if self.command_menu == 'root':
            # Keep all five primary commands visible without growing the HUD.
            primary = min(5, len(actions))
            compact = max(small+2, available//max(1, primary))
            for index in range(primary):
                if len(self._command_lines[actions[index]]) == 1:
                    row_heights[index] = min(row_heights[index], compact)
        self._command_scroll = min(self._command_scroll, max(0, len(actions)-1))
        if actions:
            selected = self.selected % len(actions)
            if selected < self._command_scroll:self._command_scroll = selected
            while sum(row_heights[self._command_scroll:selected+1]) > available:
                self._command_scroll += 1
        self.command_rects = {}
        y = top+small+10
        for index in range(self._command_scroll, len(actions)):
            row_height = row_heights[index]
            if y+row_height > self.panel_rect.bottom-5:break
            self.command_rects[actions[index]] = pygame.Rect(self.commands_panel.left+6, y, self.commands_panel.width-12, row_height)
            y += row_height
        self.enemy_rows = {}
        self._enemy_label_height = small+13
        if self._group:
            for identifier, slot in self._group_slots().items():
                self.enemy_rows[identifier] = {'row': slot,
                    'name': pygame.Rect(slot.left+4, slot.top+1, slot.width-8, small+1),
                    'hp': pygame.Rect(slot.left+4, slot.top+small+3, slot.width-8, 3),
                    'atb': pygame.Rect(slot.left+4, slot.top+small+7, slot.width-8, 2),
                    'body': self._group_body_area(identifier)}
        else:
            enemy_x = 119 if len(self.model.party) > 1 else 126
            width, height = painter.font('name', bold=True).size(self.model.enemy.name)
            name_rect = pygame.Rect(0, 0, width, height)
            name_rect.center = (enemy_x, 43)
            bar = pygame.Rect(45, 57, 150, 6) if len(self.model.party) > 1 else pygame.Rect(86, 57, 80, 6)
            atb = pygame.Rect(bar.x, 65, bar.width, 2)
            if self.channel_art is not None and self.battlefield=='cave_echo_chamber':
                name_rect.midbottom=(240,114)
                bar=pygame.Rect(165,117,150,5)
                atb=pygame.Rect(165,124,150,2)
            self.enemy_rows['enemy'] = {'row': name_rect.union(bar).union(atb).inflate(6, 4),
                'name': name_rect, 'hp': bar, 'atb': atb}
        return small, name

    @property
    def tutorial_active(self):return bool(self._tutorial_queue)

    @property
    def tutorial_text(self):
        return self._tutorial_queue[0]['text'] if self._tutorial_queue else ''

    def _queue_tutorial(self, key, text, help_text='', speaker='mira'):
        if not self.tutorial or key in self._tutorial_seen:return
        self._tutorial_seen.add(key)
        self._tutorial_queue.append({'key': key, 'text': text, 'help': help_text, 'speaker': speaker})

    def advance_tutorial(self):
        """Acknowledge one line without submitting a combat command."""
        if not self.tutorial_active:return False
        self._tutorial_queue.pop(0)
        self._sound('confirm')
        return True

    def _charging_tutorials(self):
        """Explain preparation before readiness, with a real window afterward.

        Blue is already seated for the guided lessons; no ready-time override
        or compulsory last-second gesture is needed to complete either lesson.
        """
        if (not self.tutorial or self.tutorial_active
                or self.model.phase != 'charging'
                or self.model.charging_boundary_seconds() < 1.):return
        if self.model.gear_available:
            self._queue_tutorial('gear_instruction',
                'Keep your focus ready while you have an opening.',
                'Adjust the gear while ATB charges. Your seated gem locks when ATB fills.')
        if not self.model.rig_reason():
            self._queue_tutorial('rig_instruction',
                'I’ll set the arm rig before I make my move.',
                'Click Mira’s rig or press M while ATB charges. Confirm power before it fills.')

    def _tutorial_event(self, event):
        if getattr(self.model, 'aqua_edge_stage', None) is not None:
            return self._aqua_tutorial_event(event)
        if event['type'] == 'spellblade_interrupted':
            self._tutorial_queue.clear()
            self._queue_tutorial('spellblade_interrupted',
                'Stay down, Cael. I’ll finish this.',
                'Caelan is incapacitated. Mira can continue the battle.')
            return
        if self.model.spellblade_stage is not None:
            return self._spellblade_tutorial_event(event)
        if event['type'] == 'player_ready':
            self._queue_tutorial('readiness',
                'Steady. Get your footing, then strike when you have an opening.',
                'Full ATB: ready to act. Gauges pause while you choose.')
            if event.get('actor') == 'mira':
                self._queue_tutorial('mira_turn',
                    'I can cover you from here.',
                    'Mira is ready. Use her confirmed power allocation, or fire Bolt Shot.')
        elif event['type'] == 'telegraph':
            target = self.model.combatant(event.get('target'))
            name = target.name if target is not None else 'us'
            line = ("It's lowering its head at you, Caelan. Turn with it—don't take it squarely."
                    if event.get('target') == 'player' else
                    "It's coming for me. I'll brace for it.")
            self._queue_tutorial('guard', line,
                'Charge targets '+name+'. Guard reduces the next hit on its user.')
        elif event['type'] == 'impact' and event.get('action') == 'tusker_charge':
            if event.get('guarded'):
                self._queue_tutorial('guard_result',
                    'Good. Back beside me.' if event.get('target') == 'player'
                    else 'That took the worst of it.')
            elif event.get('remaining_hp'):
                self._queue_tutorial('guard_result',
                    'Keep your guard up when it lowers those tusks.')

    def _spellblade_tutorial_event(self, event):
        kind=event['type'];stage=self.model.spellblade_stage
        if kind=='telegraph' and 'guard' not in self._tutorial_seen:
            lines=(('mira','Watch its head. It’s digging in.'),
                   ('caelan','Should I move?'),
                   ('mira','Brace first. Keep the blade between you and its tusks.'))
            for index,(speaker,text) in enumerate(lines):
                self._queue_tutorial('spellblade_guard_'+str(index),text,
                    'Guard halves the next incoming attack.' if index==2 else '',speaker)
            self._tutorial_seen.add('guard')
        elif kind=='player_ready' and event.get('actor')=='player':
            if stage=='guard':
                self._queue_tutorial('readiness','Steady. Get your footing.',
                    'Full ATB: ready to act. Gauges pause while you choose. Select Guard.')
            elif stage=='first_edge':
                self._queue_tutorial('spellblade_choose','Now—while it’s turning. Try drawing through the blue gem.',
                    'Choose Skills → Aqua Edge.')
                self._queue_tutorial('blue_focus_ready',
                    'The blue gem is seated. Keep the blade steady and draw your aether through it.')
        elif kind=='spellblade_failed':
            lines=(('caelan','It didn’t—'),('mira','Stay with me.'),
                   ('caelan','*breathing quickly* I turned it. I’m trying, but nothing’s happening!'),
                   ('mira','Cael, look at the blade. Use it as the focus. Direct your aether through it.'),
                   ('caelan','Wait—there’s something else—'))
            for index,(speaker,text) in enumerate(lines):
                self._queue_tutorial('spellblade_failed_'+str(index),text,'',speaker)
        elif kind=='spellblade_discovered':
            lines=(('caelan','That wasn’t what I was trying to do.'),
                   ('mira','It struck. Can you do that again?'),
                   ('caelan','I think so. But the focus—'),
                   ('mira','Go with it. We’ll work out the rest when we’re clear.'))
            for index,(speaker,text) in enumerate(lines):
                self._queue_tutorial('spellblade_discovered_'+str(index),text,
                    'Learned Aether Edge · 4 MP. Normal party commands are now available.' if index==3 else '',speaker)
        elif kind=='player_ready' and event.get('actor')=='mira' and stage=='complete':
            self._queue_tutorial('mira_turn','I can cover you from here.',
                'Mira is ready. Use her confirmed power allocation, or fire Bolt Shot.')

    def _aqua_tutorial_event(self, event):
        kind = event['type']
        if kind == 'player_ready' and event.get('actor') == 'player' and self.model.aqua_edge_guided:
            self._queue_tutorial('aqua_retry',
                'The blue gem… it’s still resonating. I can feel the aether following the blade.',
                'Choose Skills → Aqua Edge. This first cast costs 0 MP.', 'caelan')
            self._queue_tutorial('aqua_cover',
                'Take your moment, Cael. I’ll cover you.')
        elif kind == 'aqua_edge_discovered':
            self._queue_tutorial('aqua_success',
                'Water! That was what I was trying to do at the mill.', '', 'caelan')
            self._queue_tutorial('aqua_learned',
                'You found the flow. Hold on to that feeling.',
                'Learned Aqua Edge. Free for this battle; 4 MP in later battles. Usable outside the cave too.')

    def _command_label(self, identifier):
        if identifier == 'items':return 'Items'
        if identifier.startswith('item:'):
            key = identifier.split(':', 1)[1]
            return self.model.item_definitions[key]['name']+' ×'+str(self.model.item_counts[key])
        if identifier.startswith('ally:'):
            return self.model.combatant(identifier.split(':', 1)[1]).name
        label = ACTION_LABELS.get(identifier, identifier)
        if identifier in ('aqua_edge', 'flame_edge', 'ice_edge', *RIG_SKILLS):
            cost = self.model.action_mp_cost(identifier, self.model.ready_actor)
            return label+' · '+str(cost)+' MP'
        return label

    def _detail_text(self):
        """Full messages flow beneath the occupied party row, never over values."""
        model = self.model
        if self.command_menu == 'items':
            actions = self._command_actions()
            chosen = actions[self.selected % len(actions)] if actions else ''
            if chosen.startswith('item:'):return model.item_definitions[chosen.split(':', 1)[1]]['description']
        if self.command_menu == 'item_targets':return 'Choose a party member for '+model.item_definitions[self._selected_item]['name']+'.'
        if self.command_menu == 'skill_targets':return 'Choose a living ally for Repair Pulse.'
        if self.rig is not None and self.rig.focused:
            return self.rig.detail_text+' · Arrows: route · Enter: apply · Tab: return'
        if self.result_error:return self.result_error
        if model.phase in RESULTS:
            if model.phase == 'victory':return ''
            if model.phase == 'defeat':
                if self._cave_field is not None:return 'Return to the cave.'
                return ('Return to the safe approach.' if self.battlefield == 'millrace'
                        else 'Return to Eldenmere.')
            return ''
        if model.phase == 'ready':
            actions = self._command_actions()
            if self.command_menu == 'skills' and actions:
                selected = actions[self.selected % len(actions)]
                if selected == 'aether_edge':
                    return '4 MP · Physical and non-elemental magical sword strike.'
                if selected in ('aqua_edge', 'flame_edge', 'ice_edge'):
                    if selected == 'aqua_edge' and self.model.spellblade_guided:
                        return self._command_reason(selected) or 'Try channeling Water through the blue gem.'
                    cost = self.model.action_mp_cost(selected, self.model.ready_actor)
                    element = {'aqua_edge': 'Water', 'flame_edge': 'Fire', 'ice_edge': 'Ice'}[selected]
                    return str(cost)+' MP · Physical sword strike with '+element+' magic.'
                if selected == 'nature_edge':
                    return self._command_reason(selected) or 'Unpractised elemental focus.'
                if selected in RIG_SKILLS:
                    from mira_rig_rules import SKILLS
                    requirement = SKILLS[selected]['requirements']
                    power = ' / '.join(key.title()+' '+str(value) for key, value in requirement.items() if value)
                    effect = {'charged_bolt': 'A powered physical shot.',
                              'bulwark': 'Barrier: 25% maximum HP for two Mira turns.',
                              'repair_pulse': 'Restore HP to one living ally.',
                              'impact_bolt': 'Physical shot and a 10% maximum-HP barrier.',
                              'arc_discharge': 'Electric magical damage.'}[selected]
                    return str(model.action_mp_cost(selected, model.ready_actor))+' MP · '+power+' · '+effect
            return ''
        return model.message if model.phase == 'acting' else 'Preparing the next action.'

    def _sound(self, kind):self.game.ui.sound(kind)

    def _sync_commands(self):
        """A command list belongs only to its current ready party member."""
        context = (self.model.phase, self.model.ready_actor)
        if context != self._command_context:
            previous_actor = self._command_context[1]
            if previous_actor != context[1] and context[1] != 'mira':self._cancel_rig()
            self.command_menu = 'root'
            self.selected = 0
            self._notice = ''
            self._target_command = None
            self._command_context = context

    def _command_actions(self):
        if self.command_menu == 'items':
            return ['item:'+key for key, count in self.model.item_counts.items() if count]+['back']
        if self.command_menu == 'item_targets':
            return ['ally:'+member.identifier for member in self.model.party]+['back']
        if self.command_menu == 'skill_targets':
            return ['ally:'+member.identifier for member in self.model.party]+['back']
        if self.command_menu == 'skills':
            return list(self.model.skill_actions())+['back']
        commands = getattr(self.model, 'command_actions', self.model.available_actions)
        return list(commands())

    def _command_reason(self, identifier):
        if identifier == 'back':return ''
        if identifier.startswith('item:'):return self.model.item_reason(identifier.split(':', 1)[1])
        if identifier.startswith('ally:'):
            target = identifier.split(':', 1)[1]
            return (self.model.action_reason(self._selected_skill, target_id=target)
                    if self.command_menu == 'skill_targets' else self.model.item_reason(self._selected_item, target))
        if identifier in ('skills', 'items'):return self.model.command_reason(identifier)
        return self.model.action_reason(identifier)

    def _set_menu(self, menu):
        self.command_menu = menu
        actions = self._command_actions()
        self.selected = actions.index('skills') if menu == 'root' and 'skills' in actions else 0
        self._notice = ''
        self._command_scroll = 0
        self._layout(self.game.ui.painter(self.game.ui_surface))

    def _selection_notice(self):
        actions = self._command_actions()
        return self._command_reason(actions[self.selected % len(actions)]) if actions else ''

    def _select_member(self, identifier):
        if not self.model.select_ready(identifier):return False
        self._cancel_rig()
        self.command_menu = 'root'
        self._command_context = (self.model.phase, self.model.ready_actor)
        self.selected = 0
        self._notice = ''
        self._target_command = None
        self._command_scroll = 0
        self._layout(self.game.ui.painter(self.game.ui_surface))
        self._sound('move')
        self._tutorial_event({'type': 'player_ready', 'actor': identifier})
        return True

    def _offensive_command(self):
        """Return the pending or highlighted command that can target a foe."""
        if self._target_command is not None:
            identifier = self._target_command
        else:
            actions = self._command_actions()
            if not actions:return None
            identifier = actions[self.selected % len(actions)]
        if identifier == 'attack' or self.model.actions.get(identifier, {}).get('target') == 'opponent':
            return identifier
        return None

    def _execute_enemy_command(self, identifier):
        """A fresh foe click chooses its target and spends exactly one action."""
        if self.model.phase != 'ready' or not self.model.select_target(identifier):return False
        command = self._offensive_command()
        if command is None:
            self._notice = 'Choose an attack or offensive skill.'
            self._sound('move')
            return False
        reason = self._command_reason(command)
        if reason:
            self._notice = reason
            self._sound('back')
            return False
        if not self.model.choose_action(command, target_id=identifier):
            self._notice = self.model.action_reason(command)
            self._sound('back')
            return False
        self._target_command = None
        self._notice = ''
        self._sync_commands()
        self._sound('confirm')
        return True

    def _refresh_enemy_rects(self):
        """Use current visible sprite bounds, including before the first draw."""
        positions = self._positions()
        self.enemy_rects = {}
        for enemy in self._enemy_members():
            actor = enemy.identifier
            if actor not in positions:continue
            state, time = self._pose(actor)
            image, anchor = self.sprites.frame(self._sprite(actor), state, time)
            scale = self._actor_scale(actor)
            rendered = pygame.transform.scale(image, (max(1, round(image.get_width()*scale)),
                                                       max(1, round(image.get_height()*scale))))
            point = positions[actor]
            origin = (round(point.x-anchor[0]*scale), round(point.y-anchor[1]*scale))
            self.enemy_rects[actor] = rendered.get_bounding_rect().move(origin)

    def _enemy_at(self, point):
        """Resolve enemy headers or bodies without reaching through the HUD."""
        field = pygame.Rect(0, 0, 480, self.panel_rect.top)
        if point is None or not field.collidepoint(point):return None
        for identifier, row in self.enemy_rows.items():
            if self.model.combatant(identifier).hp and row['row'].clip(field).collidepoint(point):
                return identifier
        self._refresh_enemy_rects()
        living = [(identifier, rect) for identifier, rect in self.enemy_rects.items()
                  if self.model.combatant(identifier).hp and rect.width and rect.height]
        for padding in (0, 8):
            hits = [(identifier, rect) for identifier, rect in living
                    if rect.inflate(padding, padding).clip(field).collidepoint(point)]
            if hits:
                return min(hits, key=lambda item: pygame.Vector2(item[1].center).distance_squared_to(point))[0]
        return None

    def _confirm(self):
        if self.model.phase == 'victory':return
        if self.model.phase in RESULTS:
            self.dismissed = True
            self._sound('confirm')
            return
        if self.model.phase != 'ready':return
        if self._target_command is not None:
            target = getattr(self.model, 'selected_target', None)
            if target is None or not self.model.combatant(target).hp:
                living = [enemy for enemy in self._enemy_members() if enemy.hp]
                if not living:return
                target = living[0].identifier
                self.model.select_target(target)
            self._execute_enemy_command(target)
            return
        self._sync_commands()
        actions = self._command_actions()
        if not actions:return
        self.selected %= len(actions)
        identifier = actions[self.selected]
        if identifier == 'back':
            self._set_menu('items' if self.command_menu == 'item_targets' else
                           'skills' if self.command_menu == 'skill_targets' else 'root')
            self._sound('back')
            return
        if identifier in ('skills', 'items'):
            reason = self._command_reason(identifier)
            if reason:
                self._notice = reason
                self._sound('back')
            else:
                self._set_menu(identifier)
                self._sound('confirm')
            return
        if identifier.startswith('item:'):
            item_id = identifier.split(':', 1)[1]
            reason = self.model.item_reason(item_id)
            if reason:self._notice = reason;self._sound('back');return
            self._selected_item = item_id
            if self.model.item_definitions[item_id]['effect']['kind'] == 'escape':self._use_item(None)
            else:self._set_menu('item_targets');self._sound('confirm')
            return
        if identifier.startswith('ally:'):
            target = identifier.split(':', 1)[1]
            if self.command_menu == 'skill_targets':self._use_ally_skill(target)
            else:self._use_item(target)
            return
        record = self.model.actions.get(identifier, {})
        if record.get('target') == 'ally':
            reason = self._command_reason(identifier)
            if reason:self._notice = reason;self._sound('back');return
            self._selected_skill = identifier
            self._set_menu('skill_targets');self._sound('confirm');return
        if self._group and (identifier == 'attack' or record.get('target') == 'opponent'):
            reason = self._command_reason(identifier)
            if reason:
                self._notice = reason;self._sound('back');return
            self._target_command = identifier
            self._notice = ''
            living = [enemy for enemy in self._enemy_members() if enemy.hp]
            if living and getattr(self.model, 'selected_target', None) not in [e.identifier for e in living]:
                self.model.select_target(living[0].identifier)
            self._sound('confirm')
            return
        if self.model.choose_action(identifier):
            self._sync_commands()
            self._sound('confirm')
        else:
            self._notice = self.model.action_reason(identifier)
            self._sound('back')

    def _use_item(self, target):
        if self.model.choose_item(self._selected_item, target):
            self._notice = '';self._sync_commands();self._sound('confirm')
        else:
            self._notice = self.model.item_reason(self._selected_item, target);self._sound('back')

    def _use_ally_skill(self, target):
        if self.model.choose_action(self._selected_skill, target_id=target):
            self._notice = '';self._sync_commands();self._sound('confirm')
        else:
            self._notice = self.model.action_reason(self._selected_skill, target_id=target)
            self._sound('back')

    def _apply_rig(self, allocation):
        if not self.rig_enabled or not self.model.set_rig_allocation(allocation):
            self.rig.notice = self.model.rig_reason() or 'The rig cannot be configured right now.'
            self._sound('back')
            return False
        self._notice = ''
        self._sound('confirm')
        return True

    def _cancel_rig(self):
        if self.rig is not None:
            self.rig.cancel();self.rig.focused = False;self.rig._held = False

    @property
    def rig_enabled(self):
        return (self.rig is not None and self.focused and not self.paused
                and not self.dismissed and not self.tutorial_active
                and not self.model.rig_reason())

    @property
    def gear_enabled(self):
        return (self.model.gear_available and not self.dismissed
                and not self.paused and self.focused and not self.tutorial_active)

    @property
    def gear_hover_available(self):
        return self.gear_enabled

    @property
    def atb_multiplier(self):
        return .25 if self.gear_hover_available and self.gear.hovered else 1.0

    def _cancel_gear(self):
        self.gear.active_gem = self.model.active_gem
        self.gear.cancel()
        self.gear.hovered = False
        self.gear.focused = False
        self.model.gear_settling = False

    def _sync_interactable_locks(self):
        """A closed charging window discards every uncommitted local edit."""
        if not self.gear_enabled:self._cancel_gear()
        if self.rig is not None:
            self.rig.sync(self.model.rig_allocation)
            if not self.rig_enabled:self._cancel_rig()
        self.gear.hovered = bool(self.gear_hover_available and self._pointer is not None
                                and self.gear.rect.collidepoint(self._pointer))

    def _commit_gear(self, gem, frame_age=0.):
        if gem is None:return
        if not self.model.set_active_gem(gem):
            self._cancel_gear()
            return
        self._slot_time = self._elapsed-frame_age
        self._gear_adjust_time = self._elapsed-frame_age
        owner = getattr(self.game, 'character_abilities', None)
        if owner is not None and owner.set_active_gem(gem):
            save = getattr(self.game, 'save_progress', None)
            if save is not None:save()

    def _advance_combat(self, seconds):
        """Share one clock across ATB boundaries and a seating completion.

        The model advances first. At equal times readiness wins over a pending
        seat, and the old committed focus is restored without a late callback.
        Action boundaries are split too, so hovering cannot slow an action but
        can slow the charging interval which follows it in the same frame.
        """
        remaining = seconds
        while True:
            self._sync_interactable_locks()
            multiplier = self.atb_multiplier
            charge_boundary = self.model.charging_boundary_seconds(multiplier)
            commit_boundary = self.gear.commit_after_seconds if self.gear_enabled else math.inf
            action = self.model.current_action
            action_boundary = (max(0.,action.duration-action.elapsed)
                if self.model.phase == 'acting' and action is not None else math.inf)
            step = min(remaining, charge_boundary, commit_boundary, action_boundary)
            events_before = len(self.model.events)
            self.model.update(step, atb_multiplier=multiplier)
            remaining = max(0.,remaining-step)
            # Preserve presentation ages across the internal simulation slices.
            for event in self.model.events[events_before:]:
                if 'frame_age' in event:event['frame_age'] += remaining
            self._sync_interactable_locks()
            if self.gear_enabled:
                self._commit_gear(self.gear.update(step, reduced_motion=self.reduced_motion),remaining)
                self.model.gear_settling = self.gear.busy
                for notice in self.gear.consume_notices():
                    self._sound('gear_seat' if notice == 'seat' else 'gear_detent')
            if remaining <= 0 or self.model.phase in RESULTS or self.model.waiting_for_player:return

    def _cycle_target(self, delta):
        enemies = [enemy.identifier for enemy in self._enemy_members() if enemy.hp]
        if not enemies:return False
        current = getattr(self.model, 'selected_target', enemies[0])
        index = enemies.index(current) if current in enemies else 0
        if self.model.select_target(enemies[(index+delta) % len(enemies)]):
            self._sound('move');return True
        return False

    def handle_event(self, event):
        if self.dismissed:return True
        self._layout(self.game.ui.painter(self.game.ui_surface))
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if hasattr(event, 'pos'):
            self._pointer_window = event.pos
            self._pointer = point
            self._hovered_enemy = None
            self.gear.hovered = bool(point is not None and self.gear.rect.collidepoint(point))
        if event.type == pygame.WINDOWLEAVE:
            self._pointer = self._pointer_window = None
            self._hovered_enemy = None
            self.gear.hovered = False
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self.paused = True
            self._held = False
            self._cancel_gear()
            self._cancel_rig()
            self.action_audio.stop()
            self.channel_audio.pause()
            return True
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
            return True
        if (self.tutorial_active and not self.paused
                and not (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)):
            self._cancel_gear()
            self._cancel_rig()
            if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False) and event.key in (
                    pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.advance_tutorial()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._held:
                    self._held = True
                    if point is not None and self.tutorial_continue_rect.collidepoint(point):
                        self.advance_tutorial()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:self._held = False
            return True
        if self.rig is not None:
            if (event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False)
                    and event.key == pygame.K_m and self.rig_enabled):
                self._cancel_gear()
                if self.rig.focused:self._cancel_rig()
                else:self.rig.focused = True;self._notice = ''
                return True
            if self.rig.focused and event.type == pygame.KEYDOWN and event.key in (pygame.K_TAB, pygame.K_g):
                self._cancel_rig()
            elif self.rig.handle_event(event, point, enabled=self.rig_enabled):
                self._cancel_gear();self._notice = ''
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:self._held = False
                return True
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:
                self._cancel_gear()
                if self.focused:
                    if not self.paused and self._target_command is not None:
                        self._target_command = None;self._notice = '';self._sound('back');return True
                    if not self.paused and self.command_menu in ('skills', 'items', 'item_targets', 'skill_targets'):
                        self._set_menu('items' if self.command_menu == 'item_targets' else
                                       'skills' if self.command_menu == 'skill_targets' else 'root')
                        self._sound('back');return True
                    self.paused = not self.paused
                    if self.paused:
                        self._cancel_rig()
                        self.action_audio.stop();self.channel_audio.pause()
                    self._held = False
                    self._sound('back' if self.paused else 'confirm')
                return True
        # The selector receives captured pointer events before character/menu hits.
        if self.gear_enabled:
            consumed = self.gear.handle_event(event, point, enabled=True, reduced_motion=self.reduced_motion)
            self.model.gear_settling = self.gear.busy
            if consumed:
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:self._held = False
                return True
        else:self._cancel_gear()
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            return True
        if self.paused:
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.focused
                    and point is not None and self.resume_rect.collidepoint(point)):
                self.paused = False;self._held = True;self._sound('confirm')
            return True
        if not self.focused:return True
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):self._confirm()
            elif self.model.phase == 'ready' and self._target_command is not None and event.key in (
                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                self._cycle_target(-1 if event.key in (pygame.K_UP, pygame.K_LEFT) else 1)
            elif self.model.phase == 'ready' and event.key == pygame.K_TAB:
                ready = self.model.ready_members
                if ready:
                    index = ready.index(self.model.ready_actor)
                    self._select_member(ready[(index+1) % len(ready)])
            elif self.model.phase == 'ready' and event.key in (
                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                actions = self._command_actions()
                delta = -1 if event.key in (pygame.K_UP, pygame.K_LEFT) else 1
                self.selected = (self.selected+delta) % len(actions) if actions else 0
                self._notice = self._selection_notice();self._sound('move')
            elif event.key == pygame.K_g and self.gear_enabled:
                self.gear.focused = True
                self._notice = 'Gear: Left/Right to turn, Enter to seat, Tab to return.'
        elif event.type == pygame.MOUSEWHEEL and self.model.phase == 'ready':
            if self._pointer is not None and self.commands_panel.collidepoint(self._pointer):
                actions = self._command_actions()
                self.selected = max(0, min(len(actions)-1, self.selected-event.y))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            self.gear.focused = False
            if point is None:return True
            if self.model.phase in RESULTS:
                if self.continue_rect.collidepoint(point):self._confirm()
            elif self.model.phase == 'ready':
                identifier = self._enemy_at(point)
                if identifier is not None:
                    self._execute_enemy_command(identifier)
                    return True
                for identifier, row in self.party_rows.items():
                    if row['row'].collidepoint(point):
                        if self.command_menu == 'item_targets':self._use_item(identifier);return True
                        if self.command_menu == 'skill_targets':self._use_ally_skill(identifier);return True
                        self._select_member(identifier);return True
                if self._target_command is not None:
                    if self._target_confirm_rect.collidepoint(point):self._confirm()
                    elif self._target_cancel_rect.collidepoint(point):
                        self._target_command = None;self._notice = '';self._sound('back')
                    return True
                actions = self._command_actions()
                for identifier, rect in self.command_rects.items():
                    if rect.collidepoint(point):
                        self.selected = actions.index(identifier);self._confirm();break
        elif event.type == pygame.MOUSEMOTION and self.model.phase == 'ready' and point is not None:
            identifier = self._enemy_at(point)
            self._hovered_enemy = identifier
            if identifier is not None:
                self.model.select_target(identifier)
                return True
            if self._target_command is not None:return True
            actions = self._command_actions()
            for identifier, rect in self.command_rects.items():
                if rect.collidepoint(point):
                    self.selected = actions.index(identifier)
                    self._notice = self._selection_notice();break
        return True

    def update(self, seconds):
        self._sync_interactable_locks()
        if self.dismissed or self.paused or not self.focused or self.tutorial_active:
            self.channel_audio.sync(self.model.current_action,paused=True)
            return
        if type(seconds) not in (int, float):raise TypeError('Scene time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid scene time')
        self.channel_audio.sync(self.model.current_action)
        viewport = (self.game.ui_surface.get_size(), getattr(self.game.audio, 'text_scale', 1))
        if viewport != self._viewport:
            self._viewport = viewport
            self._cancel_gear()
            self._layout(self.game.ui.painter(self.game.ui_surface))
        if self._pointer_window is not None:
            self._pointer = self.game.to_canvas(self._pointer_window)
        self.gear.hovered = bool(self.gear_hover_available and self._pointer is not None
                                 and self.gear.rect.collidepoint(self._pointer))
        self._elapsed += seconds
        self.announcements.update(seconds)
        for reaction in self._reactions.values():reaction['age'] += seconds
        self._reactions = {key: value for key, value in self._reactions.items() if value['age'] < .55}
        self._action_cues()
        for popup in self._popups:popup['age'] += seconds
        self._popups = [popup for popup in self._popups if popup['age'] < 1.1]
        self._advance_combat(seconds)
        self._action_cues()
        self._phase_elapsed = (0.0 if self.model.phase != self._last_phase
                               else self._phase_elapsed+seconds)
        roar_impact_cued = False
        for event in self.model.drain_events():
            if event['type'] == 'skill_heal':
                if event['amount']:
                    self._popups.append({'target': event['target'], 'text': '+'+str(event['amount']),
                        'age': event.get('frame_age', 0.), 'healing': True})
                self.action_audio.play('focus')
            elif event['type'] == 'barrier_applied':
                self._popups.append({'target': event['target'], 'text': 'Shield '+str(event['amount']),
                    'age': event.get('frame_age', 0.), 'shield': True})
            elif event['type'] == 'barrier_absorbed':
                self._popups.append({'target': event['target'], 'text': 'Blocked '+str(event['amount']),
                    'age': event.get('frame_age', 0.), 'shield': True, 'offset': 14})
            if event['type'] == 'item_effect':
                if event['amount']:
                    self._popups.append({'target': event['target'], 'text': '+'+str(event['amount'])+
                        (' MP' if event.get('resource') == 'mp' else ''), 'age': event.get('frame_age', 0.),
                        'healing': event.get('resource') != 'mp', 'mp': event.get('resource') == 'mp'})
                self.action_audio.play('focus')
            self.announcements.consume(event)
            self._tutorial_event(event)
            if event['type'] == 'impact':
                age = max(0., event.get('frame_age', 0.))
                self._reactions[event['target']] = {'age': age, 'guarded': event.get('guarded', False),
                    'lethal': not event['remaining_hp'], 'action': event['action']}
                group_spell = event['action'] in ('vespermaw_confluence_roar',
                                                  'embravyr_emberwash', 'nivareth_glassfall')
                if age < .12 and (not group_spell or not roar_impact_cued):
                    metallic = event.get('guarded') and (event['target'] != 'player' or self.model.weapon_equipped)
                    self.action_audio.play('guard_hit' if metallic else 'impact')
                    if group_spell:roar_impact_cued = True
                self._popups.append({'target': event['target'],
                                     'text': str(event['damage']), 'age': age,
                                     'guarded': event.get('guarded', False)})
                if event.get('healing'):
                    self._popups.append({'target': event['target'],
                        'text': '+'+str(event['healing']), 'age': age,
                        'healing': True, 'offset': 14})
                if not event['remaining_hp']:self._defeat_times[event['target']] = self._elapsed-age
            elif event['type'] == 'guard':
                self._popups.append({'target': event.get('actor', 'player'), 'text': 'Guard', 'age': 0.0})
            elif event['type'] == 'enchant':
                self._popups.append({'target': event['actor'], 'text': 'Aether Edge',
                                     'age': 0.0, 'enchant': True})
            elif event['type'] == 'player_ready':
                self.command_menu = 'root'
                self.selected = 0
                self._notice = ''
            elif event['type'] == 'telegraph' and event.get('prepared_action'):
                # Start the held wingbeat after Gather Charge finishes. The
                # model's event age also makes large-frame updates seekable.
                self._enemy_charge_time = (self._elapsed-max(0., event.get('frame_age', 0.))
                                           +event.get('hold_after', 0.))
                self._enemy_charge_times[event.get('actor', 'enemy')] = self._enemy_charge_time
            elif event['type'] == 'recovery_started':
                definition = self.model.actions.get(event.get('action'), {})
                remaining = max(0., definition.get('duration', 0)-definition.get('impact_at', 0))
                self._enemy_recovery_times[event.get('actor', 'enemy')] = (
                    self._elapsed-max(0., event.get('frame_age', 0.))+remaining)
            elif event['type'] == 'recovery_ended':
                self._enemy_recovery_times.pop(event.get('actor', 'enemy'), None)
            elif event['type'] == 'result':
                self._enemy_recovery_times.clear()
                self._enemy_charge_times.clear()
                self._enemy_charge_time = None
        self._popups = [popup for popup in self._popups if popup['age'] < 1.1]
        self._reactions = {key: value for key, value in self._reactions.items() if value['age'] < .55}
        self._sync_commands()
        self._last_phase = self.model.phase
        if self.model.phase in RESULTS or self.tutorial_active:self._cancel_gear()
        self._charging_tutorials()

    @property
    def reduced_motion(self):return getattr(self.game.audio, 'reduced_motion', False)

    def _choreography(self, action=None):
        action = self.model.current_action if action is None else action
        if action is None or not getattr(action, 'choreography', None):return None
        return sample_choreography(action.choreography, action.elapsed, armed=action.weapon_equipped)

    def _action_cues(self):
        action = self.model.current_action
        self.channel_audio.sync(action, paused=self.paused or not self.focused)
        if action is not self._cue_action:
            self._cue_action = action
            self._cue_phases.clear()
        if action is not None and action.action=='vespermaw_attune':return
        if (action is not None and action.actor == 'mira'
                and action.action == 'bolt_shot' and self.mira_art is not None):
            if action.elapsed >= self.mira_art.release_at and 'mira_release' not in self._cue_phases:
                self._cue_phases.add('mira_release')
                self.action_audio.play('focus')
            return
        if action is not None and action.actor == 'mira' and action.action in RIG_SKILLS:
            if action.elapsed >= max(.05, action.impact_at-.18) and 'rig_release' not in self._cue_phases:
                self._cue_phases.add('rig_release')
                self.action_audio.play('focus' if action.kind in ('heal', 'barrier') else 'release')
            return
        if action is not None and self._is_enemy(action.actor) and self._sprite(action.actor) in CAVE_ENEMIES:
            clocks = ({'focus': 0.} if action.kind == 'prepare' else
                      {'focus': 0., 'release': self.action_fx.release_at(action)} if action.kind == 'magical' else
                      {'step': 0., 'swing': action.impact_at*.6, 'land': action.impact_at+.02})
            for cue, boundary in clocks.items():
                key = 'enemy_'+cue
                if action.elapsed >= boundary and key not in self._cue_phases:
                    self._cue_phases.add(key)
                    self.action_audio.play(cue)
            return
        sample = self._choreography(action)
        if sample is None or sample.phase in self._cue_phases:return
        self._cue_phases.add(sample.phase)
        cue = {'approach': 'step', 'strike': 'swing', 'retreat': 'step',
               'land': 'land', 'focus': 'focus', 'release': 'release'}.get(sample.phase)
        if cue:self.action_audio.play(cue)

    def _home_positions(self):
        offset = max(0, 202-self.panel_rect.top)
        if len(self.model.party) == 3:
            # Three native-size silhouettes step upward toward the right edge.
            # Reduce the stagger at the largest native-resolution text setting
            # so the topmost silhouette also remains inside the battlefield.
            stagger = min(1, max(0, (self.panel_rect.top-108)/47))
            positions = {member.identifier: pygame.Vector2(x, self.panel_rect.top-6-(y-6)*stagger)
                         for member, (x, y) in zip(self.model.party,
                                                  ((329, 6), (385, 29), (439, 53)))}
            positions['enemy'] = pygame.Vector2(119, 196-offset)
        elif len(self.model.party) == 2:
            positions = {self.model.party[0].identifier: pygame.Vector2(354, 194-offset),
                         self.model.party[1].identifier: pygame.Vector2(404, 151-offset),
                         'enemy': pygame.Vector2(119, 196-offset)}
        else:
            positions = {'player': pygame.Vector2(354, 184-offset),
                         'enemy': pygame.Vector2(126, 170-offset)}
        if self._group:
            positions.pop('enemy', None)
            for enemy in self._enemy_members():
                identifier = enemy.identifier
                area = self._group_body_area(identifier)
                art, scale = self._enemy_art(identifier), self._actor_scale(identifier)
                bounds, anchor = art['bounds'], art['anchor']
                point = pygame.Vector2(area.centerx-(bounds.centerx-anchor[0])*scale,
                                       area.bottom-(bounds.bottom-anchor[1])*scale)
                positions[identifier] = self._clamp_enemy_position(point, identifier)
        elif hasattr(self.sprites, 'actors'):
            positions['enemy'] = self._clamp_enemy_position(positions['enemy'])
        return positions

    def _group_body_zone(self, actor):
        members = self._enemy_members()
        index = next(index for index, enemy in enumerate(members) if enemy.identifier == actor)
        label = getattr(self, '_enemy_label_height', 21)
        top = 35+math.ceil(len(members)/self._enemy_header_columns())*label+4
        bottom = self.panel_rect.top-5
        columns = (len(members) if bottom-top < 100 or all(self._sprite(enemy.identifier) == 'bat' for enemy in members)
                   else min(2, len(members)))
        rows = math.ceil(len(members)/columns)
        left = 10+round(index % columns*236/columns)
        right = 10+round((index % columns+1)*236/columns)
        row_top = top+round(index//columns*(bottom-top)/rows)
        row_bottom = top+round((index//columns+1)*(bottom-top)/rows)
        return pygame.Rect(left+3, row_top, right-left-6, max(1, row_bottom-row_top-2))

    def _group_body_area(self, actor):
        area = self._group_body_zone(actor)
        space = min(FINGER_SIZE[1]+FINGER_GAP, max(0, area.height-1))
        return pygame.Rect(area.x, area.y+space, area.width, area.height-space)

    def _enemy_body_area(self, actor):
        if self._group:return self._group_body_area(actor)
        top = (70 if self._cave_field is not None else 65)+FINGER_SIZE[1]+FINGER_GAP
        return pygame.Rect(5, top, 470, max(1, self.panel_rect.top-top-3))

    def _target_marker_bounds(self, actor):
        if self._group:return self._group_body_zone(actor)
        top = 70 if self._cave_field is not None else 65
        return pygame.Rect(5, top, 470, max(1, self.panel_rect.top-top-3))

    def _marked_enemy(self):
        if (self.model.phase != 'ready' or self.paused or not self.focused
                or self.tutorial_active or self._offensive_command() is None):return None
        identifier = getattr(self.model, 'selected_target', None)
        enemy = self.model.combatant(identifier)
        return identifier if enemy is not None and self._is_enemy(identifier) and enemy.hp else None

    def _enemy_art(self, actor='enemy'):
        """The complete native occupied bounds, including attack/defeat poses."""
        sprite = self._sprite(actor)
        if sprite not in self.sprites.actors:self.sprites._load_actor(sprite)
        return self.sprites.actors[sprite]

    def _actor_scale(self, actor):
        """Fit only the new large silhouettes between the HP bar and menus.

        Native frames always use nearest-neighbour scaling. Legacy actors keep
        their established 2x presentation; compact accessibility layouts can
        reduce larger species without clipping wings, stone plates or boss poses.
        """
        if not self._is_enemy(actor):return 2.
        if self._group:
            bounds, area = self._enemy_art(actor)['bounds'], self._group_body_area(actor)
            inset = 2 if self._sprite(actor) in ('vespermaw', *ELEMENTALS) else 0
            return min(2., max(1, area.width-4-inset)/max(1, bounds.width),
                       max(1, area.height-2-inset)/max(1, bounds.height))
        # Injected test/preview sprite banks may not supply occupied metadata.
        if not hasattr(self.sprites, 'actors'):return 2.
        bounds = self._enemy_art(actor)['bounds']
        available = self._enemy_body_area(actor).height
        if self._sprite(actor) in ('vespermaw', *ELEMENTALS):available = max(1, available-2)
        return min(2., 224/max(1, bounds.width), available/max(1, bounds.height))

    def _clamp_enemy_position(self, point, actor='enemy', *, moving=False):
        art = self._enemy_art(actor)
        scale = self._actor_scale(actor)
        bounds, anchor = art['bounds'], art['anchor']
        area = (pygame.Rect(5, 35, 470, max(1, self.panel_rect.top-38)) if moving and self._group else
                self._enemy_body_area(actor))
        # A large canvas scaled to a fractional size can gain one raster pixel
        # after both the target size and blit origin round. Keep that pixel in
        # the field rather than overlapping the status panel or target header.
        if self._sprite(actor) in ('vespermaw', *ELEMENTALS):area = area.inflate(-2, -2)
        low = pygame.Vector2(area.left-(bounds.left-anchor[0])*scale,
                             area.top-(bounds.top-anchor[1])*scale)
        high = pygame.Vector2(area.right-(bounds.right-anchor[0])*scale,
                              area.bottom-(bounds.bottom-anchor[1])*scale)
        return pygame.Vector2(max(low.x, min(high.x, point.x)),
                              max(low.y, min(high.y, point.y)))

    def _hit_point(self, actor, positions=None):
        positions = self._home_positions() if positions is None else positions
        point = positions[actor]
        if self._is_enemy(actor):
            if hasattr(self.sprites, 'actors'):
                art = self._enemy_art(actor)
                offset = pygame.Vector2(art['idle_bounds'].center)-art['anchor']
                return point+offset*self._actor_scale(actor)
            return point+((54, -38) if self._sprite(actor) == 'ridgeback_tusker' else (8, -32))
        return point+(0, -36)

    def _contact_position(self, action, positions):
        """Match the authored contact point to the target's near-side silhouette."""
        contact = sample_choreography(action.choreography, action.impact_at,
                                      armed=action.weapon_equipped)
        local = motion_anchors(contact.pose, contact.pose_ms, armed=action.weapon_equipped)
        strike = local.get('strike_point', local['blade_tip'])
        floor = local.get('floor', (32, 56))
        reach = pygame.Vector2(strike)-floor
        return self._hit_point(action.target, positions)-reach*2

    def _ground_positions(self):
        positions = self._home_positions()
        action = self.model.current_action
        sample = self._choreography(action)
        if action is not None and sample is not None:
            if action.kind in ('physical', 'spellblade') and action.target in positions:
                contact = self._contact_position(action, positions)
                blend = 0 if self.reduced_motion else sample.approach
                positions[action.actor] = positions[action.actor].lerp(contact, blend)
        elif (action is not None and action.kind in ('physical', 'spellblade')
              and action.actor != 'mira' and not self.reduced_motion):
            # Other actors keep their established action choreography.
            approach = (action.elapsed/max(.001, action.impact_at)
                        if action.elapsed <= action.impact_at else
                        (action.duration-action.elapsed)/max(.001, action.duration-action.impact_at))
            blend = 1-(1-max(0.0, min(1.0, approach)))**3
            target = positions[action.target]
            if self._is_enemy(action.actor):
                if self._group or self._sprite(action.actor) in CAVE_ENEMIES:
                    art = self._enemy_art(action.actor)
                    bounds, anchor = art['idle_bounds'], art['anchor']
                    reach = pygame.Vector2(bounds.right-anchor[0]-5, bounds.centery-anchor[1])
                    target = self._hit_point(action.target, positions)
                    contact = -reach*self._actor_scale(action.actor)
                else:
                    contact = pygame.Vector2(-96, -4) if self._sprite(action.actor) == 'ridgeback_tusker' else pygame.Vector2(-34, -14)
            elif self._group and self._is_enemy(action.target):
                image, anchor = self.sprites.frame(self._sprite(action.actor), action.animation,
                                                    action.impact_at*1000)
                bounds = image.get_bounding_rect()
                reach = pygame.Vector2(bounds.left+3-anchor[0], bounds.centery-anchor[1])*2
                target = self._hit_point(action.target, positions)
                contact = -reach
            else:contact = pygame.Vector2(83, -4)
            positions[action.actor] = positions[action.actor].lerp(target+contact, blend)
        for actor, record in self._reactions.items():
            if actor not in positions:continue
            sprite = self._sprite(actor)
            reaction = target_reaction(sprite, record['age'], direction=-1 if self._is_enemy(actor) else 1,
                                       reduced_motion=self.reduced_motion, guarded=record['guarded'])
            if reaction['active']:
                positions[actor] += pygame.Vector2(reaction['offset'])*(.5 if record['guarded'] else 1)
        if self._group:
            for enemy in self._enemy_members():
                identifier = enemy.identifier
                moving = action is not None and action.actor == identifier and action.kind in ('physical', 'spellblade')
                positions[identifier] = self._clamp_enemy_position(positions[identifier], identifier, moving=moving)
        elif self._cave_field is not None or self.model.enemy_sprite_id in CAVE_ENEMIES:
            positions['enemy'] = self._clamp_enemy_position(positions['enemy'])
        return positions

    def _positions(self):
        positions = self._ground_positions()
        if not self.reduced_motion:
            for index, enemy in enumerate(self._enemy_members()):
                if self._sprite(enemy.identifier) == 'bat':
                    amount = .5 if self._group else 0 if self._cave_field is not None else 2
                    positions[enemy.identifier].y += math.sin(self._elapsed*4+index)*amount
        sample = self._choreography()
        if sample is not None and not self.reduced_motion:
            positions['player'].y -= sample.elevation
        return positions

    def _camera(self):
        sample = self._choreography()
        if self._group or self.reduced_motion or sample is None:return 1., (0., 0.)
        weight = sample.camera_weight
        zoom = 1+.04*weight
        homes = self._home_positions()
        center = (homes['player']+homes['enemy'])/2+pygame.Vector2(0, -30)
        pan = (pygame.Vector2(240, 125)-center)*(.10*weight)
        offset = pygame.Vector2(240, 160)*(1-zoom)+pan
        offset.x = max(480*(1-zoom), min(0., offset.x))
        offset.y = max(320*(1-zoom), min(0., offset.y))
        return zoom, (offset.x, offset.y)

    def _project(self, point):
        zoom, offset = self._camera()
        return pygame.Vector2(point)*zoom+offset

    def _pose(self, actor):
        combatant = self.model.combatant(actor)
        reaction = self._reactions.get(actor)
        sprite = self._sprite(actor)
        reaction_length = target_reaction(sprite, 0., guarded=bool(reaction and reaction['guarded']))['duration']
        if reaction is not None and reaction['age'] < (.18 if reaction['lethal'] else reaction_length):
            age = reaction['age']
            if actor == 'player':
                return ('guard_impact' if reaction['guarded'] else 'hurt_recover'), age*1000
            if actor == 'mira' and reaction['guarded']:
                return 'guard_impact', age*1000
            if self._is_enemy(actor) and sprite in ('vespermaw', *ELEMENTALS) and not reaction['lethal']:
                frames = self._enemy_art(actor)['animations']['hurt'][0]
                return 'hurt', age/reaction_length*sum(length for _, length in frames)
            return 'hurt', age*1000
        if combatant.hp <= 0:
            return 'defeat', max(0., self._elapsed-self._defeat_times.get(actor, 0)-.18)*1000
        if not self._is_enemy(actor) and self.model.phase == 'victory':return 'victory', self._phase_elapsed*1000
        action = self.model.current_action
        if action is not None and action.actor == actor:
            if sprite=='vespermaw' and action.action=='vespermaw_attune':
                return 'channel', action.elapsed*1000
            if action.kind == 'item':return 'idle', 0 if self.reduced_motion else action.elapsed*1000
            if actor == 'mira' and action.action in RIG_SKILLS:
                return action.action, self.mira_art.action_time(action.action, action.elapsed,
                    action.impact_at, action.duration)
            sequence = self._choreography(action)
            if sequence is not None:return sequence.pose, sequence.pose_ms
            if actor == 'mira' and action.kind == 'guard':
                return 'guard_enter', action.elapsed*1000
            if self._is_enemy(actor) and sprite in CAVE_ENEMIES:
                if sprite == 'lithrusk' and action.kind == 'physical':
                    return self._lithrusk_pose(action, actor)
                if sprite in ('vespermaw', *ELEMENTALS):
                    if action.kind == 'recover':
                        start = self._enemy_recovery_times.setdefault(actor, self._elapsed)
                        return action.animation, 0 if self.reduced_motion else max(0., self._elapsed-start)*1000
                    return self._vespermaw_pose(action, actor)
                return action.animation, action.elapsed*1000
            state = ('aether_edge' if actor == 'player' and action.action == 'aether_edge' else
                     'cast' if action.kind in ('magical', 'enchant', 'failed_edge') else 'guard' if action.kind == 'guard'
                     else 'idle' if action.kind == 'flee' else action.animation
                     if action.animation in ('prepare', 'charge') else 'attack')
            return state, action.elapsed*1000
        if self._is_enemy(actor) and self._telegraphs().get(actor):
            if sprite in ('veylume', 'vespermaw', *ELEMENTALS):
                started = self._enemy_charge_times.get(actor, self._enemy_charge_time)
                start = self._elapsed if started is None else started
                elapsed = max(0., self._elapsed-start)
                return 'charged_hold', 0 if self.reduced_motion else elapsed*1000
            return 'prepare', self._elapsed*1000
        if (self._is_enemy(actor) and sprite in ('vespermaw', *ELEMENTALS)
                and actor in getattr(self.model, 'enemy_recovery_states', {})):
            start = self._enemy_recovery_times.setdefault(actor, self._elapsed)
            recovery = {'vespermaw': 'exhausted', 'embravyr': 'cooling', 'nivareth': 'settling'}[sprite]
            return recovery, 0 if self.reduced_motion else max(0., self._elapsed-start)*1000
        if combatant.guarded:
            return ('guard_enter', 300.) if actor == 'player' else ('guard', self._elapsed*1000)
        if actor == 'player' and self._gear_adjust_time is not None:
            age = self._elapsed-self._gear_adjust_time
            if age < .6:return 'focus_adjust', age*1000
        if self._is_enemy(actor) and sprite == 'veylume' and self._elapsed < .65 and not self.reduced_motion:
            frames = self._enemy_art(actor)['animations']['fly'][0]
            return 'fly', self._elapsed/.65*sum(length for _, length in frames)
        if self._is_enemy(actor) and sprite in ELEMENTALS and self._elapsed < .8 and not self.reduced_motion:
            frames = self._enemy_art(actor)['animations']['emerge'][0]
            return 'emerge', self._elapsed/.8*sum(length for _, length in frames)
        return 'idle', 0 if self.reduced_motion and sprite in CAVE_ENEMIES else self._elapsed*1000

    def _vespermaw_pose(self, action, actor='enemy'):
        """Preserve the complete authored move and its marked contact drawing.

        The art clock is independent of a future action's battle duration. Its
        contact point lands on that action's authoritative impact boundary;
        anticipation and followthrough retain all of their source drawings.
        """
        art = self._enemy_art(actor)
        state = action.animation if action.animation in art['animations'] else 'idle'
        frames = art['animations'][state][0]
        total = sum(length for _, length in frames)
        contact = art['timing'][state]['contact_ms']
        if contact is None:contact = total*action.impact_at/max(.001, action.duration)
        age, impact = max(0., action.elapsed), action.impact_at
        time = (contact*age/max(.001, impact) if age <= impact else
                contact+(total-contact)*(age-impact)/max(.001, action.duration-impact))
        return state, max(0., min(total-1, time))

    def _lithrusk_pose(self, action, actor='enemy'):
        """Show the gait on approach/retreat and every strike drawing at contact.

        The strike clock is piecewise around the authoritative impact boundary;
        the source's contact drawing still lands on the exact damage frame.
        """
        age, duration, impact = action.elapsed, action.duration, action.impact_at
        start, end = .2*duration, .8*duration
        if not self.reduced_motion and (age < start or age >= end):
            return 'walk', max(0., age if age < start else age-end)*1000
        if self.reduced_motion:start, end = 0., duration
        art = self._enemy_art(actor)
        source = art['animations'][action.animation][0]
        milliseconds = sum(length for _, length in source)
        contact = art['timing'][action.animation]['contact_ms']
        if contact is None:contact = impact*1000
        time = (contact*max(0., age-start)/max(.001, impact-start) if age <= impact else
                contact+(milliseconds-contact)*min(1., (age-impact)/max(.001, end-impact)))
        return action.animation, min(milliseconds-1, max(0., time))

    def _vespermaw_channel_state(self):
        state={'element':getattr(self.model,'vespermaw_element','fire')}
        action=self.model.current_action
        if action is not None and action.action=='vespermaw_attune':
            state.update({'from':action.channel_from,'to':action.channel_to,
                          'progress':max(0.,min(1.,action.elapsed/action.duration)),
                          'commit':action.impact_at/action.duration})
        return state

    def _field_offset(self):
        # The echo chamber's three wall crystals are essential combat cues.
        # Keep their authored composition under large-font HUD growth; actor
        # stations already move upward independently with the compact panel.
        if self.battlefield=='cave_echo_chamber':return 0
        return round(max(0,210-self.panel_rect.top)*.5)

    def _draw_field(self, canvas):
        channel_state=self._vespermaw_channel_state()
        field_offset=self._field_offset()
        if self._cave_field is not None:
            self._cave_field.draw(canvas, self._elapsed*1000, self.reduced_motion,
                                  vertical_offset=field_offset,
                                  elemental_state=(channel_state if self.channel_art
                                                   and self.model.phase not in RESULTS else None))
        else:canvas.blit(self._background, (0, 0))
        positions = self._positions()
        ground = self._ground_positions()
        self.enemy_rects = {}
        self.target_marker_rects = {}
        self.charge_aura_rects = {}
        marked = self._marked_enemy()
        charges = {warning['actor']: warning for warning in enemy_charge_warnings(
            self.model, display_name=self._feedback_name)}
        for actor in sorted(positions, key=lambda identifier: ground[identifier].y):
            point = positions[actor]
            self._draw_shadow(canvas, actor, ground[actor])
            state, time = self._pose(actor)
            sprite = self._sprite(actor)
            image, anchor = self.sprites.frame(sprite, state, time)
            if sprite=='vespermaw' and self.channel_art is not None:
                current=self.model.current_action
                if current is not None and current.actor==actor and current.action=='vespermaw_attune':
                    image,anchor=self.channel_art.channel_frame(current.elapsed*1000,
                        current.channel_from,current.channel_to,reduced_motion=self.reduced_motion)
                else:image=self.channel_art.tint(image,channel_state['element'])
            if actor == 'player':
                sequence = self._choreography()
                if sequence is not None or state in MOTION_STATES:
                    image, anchor = motion_frame(state, time, armed=self.model.weapon_equipped,
                                                 owned_gems=self.model.owned_gems)
                elif self.model.weapon_equipped:
                    from gearblade_art import combat_frame
                    image, anchor = combat_frame(image, state, time, owned_gems=self.model.owned_gems)
            scale = self._actor_scale(actor)
            rendered = pygame.transform.scale(image, (max(1, round(image.get_width()*scale)), max(1, round(image.get_height()*scale))))
            origin = (round(point.x-anchor[0]*scale), round(point.y-anchor[1]*scale))
            body = rendered.get_bounding_rect().move(origin)
            if sprite=='vespermaw' and self.channel_art is not None:
                self._draw_channel_stream(canvas,actor,point,scale,foreground=False)
            aura_bounds = None
            if actor in charges and body.width and body.height:
                aura_bounds = (pygame.Rect(0, 35, 480, max(1, self.panel_rect.top-35))
                    if charges[actor].get('stage') == 'release' else self._target_marker_bounds(actor))
                self.charge_aura_rects[actor] = self.charge_aura.draw(canvas, body, self._elapsed,
                    actor_key=actor, reduced_motion=self.reduced_motion, bounds=aura_bounds)
            if actor == marked and body.width and body.height:
                bounds = self._target_marker_bounds(actor)
                # A fixed idle footprint keeps the floor ring from breathing
                # with flying enemies' wingbeats and their idle bob.
                footprint = body
                if hasattr(self.sprites, 'actors'):
                    art = self._enemy_art(actor)
                    idle = art['idle_bounds']
                    home = self._home_positions()[actor]
                    footprint = pygame.Rect(round(home.x+(idle.x-art['anchor'][0])*scale),
                        round(home.y+(idle.y-art['anchor'][1])*scale),
                        max(1, round(idle.width*scale)), max(1, round(idle.height*scale)))
                floor = ground[actor].copy()
                if self._sprite(actor) == 'bat' and not self._group and self._cave_field is None:
                    floor.y = self._home_positions()[actor].y+14
                self.target_marker_rects = target_marker_geometry(body, floor, bounds=bounds)
                self.target_marker_rects['ring'] = draw_target_ring(canvas, footprint, floor, bounds=bounds)
            canvas.blit(rendered, origin)
            if sprite=='vespermaw' and self.channel_art is not None:
                if self.model.combatant(actor).hp:
                    self.channel_art.draw_motes(canvas,point,scale,channel_state['element'],
                        self._elapsed*1000,reduced_motion=self.reduced_motion)
                self._draw_channel_stream(canvas,actor,point,scale,foreground=True)
            if aura_bounds is not None:
                self.charge_aura.draw(canvas, body, self._elapsed, actor_key=actor,
                    reduced_motion=self.reduced_motion, bounds=aura_bounds, foreground=True)
            if self._is_enemy(actor):
                self.enemy_rects[actor] = body
            if actor == 'player' and self.model.weapon_equipped and self.model.player.hp:
                current = self.model.current_action
                own_action = current if current is not None and current.actor == 'player' else None
                context = ({key: getattr(own_action, key) for key in
                            ('action', 'kind', 'elapsed', 'duration', 'impact_at')}
                           if own_action is not None else {})
                from gear_state import REQUIRED_GEMS
                mastered = any(key in self.model.learned_abilities and gem == self.model.active_gem
                               for key, gem in REQUIRED_GEMS.items())
                context['unmastered'] = not mastered and context.get('action') != 'aether_edge'
                # Aqua shares the authored sword motion, while the light keeps
                # its Water identity even during an Aether-shaped pose.
                if context.get('action') in ('aqua_edge', 'flame_edge', 'ice_edge'):
                    context['elemental'] = True
                self.gear_fx.draw(canvas, point, state, time, self.model.active_gem, self._elapsed,
                    slot_age=None if self._slot_time is None else self._elapsed-self._slot_time,
                    action=context, reduced_motion=self.reduced_motion,
                    owned_gems=self.model.owned_gems)
        action = self.model.current_action
        if action is not None and getattr(action, 'choreography', None):
            sequence = self._choreography(action)
            point = positions[action.actor]
            local = motion_anchors(sequence.pose, sequence.pose_ms, armed=action.weapon_equipped)
            origin = pygame.Vector2(point)-pygame.Vector2(32,56)*2
            attachment = {key: origin+pygame.Vector2(value)*2 for key,value in local.items()
                          if isinstance(value, (tuple,list)) and len(value) == 2}
            attachment.update(show_impact=False, target_hit=self._hit_point(action.target, positions)
                              if action.target in positions else point,
                              dash_origin=self._home_positions()[action.actor],
                              landing=self._home_positions()[action.actor],
                              dash_at=.46 if action.choreography == 'aether_edge' else .14,
                              landing_at=1.8 if action.choreography == 'aether_edge' else 1.25)
            self.action_fx.draw(canvas, point, positions.get(action.target,point), action,
                                anchors=attachment, reduced_motion=self.reduced_motion)
        for actor, reaction in self._reactions.items():
            if actor in positions:
                self.action_fx.draw_impact(canvas, self._hit_point(actor, positions), reaction['age'],
                                           reaction['action'], reduced_motion=self.reduced_motion)
        if action is not None and action.kind == 'enchant':
            point = positions[action.actor]+(0, -34)
            pulse = 0 if self.reduced_motion else round(math.sin(action.elapsed*10)*2)
            pygame.draw.circle(canvas, '#5da9e9', (round(point.x), round(point.y)), 15+pulse, 1)
            pygame.draw.circle(canvas, '#b1e4ff', (round(point.x), round(point.y)-18), 2)
        self._draw_mira_effects(canvas)
        self._draw_rig_skill_effects(canvas, positions)
        self._draw_rig_barriers(canvas, positions)
        self._draw_cave_enemy_effects(canvas, positions)
        self._draw_elemental_effects(canvas, positions)
        self._draw_item_effects(canvas, positions)
        self._draw_vespermaw_roar(canvas, positions)
        if marked is not None and self.target_marker_rects:
            self.target_marker_rects['finger'] = draw_target_finger(canvas, self.enemy_rects[marked],
                bounds=self._target_marker_bounds(marked))
        if (action is not None and action.kind == 'magical' and not action.resolved
                and not getattr(action, 'choreography', None)
                and action.target in positions
                and action.action not in RIG_SKILLS
                and not (self._is_enemy(action.actor) and self._sprite(action.actor) in ('veylume', *ELEMENTALS))):
            fraction = max(0, min(1, action.elapsed/max(.001, action.impact_at)))
            start = positions[action.actor]+(-23 if action.actor == 'player' else 20, -37)
            end = positions[action.target]+(0, -33)
            point = start.lerp(end, fraction)
            for index, radius in enumerate((5, 3, 1)):
                color = ('#376ea2', '#72c8f0', '#d8f7ff')[index]
                pygame.draw.circle(canvas, color, (round(point.x), round(point.y)), radius)
        self._draw_foreground(canvas)

    def _draw_channel_stream(self,canvas,actor,point,scale,*,foreground):
        action=self.model.current_action
        if action is None or action.actor!=actor or action.action!='vespermaw_attune':return
        offset=self._field_offset()
        source=(self._cave_field.crystal_origin(action.channel_to,vertical_offset=offset)
                if self._cave_field is not None else (94,42))
        anchors=self.channel_art.anchors(action.elapsed*1000)
        spine=pygame.Vector2(point)+(pygame.Vector2(anchors.get('spine',(64,80)))-pygame.Vector2(64,128))*scale
        self.channel_fx.draw(canvas,source,spine,point,action,
            bounds=pygame.Rect(0,35,480,max(1,self.panel_rect.top-35)),
            reduced_motion=self.reduced_motion,foreground=foreground)

    def _vespermaw_roar_geometry(self, positions):
        """Sample a mouth-origin wave toward each living opposing character."""
        action = self.model.current_action
        if (action is None or action.action != 'vespermaw_confluence_roar'
                or action.actor not in positions or not self._is_enemy(action.actor)):
            return None
        state, clock = self._pose(action.actor)
        sprite = self._sprite(action.actor)
        art = self._enemy_art(action.actor)
        points = self.sprites.anchors(sprite, state, clock)
        native = points.get('cast_origin', points.get('body', art['anchor']))
        origin = positions[action.actor]+(pygame.Vector2(native)-art['anchor'])*self._actor_scale(action.actor)
        affected = getattr(action, 'targets', ()) or tuple(
            member.identifier for member in self.model.party if member.hp)
        targets = tuple((identifier, self._hit_point(identifier, positions))
                        for identifier in affected if identifier in positions)
        fraction = max(0., min(1., action.elapsed/max(.001, action.impact_at)))
        return {'origin': origin, 'targets': targets, 'fraction': fraction,
                'age': max(0., action.elapsed-action.impact_at)}

    def _draw_vespermaw_roar(self, canvas, positions):
        geometry = self._vespermaw_roar_geometry(positions)
        if geometry is None:return
        origin, fraction = geometry['origin'], geometry['fraction']
        previous = canvas.get_clip()
        canvas.set_clip(pygame.Rect(0, 35, 480, max(1, self.panel_rect.top-35)))
        try:
            colors=CONFLUENCE_COLORS.get(getattr(self.model,'vespermaw_element','water'),
                                         CONFLUENCE_COLORS['water'])
            # Small attached throat light remains static under reduced motion.
            pygame.draw.circle(canvas, colors[1], (round(origin.x), round(origin.y)), 3, 1)
            for _, target in geometry['targets']:
                if self.reduced_motion:
                    if fraction < 1:continue
                    center, radius = target, 6
                else:
                    center = origin.lerp(target, fraction)
                    radius = 4+round(7*fraction)
                for offset, color in ((0, colors[1]), (3, colors[2])):
                    rect = pygame.Rect(round(center.x-radius/2-offset), round(center.y-radius-offset),
                                       radius+offset*2, radius*2+offset*2)
                    pygame.draw.arc(canvas, color, rect, -1.15, 1.15, 1)
        finally:
            canvas.set_clip(previous)

    def _draw_cave_enemy_effects(self, canvas, positions):
        for enemy in self._enemy_members():
            identifier = enemy.identifier
            if self._sprite(identifier) != 'veylume' or not enemy.hp:continue
            art = self._enemy_art(identifier)
            bounds, anchor = art['idle_bounds'], art['anchor']
            scale = self._actor_scale(identifier)
            origin = positions[identifier]+pygame.Vector2(bounds.right-anchor[0]-8,
                                                          bounds.centery-anchor[1]-6)*scale
            action = self.model.current_action
            if (action is not None and action.actor == identifier
                    and action.kind == 'magical' and action.target in positions):
                self.action_fx.draw(canvas, positions[identifier], positions[action.target], action,
                                    anchors={'cast_origin': origin, 'release_origin': origin,
                                             'target_hit': self._hit_point(action.target, positions),
                                             'show_impact': False}, reduced_motion=self.reduced_motion)
            if (self._telegraphs().get(identifier) or action is not None and action.actor == identifier
                    and action.kind == 'prepare'):
                elapsed = action.elapsed if action is not None and action.actor == identifier else self._elapsed
                self.action_fx.draw_electric_charge(canvas, origin, elapsed,
                                                   reduced_motion=self.reduced_motion)

    def _draw_item_effects(self, canvas, positions):
        action = self.model.current_action
        if action is None or action.kind != 'item':return
        key = action.action.split(':', 1)[1]
        kind = self.model.item_definitions[key]['effect']['kind']
        target = action.actor if kind == 'escape' else action.target
        if target not in positions:return
        if not hasattr(self, '_item_layer'):
            self._item_layer = pygame.Surface((480, 320), pygame.SRCALPHA)
        layer = self._item_layer;layer.fill((0, 0, 0, 0))
        layer.set_clip(pygame.Rect(0, 35, 480, max(1, self.panel_rect.top-35)))
        center = self._hit_point(target, positions)
        progress = max(0., min(1., action.elapsed/action.duration))
        rgb = ((175, 185, 177) if kind == 'escape' else (108, 184, 239) if kind == 'restore_mp'
               else (245, 208, 111) if kind == 'revive' else (125, 226, 157))
        alpha = round(190*(1-progress*.6))
        if self.reduced_motion:
            pygame.draw.circle(layer, (*rgb, alpha), (round(center.x), round(center.y)), 12, 2)
        elif kind == 'escape':
            for index in range(7):
                point = center+pygame.Vector2((index-3)*(5+progress*5), -progress*index*3)
                pygame.draw.circle(layer, (*rgb, alpha//2), (round(point.x), round(point.y)), 8+round(progress*12))
        else:
            for index in range(8):
                angle = index*math.tau/8+progress*1.3
                point = center+pygame.Vector2(math.cos(angle), math.sin(angle))*(10+progress*15)
                pygame.draw.circle(layer, (*rgb, alpha), (round(point.x), round(point.y)), 2)
            pygame.draw.circle(layer, (*rgb, alpha//2), (round(center.x), round(center.y)), 9+round(progress*10), 1)
        canvas.blit(layer, (0, 0))

    def _draw_elemental_effects(self, canvas, positions):
        """Attach elemental casts to authored cores and show cooling/melting."""
        previous = canvas.get_clip()
        field = pygame.Rect(0, 35, 480, max(1, self.panel_rect.top-35))
        canvas.set_clip(field)
        try:
            action = self.model.current_action
            if (action is not None and self._is_enemy(action.actor)
                    and self._sprite(action.actor) in ELEMENTALS and action.kind == 'magical'):
                actor = action.actor
                art = self._enemy_art(actor)
                state, clock = self._pose(actor)
                points = self.sprites.anchors(self._sprite(actor), state, clock)
                native = points.get('cast_origin', points.get('core',
                    points.get('body', art['idle_bounds'].center)))
                origin = positions[actor]+(pygame.Vector2(native)-art['anchor'])*self._actor_scale(actor)
                targets = getattr(action, 'targets', ()) or (
                    tuple(member.identifier for member in self.model.party if member.hp)
                    if action.target == 'all_opponents' else (action.target,))
                for target in targets:
                    if target not in positions:continue
                    self.action_fx.draw(canvas, positions[actor], positions[target], action,
                        anchors={'cast_origin': origin, 'release_origin': origin,
                                 'target_hit': self._hit_point(target, positions), 'show_impact': False},
                        reduced_motion=self.reduced_motion)
            layer = self._elemental_layer
            layer.fill((0, 0, 0, 0))
            layer.set_clip(field)
            for actor, reaction in self._reactions.items():
                if actor not in positions or not self._is_enemy(actor):continue
                sprite, move = self._sprite(actor), reaction['action']
                steam = sprite == 'embravyr' and move in ('aqua_edge', 'ice_edge')
                melt = sprite == 'nivareth' and move == 'flame_edge'
                if not (steam or melt):continue
                age = reaction['age']
                if not 0 <= age < .5:continue
                point = self._hit_point(actor, positions)
                fraction = age/.5
                alpha = round((1-fraction)*190)
                if self.reduced_motion:
                    pygame.draw.circle(layer, (195, 235, 245, alpha),
                                       (round(point.x), round(point.y)), 7, 1)
                    continue
                for index in range(7):
                    spread = (index-3)*4
                    x = point.x+spread+math.sin(index*1.7+fraction*2)*3
                    y = point.y-4-fraction*(10+index%3*4) if steam else point.y+fraction*(9+index%3*3)
                    if steam:
                        pygame.draw.circle(layer, (215, 235, 238, alpha),
                                           (round(x), round(y)), 2+index%2)
                    else:
                        pygame.draw.line(layer, (196, 238, 250, alpha),
                                         (round(x), round(y-2)), (round(x), round(y+2)), 1)
                        if index%2 == 0:
                            pygame.draw.circle(layer, (248, 165, 86, alpha),
                                               (round(x+2), round(y-4)), 1)
            canvas.blit(layer, (0, 0))
        finally:
            canvas.set_clip(previous)

    def _mira_shot(self):
        action = self.model.current_action
        if (self.mira_art is None or action is None or action.actor != 'mira'
                or action.action != 'bolt_shot'):
            return None
        homes = self._home_positions()
        return self.mira_art.shot(action.elapsed, action.impact_at, homes['mira'],
                                  self._hit_point(action.target, homes), resolved=action.resolved)

    def _draw_mira_effects(self, canvas):
        shot = self._mira_shot()
        if shot is not None:
            if shot['projectile'] is not None:
                point = pygame.Vector2(shot['projectile'])
                direction = pygame.Vector2(shot['target']) - pygame.Vector2(shot['origin'])
                direction = direction.normalize() if direction.length_squared() else pygame.Vector2(-1, 0)
                tail = point-direction*7
                pygame.draw.line(canvas, '#bd8751', tuple(round(n) for n in tail),
                                 tuple(round(n) for n in point), 2)
                pygame.draw.line(canvas, '#f1cd77', tuple(round(n) for n in point-direction*3),
                                 tuple(round(n) for n in point), 1)
            if shot['flash'] and not self.reduced_motion:
                x, y = (round(n) for n in shot['muzzle'])
                # A small spring-release glint, not a firearm's fireball.
                pygame.draw.line(canvas, '#f1cd77', (x-3, y-2), (x-1, y-1), 1)
                pygame.draw.line(canvas, '#f8f0d9', (x-3, y+2), (x-1, y+1), 1)
    def _rig_skill_geometry(self, positions=None):
        """Read-only skill attachments sampled from the authoritative action."""
        action = self.model.current_action
        if (self.mira_art is None or action is None or action.actor != 'mira'
                or action.action not in RIG_SKILLS):return None
        positions = self._positions() if positions is None else positions
        key = action.action
        attachment = 'tool' if key == 'repair_pulse' else 'projector' if key == 'bulwark' else 'muzzle'
        clock = self.mira_art.action_time(key, action.elapsed, action.impact_at, action.duration)
        current = pygame.Vector2(self.mira_art.world_anchor(key, clock, attachment, positions['mira']))
        release_at = max(.05, action.impact_at-.18)
        release_clock = self.mira_art.action_time(key, release_at, action.impact_at, action.duration)
        origin = pygame.Vector2(self.mira_art.world_anchor(key, release_clock, attachment, positions['mira']))
        target_id = action.actor if key == 'bulwark' else action.target
        if target_id not in positions:return None
        target = self._hit_point(target_id, positions)
        traveling = release_at <= action.elapsed < action.impact_at and not action.resolved
        fraction = ((action.elapsed-release_at)/(action.impact_at-release_at)) if traveling else None
        return {'key': key, 'action': action, 'origin': origin, 'attachment': current,
                'target': pygame.Vector2(target), 'target_id': target_id,
                'fraction': fraction, 'release_at': release_at}

    def _draw_rig_skill_effects(self, canvas, positions):
        geometry = self._rig_skill_geometry(positions)
        if geometry is None:return
        action, key = geometry['action'], geometry['key']
        layer = self._rig_layer;layer.fill((0, 0, 0, 0))
        layer.set_clip(pygame.Rect(0, 35, 480, max(1, self.panel_rect.top-35)))
        origin, attachment, target = geometry['origin'], geometry['attachment'], geometry['target']
        fraction = geometry['fraction']
        color = ((134, 221, 158) if key == 'repair_pulse' else
                 (126, 221, 237) if key in ('bulwark', 'arc_discharge') else (246, 193, 103))
        def point(value):return round(value[0]), round(value[1])
        if action.elapsed < action.impact_at:
            strength = min(1., action.elapsed/max(.001, geometry['release_at']))
            pygame.draw.circle(layer, (*color, 80), point(attachment), 3+round(strength*2), 1)
            pygame.draw.circle(layer, (*color, 235), point(attachment), 1)
            if not self.reduced_motion:
                for index in range(3):
                    angle = index*math.tau/3+action.elapsed*5
                    mote = attachment+pygame.Vector2(math.cos(angle), math.sin(angle))*(6-strength*3)
                    pygame.draw.circle(layer, (*color, 155), point(mote), 1)
        if fraction is not None:
            projectile = origin.lerp(target, fraction)
            if key in ('charged_bolt', 'impact_bolt'):
                direction = target-origin
                direction = direction.normalize() if direction.length_squared() else pygame.Vector2(-1, 0)
                pygame.draw.line(layer, (*color, 230), point(projectile-direction*9), point(projectile), 2)
                pygame.draw.line(layer, (255, 247, 215, 245), point(projectile-direction*3), point(projectile), 1)
            elif key == 'repair_pulse':
                if not self.reduced_motion:
                    pygame.draw.line(layer, (*color, 55), point(origin), point(target), 1)
                    for index in range(4):
                        mote = origin.lerp(target, max(0., min(1., fraction-index*.12)))
                        pygame.draw.circle(layer, (*color, 225-index*35), point(mote), 1)
                else:pygame.draw.circle(layer, (*color, 175), point(target), 9, 1)
            elif key == 'arc_discharge':
                nodes = [point(origin)]
                for index in range(1, 7):
                    node = origin.lerp(projectile, index/7)
                    if not self.reduced_motion:node.y += math.sin(index*2.7+action.elapsed*40)*3
                    nodes.append(point(node))
                nodes.append(point(projectile))
                pygame.draw.lines(layer, (*color, 225), False, nodes, 1)
                pygame.draw.circle(layer, (225, 249, 255, 225), point(projectile), 2)
            elif key == 'bulwark':
                pygame.draw.line(layer, (*color, 115), point(origin), point(target), 1)
                self._rig_hex(layer, target, 9+round(fraction*15), (*color, 150))
        # Impact decoration never precedes the actual impact. Lasting shields
        # are rendered separately from the live, remaining barrier pool.
        impact_age = action.elapsed-action.impact_at
        if action.resolved and 0 <= impact_age < .18:
            radius = 8 if self.reduced_motion else 6+round(impact_age*45)
            pygame.draw.circle(layer, (*color, 180), point(target), radius, 1)
            if key == 'repair_pulse':
                pygame.draw.line(layer, (*color, 220), point(target+(-3, 0)), point(target+(3, 0)), 1)
                pygame.draw.line(layer, (*color, 220), point(target+(0, -3)), point(target+(0, 3)), 1)
        canvas.blit(layer, (0, 0))

    @staticmethod
    def _rig_hex(layer, center, radius, color):
        vertices = [(round(center.x+math.cos(index*math.tau/6)*radius),
                     round(center.y+math.sin(index*math.tau/6)*radius*1.2)) for index in range(6)]
        pygame.draw.polygon(layer, (*color[:3], min(28, color[3])), vertices)
        pygame.draw.polygon(layer, color, vertices, 1)

    def _draw_rig_barriers(self, canvas, positions):
        layer = self._rig_layer;layer.fill((0, 0, 0, 0))
        layer.set_clip(pygame.Rect(0, 35, 480, max(1, self.panel_rect.top-35)))
        any_barrier = False
        for member in self.model.party:
            if not member.hp or not getattr(member, 'barrier', 0):continue
            center = self._hit_point(member.identifier, positions)
            self._rig_hex(layer, center, 23, (131, 215, 235, 135))
            any_barrier = True
        if any_barrier:canvas.blit(layer, (0, 0))

    @staticmethod
    def _bar(painter, rect, fraction, color):
        painter.rect(FOREST_DARK, rect)
        inner = pygame.Rect(rect).inflate(-2, -2)
        inner.width = round(inner.width*max(0, min(1, fraction)))
        if inner.width:painter.rect(color, inner)
        painter.rect(BRASS, rect, 1)

    @staticmethod
    def _health_color(current, maximum):
        if current*4 <= maximum:return HP_RED
        if current*2 <= maximum:return HP_YELLOW
        return HP_GREEN

    def _draw_enemy_status(self, painter):
        model = self.model
        if not self._group:
            enemy = model.enemy
            if self.channel_art is not None and self.battlefield=='cave_echo_chamber':
                # Center the boss readout beneath the middle crystal, leaving
                # all three silhouettes and their pulse unobscured.
                painter.text(enemy.name,(241,115),role='name',color=FOREST_DARK,
                             anchor='midbottom',bold=True)
                painter.text(enemy.name,(240,114),role='name',anchor='midbottom',bold=True)
                self._bar(painter,pygame.Rect(165,117,150,5),enemy.hp/enemy.value('hp'),'#9ab46b')
                self._enemy_atb(painter,pygame.Rect(165,124,150,2),enemy.atb)
                return
            enemy_x = 119 if len(model.party) > 1 else 126
            painter.text(enemy.name, (enemy_x+1, 44), role='name', color=FOREST_DARK, anchor='center', bold=True)
            painter.text(enemy.name, (enemy_x, 43), role='name', anchor='center', bold=True)
            enemy_bar = pygame.Rect(45, 57, 150, 6) if len(model.party) > 1 else pygame.Rect(86, 57, 80, 6)
            self._bar(painter, enemy_bar, enemy.hp/enemy.value('hp'), '#9ab46b')
            if self._cave_field is not None:
                self._enemy_atb(painter, pygame.Rect(enemy_bar.x, 65, enemy_bar.width, 2), enemy.atb)
            return
        action = model.current_action
        if action is not None and action.kind in ('physical', 'spellblade'):
            # Give approaching bodies a clear lane through the formation.
            # The attacked foe's status stays in the free upper header;
            # formation nameplates return when everyone is at home.
            identifier = action.target if self._is_enemy(action.target) else action.actor
            if self._is_enemy(identifier):
                enemy = model.combatant(identifier)
                painter.text(self._enemy_name(identifier), (14, 36), role='small', color=GOLD, bold=True)
                self._bar(painter, pygame.Rect(14, 51, 246, 4), enemy.hp/enemy.max_hp, '#9ab46b')
                self._enemy_atb(painter, pygame.Rect(14, 57, 246, 2), enemy.atb)
            return
        selected = getattr(model, 'selected_target', None)
        for enemy in self._enemy_members():
            identifier = enemy.identifier
            row = self.enemy_rows[identifier]
            header = pygame.Rect(row['name'].left-2, row['name'].top-1,
                                 row['name'].width+4, row['atb'].bottom-row['name'].top+3)
            painter.rect(FOREST_DARK, header)
            label = self._enemy_name(identifier)
            font = painter.font('small', bold=True)
            while len(label) > 2 and font.size(label)[0] > row['name'].width:
                label = label[:-2]+'…'
            painter.text(label, row['name'].topleft, role='small', bold=True,
                         color=GOLD if enemy.hp else MUTED)
            self._bar(painter, row['hp'], enemy.hp/enemy.max_hp, '#9ab46b')
            self._enemy_atb(painter, row['atb'], enemy.atb)
            if selected == identifier and enemy.hp and model.phase == 'ready':
                painter.rect(GOLD, row['row'], 1)

    @staticmethod
    def _enemy_atb(painter, rect, value):
        painter.rect(FOREST, rect)
        fill = pygame.Rect(rect)
        fill.width = round(fill.width*max(0., min(1., value)))
        if fill.width:painter.rect(ATB_YELLOW, fill)

    def _draw_announcement(self, painter):
        message = self.announcements.current
        action=self.model.current_action
        if action is not None and action.action=='vespermaw_attune':
            message={'text':'Vespermaw — '+action.channel_to.title()+' Confluence',
                     'kind':'ability','age':action.elapsed,'duration':action.duration}
        target = self._marked_enemy()
        text = (message['text'] if message is not None else
                'Target: '+self._enemy_name(target) if target is not None else self.location_name)
        rect = self.announcement_rect
        painter.panel(rect)
        color = '#ffb0a0' if message and message.get('kind') == 'warning' else GOLD
        if message and message.get('kind') == 'warning':painter.rect('#c84b4a', rect, 1)
        line_height = painter.font(bold=True).get_linesize()
        capacity = max(1, (rect.height-6)//line_height)
        lines = painter.wrap(text, rect.width-18, bold=True)
        # Keep a warning's direction cue with its target on the next page.
        # Wrapping may otherwise strand an arrow at the end of the first line.
        for index in range(len(lines)-1):
            if lines[index].rstrip().endswith(' →'):
                lines[index] = lines[index].rstrip()[:-2].rstrip()
                lines[index+1:index+2] = painter.wrap('→ '+lines[index+1],
                                                     rect.width-18, bold=True)
        pages = max(1, math.ceil(len(lines)/capacity))
        age = max(0., float(message.get('age', 0.))) if message else 0.
        duration = max(.01, float(message.get('duration', pages*2.5))) if message else pages*2.5
        page = min(pages-1, int(age*pages/duration))
        visible = lines[page*capacity:(page+1)*capacity]
        y = rect.centery-len(visible)*line_height/2
        self.announcement_text_rects = []
        painter.clip(rect.inflate(-8, -2))
        for line in visible:
            self.announcement_text_rects.append(painter.text(line, (rect.centerx, y),
                color=color, anchor='midtop', bold=True))
            y += line_height
        painter.clip()

    def draw(self, world_canvas, ui_surface):
        painter = self.game.ui.painter(ui_surface)
        small, name = self._layout(painter)
        self._draw_field(world_canvas)
        zoom, offset = self._camera()
        if zoom != 1:
            field = pygame.transform.scale(world_canvas, (round(480*zoom), round(320*zoom)))
            world_canvas.blit(field, (round(offset[0]), round(offset[1])))
        pygame.transform.scale(world_canvas, ui_surface.get_size(), ui_surface)
        model, player, enemy = self.model, self.model.player, self.model.enemy
        self._draw_enemy_status(painter)
        self._draw_announcement(painter)
        positions = self._positions()
        for popup in self._popups:
            if popup['target'] not in positions:continue
            if self._group and self._is_enemy(popup['target']):
                point = self._hit_point(popup['target'], positions)+(0, -12)
            else:
                point = positions[popup['target']]+(0, -(88 if self._is_enemy(popup['target'])
                    and self._sprite(popup['target']) == 'ridgeback_tusker' else 75))
            x, y = self._project(point)
            y -= popup.get('offset', 0)
            y -= 0 if self.reduced_motion else min(14, popup['age']*20)
            popup_width, popup_height = painter.font('name', bold=True).size(popup['text'])
            x = max(popup_width/2+2, min(478-popup_width/2, x))
            y = max(popup_height/2+2, min(self.panel_rect.top-popup_height/2-2, y))
            painter.text(popup['text'], (x+1, y+1), role='name', color=FOREST_DARK, anchor='center', bold=True)
            painter.text(popup['text'], (x, y), role='name',
                         color=HP_GREEN if popup.get('healing') else MP_BLUE if popup.get('enchant') or popup.get('mp') or popup.get('shield') else GOLD,
                         anchor='center', bold=True)
        self.barrier_badges = {}
        for member in model.party:
            if not member.hp or not getattr(member, 'barrier', 0):continue
            point = self._project(positions[member.identifier])
            label = 'Shield '+str(member.barrier)+' · '+str(member.barrier_turns)+'t'
            width, height = painter.font('small', bold=True).size(label)
            x = max(width/2+3, min(477-width/2, point.x))
            y = min(self.panel_rect.top-3, point.y+10)
            badge = pygame.Rect(round(x-width/2-3), round(y-height-2), width+6, height+3)
            painter.rect(FOREST_DARK, badge);painter.rect(MP_BLUE, badge, 1)
            self.barrier_badges[member.identifier] = painter.text(label, (x, y), role='small',
                color='#a8e2ef', anchor='midbottom', bold=True)
        for member in model.party:
            hits = getattr(member, 'aether_edge_hits', 0)
            if not hits or not member.hp:continue
            point = self._project(positions[member.identifier])
            cue = 'Edge · '+str(hits)+(' strike' if hits == 1 else ' strikes')
            cue_point = (point.x, min(point.y+20, self.panel_rect.top-8))
            painter.text(cue, (cue_point[0]+1, cue_point[1]+1), role='small',
                         color=FOREST_DARK, anchor='midbottom', bold=True)
            painter.text(cue, cue_point, role='small', color=MP_BLUE, anchor='midbottom', bold=True)
        if model.phase == 'victory':
            # The encounter owner advances this celebration to Spoils of Battle.
            # Rewards and an exit command belong to that separate screen.
            banner_height = max(46, painter.font('title', bold=True).get_linesize()+20)
            self.victory_banner_rect = pygame.Rect(66, 86, 348, banner_height)
            painter.panel(self.victory_banner_rect)
            painter.text('VICTORY', self.victory_banner_rect.center, role='title',
                         color=GOLD, anchor='center', bold=True)
            if self.paused:
                painter.veil(150)
                painter.panel((124, 111, 232, 100))
                painter.text('Battle paused', (240, 126), color=GOLD, anchor='midtop', bold=True)
                painter.button(self.resume_rect, 'Resume', disabled=not self.focused)
            painter.clip()
            return
        painter.panel(self.panel_rect)
        top = self.panel_rect.top
        heading = ({'defeat': 'DEFEATED', 'fled': 'ESCAPED'}.get(model.phase)
                   or ('TARGET' if self._target_command is not None else '')
                   or {'skills': 'SKILLS', 'items': 'ITEMS', 'item_targets': 'RECIPIENT',
                       'skill_targets': 'RECIPIENT'}.get(self.command_menu, 'COMMANDS'))
        painter.text(heading, (self.commands_panel.centerx, top+5), role='small',
                     color=GOLD, anchor='midtop', bold=True)
        self.header_rects = {}
        for member in model.party:
            row = self.party_rows[member.identifier]
            if model.phase == 'ready' and model.ready_actor == member.identifier:
                painter.rect(FOREST_LIGHT, row['row'])
                painter.rect(GOLD, row['row'], 1)
            painter.text(member.name, row['name'].topleft, role='small',
                         color=GOLD if member.hp else MUTED, bold=True)
            self._bar(painter, row['atb'], member.atb, ATB_YELLOW)
            for label, value, maximum, key, color in (
                    ('HP', member.hp, member.max_hp, 'hp', self._health_color(member.hp, member.max_hp)),
                    ('MP', member.mp, member.max_mp, 'mp', MP_BLUE)):
                text_rect = row[key+'_text']
                self.header_rects[label] = painter.text(
                    label+' '+str(value)+'/'+str(maximum), text_rect.topleft,
                    role='small', color=GOLD)
                self._bar(painter, row[key], value/maximum if maximum else 0, color)
            column = row['column']
            painter.line(BRASS, (column.right, top+5), (column.right, self.panel_rect.bottom-5))
            painter.line(BRASS, (column.left+4, top+self._status_height),
                         (column.right-4, top+self._status_height))
        self.gear.draw(painter, self._elapsed, enabled=self.gear_enabled,
                       slowed=self.atb_multiplier < 1, focused=self.gear.focused)
        if self.rig is not None and 'mira' in self.party_rows:
            self.rig.draw(painter, self.party_rows['mira']['interactable'], enabled=self.rig_enabled)
        space = self.party_rows['player']['interactable']
        if space.width >= 140:
            painter.text(GEM_NAMES[self.model.active_gem], (self.gear.rect.right+7, self.gear.rect.centery),
                         role='small', color=GEM_COLORS[self.model.active_gem], anchor='midleft', bold=True)
            if self.atb_multiplier < 1:
                painter.text('ATB 25%', (self.gear.rect.right+7, self.gear.rect.centery+14),
                             role='small', color=MUTED, anchor='midleft')
        if model.phase in RESULTS:
            painter.button(self.continue_rect, 'Retry' if self.result_error else 'Continue')
        elif self._target_command is not None:
            help_lines = painter.wrap('Arrows or click a foe', self.commands_panel.width-14, role='small')
            y = top+small+11
            for line in help_lines:
                painter.text(line, (self.commands_panel.left+7, y), role='small', color=IVORY)
                y += small
            painter.button(self._target_confirm_rect, 'Confirm')
            painter.button(self._target_cancel_rect, 'Back')
        else:
            actions = self._command_actions()
            for identifier, rect in self.command_rects.items():
                disabled = model.phase != 'ready' or bool(self._command_reason(identifier))
                painter.rect(FOREST, rect)
                lines = self._command_lines[identifier]
                y = rect.centery-len(lines)*small/2
                for line in lines:
                    painter.text(line, (rect.centerx, y), role='small', anchor='midtop',
                                 color=MUTED if disabled else IVORY)
                    y += small
                if model.phase == 'ready' and actions.index(identifier) == self.selected:
                    painter.rect(MUTED if disabled else GOLD, rect, 1)
            detail = self._notice or self._detail_text()
            if detail and (self._notice or self.command_menu in ('skills', 'items', 'item_targets', 'skill_targets')
                           or self.rig is not None and self.rig.focused) and (
                    self._hovered_enemy is None or self._notice):
                lines = painter.wrap(detail, 270, role='small')
                box = pygame.Rect(192, top-len(lines)*small-12, 280, len(lines)*small+8)
                painter.panel(box)
                for index, line in enumerate(lines):
                    painter.text(line, (box.x+5, box.y+4+index*small), role='small', color=IVORY)
        if self.tutorial_active:self._draw_tutorial(painter)
        if self.paused:
            painter.veil(150)
            painter.panel((124, 111, 232, 100))
            painter.text('Battle paused', (240, 126), color=GOLD, anchor='midtop', bold=True)
            painter.button(self.resume_rect, 'Resume', disabled=not self.focused)
        painter.clip()

    def _draw_tutorial(self, painter):
        line = self._tutorial_queue[0]
        small = painter.font('small').get_linesize()
        spoken = painter.wrap(line['text'], 336, role='small')
        hints = painter.wrap(line['help'], 336, role='small') if line['help'] else []
        button_height = max(20, painter.font().get_height()+4)
        height = max(98,24+small+(len(spoken)+len(hints))*small+button_height+(5 if hints else 0))
        panel = pygame.Rect(22, 10, 436, height)
        painter.panel(panel)
        speaker=line.get('speaker','mira')
        social=getattr(self.game,'social',None)
        if social is not None:
            portrait=social.portraits[social.data['speakers'][speaker]['portrait']]
            painter.image(portrait,pygame.Rect(34,28,48,48))
            painter.rect(BRASS,pygame.Rect(33,27,50,50),1)
        painter.text('Caelan' if speaker=='caelan' else 'Mira', (94, 18), role='small', color=GOLD, bold=True)
        y = 20+small
        for text in spoken:
            painter.text(text, (94, y), role='small');y += small
        if hints:y += 5
        for text in hints:
            painter.text(text, (94, y), role='small', color=MUTED);y += small
        self.tutorial_continue_rect = pygame.Rect(354, panel.bottom-button_height-8,
                                                   90, button_height)
        painter.button(self.tutorial_continue_rect, 'Continue')
