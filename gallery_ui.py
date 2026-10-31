"""Scrollable, display-resolution catalogue for isolated cutscene previews."""
from __future__ import annotations

import math
from pathlib import Path

import pygame

from ui_style import BRASS, FOREST, FOREST_DARK, FOREST_LIGHT, GOLD, IVORY, MUTED

ROOT = Path(__file__).resolve().parent
SIZE = (640, 360)


class GalleryUI:
    """Metadata-only browsing; scene worlds are created only when Play is chosen."""

    def __init__(self, game, entries=None):
        if entries is None:
            from cutscene_gallery import GALLERY_ENTRIES
            entries = GALLERY_ENTRIES
        self.game = game
        self.entries = tuple(entries)
        self.selected = 0
        self.scroll = 0
        self.max_scroll = 0
        self.rows = []
        self.viewport = pygame.Rect(36, 86, 556, 214)
        self.panel = pygame.Rect(20, 14, 600, 332)
        self.back_rect = pygame.Rect(502, 27, 100, 26)
        self.play_rect = pygame.Rect(482, 310, 118, 24)
        self._thumbnails = {}
        self._frame = None
        self._layout_key = None
        self._focus_pending = True
        self._mouse_held = False
        self.error = None
        self._error_back = pygame.Rect(215, 230, 210, 29)

    @property
    def selected_entry(self):
        return self.entries[self.selected] if self.entries else None

    def resume(self):
        """Clear press ownership without disturbing catalogue position."""
        self._mouse_held = False

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = min(width/SIZE[0], height/SIZE[1])
        return pygame.Vector2((point[0]-(width-SIZE[0]*scale)/2)/scale,
                              (point[1]-(height-SIZE[1]*scale)/2)/scale)

    def _painter(self):
        size = self.game.window.get_size()
        if self._frame is None or self._frame.get_size() != size:
            self._frame = pygame.Surface(size).convert()
        return self.game.ui.painter(self._frame, SIZE)

    def layout(self, painter):
        key = (self.game.window.get_size(), getattr(self.game.audio, 'text_scale', 1), id(self.entries))
        changed = key != self._layout_key
        if changed:
            self._layout_key = key
            self._focus_pending = True
        self.selected = max(0, min(self.selected, len(self.entries)-1))
        small = painter.font('small')
        body = painter.font('body', bold=True)
        heading = painter.font('heading', bold=True)
        self.back_rect.height = max(25, body.get_height()+9)
        self.back_rect.width = max(100, painter.font().size('Back · Esc')[0]+20)
        self.back_rect.right = 602
        header_bottom = 28+max(heading.get_height(), self.back_rect.height)
        self._subtitle = painter.wrap('Replay any scene. Your saved journey stays untouched.', 556, 'small')
        self._subtitle_y = header_bottom+6
        viewport_top = self._subtitle_y+len(self._subtitle)*(small.get_linesize()+1)+12
        self.play_rect.height = max(25, body.get_height()+9)
        self.play_rect.width = max(118, body.size('Play scene')[0]+38)
        self.play_rect.right = 600
        footer_height = max(self.play_rect.height+15, small.get_linesize()*2+18)
        self.play_rect.bottom = self.panel.bottom-12
        self.viewport = pygame.Rect(36, viewport_top, 556, max(64, self.panel.bottom-footer_height-viewport_top))
        self.play_rect.centery = self.viewport.bottom+(self.panel.bottom-self.viewport.bottom)//2
        hint_width = self.play_rect.left-48
        self._footer_hint = next((hint for hint in
                                  ('↑↓ Select · Enter Play · Wheel Scroll', '↑↓ Select · Enter Play', '↑↓ / Enter')
                                  if small.size(hint)[0] <= hint_width), 'Enter')
        if changed:
            self._row_content = []
            offset = 0
            self._starts = []
            self._heights = []
            for entry in self.entries:
                chapter = painter.wrap(entry.chapter, 414, 'small')
                name = painter.wrap(entry.name, 414, 'body', bold=True)
                description = painter.wrap(entry.description, 414, 'small') if entry.description else []
                height = max(84, 20+(len(chapter)+len(description))*(small.get_linesize()+1)
                             +len(name)*(body.get_linesize()+1)+6)
                self._row_content.append((chapter, name, description))
                self._starts.append(offset)
                self._heights.append(height)
                offset += height+7
            self._content_height = max(0, offset-7)
        self.max_scroll = max(0, self._content_height-self.viewport.height)
        self.scroll = max(0, min(self.max_scroll, self.scroll))
        if self.entries and self._focus_pending:
            start = self._starts[self.selected]
            end = start+min(self._heights[self.selected], self.viewport.height)
            self.scroll = max(0, min(self.max_scroll, min(self.scroll, start)))
            self.scroll = max(self.scroll, end-self.viewport.height)
        self._focus_pending = False
        self.rows = [pygame.Rect(self.viewport.left, self.viewport.top+start-self.scroll,
                                 self.viewport.width, height)
                     for start, height in zip(self._starts, self._heights)]

    def _select(self, index, reveal=True):
        if not self.entries:return
        index = max(0, min(len(self.entries)-1, index))
        if self.selected != index:self.game.ui.sound('move')
        self.selected = index
        self._focus_pending = reveal
        self.layout(self._painter())

    def _row_at(self, point):
        if not self.viewport.collidepoint(point):return None
        return next((index for index, row in enumerate(self.rows) if row.collidepoint(point)), None)

    def _scroll(self, distance):
        self.scroll = max(0, min(self.max_scroll, self.scroll+distance))
        self._focus_pending = False
        self.layout(self._painter())

    def activate(self):
        if self.selected_entry is not None:
            self.error = None
            self._mouse_held = False
            self.game.ui.sound('confirm')
            self.game.launch_gallery_scene(self.selected_entry.id)
        return True

    def _back(self):
        self.resume()
        self.game.ui.sound('back')
        self.game.close_gallery()

    def handle_event(self, event):
        self.layout(self._painter())
        if self.error:
            if ((event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False)
                 and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE))
                    or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                        and self._error_back.collidepoint(self.to_canvas(event.pos)))):
                self.error = None
                self.resume()
                self.game.ui.sound('back')
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_held = False
        elif event.type == pygame.MOUSEWHEEL:
            self._scroll(-event.y*64)
        elif event.type == pygame.MOUSEMOTION:
            row = self._row_at(self.to_canvas(event.pos))
            if row is not None:self._select(row, reveal=False)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (4, 5):
                self._scroll(-64 if event.button == 4 else 64)
            elif event.button == 1 and not self._mouse_held:
                self._mouse_held = True
                point = self.to_canvas(event.pos)
                if self.back_rect.collidepoint(point):self._back()
                elif self.play_rect.collidepoint(point):return self.activate()
                else:
                    row = self._row_at(point)
                    if row is not None:
                        self._select(row, reveal=False)
                        return self.activate()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):self._select(self.selected-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):self._select(self.selected+1)
            elif event.key == pygame.K_HOME:self._select(0)
            elif event.key == pygame.K_END:self._select(len(self.entries)-1)
            elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                direction = -1 if event.key == pygame.K_PAGEUP else 1
                count = max(1, self.viewport.height//91)
                self._select(self.selected+direction*count)
            elif not getattr(event, 'repeat', False):
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):self._back()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):return self.activate()
        return True

    def update(self, seconds):
        pass

    def _thumbnail(self, path):
        """Load only visible entries, and cache failures as intentional fallbacks."""
        if path not in self._thumbnails:
            try:
                self._thumbnails[path] = pygame.image.load(str(ROOT/path)).convert()
            except (OSError, ValueError, TypeError, pygame.error):
                self._thumbnails[path] = None
        return self._thumbnails[path]

    def _draw_thumbnail(self, painter, path, rect):
        image = self._thumbnail(path)
        painter.rect(FOREST_DARK, rect)
        if image is not None:
            # Fill the frame with an aspect-preserving, centered crop.
            ratio = rect.width/rect.height
            width, height = image.get_size()
            crop = (pygame.Rect((width-height*ratio)/2, 0, height*ratio, height)
                    if width/height > ratio else
                    pygame.Rect(0, (height-width/ratio)/2, width, width/ratio))
            painter.image(image.subsurface(crop), rect)
        else:
            painter.lantern((rect.centerx, rect.centery-7), color=MUTED, size=18)
            painter.text('Scene preview', (rect.centerx, rect.centery+12), role='small',
                         color=MUTED, anchor='midtop')
        painter.rect(BRASS, rect, 1)

    def draw(self):
        painter = self._painter()
        self.layout(painter)
        background = getattr(getattr(self.game, 'title', None), 'background', None)
        if background is not None:
            width, height = self._frame.get_size()
            scale = max(width/background.get_width(), height/background.get_height())
            size = tuple(math.ceil(value*scale) for value in background.get_size())
            self._frame.blit(pygame.transform.scale(background, size),
                             ((width-size[0])//2, (height-size[1])//2))
        else:self._frame.fill(FOREST_DARK)
        painter.veil(140)
        painter.panel(self.panel)
        painter.lantern((43, 40), size=11)
        painter.text('Gallery', (57, 26), role='heading', color=GOLD, bold=True)
        painter.button(self.back_rect, 'Back · Esc')
        for index, line in enumerate(self._subtitle):
            painter.text(line, (36, self._subtitle_y+index*(painter.font('small').get_linesize()+1)),
                         role='small', color=MUTED)
        painter.line(BRASS, (36, self.viewport.top-7), (604, self.viewport.top-7))
        painter.clip(self.viewport)
        if not self.entries:
            painter.lantern((self.viewport.centerx, self.viewport.centery-22), size=20)
            painter.text('No scenes yet', self.viewport.center, role='heading', anchor='center', bold=True)
            painter.text('New cutscenes will appear here.',
                         (self.viewport.centerx, self.viewport.centery+23), role='small', color=MUTED,
                         anchor='midtop')
        for index, (entry, row) in enumerate(zip(self.entries, self.rows)):
            if not row.colliderect(self.viewport):continue
            selected = index == self.selected
            painter.rect(FOREST_LIGHT if selected else FOREST_DARK, row)
            painter.rect(GOLD if selected else FOREST, row, 1)
            thumb = pygame.Rect(row.left+8, row.top+8, 112, 63)
            self._draw_thumbnail(painter, entry.thumbnail, thumb)
            text_x = row.left+132
            y = row.top+9
            chapter, name, description = self._row_content[index]
            for line in chapter:
                painter.text(line, (text_x, y), role='small', color=MUTED)
                y += painter.font('small').get_linesize()+1
            y += 2
            for line in name:
                painter.text(line, (text_x, y), color=GOLD if selected else IVORY, bold=True)
                y += painter.font('body', bold=True).get_linesize()+1
            y += 3
            for line in description:
                painter.text(line, (text_x, y), role='small', color=MUTED)
                y += painter.font('small').get_linesize()+1
        painter.clip()
        if self.max_scroll:
            track = pygame.Rect(599, self.viewport.top, 4, self.viewport.height)
            thumb_height = max(14, round(track.height*track.height/(track.height+self.max_scroll)))
            offset = round((track.height-thumb_height)*self.scroll/self.max_scroll)
            painter.rect(FOREST_DARK, track)
            painter.rect(BRASS, (track.left, track.top+offset, track.width, thumb_height))
        painter.line(BRASS, (36, self.viewport.bottom+7), (604, self.viewport.bottom+7))
        painter.button(self.play_rect, 'Play scene', selected=bool(self.entries), disabled=not self.entries)
        count = f'{self.selected+1} / {len(self.entries)} scenes' if self.entries else '0 scenes'
        footer_y = self.viewport.bottom+12
        painter.text(count, (36, footer_y), role='small', color=MUTED)
        painter.text(self._footer_hint,
                     (36, footer_y+painter.font('small').get_linesize()+2), role='small', color=IVORY)
        if self.error:
            # The runtime can report a failed adapter without leaving an unusable screen.
            painter.veil(130)
            error_lines = painter.wrap(self.error, 456)
            line_height = painter.font().get_linesize()+1
            max_lines = max(1, (250-painter.font('heading').get_linesize())//line_height)
            if len(error_lines) > max_lines:error_lines = error_lines[:max_lines-1]+['…']
            height = min(320, 90+painter.font('heading').get_height()+len(error_lines)*line_height)
            error = pygame.Rect(72, (360-height)//2, 496, height)
            painter.panel(error)
            painter.text('Scene unavailable', (error.left+20, error.top+13),
                         role='heading', color=GOLD, bold=True)
            text_top = error.top+23+painter.font('heading').get_height()
            for index, line in enumerate(error_lines):
                painter.text(line, (error.left+20, text_top+index*line_height))
            self._error_back = pygame.Rect(0, 0, max(210, painter.font(bold=True).size('Back to Gallery')[0]+38),
                                           max(29, painter.font().get_height()+9))
            self._error_back.midbottom = (error.centerx, error.bottom-12)
            painter.button(self._error_back, 'Back to Gallery', selected=True)
        self.game.window.blit(self._frame, (0, 0))
        pygame.display.flip()
