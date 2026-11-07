"""Draft-and-confirm party formation with keyboard and mouse parity."""
from __future__ import annotations

from pathlib import Path

import pygame

from ui_style import (FOREST_DARK, FOREST_LIGHT, IVORY, GOLD, BRASS,
                      MUTED, DISABLED, ERROR)


ROOT = Path(__file__).resolve().parent


class PartyUI:
    """Edits a local formation; only Confirm writes through the game owner."""

    def __init__(self, game):
        self.game = game
        self.is_open = False
        self.panel = pygame.Rect(10, 10, 460, 300)
        self.slot_rects = [pygame.Rect(22, 74+i*54, 152, 50) for i in range(3)]
        self.roster_view = pygame.Rect(186, 74, 272, 158)
        self.roster_rects = {}
        self.confirm_rect = pygame.Rect(356, 278, 102, 24)
        self.cancel_rect = pygame.Rect(246, 278, 102, 24)
        self.clear_rect = pygame.Rect(22, 278, 102, 24)
        self.detail_view = pygame.Rect(22, 237, 428, 38)
        self.detail_up = pygame.Rect(450, 237, 12, 19)
        self.detail_down = pygame.Rect(450, 256, 12, 19)
        self.detail_scroll = self.detail_max_scroll = 0
        self._detail = ''
        self.row_height = 70
        self._layout_signature = None
        self.scroll = self.max_scroll = 0
        self.selected_slot = 1
        self.selected_member = 0
        self.selected_button = 2
        self.focus = 'slots'
        self.draft = []
        self.message = ''
        self.prompt = None
        self._held = False
        self._portraits = {}
        self._on_confirm = self._on_cancel = None

    @property
    def party(self):return self.game.party

    @property
    def roster(self):return tuple(self.party.members)

    @property
    def formation(self):return tuple(identifier for identifier in self.draft if identifier is not None)

    def _sound(self, name):self.game.ui.sound(name)

    def open(self, prompt=None, on_confirm=None, on_cancel=None):
        self.is_open = True
        self.prompt = prompt
        self.draft = list(self.party.active_ids)+[None]*(3-len(self.party.active_ids))
        self.selected_slot = min(2, len(self.party.active_ids))
        self.selected_member = self.selected_button = 0
        self.focus = 'slots'
        self.scroll = 0
        self._layout_signature = None
        self.message = ''
        self.detail_scroll = 0
        self._detail = ''
        self._held = False
        self._on_confirm, self._on_cancel = on_confirm, on_cancel
        self.game._mouse_held = False
        self._sound('confirm')

    def open_selection(self, title, on_confirm=None, on_cancel=None):
        self.open(prompt=title, on_confirm=on_confirm, on_cancel=on_cancel)

    def reset(self):
        self.is_open = False
        self.draft = []
        self.message = ''
        self._held = False
        self._on_confirm = self._on_cancel = None

    def close(self):
        callback = self._on_cancel
        self.reset()
        self.game._mouse_held = False
        self._sound('back')
        if callback is not None:callback()

    def _blocked(self):
        reason = self.party.selection_change_reason()
        if reason:
            self.message = reason
            self._sound('back')
        return bool(reason)

    def _name(self, identifier):return self.party.definitions[identifier]['name']

    def choose_member(self, identifier):
        """Put a companion in the chosen slot, swapping existing active slots."""
        if self._blocked():return False
        member = self.party.members.get(identifier)
        if member is None:return False
        if not member['available']:
            self.message = member.get('reason') or 'This companion is currently unavailable.'
            self._sound('back')
            return False
        old = self.draft[self.selected_slot]
        proposed = list(self.draft)
        if identifier in proposed:
            index = proposed.index(identifier)
            proposed[index] = old
        proposed[self.selected_slot] = identifier
        reason = self.party.selection_reason(tuple(value for value in proposed if value is not None))
        if reason:
            self.message = reason
            self._sound('back')
            return False
        self.draft = proposed
        self.message = ''
        self.focus = 'slots'
        self._sound('confirm')
        return True

    def clear_slot(self):
        if self._blocked():return False
        identifier = self.draft[self.selected_slot]
        if identifier in self.party.required_ids:
            self.message = self._name(identifier)+' is required for this part of the story.'
            self._sound('back')
            return False
        proposed = list(self.draft)
        proposed[self.selected_slot] = None
        reason = self.party.selection_reason(tuple(value for value in proposed if value is not None))
        if reason:
            self.message = reason
            return False
        self.draft = proposed
        self.message = ''
        self._sound('confirm')
        return True

    def confirm(self):
        if self._blocked():return False
        reason = self.party.selection_reason(self.formation)
        if reason:
            self.message = reason
            self._sound('back')
            return False
        if not self.game.set_active_party(self.formation):
            self.message = getattr(self.game, 'save_error', None) or 'The party could not be saved. Please retry.'
            self._sound('back')
            return False
        callback = self._on_confirm
        self.reset()
        self.game._mouse_held = False
        self._sound('confirm')
        if callback is not None:callback()
        return True

    def _point(self, point):
        if hasattr(self.game, 'to_canvas'):return self.game.to_canvas(point)
        width, height = self.game.window.get_size()
        scale = min(width/480, height/320)
        x, y = (point[0]-(width-480*scale)/2)/scale, (point[1]-(height-320*scale)/2)/scale
        return (x, y) if 0 <= x < 480 and 0 <= y < 320 else None

    def _layout(self, painter, *, ensure_visible=False):
        self.row_height = max(70, painter.font().get_linesize()+4*painter.font('small').get_linesize()+12)
        signature = (self.row_height, tuple(self.roster_view))
        # Resizing and text preferences can enlarge the selected row. Reveal it
        # once after that change, without undoing deliberate mouse scrolling.
        ensure_visible = ensure_visible or signature != self._layout_signature
        self._layout_signature = signature
        self.max_scroll = max(0, len(self.roster)*self.row_height-self.roster_view.height)
        self.scroll = max(0, min(self.scroll, self.max_scroll))
        if ensure_visible and self.roster:
            top = self.selected_member*self.row_height
            self.scroll = min(self.scroll, top)
            self.scroll = max(self.scroll, top+self.row_height-self.roster_view.height)
            self.scroll = max(0, min(self.scroll, self.max_scroll))
        self.roster_rects = {identifier:pygame.Rect(self.roster_view.left,
                            self.roster_view.top+i*self.row_height-self.scroll,
                            self.roster_view.width-9, self.row_height-4)
                             for i, identifier in enumerate(self.roster)}

    def _activate(self):
        if self.focus == 'slots':
            self.focus = 'roster'
            self._sound('move')
        elif self.focus == 'roster' and self.roster:
            self.choose_member(self.roster[self.selected_member])
        elif self.focus == 'buttons':
            (self.clear_slot, self.close, self.confirm)[self.selected_button]()

    def _detail_lines(self, painter):
        selected = self.roster[self.selected_member] if self.roster else None
        detail = self.message or self.party.selection_change_reason()
        if not detail and selected and not self.party.members[selected]['available']:
            detail = self._name(selected)+': '+self.party.members[selected].get('reason', 'Currently unavailable.')
        pending=self.party.pending_selection
        if not self.message and pending is not None and pending['lock_after']:
            warning='Confirm locks this party until the event ends.'
            detail=warning+(' '+detail if detail else '')
        if not detail:detail = 'Choose a slot, then a companion. Tab: controls · Del: clear · Esc: cancel'
        if detail != self._detail:self.detail_scroll = 0
        self._detail = detail
        lines = painter.wrap(detail, self.detail_view.width, role='small')
        line_height = painter.font('small').get_linesize()
        self.detail_max_scroll = max(0, len(lines)*line_height-self.detail_view.height)
        self.detail_scroll = max(0, min(self.detail_scroll, self.detail_max_scroll))
        return lines, line_height

    def handle_event(self, event):
        if not self.is_open:return False
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            return True
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:self.close()
            elif event.key == pygame.K_TAB:
                groups = ('slots', 'roster', 'buttons')
                direction = -1 if getattr(event, 'mod', 0) & pygame.KMOD_SHIFT else 1
                self.focus = groups[(groups.index(self.focus)+direction)%3]
                if self.focus == 'buttons':self.selected_button = 2
                self._sound('move')
            elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):self.clear_slot()
            elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END):
                self._detail_lines(self.game.ui.painter(self.game.ui_surface))
                if event.key == pygame.K_HOME:self.detail_scroll = 0
                elif event.key == pygame.K_END:self.detail_scroll = self.detail_max_scroll
                else:self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll+
                    (-1 if event.key == pygame.K_PAGEUP else 1)*self.detail_view.height))
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):self._activate()
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                direction = -1 if event.key in (pygame.K_UP, pygame.K_w) else 1
                if self.focus == 'slots':self.selected_slot = (self.selected_slot+direction)%3
                elif self.focus == 'roster' and self.roster:
                    self.selected_member = (self.selected_member+direction)%len(self.roster)
                    self._layout(self.game.ui.painter(self.game.ui_surface), ensure_visible=True)
                self.message = ''
                self._sound('move')
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                direction = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
                if self.focus == 'buttons':self.selected_button = (self.selected_button+direction)%3
                else:self.focus = 'slots' if direction < 0 else 'roster'
                self._sound('move')
            return True
        if event.type == pygame.MOUSEWHEEL:
            point = self._point(getattr(event, 'pos', pygame.mouse.get_pos()))
            if point is not None and self.detail_view.collidepoint(point):
                self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll-event.y*19))
            else:self.scroll = max(0, min(self.max_scroll, self.scroll-event.y*self.row_height))
            return True
        point = self._point(event.pos) if hasattr(event, 'pos') else None
        if point is None:return True
        if event.type == pygame.MOUSEMOTION and self.roster_view.collidepoint(point):
            identifier = next((key for key, rect in self.roster_rects.items() if rect.collidepoint(point)), None)
            if identifier is not None:
                self.selected_member = self.roster.index(identifier)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self._held:
            self._held = True
            if self.detail_max_scroll:
                for rect, direction in ((self.detail_up, -1), (self.detail_down, 1)):
                    if rect.collidepoint(point):
                        self.detail_scroll = max(0, min(self.detail_max_scroll,
                            self.detail_scroll+direction*self.detail_view.height))
                        return True
            for index, rect in enumerate(self.slot_rects):
                if rect.collidepoint(point):
                    self.selected_slot, self.focus, self.message = index, 'slots', ''
                    self._sound('move')
                    return True
            for index, rect in enumerate((self.clear_rect, self.cancel_rect, self.confirm_rect)):
                if rect.collidepoint(point):
                    self.selected_button, self.focus = index, 'buttons'
                    self._activate()
                    return True
            if self.roster_view.collidepoint(point):
                identifier = next((key for key, rect in self.roster_rects.items() if rect.collidepoint(point)), None)
                if identifier is not None:
                    self.selected_member = self.roster.index(identifier)
                    self.choose_member(identifier)
        return True

    def _portrait(self, identifier):
        if identifier not in self._portraits:
            filename = self.party.definitions[identifier].get('portrait')
            try:self._portraits[identifier] = pygame.image.load(str(ROOT/filename)).convert_alpha() if filename else None
            except (OSError, pygame.error):self._portraits[identifier] = None
        return self._portraits[identifier]

    def _status(self, identifier):
        member = self.party.members[identifier]
        if not member['available']:return 'Unavailable', DISABLED
        if identifier in self.party.required_ids:return 'Required', GOLD
        if identifier in self.draft:return 'Active', IVORY
        return 'Reserve', MUTED

    def draw(self, canvas):
        if not self.is_open:return
        painter = self.game.ui.painter(canvas)
        self._layout(painter)
        painter.veil(195)
        painter.panel(self.panel)
        title = self.prompt or 'Party'
        title_lines = painter.wrap(title, 424, role='heading', bold=True)
        painter.text(title_lines[0], (22, 17), role='heading', color=GOLD, bold=True)
        painter.text('Active '+str(len(self.formation))+' / 3', (22, 53), role='small', bold=True)
        painter.text('Recruited companions', (186, 53), role='small', bold=True)
        for index, rect in enumerate(self.slot_rects):
            selected = self.selected_slot == index
            painter.rect(FOREST_LIGHT if selected else FOREST_DARK, rect)
            painter.rect(GOLD if selected and self.focus == 'slots' else BRASS, rect, 1)
            identifier = self.draft[index]
            if identifier is None:
                painter.text(str(index+1)+'  Empty', rect.center, color=MUTED, anchor='center')
                continue
            attributes = self.party.characters[identifier]
            portrait = self._portrait(identifier)
            if portrait is not None:painter.image(portrait, (rect.left+5, rect.top+4, 26, 26))
            painter.text(self._name(identifier), (rect.left+36, rect.top+5), bold=True)
            painter.text('HP '+str(attributes.current_hp)+'  MP '+str(attributes.current_mp),
                         (rect.left+6, rect.top+29), role='small', color=MUTED)
            if identifier in self.party.required_ids:
                painter.rect(GOLD, (rect.right-5, rect.top+4, 2, 8))
        painter.clip(self.roster_view)
        for index, identifier in enumerate(self.roster):
            rect = self.roster_rects[identifier]
            if not self.roster_view.colliderect(rect):continue
            selected = index == self.selected_member
            painter.rect(FOREST_LIGHT if selected else FOREST_DARK, rect)
            painter.rect(GOLD if selected and self.focus == 'roster' else BRASS, rect, 1)
            portrait = self._portrait(identifier)
            if portrait is not None:painter.image(portrait, (rect.left+6, rect.top+9, 40, 40))
            x, y = rect.left+54, rect.top+5
            definition, attributes = self.party.definitions[identifier], self.party.characters[identifier]
            painter.text(definition['name'], (x, y), bold=True)
            y += painter.font().get_linesize()
            painter.text(definition['job'], (x, y), role='small', color=MUTED)
            y += painter.font('small').get_linesize()
            resources = 'HP '+str(attributes.current_hp)+'/'+str(attributes.value('hp'))+'   MP '+str(attributes.current_mp)+'/'+str(attributes.value('mp'))
            for line in painter.wrap(resources, rect.right-x-5, role='small'):
                painter.text(line, (x, y), role='small')
                y += painter.font('small').get_linesize()
            status, color = self._status(identifier)
            if self.party.members[identifier].get('temporary'):status += ' · Guest'
            painter.text(status, (x, y), role='small', color=color)
        painter.clip()
        if self.max_scroll:
            track = pygame.Rect(self.roster_view.right-5, self.roster_view.top, 4, self.roster_view.height)
            height = max(14, round(track.height*self.roster_view.height/(len(self.roster)*self.row_height)))
            offset = round((track.height-height)*self.scroll/self.max_scroll)
            painter.rect(FOREST_DARK, track)
            painter.rect(BRASS, (track.x, track.y+offset, track.width, height))
        lines, line_height = self._detail_lines(painter)
        painter.clip(self.detail_view)
        for index, line in enumerate(lines):
            painter.text(line, (self.detail_view.x, self.detail_view.y+index*line_height-self.detail_scroll),
                         role='small', color=ERROR if self.message else MUTED)
        painter.clip()
        if self.detail_max_scroll:
            # Mouse arrows/wheel and Page Up/Down expose long story reasons.
            painter.text('↑', self.detail_up.center, role='small', color=GOLD, anchor='center')
            painter.text('↓', self.detail_down.center, role='small', color=GOLD, anchor='center')
        for index, (rect, label) in enumerate(((self.clear_rect, 'Clear slot'), (self.cancel_rect, 'Cancel'),
                                             (self.confirm_rect, 'Confirm'))):
            painter.button(rect, label, selected=self.focus == 'buttons' and self.selected_button == index)
