"""Shared, legible pause/settings panels with explicit overlay ownership."""
from __future__ import annotations

import pygame

from ui_style import UIStyle, FOREST, FOREST_LIGHT, FOREST_DARK, IVORY, BRASS, GOLD, MUTED


DECREASE_KEYS = (pygame.K_LEFT, pygame.K_a, pygame.K_MINUS, pygame.K_KP_MINUS)
INCREASE_KEYS = (pygame.K_RIGHT, pygame.K_d, pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)


class SettingsPanel:
    """The same settings layout and slider behavior on title and pause screens."""
    labels = ('Display', 'Music', 'Effects', 'Text size', 'Reduced motion',
              'Objective tracker', 'Controls', 'Back')

    def __init__(self, owner, logical_size=(480, 320)):
        self.owner = owner
        self.game = owner.game
        self.logical_size = logical_size
        width, height = logical_size
        self.panel = pygame.Rect((width-376)//2, (height-286)//2, 376, 286)
        self.rows = [pygame.Rect(self.panel.left+14, self.panel.top+47+index*25, 348, 23)
                     for index in range(len(self.labels))]
        self.slider_rects = {index: pygame.Rect(row.left+130, row.centery-3, row.width-226, 6)
                             for index, row in enumerate(self.rows) if index in (1, 2)}
        self.controls = False
        self.controls_back = pygame.Rect(width//2-72, self.panel.bottom-34, 144, 23)
        self.dragging = None
        self.pressed = None
        self.scroll = 0
        self.row_height = 25
        self.max_scroll = 0
        self._manual_scroll = False
        self.viewport = pygame.Rect(self.panel.left+14, self.panel.top+47, 348, 198)

    def layout(self, painter):
        body_height = painter.font('body').get_height()
        small_height = painter.font('small').get_height()
        heading_height = painter.font('heading', bold=True).get_height()
        self.row_height = max(25, body_height+5)
        header = max(47, heading_height+21)
        footer = max(29, small_height+14)
        total = self.row_height*len(self.labels)
        height = min(self.logical_size[1]-16, max(286, header+total+footer))
        self.panel.height = height
        self.panel.centery = self.logical_size[1]//2
        self.viewport = pygame.Rect(self.panel.left+14, self.panel.top+header, 348, height-header-footer)
        self.max_scroll = max(0, total-self.viewport.height)
        self.scroll = min(self.max_scroll, max(0, self.scroll))
        if not self._manual_scroll:
            start = self.owner.selected*self.row_height
            self.scroll = min(self.scroll, start)
            self.scroll = max(self.scroll, start+self.row_height-self.viewport.height)
            self.scroll = min(self.max_scroll, max(0, self.scroll))
        self.rows[:] = [pygame.Rect(self.viewport.left, self.viewport.top+index*self.row_height-self.scroll,
                                   self.viewport.width, self.row_height-2) for index in range(len(self.labels))]
        self.slider_rects.clear()
        self.slider_rects.update({index: pygame.Rect(row.left+130, row.centery-3, row.width-226, 6)
                                  for index, row in enumerate(self.rows) if index in (1, 2)})
        self.controls_back.midbottom = (self.panel.centerx, self.panel.bottom-11)

    def reset(self):
        self.controls = False
        self.dragging = self.pressed = None
        self.scroll = 0
        self._manual_scroll = False

    def _sound(self, kind):self.game.ui.sound(kind)

    def _back(self):
        self._sound('back')
        if self.controls:
            self.controls = False
            self.owner.selected = 6
        else:
            self.owner.settings = False
            self.owner.selected = self.owner.settings_index
        self.dragging = self.pressed = None

    def _set_slider(self, index, point):
        track = self.slider_rects[index]
        value = max(0, min(1, (point[0]-track.left)/track.width))
        setter = self.game.audio.set_music if index == 1 else self.game.audio.set_effects
        changed = setter(value)
        if index == 1 and hasattr(self.owner, '_sync_music'):self.owner._sync_music()
        if changed:self._sound('move')

    def _adjust(self, direction):
        selected = self.owner.selected
        audio = self.game.audio
        self._manual_scroll = False
        changed = False
        if selected == 0:
            self.game.toggle_fullscreen();changed = True
        elif selected in (1, 2):
            setter = audio.set_music if selected == 1 else audio.set_effects
            current = audio.music_volume if selected == 1 else audio.effects_volume
            changed = setter(current+direction*.1)
            if selected == 1 and hasattr(self.owner, '_sync_music'):self.owner._sync_music()
        elif selected == 3:
            levels = (1.0, 1.25, 1.5)
            current = min(range(3), key=lambda i:abs(levels[i]-getattr(audio, 'text_scale', 1)))
            changed = audio.set_text_scale(levels[(current+direction) % 3])
        elif selected == 4:changed = audio.toggle_reduced_motion()
        elif selected == 5:changed = audio.toggle_tracker()
        if changed:self._sound('move')

    def activate(self):
        selected = self.owner.selected
        audio = self.game.audio
        if selected == 0:self.game.toggle_fullscreen()
        elif selected == 1:
            audio.toggle_music()
            if hasattr(self.owner, '_sync_music'):self.owner._sync_music()
        elif selected == 2:audio.toggle_effects()
        elif selected in (3, 4, 5):self._adjust(1);return True
        elif selected == 6:self.controls = True
        else:self._back();return True
        self._sound('confirm')
        return True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = self.pressed = None
            self.owner._mouse_held = False
            return True
        point = self.owner.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if self.controls:
            if ((event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False) and
                    event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)) or
                    (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and
                     point is not None and self.controls_back.collidepoint(point))):
                self._back()
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll-event.y*self.row_height))
            self._manual_scroll = True
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging is not None and point is not None:
                self._set_slider(self.dragging, point)
            elif point is not None and self.viewport.collidepoint(point):
                row = next((i for i, rect in enumerate(self.rows) if rect.collidepoint(point)), None)
                if row is not None and row != self.owner.selected:
                    self.owner.selected = row;self._sound('move')
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.owner._mouse_held:return True
            self.owner._mouse_held = True
            if point is None or not self.viewport.collidepoint(point):return True
            row = next((i for i, rect in enumerate(self.rows) if rect.collidepoint(point)), None)
            if row is None:return True
            self.owner.selected = self.pressed = row
            if row in (1, 2):
                track = self.slider_rects[row]
                if pygame.Rect(track.left-23, self.rows[row].top, 18, self.rows[row].height).collidepoint(point):
                    self._adjust(-1);return True
                if pygame.Rect(track.right+5, self.rows[row].top, 18, self.rows[row].height).collidepoint(point):
                    self._adjust(1);return True
                if track.inflate(0, 16).collidepoint(point):
                    self.dragging = row;self._set_slider(row, point);return True
            return self.activate()
        elif event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:self._back()
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                direction = -1 if event.key in (pygame.K_UP, pygame.K_w) else 1
                self.owner.selected = (self.owner.selected+direction) % len(self.rows)
                self._manual_scroll = False
                self._sound('move')
            elif event.key in DECREASE_KEYS:self._adjust(-1)
            elif event.key in INCREASE_KEYS:self._adjust(1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):return self.activate()
        return True

    def draw(self, painter):
        self.layout(painter)
        painter.panel(self.panel)
        center = self.panel.centerx
        painter.lantern((self.panel.left+23, self.panel.top+22), size=10)
        painter.text('Controls' if self.controls else 'Settings', (center, self.panel.top+8),
                     role='heading', color=GOLD, anchor='midtop', bold=True)
        painter.line(BRASS, (self.panel.left+15, self.viewport.top-8), (self.panel.right-15, self.viewport.top-8))
        if self.controls:
            controls = [('Move', 'WASD / arrow keys'), ('Run', 'Hold Shift'),
                        ('Read dialogue', 'Left click / Space / E'), ('Choose an answer', 'Click its button'),
                        ('Map / Journal / Satchel', 'M / J / I'), ('Inspect / Join meal', 'E near the prompt'),
                        ('Pause / Close', 'Escape'), ('Screen mode', 'F11')]
            spacing = min(25, max(20, (self.controls_back.top-self.viewport.top-8)//len(controls)))
            for index, (label, keys) in enumerate(controls):
                y = self.viewport.top+index*spacing
                painter.text(label, (self.panel.left+16, y), role='small', color=MUTED)
                painter.text(keys, (self.panel.right-16, y), role='small', anchor='topright')
            painter.button(self.controls_back, 'Back', selected=True)
            return
        audio = self.game.audio
        values = (('Fullscreen' if self.game.fullscreen else 'Windowed'),
                  f'{round(audio.music_volume*100)}%', f'{round(audio.effects_volume*100)}%',
                  f'{round(getattr(audio, "text_scale", 1)*100)}%',
                  'On' if getattr(audio, 'reduced_motion', False) else 'Off',
                  'Shown' if getattr(audio, 'tracker_visible', True) else 'Hidden', '', '')
        painter.clip(self.viewport)
        for index, (label, value, row) in enumerate(zip(self.labels, values, self.rows)):
            if not row.colliderect(self.viewport):continue
            selected = index == self.owner.selected
            if selected:
                painter.rect(FOREST_DARK if self.pressed == index else FOREST_LIGHT, row)
                painter.line(BRASS, row.bottomleft, row.bottomright)
            painter.text(label, (row.left+10, row.centery), anchor='midleft',
                         color=GOLD if selected else IVORY, bold=selected)
            if index in (1, 2):
                track = self.slider_rects[index]
                volume = audio.music_volume if index == 1 else audio.effects_volume
                painter.rect(FOREST_DARK, track)
                painter.rect(BRASS, track, 1)
                if volume:painter.rect(GOLD, (track.left, track.top+1, max(1, round(track.width*volume)), track.height-2))
                knob = pygame.Rect(round(track.left+volume*track.width)-3, track.centery-5, 6, 10)
                painter.rect(IVORY if self.dragging == index else GOLD, knob)
                painter.text('-', (track.left-14, row.centery), color=GOLD, anchor='center')
                painter.text('+', (track.right+14, row.centery), color=GOLD, anchor='center')
                painter.text(value, (row.right-8, row.centery), role='small', anchor='midright')
            elif value:
                painter.text(value, (row.right-10, row.centery), anchor='midright', color=GOLD if selected else IVORY)
        painter.clip()
        if self.max_scroll:
            track = pygame.Rect(self.panel.right-9, self.viewport.top, 3, self.viewport.height)
            painter.rect(FOREST_DARK, track)
            thumb = max(12, round(track.height*track.height/(track.height+self.max_scroll)))
            offset = round((track.height-thumb)*self.scroll/self.max_scroll)
            painter.rect(BRASS, (track.left, track.top+offset, track.width, thumb))
        painter.text('Sliders: drag • Arrows / +/-',
                     (center, self.panel.bottom-10), role='small', color=MUTED, anchor='midbottom')


class PauseMenu:
    settings_index = 4
    options = ('Resume', 'Inventory', 'Journal', 'Map', 'Settings', 'Quit')

    def __init__(self, game):
        self.game = game
        if not hasattr(game, 'ui'):game.ui = UIStyle(game)
        self.is_open = False
        self.settings = False
        self.selected = 0
        self.overlay = None
        self.rows = [pygame.Rect(146, 78+index*31, 188, 26) for index in range(len(self.options))]
        self.settings_panel = SettingsPanel(self)
        self.settings_rows = self.settings_panel.rows
        self.slider_rects = self.settings_panel.slider_rects
        self._mouse_held = False
        self._pressed = None
        self._opened_at = 0

    def open(self):
        self.is_open = True
        self.settings = False
        self.overlay = None
        self.selected = 0
        self.settings_panel.reset()
        self._mouse_held = False
        self.game._mouse_held = False
        self._opened_at = pygame.time.get_ticks()
        self.game.ui.sound('confirm')
        save = getattr(self.game, 'save_progress', None)
        if save is not None:save()

    def close(self):
        self.is_open = False
        self.settings = False
        self.overlay = None
        self.selected = 0
        self.settings_panel.reset()
        self._mouse_held = False
        self.game._mouse_held = False
        self.game.ui.sound('back')

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = ((point[0]-(width-480*scale)//2)/scale,
                 (point[1]-(height-320*scale)//2)/scale)
        return point if 0 <= point[0] < 480 and 0 <= point[1] < 320 else None

    def _row_at(self, point):
        if point is None:return None
        return next((index for index, row in enumerate(self.settings_rows if self.settings else self.rows)
                     if row.collidepoint(point)), None)

    def _adjust(self, direction):return self.settings_panel._adjust(direction)

    def activate(self):
        if self.settings:return self.settings_panel.activate()
        label=self.options[self.selected]
        if label == 'Resume':self.close()
        elif label == 'Inventory':
            self.overlay = 'inventory'
            self.game.inventory_ui.open()
        elif label == 'Journal':
            self.overlay = 'journal'
            self.game.quest_ui.journal_open = True
            self.game.ui.sound('confirm')
        elif label == 'Map':
            self.overlay = 'map'
            self.game.map_open = True
            self.game.ui.sound('confirm')
        elif label == 'Settings':
            self.settings = True;self.selected = 0;self.settings_panel.reset()
            self.game.ui.sound('confirm')
        elif label == 'Quit':
            self.game.ui.sound('confirm');return False
        return True

    def handle_event(self, event):
        if not self.is_open:return True
        if self.overlay is not None:
            if self.overlay == 'inventory':
                self.game.inventory_ui.handle_event(event)
                closed = not self.game.inventory_ui.is_open
            elif self.overlay == 'journal':
                self.game.quest_ui.handle_event(event)
                closed = not self.game.quest_ui.journal_open
            else:
                if hasattr(self.game, 'map_ui'):self.game.map_ui.handle_event(event)
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_m):self.game.map_open = False
                closed = not self.game.map_open
            if closed:
                self.overlay = None
                self._mouse_held = False
                self.game._mouse_held = False
                self.game.ui.sound('back')
            return True
        if self.settings:return self.settings_panel.handle_event(event)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_held = False;self._pressed = None
        elif event.type == pygame.MOUSEMOTION:
            row = self._row_at(self.to_canvas(event.pos))
            if row is not None and row != self.selected:
                self.selected = row;self.game.ui.sound('move')
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._mouse_held:return True
            self._mouse_held = True
            row = self._row_at(self.to_canvas(event.pos))
            if row is not None:
                self.selected = self._pressed = row
                return self.activate()
        elif event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:self.close()
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected+(-1 if event.key in (pygame.K_UP, pygame.K_w) else 1)) % len(self.rows)
                self.game.ui.sound('move')
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):return self.activate()
        return True

    def draw(self, canvas):
        if not self.is_open:return
        painter = self.game.ui.painter(canvas)
        elapsed = pygame.time.get_ticks()-self._opened_at
        progress = 1 if getattr(self.game.audio, 'reduced_motion', False) else min(1, .65+elapsed/430)
        painter.veil(190*progress)
        if self.overlay:return
        if self.settings:
            self.settings_panel.draw(painter)
            return
        panel = pygame.Rect(126, 24, 228, 282)
        painter.panel(panel)
        painter.lantern((panel.left+23, panel.top+25), size=10)
        painter.text('Paused', (240, 36), role='heading', color=GOLD, anchor='midtop', bold=True)
        for index, (label, row) in enumerate(zip(self.options, self.rows)):
            painter.button(row, label, selected=index == self.selected,
                           pressed=self._pressed == index and self._mouse_held)
        painter.text('Arrows + Enter • Esc: resume', (240, panel.bottom-9),
                     role='small', color=MUTED, anchor='midbottom')
