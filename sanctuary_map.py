"""A local reserve overview, shared with its hall without loading another scene."""
from __future__ import annotations

import json
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
MAP_FILE = ROOT/'assets/maps/elden_vale_sanctuary/map.json'
RESERVE_ID = 'elden_vale_sanctuary'


class SanctuaryMapUI:
    def __init__(self, game):
        self.game = game
        self.data = json.loads(MAP_FILE.read_text(encoding='utf-8'))
        self.landmarks = self.data['landmarks']
        self.overview = game.town.image(self.data['overview'], False)
        self.selected = 0
        self.hovered = None
        self.detail_scroll = self.detail_max_scroll = 0
        self.close_rect = pygame.Rect(432, 22, 28, 22)
        self.map_rect = pygame.Rect(26, 82, 270, 180)
        self.marker_rects = {}
        self._mouse_held = False
        self.reset()

    @property
    def selected_landmark(self):
        return self.landmarks[self.selected] if self.landmarks else None

    def player_position(self):
        if self.game.world.data.get('id') == RESERVE_ID:
            return tuple(self.game.player.position)
        # The hall shares this reserve map. Its own indoor coordinates have
        # no relationship to the exterior's geography or Eldenmere's entrance.
        return tuple(self.game.world.data.get('exterior_map_position',
                     self.data.get('hall_approach', (535, 345))))

    def world_to_map(self, point):
        width, height = self.data['size_pixels']
        return (self.map_rect.x+point[0]*self.map_rect.width/width,
                self.map_rect.y+point[1]*self.map_rect.height/height)

    def reset(self):
        self._mouse_held = False
        self.hovered = None
        self.detail_scroll = 0
        if self.landmarks:
            player = pygame.Vector2(self.player_position())
            self.selected = min(range(len(self.landmarks)), key=lambda i:
                                player.distance_squared_to(self.landmarks[i]['position']))

    def select_landmark(self, identifier):
        for index, record in enumerate(self.landmarks):
            if record['id'] == identifier:
                self.selected = index
                self.detail_scroll = 0
                return True
        return False

    def _sound(self, kind):
        self.game.ui.sound(kind)

    def _at(self, point):
        if point is None:return None
        return next((i for i, record in enumerate(self.landmarks)
                     if self.marker_rects.get(record['id'], pygame.Rect(0, 0, 0, 0)).collidepoint(point)), None)

    def handle_event(self, event):
        if not self.game.map_open:return False
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key in (pygame.K_m, pygame.K_ESCAPE):
                self.game.map_open = False
                self._sound('back')
            elif self.landmarks and event.key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a,
                                                   pygame.K_DOWN, pygame.K_RIGHT, pygame.K_s, pygame.K_d):
                step = -1 if event.key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a) else 1
                self.selected = (self.selected+step) % len(self.landmarks)
                self.detail_scroll = 0
                self._sound('move')
            elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                self.detail_scroll = max(0, min(self.detail_max_scroll,
                    self.detail_scroll+(-80 if event.key == pygame.K_PAGEUP else 80)))
            elif event.key == pygame.K_HOME:self.detail_scroll = 0
            elif event.key == pygame.K_END:self.detail_scroll = self.detail_max_scroll
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll-event.y*24))
        elif event.type == pygame.MOUSEMOTION:
            self.hovered = self._at(self.game.to_canvas(event.pos))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_held = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._mouse_held:return True
            self._mouse_held = True
            point = self.game.to_canvas(event.pos)
            if point is not None and self.close_rect.collidepoint(point):
                self.game.map_open = False
                self._sound('back')
            else:
                index = self._at(point)
                if index is not None:
                    self.selected = index
                    self.detail_scroll = 0
                    self._sound('confirm')
        return event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN,
                              pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL,
                              pygame.KEYDOWN, pygame.KEYUP)

    def draw(self, canvas):
        if not self.game.map_open:return
        painter = self.game.ui.painter(canvas)
        painter.veil(190)
        painter.panel((12, 12, 456, 296), parchment=True)
        painter.text('Elden Vale Sanctuary', (26, 24), role='heading', color='#344337', bold=True)
        painter.button(self.close_rect, '×')
        top = max(67, 24+painter.font('heading', bold=True).get_linesize()+12)
        available = pygame.Rect(26, top, 270, 275-top)
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
            center = painter.point(point)
            pygame.draw.circle(canvas, '#344337', center, max(2, round(4*painter.scale)))
            pygame.draw.circle(canvas, color, center, max(1, round(2.5*painter.scale)))
            if index in (self.selected, self.hovered):
                pygame.draw.circle(canvas, color, center, max(3, round(6*painter.scale)),
                                   max(1, round(painter.scale)))
        from map_ui import MapUI
        MapUI._player_symbol(painter, self.world_to_map(self.player_position()))
        MapUI._player_symbol(painter, (32, 289))
        inside = self.game.world.data.get('id') != RESERVE_ID
        painter.text('You are here · Inside the hall' if inside else 'You are here',
                     (43, 282), role='small', color='#344337')
        painter.line('#c4b184', (304, top), (304, 290), 1)
        self._draw_details(painter, top)

    def _draw_details(self, painter, top):
        record = self.selected_landmark
        if record is None:return
        clip = pygame.Rect(318, top, 132, 290-top)
        names = painter.wrap(record['name'], clip.width, role='name', bold=True)
        lines = painter.wrap(record.get('description', 'A place within the sanctuary reserve.'),
                             clip.width, role='body')
        name_height = painter.font('name', bold=True).get_linesize()
        body_height = painter.font('body').get_linesize()
        content_height = len(names)*name_height+10+len(lines)*body_height
        self.detail_max_scroll = max(0, content_height-clip.height)
        self.detail_scroll = max(0, min(self.detail_scroll, self.detail_max_scroll))
        y = clip.top-self.detail_scroll
        painter.clip(clip)
        for line in names:
            painter.text(line, (clip.left, y), role='name', color='#344337', bold=True)
            y += name_height
        y += 10
        for line in lines:
            painter.text(line, (clip.left, y), role='body', color='#6d7054')
            y += body_height
        painter.clip(None)
        if self.detail_max_scroll:
            painter.rect('#c6b588', (454, clip.top, 2, clip.height))
            thumb = max(10, clip.height*clip.height/(clip.height+self.detail_max_scroll))
            offset = (clip.height-thumb)*self.detail_scroll/self.detail_max_scroll
            painter.rect('#a88c4b', (454, clip.top+offset, 2, thumb))
