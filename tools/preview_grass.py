"""Play the isolated grass study with Caelan's normal movement and sprites.

This preview constructs the shared World/Player renderer directly. It never
opens a journey, settings file, quest coordinator or an existing town scene.
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

from grass_demo import GrassDemoWorld
from main import Player, VIEW_SIZE, camera_for
from ui_style import UIStyle


MAP_PATH = ROOT/'assets/maps/grass_demo/map.json'


class GrassDemo:
    """A playable, disposable material study using production movement rules."""

    def __init__(self, window_size=(960, 640), reduced_motion=False):
        pygame.display.init()
        pygame.font.init()
        self.window = pygame.display.set_mode(self._window_size(window_size), pygame.RESIZABLE)
        pygame.display.set_caption('Project JRPG — Grass demonstration')
        self.canvas = pygame.Surface(VIEW_SIZE)
        self.ui_surface = None
        self.ui = UIStyle(self)
        self.reduced_motion = bool(reduced_motion)
        self.show_guide = True
        self.running = True
        self.focused = True
        self.keys = set()
        self.reset()

    @staticmethod
    def _window_size(size):
        return max(VIEW_SIZE[0], int(size[0])), max(VIEW_SIZE[1], int(size[1]))

    def reset(self):
        cache = self.world._images if hasattr(self, 'world') else None
        self.world = GrassDemoWorld(MAP_PATH, image_cache=cache)
        self.player = Player(self.world)
        self.elapsed_ms = 0.
        self.camera = camera_for(self.player.position, self.world.size)
        self.keys.clear()
        self.world.update_grass(0., self.player, reduced_motion=self.reduced_motion)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            self.keys.add(event.key)
            if not getattr(event, 'repeat', False):
                if event.key == pygame.K_ESCAPE:self.running = False
                elif event.key == pygame.K_r:self.reset()
                elif event.key == pygame.K_h:self.show_guide = not self.show_guide
                elif event.key == pygame.K_m:self.reduced_motion = not self.reduced_motion
        elif event.type == pygame.KEYUP:
            self.keys.discard(event.key)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.keys.clear()
            self.focused = False
        elif event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
        elif event.type == pygame.VIDEORESIZE:
            self.window = pygame.display.set_mode(self._window_size((event.w, event.h)),
                                                 pygame.RESIZABLE)
        return self.running

    def input_direction(self):
        keys = self.keys
        return (int(bool(keys & {pygame.K_d, pygame.K_RIGHT}))
                -int(bool(keys & {pygame.K_a, pygame.K_LEFT})),
                int(bool(keys & {pygame.K_s, pygame.K_DOWN}))
                -int(bool(keys & {pygame.K_w, pygame.K_UP})))

    def step(self, seconds, direction=(0, 0), running=False):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= 60:
            raise ValueError('Preview time must be a finite number from 0 to 60 seconds')
        if not self.running or not self.focused:return
        # Contact is sampled along actual travel, even for a longer capture
        # step. Crossing a clump cannot skip its parting/recovery sequence.
        remaining = float(seconds)
        while remaining > 1e-10:
            delta = min(1/60, remaining)
            self.player.update(direction, delta, self.world, running=running)
            self.world.update_grass(delta, self.player, reduced_motion=self.reduced_motion)
            self.elapsed_ms += delta*1000
            remaining -= delta
        self.camera = camera_for(self.player.position, self.world.size)

    def region_label(self):
        point = self.player.position
        for region in self.world.data.get('regions', []):
            if 'rect' in region and pygame.Rect(region['rect']).collidepoint(point):
                return region['label']
            polygon = region.get('polygon', [])
            inside = False
            for first, second in zip(polygon, polygon[1:]+polygon[:1]):
                if (first[1] > point.y) != (second[1] > point.y):
                    cross = ((second[0]-first[0])*(point.y-first[1])
                             /(second[1]-first[1])+first[0])
                    if point.x < cross:inside = not inside
            if inside:return region['label']
        return 'Grass demonstration'

    def draw(self):
        self.world.draw(self.canvas, self.camera, self.player, self.elapsed_ms, include_ui=False)
        width, height = self.window.get_size()
        scale = max(1, min(width//VIEW_SIZE[0], height//VIEW_SIZE[1]))
        size = VIEW_SIZE[0]*scale, VIEW_SIZE[1]*scale
        origin = (width-size[0])//2, (height-size[1])//2
        if self.ui_surface is None or self.ui_surface.get_size() != size:
            self.ui_surface = pygame.Surface(size)
        pygame.transform.scale(self.canvas, size, self.ui_surface)
        if self.show_guide:
            painter = self.ui.painter(self.ui_surface)
            painter.panel((8, 8, 464, 24))
            painter.text('Grass demonstration', (16, 13), role='label', bold=True)
            painter.text(self.region_label(), (464, 14), role='small', anchor='topright')
            painter.panel((8, 278, 464, 34))
            painter.text('WASD / arrows: move   Shift: run   R: reset', (16, 282), role='small')
            motion = 'reduced' if self.reduced_motion else 'normal'
            painter.text(f'H: hide guide   M: motion ({motion})   Esc: close',
                         (16, 296), role='small')
        self.window.fill('#10271f')
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
    parser.add_argument('--frames', type=int, default=0,
                        help='Stop after this many frames; headless defaults to 120.')
    parser.add_argument('--screenshot', type=Path)
    parser.add_argument('--reduced-motion', action='store_true')
    args = parser.parse_args(argv)
    if args.frames < 0:parser.error('--frames must be nonnegative')
    if args.headless:
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    frames = args.frames or (120 if args.headless else 0)
    demo = GrassDemo(reduced_motion=args.reduced_motion)
    clock = pygame.time.Clock()
    count = 0
    try:
        while demo.running and (not frames or count < frames):
            for event in pygame.event.get():demo.handle_event(event)
            seconds = 1/60 if args.headless else min(.1, clock.tick(60)/1000)
            demo.step(seconds, demo.input_direction(),
                      running=bool(demo.keys & {pygame.K_LSHIFT, pygame.K_RSHIFT}))
            demo.draw()
            count += 1
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(demo.window, str(args.screenshot))
    finally:
        demo.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
