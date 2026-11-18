"""A frozen cave approach, followed by a genuinely presented loading frame.

This presentation owns no combat or encounter randomness. The encounter owner
loads its already-selected combatants only after ``ready_to_load`` becomes
true, which requires drawing the loading screen on a previous frame.
"""
from __future__ import annotations

import math

import pygame

from ui_style import GOLD, IVORY


class CaveBattleEntry:
    tutorial_active = False

    def __init__(self, world_frame, focus, location, *, reduced_motion=False):
        self.world_frame = world_frame.copy()
        self.focus = pygame.Vector2(focus)
        self.location = str(location)
        self.reduced_motion = bool(reduced_motion)
        self.elapsed = 0.
        self.duration = .35 if self.reduced_motion else .8
        self.phase = 'cutscene'
        self.paused = False
        self.focused = True
        self.loading_presented = False
        self.retry_requested = False
        self.error = ''
        self._held = False
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.retry_rect = pygame.Rect(172, 226, 136, 29)

    @property
    def ready_to_load(self):
        return (self.phase == 'loading' and self.loading_presented
                and not self.paused and self.focused and not self.error)

    def set_error(self, message):
        self.error = str(message)
        self.retry_requested = False

    def clear_error(self):
        self.error = ''
        self.retry_requested = False

    def update(self, seconds):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid cave entry clock')
        if self.paused or not self.focused or self.error:return
        if self.phase == 'cutscene':
            self.elapsed = min(self.duration, self.elapsed+seconds)
            if self.elapsed >= self.duration:self.phase = 'loading'

    def handle_event(self, game, event):
        point = game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False;self.paused = True;self._held = False
        elif event.type == pygame.WINDOWFOCUSGAINED:self.focused = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:self._held = False
        elif event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE and self.focused:
                self.paused = not self.paused
            elif (self.error and self.focused and not self.paused
                  and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)):
                self.retry_requested = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if self.paused and self.focused and point is not None and self.resume_rect.collidepoint(point):
                self.paused = False
            elif self.error and self.focused and point is not None and self.retry_rect.collidepoint(point):
                self.retry_requested = True
        return True

    def draw(self, game, canvas, ui_surface):
        if self.phase == 'cutscene':
            progress = min(1., self.elapsed/self.duration)
            if self.reduced_motion:
                canvas.blit(self.world_frame, (0, 0))
            else:
                # A gentle push toward the actual party, not a flashing screen
                # or an invented encounter actor pasted into the cave.
                zoom = 1+.035*math.sin(progress*math.pi)
                size = tuple(round(n*zoom) for n in self.world_frame.get_size())
                image = pygame.transform.scale(self.world_frame, size)
                origin = self.focus*(1-zoom)
                origin.x = max(canvas.get_width()-size[0], min(0, origin.x))
                origin.y = max(canvas.get_height()-size[1], min(0, origin.y))
                canvas.blit(image, (round(origin.x), round(origin.y)))
            pygame.transform.scale(canvas, ui_surface.get_size(), ui_surface)
            painter = game.ui.painter(ui_surface)
            if not self.reduced_motion and .15 < progress < .75:
                painter.text('!', (self.focus.x, max(16, self.focus.y-42)),
                             role='heading', color=GOLD, anchor='center', bold=True)
            painter.veil(round(255*max(0., (progress-.65)/.35)))
        else:
            canvas.fill('#071211');ui_surface.fill('#071211')
            painter = game.ui.painter(ui_surface)
            painter.text('Loading battle…', (240, 144), role='heading', color=GOLD,
                         anchor='center', bold=True)
            painter.text(self.location, (240, 172), role='small', color=IVORY, anchor='center')
            # One honest loading frame must reach the draw path before any
            # model, sprite bank or cave battlefield is constructed.
            self.loading_presented = True
        painter = game.ui.painter(ui_surface)
        if self.error:
            painter.veil(170)
            painter.panel((88, 94, 304, 168))
            for index, line in enumerate(painter.wrap(self.error, 274, role='small')):
                painter.text(line, (103, 112+index*painter.font('small').get_linesize()),
                             role='small', color=IVORY)
            painter.button(self.retry_rect, 'Retry')
        if self.paused:
            painter.veil(150)
            painter.panel((124, 111, 232, 100))
            painter.text('Battle paused', (240, 126), color=GOLD, anchor='midtop', bold=True)
            painter.button(self.resume_rect, 'Resume', disabled=not self.focused)
        painter.clip()
