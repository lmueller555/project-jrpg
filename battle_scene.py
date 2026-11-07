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

from ui_style import FOREST, FOREST_DARK, FOREST_LIGHT, IVORY, GOLD, BRASS, MUTED


ROOT = Path(__file__).resolve().parent
COMBAT_ART = ROOT/'assets/combat'
RESULTS = ('victory', 'defeat', 'fled')
ACTION_LABELS = {'attack': 'Attack', 'guard': 'Guard', 'flee': 'Flee',
                 'skills': 'Skills', 'back': 'Back',
                 'aether_edge': 'Aether Edge', 'aether_dart': 'Dart · 4 MP',
                 'nature_edge': 'Nature Edge', 'aqua_edge': 'Aqua Edge',
                 'flame_edge': 'Flame Edge',
                 'overclock': 'Overclock'}
HP_GREEN = '#6fc878'
HP_YELLOW = GOLD
HP_RED = '#df6b62'
MP_BLUE = '#5da9e9'
ATB_YELLOW = GOLD


class CombatSprites:
    """Native combat frames loaded once, including optional guest/enemy art."""

    def __init__(self, root=COMBAT_ART):
        self.root = Path(root)
        self.actors = {}
        for actor in ('caelan', 'bat'):
            self._load_actor(actor)

    def _load_actor(self, actor):
        if actor not in ('caelan', 'bat', 'mira', 'rivet', 'ridgeback_tusker', 'lucan', 'rhea', 'edran'):
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
        for state, animation in data['animations'].items():
            frames = []
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
            if not frames or type(animation['loop']) is not bool:
                raise ValueError('Invalid combat animation')
            animations[state] = (frames, animation['loop'])
        if 'idle' not in animations:raise ValueError('Combat sprites require an idle')
        self.actors[actor] = {'anchor': tuple(anchor), 'animations': animations}

    def frame(self, actor, state, elapsed_ms):
        if actor not in self.actors:self._load_actor(actor)
        data = self.actors[actor]
        frames, loop = data['animations'].get(state, data['animations']['idle'])
        duration = sum(frame[1] for frame in frames)
        time = max(0, elapsed_ms)
        time = time % duration if loop else min(time, duration-1)
        for surface, length in frames:
            if time < length:return surface, data['anchor']
            time -= length
        return frames[-1][0], data['anchor']


