"""Encounter battle views, compact party status and contextual guidance."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

from ui_style import FOREST, FOREST_DARK, FOREST_LIGHT, IVORY, GOLD, BRASS, MUTED


ROOT = Path(__file__).resolve().parent
COMBAT_ART = ROOT/'assets/combat'
RESULTS = ('victory', 'defeat', 'fled')
ACTION_LABELS = {'attack': 'Attack', 'guard': 'Guard', 'flee': 'Flee',
                 'aether_dart': 'Dart · 4 MP'}
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
        if actor not in ('caelan', 'bat', 'mira', 'ridgeback_tusker'):
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
        self.dismissed = False
        self.result_error = ''
        self.paused = False
        self.focused = True
        self.selected = 0
        self._held = False
        self._elapsed = 0.0
        self._phase_elapsed = 0.0
        self._defeat_times = {member.identifier: 0.0 for member in
                              (*model.party, model.enemy) if not member.hp}
        self._popups = []
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
                                   ('enemy_low', (30, 7), 48),
                                   ('enemy_high', (24, 5), 34),
                                   ('tusker', (114, 14), 62)):
            image = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.ellipse(image, (31, 43, 29, opacity//2), image.get_rect())
            pygame.draw.ellipse(image, (31, 43, 29, opacity), image.get_rect().inflate(-8, -2))
            shadows[key] = image
        return shadows

    def _draw_shadow(self, canvas, actor, point):
        if actor != 'enemy':
            image, ground_y = self._shadows['player'], round(point.y)
        elif self.model.enemy_id == 'ridgeback_tusker':
            image, ground_y = self._shadows['tusker'], round(point.y)
        else:
            # The Bat moves above the same ground plane, including its idle bob.
            ground_y = 184
            image = self._shadows['enemy_low' if point.y > 177 else 'enemy_high']
        canvas.blit(image, (round(point.x)-image.get_width()//2,
                            ground_y-image.get_height()//2))

    def _layout(self, painter):
        small = painter.font('small').get_linesize()
        name = painter.font('name', bold=True).get_linesize()
        self._detail_lines = painter.wrap(self._detail_text(), 308, role='small')
        row_height = max(name, small+6)+3
        command_height = max(14, small)
        content_offset = small+8
        # The ordinary panel is 26% shorter. Font enlargement gets real space,
        # rather than clipped labels or vertically compressed typography.
        height = max(80, content_offset+max(
            len(self.model.available_actions())*command_height+3,
            len(self.model.party)*row_height+5+len(self._detail_lines)*small+3))
        self.panel_rect = pygame.Rect(8, 312-height, 464, height)
        top = self.panel_rect.top
        row_top = top+content_offset
        self.party_rows = {}
        for index, member in enumerate(self.model.party):
            name_width, name_height = painter.font('name', bold=True).size(member.name)
            name_rect = pygame.Rect(220, row_top+index*row_height, name_width, name_height)
            self.party_rows[member.identifier] = {
                'row': pygame.Rect(152, name_rect.top-1, 308, row_height),
                'name': name_rect,
                'atb': pygame.Rect(156, name_rect.centery-3, 50, 6),
                'hp': pygame.Rect(294, name_rect.top+small+1, 86, 5),
                'mp': pygame.Rect(390, name_rect.top+small+1, 70, 5)}
        player_row = self.party_rows['player']
        self.name_rect, self.atb_rect = player_row['name'], player_row['atb']
        self.hp_rect, self.mp_rect = player_row['hp'], player_row['mp']
        self.party_row_rect = player_row['row']
        self._party_bottom = max(row['row'].bottom for row in self.party_rows.values())
        self._detail_top = self._party_bottom+5
        continue_height = max(20, painter.font().get_height()+4)
        self.continue_rect = pygame.Rect(20, self.panel_rect.bottom-continue_height-5,
                                         110, continue_height)
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.command_rects = {}
        for index, identifier in enumerate(self.model.available_actions()):
            self.command_rects[identifier] = pygame.Rect(20, row_top+index*command_height,
                                                        110, command_height)
        return small, name

    @property
    def tutorial_active(self):return bool(self._tutorial_queue)

    @property
    def tutorial_text(self):
        return self._tutorial_queue[0]['text'] if self._tutorial_queue else ''

    def _queue_tutorial(self, key, text, help_text=''):
        if not self.tutorial or key in self._tutorial_seen:return
        self._tutorial_seen.add(key)
        self._tutorial_queue.append({'key': key, 'text': text, 'help': help_text})

    def advance_tutorial(self):
        """Acknowledge one line without submitting a combat command."""
        if not self.tutorial_active:return False
        self._tutorial_queue.pop(0)
        self._sound('confirm')
        return True

    def _tutorial_event(self, event):
        if event['type'] == 'player_ready':
            self._queue_tutorial('readiness',
                'Steady. Get your footing, then strike when you have an opening.',
                'Full ATB: ready to act. Gauges pause while you choose.')
            if event.get('actor') == 'mira':
                self._queue_tutorial('mira_turn',
                    'Stay clear of the point. I can reach it from here.',
                    'Mira is ready. Commands belong to the highlighted party row.')
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
        if model.phase == 'ready':return ''
        return model.message if model.phase == 'acting' else 'Preparing the next action.'

    def _sound(self, kind):self.game.ui.sound(kind)

    def _select_member(self, identifier):
        if not self.model.select_ready(identifier):return False
        self.selected = 0
        self._notice = ''
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
        actions = self.model.available_actions()
        if not actions:return
        self.selected %= len(actions)
        identifier = actions[self.selected]
        if self.model.choose_action(identifier):
            self._notice = ''
            self._sound('confirm')
        else:
            self._notice = self.model.action_reason(identifier)
            self._sound('back')

    def handle_event(self, event):
        if self.dismissed:return True
        self._layout(self.game.ui.painter(self.game.ui_surface))
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            return True
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self.paused = True
            self._held = False
            return True
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
            return True
        if (self.tutorial_active and not self.paused
                and not (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)):
            if (event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False)
                    and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)):
                self.advance_tutorial()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._held:
                    self._held = True
                    if point is not None and self.tutorial_continue_rect.collidepoint(point):
                        self.advance_tutorial()
            return True
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:
                if self.focused:
                    self.paused = not self.paused
                    self._held = False
                    self._sound('back' if self.paused else 'confirm')
                return True
            if self.paused:return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._confirm()
            elif self.model.phase == 'ready' and event.key == pygame.K_TAB:
                ready = self.model.ready_members
                if ready:
                    index = ready.index(self.model.ready_actor)
                    self._select_member(ready[(index+1) % len(ready)])
            elif self.model.phase == 'ready' and event.key in (
                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                actions = self.model.available_actions()
                delta = -1 if event.key in (pygame.K_UP, pygame.K_LEFT) else 1
                self.selected = (self.selected+delta) % len(actions)
                self._notice = ''
                self._sound('move')
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if point is None:return True
            if self.paused:
                if self.focused and self.resume_rect.collidepoint(point):
                    self.paused = False
                    self._sound('confirm')
                return True
            if self.model.phase in RESULTS:
                if self.continue_rect.collidepoint(point):self._confirm()
            elif self.model.phase == 'ready':
                for identifier, row in self.party_rows.items():
                    if row['row'].collidepoint(point):
                        self._select_member(identifier)
                        return True
                for index, (identifier, rect) in enumerate(self.command_rects.items()):
                    if rect.collidepoint(point):
                        self.selected = index
                        self._confirm()
                        break
        elif event.type == pygame.MOUSEMOTION and not self.paused and self.model.phase == 'ready':
            if point is not None:
                for index, rect in enumerate(self.command_rects.values()):
                    if rect.collidepoint(point):self.selected = index;break
        return True

    def update(self, seconds):
        if self.dismissed or self.paused or not self.focused or self.tutorial_active:return
        if type(seconds) not in (int, float):raise TypeError('Scene time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid scene time')
        self._elapsed += seconds
        for popup in self._popups:popup['age'] += seconds
        self._popups = [popup for popup in self._popups if popup['age'] < 1.1]
        self.model.update(seconds)
        self._phase_elapsed = (0.0 if self.model.phase != self._last_phase
                               else self._phase_elapsed+seconds)
        for event in self.model.drain_events():
            self._tutorial_event(event)
            if event['type'] == 'impact':
                self._popups.append({'target': event['target'],
                                     'text': str(event['damage']), 'age': 0.0,
                                     'guarded': event.get('guarded', False)})
                if not event['remaining_hp']:self._defeat_times[event['target']] = self._elapsed
            elif event['type'] == 'guard':
                self._popups.append({'target': event.get('actor', 'player'), 'text': 'Guard', 'age': 0.0})
            elif event['type'] == 'player_ready':
                self.selected = 0
                self._notice = ''
        self._last_phase = self.model.phase

    @property
    def reduced_motion(self):return getattr(self.game.audio, 'reduced_motion', False)

    def _positions(self):
        party_battle = len(self.model.party) > 1
        if party_battle:
            offset = max(0, 202-self.panel_rect.top)
            positions = {'player': pygame.Vector2(354, 194-offset),
                         'mira': pygame.Vector2(404, 151-offset),
                         'enemy': pygame.Vector2(119, 196-offset)}
        else:
            positions = {'player': pygame.Vector2(354, 184),
                         'enemy': pygame.Vector2(126, 170)}
        if self.model.enemy_id == 'bat' and not self.reduced_motion:
            positions['enemy'].y += math.sin(self._elapsed*4)*2
        action = self.model.current_action
        if action is not None and action.kind == 'physical' and not self.reduced_motion:
            approach = (action.elapsed/max(.001, action.impact_at)
                        if action.elapsed <= action.impact_at else
                        (action.duration-action.elapsed)/max(.001, action.duration-action.impact_at))
            blend = 1-(1-max(0.0, min(1.0, approach)))**3
            if not party_battle:
                positions[action.actor] += pygame.Vector2(-202 if action.actor == 'player' else 202,
                                                           -10 if action.actor == 'player' else 17)*blend
            else:
                target = positions[action.target]
                contact = (pygame.Vector2(-66, 0) if action.actor == 'enemy' else
                           pygame.Vector2(136 if action.actor == 'mira' else 112, -4))
                positions[action.actor] = positions[action.actor].lerp(target+contact, blend)
                if action.action == 'tusker_charge':
                    member = self.model.combatant(action.target)
                    guarded = member.guarded or any(
                        popup['target'] == action.target and popup.get('guarded')
                        and popup['age'] < .55 for popup in self._popups)
                    if guarded:
                        # Turn the full standing silhouette out of the direct
                        # line of impact; no limb scaling or anchored-leg bend.
                        step = math.sin(math.pi*min(1, action.elapsed/action.duration))
                        positions[action.target] += pygame.Vector2(9, -3)*step
        return positions

    def _pose(self, actor):
        combatant = self.model.combatant(actor)
        if combatant.hp <= 0:
            return 'defeat', (self._elapsed-self._defeat_times.get(actor, 0))*1000
        if actor != 'enemy' and self.model.phase == 'victory':return 'victory', self._phase_elapsed*1000
        for popup in self._popups:
            if popup['target'] == actor and popup['text'].isdigit() and popup['age'] < .28:
                return 'hurt', popup['age']*1000
        action = self.model.current_action
        if action is not None and action.actor == actor:
            state = ('cast' if action.kind == 'magical' else 'guard' if action.kind == 'guard'
                     else 'idle' if action.kind == 'flee' else action.animation
                     if action.animation in ('prepare', 'charge') else 'attack')
            return state, action.elapsed*1000
        if actor == 'enemy' and self.model.telegraphed_target:
            return 'prepare', self._elapsed*1000
        if combatant.guarded:return 'guard', self._elapsed*1000
        return 'idle', self._elapsed*1000

    def _draw_field(self, canvas):
        canvas.blit(self._background, (0, 0))
        positions = self._positions()
        for actor in sorted(positions, key=lambda identifier: positions[identifier].y):
            point = positions[actor]
            self._draw_shadow(canvas, actor, point)
            state, time = self._pose(actor)
            sprite = ('caelan' if actor == 'player' else self.model.enemy_id
                      if actor == 'enemy' else actor)
            image, anchor = self.sprites.frame(sprite, state, time)
            canvas.blit(pygame.transform.scale(image, (image.get_width()*2, image.get_height()*2)),
                        (round(point.x-anchor[0]*2), round(point.y-anchor[1]*2)))
        action = self.model.current_action
        if action is not None and action.kind == 'magical' and not action.resolved:
            fraction = max(0, min(1, action.elapsed/max(.001, action.impact_at)))
            start = positions[action.actor]+(-23 if action.actor == 'player' else 20, -37)
            end = positions[action.target]+(0, -33)
            point = start.lerp(end, fraction)
            for index, radius in enumerate((5, 3, 1)):
                color = ('#376ea2', '#72c8f0', '#d8f7ff')[index]
                pygame.draw.circle(canvas, color, (round(point.x), round(point.y)), radius)
        self._draw_foreground(canvas)

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
            warning = 'Charge → '+target.name
            painter.text(warning, (461, 44), role='small', color=FOREST_DARK, anchor='topright')
            painter.text(warning, (460, 43), role='small', color=GOLD, anchor='topright')
        positions = self._positions()
        for popup in self._popups:
            if len(model.party) > 1:
                point = positions[popup['target']]
                x, y = point.x, point.y-(120 if popup['target'] == 'enemy' else 85)
            else:
                x, y = (354 if popup['target'] == 'player' else 126), 99
            y -= 0 if self.reduced_motion else min(14, popup['age']*20)
            painter.text(popup['text'], (x+1, y+1), role='name', color=FOREST_DARK, anchor='center', bold=True)
            painter.text(popup['text'], (x, y), role='name', color=GOLD, anchor='center', bold=True)
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
        heading = ({'victory': 'VICTORY', 'defeat': 'DEFEATED', 'fled': 'ESCAPED'}[model.phase]
                   if model.phase in RESULTS else 'COMMANDS')
        painter.text(heading, (20, top+5), role='small', color=GOLD, bold=True)
        self.header_rects = {}
        for label, center in (('ATB', 181), ('NAME', 254), ('HP', 337), ('MP', 425)):
            self.header_rects[label] = painter.text(label, (center, top+5), role='small',
                                                   color=GOLD, anchor='midtop', bold=True)
        if model.phase == 'ready':
            painter.rect(FOREST_LIGHT, self.party_rows[model.ready_actor]['row'])
        painter.line(BRASS, (152, top+small+7), (460, top+small+7))
        for member in model.party:
            row = self.party_rows[member.identifier]
            painter.text(member.name, row['name'].topleft, role='name',
                         color=GOLD if member.hp else MUTED, bold=True)
            painter.text(str(member.hp)+'/'+str(member.max_hp),
                         (row['hp'].left, row['name'].top), role='small')
            self._bar(painter, row['hp'], member.hp/member.max_hp,
                      self._health_color(member.hp, member.max_hp))
            painter.text(str(member.mp)+'/'+str(member.max_mp),
                         (row['mp'].left, row['name'].top), role='small')
            self._bar(painter, row['mp'], member.mp/member.max_mp if member.max_mp else 0, MP_BLUE)
            self._bar(painter, row['atb'], member.atb, ATB_YELLOW)
            painter.line(FOREST_LIGHT, (152, row['row'].bottom), (460, row['row'].bottom))
        painter.line(FOREST_LIGHT, (142, top+5), (142, self.panel_rect.bottom-5))
        for x in (214, 288, 384):
            painter.line(FOREST_LIGHT, (x, top+5), (x, self._party_bottom))
        for index, line in enumerate(self._detail_lines):
            painter.text(line, (152, self._detail_top+index*small), role='small',
                         color=MUTED if self.result_error else IVORY)
        if model.phase in RESULTS:
            painter.button(self.continue_rect, 'Try again' if self.result_error else 'Continue')
        elif model.phase == 'ready':
            for index, (identifier, rect) in enumerate(self.command_rects.items()):
                disabled = bool(model.action_reason(identifier))
                painter.rect(FOREST, rect)
                painter.text(ACTION_LABELS.get(identifier, identifier), rect.center,
                             role='small', anchor='center', color=MUTED if disabled else IVORY)
                if index == self.selected and not disabled:painter.rect(GOLD, rect, 1)
            if self._notice:
                painter.text(self._notice, (240, self.panel_rect.top-6),
                             role='small', color=GOLD, anchor='midbottom')
        else:
            painter.text('Waiting' if model.phase == 'charging' else 'Acting',
                         (20, self.name_rect.top), role='small', color=MUTED)
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
        spoken = painter.wrap(line['text'], 400, role='small')
        hints = painter.wrap(line['help'], 400, role='small') if line['help'] else []
        button_height = max(20, painter.font().get_height()+4)
        height = 24+small+(len(spoken)+len(hints))*small+button_height+(5 if hints else 0)
        panel = pygame.Rect(22, 10, 436, height)
        painter.panel(panel)
        painter.text('Mira', (34, 18), role='small', color=GOLD, bold=True)
        y = 20+small
        for text in spoken:
            painter.text(text, (34, y), role='small');y += small
        if hints:y += 5
        for text in hints:
            painter.text(text, (34, y), role='small', color=MUTED);y += small
        self.tutorial_continue_rect = pygame.Rect(354, panel.bottom-button_height-8,
                                                   90, button_height)
        painter.button(self.tutorial_continue_rect, 'Continue')
