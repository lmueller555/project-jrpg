"""A bounded, display-resolution chart of the current overworld region.

Only authored vector geometry is read here. Opening this map never requests a
world overview, renders a chunk, or allocates a surface sized to the region.
Coordinates remain global tiles, including the region's negative origin.
"""
from __future__ import annotations

import math

import pygame


PAPER = '#e8d8ad'
INK = '#344337'
MUTED = '#6d7054'
BRASS = '#a88c4b'
WATER = '#789b9b'
WATER_EDGE = '#547679'
FIELD_STYLES = {
    'grain': ('#d7c18a', '#a9915c'),
    'vegetables': ('#b2c29b', '#789167'),
    'fallow': ('#c7b395', '#a18c70'),
    'pasture': ('#c5ca99', '#97a575'),
    'orchard': ('#b4c49b', '#738b63'),
}


class RegionalMapUI:
    MAX_ZOOM = 5.0

    def __init__(self, game):
        self.game = game
        self.map_rect = pygame.Rect(28, 64, 284, 220)
        self.close_rect = pygame.Rect(432, 22, 28, 22)
        self.fit_rect = pygame.Rect(268, 288, 44, 16)
        self.detail_rect = pygame.Rect(328, 88, 116, 138)
        self.selected = 0
        self.hovered = None
        self.pointer = None
        self.detail_scroll = 0
        self.detail_max_scroll = 0
        self.zoom = 1.0
        self.center = pygame.Vector2()
        self._drag = None
        self._world = None
        self.landmarks = []
        self.marker_rects = {}
        self.reset()

    @property
    def data(self):
        world = self.game.world
        return getattr(world, 'region', None) or world.data

    @property
    def bounds(self):
        return tuple(self.data['bounds_tiles'])

    @property
    def tile_size(self):
        return self.data.get('tile_size', 24)

    @property
    def scale(self):
        _, _, width, height = self.bounds
        return min((self.map_rect.width-16)/width,
                   (self.map_rect.height-16)/height)*self.zoom

    @property
    def selected_landmark(self):
        if not self.landmarks:return None
        self.selected %= len(self.landmarks)
        return self.landmarks[self.selected]

    def tile_to_map(self, point):
        point = pygame.Vector2(self.map_rect.center)+(pygame.Vector2(point)-self.center)*self.scale
        return point.x, point.y

    def world_to_map(self, position):
        return self.tile_to_map(pygame.Vector2(position)/self.tile_size)

    def map_to_tile(self, point):
        return self.center+(pygame.Vector2(point)-self.map_rect.center)/self.scale

    def _flags(self):
        return getattr(getattr(self.game, 'social', None), 'flags', set())

    def _collect_landmarks(self):
        records = []
        town = self.data.get('town', {})
        if town:
            records.append(dict(town, kind='town', name=town.get('name', 'Eldenmere'),
                                description='The village, its homes, and the road back to familiar places.'))
        bridge = self.data.get('bridge', {})
        if bridge:
            records.append(dict(bridge, kind='bridge', name=bridge.get('name', 'Western bridge')))
        for gate in self.data.get('gates', []):
            records.append(dict(gate, kind='checkpoint', name=gate.get('label', 'Road checkpoint')))
        discovered = getattr(getattr(self.game, 'overworld_travel', None), 'discovered', None)
        for record in self.data.get('landmarks', []):
            known = (record.get('id') in discovered if discovered is not None else
                     record.get('discovered', True))
            if known or record.get('discovery_flag') in self._flags():
                records.append(dict(record))
        seen = set()
        self.landmarks = []
        for record in records:
            if record.get('id') in seen or 'tile_position' not in record:continue
            seen.add(record.get('id'))
            self.landmarks.append(record)

    def reset(self):
        self._world = self.game.world
        self._collect_landmarks()
        self.fit()
        self.pointer = self.hovered = None
        self.detail_scroll = self.detail_max_scroll = 0
        player = pygame.Vector2(self.game.player.position)/self.tile_size
        self.selected = (min(range(len(self.landmarks)),
                             key=lambda i: player.distance_squared_to(self.landmarks[i]['tile_position']))
                         if self.landmarks else 0)
        self._layout_markers()

    def fit(self):
        x, y, width, height = self.bounds
        self.center.update(x+width/2, y+height/2)
        self.zoom = 1.0
        self._drag = None

    def _clamp(self):
        x, y, width, height = self.bounds
        for axis, (start, extent) in enumerate(((x, width), (y, height))):
            half = (self.map_rect.size[axis]-16)/(2*self.scale)
            self.center[axis] = (start+extent/2 if half*2 >= extent else
                                 max(start+half, min(start+extent-half, self.center[axis])))

    def zoom_at(self, point, steps):
        if not self.map_rect.collidepoint(point):return
        before = self.map_to_tile(point)
        self.zoom = max(1.0, min(self.MAX_ZOOM, self.zoom*1.25**max(-20, min(20, steps))))
        self.center.update(before-(pygame.Vector2(point)-self.map_rect.center)/self.scale)
        self._clamp()
        self._layout_markers()

    def _layout_markers(self):
        self.marker_rects = {}
        for record in self.landmarks:
            rect = pygame.Rect(0, 0, 15, 15)
            rect.center = tuple(round(value) for value in self.tile_to_map(record['tile_position']))
            self.marker_rects[record['id']] = rect.clip(self.map_rect)

    def _at(self, point):
        if point is None or not self.map_rect.collidepoint(point):return None
        candidates = [index for index, record in enumerate(self.landmarks)
                      if self.marker_rects[record['id']].collidepoint(point)]
        return min(candidates, key=lambda i: pygame.Vector2(point).distance_squared_to(
                   self.tile_to_map(self.landmarks[i]['tile_position']))) if candidates else None

    def _point(self, event):
        position = getattr(event, 'pos', pygame.mouse.get_pos())
        convert = getattr(self.game, 'to_canvas', None)
        return convert(position) if convert is not None else position

    def _sound(self, kind):
        style = getattr(self.game, 'ui', None)
        if style is not None:style.sound(kind)

    def _close(self):
        self.game.map_open = False
        self._drag = None
        self._sound('back')

    def handle_event(self, event):
        if not self.game.map_open:return False
        if self._world is not self.game.world:self.reset()
        if event.type == pygame.WINDOWFOCUSLOST:
            self._drag = None
        elif event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key in (pygame.K_m, pygame.K_ESCAPE):self._close()
            elif event.key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a,
                               pygame.K_DOWN, pygame.K_RIGHT, pygame.K_s, pygame.K_d) and self.landmarks:
                step = -1 if event.key in (pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a) else 1
                self.selected = (self.selected+step) % len(self.landmarks)
                self.detail_scroll = 0
                if self.zoom > 1:
                    self.center.update(self.selected_landmark['tile_position'])
                    self._clamp()
                    self._layout_markers()
                self._sound('move')
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.zoom_at(self.map_rect.center, 1)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):self.zoom_at(self.map_rect.center, -1)
            elif event.key == pygame.K_f:
                self.fit()
                self._layout_markers()
            elif event.key == pygame.K_HOME:self.detail_scroll = 0
            elif event.key == pygame.K_END:self.detail_scroll = self.detail_max_scroll
            elif event.key == pygame.K_PAGEUP:self.detail_scroll = max(0, self.detail_scroll-70)
            elif event.key == pygame.K_PAGEDOWN:
                self.detail_scroll = min(self.detail_max_scroll, self.detail_scroll+70)
        elif event.type == pygame.MOUSEWHEEL:
            point = self._point(event)
            if point is not None:
                if self.map_rect.collidepoint(point):self.zoom_at(point, getattr(event, 'precise_y', event.y))
                elif self.detail_rect.collidepoint(point):
                    self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll-event.y*24))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            point = self._point(event)
            self.pointer = point
            if point is not None and event.button == 1:
                if self.close_rect.collidepoint(point):self._close()
                elif self.fit_rect.collidepoint(point):
                    self.fit()
                    self._layout_markers()
                elif self.map_rect.collidepoint(point):
                    self._drag = pygame.Vector2(point)
                    index = self._at(point)
                    if index is not None:
                        self.selected = index
                        self.detail_scroll = 0
                        self._sound('confirm')
            elif point is not None and event.button in (4, 5):
                self.zoom_at(point, 1 if event.button == 4 else -1)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:self._drag = None
        elif event.type == pygame.MOUSEMOTION:
            point = self._point(event)
            self.pointer = point
            if self._drag is not None:
                if point is None:self._drag = None
                else:
                    self.center -= (pygame.Vector2(point)-self._drag)/self.scale
                    self._drag.update(point)
                    self._clamp()
                    self._layout_markers()
            self.hovered = self._at(point)
        return True

    @staticmethod
    def _polygon(painter, color, points, width=0):
        if len(points) >= 3:
            pygame.draw.polygon(painter.canvas, color, [painter.point(point) for point in points],
                                max(1, round(width*painter.scale)) if width else 0)

    @staticmethod
    def _circle(painter, color, point, radius, width=0):
        pygame.draw.circle(painter.canvas, color, painter.point(point), max(1, round(radius*painter.scale)),
                           max(1, round(width*painter.scale)) if width else 0)

    @staticmethod
    def _inside(point, polygon):
        x, y = point
        inside = False
        previous = polygon[-1]
        for current in polygon:
            ax, ay = previous
            bx, by = current
            if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:inside = not inside
            previous = current
        return inside

    def _terrain_hatching(self, painter, record, kind, points, edge):
        # Work only over the clipped display rectangle. Neither large authored
        # polygons nor increased map zoom increase the glyph allocation budget.
        box = pygame.Rect(min(p[0] for p in points), min(p[1] for p in points),
                          max(p[0] for p in points)-min(p[0] for p in points),
                          max(p[1] for p in points)-min(p[1] for p in points)).clip(self.map_rect)
        spacing = 12 if kind == 'forests' else 13
        angle = math.radians(record.get('row_angle', -18))
        direction = (math.cos(angle), math.sin(angle))
        crop = record.get('crop', 'grain')
        for row, y in enumerate(range(box.top+5, box.bottom-3, spacing)):
            for column, x in enumerate(range(box.left+5, box.right-3, spacing)):
                # Full little glyphs stay within their own parcel or woodland.
                if not all(self._inside(point, points) for point in
                           ((x-4, y-4), (x+4, y-4), (x-4, y+4), (x+4, y+4))):continue
                if kind == 'fields':
                    if crop == 'orchard':
                        self._circle(painter, edge, (x, y-1), 2, 1)
                        painter.line(edge, (x, y+1), (x, y+4))
                    elif crop == 'pasture':
                        painter.line(edge, (x-3, y+2), (x-1, y-1))
                        painter.line(edge, (x-1, y-1), (x, y+2))
                        painter.line(edge, (x, y+2), (x+2, y))
                    else:
                        dx, dy = direction[0]*4, direction[1]*4
                        painter.line(edge, (x-dx, y-dy), (x+dx, y+dy))
                        if crop == 'vegetables':
                            for offset in (-2, 2):
                                self._circle(painter, edge,
                                             (x+direction[0]*offset, y+direction[1]*offset), .7)
                        elif crop == 'fallow':
                            normal = (-direction[1]*2, direction[0]*2)
                            painter.line(edge, (x-dx+normal[0], y-dy+normal[1]),
                                         (x+dx+normal[0], y+dy+normal[1]))
                elif kind == 'forests':
                    conifer = (record.get('style') == 'conifer' or
                               record.get('style') == 'mixed' and (row+column)%3 == 0)
                    if conifer:
                        self._polygon(painter, edge, ((x, y-4), (x-3, y+2), (x+3, y+2)), 1)
                        painter.line(edge, (x, y+2), (x, y+4))
                    else:
                        self._circle(painter, edge, (x-1, y-1), 2, 1)
                        self._circle(painter, edge, (x+1, y-2), 2, 1)
                        painter.line(edge, (x, y+1), (x, y+4))
                elif kind == 'hills':
                    if record.get('style') == 'wooded_rise':
                        for a, b in (((x-4, y+2), (x-2, y)), ((x-2, y), (x+1, y-1)),
                                     ((x+1, y-1), (x+4, y+1))):painter.line(edge, a, b)
                    else:
                        painter.line(edge, (x-4, y+2), (x, y-3))
                        painter.line(edge, (x, y-3), (x+4, y+2))
                        painter.line(edge, (x, y-3), (x+1, y+1))
                else:painter.line(edge, (x-3, y+2), (x+3, y-1))

    def _draw_terrain(self, painter):
        painter.rect(PAPER, self.map_rect)
        terrain = self.data.get('terrain', {})
        for kind, fill, edge in (('fields', '#c5c79d', '#adb58b'),
                                  ('forests', '#a4b28c', '#657e66'),
                                  ('hills', '#d5caa3', '#aca87f'),
                                  ('scorched', '#beb099', '#97866f')):
            for record in terrain.get(kind, []):
                polygon = record.get('polygon', [])
                points = [self.tile_to_map(point) for point in polygon]
                parcel_fill, parcel_edge = (FIELD_STYLES.get(record.get('crop'), FIELD_STYLES['grain'])
                                            if kind == 'fields' else (fill, edge))
                self._polygon(painter, parcel_fill, points)
                if len(points) < 3:continue
                if kind == 'fields':self._polygon(painter, parcel_edge, points, .5)
                self._terrain_hatching(painter, record, kind, points, parcel_edge)
        for record in terrain.get('rivers', []):
            self._draw_route(painter, record, WATER_EDGE, WATER, minimum=3)

    def _draw_route(self, painter, record, edge, fill, minimum=2):
        points = [self.tile_to_map(point) for point in record.get('points', [])]
        width = max(minimum, record.get('width', 2)*self.scale)
        for start, end in zip(points, points[1:]):
            painter.line(edge, start, end, width+2)
            painter.line(fill, start, end, width)
            self._circle(painter, fill, start, width/2)
        if points:self._circle(painter, fill, points[-1], width/2)

    def _draw_footpath(self, painter, record):
        # Accumulate dashes along the route rather than restarting at each
        # sampled curve point, so densified paths remain a coherent fine line.
        points = [self.tile_to_map(point) for point in record.get('points', [])]
        phase = 0.0
        for start, end in zip(points, points[1:]):
            delta = pygame.Vector2(end)-start
            length = delta.length()
            if not length:continue
            direction = delta/length
            offset = 0.0
            while offset < length:
                step = min(length-offset, 7-phase)
                if phase < 4:
                    visible = min(step, 4-phase)
                    painter.line('#a28f6b', pygame.Vector2(start)+direction*offset,
                                 pygame.Vector2(start)+direction*(offset+visible), 1)
                offset += step
                phase = (phase+step)%7

    def _draw_farmsteads(self, painter):
        # Farmyards are descriptive cartography, not selectable destinations or
        # additional discovery records. Existing landmark/save identities stay
        # entirely with the travel controller.
        for record in self.data.get('setpieces', []):
            if record.get('kind') not in ('farm', 'farmstead', 'farmyard'):continue
            position = record.get('tile_position')
            if position is None:continue
            x, y = self.tile_to_map(position)
            if not self.map_rect.inflate(12, 12).collidepoint(x, y):continue
            painter.rect('#b8a17b', (x-3, y-1, 6, 4))
            self._polygon(painter, '#8d7657', ((x-4, y), (x, y-4), (x+4, y)))
            painter.line('#a39370', (x-5, y+5), (x+5, y+5))

    def _draw_roads_walls(self, painter):
        for road in self.data.get('roads', []):
            kind = road.get('kind', 'stone' if road.get('surface') == 'stone_road' else 'cart')
            if kind == 'foot':self._draw_footpath(painter, road)
            elif kind == 'stone':self._draw_route(painter, road, '#a79e83', '#ded2af', minimum=2.2)
            else:self._draw_route(painter, road, '#b49d75', '#d2bc8c', minimum=1.3)
        for wall in self.data.get('walls', []):
            left = self.tile_to_map((wall['x0'], wall['y']))
            right = self.tile_to_map((wall['x1'], wall['y']))
            gate = self.tile_to_map((wall['gate_x'], wall['y']))
            half = max(3, wall.get('gate_width', 4)*self.scale/2)
            for start, end in ((left, (gate[0]-half, gate[1])),
                               ((gate[0]+half, gate[1]), right)):
                painter.line('#777866', (start[0], start[1]+2), (end[0], end[1]+2), 5)
                painter.line('#a39d7c', start, end, 4)
                painter.line('#e1d0a7', start, end, 1)
                for x in range(round(start[0])+2, round(end[0]), 7):
                    if self.map_rect.left <= x <= self.map_rect.right:
                        painter.rect('#8c8c70', (x, start[1]-3, 3, 3))

    def _draw_marker(self, painter, record):
        x, y = self.tile_to_map(record['tile_position'])
        if not self.map_rect.inflate(16, 16).collidepoint((x, y)):return
        kind = record.get('kind')
        if kind == 'town':
            # A settlement glyph keeps Eldenmere legible at regional scale.
            for dx, dy in ((-5, 1), (2, 3), (-1, -4)):
                painter.rect('#b5a17b', (x+dx-2, y+dy, 5, 5))
                self._polygon(painter, '#796b56', [(x+dx-3, y+dy+1), (x+dx, y+dy-3), (x+dx+3, y+dy+1)])
            painter.text(record['name'], (x+10, y-12), role='small', color=INK)
        elif kind == 'bridge':
            repaired = record.get('repair_flag') in self._flags()
            for dx in (-6, 3):
                painter.rect('#88745a', (x+dx, y-3, 4, 7))
                painter.line('#d9c49c', (x+dx+1, y-3), (x+dx+1, y+3), 1)
            if repaired:painter.rect('#88745a', (x-2, y-3, 5, 7))
            else:
                painter.line('#8b4f3e', (x-2, y-4), (x+2, y+4), 2)
                painter.line('#8b4f3e', (x+2, y-4), (x-2, y+4), 2)
        elif kind == 'checkpoint':
            painter.rect('#706e5b', (x-5, y-4, 3, 8))
            painter.rect('#706e5b', (x+3, y-4, 3, 8))
            painter.line('#e5d5ad', (x-5, y-5), (x+6, y-5), 2)
            if not (record.get('clearance_flag') in self._flags() and
                    record.get('destination_ready', False)):
                painter.line('#8b4f3e', (x-2, y), (x+3, y), 2)
        else:
            self._circle(painter, '#f2e5c4', (x, y), 3)
            self._circle(painter, '#64745d', (x, y), 3, 1)
            self._circle(painter, '#64745d', (x, y), 1)

    @staticmethod
    def _player_symbol(painter, point):
        x, y = point
        for a, b in (((x-4, y), (x, y-4)), ((x, y-4), (x+4, y)),
                     ((x+4, y), (x, y+4)), ((x, y+4), (x-4, y))):
            painter.line('#fff1c8', a, b, 3)
            painter.line(INK, a, b, 1)
        painter.rect(INK, (x-1, y-1, 2, 2))

    def _description(self, record):
        if record.get('kind') == 'bridge':
            return ('The western crossing is passable.' if record.get('repair_flag') in self._flags() else
                    'The western crossing is broken. The far bank cannot be reached here.')
        if record.get('kind') == 'checkpoint':
            return ('The watch has granted passage.' if record.get('clearance_flag') in self._flags() and
                    record.get('destination_ready', False) else 'The watch keeps this checkpoint closed.')
        return record.get('description', 'A familiar landmark in Elden Vale.')

    def _draw_details(self, painter):
        painter.text('SELECTED PLACE', (328, 67), role='small', color=MUTED, bold=True)
        self.detail_rect.top = max(88, 67+painter.font('small', bold=True).get_linesize()+6)
        self.detail_rect.height = max(30, 225-self.detail_rect.top)
        record = self.selected_landmark
        name = record.get('name', 'Elden Vale') if record else 'Elden Vale'
        description = self._description(record) if record else 'Follow the roads to discover the region.'
        name_lines = painter.wrap(name, self.detail_rect.width, role='name', bold=True)
        lines = painter.wrap(description, self.detail_rect.width, role='body')
        name_height = painter.font('name', bold=True).get_linesize()
        body_height = painter.font('body').get_linesize()
        total = len(name_lines)*name_height+8+len(lines)*body_height
        self.detail_max_scroll = max(0, total-self.detail_rect.height)
        self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll))
        painter.clip(self.detail_rect)
        y = self.detail_rect.top-self.detail_scroll
        for line in name_lines:
            painter.text(line, (328, y), role='name', color=INK, bold=True)
            y += name_height
        y += 8
        for line in lines:
            painter.text(line, (328, y), role='body', color=MUTED)
            y += body_height
        painter.clip(None)
        if self.detail_max_scroll:
            painter.rect('#c6b588', (449, self.detail_rect.top, 2, self.detail_rect.height))
            thumb = max(10, self.detail_rect.height**2/(self.detail_rect.height+self.detail_max_scroll))
            offset = (self.detail_rect.height-thumb)*self.detail_scroll/self.detail_max_scroll
            painter.rect(BRASS, (449, self.detail_rect.top+offset, 2, thumb))
        painter.line('#c4b184', (328, 232), (444, 232))
        self._player_symbol(painter, (334, 245))
        painter.text('You are here', (345, 237), role='small', color=INK, bold=True)
        painter.text('Elden Vale', (328, 258), role='small', color=MUTED)

    def _draw_hover(self, painter):
        if self.hovered is None or self.hovered >= len(self.landmarks):return
        record = self.landmarks[self.hovered]
        lines = painter.wrap(record.get('name', 'Landmark'), 146, role='small', bold=True)
        height = len(lines)*painter.font('small', bold=True).get_linesize()+8
        width = max(painter.font('small', bold=True).size(line)[0] for line in lines)+12
        point = self.tile_to_map(record['tile_position'])
        rect = pygame.Rect(point[0]+10, point[1]+11, width, height).clamp(self.map_rect.inflate(-6, -6))
        painter.rect('#f1e5c5', rect)
        painter.rect(BRASS, rect, 1)
        for index, line in enumerate(lines):
            painter.text(line, (rect.left+6, rect.top+4+index*painter.font('small', bold=True).get_linesize()),
                         role='small', bold=True, color=INK)

    def draw(self, canvas):
        if not self.game.map_open:return
        if self._world is not self.game.world:self.reset()
        style = getattr(self.game, 'ui', None)
        if style is None:
            from ui_style import UIStyle
            style = self.game.ui = UIStyle(self.game)
        painter = style.painter(canvas, logical_size=(480, 320))
        old_clip = canvas.get_clip()
        try:
            painter.veil(190)
            painter.panel((12, 12, 456, 296), parchment=True)
            painter.lantern((31, 31), color=BRASS, size=10)
            painter.text('Elden Vale', (47, 23), role='heading', color=INK, bold=True)
            subtitle_y = 23+painter.font('heading', bold=True).get_linesize()+2
            if subtitle_y+painter.font('small').get_linesize() <= self.map_rect.top-4:
                painter.text('Merovar · Regional map', (28, subtitle_y), role='small', color=MUTED)
            painter.button(self.close_rect, '×', selected=self.pointer is not None and
                           self.close_rect.collidepoint(self.pointer))
            painter.clip(self.map_rect)
            self._draw_terrain(painter)
            self._draw_roads_walls(painter)
            self._draw_farmsteads(painter)
            self._layout_markers()
            for index, record in enumerate(self.landmarks):
                self._draw_marker(painter, record)
                if index == self.selected or index == self.hovered:
                    x, y = self.tile_to_map(record['tile_position'])
                    self._circle(painter, '#967135' if index == self.selected else BRASS, (x, y), 9, 1)
            self._player_symbol(painter, self.world_to_map(self.game.player.position))
            self._draw_hover(painter)
            painter.text('N', (self.map_rect.right-11, self.map_rect.top+6), role='small', color=INK, anchor='midtop')
            painter.line(INK, (self.map_rect.right-11, self.map_rect.top+32),
                         (self.map_rect.right-11, self.map_rect.top+21))
            painter.line(INK, (self.map_rect.right-11, self.map_rect.top+21),
                         (self.map_rect.right-14, self.map_rect.top+26))
            painter.line(INK, (self.map_rect.right-11, self.map_rect.top+21),
                         (self.map_rect.right-8, self.map_rect.top+26))
            painter.clip(None)
            painter.rect(BRASS, self.map_rect, 1)
            painter.line('#c4b184', (320, 64), (320, 284))
            self._draw_details(painter)
            painter.text('Scroll: zoom · Drag: pan', (28, 289), role='small', color=MUTED)
            painter.button(self.fit_rect, 'Fit', selected=self.pointer is not None and
                           self.fit_rect.collidepoint(self.pointer))
        finally:canvas.set_clip(old_clip)
