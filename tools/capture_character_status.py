"""Capture the real pause/status flow at normal and enlarged text sizes."""
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from main import Game


def main():
    output = ROOT/'work/character-status'
    output.mkdir(parents=True, exist_ok=True)
    game = Game(fullscreen=False, start_on_title=False)
    game.audio.set_music(0)
    game.audio.set_effects(0)
    game.pause.open()
    game.pause.selected = game.pause.options.index('Status')
    game.pause.activate()
    game.status_ui._select('spr')
    for scale, suffix in ((1.0, 'normal'), (1.5, 'large')):
        game.audio.set_text_scale(scale)
        game.draw()
        pygame.image.save(game.window, str(output/('status_'+suffix+'.png')))
    game.status_ui.close()
    game.pause.overlay = None
    game.draw()
    pygame.image.save(game.window, str(output/'pause_large.png'))
    pygame.quit()
    print(output)


if __name__ == '__main__':main()
