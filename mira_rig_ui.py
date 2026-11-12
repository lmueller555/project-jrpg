"""Mira's wearable arm-rig console, with local drafts and deliberate commits.

An optional apply callback binds this editor to an authoritative battle model.
The standalone art study supplies no callback and remains entirely local. The
widget owns no character resources, ability effects, progression or save files.
"""
from __future__ import annotations

import pygame

from ui_style import FOREST, FOREST_DARK, FOREST_LIGHT, GOLD, BRASS, IVORY, MUTED


CHANNELS = ('weapons', 'protection', 'support')
COLORS = {'weapons': '#ec9c59', 'protection': '#76c8dc', 'support': '#8dca9d'}
DESCRIPTIONS = {
    'weapons': 'Weapons · forearm emitter and powered actuator',
    'protection': 'Protection · bracer plates and barrier projector',
    'support': 'Support · sensors and engineering tools',
}
CAPACITY = 6


class MiraRigUI:
    """A compact, keyboard/mouse allocation console with explicit input focus."""

    def __init__(self, allocation=None, *, on_apply=None):
        allocation = dict.fromkeys(CHANNELS, 2) if allocation is None else allocation
        if not self.valid_allocation(allocation):raise ValueError('Invalid rig allocation')
        self._allocation = dict(allocation)
        self._draft = dict(allocation)
        self.on_apply = on_apply
        self.rect = pygame.Rect(0, 0, 120, 60)
        self.buttons = {}
        self.channel_rects = {}
        self.pip_rects = {}
        self.focused = False
        self.selected_channel = 'weapons'
        self.notice = ''
        self._held = False
        self._row_height = 11
        self._header_height = 11
        self._footer_height = 12

    @staticmethod
    def valid_allocation(value):
        return (isinstance(value, dict) and set(value) == set(CHANNELS)
                and all(type(value[key]) is int and 0 <= value[key] <= CAPACITY for key in CHANNELS)
                and sum(value.values()) == CAPACITY)

    @property
    def allocation(self):return dict(self._allocation)

    @property
    def draft(self):return dict(self._draft)

    @property
    def available(self):return CAPACITY-sum(self._draft.values())

    @property
    def dirty(self):return self._draft != self._allocation

    @property
    def detail_text(self):
        if self.notice:return self.notice
        return DESCRIPTIONS[self.selected_channel]

    def adjust(self, channel, delta):
        if channel not in CHANNELS or type(delta) is not int or delta not in (-1, 1):return False
        if self._draft[channel]+delta < 0 or delta > 0 and self.available == 0:
            self.notice = ('Remove a unit from another system first.' if delta > 0
                           else 'This system has no allocated power.')
            return False
        self.selected_channel = channel
        self._draft[channel] += delta
        self.notice = ''
        return True

    def commit(self):
        if not self.valid_allocation(self._draft):
            self.notice = 'Allocate all six power units before applying.'
            return False
        if self.on_apply is not None:
            self.notice = ''
            if not self.on_apply(dict(self._draft)):
                if not self.notice:self.notice = 'The rig cannot be configured right now.'
                return False
        self._allocation = dict(self._draft)
        self.notice = ('Allocation applied to the preview.' if self.on_apply is None
                       else 'Power allocation applied.')
        return True

    def sync(self, allocation):
        """Accept an authoritative allocation without discarding unchanged drafts."""
        if not self.valid_allocation(allocation):return False
        if allocation != self._allocation:
            self._allocation = dict(allocation)
            self.cancel()
        return True

    def cancel(self):
        self._draft = dict(self._allocation)
        self.notice = ''

    def layout(self, rect, painter=None):
        self.rect = pygame.Rect(rect)
        small = 9 if painter is None else painter.font('small').get_linesize()
        self._header_height = max(11, small+2)
        self._footer_height = max(12, small+3)
        self._row_height = max(10, (self.rect.height-self._header_height-self._footer_height)//3)
        # All logical hit boxes remain within the supplied character column.
        self.buttons = {}
        self.channel_rects = {}
        for index, key in enumerate(CHANNELS):
            row = pygame.Rect(self.rect.left+2,
                              self.rect.top+self._header_height+index*self._row_height,
                              self.rect.width-4, self._row_height)
            self.channel_rects[key] = row
            size = min(13, self._row_height-1)
            for offset, sign in enumerate(('+', '-')):
                button = pygame.Rect(row.right-2-size-offset*(size+2), row.centery-size//2, size, size)
                self.buttons[(key, sign)] = button
        footer_y = self.rect.bottom-self._footer_height+1
        cancel_width = max(14, self._footer_height-2)
        apply_width = 41 if self.rect.width >= 140 else 30
        self.buttons['cancel'] = pygame.Rect(self.rect.right-cancel_width-3, footer_y,
                                              cancel_width, self._footer_height-2)
        self.buttons['apply'] = pygame.Rect(self.buttons['cancel'].left-apply_width-3,
                                             footer_y, apply_width, self._footer_height-2)
        return self.rect

    def handle_event(self, event, point=None, enabled=True):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self._held = False
            return False
        if not enabled:
            self.cancel()
            self.focused = False
            self._held = False
            return False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            return self.focused and point is not None and self.rect.collidepoint(point)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if point is None or not self.rect.collidepoint(point):
                self.focused = False
                return False
            if self._held:return True
            self._held = True;self.focused = True
            for key, rect in self.buttons.items():
                if not rect.collidepoint(point):continue
                if key == 'apply':self.commit()
                elif key == 'cancel':self.cancel()
                else:self.adjust(key[0], 1 if key[1] == '+' else -1)
                return True
            for key, rect in self.channel_rects.items():
                if rect.collidepoint(point):self.selected_channel = key;self.notice = '';break
            return True
        if event.type != pygame.KEYDOWN or not self.focused:return False
        if getattr(event, 'repeat', False):return True
        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.cancel();self.focused = False
        elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
            direction = -1 if event.key == pygame.K_UP else 1
            if event.key == pygame.K_TAB and getattr(event, 'mod', 0) & pygame.KMOD_SHIFT:direction = -1
            self.selected_channel = CHANNELS[(CHANNELS.index(self.selected_channel)+direction) % 3]
            self.notice = ''
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.adjust(self.selected_channel, -1 if event.key == pygame.K_LEFT else 1)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):self.commit()
        else:return False
        return True

    @staticmethod
    def _icon(painter, key, center, color):
        x, y = center
        if key == 'weapons':
            points = ((x+2, y-4), (x-2, y), (x+1, y), (x-2, y+4))
            for start, end in zip(points, points[1:]):painter.line(color, start, end)
        elif key == 'protection':
            points = ((x-3, y-3), (x+3, y-3), (x+3, y+1), (x, y+4), (x-3, y+1), (x-3, y-3))
            for start, end in zip(points, points[1:]):painter.line(color, start, end)
            painter.line(color, (x, y-2), (x, y+2))
        else:
            painter.line(color, (x-3, y+3), (x+2, y-2), 2)
            painter.line(color, (x+2, y-2), (x+2, y-4))
            painter.line(color, (x+2, y-2), (x+4, y-2))

    @staticmethod
    def _button(painter, rect, text, enabled=True, color=IVORY):
        painter.rect(FOREST_DARK, rect)
        painter.rect(BRASS if enabled else FOREST_LIGHT, rect, 1)
        painter.text(text, rect.center, role='small', color=color if enabled else MUTED,
                     anchor='center', bold=True)

    def draw(self, painter, rect=None, enabled=True, focused=None):
        if rect is not None:self.layout(rect, painter)
        else:self.layout(self.rect, painter)
        focused = self.focused if focused is None else focused
        bounds = self.rect
        previous_clip = painter.canvas.get_clip()
        painter.clip(bounds)
        painter.rect(FOREST_DARK, bounds)
        painter.rect(BRASS if enabled else FOREST_LIGHT, bounds, 1)
        # Copper bus at the left and two miniature fasteners make the console
        # feel like a built object without competing with the character art.
        painter.line(BRASS, (bounds.left+2, bounds.top+2), (bounds.left+2, bounds.bottom-3))
        for x in (bounds.left+4, bounds.right-5):
            painter.rect(GOLD, (x, bounds.top+2, 1, 1))
        title = 'ARM RIG' if bounds.width >= 140 else 'RIG'
        painter.text(title, (bounds.left+7, bounds.top+2), role='small', color=GOLD, bold=True)
        if not enabled:
            x=bounds.left+7+painter.font('small').size(title)[0]+5
            y=bounds.top+3
            painter.rect(MUTED,(x,y+3,6,5))
            painter.rect(MUTED,(x+1,y,4,5),1)
            painter.line(FOREST_DARK,(x+3,y+5),(x+3,y+6))
        budget = str(CAPACITY-self.available)+'/'+str(CAPACITY)
        painter.text(budget, (bounds.right-5, bounds.top+2), role='small', color=GOLD, anchor='topright')
        # Channel symbols identify each row; the pips show allocated power.
        self.pip_rects = {}
        for key in CHANNELS:
            row = self.channel_rects[key]
            chosen = enabled and focused and key == self.selected_channel
            painter.rect(FOREST_LIGHT if chosen else FOREST, row)
            if chosen:painter.rect(GOLD, row, 1)
            color = COLORS[key] if enabled else MUTED
            self._icon(painter, key, (row.left+8, row.centery), color)
            first_button = self.buttons[(key, '-')]
            pip_left = row.left+20
            pip_right = first_button.left-4
            step = min(10, max(3, (pip_right-pip_left)//CAPACITY))
            pip_left += max(0, (pip_right-pip_left-CAPACITY*step)//2)
            pip_width = max(2, step-2)
            self.pip_rects[key] = []
            for index in range(CAPACITY):
                pip = pygame.Rect(pip_left+index*step, row.centery-2, pip_width, 4)
                self.pip_rects[key].append(pip)
                painter.rect(color if index < self._draft[key] else FOREST_DARK, pip)
                painter.rect(color if index < self._draft[key] else BRASS, pip, 1)
            for sign in ('-', '+'):
                can_change = enabled and (self._draft[key] > 0 if sign == '-' else self.available > 0)
                self._button(painter, self.buttons[(key, sign)], '−' if sign == '-' else '+', can_change)
        footer = self.buttons['apply']
        footer_text = str(self.available)+' free' if self.available else ('Edited' if self.dirty else 'Ready')
        painter.text(footer_text, (bounds.left+6, footer.centery), role='small', color=MUTED, anchor='midleft')
        self._button(painter, footer, 'Apply' if bounds.width >= 140 else 'OK', enabled and self.available == 0,
                     color=GOLD)
        self._button(painter, self.buttons['cancel'], '×', enabled and self.dirty)
        painter.canvas.set_clip(previous_clip)
        return bounds
