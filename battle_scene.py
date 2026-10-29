"""A separate Eldenmere battle view with a compact, player-only ATB display."""
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


class CombatSprites:
    """Native pixel frames shared by the battle scene and the roaming Bat."""

    def __init__(self, root=COMBAT_ART):
        self.actors = {}
        for actor in ('caelan', 'bat'):
            folder = Path(root)/actor
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

    def __init__(self, game, model, sprites=None):
        self.game, self.model = game, model
        self.sprites = sprites if sprites is not None else CombatSprites()
        self.dismissed = False
        self.result_error = ''
        self.paused = False
        self.focused = True
        self.selected = 0
        self._held = False
        self._elapsed = 0.0
        self._phase_elapsed = 0.0
        self._defeat_times = {actor: 0.0 for actor, member in
                              (('player', model.player), ('enemy', model.enemy)) if not member.hp}
        self._popups = []
        self._last_phase = model.phase
        self._notice = ''
        self.panel_rect = pygame.Rect(8, 204, 464, 108)
        self.command_rects = {}
        self.continue_rect = pygame.Rect(268, 267, 180, 29)
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.atb_rect = pygame.Rect(56, 290, 174, 10)
        self._background = self._make_background()

    @staticmethod
    def _make_background():
        """An original, quiet clearing; it does not advance the exploration world."""
        image = pygame.Surface((480, 320))
        image.fill(FOREST_DARK)
        pygame.draw.rect(image, '#3b5a4a', (0, 0, 480, 80))
        for band, color in ((25, '#294a3d'), (44, '#345943'), (66, '#42694b')):
            for x in range(-18, 500, 36):
                top = band-(x//36 % 3)*6
                pygame.draw.polygon(image, color, ((x, 100), (x+19, top), (x+40, 100)))
        pygame.draw.rect(image, '#55794d', (0, 88, 480, 120))
        pygame.draw.ellipse(image, '#68834f', (-60, 101, 610, 174))
        pygame.draw.ellipse(image, '#758956', (34, 142, 412, 111))
        # Stable grass flecks are native pixels, not time-based noise.
        for index in range(75):
            x = (index*67+19) % 480
            y = 95+(index*37) % 112
            color = '#496d45' if index % 3 else '#83935b'
            pygame.draw.line(image, color, (x, y), (x+2, y-2), 1)
        pygame.draw.rect(image, FOREST_DARK, (0, 204, 480, 116))
        return image

    def _layout(self, painter):
        small = painter.font('small').get_linesize()
        name = painter.font('name', bold=True).get_linesize()
        height = max(108, name+small*3+24)
        self.panel_rect = pygame.Rect(8, 312-height, 464, height)
        top = self.panel_rect.top
        self.atb_rect = pygame.Rect(56, top+name+small*2+18, 174, 9)
        self.continue_rect = pygame.Rect(258, self.panel_rect.bottom-39, 196, 29)
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.command_rects = {}
        for index, identifier in enumerate(self.model.available_actions()):
            self.command_rects[identifier] = pygame.Rect(250+(index % 2)*106,
                                                        top+29+(index//2)*35, 100, 30)
        return small, name

    def _sound(self, kind):self.game.ui.sound(kind)

    def _confirm(self):
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
        if self.dismissed or self.paused or not self.focused:return
        if type(seconds) not in (int, float):raise TypeError('Scene time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid scene time')
        self._elapsed += seconds
        for popup in self._popups:popup['age'] += seconds
        self._popups = [popup for popup in self._popups if popup['age'] < 1.1]
        self.model.update(seconds)
        self._phase_elapsed = (0.0 if self.model.phase != self._last_phase
                               else self._phase_elapsed+seconds)
        for event in self.model.drain_events():
            if event['type'] == 'impact':
                self._popups.append({'target': event['target'],
                                     'text': str(event['damage']), 'age': 0.0})
                if not event['remaining_hp']:self._defeat_times[event['target']] = self._elapsed
            elif event['type'] == 'guard':
                self._popups.append({'target': 'player', 'text': 'Guard', 'age': 0.0})
            elif event['type'] == 'player_ready':
                self.selected = 0
                self._notice = ''
        self._last_phase = self.model.phase

    @property
    def reduced_motion(self):return getattr(self.game.audio, 'reduced_motion', False)

    def _positions(self):
        positions = {'player': pygame.Vector2(354, 184), 'enemy': pygame.Vector2(126, 170)}
        if not self.reduced_motion:positions['enemy'].y += math.sin(self._elapsed*4)*2
        action = self.model.current_action
        if action is not None and action.kind == 'physical' and not self.reduced_motion:
            approach = (action.elapsed/max(.001, action.impact_at)
                        if action.elapsed <= action.impact_at else
                        (action.duration-action.elapsed)/max(.001, action.duration-action.impact_at))
            blend = 1-(1-max(0.0, min(1.0, approach)))**3
            positions[action.actor] += pygame.Vector2(-202 if action.actor == 'player' else 202,
                                                       -10 if action.actor == 'player' else 17)*blend
        return positions

    def _pose(self, actor):
        combatant = self.model.player if actor == 'player' else self.model.enemy
        if combatant.hp <= 0:
            return 'defeat', (self._elapsed-self._defeat_times.get(actor, 0))*1000
        if actor == 'player' and self.model.phase == 'victory':return 'victory', self._phase_elapsed*1000
        for popup in self._popups:
            if popup['target'] == actor and popup['text'].isdigit() and popup['age'] < .28:
                return 'hurt', popup['age']*1000
        action = self.model.current_action
        if action is not None and action.actor == actor:
            state = ('cast' if action.kind == 'magical' else 'guard' if action.kind == 'guard'
                     else 'idle' if action.kind == 'flee' else 'attack')
            return state, action.elapsed*1000
        if combatant.guarded:return 'guard', self._elapsed*1000
        return 'idle', self._elapsed*1000

    def _draw_field(self, canvas):
        canvas.blit(self._background, (0, 0))
        positions = self._positions()
        for actor in ('enemy', 'player'):
            point = positions[actor]
            pygame.draw.ellipse(canvas, '#496044', (round(point.x)-20, 181, 40, 8))
            state, time = self._pose(actor)
            image, anchor = self.sprites.frame('caelan' if actor == 'player' else 'bat', state, time)
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

    @staticmethod
    def _bar(painter, rect, fraction, color):
        painter.rect(FOREST_DARK, rect)
        inner = pygame.Rect(rect).inflate(-2, -2)
        inner.width = round(inner.width*max(0, min(1, fraction)))
        if inner.width:painter.rect(color, inner)
        painter.rect(BRASS, rect, 1)

    def draw(self, world_canvas, ui_surface):
        self._draw_field(world_canvas)
        pygame.transform.scale(world_canvas, ui_surface.get_size(), ui_surface)
        painter = self.game.ui.painter(ui_surface)
        small, name = self._layout(painter)
        model, player, enemy = self.model, self.model.player, self.model.enemy
        painter.text(enemy.name, (126, 43), role='name', anchor='center', bold=True)
        self._bar(painter, pygame.Rect(86, 57, 80, 6), enemy.hp/enemy.value('hp'), '#9ab46b')
        caption = model.current_action.name if model.current_action is not None else 'Eldenmere'
        painter.text(caption, (240, 15), color=GOLD, anchor='midtop')
        for popup in self._popups:
            x = 354 if popup['target'] == 'player' else 126
            y = 99-(0 if self.reduced_motion else min(14, popup['age']*20))
            painter.text(popup['text'], (x+1, y+1), role='name', color=FOREST_DARK, anchor='center', bold=True)
            painter.text(popup['text'], (x, y), role='name', color=GOLD, anchor='center', bold=True)
        painter.panel(self.panel_rect)
        top = self.panel_rect.top
        painter.text(player.name, (20, top+8), role='name', color=GOLD, bold=True)
        painter.text('HP '+str(player.hp)+' / '+str(player.value('hp')),
                     (20, top+name+10), role='small')
        painter.text('MP '+str(player.mp)+' / '+str(player.value('mp')),
                     (20, top+name+small+11), role='small')
        painter.text('ATB', (20, self.atb_rect.centery), role='small', color=GOLD, anchor='midleft')
        self._bar(painter, self.atb_rect, player.atb, GOLD if model.phase == 'ready' else '#91b58d')
        painter.line(FOREST_LIGHT, (240, top+10), (240, self.panel_rect.bottom-10))
        if model.phase in RESULTS:
            title = {'victory': 'Victory', 'defeat': 'Defeated', 'fled': 'Escaped'}[model.phase]
            painter.text(title, (254, top+9), color=GOLD, bold=True)
            if self.result_error:
                for index, line in enumerate(painter.wrap(self.result_error, 198, role='small')[:2]):
                    painter.text(line, (254, top+31+index*small), role='small', color=MUTED)
            elif model.phase == 'victory':
                rewards = model.enemy_definition['rewards']
                reward_text = str(rewards['rp'])+' RP'
                definitions = getattr(getattr(self.game, 'inventory', None), 'definitions', {})
                for identifier, quantity in rewards['drops'].items():
                    name = definitions.get(identifier, {}).get('name', identifier.replace('_', ' ').title())
                    reward_text += ' · '+name+' ×'+str(quantity)
                for index, line in enumerate(painter.wrap(reward_text, 198, role='small')[:2]):
                    painter.text(line, (254, top+31+index*small), role='small')
            elif model.phase == 'defeat':
                painter.text('Return to Eldenmere.', (254, top+34), role='small')
            painter.button(self.continue_rect, 'Try again' if self.result_error else 'Continue')
        elif model.phase == 'ready':
            painter.text('Choose action', (254, top+8), role='small', color=GOLD)
            for index, (identifier, rect) in enumerate(self.command_rects.items()):
                disabled = bool(model.action_reason(identifier))
                painter.button(rect, ACTION_LABELS.get(identifier, identifier), disabled=disabled)
                if index == self.selected and not disabled:painter.rect(GOLD, rect, 1)
            if self._notice:
                painter.text(self._notice, (240, self.panel_rect.top-6),
                             role='small', color=GOLD, anchor='midbottom')
        else:
            painter.text('Waiting' if model.phase == 'charging' else 'Acting',
                         (254, top+10), color=MUTED)
            text = model.message if model.phase == 'acting' else 'Preparing the next action.'
            for index, line in enumerate(painter.wrap(text, 198, role='small')[:2]):
                painter.text(line, (254, top+38+index*small), role='small')
        if self.paused:
            painter.veil(150)
            painter.panel((124, 111, 232, 100))
            painter.text('Battle paused', (240, 126), color=GOLD, anchor='midtop', bold=True)
            painter.button(self.resume_rect, 'Resume', disabled=not self.focused)
        painter.clip()
