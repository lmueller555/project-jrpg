"""Open an isolated Aether Lattice preview with temporary rewards and saves.

Run without arguments for the first rank-up and one Emerald. For a wider
exploration fixture, use ``--rp 500 --crystals 10``. No normal journey or
settings file is read or written by this tool.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from main import Game


class LatticePreview:
    """Production game/UI with a disposable journey and explicit sample reward."""

    def __init__(self, rp=20, crystals=None, window_size=(960, 640)):
        self.directory = tempfile.TemporaryDirectory(prefix='aether-lattice-preview-')
        self.path = Path(self.directory.name)
        self.game = Game(window_size=window_size, fullscreen=False, start_on_title=False,
                         save_path=self.path/'journey.json', settings_path=self.path/'settings.json')
        self.game.audio.set_music(0)
        self.game.audio.set_effects(0)
        pygame.event.clear()
        pygame.display.set_caption('Aether Lattice — isolated preview')
        drops = ({'aether_emerald': 1} if crystals is None else
                 {identifier: crystals for identifier in self.game.lattice.board.crystals}
                 if crystals else {})
        awards = {'caelan': rp} if rp else {}
        if awards or drops:
            if not self.game.award_battle_rewards('preview_start', awards, drops):
                self.close()
                raise ValueError('The preview reward could not be applied.')
        self.open_menu('Aether Lattice')

    def key(self, key, **extra):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=key, repeat=False, **extra))
        if not self.game.handle_events():raise RuntimeError('The preview was closed during input.')

    def point(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+logical[0]*scale),
                round((height-320*scale)//2+logical[1]*scale))

    def click(self, logical):
        point = self.point(logical)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        if not self.game.handle_events():raise RuntimeError('The preview was closed during input.')

    def hover(self, logical):
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=self.point(logical),
                                            rel=(0, 0), buttons=(0, 0, 0)))
        if not self.game.handle_events():raise RuntimeError('The preview was closed during input.')

    def advance(self, seconds=.25, draw=True):
        """Advance the real paused-menu update loop at deterministic 60 Hz."""
        if seconds < 0:raise ValueError('Preview time must be nonnegative.')
        count = max(1, math.ceil(seconds*60))
        for _ in range(count):
            if not self.game.handle_events():raise RuntimeError('The preview was closed during animation.')
            self.game.update(seconds/count)
            if draw:self.game.draw()

    def open_menu(self, label):
        for _ in range(3):
            if self.game.pause.overlay is None:break
            self.key(pygame.K_ESCAPE)
        if self.game.pause.overlay is not None:raise RuntimeError('The preview overlay did not close.')
        if not self.game.pause.is_open:self.key(pygame.K_ESCAPE)
        target = self.game.pause.options.index(label)
        for _ in range(len(self.game.pause.options)):
            if self.game.pause.selected == target:break
            self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)

    def select_node(self, identifier):
        """Move the real UI cursor with Tab, without spending lattice Steps."""
        if identifier not in self.game.lattice.board.nodes:raise ValueError('Unknown preview node.')
        for _ in range(len(self.game.lattice.board.nodes)+1):
            if self.game.lattice_ui.selected == identifier:
                self.advance()
                return
            self.key(pygame.K_TAB)
        raise RuntimeError('The lattice cursor could not reach the selected node.')

    def resize(self, size, text_scale=1.0):
        self.game.windowed_size = tuple(size)
        self.game.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.game.audio.set_text_scale(text_scale)
        self.game.draw()

    def close(self):
        if getattr(self, 'game', None) is not None:
            self.game.opening_audio.reset()
        pygame.quit()
        self.directory.cleanup()

    def __enter__(self):return self

    def __exit__(self, *_):self.close()


def nonnegative(value):
    result = int(value)
    if result < 0:raise argparse.ArgumentTypeError('Use zero or a positive integer.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rp', type=nonnegative, default=20, help='Sample Resonance Points (default: 20).')
    parser.add_argument('--crystals', type=nonnegative, default=None,
                        help='Sample quantity of every crystal; default is one Emerald only.')
    parser.add_argument('--headless', action='store_true', help='Use an offscreen display.')
    parser.add_argument('--frames', type=nonnegative, default=0, help='Exit after this many frames (0: interactive).')
    parser.add_argument('--screenshot', type=Path, help='Save the final rendered preview.')
    args = parser.parse_args(argv)
    if args.headless:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    with LatticePreview(args.rp, args.crystals) as preview:
        game = preview.game
        clock = pygame.time.Clock()
        limit = args.frames or (1 if args.headless else 0)
        count = 0
        while game.handle_events():
            seconds = 1/60 if args.headless else min(clock.tick(60)/1000, .1)
            game.update(seconds);game.draw();count += 1
            if limit and count >= limit:break
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(game.window, str(args.screenshot))
    return 0


if __name__ == '__main__':raise SystemExit(main())
