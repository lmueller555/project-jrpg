"""Read-only character attributes with keyboard and mouse inspection."""
from pathlib import Path

import pygame

from character_attributes import ATTRIBUTE_IDS
from attribute_icons import draw_attribute_icon
from ui_style import FOREST, IVORY, GOLD, INK, BRASS, PARCHMENT_DARK


ROOT = Path(__file__).resolve().parent


class StatusUI:
    def __init__(self, game):
        self.game = game
        self.is_open = False
        self.selected = 'hp'
        self.detail_scroll = 0
        self.detail_max_scroll = 0
        self._held = False
        self.hovered = None
        self.keyboard_tooltip = False
        self.close_rect = pygame.Rect(438, 18, 22, 22)
        self.stat_rects = {'hp': pygame.Rect(244, 23, 92, 57),
                           'mp': pygame.Rect(344, 23, 92, 57)}
        for index, identifier in enumerate(ATTRIBUTE_IDS[2:]):
            self.stat_rects[identifier] = pygame.Rect(26+(index % 3)*144,
                                                     106+(index//3)*39, 132, 32)
        self.detail_view = pygame.Rect(27, 233, 412, 40)
        self.tooltip_bounds = pygame.Rect(20, 48, 440, 226)
        self.icon_rects = {}
        self.detail_track = pygame.Rect(445, 233, 5, 40)
        self.detail_thumb = None
        self.dragging = False
        self.drag_offset = 0
        self.portrait = pygame.image.load(str(ROOT/'assets/portraits/eldenmere/caelan_neutral.png'))

    def _painter(self, canvas=None):
        return self.game.ui.painter(canvas if canvas is not None else self.game.ui_surface)

    def open(self):
        self.is_open = True
        self.hovered = None
        self.keyboard_tooltip = False
        self._held = False
        self.dragging = False
        self.game.ui.sound('confirm')

    def close(self):
        self.is_open = False
        self.hovered = None
        self.keyboard_tooltip = False
        self._held = False
        self.dragging = False
        self.game.ui.sound('back')

    def reset(self):
        self.is_open = False
        self.selected = 'hp'
        self.detail_scroll = 0
        self._held = False
        self.hovered = None
        self.keyboard_tooltip = False
        self.dragging = False

    def _select(self, identifier):
        if identifier == self.selected:return
        self.selected = identifier
        self.detail_scroll = 0
        self.game.ui.sound('move')

    def _layout(self, painter):
        definition = self.game.attributes.definitions[self.hovered or self.selected]
        lines = painter.wrap(definition['name']+': '+definition['description'], self.detail_view.width)
        line_height = painter.font().get_linesize()+3
        self.detail_max_scroll = max(0, len(lines)*line_height-self.detail_view.height)
        self.detail_scroll = max(0, min(self.detail_scroll, self.detail_max_scroll))
        self.detail_thumb = None
        if self.detail_max_scroll:
            height = max(14, round(self.detail_track.height*self.detail_view.height/
                                   (self.detail_max_scroll+self.detail_view.height)))
            offset = round((self.detail_track.height-height)*self.detail_scroll/self.detail_max_scroll)
            self.detail_thumb = pygame.Rect(self.detail_track.left, self.detail_track.top+offset,
                                           self.detail_track.width, height)
        else:self.dragging = False
        return lines, line_height

    def tooltip_layout(self, painter=None):
        """Return a fully wrapped, viewport-bounded hover/focus explanation."""
        identifier = self.hovered or (self.selected if self.keyboard_tooltip else None)
        if not self.is_open or identifier is None:return None
        painter = painter or self._painter()
        definition = self.game.attributes.definitions[identifier]
        width = min(414, self.tooltip_bounds.width)
        lines = painter.wrap(definition['description'], width-24)
        title = definition['label']+' — '+definition['name']
        title_lines = painter.wrap(title, width-24, bold=True)
        line_height = painter.font().get_linesize()+1
        title_height = painter.font(bold=True).get_linesize()+1
        height = 24+len(title_lines)*title_height+len(lines)*line_height
        anchor = self.stat_rects[identifier]
        candidates = [pygame.Rect(anchor.left, anchor.bottom+5, width, height),
                      pygame.Rect(anchor.left, anchor.top-height-5, width, height)]
        candidates = [rect.clamp(self.tooltip_bounds) for rect in candidates]
        rect = min(candidates, key=lambda candidate: candidate.clip(anchor.inflate(0, 6)).width*
                   candidate.clip(anchor.inflate(0, 6)).height)
        return {'attribute': identifier, 'rect': rect, 'title': title,
                'title_lines': title_lines, 'lines': lines,
                'line_height': line_height, 'title_height': title_height}

    def _scroll(self, amount):
        self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll+amount))

    def handle_event(self, event):
        if not self.is_open:return False
        self._layout(self._painter())
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and not getattr(event, 'repeat', False):self.close()
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a,
                               pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                backward = event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a) or (
                    event.key == pygame.K_TAB and getattr(event, 'mod', 0)&pygame.KMOD_SHIFT)
                index = (ATTRIBUTE_IDS.index(self.selected)+(-1 if backward else 1)) % len(ATTRIBUTE_IDS)
                self.hovered = None
                self.keyboard_tooltip = True
                self._select(ATTRIBUTE_IDS[index])
            elif event.key == pygame.K_PAGEUP:self._scroll(-self.detail_view.height)
            elif event.key == pygame.K_PAGEDOWN:self._scroll(self.detail_view.height)
            elif event.key == pygame.K_HOME:self.detail_scroll = 0
            elif event.key == pygame.K_END:self.detail_scroll = self.detail_max_scroll
        elif event.type == pygame.MOUSEWHEEL:self._scroll(-event.y*24)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            previous = self.hovered
            self.hovered = next((identifier for identifier, rect in self.stat_rects.items()
                                 if point is not None and rect.collidepoint(point)), None)
            self.keyboard_tooltip = False
            if previous != self.hovered:self.detail_scroll = 0
            if self.dragging and point is not None and self.detail_thumb is not None:
                travel = self.detail_track.height-self.detail_thumb.height
                fraction = (point[1]-self.detail_track.top-self.drag_offset)/max(1, travel)
                self.detail_scroll = round(max(0, min(1, fraction))*self.detail_max_scroll)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if point is None:return True
            if self.close_rect.collidepoint(point):self.close()
            elif self.detail_thumb is not None and self.detail_track.inflate(8, 0).collidepoint(point):
                self.dragging = True
                self.drag_offset = point[1]-self.detail_thumb.top if self.detail_thumb.collidepoint(point) else self.detail_thumb.height/2
            else:
                for identifier, rect in self.stat_rects.items():
                    if rect.collidepoint(point):self._select(identifier);break
        elif event.type in (pygame.WINDOWLEAVE, pygame.WINDOWFOCUSLOST):
            self.hovered = None
            self.keyboard_tooltip = False
        return event.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEWHEEL,
                              pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)

    def draw(self, canvas):
        if not self.is_open:return
        painter = self._painter(canvas)
        lines, line_height = self._layout(painter)
        attributes = self.game.attributes
        painter.veil(210)
        painter.panel((12, 12, 456, 296), parchment=True)
        painter.image(self.portrait, (26, 36, 50, 50))
        painter.rect(BRASS, (26, 36, 50, 50), 1)
        painter.text('Characters', (26, 15), role='small', color=INK)
        painter.text(attributes.name, (88, 24), role='heading', color=FOREST, bold=True)
        lattice = getattr(self.game, 'lattice', None)
        if lattice is not None:
            progress, needed = lattice.rp_progress(attributes.character_id)
            painter.text('Attunement '+str(lattice.rank(attributes.character_id)),
                         (88, 60), role='small', color=INK)
            painter.text('RP '+str(progress)+' / '+str(needed), (88, 79), role='small', color=FOREST)
        painter.button(self.close_rect, '×')
        for identifier, rect in self.stat_rects.items():
            selected = identifier == self.selected
            painter.rect(FOREST if selected else PARCHMENT_DARK, rect)
            if selected or self.hovered == identifier:painter.rect(BRASS, rect, 1)
            color = IVORY if selected else INK
            label = attributes.definitions[identifier]['label']
            if identifier in ('hp', 'mp'):
                current = attributes.current_hp if identifier == 'hp' else attributes.current_mp
                label_width = painter.font(bold=True).size(label)[0]
                icon = pygame.Rect(rect.centerx-(17+label_width)//2, rect.top+8, 12, 12)
                self.icon_rects[identifier] = icon
                draw_attribute_icon(painter, identifier, icon, color)
                painter.text(label, (icon.right+5, icon.centery), color=color, anchor='midleft', bold=True)
                painter.text(str(current)+' / '+str(attributes.value(identifier)),
                             (rect.centerx, rect.bottom-6), color=GOLD if selected else FOREST,
                             anchor='midbottom', role='small')
            else:
                icon = pygame.Rect(rect.left+8, rect.centery-6, 12, 12)
                self.icon_rects[identifier] = icon
                draw_attribute_icon(painter, identifier, icon, color)
                painter.text(label, (icon.right+6, rect.centery), color=color, anchor='midleft', bold=selected)
                painter.text(str(attributes.value(identifier)), (rect.right-9, rect.centery),
                             color=GOLD if selected else FOREST, anchor='midright', bold=True)
        painter.line(BRASS, (26, 223), (450, 223))
        painter.clip(self.detail_view)
        for index, line in enumerate(lines):
            painter.text(line, (self.detail_view.x, self.detail_view.y+index*line_height-self.detail_scroll), color=INK)
        painter.clip()
        if self.detail_thumb is not None:
            painter.rect(PARCHMENT_DARK, self.detail_track)
            painter.rect(BRASS, self.detail_thumb)
        hint = 'Hover / arrows: details • Esc: back'
        hint_lines = painter.wrap(hint, 424, role='small')
        hint_height = painter.font('small').get_linesize()
        for index, line in enumerate(hint_lines):
            painter.text(line, (27, 280+index*hint_height), role='small', color=INK)
        tooltip = self.tooltip_layout(painter)
        if tooltip is not None:
            painter.panel(tooltip['rect'])
            x, y = tooltip['rect'].left+12, tooltip['rect'].top+10
            for line in tooltip['title_lines']:
                painter.text(line, (x, y), color=GOLD, bold=True)
                y += tooltip['title_height']
            y += 4
            for line in tooltip['lines']:
                painter.text(line, (x, y), color=IVORY)
                y += tooltip['line_height']
