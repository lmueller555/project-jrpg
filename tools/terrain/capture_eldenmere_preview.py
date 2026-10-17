"""Capture Eldenmere with the default native grassland renderer."""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
from pathlib import Path
import pygame
from main import Game

def main():
    out=Path("artifacts/eldenmere_grassland")
    out.mkdir(parents=True,exist_ok=True)
    game=Game()
    game.load("eldenmere")
    game.render()
    pygame.image.save(game.world_canvas,str(out/"eldenmere_default_grassland.png"))
    pygame.quit()
    print("Saved default Eldenmere 640x448 terrain screenshot")

if __name__=="__main__":
    main()