class BattleScene:
    """Render and operate a BattleModel without settling its persistent outcome.

    Game owns transition, checkpoint and rewards. A confirmed result sets
    dismissed, which lets Game return safely to the original world position.
    """

    def __init__(self, game, model, sprites=None, *, battlefield='eldenmere', tutorial=False):
        if battlefield not in ('eldenmere', 'millrace'):
            raise ValueError('Unknown battlefield')
        self.game, self.model = game, model
        self.battlefield = battlefield
        self.location_name = 'Upper Millrace' if battlefield == 'millrace' else 'Eldenmere'
        self.tutorial = bool(tutorial)
        self._tutorial_queue = []
        self._tutorial_seen = set()
        self.tutorial_continue_rect = pygame.Rect(354, 61, 90, 20)
        self.sprites = sprites if sprites is not None else CombatSprites()
        self.mira_art = MiraCombatArt() if model.combatant('mira') is not None else None
        if model.weapon_equipped:
            from gearblade_art import prepare_combat_art
            prepare_combat_art()
        self.dismissed = False
        self.result_error = ''
        self.paused = False
        self.focused = True
        self.selected = 0
        self.command_menu = 'root'
        self._command_context = (model.phase, model.ready_actor)
        self._held = False
        self._elapsed = 0.0
        self._phase_elapsed = 0.0
        # A result clears the model's attachments. Keep only a visual reference
        # for the celebration; it never supplies commands or combat resources.
        self._encounter_bots = tuple(getattr(model, 'bots', ()))
        self._deploy_times = {bot.identifier: 0.0 for bot in self._encounter_bots}
        self.bot_status = {}
        self._defeat_times = {member.identifier: 0.0 for member in
                              (*model.party, model.enemy) if not member.hp}
        self._popups = []
        self._reactions = {}
        self.action_fx = BattleActionEffects()
        motion_frame('plant', 0, armed=model.weapon_equipped)
        self.action_audio = BattleActionAudio(game)
        self._cue_action = None
        self._cue_phases = set()
        self._last_phase = model.phase
        self._notice = ''
        self.panel_rect = pygame.Rect(8, 232, 464, 80)
        self.command_rects = {}
        self.continue_rect = pygame.Rect(20, 286, 110, 20)
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.name_rect = pygame.Rect(220, 252, 40, 15)
        self.atb_rect = pygame.Rect(156, 256, 50, 6)
        self.hp_rect = pygame.Rect(294, 266, 86, 5)
        self.mp_rect = pygame.Rect(390, 266, 70, 5)
        self.party_row_rect = pygame.Rect(152, 250, 308, 24)
        self.party_rows = {}
        self.header_rects = {}
        self._detail_lines = []
        self.gear = GearWidget(getattr(model, 'active_gem', 'water'))
        self.gear_fx = GearbladeEffects()
        self._slot_time = None
        self._gear_adjust_time = None
        self._command_scroll = 0
        self._pointer = None
        self._pointer_window = None
        self._viewport = (self.game.ui_surface.get_size(), getattr(self.game.audio, 'text_scale', 1))
        self._command_lines = {}
        self._background = self._make_background(COMBAT_ART/battlefield/'background.png')
        self._grass = self._make_grass() if battlefield == 'eldenmere' else ()
        self._shadows = self._make_shadows()

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
                                   ('bot', (25, 5), 55),
                                   ('enemy_low', (30, 7), 48),
                                   ('enemy_high', (24, 5), 34),
                                   ('tusker', (114, 14), 62)):
            image = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.ellipse(image, (31, 43, 29, opacity//2), image.get_rect())
            pygame.draw.ellipse(image, (31, 43, 29, opacity), image.get_rect().inflate(-8, -2))
            shadows[key] = image
        return shadows

    def _draw_shadow(self, canvas, actor, point):
        if self._bot(actor) is not None:
            image, ground_y = self._shadows['bot'], round(point.y)
        elif actor != 'enemy':
            image, ground_y = self._shadows['player'], round(point.y)
        elif self.model.enemy_sprite_id == 'ridgeback_tusker':
            image, ground_y = self._shadows['tusker'], round(point.y)
        else:
            # The Bat moves above the same ground plane, including its idle bob.
            ground_y = round(self._home_positions()['enemy'].y+14)
            image = self._shadows['enemy_low' if point.y > 177 else 'enemy_high']
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
        self.continue_rect = pygame.Rect(self.commands_panel.left+6, self.panel_rect.bottom-25, self.commands_panel.width-12, 20)
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.header_rects = {}
        actions = self._command_actions()
        self._command_lines = {identifier: painter.wrap(ACTION_LABELS.get(identifier, identifier),
                                                        self.commands_panel.width-16, role='small')
                               for identifier in actions}
        row_heights = [max(16, len(self._command_lines[item])*small+5) for item in actions]
        available = height-small-15
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
        return small, name

    def _bot(self, identifier):
        return next((bot for bot in self._encounter_bots
                     if bot.identifier == identifier), None)

    def _field_bots(self):
        if self.model.phase in ('victory', 'defeat'):
            return self._encounter_bots
        return tuple(getattr(self.model, 'bots', ()))

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

    def _tutorial_event(self, event):
        if event['type'] == 'spellblade_interrupted':
            self._tutorial_queue.clear()
            self._queue_tutorial('spellblade_interrupted',
                'Stay down, Cael. I’ll finish this.',
                'Caelan is incapacitated. Mira and Rivet can continue the battle.')
            return
        if self.model.spellblade_stage is not None:
            return self._spellblade_tutorial_event(event)
        if event['type'] == 'player_ready':
            self._queue_tutorial('readiness',
                'Steady. Get your footing, then strike when you have an opening.',
                'Full ATB: ready to act. Gauges pause while you choose.')
            if event.get('actor') == 'mira':
                self._queue_tutorial('mira_turn',
                    'Rivet, keep it busy. I can cover you both from here.',
                    'Mira fires Bolt Shot. Skills → Overclock costs 5 MP and hastens Rivet for 8 bot turns.')
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
                self._queue_tutorial('spellblade_choose','Now—while it’s turning. Choose a focus.',
                    'Drag the gear to seat a gem in the top catch, then try its Edge from Skills.')
                self._queue_tutorial('gear_instruction',
                    'The catch at the top, Cael. Turn a gem into it, then draw your aether through the blade.',
                    'Hovering over the gear slows all ATB charging to 25%. You can also adjust it while choosing an action.')
        elif kind=='spellblade_failed':
            lines=(('caelan','It didn’t—'),('mira','Stay with me.'),
                   ('caelan','*breathing quickly* I turned it. I’m trying, but nothing’s happening!'),
                   ('mira','Cael, look at the blade. Use it as the focus. Direct your aether through it.'),
                   ('caelan','I don’t know if I can do that here.'),
                   ('mira','Wait for your opening. I’m here.'))
            for index,(speaker,text) in enumerate(lines):
                self._queue_tutorial('spellblade_failed_'+str(index),text,
                    'On Caelan’s next full ATB, choose a focus from Skills again.' if index==5 else '',speaker)
        elif kind=='spellblade_discovered':
            lines=(('caelan','That wasn’t what I was trying to do.'),
                   ('mira','It struck. Can you do that again?'),
                   ('caelan','I think so. But the focus—'),
                   ('mira','Go with it. We’ll work out the rest when we’re clear.'))
            for index,(speaker,text) in enumerate(lines):
                self._queue_tutorial('spellblade_discovered_'+str(index),text,
                    'Learned Aether Edge · 4 MP. Normal party commands are now available.' if index==3 else '',speaker)
        elif kind=='player_ready' and event.get('actor')=='mira' and stage=='complete':
            self._queue_tutorial('mira_turn','Rivet, keep it busy. I can cover you both from here.',
                'Mira fires Bolt Shot. Skills → Overclock hastens Rivet for 8 bot turns.')

    def _detail_text(self):
        """Full messages flow beneath the occupied party row, never over values."""
        model = self.model
        if model.phase in RESULTS:
            if model.phase == 'victory':return ''
            if self.result_error:return self.result_error
            if model.phase == 'defeat':
                return ('Return to the safe approach.' if self.battlefield == 'millrace'
                        else 'Return to Eldenmere.')
            return ''
        if model.phase == 'ready':
            actions = self._command_actions()
            if self.command_menu == 'skills' and actions:
                selected = actions[self.selected % len(actions)]
                if selected == 'aether_edge':
                    return '4 MP · Physical and non-elemental magical sword strike.'
                if selected in ('nature_edge','aqua_edge','flame_edge'):
                    return self._command_reason(selected) or 'Unpractised elemental focus.'
                if selected == 'overclock':
                    return '5 MP · Haste: +50% ATB for 8 bot turns.'
            return ''
        return model.message if model.phase == 'acting' else 'Preparing the next action.'

    def _sound(self, kind):self.game.ui.sound(kind)

    def _sync_commands(self):
        """A command list belongs only to its current ready party member."""
        context = (self.model.phase, self.model.ready_actor)
        if context != self._command_context:
            self.command_menu = 'root'
            self.selected = 0
            self._notice = ''
            self._command_context = context

    def _command_actions(self):
        if self.command_menu == 'skills':
            return list(self.model.skill_actions())+['back']
        commands = getattr(self.model, 'command_actions', self.model.available_actions)
        return list(commands())

    def _command_reason(self, identifier):
        if identifier == 'back':return ''
        if identifier == 'skills':return self.model.command_reason(identifier)
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
        self.command_menu = 'root'
        self._command_context = (self.model.phase, self.model.ready_actor)
        self.selected = 0
        self._notice = ''
        self._command_scroll = 0
        self._layout(self.game.ui.painter(self.game.ui_surface))
        self._sound('move')
        self._tutorial_event({'type': 'player_ready', 'actor': identifier})
        return True

    def _confirm(self):
        if self.model.phase == 'victory':return
        if self.model.phase in RESULTS:
            self.dismissed = True
            self._sound('confirm')
            return
        if self.model.phase != 'ready':return
        self._sync_commands()
        actions = self._command_actions()
        if not actions:return
        self.selected %= len(actions)
        identifier = actions[self.selected]
        if identifier == 'back':
            self._set_menu('root')
            self._sound('back')
            return
        if identifier == 'skills':
            reason = self._command_reason(identifier)
            if reason:
                self._notice = reason
                self._sound('back')
            else:
                self._set_menu('skills')
                self._sound('confirm')
            return
        if self.model.choose_action(identifier):
            self._sync_commands()
            self._sound('confirm')
        else:
            self._notice = self.model.action_reason(identifier)
            self._sound('back')

    @property
    def gear_enabled(self):
        action = self.model.current_action
        return (self.model.weapon_equipped and self.model.player.hp > 0
                and self.model.phase not in RESULTS and not self.dismissed
                and not self.paused and self.focused and not self.tutorial_active
                and not (action is not None and action.actor == 'player'))

    @property
    def gear_hover_available(self):
        return (self.model.weapon_equipped and self.model.player.hp > 0
                and self.model.phase not in RESULTS and not self.dismissed
                and not self.paused and self.focused and not self.tutorial_active)

    @property
    def atb_multiplier(self):
        return .25 if self.gear_hover_available and self.gear.hovered else 1.0

    def _cancel_gear(self):
        self.gear.active_gem = self.model.active_gem
        self.gear.cancel()
        self.gear.hovered = False
        self.gear.focused = False
        self.model.gear_settling = False

    def handle_event(self, event):
        if self.dismissed:return True
        self._layout(self.game.ui.painter(self.game.ui_surface))
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if hasattr(event, 'pos'):
            self._pointer_window = event.pos
            self._pointer = point
            self.gear.hovered = bool(point is not None and self.gear.rect.collidepoint(point))
        if event.type == pygame.WINDOWLEAVE:
            self._pointer = self._pointer_window = None
            self.gear.hovered = False
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self.paused = True
            self._held = False
            self._cancel_gear()
            self.action_audio.stop()
            return True
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
            return True
        if (self.tutorial_active and not self.paused
                and not (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)):
            self._cancel_gear()
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
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:
                self._cancel_gear()
                if self.focused:
                    if not self.paused and self.command_menu == 'skills':
                        self._set_menu('root');self._sound('back');return True
                    self.paused = not self.paused
                    if self.paused:self.action_audio.stop()
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
        elif self.gear.busy:self._cancel_gear()
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            return True
        if self.paused:
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.focused
                    and point is not None and self.resume_rect.collidepoint(point)):
                self.paused = False;self._sound('confirm')
            return True
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):self._confirm()
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
                for identifier, row in self.party_rows.items():
                    if row['row'].collidepoint(point):
                        self._select_member(identifier);return True
                actions = self._command_actions()
                for identifier, rect in self.command_rects.items():
                    if rect.collidepoint(point):
                        self.selected = actions.index(identifier);self._confirm();break
        elif event.type == pygame.MOUSEMOTION and self.model.phase == 'ready' and point is not None:
            actions = self._command_actions()
            for identifier, rect in self.command_rects.items():
                if rect.collidepoint(point):
                    self.selected = actions.index(identifier)
                    self._notice = self._selection_notice();break
        return True

    def update(self, seconds):
        if self.dismissed or self.paused or not self.focused or self.tutorial_active:return
        if type(seconds) not in (int, float):raise TypeError('Scene time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid scene time')
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
        for reaction in self._reactions.values():reaction['age'] += seconds
        self._reactions = {key: value for key, value in self._reactions.items() if value['age'] < .55}
        self._action_cues()
        for popup in self._popups:popup['age'] += seconds
        self._popups = [popup for popup in self._popups if popup['age'] < 1.1]
        if not self.gear_enabled and (self.gear.busy):self._cancel_gear()
        gem = self.gear.update(seconds, reduced_motion=self.reduced_motion)
        if gem is not None and self.model.set_active_gem(gem):
            self._slot_time = self._elapsed
            self._gear_adjust_time = self._elapsed
            owner = getattr(self.game, 'character_abilities', None)
            if owner is not None and owner.set_active_gem(gem):
                save = getattr(self.game, 'save_progress', None)
                if save is not None:save()
        self.model.gear_settling = self.gear.busy
        for notice in self.gear.consume_notices():
            self._sound('gear_seat' if notice == 'seat' else 'gear_detent')
        self.model.update(seconds, atb_multiplier=self.atb_multiplier)
        self._action_cues()
        self._phase_elapsed = (0.0 if self.model.phase != self._last_phase
                               else self._phase_elapsed+seconds)
        for event in self.model.drain_events():
            self._tutorial_event(event)
            if event['type'] == 'impact':
                age = max(0., event.get('frame_age', 0.))
                self._reactions[event['target']] = {'age': age, 'guarded': event.get('guarded', False),
                    'lethal': not event['remaining_hp'], 'action': event['action']}
                if age < .12:
                    metallic = event.get('guarded') and (event['target'] != 'player' or self.model.weapon_equipped)
                    self.action_audio.play('guard_hit' if metallic else 'impact')
                self._popups.append({'target': event['target'],
                                     'text': str(event['damage']), 'age': age,
                                     'guarded': event.get('guarded', False)})
                if not event['remaining_hp']:self._defeat_times[event['target']] = self._elapsed-age
            elif event['type'] == 'guard':
                self._popups.append({'target': event.get('actor', 'player'), 'text': 'Guard', 'age': 0.0})
            elif event['type'] == 'enchant':
                self._popups.append({'target': event['actor'], 'text': 'Aether Edge',
                                     'age': 0.0, 'enchant': True})
            elif event['type'] == 'haste_applied':
                self._popups.append({'target': event['target'], 'text': 'Haste',
                                     'age': 0.0, 'enchant': True})
            elif event['type'] == 'bot_deployed':
                self._deploy_times[event['actor']] = self._elapsed
            elif event['type'] == 'player_ready':
                self.command_menu = 'root'
                self.selected = 0
                self._notice = ''
        self._popups = [popup for popup in self._popups if popup['age'] < 1.1]
        self._reactions = {key: value for key, value in self._reactions.items() if value['age'] < .55}
        self._sync_commands()
        self._last_phase = self.model.phase
        if self.model.phase in RESULTS or self.tutorial_active:self._cancel_gear()

    @property
    def reduced_motion(self):return getattr(self.game.audio, 'reduced_motion', False)

    def _bot_home(self):
        if len(self.model.party) == 3:
            return pygame.Vector2(271, self.panel_rect.top-18)
        return pygame.Vector2(296, 181-max(0, 202-self.panel_rect.top))

    def _choreography(self, action=None):
        action = self.model.current_action if action is None else action
        if action is None or not getattr(action, 'choreography', None):return None
        return sample_choreography(action.choreography, action.elapsed, armed=action.weapon_equipped)

    def _action_cues(self):
        action = self.model.current_action
        if action is not self._cue_action:
            self._cue_action = action
            self._cue_phases.clear()
        if (action is not None and action.actor == 'mira'
                and action.action == 'bolt_shot' and self.mira_art is not None):
            if action.elapsed >= self.mira_art.release_at and 'mira_release' not in self._cue_phases:
                self._cue_phases.add('mira_release')
                self.action_audio.play('focus')
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
        for bot in self._field_bots():positions[bot.identifier] = self._bot_home()
        return positions

    def _hit_point(self, actor, positions=None):
        positions = self._home_positions() if positions is None else positions
        point = positions[actor]
        if actor == 'enemy':
            return point+((54, -38) if self.model.enemy_sprite_id == 'ridgeback_tusker' else (8, -32))
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
            if action.actor == 'enemy':
                contact = pygame.Vector2(-96, -4) if self.model.enemy_sprite_id == 'ridgeback_tusker' else pygame.Vector2(-34, -14)
            else:contact = pygame.Vector2(83, -4)
            positions[action.actor] = positions[action.actor].lerp(target+contact, blend)
        for actor, record in self._reactions.items():
            if actor not in positions:continue
            sprite = self.model.enemy_sprite_id if actor == 'enemy' else 'caelan' if actor == 'player' else actor
            reaction = target_reaction(sprite, record['age'], direction=-1 if actor == 'enemy' else 1,
                                       reduced_motion=self.reduced_motion, guarded=record['guarded'])
            if reaction['active']:
                positions[actor] += pygame.Vector2(reaction['offset'])*(.5 if record['guarded'] else 1)
        return positions

    def _positions(self):
        positions = self._ground_positions()
        if self.model.enemy_sprite_id == 'bat' and not self.reduced_motion:
            positions['enemy'].y += math.sin(self._elapsed*4)*2
        sample = self._choreography()
        if sample is not None and not self.reduced_motion:
            positions['player'].y -= sample.elevation
        return positions

    def _camera(self):
        sample = self._choreography()
        if self.reduced_motion or sample is None:return 1., (0., 0.)
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
        bot = self._bot(actor)
        if bot is not None:
            owner = self.model.combatant(bot.owner_id)
            if owner is None or not owner.hp or self.model.phase in ('defeat', 'fled'):
                return 'suspend', self._elapsed*1000
            if self.model.phase == 'victory':return 'victory', self._phase_elapsed*1000
            action = self.model.current_action
            if action is not None:
                if action.kind == 'haste' and action.target == actor:
                    return 'overclock', action.elapsed*1000
                if action.actor == actor:return action.animation, action.elapsed*1000
            deployment = self._elapsed-self._deploy_times.get(actor, 0)
            if deployment < .6:return 'deploy', deployment*1000
            return 'idle', self._elapsed*1000
        combatant = self.model.combatant(actor)
        reaction = self._reactions.get(actor)
        sprite = self.model.enemy_sprite_id if actor == 'enemy' else actor
        reaction_length = target_reaction(sprite, 0., guarded=bool(reaction and reaction['guarded']))['duration']
        if reaction is not None and reaction['age'] < (.18 if reaction['lethal'] else reaction_length):
            age = reaction['age']
            if actor == 'player':
                return ('guard_impact' if reaction['guarded'] else 'hurt_recover'), age*1000
            if actor == 'mira' and reaction['guarded']:
                return 'guard_impact', age*1000
            return 'hurt', age*1000
        if combatant.hp <= 0:
            return 'defeat', max(0., self._elapsed-self._defeat_times.get(actor, 0)-.18)*1000
        if actor != 'enemy' and self.model.phase == 'victory':return 'victory', self._phase_elapsed*1000
        action = self.model.current_action
        if action is not None and action.actor == actor:
            sequence = self._choreography(action)
            if sequence is not None:return sequence.pose, sequence.pose_ms
            if actor == 'mira' and action.kind == 'guard':
                return 'guard_enter', action.elapsed*1000
            state = ('aether_edge' if actor == 'player' and action.action == 'aether_edge' else
                     'overclock' if action.kind == 'haste' else
                     'cast' if action.kind in ('magical', 'enchant', 'failed_edge') else 'guard' if action.kind == 'guard'
                     else 'idle' if action.kind == 'flee' else action.animation
                     if action.animation in ('prepare', 'charge') else 'attack')
            return state, action.elapsed*1000
        if actor == 'enemy' and self.model.telegraphed_target:
            return 'prepare', self._elapsed*1000
        if combatant.guarded:
            return ('guard_enter', 300.) if actor == 'player' else ('guard', self._elapsed*1000)
        if actor == 'player' and self._gear_adjust_time is not None:
            age = self._elapsed-self._gear_adjust_time
            if age < .6:return 'focus_adjust', age*1000
        return 'idle', self._elapsed*1000

    def _draw_field(self, canvas):
        canvas.blit(self._background, (0, 0))
        positions = self._positions()
        ground = self._ground_positions()
        for actor in sorted(positions, key=lambda identifier: ground[identifier].y):
            point = positions[actor]
            self._draw_shadow(canvas, actor, ground[actor])
            state, time = self._pose(actor)
            sprite = ('caelan' if actor == 'player' else self.model.enemy_sprite_id
                      if actor == 'enemy' else actor)
            image, anchor = self.sprites.frame(sprite, state, time)
            if actor == 'player':
                sequence = self._choreography()
                if sequence is not None or state in MOTION_STATES:
                    image, anchor = motion_frame(state, time, armed=self.model.weapon_equipped)
                elif self.model.weapon_equipped:
                    from gearblade_art import combat_frame
                    image, anchor = combat_frame(image, state, time)
            canvas.blit(pygame.transform.scale(image, (image.get_width()*2, image.get_height()*2)),
                        (round(point.x-anchor[0]*2), round(point.y-anchor[1]*2)))
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
                self.gear_fx.draw(canvas, point, state, time, self.model.active_gem, self._elapsed,
                    slot_age=None if self._slot_time is None else self._elapsed-self._slot_time,
                    action=context, reduced_motion=self.reduced_motion)
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
                              dash_at=.46 if action.action == 'aether_edge' else .14,
                              landing_at=1.8 if action.action == 'aether_edge' else 1.25)
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
        if action is not None and action.kind == 'haste' and action.target in positions:
            point = positions[action.target]+(0, -24)
            pulse = 0 if self.reduced_motion else round(math.sin(action.elapsed*12)*2)
            pygame.draw.circle(canvas, '#72c8f0', (round(point.x), round(point.y)), 19+pulse, 1)
            for offset in (-9, 9):
                pygame.draw.circle(canvas, '#d8f7ff',
                                   (round(point.x+offset), round(point.y-25)), 2)
        self._draw_mira_effects(canvas)
        if (action is not None and action.kind == 'magical' and not action.resolved
                and not getattr(action, 'choreography', None)):
            fraction = max(0, min(1, action.elapsed/max(.001, action.impact_at)))
            start = positions[action.actor]+(-23 if action.actor == 'player' else 20, -37)
            end = positions[action.target]+(0, -33)
            point = start.lerp(end, fraction)
            for index, radius in enumerate((5, 3, 1)):
                color = ('#376ea2', '#72c8f0', '#d8f7ff')[index]
                pygame.draw.circle(canvas, color, (round(point.x), round(point.y)), radius)
        self._draw_foreground(canvas)

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
        action = self.model.current_action
        if (self.mira_art is not None and action is not None and action.actor == 'mira'
                and action.action == 'overclock' and action.impact_at <= action.elapsed < action.impact_at+.08
                and not self.reduced_motion):
            point = self.mira_art.world_anchor('overclock', action.elapsed*1000, 'controller',
                                               self._home_positions()['mira'])
            x, y = (round(n) for n in point)
            pygame.draw.line(canvas, '#f1cd77', (x-3, y-2), (x-1, y-1), 1)
            pygame.draw.line(canvas, '#f8f0d9', (x+3, y-2), (x+1, y-1), 1)

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
        enemy_x = 119 if len(model.party) > 1 else 126
        painter.text(enemy.name, (enemy_x+1, 44), role='name', color=FOREST_DARK, anchor='center', bold=True)
        painter.text(enemy.name, (enemy_x, 43), role='name', anchor='center', bold=True)
        enemy_bar = pygame.Rect(45, 57, 150, 6) if len(model.party) > 1 else pygame.Rect(86, 57, 80, 6)
        self._bar(painter, enemy_bar, enemy.hp/enemy.value('hp'), '#9ab46b')
        caption = model.current_action.name if model.current_action is not None else self.location_name
        painter.text(caption, (241, 16), color=FOREST_DARK, anchor='midtop')
        painter.text(caption, (240, 15), color=GOLD, anchor='midtop')
        target = model.combatant(model.telegraphed_target) if model.telegraphed_target else None
        if target is not None:
            compact = len(model.party) == 3
            warning = 'Charge → '+(target.name.split()[0] if compact else target.name)
            warning_y = self.panel_rect.top-small-5 if compact else 43
            painter.text(warning, (461, warning_y+1), role='small', color=FOREST_DARK, anchor='topright')
            painter.text(warning, (460, warning_y), role='small', color=GOLD, anchor='topright')
        positions = self._positions()
        for popup in self._popups:
            if popup['target'] not in positions:continue
            point = positions[popup['target']]+(0, -(88 if popup['target'] == 'enemy'
                and self.model.enemy_sprite_id == 'ridgeback_tusker' else 18 if self._bot(popup['target']) else 75))
            x, y = self._project(point)
            y -= 0 if self.reduced_motion else min(14, popup['age']*20)
            popup_width, popup_height = painter.font('name', bold=True).size(popup['text'])
            x = max(popup_width/2+2, min(478-popup_width/2, x))
            y = max(popup_height/2+2, min(self.panel_rect.top-popup_height/2-2, y))
            painter.text(popup['text'], (x+1, y+1), role='name', color=FOREST_DARK, anchor='center', bold=True)
            painter.text(popup['text'], (x, y), role='name',
                         color=MP_BLUE if popup.get('enchant') else GOLD, anchor='center', bold=True)
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
                   or ('SKILLS' if self.command_menu == 'skills' else 'COMMANDS'))
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
        space = self.party_rows['player']['interactable']
        if space.width >= 140:
            painter.text(GEM_NAMES[self.model.active_gem], (self.gear.rect.right+7, self.gear.rect.centery),
                         role='small', color=GEM_COLORS[self.model.active_gem], anchor='midleft', bold=True)
            if self.atb_multiplier < 1:
                painter.text('ATB 25%', (self.gear.rect.right+7, self.gear.rect.centery+14),
                             role='small', color=MUTED, anchor='midleft')
        if model.phase in RESULTS:
            painter.button(self.continue_rect, 'Retry' if self.result_error else 'Continue')
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
            if detail and (self._notice or self.command_menu == 'skills'):
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
