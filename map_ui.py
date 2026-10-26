"""A readable parchment town map traced from Eldenmere's approved geography.

The map uses world metadata, never room instantiation or NPC simulation. Its
selection and input remain in native logical coordinates while the shared
painter draws text directly at the display's resolution.
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
PAPER = '#e8d8ad'
INK = '#344337'
SOFT_INK = '#6d7054'
BRASS = '#a88c4b'
PATH_EDGE = '#ad9768'
PATH_FILL = '#d3bb88'
WATER = '#789798'
WATER_EDGE = '#547679'
ROOF = '#8a7660'
WALL = '#d1bb91'

DESCRIPTIONS = {
    'sanctuary': 'Home, shared meals, and a quiet place to begin.',
    'mira': 'Mira works at the bench outside her workshop.',
    'mill': 'The waterwheel turns beside the brook.',
    'halden': 'Halden lives on the eastern terrace.',
    'elira': 'Elira’s cottage stands near the southern bridge.',
    'venn': 'The Venn family lives beside the growing plots.',
    'commons': 'The village well and a place to meet.',
    'liam_house': 'Liam, his parents, and Daisy live here.',
    'school': 'Eldenmere’s children learn together here.',
}


class MapUI:
    def __init__(self, game):
        self.game = game
        self.selected = 0
        self.hovered = None
        self.close_hovered = False
        self.close_rect = pygame.Rect(432, 22, 28, 22)
        self.map_rect = pygame.Rect(28, 66, 256, 224)
        self.detail_rect = pygame.Rect(306, 66, 146, 224)
        self.player_legend_rect = pygame.Rect(314, 232, 130, 50)
        self.building_rects = {}
        self._mouse_held = False
        self.detail_scroll = 0
        self.detail_max_scroll = 0
        self._plan = self._read_plan()
        self._extras = self._read_extras()
        self._footprints = self._collect_footprints()
        self._layout()
        self.reset()

    @property
    def landmarks(self):
        return self.game.town.data.get('landmarks', [])

    @property
    def selected_landmark(self):
        if not self.landmarks:return None
        self.selected = max(0, min(self.selected, len(self.landmarks)-1))
        return self.landmarks[self.selected]

    @staticmethod
    def _read_json(path):
        if not path:return {}
        source = Path(path)
        if not source.is_absolute():source = ROOT/source
        try:
            record = json.loads(source.read_text(encoding='utf-8'))
            return record if isinstance(record, dict) else {}
        except (OSError, ValueError):return {}

    def _read_plan(self):
        data = self.game.town.data
        plan = self._read_json(data.get('original_layout_source'))
        if not plan:
            plan = self._read_json(data.get('layout_source'))
        return plan

    def _read_extras(self):
        data = self.game.town.data
        paths = list(data.get('layout_additions', []))
        if data.get('layout_source'):paths.append(data['layout_source'])
        return [self._read_json(path) for path in paths]

    def _collect_footprints(self):
        tile = self.game.town.data.get('tile_size', self._plan.get('tile_size_px', 24))
        result = {item['id']: tuple(value*tile for value in item['rect'])
                  for item in self._plan.get('buildings', [])}
        for item in self._extras:
            if 'ground_rect' in item:
                result[item.get('id', '')] = tuple(item['ground_rect'])
            if 'well_ground_rect' in item:
                result['commons'] = tuple(item['well_ground_rect'])
        return result

    def world_to_map(self, position):
        width, height = self.game.town.size
        return (self.map_rect.x+position[0]*self.map_rect.width/width,
                self.map_rect.y+position[1]*self.map_rect.height/height)

    def _world_rect(self, record):
        x, y = self.world_to_map(record[:2])
        width, height = self.game.town.size
        return pygame.Rect(round(x), round(y),
                           max(2, round(record[2]*self.map_rect.width/width)),
                           max(2, round(record[3]*self.map_rect.height/height)))

    def _tile_rect(self, record):
        tile = self.game.town.data.get('tile_size', self._plan.get('tile_size_px', 24))
        return self._world_rect(tuple(value*tile for value in record))

    def _tile_point(self, record):
        tile = self.game.town.data.get('tile_size', self._plan.get('tile_size_px', 24))
        return self.world_to_map((record[0]*tile, record[1]*tile))

    def _layout(self):
        # The cartographic field and dedicated legend never share rows.
        self.building_rects = {}
        for landmark in self.landmarks:
            footprint = self._footprints.get(landmark['id'])
            if footprint is not None:
                rect = self._world_rect(footprint).inflate(8, 10)
            else:
                point = self.world_to_map(landmark['position'])
                rect = pygame.Rect(0, 0, 16, 16)
                rect.center = tuple(round(value) for value in point)
            self.building_rects[landmark['id']] = rect.clip(self.map_rect)

    def player_position(self):
        if self.game.world is self.game.town:
            return tuple(self.game.player.position)
        return tuple(self.game.exterior_position)

    def reset(self):
        self._mouse_held = False
        self.hovered = None
        self.close_hovered = False
        self.detail_scroll = 0
        if self.landmarks:
            player = pygame.Vector2(self.player_position())
            self.selected = min(range(len(self.landmarks)),
                                key=lambda index: player.distance_squared_to(self.landmarks[index]['position']))
        else:self.selected = 0

    def _sound(self, kind):
        style = getattr(self.game, 'ui', None)
        if style is not None and hasattr(style, 'sound'):style.sound(kind)

    def _point(self, position):
        convert = getattr(self.game, 'to_canvas', None)
        if convert is not None:return convert(position)
        return position

    def _at(self, point):
        if point is None:return None
        candidates = [(index, record) for index, record in enumerate(self.landmarks)
                      if self.building_rects[record['id']].collidepoint(point)]
        if not candidates:return None
        # Small footprints take precedence if a church roof overhangs a nearby
        # house on the compact illustrated map.
        return min(candidates, key=lambda pair: self.building_rects[pair[1]['id']].width*
                   self.building_rects[pair[1]['id']].height)[0]

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
            elif event.key == pygame.K_PAGEUP:
                self.detail_scroll = max(0, self.detail_scroll-80)
            elif event.key == pygame.K_PAGEDOWN:
                self.detail_scroll = min(self.detail_max_scroll, self.detail_scroll+80)
            elif event.key == pygame.K_HOME:self.detail_scroll = 0
            elif event.key == pygame.K_END:self.detail_scroll = self.detail_max_scroll
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._sound('confirm')
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll-event.y*24))
        elif event.type == pygame.MOUSEMOTION:
            point = self._point(event.pos)
            self.hovered = self._at(point)
            self.close_hovered = point is not None and self.close_rect.collidepoint(point)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_held = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._mouse_held:return True
            self._mouse_held = True
            point = self._point(event.pos)
            if point is not None and self.close_rect.collidepoint(point):
                self.game.map_open = False
                self._sound('back')
            else:
                index = self._at(point)
                if index is not None:
                    self.selected = index
                    self.detail_scroll = 0
                    self._sound('confirm')
        return event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                              pygame.MOUSEWHEEL, pygame.KEYDOWN, pygame.KEYUP)

    def _painter(self, canvas):
        style = getattr(self.game, 'ui', None)
        if style is None:
            from ui_style import UIStyle
            style = self.game.ui = UIStyle(self.game)
        return style.painter(canvas, logical_size=(480, 320))

    def _draw_land(self, painter):
        painter.rect(PAPER, self.map_rect)
        for record in self._plan.get('elevations', []):
            rect = self._tile_rect(record['rect']).clip(self.map_rect)
            color = '#ced0a6' if record.get('level', 1) >= 3 else '#dbd3ab'
            painter.rect(color, rect)
            if record.get('level', 1) == 2:
                painter.line('#b9b58d', (rect.left, rect.bottom-1), (rect.right, rect.bottom-1), 1)
        for record in self._plan.get('spaces', []):
            if record.get('kind') in ('garden', 'plots'):
                rect = self._tile_rect(record['rect'])
                painter.rect('#b9c19a', rect)
                for y in range(rect.top+2, rect.bottom, 3):
                    painter.line('#9ca87e', (rect.left+1, y), (rect.right-1, y), 1)

    def _draw_water(self, painter):
        tile = self.game.town.data.get('tile_size', self._plan.get('tile_size_px', 24))
        for start, end, center in self._plan.get('stream_centres', []):
            # Stream bands retain the approved stepped meander and its width.
            record = ((center-1.5)*tile, start*tile, 3*tile, (end-start+1)*tile)
            rect = self._world_rect(record)
            painter.rect(WATER_EDGE, rect)
            painter.rect(WATER, rect.inflate(-2, 0))
        for branch in self._plan.get('water_branches', []):
            points = [self._tile_point(point) for point in branch.get('points', [])]
            for a, b in zip(points, points[1:]):
                painter.line(WATER_EDGE, a, b, 3)
                painter.line(WATER, a, b, 1)

    def _draw_roads(self, painter):
        tile_width = self.map_rect.width/self.game.town.size[0]*self.game.town.data.get('tile_size', 24)
        for record in self._plan.get('roads', []):
            points = [self._tile_point(point) for point in record['points']]
            width = max(2, round(record.get('width', 2)*tile_width))
            for a, b in zip(points, points[1:]):
                painter.line(PATH_EDGE, a, b, width+1)
                painter.line(PATH_FILL, a, b, width-1)
        for item in self._extras:
            rects = list(item.get('path_rects_tiles', []))
            if 'path_rect_tiles' in item:rects.append(item['path_rect_tiles'])
            if 'plaza_rect_tiles' in item:rects.append(item['plaza_rect_tiles'])
            for record in rects:
                painter.rect(PATH_FILL, self._tile_rect(record))
        for record in self._plan.get('crossings', []):
            rect = self._tile_rect(record['rect'])
            painter.rect('#a68e67', rect)
            painter.rect('#755f45', rect, 1)
            if record.get('orientation') == 'east-west':
                for x in range(rect.left+2, rect.right, 3):
                    painter.line('#d9c49c', (x, rect.top+1), (x, rect.bottom-1), 1)

    def _draw_buildings(self, painter):
        selected = self.selected_landmark
        selected_id = selected['id'] if selected else None
        hovered_id = self.landmarks[self.hovered]['id'] if self.hovered is not None else None
        for identifier, record in self._footprints.items():
            if not identifier:continue
            rect = self._world_rect(record)
            if identifier == 'commons':
                painter.rect('#7b8070', rect)
                painter.rect('#d5d1b7', rect.inflate(-3, -3))
                painter.rect('#555f54', rect.inflate(-6, -6))
            else:
                wall = rect.move(0, 2)
                painter.rect('#907859', wall)
                painter.rect(WALL, wall.inflate(-2, -2))
                roof = pygame.Rect(rect.left-1, rect.top-2, rect.width+2, max(4, rect.height//2+2))
                painter.rect(ROOF, roof)
                painter.line('#c0a778', (roof.left+1, roof.top+1), (roof.right-1, roof.top+1), 1)
                painter.rect('#6c5943', (rect.centerx-1, rect.bottom-2, 3, 4))
            if identifier in (selected_id, hovered_id):
                painter.rect('#967135' if identifier == selected_id else '#b29a61', rect.inflate(7, 9), 1)
        # A sparse compass belongs to the map field, separate from the legend.
        painter.text('N', (self.map_rect.right-9, self.map_rect.top+7), role='small', color=INK, anchor='midtop')
        x, y = self.map_rect.right-9, self.map_rect.top+24
        painter.line(INK, (x, y+9), (x, y), 1)
        painter.line(INK, (x, y), (x-3, y+4), 1)
        painter.line(INK, (x, y), (x+3, y+4), 1)

    @staticmethod
    def _player_symbol(painter, point):
        x, y = point
        for a, b in (((x-4, y), (x, y-4)), ((x, y-4), (x+4, y)),
                     ((x+4, y), (x, y+4)), ((x, y+4), (x-4, y))):
            painter.line('#f8edcd', a, b, 3)
            painter.line(INK, a, b, 1)
        painter.rect(INK, (x-1, y-1, 2, 2))

    def draw(self, canvas):
        if not self.game.map_open:return
        painter = self._painter(canvas)
        self._layout()
        painter.veil(190)
        painter.panel((12, 12, 456, 296), parchment=True)
        painter.lantern((31, 31), color=BRASS, size=10)
        painter.text('Eldenmere', (47, 23), role='heading', color=INK, bold=True)
        subtitle_y = 23+painter.font('heading', bold=True).get_linesize()+2
        # The decorative subtitle yields its space at larger text sizes; the
        # town name, close control, geography and selected-place text remain.
        if subtitle_y+painter.font('small').get_linesize() <= self.map_rect.top-4:
            painter.text('Select a place · Arrows to browse', (28, subtitle_y), role='small', color=SOFT_INK)
        painter.button(self.close_rect, '×')
        if self.close_hovered:painter.rect('#e4c16e', self.close_rect, 2)
        painter.clip(self.map_rect)
        self._draw_land(painter)
        self._draw_water(painter)
        self._draw_roads(painter)
        self._draw_buildings(painter)
        player = self.world_to_map(self.player_position())
        quest_ui = getattr(self.game, 'quest_ui', None)
        if quest_ui is not None:
            quest_ui.draw_map_markers(canvas, self.map_rect.topleft, self.map_rect.size,
                                      avoid_point=player)
        self._player_symbol(painter, player)
        painter.clip(None)
        painter.rect(BRASS, self.map_rect, 1)
        painter.line('#c4b184', (299, 66), (299, 290), 1)
        self._draw_details(painter)

    def _draw_details(self, painter):
        record = self.selected_landmark
        painter.text('SELECTED PLACE', (314, 68), role='small', color=SOFT_INK, bold=True)
        detail_top = max(86, 68+painter.font('small', bold=True).get_linesize()+5)
        y = detail_top
        if record is None:
            name, description = 'Eldenmere', 'Explore the village to find your bearings.'
        else:
            name = record['name']
            description = DESCRIPTIONS.get(record['id'], 'A home in Eldenmere.')
            conclusion = getattr(self.game, 'opening_conclusion', None)
            if record['id']=='mill' and conclusion is not None and conclusion.mill_stopped:
                description = 'The mill wheel has stopped. Halden needs Mira’s help.'
        name_lines = painter.wrap(name, 130, role='name', bold=True)
        name_height = painter.font('name', bold=True).get_linesize()
        body_height = painter.font('body').get_linesize()
        detail_clip = pygame.Rect(314, round(detail_top), 132, round(224-detail_top))
        description_lines = painter.wrap(description, 130, role='body')
        total_height = len(name_lines)*name_height+10+len(description_lines)*body_height
        self.detail_max_scroll = max(0, total_height-detail_clip.height)
        self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll))
        y -= self.detail_scroll
        painter.clip(detail_clip)
        for line in name_lines:
            painter.text(line, (314, y), role='name', color=INK, bold=True)
            y += name_height
        y += 10
        for line in description_lines:
            painter.text(line, (314, y), role='body', color=SOFT_INK)
            y += body_height
        painter.clip(None)
        if self.detail_max_scroll:
            painter.rect('#c6b588', (449, detail_clip.top, 2, detail_clip.height))
            thumb = max(10, detail_clip.height*detail_clip.height/(detail_clip.height+self.detail_max_scroll))
            offset = (detail_clip.height-thumb)*self.detail_scroll/self.detail_max_scroll
            painter.rect(BRASS, (449, detail_clip.top+offset, 2, thumb))
        painter.line('#c4b184', (314, 228), (444, 228), 1)
        self._player_symbol(painter, (320, 244))
        painter.text('You are here', (331, 236), role='small', color=INK, bold=True)
        if self.game.world is not self.game.town:
            y = 236+painter.font('small', bold=True).get_linesize()+5
            painter.text('Indoors', (314, y), role='small', color=SOFT_INK)
        # The dedicated location legend never competes with landmark rows.
