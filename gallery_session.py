"""A disposable game runtime for each Gallery playback.

The title's world, save store, loaded journey and settings never enter this
runtime. It shares only the display, and takes a read-only snapshot of settings.
"""
from __future__ import annotations

import math
import pygame

from ui_style import FOREST_DARK, BRASS, GOLD, MUTED


class GallerySession:
    def __init__(self, parent, entry):
        from main import Game
        self.parent = parent
        self.entry = entry
        self.game = None
        self.playback = None
        self.closed = False
        self.back_rect = pygame.Rect(482, 5, 150, 24)
        self.restart_rect = pygame.Rect(366, 5, 108, 24)
        self.bar_rect = pygame.Rect(0, 0, 640, 34)
        self.viewport_rect = pygame.Rect(0,0,1,1)
        self._preview_surface = None
        self._layout()
        parent.music.stop()
        parent.opening_audio.reset()
        parent.regional_audio.reset()
        try:
            self.game = Game(window_size=parent.window.get_size(), fullscreen=parent.fullscreen,
                             start_on_title=False, _preview_window=self._preview_surface,
                             _preview_settings=parent.audio)
            self.game._music_focused = parent._music_focused
            self.playback = entry.start(self.game)
            self.game.music.set_paused(not parent._music_focused)
        except Exception:
            # A missing optional scene asset must not strand the soundtrack or
            # leak a half-created runtime into Continue.
            self.close()
            raise

    def _point(self, position):
        painter = self._painter()
        return tuple((value-painter.offset[index])/painter.scale
                     for index, value in enumerate(position))

    def _painter(self):
        width,height = self.parent.window.get_size()
        return self.parent.ui.painter(self.parent.window, (640,height*640/width))

    def _layout(self):
        painter = self._painter()
        height = max(24, painter.font('small').get_height()+10)
        self.back_rect.height = self.restart_rect.height = height
        self.bar_rect.height = max(height+10,16+2*painter.font('small').get_linesize())
        width,height = self.parent.window.get_size()
        top = math.ceil(painter.area(self.bar_rect).bottom+1)
        self.viewport_rect = pygame.Rect(0,top,width,max(1,height-top))
        if self._preview_surface is None or self._preview_surface.get_size() != self.viewport_rect.size:
            self._preview_surface = pygame.Surface(self.viewport_rect.size)
        if self.game is not None:
            self.game.window = self._preview_surface
            self.game._ensure_ui_surface()
        return painter

    def handle_events(self, events):
        if self.closed:return True
        self._layout()
        forwarded = []
        for event in events:
            if event.type == pygame.QUIT:
                self.close(resume_music=False)
                self.parent.music.stop()
                return False
            if event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED):
                self.parent._music_focused = event.type == pygame.WINDOWFOCUSGAINED
                forwarded.append(event)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11 and not getattr(event, 'repeat', False):
                    self.parent.toggle_fullscreen()
                    self.game.fullscreen = self.parent.fullscreen
                    self._layout()
                    continue
                if getattr(event, 'repeat', False):continue
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.close()
                    return True  # discard the release/repeat tail of this batch
                if not self.parent._music_focused:continue
                if event.key == pygame.K_r:
                    self.restart()
                    return True
                cinematic = self.game.opening_cinematic.active or self.game.regent_arrival.active
                if event.key == pygame.K_p and cinematic:
                    forwarded.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
                elif event.key in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if cinematic or self.game.social.active:
                        # All preview confirms are dialogue-only. A second E in
                        # this batch must not become a world interaction when
                        # the first E closes the final page and runs its callback.
                        forwarded.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=False))
                continue
            if event.type == pygame.VIDEORESIZE and not self.parent.fullscreen:
                self.parent.window = pygame.display.set_mode((max(480,event.w),max(320,event.h)),pygame.RESIZABLE)
                self.parent._ensure_ui_surface()
                self._layout()
                continue
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                if event.type != pygame.MOUSEMOTION and event.button != 1:continue
                if not self.parent._music_focused and event.type != pygame.MOUSEBUTTONUP:continue
                point = self._point(event.pos)
                if self.bar_rect.collidepoint(point):
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.back_rect.collidepoint(point):
                            self.close();return True
                        if self.restart_rect.collidepoint(point):
                            self.restart();return True
                    # Release must clear a scene press even if the cursor moved
                    # into the toolbar since the initial click.
                    if event.type != pygame.MOUSEBUTTONUP:continue
                if (self.game.opening_cinematic.active or self.game.regent_arrival.active
                        or self.game.social.active or event.type == pygame.MOUSEBUTTONUP):
                    forwarded.append(pygame.event.Event(event.type,dict(event.dict,
                        pos=(event.pos[0]-self.viewport_rect.x,event.pos[1]-self.viewport_rect.y))))
        self.game.handle_events(forwarded)
        if not self.parent._music_focused:
            self.game.music.set_paused(True)
            self.game.opening_audio.set_paused(True)
            self.game.regional_audio.stop()
        if self.parent._music_focused:self.playback.update(0)
        return True

    def update(self, seconds):
        if self.closed:return
        if not self.parent._music_focused:return
        if not self.playback.settling:
            self.game.update(seconds, (0, 0), False)
        self.playback.update(seconds)
        if self.playback.finished:self.close()

    def draw(self):
        if self.closed:return
        painter = self._layout()
        self.game.draw()
        self.parent.window.fill(FOREST_DARK)
        self.parent.window.blit(self.game.window,self.viewport_rect)
        painter.rect(FOREST_DARK, self.bar_rect)
        painter.line(BRASS, (0,self.bar_rect.bottom), (640,self.bar_rect.bottom))
        painter.button(self.restart_rect, 'Restart · R')
        painter.button(self.back_rect, 'Gallery · Esc')
        label = self.entry.name
        while label and painter.font('small', bold=True).size(label)[0] > 342:
            label = label[:-2].rstrip()+'…'
        painter.text(label, (10,6), role='small', color=GOLD, bold=True)
        hint = self.entry.controls.replace(' · Esc: Gallery', '')
        while hint and painter.font('small').size(hint)[0] > 342:
            hint = hint[:-2].rstrip()+'…'
        painter.text(hint, (10,8+painter.font('small').get_linesize()), role='small', color=MUTED)
        pygame.display.flip()

    def restart(self):
        if self.closed:return False
        entry_id = self.entry.id
        self.close()
        return self.parent.launch_gallery_scene(entry_id)

    def fail(self, error):
        """Recover expected missing/corrupt asset failures, including lazy loads."""
        self.close()
        self.parent.gallery.error=f'This scene could not play: {error}'

    def close(self, *, resume_music=True):
        if self.closed:return
        self.closed = True
        game = self.game
        if game is not None:
            game.regional_audio.reset()
            game.opening_audio.reset()
            game.regent_arrival.reset()
            game.opening_cinematic.reset()
            game.combat.reset()
            game.music.stop()
            # UI ticks are short, but they too belong to this discarded runtime.
            for sound in game.ui._sounds.values():sound.stop()
            game.social.clear_pointer()
            game._mouse_held = False
        if self.parent.gallery_session is self:self.parent.gallery_session = None
        self.parent.on_gallery = True
        if self.parent.gallery is not None:self.parent.gallery.resume()
        self.parent.title._mouse_held = False
        self.parent.title._pressed = None
        if resume_music:
            self.parent.music.set_paused(not self.parent._music_focused)
            self.parent.music.set_ducked(False)
            self.parent.music.play('eldenmere', fade_ms=250)
