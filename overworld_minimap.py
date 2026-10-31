"""A local, north-up chart sharing the regional atlas's illustrated tiles.

The widget uses logical HUD coordinates, while terrain and symbols render at
the actual display resolution. It never asks the gameplay world to render an
overview and keeps no second terrain cache.
"""
from __future__ import annotations

import pygame


FRAME = pygame.Rect(364, 230, 104, 78)
TILES_ACROSS = 80


class OverworldMinimap:
    def __init__(self, game):
        self.game = game
        self.marker_rects = {}

    @property
    def rect(self):
        return FRAME.copy()

    @property
    def content_rect(self):
        return self.rect.inflate(-6, -6)

    @property
    def visible(self):
        g = self.game
        if (not getattr(getattr(g, 'world', None), 'is_overworld', False)
                or getattr(g, 'on_title', False) or getattr(g, 'map_open', False)
                or getattr(g, 'household_action', None)):
            return False
        for owner, flag in (
                ('pause', 'is_open'), ('inventory_ui', 'is_open'),
                ('status_ui', 'is_open'), ('lattice_ui', 'is_open'),
                ('quest_ui', 'journal_open'), ('world_map_viewer', 'is_open'),
                ('opening_cinematic', 'active'), ('combat', 'active'),
                ('social', 'locked'), ('social', 'active'), ('opening', 'locks_player'),
                ('opening', 'controls_player'), ('opening', 'in_action'),
                ('mill_quest', 'encounter_cutscene_active')):
            if getattr(getattr(g, owner, None), flag, False):
                return False
        # Notices can grow into the lower HUD when accessibility text is large.
        return getattr(getattr(g, 'quest_ui', None), 'current_notice', None) is None

    @property
    def data(self):
        world = self.game.world
        return getattr(world, 'region', None) or world.data

    @property
    def tile_size(self):
        return self.data.get('tile_size', 24)

    @property
    def center_tiles(self):
        return pygame.Vector2(self.game.player.position) / self.tile_size

    @property
    def scale(self):
        return self.content_rect.width / TILES_ACROSS

    def tile_to_map(self, position):
        return (pygame.Vector2(self.content_rect.center)
                + (pygame.Vector2(position)-self.center_tiles)*self.scale)

    def world_to_map(self, position):
        return self.tile_to_map(pygame.Vector2(position)/self.tile_size)

    def cartography(self):
        from regional_cartography import get_cartography
        return get_cartography(self.game)

    def _places(self):
        records = []
        if self.data.get('town'):
            records.append(dict(self.data['town'], kind='town'))
        if self.data.get('bridge'):
            records.append(dict(self.data['bridge'], kind='bridge'))
        records.extend(dict(gate, kind='checkpoint') for gate in self.data.get('gates', []))
        discovered = getattr(getattr(self.game, 'overworld_travel', None), 'discovered', set())
        records.extend(record for record in self.data.get('landmarks', [])
                       if record.get('id') in discovered)
        return records

    def _icon_key(self, record):
        flags = getattr(getattr(self.game, 'social', None), 'flags', set())
        kind = record.get('kind')
        if kind == 'bridge':
            return 'bridge_repaired' if record.get('repair_flag') in flags else 'bridge_broken'
        if kind == 'checkpoint':
            opened = (record.get('destination_ready', False)
                      and record.get('clearance_flag') in flags)
            return 'gate_open' if opened else 'gate_closed'
        return {'town': 'town', 'millrace': 'millrace', 'staging': 'relief',
                'overlook': 'overlook'}.get(kind, 'overlook')

    def _draw_place(self, target, painter, chart, record):
        logical = self.tile_to_map(record['tile_position'])
        if not self.content_rect.inflate(8, 8).collidepoint(logical):
            return
        point = painter.point(logical)
        kind = record.get('kind')
        size = max(9, round((7 if kind in ('town', 'bridge', 'checkpoint') else 5)*painter.scale))
        icon = chart.icon(self._icon_key(record), size)
        if icon is not None:
            rect = icon.get_rect(center=point)
            target.blit(icon, rect)
        else:
            # Small compatible fixtures and an unavailable art pack still have
            # a readable landmark, without any world-sized fallback image.
            radius = max(2, round(2*painter.scale))
            pygame.draw.circle(target, '#f3e6bb', point, radius+1)
            pygame.draw.circle(target, '#485e49', point, radius)
            rect = pygame.Rect(point[0]-radius, point[1]-radius, radius*2+1, radius*2+1)
        self.marker_rects[record.get('id', self._icon_key(record))] = rect

    def _draw_player(self, target, painter):
        center = pygame.Vector2(painter.point(self.content_rect.center))
        direction = pygame.Vector2({'front': (0, 1), 'back': (0, -1),
                                   'left': (-1, 0), 'right': (1, 0)}
                                  .get(getattr(self.game.player, 'facing', 'front'), (0, 1)))
        side = pygame.Vector2(-direction.y, direction.x)
        size = max(4, painter.scale*3.6)
        points = [center+direction*size*1.25,
                  center-direction*size*.8+side*size*.78,
                  center-direction*size*.32,
                  center-direction*size*.8-side*size*.78]
        halo = max(6, round(size*1.45))
        pygame.draw.circle(target, '#16382c', center, halo)
        pygame.draw.polygon(target, '#fff3ce', points)
        pygame.draw.polygon(target, '#513f22', points, max(1, round(painter.scale*.7)))
        pygame.draw.circle(target, '#efc66c', center, max(1, round(painter.scale)))

    def draw(self, target):
        self.marker_rects.clear()
        if not self.visible:
            return
        painter = self.game.ui.painter(target)
        frame = self.rect
        painter.rect('#0c241d', frame.move(1, 2))
        painter.rect('#1c3a32', frame)
        content = painter.area(self.content_rect)
        clip = target.get_clip()
        try:
            target.set_clip(content.clip(clip))
            chart = self.cartography()
            chart.draw_terrain(target, content, self.center_tiles, self.scale*painter.scale)
            flags = getattr(getattr(self.game, 'social', None), 'flags', set())
            chart.draw_routes(target, content, self.center_tiles, self.scale*painter.scale,
                              flags=flags)
            for record in self._places():
                self._draw_place(target, painter, chart, record)
            self._draw_player(target, painter)
            # Only north is labelled; local places use the same atlas symbols.
            badge = pygame.Rect(self.content_rect.right-11, self.content_rect.top+1, 10, 11)
            painter.rect('#1c3a32', badge)
            painter.text('N', badge.center, role='hint', color='#f6e8bc',
                         anchor='center', bold=True)
        finally:
            target.set_clip(clip)
        painter.rect('#b59d66', frame, 1)
        painter.rect('#647753', frame.inflate(-4, -4), 1)

    def handle_event(self, event):
        if (not self.visible or event.type != pygame.MOUSEBUTTONDOWN
                or event.button != 1 or getattr(self.game, '_mouse_held', False)):
            return False
        point = self.game.to_canvas(event.pos)
        if point is None or not self.rect.collidepoint(point):
            return False
        self.game.social.clear_pointer()
        self.game._mouse_held = False
        self.game.map_open = True
        self.game.map_ui.reset()
        self.game.ui.sound('confirm')
        return True
