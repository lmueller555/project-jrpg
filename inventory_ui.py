"""A four-category, readable satchel with independent list/detail scrolling."""
import pygame

from inventory import CATEGORIES, CATEGORY_NAMES
from ui_style import FOREST, FOREST_LIGHT, IVORY, GOLD, INK, BRASS, PARCHMENT_DARK


class InventoryUI:
    def __init__(self, game):
        self.game = game
        self.is_open = False
        self.category_index = 3
        self.selected = None
        self.list_scroll = self.detail_scroll = 0
        self.list_max_scroll = self.detail_max_scroll = 0
        self._held = False
        self.hovered = None
        self.dragging = None
        self.drag_offset = 0
        self.close_rect = pygame.Rect(438, 20, 22, 22)
        self.tabs = [pygame.Rect(24+i*108, 53, 106, 28) for i in range(4)]
        self.list_view = pygame.Rect(24, 96, 184, 181)
        self.detail_view = pygame.Rect(234, 96, 202, 181)
        self.item_rects = {}
        self.tracks = {'list': pygame.Rect(211, 96, 6, 181),
                       'details': pygame.Rect(443, 96, 6, 181)}
        self.thumbs = {}

    @property
    def category(self):return CATEGORIES[self.category_index]

    def open(self):
        self.is_open = True
        self._held = False
        self.dragging = None
        self.game.ui.sound('confirm')

    def close(self):
        self.is_open = False
        self._held = False
        self.dragging = None
        self.game.ui.sound('back')

    def reset(self):
        self.is_open = False
        self.category_index = 3
        self.selected = None
        self.list_scroll = self.detail_scroll = 0
        self._held = False
        self.dragging = None

    def _painter(self, canvas=None):
        return self.game.ui.painter(canvas if canvas is not None else self.game.ui_surface)

    def _select(self, identifier):
        if identifier != self.selected:
            self.selected = identifier
            self.detail_scroll = 0
            self.game.ui.sound('move')

    def _category(self, index):
        if index == self.category_index:return
        self.category_index = index % 4
        self.selected = None
        self.list_scroll = self.detail_scroll = 0
        self.game.ui.sound('move')

    def _details(self, painter, item):
        rows = []
        def add(text, role='body', color=INK, bold=False):
            for line in painter.wrap(text, self.detail_view.width, role=role, bold=bold):
                rows.append((line, role, color, bold))
        add(CATEGORY_NAMES[self.category_index], 'small', FOREST, True)
        add(item['name'], 'name', FOREST, True)
        add('Quantity: '+str(item['quantity']))
        add('')
        add(item['description'])
        if item.get('recipient_name'):
            add('')
            add('For '+item['recipient_name'], color=FOREST, bold=True)
        if item['category'] == 'key_items':
            add('')
            add('Quest item — kept safe until its handoff.', 'small', FOREST)
        if item.get('equipment_slot'):
            add('')
            add('Slot: '+item['equipment_slot'].replace('_', ' ').title())
        for stat, value in item.get('stats', {}).items():
            add(stat.replace('_', ' ').title()+': '+str(value))
        return rows

    def _layout(self, painter):
        entries = self.game.inventory.entries(self.category)
        if self.selected not in {item['id'] for item in entries}:
            self.selected = entries[0]['id'] if entries else None
            if self.category == 'key_items':
                carried={item['id'] for item in entries}
                for delivery in self.game.inventory.deliveries.values():
                    if self.game.quests.objective_status(delivery['quest'],delivery['objective'])=='active':
                        candidate=next((item for item in delivery['items'] if item in carried),None)
                        if candidate is not None:
                            self.selected=candidate
                            break
            self.detail_scroll = 0
        content = []
        y = 0
        line_height = painter.font().get_linesize()+2
        for item in entries:
            quantity_width=max(51,painter.font().size('×'+str(item['quantity']))[0]+16)
            lines = painter.wrap(item['name'], self.list_view.width-quantity_width)
            height = max(34, len(lines)*line_height+12)
            content.append((item, lines, pygame.Rect(self.list_view.x, y, self.list_view.width, height)))
            y += height+4
        self.list_max_scroll = max(0, y-4-self.list_view.height)
        self.list_scroll = max(0, min(self.list_scroll, self.list_max_scroll))
        self.item_rects = {}
        for item, lines, rect in content:
            displayed = rect.move(0, self.list_view.y-self.list_scroll)
            if displayed.colliderect(self.list_view):self.item_rects[item['id']] = displayed.clip(self.list_view)
        item = next((item for item in entries if item['id'] == self.selected), None)
        details = self._details(painter, item) if item else []
        self.detail_max_scroll = max(0, sum(painter.font(role, bold).get_linesize()+4
                                          for _, role, _, bold in details)-self.detail_view.height)
        self.detail_scroll = max(0, min(self.detail_scroll, self.detail_max_scroll))
        self.thumbs = {}
        for name, maximum, scroll in (('list', self.list_max_scroll, self.list_scroll),
                                       ('details', self.detail_max_scroll, self.detail_scroll)):
            if not maximum:continue
            track = self.tracks[name]
            height = max(15, round(track.height*track.height/(maximum+track.height)))
            offset = round((track.height-height)*scroll/maximum)
            self.thumbs[name] = pygame.Rect(track.x, track.y+offset, track.width, height)
        if self.dragging not in self.thumbs:self.dragging = None
        return entries, content, details

    def handle_event(self, event):
        if not self.is_open:return False
        painter = self._painter()
        entries, content, _ = self._layout(painter)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_i, pygame.K_ESCAPE) and not getattr(event, 'repeat', False):self.close()
            elif event.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
                direction = -1 if event.key == pygame.K_LEFT or (event.key == pygame.K_TAB and getattr(event, 'mod', 0)&pygame.KMOD_SHIFT) else 1
                self._category(self.category_index+direction)
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s) and entries:
                index = next(i for i, item in enumerate(entries) if item['id'] == self.selected)
                index = (index+(-1 if event.key in (pygame.K_UP, pygame.K_w) else 1)) % len(entries)
                self._select(entries[index]['id'])
                rect = content[index][2]
                self.list_scroll = max(min(self.list_scroll, rect.y), rect.bottom-self.list_view.height)
            elif event.key == pygame.K_PAGEUP:self.detail_scroll = max(0, self.detail_scroll-100)
            elif event.key == pygame.K_PAGEDOWN:self.detail_scroll = min(self.detail_max_scroll, self.detail_scroll+100)
            elif event.key == pygame.K_HOME:self.detail_scroll = 0
            elif event.key == pygame.K_END:self.detail_scroll = self.detail_max_scroll
            return True
        if event.type == pygame.MOUSEWHEEL:
            point = self.game.to_canvas(pygame.mouse.get_pos())
            if point is not None and self.list_view.collidepoint(point):
                self.list_scroll = max(0, min(self.list_max_scroll, self.list_scroll-event.y*30))
            else:self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll-event.y*30))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            self.dragging = None
        elif event.type == pygame.MOUSEMOTION:
            point = self.game.to_canvas(event.pos)
            self.hovered = next((key for key, rect in self.item_rects.items()
                                 if point is not None and rect.collidepoint(point)), None)
            if self.dragging is not None and point is not None:
                name = self.dragging
                track, thumb = self.tracks[name], self.thumbs[name]
                maximum = self.list_max_scroll if name == 'list' else self.detail_max_scroll
                value = round(max(0, min(1, (point[1]-track.top-self.drag_offset)/max(1, track.height-thumb.height)))*maximum)
                if name == 'list':self.list_scroll = value
                else:self.detail_scroll = value
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            point = self.game.to_canvas(event.pos)
            if point is None:return True
            if self.close_rect.collidepoint(point):self.close()
            else:
                for index, rect in enumerate(self.tabs):
                    if rect.collidepoint(point):self._category(index);return True
                for name, thumb in self.thumbs.items():
                    if self.tracks[name].collidepoint(point):
                        self.dragging = name
                        self.drag_offset = point[1]-thumb.top if thumb.collidepoint(point) else thumb.height/2
                        return True
                for identifier, rect in self.item_rects.items():
                    if rect.collidepoint(point):self._select(identifier);break
        return event.type in (pygame.MOUSEWHEEL, pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.KEYUP)

    def draw(self, canvas):
        if not self.is_open:return
        painter = self._painter(canvas)
        entries, content, details = self._layout(painter)
        painter.veil(210)
        painter.panel((12, 12, 456, 296), parchment=True)
        painter.lantern((31, 31), color=FOREST, size=10)
        painter.text('Caelan’s satchel', (46, 20), role='name', color=FOREST, bold=True)
        painter.button(self.close_rect, '×')
        for index, (label, rect) in enumerate(zip(CATEGORY_NAMES, self.tabs)):
            selected=index == self.category_index
            painter.rect(FOREST_LIGHT if selected else FOREST,rect)
            painter.rect(BRASS,rect,1)
            painter.text(label,rect.center,color=GOLD if selected else IVORY,anchor='center',bold=selected)
        painter.line(BRASS, (225, 96), (225, 277))
        painter.clip(self.list_view)
        for item, lines, rect in content:
            rect = rect.move(0, self.list_view.y-self.list_scroll)
            if not rect.colliderect(self.list_view):continue
            selected = item['id'] == self.selected
            painter.rect(FOREST if selected else PARCHMENT_DARK, rect)
            if self.hovered == item['id']:painter.rect(BRASS, rect, 1)
            for index, line in enumerate(lines):
                painter.text(line, (rect.x+7, rect.y+6+index*(painter.font().get_linesize()+2)), color=IVORY if selected else INK)
            painter.text('×'+str(item['quantity']), (rect.right-7, rect.y+6), color=GOLD if selected else FOREST, anchor='topright')
        if not entries:
            for index, line in enumerate(painter.wrap('No '+CATEGORY_NAMES[self.category_index].lower()+' carried.', self.list_view.width-12)):
                painter.text(line, (self.list_view.x+6, self.list_view.y+8+index*painter.font().get_linesize()), color=INK)
        painter.clip(self.detail_view)
        y = self.detail_view.y-self.detail_scroll
        if not details:
            text = 'Quest supplies will appear here when entrusted to you.' if self.category == 'key_items' else 'Items you acquire will appear in your satchel.'
            for line in painter.wrap(text, self.detail_view.width):
                painter.text(line, (self.detail_view.x, y), color=INK)
                y += painter.font().get_linesize()+4
        for line, role, color, bold in details:
            painter.text(line, (self.detail_view.x, y), role=role, color=color, bold=bold)
            y += painter.font(role, bold).get_linesize()+4
        painter.clip()
        for name, thumb in self.thumbs.items():
            painter.rect(PARCHMENT_DARK, self.tracks[name])
            painter.rect(BRASS, thumb)
        hint = 'I / Esc: close • Tab: category • ↑ / ↓: select'
        for index, line in enumerate(painter.wrap(hint, 428, role='small')):
            painter.text(line, (26, 285+index*painter.font('small').get_linesize()), role='small', color=INK)
