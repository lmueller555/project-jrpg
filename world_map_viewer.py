"""Inspect Auratia's classroom map without reducing its art to world resolution."""
from __future__ import annotations

import math
from pathlib import Path

import pygame

from ui_style import BRASS, FOREST_DARK, IVORY, MUTED


ROOT = Path(__file__).resolve().parent
MAP_IMAGE = ROOT/'assets/world/auratia/world_map.png'


class WorldMapViewer:
    """A modal, display-resolution physical atlas with bounded pan and zoom.

    Camera coordinates refer to original image pixels. Only the visible crop is
    scaled, so zooming on a large display never allocates a whole enlarged atlas.
    The caller owns pausing the world and routing events while ``is_open``.
    """

    MAX_ZOOM = 6.0

    def __init__(self, game, image_path=None):
        self.game = game
        self.image_path = Path(image_path) if image_path is not None else MAP_IMAGE
        self.is_open = False
        self.image = None
        self.zoom = 1.0
        self.center = pygame.Vector2()
        self.viewport = pygame.Rect(8, 38, 464, 250)
        self.close_rect = pygame.Rect(416, 6, 56, 26)
        self.fit_rect = pygame.Rect(420, 292, 52, 22)
        self._drag = None
        self._pointer = None
        self._cached_key = None
        self._cached_crop = None
        self._hint_lines = []

    @property
    def fit_scale(self):
        if self.image is None:return 1.0
        width, height = self.image.get_size()
        return min(self.viewport.width/width, self.viewport.height/height)

    @property
    def scale(self):
        return self.fit_scale*self.zoom

    @property
    def image_rect(self):
        """The image's current logical footprint, before viewport clipping."""
        if self.image is None:return pygame.Rect(0, 0, 0, 0)
        width, height = self.image.get_size()
        scale = self.scale
        return pygame.Rect(round(self.viewport.centerx-self.center.x*scale),
                           round(self.viewport.centery-self.center.y*scale),
                           round(width*scale), round(height*scale))

    def _sound(self, kind):
        self.game.ui.sound(kind)

    def _layout(self, target):
        painter = self.game.ui.painter(target)
        header = max(34, painter.font('heading').get_linesize()+14)
        self._hint_lines = painter.wrap('Scroll to zoom · Drag to explore · Esc / E to close',
                                        396, role='small')
        line_height = painter.font('small').get_linesize()
        footer = max(30, len(self._hint_lines)*line_height+12)
        self.close_rect = pygame.Rect(416, 6, 56, header-12)
        self.fit_rect = pygame.Rect(420, 320-footer+(footer-22)//2, 52, 22)
        viewport = pygame.Rect(8, header+3, 464, max(40, 320-header-footer-6))
        if viewport != self.viewport:
            self.viewport = viewport
            self._clamp()
        return painter, header, footer, line_height

    def open(self):
        if self.image is None:
            self.image = pygame.image.load(str(self.image_path)).convert()
        target = getattr(self.game, 'ui_surface', None)
        if target is not None:self._layout(target)
        self.is_open = True
        self.reset()
        self._sound('confirm')

    def reset(self):
        self.zoom = 1.0
        self.center.update(pygame.Vector2(self.image.get_size())/2)
        self._drag = None
        self._pointer = None
        self._cached_key = None
        self._cached_crop = None
        self._clamp()

    def close(self):
        if not self.is_open:return
        self.is_open = False
        self._drag = None
        self._pointer = None
        self._sound('back')

    def _clamp(self):
        if self.image is None:return
        for axis, extent in enumerate(self.image.get_size()):
            half = self.viewport.size[axis]/(2*self.scale)
            self.center[axis] = (extent/2 if half*2 >= extent else
                                 max(half, min(extent-half, self.center[axis])))

    def image_point(self, point):
        """Original-art coordinate under a logical pointer position."""
        return self.center+(pygame.Vector2(point)-self.viewport.center)/self.scale

    def zoom_at(self, point, steps):
        if not self.viewport.collidepoint(point):return
        before = self.image_point(point)
        self.zoom = max(1.0, min(self.MAX_ZOOM, self.zoom*1.25**max(-20, min(20, steps))))
        self.center.update(before-(pygame.Vector2(point)-self.viewport.center)/self.scale)
        self._clamp()

    def _point(self, event):
        position = getattr(event, 'pos', pygame.mouse.get_pos())
        return self.game.to_canvas(position)

    def handle_event(self, event):
        if not self.is_open:return False
        if event.type == pygame.WINDOWFOCUSLOST:
            self._drag = None
        elif event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key in (pygame.K_ESCAPE, pygame.K_e):self.close()
        elif event.type == pygame.MOUSEWHEEL:
            point = self._point(event)
            if point is not None:self.zoom_at(point, getattr(event, 'precise_y', event.y))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            point = self._point(event)
            if point is not None:
                if event.button == 1:
                    if self.close_rect.collidepoint(point):self.close()
                    elif self.fit_rect.collidepoint(point):
                        self.reset()
                        self._sound('move')
                    elif self.viewport.collidepoint(point):self._drag = pygame.Vector2(point)
                elif event.button in (4, 5):self.zoom_at(point, 1 if event.button == 4 else -1)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = None
        elif event.type == pygame.MOUSEMOTION:
            point = self._point(event)
            self._pointer = point
            if self._drag is not None:
                if point is None:self._drag = None
                else:
                    delta = pygame.Vector2(point)-self._drag
                    self.center -= delta/self.scale
                    self._drag.update(point)
                    self._clamp()
        return True

    def _draw_image(self, target, painter):
        viewport = painter.area(self.viewport)
        scale = self.scale*painter.scale
        middle = pygame.Vector2(painter.point(self.viewport.center))
        half = pygame.Vector2(viewport.size)/(2*scale)
        start = self.center-half
        end = self.center+half
        size = self.image.get_size()
        left, top = max(0, math.floor(start.x)), max(0, math.floor(start.y))
        right, bottom = min(size[0], math.ceil(end.x)), min(size[1], math.ceil(end.y))
        source = pygame.Rect(left, top, right-left, bottom-top)
        if source.width <= 0 or source.height <= 0:return
        scaled_size = (max(1, round(source.width*scale)), max(1, round(source.height*scale)))
        key = tuple(source), scaled_size
        if key != self._cached_key:
            self._cached_crop = pygame.transform.scale(self.image.subsurface(source), scaled_size)
            self._cached_key = key
        position = middle+(pygame.Vector2(source.topleft)-self.center)*scale
        previous_clip = target.get_clip()
        target.set_clip(viewport.clip(previous_clip))
        try:target.blit(self._cached_crop, (round(position.x), round(position.y)))
        finally:target.set_clip(previous_clip)

    def draw(self, target):
        if not self.is_open:return
        painter, header, footer, line_height = self._layout(target)
        target.fill(FOREST_DARK)
        painter.text('World map', (10, header/2), role='heading', anchor='midleft', color=IVORY)
        painter.line(BRASS, (8, header), (472, header))
        self._draw_image(target, painter)
        painter.button(self.close_rect, 'Close',
                       selected=self._pointer is not None and self.close_rect.collidepoint(self._pointer))
        painter.button(self.fit_rect, 'Fit',
                       selected=self._pointer is not None and self.fit_rect.collidepoint(self._pointer))
        for index, line in enumerate(self._hint_lines):
            painter.text(line, (8, 320-footer+6+index*line_height), role='small', color=MUTED)
