"""Play the isolated expanded dungeon asset scene with production movement.

This viewer constructs only World and Player. It does not load or write a
journey, settings, quests or party state, and the live cave remains independent.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from main import Player, World, VIEW_SIZE, camera_for
from sanctuary_cave_world import SanctuaryCaveWorld
from ui_style import UIStyle


MAP_PATH = ROOT/'assets/maps/dungeon_pack_review/map.json'


class DungeonPackDemo:
    """Disposable material review using the game's exact feet and animation."""
    def __init__(self, window_size=(960, 640), reduced_motion=False):
        pygame.display.init();pygame.font.init()
        self.window = pygame.display.set_mode(self._window_size(window_size), pygame.RESIZABLE)
        pygame.display.set_caption('Project JRPG — Dungeon asset pack review')
        self.canvas = pygame.Surface(VIEW_SIZE)
        self.ui_surface = None
        self.ui = UIStyle(self)
        self.reduced_motion = bool(reduced_motion)
        self.show_guide = True
        self.material_view = False
        self.pulse_mode = 0
        self.running = self.focused = True
        self.keys = set()
        self.reset()

    @staticmethod
    def _window_size(size):
        return max(VIEW_SIZE[0], int(size[0])), max(VIEW_SIZE[1], int(size[1]))

    def reset(self):
        cache = self.world._images if hasattr(self, 'world') else None
        self.world = SanctuaryCaveWorld(MAP_PATH, image_cache=cache)
        self.player = Player(self.world)
        self.elapsed_ms = 0.
        self.keys.clear()
        self.world.reduced_motion = self.reduced_motion
        self.camera = camera_for(self.player.position, self.world.size)

    def handle_event(self, event):
        if event.type == pygame.QUIT:self.running = False
        elif event.type == pygame.KEYDOWN:
            self.keys.add(event.key)
            if not getattr(event, 'repeat', False):
                if event.key == pygame.K_ESCAPE:self.running = False
                elif event.key == pygame.K_HOME:self.reset()
                elif event.key == pygame.K_h:self.show_guide = not self.show_guide
                elif event.key == pygame.K_r:self.reduced_motion = not self.reduced_motion
                elif event.key == pygame.K_l:self.material_view = not self.material_view
                elif event.key == pygame.K_SPACE:self.pulse_mode = (self.pulse_mode+1) % 3
        elif event.type == pygame.KEYUP:self.keys.discard(event.key)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.keys.clear();self.focused = False
        elif event.type == pygame.WINDOWFOCUSGAINED:self.focused = True
        elif event.type == pygame.VIDEORESIZE:
            self.window = pygame.display.set_mode(self._window_size((event.w, event.h)), pygame.RESIZABLE)
        return self.running

    def input_direction(self):
        keys = self.keys
        return (int(bool(keys & {pygame.K_d, pygame.K_RIGHT}))-int(bool(keys & {pygame.K_a, pygame.K_LEFT})),
                int(bool(keys & {pygame.K_s, pygame.K_DOWN}))-int(bool(keys & {pygame.K_w, pygame.K_UP})))

    def step(self, seconds, direction=(0, 0), running=False):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= 60:
            raise ValueError('Preview time must be finite and between 0 and 60 seconds')
        if not self.running or not self.focused:return
        remaining = float(seconds)
        while remaining > 1e-10:
            delta = min(1/60, remaining)
            self.player.update(direction, delta, self.world, running=running)
            self.elapsed_ms += delta*1000
            remaining -= delta
        self.world.reduced_motion = self.reduced_motion
        self.camera = camera_for(self.player.position, self.world.size)

    @property
    def draw_clock(self):
        return self.elapsed_ms if self.pulse_mode == 0 else 0. if self.pulse_mode == 1 else 3000.

    def draw(self):
        self.world.reduced_motion = self.reduced_motion
        self.world.draw(self.canvas, self.camera, self.player, self.draw_clock, include_ui=False)
        if self.material_view:
            # Reuse the exact scenery/actor ordering with the light pass absent;
            # this is a source-material comparison, not a different mock image.
            World.draw(self.world, self.canvas, self.camera, self.player, self.draw_clock, include_ui=False)
        width, height = self.window.get_size()
        scale = max(1, min(width//VIEW_SIZE[0], height//VIEW_SIZE[1]))
        size = VIEW_SIZE[0]*scale, VIEW_SIZE[1]*scale
        origin = (width-size[0])//2, (height-size[1])//2
        if self.ui_surface is None or self.ui_surface.get_size() != size:self.ui_surface = pygame.Surface(size)
        pygame.transform.scale(self.canvas, size, self.ui_surface)
        if self.show_guide:
            painter = self.ui.painter(self.ui_surface)
            painter.panel((8, 8, 464, 25))
            painter.text('Dungeon asset pack review', (16, 13), role='label', bold=True)
            mode = 'Material colors' if self.material_view else 'Crystal lighting'
            painter.text(mode, (464, 15), role='small', anchor='topright')
            painter.panel((8, 268, 464, 44))
            painter.text('WASD / arrows: move   Shift: run   Space: hold pulse', (16, 273), role='small')
            motion = 'on' if self.reduced_motion else 'off'
            painter.text(f'L: materials   R: reduced motion ({motion})   H: guide', (16, 287), role='small')
            painter.text('Home: reset   Esc: close', (16, 300), role='small')
        self.window.fill('#161c1b')
        self.window.blit(self.ui_surface, origin)
        pygame.display.flip()
        return self.window

    def close(self):
        self.running = False
        self.keys.clear()
        pygame.quit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--frames', type=int, default=0)
    parser.add_argument('--screenshot', type=Path)
    parser.add_argument('--reduced-motion', action='store_true')
    parser.add_argument('--materials', action='store_true')
    parser.add_argument('--hide-guide', action='store_true')
    args = parser.parse_args(argv)
    if args.frames < 0:parser.error('--frames must be nonnegative')
    if args.headless:
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy');os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    limit = args.frames or (120 if args.headless else 0)
    demo = DungeonPackDemo(reduced_motion=args.reduced_motion)
    demo.material_view = args.materials
    demo.show_guide = not args.hide_guide
    clock = pygame.time.Clock();count = 0
    try:
        while demo.running and (not limit or count < limit):
            for event in pygame.event.get():demo.handle_event(event)
            seconds = 1/60 if args.headless else min(.1, clock.tick(60)/1000)
            demo.step(seconds, demo.input_direction(), bool(demo.keys & {pygame.K_LSHIFT, pygame.K_RSHIFT}))
            demo.draw();count += 1
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(demo.window, str(args.screenshot))
    finally:demo.close()
    return 0


if __name__ == '__main__':raise SystemExit(main())
