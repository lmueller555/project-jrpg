"""Current-section cave navigation built from the authored scene overview.

Only room landmarks and connecting passages receive markers. Treasure and
encounter metadata are deliberately absent from the map's navigation records.
"""
from __future__ import annotations

import pygame

from sanctuary_map import SanctuaryMapUI


class SanctuaryCaveMapUI(SanctuaryMapUI):
    def __init__(self, game):
        self.game = game
        self.data = None
        self.landmarks = []
        self.overview = None
        self.selected = 0
        self.hovered = None
        self.detail_scroll = self.detail_max_scroll = 0
        self.close_rect = pygame.Rect(432, 22, 28, 22)
        self.map_rect = pygame.Rect(26, 82, 270, 180)
        self.marker_rects = {}
        self._mouse_held = False
        self.ensure_scene()

    def ensure_scene(self):
        data = self.game.world.data
        if self.data is data:return
        self.data = data
        self.landmarks = [dict(record) for record in data.get('landmarks', [])]
        for link in data.get('cave', {}).get('links', []):
            destination = link['destination'].replace('sanctuary_cave_', '').replace('_', ' ').title()
            if link['destination'] == 'elden_vale_sanctuary':destination = 'Sanctuary grounds'
            self.landmarks.append({
                'id': 'passage:'+link['id'], 'name': link.get('label', 'To '+destination),
                'position': list(link['position']),
                'description': 'A passage leading to '+destination+'.', 'passage': True})
        self.overview = self.game.town.image(data['overview'], False)
        self.marker_rects.clear()
        self.reset()

    def player_position(self):
        return tuple(self.game.player.position)

    def draw(self, canvas):
        if not self.game.map_open:return
        self.ensure_scene()
        painter = self.game.ui.painter(canvas)
        painter.veil(190)
        painter.panel((12, 12, 456, 296), parchment=True)
        painter.text('Sanctuary Cave', (26, 24), role='heading', color='#344337', bold=True)
        painter.button(self.close_rect, '×')
        subtitle_y = 24+painter.font('heading', bold=True).get_linesize()+3
        subtitle = self.data.get('name', 'Crystal caverns')
        top = subtitle_y
        for line in painter.wrap(subtitle, 390, role='small'):
            painter.text(line, (26, top), role='small', color='#6d7054')
            top += painter.font('small').get_linesize()
        top = max(82, top+9)
        available = pygame.Rect(26, top, 270, max(80, 271-top))
        width, height = self.data['size_pixels']
        scale = min(available.width/width, available.height/height)
        self.map_rect = pygame.Rect(0, 0, round(width*scale), round(height*scale))
        self.map_rect.center = available.center
        painter.image(self.overview, self.map_rect)
        painter.rect('#a88c4b', self.map_rect, 1)
        self.marker_rects = {}
        for index, record in enumerate(self.landmarks):
            point = tuple(round(value) for value in self.world_to_map(record['position']))
            rect = pygame.Rect(0, 0, 14, 14);rect.center = point
            self.marker_rects[record['id']] = rect
            color = '#f5ce6d' if index == self.selected else '#f6efd7'
            if record.get('passage'):
                painter.rect('#344337', (point[0]-4, point[1]-4, 8, 8))
                painter.rect(color, (point[0]-3, point[1]-3, 6, 6), 1)
            else:
                center = painter.point(point)
                pygame.draw.circle(canvas, '#344337', center, max(2, round(4*painter.scale)))
                pygame.draw.circle(canvas, color, center, max(1, round(2.5*painter.scale)))
            if index in (self.selected, self.hovered):
                painter.rect('#f5ce6d', (rect.x, rect.y, rect.width, rect.height), 1)
        from map_ui import MapUI
        MapUI._player_symbol(painter, self.world_to_map(self.player_position()))
        MapUI._player_symbol(painter, (32, 289))
        painter.text('You', (43, 282), role='small', color='#344337')
        painter.rect('#344337', (103, 285, 8, 8), 1)
        painter.text('Passage', (118, 282), role='small', color='#344337')
        painter.line('#c4b184', (304, top), (304, 290), 1)
        self._draw_details(painter, top)
