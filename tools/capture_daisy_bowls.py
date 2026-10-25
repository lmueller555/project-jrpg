"""Actual room placement plus enlarged full/half/empty bowl comparisons."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
from pathlib import Path
import sys

import pygame
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from build_liam_family_front_walks import font

OUT=ROOT/'docs/reviews/daisy_bowls'


def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    game=main.Game(fullscreen=False,start_on_title=False)
    game.world=game._scene_by_id('liam_house');game.player.position.update(214,270)
    game.update(.5,(0,0),False);game.draw()
    im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    card(im,"Daisy's wooden food and water bowls",'Full bowls placed side by side beside her rug | no routines yet',2).save(OUT/'interior.png')
    game.world.draw(game.canvas,(-24,16),game.player,game.elapsed_ms)
    im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    card(im.crop((100,232,226,284)),"Daisy's rug and feeding bowls",'Wooden food bowl on the left; water bowl on the right',6).save(OUT/'closeup.png')
    pygame.quit()
    meta=main.read_json(ROOT/'assets/terrain/eldenmere/liam_home/bowls/bowls.json')
    scale=14;stride=24*scale+32
    board=Image.new('RGB',(24+3*stride,104+2*(24*scale+52)),'#e8edf2')
    d=ImageDraw.Draw(board);d.fontmode='1'
    d.text((24,16),'Daisy / wooden bowls and fill states',font=font(26),fill='#26343e')
    d.text((24,56),'24x24 frames | full, half-full and empty | shared 14x scale',font=font(18),fill='#52616c')
    for row,kind in enumerate(('food','water')):
        for col,state in enumerate(('full','half_full','empty')):
            image=Image.open(ROOT/meta['bowls'][kind]['states'][state]['image_from_repo_root']).convert('RGBA')
            image=image.resize((24*scale,24*scale),Image.Resampling.NEAREST)
            x=24+col*stride;y=104+row*(24*scale+52)
            board.paste(image,(x,y),image)
            d.text((x,y+24*scale+8),f'{kind.title()} / {state.replace("_","-")}',font=font(20),fill='#26343e')
    board.save(OUT/'all_variants.png')
    print('Captured actual in-game bowls and all six enlarged fill variants.')


if __name__=='__main__':capture()
