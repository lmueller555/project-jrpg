"""Disposable full gameplay, with host-owned display and playtest controls."""
from __future__ import annotations

import math
import pygame

from quest_playtest import prepare_quest
from save_library import SaveLibrary
from ui_style import BRASS, FOREST_DARK, GOLD, MUTED


class QuestPlaytestSession:
    def __init__(self, parent, entry):
        from main import Game
        self.parent = parent
        self.entry = entry
        self.game = None
        self.closed = False
        self.back_rect = pygame.Rect(0, 5, 120, 25)
        self.restart_rect = pygame.Rect(0, 5, 140, 25)
        self.bar_rect = pygame.Rect(0, 0, 640, 40)
        self.viewport_rect = pygame.Rect(0, 0, 1, 1)
        self._surface = None
        self._layout()
        parent.music.stop()
        parent.opening_audio.reset()
        parent.regional_audio.reset()
        ready = False
        try:
            self.game = Game(fullscreen=parent.fullscreen, start_on_title=False,
                             _preview_window=self._surface, _preview_settings=parent.audio,
                             _quest_playtest=True)
            self.game._music_focused = parent._music_focused
            self.game._display_owner = parent
            self._layout()
            prepare_quest(self.game, entry.id)
            checkpoint = parent.save_store.path
            if checkpoint is not None:
                checkpoint = checkpoint.parent/'playtests'/entry.id/'checkpoint.json'
            self.game.saves.library = SaveLibrary(checkpoint)
            self.game.saves.begin()
            self.game.music.set_paused(not parent._music_focused)
            ready = True
        finally:
            if not ready:
                self.close()

    def _painter(self):
        width, height = self.parent.window.get_size()
        style = self.game.ui if self.game is not None else self.parent.ui
        return style.painter(self.parent.window, (640, height*640/width))

    def _layout(self):
        painter = self._painter()
        font = painter.font('body', bold=True)
        height = max(25, font.get_height()+10)
        self.back_rect.size = (font.size('Quests (F9)')[0]+22, height)
        self.back_rect.right = 632
        self.restart_rect.size = (font.size('Restart (F10)')[0]+22, height)
        self.restart_rect.right = self.back_rect.left-8
        self.bar_rect.height = max(height+10, 16+2*painter.font('small').get_linesize())
        width, height = self.parent.window.get_size()
        top = math.ceil(painter.area(self.bar_rect).bottom+1)
        self.viewport_rect = pygame.Rect(0, top, width, max(1, height-top))
        if self._surface is None or self._surface.get_size() != self.viewport_rect.size:
            self._surface = pygame.Surface(self.viewport_rect.size)
        if self.game is not None:
            self.game.window = self._surface
            self.game._input_offset = self.viewport_rect.topleft
            self.game._ensure_ui_surface()
        return painter

    def handle_events(self, events):
        if self.closed:
            return True
        painter = self._layout()
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
            if event.type == pygame.VIDEORESIZE and not self.parent.fullscreen:
                self.parent.window = pygame.display.set_mode(
                    (max(480, event.w), max(320, event.h)), pygame.RESIZABLE)
                self.parent._ensure_ui_surface()
                painter = self._layout()
                continue
            if event.type == pygame.KEYDOWN:
                if getattr(event, 'repeat', False):
                    if event.key in (pygame.K_F9, pygame.K_F10, pygame.K_F11):
                        continue
                elif event.key == pygame.K_F11:
                    self.parent.toggle_fullscreen()
                    self.game.fullscreen = self.parent.fullscreen
                    painter = self._layout()
                    continue
                elif self.parent._music_focused and event.key == pygame.K_F9:
                    self.close()
                    return True
                elif self.parent._music_focused and event.key == pygame.K_F10:
                    self.restart()
                    return True
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                point = tuple((value-painter.offset[index])/painter.scale
                              for index, value in enumerate(event.pos))
                if self.bar_rect.collidepoint(point):
                    if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                            and self.parent._music_focused):
                        if self.back_rect.collidepoint(point):
                            self.close()
                            return True
                        if self.restart_rect.collidepoint(point):
                            self.restart()
                            return True
                    if event.type != pygame.MOUSEBUTTONUP:
                        continue
            forwarded.append(event)
        running = self.game.handle_events(forwarded)
        if not running:
            self.close(resume_music=False)
            self.parent.music.stop()
            return False
        self._layout()
        request = self.game._playtest_request
        if request == 'restart':
            self.restart()
        elif request == 'quests':
            self.close()
        return True

    def update(self, seconds, direction=None, running=None):
        if self.closed or not self.parent._music_focused:
            return
        self.game.update(seconds, direction, running)
        self._layout()

    def draw(self):
        if self.closed:
            return
        painter = self._layout()
        self.game.draw()
        self.parent.window.fill(FOREST_DARK)
        self.parent.window.blit(self._surface, self.viewport_rect)
        painter.rect(FOREST_DARK, self.bar_rect)
        painter.line(BRASS, (0, self.bar_rect.bottom), (640, self.bar_rect.bottom))
        painter.button(self.restart_rect, 'Restart (F10)')
        painter.button(self.back_rect, 'Quests (F9)')
        width = self.restart_rect.left-20
        for index, text in enumerate((f'PLAYTEST - {self.entry.id} - separate saves', self.entry.name)):
            lines = painter.wrap(text, width, role='small', bold=index == 0)
            line = lines[0] if lines else ''
            painter.text(line, (8, 5+index*painter.font('small').get_linesize()),
                         role='small', color=GOLD if index == 0 else MUTED, bold=index == 0)
        pygame.display.flip()

    def restart(self):
        if self.closed:
            return False
        identifier = self.entry.id
        self.close()
        return self.parent.launch_quest_playtest(identifier)

    def fail(self, error):
        self.close()
        self.parent.quest_playtest_menu.error = f'This playtest could not continue: {error}'

    def close(self, *, resume_music=True):
        if self.closed:
            return
        self.closed = True
        if self.game is not None:
            game = self.game
            game.regional_audio.reset()
            game.opening_audio.reset()
            game.regent_arrival.reset()
            game.opening_cinematic.reset()
            game.mill_gift.reset()
            game.elemental_bosses.stop_audio()
            game.combat.reset()
            game.music.stop()
            for sound in game.ui._sounds.values():
                sound.stop()
            game.social.clear_pointer()
            game._mouse_held = False
            game._playtest_request = None
            game._display_owner = None
        if self.parent.quest_playtest_session is self:
            self.parent.quest_playtest_session = None
        self.parent.on_quest_playtest = True
        if self.parent.quest_playtest_menu is not None:
            self.parent.quest_playtest_menu.resume()
        self.parent.title._mouse_held = False
        self.parent.title._pressed = None
        if resume_music:
            self.parent.music.set_paused(not self.parent._music_focused)
            self.parent.music.set_ducked(False)
            self.parent.music.play('title', fade_ms=250)
