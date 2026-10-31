"""Illustrated regional atlas with live navigation and readable place labels.

Terrain tiles are shared with the exploration minimap. Labels, roads, passage
states and Caelan's marker stay live, in display pixels. Old vector helpers are
kept as a bounded fallback for unregistered fixture or future-region geometry.
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
        self.map_rect = pygame.Rect(16, 42, 448, 240)
        self.close_rect = pygame.Rect(438, 13, 24, 22)
        self.fit_rect = pygame.Rect(408, 291, 44, 18)
        self.detail_rect = pygame.Rect(0, 0, 150, 70)
        self.detail_panel = pygame.Rect(0, 0, 172, 126)
        self.detail_close_rect = pygame.Rect(0, 0, 14, 14)
        self.details_visible = False
        self.selected = 0
        self.hovered = None
        self.pointer = None
        self.detail_scroll = 0
        self.detail_max_scroll = 0
        self.zoom = 1.0
        self.center = pygame.Vector2()
        self._drag = None
        self._pressed_place = None
        self._drag_travel = 0
        self._world = None
        self.landmarks = []
        self.marker_rects = {}
        self.label_rects = {}
        self._label_layout = []
        self._fit_bounds = None
        self._footer_y = 287
        self._hint_y = 299
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
        _, _, width, height = self.focus_bounds
        return min((self.map_rect.width-16)/width,
                   (self.map_rect.height-16)/height)*self.zoom

    @property
    def min_zoom(self):
        _,_,width,height = self.bounds
        _,_,focus_width,focus_height = self.focus_bounds
        context_scale = min((self.map_rect.width-16)/width,(self.map_rect.height-16)/height)
        focus_scale = min((self.map_rect.width-16)/focus_width,(self.map_rect.height-16)/focus_height)
        return min(1.0,context_scale/focus_scale)

    @property
    def focus_bounds(self):
        chart = self._chart()
        return tuple(chart.focus_bounds) if chart is not None else self.bounds

    def _chart(self, refresh=False):
        try:
            from regional_cartography import get_cartography
            return get_cartography(self.game, refresh=refresh)
        except (ImportError, FileNotFoundError):
            return None

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
            records.append(dict(bridge, kind='bridge', name=bridge.get('name', 'Western crossing')))
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
        self._chart(refresh=True)
        self._collect_landmarks()
        self.fit()
        self.pointer = self.hovered = None
        self.detail_scroll = self.detail_max_scroll = 0
        self.details_visible = False
        player = pygame.Vector2(self.game.player.position)/self.tile_size
        self.selected = (min(range(len(self.landmarks)),
                             key=lambda i: player.distance_squared_to(self.landmarks[i]['tile_position']))
                         if self.landmarks else 0)
        self._layout_markers()

    def fit(self):
        x, y, width, height = self.focus_bounds
        self.center.update(x+width/2, y+height/2)
        self.zoom = 1.0
        self._drag = None
        self.details_visible = False
        self.detail_scroll = 0

    def _clamp(self):
        x, y, width, height = self.bounds
        for axis, (start, extent) in enumerate(((x, width), (y, height))):
            half = (self.map_rect.size[axis]-16)/(2*self.scale)
            self.center[axis] = (start+extent/2 if half*2 >= extent else
                                 max(start+half, min(start+extent-half, self.center[axis])))

    def zoom_at(self, point, steps):
        if not self.map_rect.collidepoint(point):return
        before = self.map_to_tile(point)
        self.zoom = max(self.min_zoom,min(self.MAX_ZOOM,
                        self.zoom*1.25**max(-20,min(20,steps))))
        self.center.update(before-(pygame.Vector2(point)-self.map_rect.center)/self.scale)
        self._clamp()
        self._layout_markers()

    def _layout_markers(self):
        self.marker_rects = {}
        for record in self.landmarks:
            size = self._marker_size(record)+4
            rect = pygame.Rect(0, 0, max(17, size), max(17, size))
            rect.center = tuple(round(value) for value in self.tile_to_map(record['tile_position']))
            self.marker_rects[record['id']] = rect.clip(self.map_rect)

    def select_landmark(self, identifier):
        """Select a known place without adding travel or discovery actions."""
        for index, record in enumerate(self.landmarks):
            if record['id'] == identifier:
                self.selected = index
                self.details_visible = True
                self.detail_scroll = 0
                return True
        return False

    def _at(self, point):
        if point is None or not self.map_rect.collidepoint(point):return None
        candidates = [index for index, record in enumerate(self.landmarks)
                      if (self.marker_rects[record['id']].collidepoint(point) or
                          self.label_rects.get(record['id'],pygame.Rect(0,0,0,0)).collidepoint(point))]
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
                self.details_visible = True
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
                if self.details_visible and self.detail_panel.collidepoint(point):
                    self.detail_scroll = max(0, min(self.detail_max_scroll, self.detail_scroll-event.y*24))
                elif self.map_rect.collidepoint(point):self.zoom_at(point, getattr(event, 'precise_y', event.y))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            point = self._point(event)
            self.pointer = point
            if point is not None and event.button == 1:
                if self.close_rect.collidepoint(point):self._close()
                elif self.fit_rect.collidepoint(point):
                    self.fit()
                    self._layout_markers()
                elif self.details_visible and self.detail_panel.collidepoint(point):
                    if self.detail_close_rect.collidepoint(point):
                        self.details_visible = False
                elif self.map_rect.collidepoint(point):
                    self._drag = pygame.Vector2(point)
                    self._pressed_place = self._at(point)
                    self._drag_travel = 0
            elif point is not None and event.button in (4, 5):
                steps = 1 if event.button == 4 else -1
                if self.details_visible and self.detail_panel.collidepoint(point):
                    self.detail_scroll = max(0,min(self.detail_max_scroll,self.detail_scroll-steps*24))
                elif self.map_rect.collidepoint(point):self.zoom_at(point,steps)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._drag is not None and self._drag_travel < 3:
                if self._pressed_place is not None:
                    self.selected = self._pressed_place
                    self.details_visible = True
                    self.detail_scroll = 0
                    self._sound('confirm')
                else:self.details_visible = False
            self._drag = self._pressed_place = None
        elif event.type == pygame.MOUSEMOTION:
            point = self._point(event)
            self.pointer = point
            if self._drag is not None:
                if point is None:self._drag = None
                else:
                    delta = pygame.Vector2(point)-self._drag
                    self._drag_travel += delta.length()
                    self.center -= delta/self.scale
                    self._drag.update(point)
                    self._clamp()
                    self._layout_markers()
            self.hovered = (None if self.details_visible and point is not None and
                            self.detail_panel.collidepoint(point) else self._at(point))
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
            if self._art_icon(painter, 'farm', (x, y), 12):continue
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

    def _legacy_marker(self, painter, record):
        x, y = self.tile_to_map(record['tile_position'])
        if not self.map_rect.inflate(16, 16).collidepoint((x, y)):return
        kind = record.get('kind')
        if kind == 'town':
            # A settlement glyph keeps Eldenmere legible at regional scale.
            for dx, dy in ((-5, 1), (2, 3), (-1, -4)):
                painter.rect('#b5a17b', (x+dx-2, y+dy, 5, 5))
                self._polygon(painter, '#796b56', [(x+dx-3, y+dy+1), (x+dx, y+dy-3), (x+dx+3, y+dy+1)])
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
    def _marker_size(record):
        return {'town':22, 'bridge':18, 'checkpoint':17}.get(record.get('kind'),13)

    def _art_icon(self, painter, key, point, size):
        chart = self._chart()
        if chart is None:return False
        icon = chart.icon(key, size=(max(1,round(size*painter.scale)),)*2)
        if icon is None:return False
        painter.canvas.blit(icon,icon.get_rect(center=painter.point(point)))
        return True

    def _marker_status(self, record):
        if record.get('kind') == 'bridge':
            return 'Passable' if record.get('repair_flag') in self._flags() else 'Ruined'
        if record.get('kind') == 'checkpoint':
            return ('Open' if record.get('clearance_flag') in self._flags() and
                    record.get('destination_ready',False) else 'Closed')
        return {'town':'Village', 'millrace':'Millrace', 'staging':'Work site',
                'overlook':'Overlook'}.get(record.get('kind'),'Landmark')

    def _draw_marker(self, painter, record):
        point = self.tile_to_map(record['tile_position'])
        if not self.map_rect.inflate(24,24).collidepoint(point):return
        kind = record.get('kind');status = self._marker_status(record)
        key = {'town':'town','overlook':'overlook','millrace':'millrace','staging':'relief'}.get(kind,'overlook')
        if kind == 'bridge':key = 'bridge_repaired' if status == 'Passable' else 'bridge_broken'
        elif kind == 'checkpoint':key = 'gate_open' if status == 'Open' else 'gate_closed'
        if not self._art_icon(painter,key,point,self._marker_size(record)):
            self._legacy_marker(painter,record)
        # These conventional marks remain live even when an illustration is
        # viewed in grayscale or at a small zoom.
        x,y = point
        if kind == 'checkpoint' and status == 'Closed':
            painter.line('#8b4f3e',(x-3,y),(x+3,y),2)
        elif kind == 'bridge' and status == 'Ruined':
            painter.line('#8b4f3e',(x-2,y-2),(x+2,y+2),1)
            painter.line('#8b4f3e',(x+2,y-2),(x-2,y+2),1)

    @staticmethod
    def _player_symbol(painter, point, facing='front'):
        angle = {'back':0,'right':math.pi/2,'front':math.pi,'left':-math.pi/2}.get(facing,math.pi)
        c,s = math.cos(angle),math.sin(angle)
        def shape(points):
            return [painter.point((point[0]+x*c-y*s,point[1]+x*s+y*c)) for x,y in points]
        outline = shape(((0,-7),(5,5),(0,2),(-5,5)))
        pygame.draw.polygon(painter.canvas,INK,outline)
        pygame.draw.polygon(painter.canvas,'#fff5d5',shape(((0,-5.5),(3.5,3.5),(0,1),(-3.5,3.5))))
        pygame.draw.polygon(painter.canvas,'#d9aa46',shape(((0,-3.5),(1.8,2),(0,.5),(-1.8,2))))

    def _description(self, record):
        if record.get('kind') == 'bridge':
            return ('The western crossing is passable.' if record.get('repair_flag') in self._flags() else
                    'The western crossing is broken. The far bank cannot be reached here.')
        if record.get('kind') == 'checkpoint':
            return ('The watch has granted passage.' if record.get('clearance_flag') in self._flags() and
                    record.get('destination_ready', False) else 'The watch keeps this checkpoint closed.')
        return record.get('description', 'A familiar landmark in Elden Vale.')

    def _layout(self, painter):
        # Both dimensions matter: a wide pane alone cannot enlarge a 4:3 map.
        title_height = painter.font('name',bold=True).get_linesize()
        small_height = painter.font('small').get_linesize()
        top = max(40,16+title_height+8)
        footer_height = small_height*2+8
        bottom = 310-footer_height
        self.map_rect.update(16,top,448,max(160,bottom-top))
        self._footer_y = bottom+3
        self._hint_y = self._footer_y+small_height+1
        button_height = max(18,painter.font('body').get_linesize()+6)
        self.fit_rect.update(408,310-button_height,44,button_height)
        self.close_rect.update(438,13,24,max(22,title_height+4))
        self._layout_markers()
        self._layout_details(painter)

    def _layout_details(self, painter):
        if not self.details_visible or self.selected_landmark is None:
            self.detail_max_scroll = 0
            return
        record = self.selected_landmark
        width = 172
        self._detail_name_lines = painter.wrap(record.get('name','Landmark'),width-34,role='name',bold=True)
        self._detail_lines = painter.wrap(self._description(record),width-20,role='body')
        name_height = painter.font('name',bold=True).get_linesize()
        line_height = painter.font('body').get_linesize()
        status_height = painter.font('small',bold=True).get_linesize()
        header_height = len(self._detail_name_lines)*name_height+status_height+21
        height = min(148,max(84,header_height+len(self._detail_lines)*line_height+9))
        safe = self.map_rect.inflate(-16,-16)
        minimum_height = min(height,max(84,header_height+28))
        heights = list(range(height,minimum_height-1,-8))
        if minimum_height not in heights:heights.append(minimum_height)
        candidates = [pygame.Rect(position,(width,h)) for h in heights for position in
                      ((safe.right-width,safe.bottom-h),(safe.left,safe.bottom-h),
                       (safe.right-width,safe.top),(safe.left,safe.top))]
        player = self.world_to_map(self.game.player.position)
        selected = self.tile_to_map(record['tile_position'])
        player_obstacle = pygame.Rect(player[0]-10,player[1]-10,20,20)
        selected_obstacle = self.marker_rects[record['id']].inflate(6,6)
        important = [self.marker_rects[item['id']].inflate(6,6) for item in self.landmarks
                     if item.get('kind') in ('town','bridge','checkpoint')]
        compass = pygame.Rect(self.map_rect.right-29,self.map_rect.top+8,22,36)
        def score(rect):
            overlap = rect.colliderect(selected_obstacle)*1000
            overlap += rect.colliderect(player_obstacle)*500
            overlap += sum(rect.colliderect(obstacle)*3 for obstacle in important)
            overlap += rect.colliderect(compass)*2
            return overlap,height-rect.height,-pygame.Vector2(rect.center).distance_squared_to(selected)
        self.detail_panel = min(candidates,key=score)
        height = self.detail_panel.height
        self.detail_close_rect = pygame.Rect(self.detail_panel.right-20,self.detail_panel.top+6,14,14)
        self.detail_rect = pygame.Rect(self.detail_panel.left+10,self.detail_panel.top+header_height,
                                      width-20,max(20,height-header_height-8))
        self.detail_max_scroll = max(0,len(self._detail_lines)*line_height-self.detail_rect.height)
        self.detail_scroll = max(0,min(self.detail_max_scroll,self.detail_scroll))

    def _label_lines(self, painter, record):
        name = record.get('name','Landmark')
        if record.get('kind') == 'bridge':name = 'Western crossing'
        if record.get('kind') == 'bridge' and painter.font('small',bold=True).size(name)[0] > 118:
            name = 'West bridge'
        if (record.get('kind') == 'checkpoint' and
                painter.font('small',bold=True).size(name)[0] > 130):
            name = 'North gate' if record['tile_position'][1] < 0 else 'South gate'
        width = 170 if record.get('kind') in ('town','bridge','checkpoint') else 118
        lines = painter.wrap(name,width,role='small',bold=True)
        if record.get('kind') in ('bridge','checkpoint'):
            lines.append(self._marker_status(record))
        return lines

    def _layout_labels(self, painter):
        self.label_rects = {}
        self._label_layout = []
        if not self.landmarks:return
        selected_id = self.selected_landmark['id'] if self.details_visible else None
        hovered_id = self.landmarks[self.hovered]['id'] if self.hovered is not None else None
        priority = {'town':0,'bridge':1,'checkpoint':2}
        records = sorted(self.landmarks,key=lambda r:(-1 if r['id']==selected_id else
                         priority.get(r.get('kind'),4),r['id']))
        major_ids = {record['id'] for record in self.landmarks if record.get('kind') in priority}
        occupied = [rect.inflate(2,2) for key,rect in self.marker_rects.items()
                    if rect.width and rect.height and key in major_ids | {selected_id}]
        player = self.world_to_map(self.game.player.position)
        occupied.append(pygame.Rect(round(player[0])-8,round(player[1])-9,16,18))
        occupied.append(pygame.Rect(self.map_rect.right-29,self.map_rect.top+7,24,38))
        if self.details_visible:occupied.append(self.detail_panel.inflate(6,6))
        safe = self.map_rect.inflate(-10,-10)
        line_height = painter.font('small',bold=True).get_linesize()
        for record in records:
            major = record.get('kind') in priority
            if not major and self.zoom < 1.6 and record['id'] not in (selected_id,hovered_id):continue
            x,y = self.tile_to_map(record['tile_position'])
            if not self.map_rect.collidepoint(x,y):continue
            lines = self._label_lines(painter,record)
            width = max(painter.font('small',bold=True).size(line)[0] for line in lines)+4
            height = line_height*len(lines)+2
            radius = self._marker_size(record)/2+5
            candidates = []
            for offset in (0,12,24,40):
                gap = radius+offset
                candidates.extend(pygame.Rect(round(px),round(py),width,height) for px,py in
                                  ((x+gap,y-height/2),(x-gap-width,y-height/2),
                                   (x+gap,y-height*.15),(x-gap-width,y-height*.15),
                                   (x+gap,y-height*.85),(x-gap-width,y-height*.85),
                                   (x-width/2,y-gap-height),(x-width/2,y+gap),
                                   (x+gap,y-gap-height),(x-gap-width,y+gap)))
            chosen = next((rect for rect in candidates if safe.contains(rect) and
                           not any(rect.colliderect(other) for other in occupied)),None)
            if chosen is None and major:
                # Major navigation names keep a place even at large text. Use
                # the least crowded in-bounds candidate rather than clipping.
                candidates = [rect.clamp(safe) for rect in candidates]
                if self.details_visible:
                    candidates = [rect for rect in candidates if not rect.colliderect(self.detail_panel)]
                if not candidates:continue
                chosen = min(candidates,key=lambda rect:sum(rect.clip(other).width*rect.clip(other).height
                                                            for other in occupied))
            if chosen is None:continue
            self.label_rects[record['id']] = chosen
            occupied.append(chosen.inflate(5,4))
            self._label_layout.append((record,lines,chosen))
        # Minor symbols yield to priority lettering at a crowded overview;
        # selecting one restores its own symbol and gives its label priority.
        major_labels = [rect for key,rect in self.label_rects.items() if key in major_ids]
        for record in self.landmarks:
            key = record['id']
            if key in major_ids or key == selected_id:continue
            if any(self.marker_rects[key].colliderect(rect) for rect in major_labels):
                self.marker_rects[key] = pygame.Rect(0,0,0,0)

    def _draw_labels(self, painter):
        line_height = painter.font('small',bold=True).get_linesize()
        for record,lines,rect in self._label_layout:
            for index,line in enumerate(lines):
                point = (rect.left+2,rect.top+index*line_height)
                color = '#704738' if index == len(lines)-1 and line in ('Closed','Ruined') else INK
                # A quiet paper halo separates lettering from rich terrain
                # without covering it with a row of opaque label boxes.
                for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                    painter.text(line,(point[0]+dx,point[1]+dy),role='small',color='#eee4c5',bold=True)
                painter.text(line,point,role='small',color=color,bold=True)

    def _draw_details(self, painter):
        if not self.details_visible or self.selected_landmark is None:return
        record = self.selected_landmark
        panel = self.detail_panel
        painter.panel(panel,parchment=True)
        painter.rect(BRASS,(panel.left+1,panel.top+1,2,panel.height-2))
        y = panel.top+8
        name_height = painter.font('name',bold=True).get_linesize()
        for line in self._detail_name_lines:
            painter.text(line,(panel.left+10,y),role='name',color=INK,bold=True)
            y += name_height
        status = self._marker_status(record)
        painter.text(status,(panel.left+10,y+2),role='small',
                     color='#8b4f3e' if status in ('Closed','Ruined') else MUTED,bold=True)
        painter.text('×',self.detail_close_rect.center,role='body',anchor='center',color=MUTED)
        painter.clip(self.detail_rect)
        line_height = painter.font('body').get_linesize()
        y = self.detail_rect.top-self.detail_scroll
        for line in self._detail_lines:
            painter.text(line,(self.detail_rect.left,y),role='body',color=INK)
            y += line_height
        painter.clip(None)
        if self.detail_max_scroll:
            x = panel.right-5
            painter.rect('#c6b588',(x,self.detail_rect.top,2,self.detail_rect.height))
            thumb = max(10,self.detail_rect.height**2/(self.detail_rect.height+self.detail_max_scroll))
            offset = (self.detail_rect.height-thumb)*self.detail_scroll/self.detail_max_scroll
            painter.rect(BRASS,(x,self.detail_rect.top+offset,2,thumb))

    def _draw_hover(self, painter):
        # Persistent names and hover-priority label placement replace the old
        # tooltip box, keeping the underlying route visible.
        return

    def _draw_legend(self, painter):
        y = self._footer_y
        self._player_symbol(painter,(23,y+4),'back')
        painter.text('You',(32,y-1),role='small',color=INK)
        x = 32+painter.font('small').size('You')[0]+17
        painter.line('#8b4f3e',(x,y+3),(x+8,y+3),2)
        painter.line(INK,(x,y),(x,y+7),1)
        painter.line(INK,(x+8,y),(x+8,y+7),1)
        painter.text('Closed gate',(x+12,y-1),role='small',color=INK)
        x += 12+painter.font('small').size('Closed gate')[0]+17
        painter.line('#8b4f3e',(x,y),(x+6,y+6),1)
        painter.line('#8b4f3e',(x+6,y),(x,y+6),1)
        painter.text('Ruined crossing',(x+11,y-1),role='small',color=INK)

    def draw(self, canvas):
        if not self.game.map_open:return
        if self._world is not self.game.world:self.reset()
        style = getattr(self.game,'ui',None)
        if style is None:
            from ui_style import UIStyle
            style = self.game.ui = UIStyle(self.game)
        painter = style.painter(canvas,logical_size=(480,320))
        old_clip = canvas.get_clip()
        try:
            self._layout(painter)
            painter.veil(205)
            painter.panel((8,8,464,304),parchment=True)
            painter.text('Elden Vale',(20,14),role='name',color=INK,bold=True)
            painter.text('REGIONAL ATLAS',(116,17),role='small',color=MUTED)
            painter.button(self.close_rect,'×',selected=self.pointer is not None and
                           self.close_rect.collidepoint(self.pointer))
            painter.clip(self.map_rect)
            chart = self._chart()
            if chart is not None:
                used_art = chart.draw_terrain(canvas,painter.area(self.map_rect),self.center,self.scale*painter.scale)
                if not used_art:self._draw_terrain(painter)
                chart.draw_routes(canvas,painter.area(self.map_rect),self.center,self.scale*painter.scale,flags=self._flags())
            else:
                self._draw_terrain(painter)
                self._draw_roads_walls(painter)
            self._draw_farmsteads(painter)
            self._layout_markers()
            self._layout_labels(painter)
            for index,record in enumerate(self.landmarks):
                if not self.marker_rects[record['id']].width:continue
                if (self.details_visible and index == self.selected) or index == self.hovered:
                    point = self.tile_to_map(record['tile_position'])
                    self._circle(painter,'#ead390',point,self._marker_size(record)/2+4,2)
                    self._circle(painter,'#6f5734',point,self._marker_size(record)/2+5,.7)
                self._draw_marker(painter,record)
            self._draw_labels(painter)
            self._player_symbol(painter,self.world_to_map(self.game.player.position),
                                getattr(self.game.player,'facing','front'))
            painter.text('N',(self.map_rect.right-15,self.map_rect.top+6),role='small',color=INK,anchor='midtop',bold=True)
            x = self.map_rect.right-15;y = self.map_rect.top+27
            self._polygon(painter,'#eee4c5',((x,y-8),(x-4,y+4),(x,y+1),(x+4,y+4)))
            painter.line(INK,(x,y-8),(x-4,y+4),1)
            painter.line(INK,(x,y-8),(x+4,y+4),1)
            painter.clip(None)
            painter.rect(BRASS,self.map_rect,1)
            self._draw_details(painter)
            self._draw_legend(painter)
            hints = ('Scroll zoom · Drag pan · Arrows places · M / Esc close',
                     'Wheel zoom · Drag pan · Arrows select · M close',
                     'Wheel zoom · Drag pan · M / Esc close')
            available = self.fit_rect.left-28
            hint = next((line for line in hints if painter.font('hint').size(line)[0]<=available),hints[-1])
            painter.text(hint,(20,self._hint_y),role='hint',color=MUTED)
            painter.button(self.fit_rect,'Fit',selected=self.pointer is not None and
                           self.fit_rect.collidepoint(self.pointer))
        finally:canvas.set_clip(old_clip)
