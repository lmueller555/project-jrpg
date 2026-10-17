"""Capture real Eldenmere Pygame screenshots without a physical display."""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
from pathlib import Path
import pygame
from main import Game

def main():
    output=Path("artifacts/eldenmere_grassland")
    output.mkdir(parents=True,exist_ok=True)
    game=Game()
    game.load("eldenmere")
    game.grassland_preview=False
    game.render()
    pygame.image.save(game.world_canvas,str(output/"eldenmere_legacy.png"))
    game.grassland_preview=True
    game.render()
    pygame.image.save(game.world_canvas,str(output/"eldenmere_blob47.png"))
    pygame.quit()
    print("Saved paired 640x448 Eldenmere render screenshots")

if __name__=="__main__":
    main()
