"""A modal, responsive pause menu that never advances the scene beneath it."""
from __future__ import annotations

import pygame


class PauseMenu:
    def __init__(self, game):
        self.game = game
        self.is_open = False
        self.settings = False
        self.selected = 0
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 15)
        self.heading_font = pygame.font.Font(None, 27)
        self.rows = [pygame.Rect(152, 109+i*34, 176, 28) for i in range(3)]
        self.settings_rows = [pygame.Rect(126, 96+i*34, 228, 28) for i in range(4)]
        self._mouse_held = False

    def open(self):
        self.is_open = True
        self.settings = False
        self.selected = 0
        self._mouse_held = False
        self.game._mouse_held = False
        save = getattr(self.game, 'save_progress', None)
        if save is not None:save()

    def close(self):
        self.is_open = False
        self.settings = False
        self.selected = 0
        self._mouse_held = False
        self.game._mouse_held = False

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = ((point[0]-(width-480*scale)//2)/scale,
                 (point[1]-(height-320*scale)//2)/scale)
        return point if 0 <= point[0] < 480 and 0 <= point[1] < 320 else None

    def _row_at(self, point):
        if point is None:return None
        return next((i for i, row in enumerate(self.settings_rows if self.settings else self.rows)
                     if row.collidepoint(point)), None)

    def _adjust(self, direction):
        if self.selected == 1:
            self.game.audio.set_music(self.game.audio.music_volume+direction*.1)
        elif self.selected == 2:
            self.game.audio.set_effects(self.game.audio.effects_volume+direction*.1)

    def activate(self):
        if self.settings:
            if self.selected == 0:self.game.toggle_fullscreen()
            elif self.selected == 1:self.game.audio.toggle_music()
            elif self.selected == 2:self.game.audio.toggle_effects()
            else:self.settings=False;self.selected=1
        elif self.selected == 0:self.close()
        elif self.selected == 1:self.settings=True;self.selected=0
        elif self.selected == 2:return False
        return True

    def handle_event(self, event):
        if not self.is_open:return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_held = False
        elif event.type == pygame.MOUSEMOTION:
            row = self._row_at(self.to_canvas(event.pos))
            if row is not None:self.selected=row
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._mouse_held:return True
            self._mouse_held=True
            point = self.to_canvas(event.pos)
            row = self._row_at(point)
            if row is not None:
                self.selected = row
                if self.settings and row in (1, 2):
                    rect = self.settings_rows[row]
                    if point[0] < rect.left+27:self._adjust(-1);return True
                    if point[0] >= rect.right-27:self._adjust(1);return True
                return self.activate()
        elif event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:
                if self.settings:self.settings=False;self.selected=1
                else:self.close()
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                direction = -1 if event.key in (pygame.K_UP, pygame.K_w) else 1
                self.selected = (self.selected+direction) % (4 if self.settings else 3)
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                if self.settings:
                    self._adjust(-1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.activate()
        return True

    def draw(self, canvas):
        if not self.is_open:return
        shade = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        shade.fill((10, 20, 18, 205))
        canvas.blit(shade, (0, 0))
        panel = pygame.Rect(108, 55, 264, 228) if self.settings else pygame.Rect(132, 65, 216, 190)
        pygame.draw.rect(canvas, '#101b19', panel.move(3, 3))
        pygame.draw.rect(canvas, '#263c35', panel)
        pygame.draw.rect(canvas, '#b7a47b', panel, 2)
        heading = self.heading_font.render('SETTINGS' if self.settings else 'PAUSED', False, '#ffdc71')
        canvas.blit(heading, heading.get_rect(midtop=(240, panel.top+14)))
        labels = (('Display: '+('Fullscreen' if self.game.fullscreen else 'Windowed'),
                   f'Music: {round(self.game.audio.music_volume*100)}%',
                   f'Effects: {round(self.game.audio.effects_volume*100)}%', 'Back')
                  if self.settings else ('Resume', 'Settings', 'Quit'))
        rows = self.settings_rows if self.settings else self.rows
        for i, (label, row) in enumerate(zip(labels, rows)):
            if i == self.selected:pygame.draw.rect(canvas, '#344e3e', row)
            color = '#ffdc71' if i == self.selected else '#f7eed5'
            rendered = self.font.render(label, False, color)
            canvas.blit(rendered, rendered.get_rect(center=row.center))
            if self.settings and i in (1, 2):
                for symbol, x in (('-', row.left+14), ('+', row.right-14)):
                    rendered = self.font.render(symbol, False, '#ffdc71')
                    canvas.blit(rendered, rendered.get_rect(center=(x, row.centery)))
        hint = 'Left/right or +/-: volume' if self.settings else 'Esc: resume   Arrows + Enter: choose'
        rendered = self.small_font.render(hint, False, '#c9c9b5')
        canvas.blit(rendered, rendered.get_rect(midbottom=(240, panel.bottom-12)))
