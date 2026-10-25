"""Review the stationary household through the actual game renderer."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
from pathlib import Path
import sys

import pygame
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card

OUT=ROOT/'docs/reviews/liam_household'


def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    game=main.Game(fullscreen=False,start_on_title=False)
    game.world=game._scene_by_id('liam_house')
    game.player.position.update(214,270)
    game.update(.5,(0,0),False);game.draw()
    im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    card(im,"Liam's family at home",'Liam, his parents and Daisy | stationary poses | no dialogue or routines',2).save(OUT/'household.png')
    # Render without the HUD for an unobstructed floor-level close-up.
    camera=(-24,16);game.world.draw(game.canvas,camera,game.player,game.elapsed_ms)
    im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    crop=im.crop((96,234,178,282))
    card(crop,"Daisy's resting spot",'Still lying pose on a woven rug | 8x native pixels',8).save(OUT/'daisy_rug.png')
    pygame.quit()
    print('Captured stationary household and Daisy rug close-up from the actual game renderer.')


if __name__=='__main__':capture()
