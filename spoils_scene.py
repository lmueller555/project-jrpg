"""A dedicated, input-safe screen for the rewards from a won battle.

The encounter owner settles the journey and calls set_awarded or set_error.
This view never grants progression, changes inventory, or controls music.
"""
from __future__ import annotations

from copy import deepcopy
import math

import pygame

from ui_style import FOREST, FOREST_DARK, FOREST_LIGHT, GOLD, BRASS, IVORY, MUTED, ERROR


CRYSTAL_COLORS = {
    'aether_emerald': '#76c58f', 'aether_sapphire': '#72a9e2',
    'aether_ruby': '#e58380', 'aether_amethyst': '#b995d7',
    'aether_opal': '#eee7d2', 'aether_topaz': '#e9c464',
    'aether_diamond': '#c6e4df',
}


class SpoilsScene:
    def __init__(self, game, rewards, *, party=None, model=None):
        self.game, self.model = game, model
        self.party = tuple(party or ())
        self.rewards = self._snapshot(rewards)
        self.awarded = False
        self.dismissed = False
        self.retry_requested = False
        self.result_error = ''
        self.paused = False
        self.focused = True
        self._held = False
        self._hover = False
        self._elapsed = 0.0
        self.scroll = self.max_scroll = 0.0
        self.panel_rect = pygame.Rect(16, 14, 448, 292)
        self.title_rect = pygame.Rect(80, 26, 320, 28)
        self.experience_rect = pygame.Rect(30, 76, 420, 54)
        self.items_view = pygame.Rect(30, 156, 420, 88)
        self.continue_rect = pygame.Rect(314, 262, 136, 30)
        self.retry_rect = self.continue_rect.copy()
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.item_rects = {}
        self._rows = []
        self._footer_lines = []

    @staticmethod
    def _snapshot(rewards):
        if (not isinstance(rewards, dict) or type(rewards.get('rp')) is not int
                or rewards['rp'] < 0 or not isinstance(rewards.get('drops'), dict)
                or any(not isinstance(key, str) or type(value) is not int or value <= 0
                       for key, value in rewards['drops'].items())):
            raise ValueError('Invalid spoils snapshot')
        return deepcopy({'rp': rewards['rp'], 'drops': rewards['drops']})

    @property
    def ready(self):return self.awarded and not self.result_error

    @property
    def tutorial_active(self):return False

    def set_pending(self):
        self.awarded = False
        self.result_error = ''
        self.retry_requested = False

    def set_awarded(self, rewards=None):
        if rewards is not None:self.rewards = self._snapshot(rewards)
        self.awarded = True
        self.result_error = ''
        self.retry_requested = False

    def set_error(self, message):
        self.awarded = False
        self.result_error = str(message).strip() or 'Rewards could not be collected. Please retry.'
        self.retry_requested = False

    def _sound(self, kind):self.game.ui.sound(kind)

    def _beneficiary(self):
        first = self.party[0] if self.party else None
        if isinstance(first, dict):return first.get('name', 'Caelan')
        return getattr(first, 'name', first if isinstance(first, str) else 'Caelan')

    def _layout(self, painter):
        small = painter.font('small').get_linesize()
        name = painter.font('name', bold=True).get_linesize()
        body = painter.font().get_linesize()
        heading = painter.font('heading', bold=True).get_linesize()
        self.title_rect = pygame.Rect(55, 26, 370, heading)
        rule = self.title_rect.bottom + 8
        self.experience_rect = pygame.Rect(30, rule + 10, 420, small + name + 19)
        items_label_y = self.experience_rect.bottom + 10
        item_top = items_label_y + small + 7

        message = (self.result_error if self.result_error else
                   'Rewards received.' if self.awarded else 'Collecting rewards…')
        self._footer_lines = painter.wrap(message, 260, role='small')
        if len(self._footer_lines) > 3:
            self._footer_lines = self._footer_lines[:3]
            self._footer_lines[-1] = self._footer_lines[-1].rstrip(' .') + '…'
        button_height = max(28, body + 12)
        footer_height = max(button_height, len(self._footer_lines) * small + 4)
        footer_top = self.panel_rect.bottom - 12 - footer_height
        self.continue_rect = pygame.Rect(314, self.panel_rect.bottom - 12 - button_height,
                                         136, button_height)
        self.retry_rect = self.continue_rect.copy()
        self._footer_top = footer_top
        self.items_view = pygame.Rect(30, item_top, 420, max(26, footer_top - 10 - item_top))
        self._items_label_y = items_label_y
        self._rule_y = rule
        self._small = small
        definitions = getattr(getattr(self.game, 'inventory', None), 'definitions', {})
        drops = sorted(self.rewards['drops'].items(),
                       key=lambda pair: definitions.get(pair[0], {}).get('name', pair[0]).casefold())
        self._rows = []
        y = 0
        for identifier, quantity in drops:
            label = definitions.get(identifier, {}).get('name', identifier.replace('_', ' ').title())
            quantity_text = '×' + str(quantity)
            quantity_width = max(48, painter.font().size(quantity_text)[0] + 10)
            lines = painter.wrap(label, self.items_view.width - quantity_width - 45)
            height = max(34, len(lines) * body + 14)
            self._rows.append((identifier, lines, quantity_text,
                               pygame.Rect(self.items_view.x, y, self.items_view.width - 10, height)))
            y += height + 4
        self.max_scroll = max(0, y - 4 - self.items_view.height)
        self.scroll = max(0.0, min(self.scroll, self.max_scroll))
        self.item_rects = {}
        for identifier, _, _, rect in self._rows:
            displayed = rect.move(0, self.items_view.y - round(self.scroll))
            if displayed.colliderect(self.items_view):
                self.item_rects[identifier] = displayed.clip(self.items_view)

    def _confirm(self):
        if self.result_error:
            self.retry_requested = True
            self._sound('confirm')
        elif self.ready:
            self.dismissed = True
            self._sound('confirm')

    def handle_event(self, event):
        if self.dismissed:return True
        self._layout(self.game.ui.painter(self.game.ui_surface))
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self.paused = True
            self._held = False
            return True
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            return True
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:
                if self.focused:
                    self.paused = not self.paused
                    self._held = False
                    self._sound('back' if self.paused else 'confirm')
                return True
            if self.paused or not self.focused:return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._confirm()
            elif event.key in (pygame.K_DOWN, pygame.K_UP, pygame.K_PAGEDOWN, pygame.K_PAGEUP,
                               pygame.K_HOME, pygame.K_END):
                if event.key == pygame.K_HOME:self.scroll = 0
                elif event.key == pygame.K_END:self.scroll = self.max_scroll
                else:
                    step = self.items_view.height if event.key in (pygame.K_PAGEDOWN, pygame.K_PAGEUP) else 30
                    self.scroll += step * (-1 if event.key in (pygame.K_UP, pygame.K_PAGEUP) else 1)
                    self.scroll = max(0, min(self.scroll, self.max_scroll))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if point is None:return True
            if self.paused:
                if self.focused and self.resume_rect.collidepoint(point):
                    self.paused = False
                    self._sound('confirm')
                return True
            if self.focused and self.continue_rect.collidepoint(point):self._confirm()
        elif event.type == pygame.MOUSEWHEEL and self.focused and not self.paused:
            self.scroll = max(0, min(self.max_scroll, self.scroll - event.y * 30))
        elif event.type == pygame.MOUSEMOTION:
            self._hover = point is not None and self.continue_rect.collidepoint(point)
        return True

    def update(self, seconds):
        if type(seconds) not in (int, float):raise TypeError('Scene time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid scene time')
        if not self.paused and self.focused:self._elapsed += seconds

    @staticmethod
    def _item_icon(painter, identifier, rect):
        color = CRYSTAL_COLORS.get(identifier)
        if color:
            x, y = rect.center
            points = [(x, y-7), (x+5, y-2), (x+3, y+5), (x, y+8), (x-4, y+4), (x-5, y-2)]
            pygame.draw.polygon(painter.canvas, color, [painter.point(point) for point in points])
            painter.line(IVORY, (x, y-5), (x-2, y-1))
        else:
            painter.rect(BRASS, rect.inflate(-7, -7), 1)
            painter.line(BRASS, (rect.centerx, rect.top+4), (rect.centerx, rect.bottom-4))

    def draw(self, world_canvas, ui_surface):
        world_canvas.fill(FOREST_DARK)
        ui_surface.fill(FOREST_DARK)
        painter = self.game.ui.painter(ui_surface)
        self._layout(painter)
        painter.panel(self.panel_rect)
        painter.text('Spoils of Battle', (240, self.title_rect.y), role='heading', color=GOLD,
                     anchor='midtop', bold=True)
        painter.lantern((35, self.title_rect.centery), size=11)
        painter.lantern((445, self.title_rect.centery), size=11)
        painter.line(BRASS, (30, self._rule_y), (450, self._rule_y))
        painter.rect(FOREST_DARK, self.experience_rect)
        painter.rect(FOREST_LIGHT, self.experience_rect, 1)
        painter.text('Resonance Points (RP)', (40, self.experience_rect.top+7),
                     role='small', color=MUTED, bold=True)
        y = self.experience_rect.top + 9 + self._small
        painter.text(self._beneficiary(), (40, y), role='name', bold=True)
        painter.text('+' + str(self.rewards['rp']) + ' RP', (438, y), role='name', color=GOLD,
                     anchor='topright', bold=True)
        painter.text('Items', (30, self._items_label_y), role='small', color=GOLD, bold=True)
        painter.clip(self.items_view)
        if not self._rows:
            painter.text('No items recovered.', self.items_view.center, color=MUTED, anchor='center')
        body = painter.font().get_linesize()
        for identifier, lines, quantity, relative in self._rows:
            row = relative.move(0, self.items_view.y - round(self.scroll))
            if not row.colliderect(self.items_view):continue
            painter.rect(FOREST_DARK, row)
            self._item_icon(painter, identifier, pygame.Rect(row.left+4, row.top+5, 20, 22))
            for index, text in enumerate(lines):
                painter.text(text, (row.left+29, row.top+7+index*body))
            painter.text(quantity, (row.right-6, row.top+7), color=GOLD, anchor='topright', bold=True)
        painter.clip()
        if self.max_scroll:
            track = pygame.Rect(self.items_view.right-4, self.items_view.top, 3, self.items_view.height)
            painter.rect(FOREST_LIGHT, track)
            height = max(12, round(track.height * self.items_view.height / (self.max_scroll+self.items_view.height)))
            offset = round((track.height-height) * self.scroll/self.max_scroll)
            painter.rect(BRASS, (track.x, track.y+offset, track.width, height))
        for index, text in enumerate(self._footer_lines):
            painter.text(text, (30, self._footer_top+index*self._small+2), role='small',
                         color=ERROR if self.result_error else GOLD if self.awarded else MUTED)
        painter.button(self.continue_rect, 'Retry' if self.result_error else 'Continue',
                       selected=self._hover, pressed=self._held and self._hover,
                       disabled=not self.ready and not self.result_error)
        if self.paused:
            painter.veil(150)
            painter.panel((124, 111, 232, 100))
            painter.text('Spoils paused', (240, 126), color=GOLD, anchor='midtop', bold=True)
            painter.button(self.resume_rect, 'Resume', disabled=not self.focused)
        painter.clip()
